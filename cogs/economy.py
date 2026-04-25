import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
import random
from datetime import datetime, timedelta
# --- 追加: Firebase用のライブラリ ---
from firebase_admin import db
# ------------------------------

DATA_FILE = 'data.json'
SHOP_FILE = 'shop_items.json'
GACHA_FILE = 'gacha_items.json' 
SHOP_JS_FILE = 'shop_items.js'
AUTH_FILE = 'user_auth.json' 
CONFIG_FILE = 'config.json'  
WEB_JSON_FILE = 'shop_item.json' 

# --- パスワード管理用 Cog ---
class Auth(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_auth(self):
        if not os.path.exists(AUTH_FILE): return {}
        with open(AUTH_FILE, 'r', encoding='utf-8') as f: return json.load(f)

    def save_auth(self, data):
        with open(AUTH_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2, ensure_ascii=False)

    @app_commands.command(name="パスワード設定", description="決済用の個人パスワードを設定します（重複不可）")
    async def set_password(self, interaction: discord.Interaction, パスワード: str):
        await interaction.response.defer(ephemeral=True)

        pwd_save = パスワード.strip()
        if len(pwd_save) < 4:
            await interaction.followup.send("パスワードは4文字以上にしてください。", ephemeral=True)
            return

        auth_data = self.load_auth()
        user_id = str(interaction.user.id)

        if pwd_save in auth_data.values():
            current_owner_id = next((uid for uid, pwd in auth_data.items() if pwd == pwd_save), None)
            if current_owner_id != user_id:
                await interaction.followup.send("❌ そのパスワードは既に他のユーザーに使用されています。", ephemeral=True)
                return

        auth_data[user_id] = pwd_save
        self.save_auth(auth_data)

        economy_cog = self.bot.get_cog('Economy')
        if economy_cog:
            economy_cog.update_web_data()
            await interaction.followup.send(f"✅ パスワードを「{pwd_save}」に設定し、Webサイトへ同期しました。", ephemeral=True)
        else:
            await interaction.followup.send(f"✅ パスワードを設定しました。Web購入時に使用してください。", ephemeral=True)

# --- 請求書用のボタン ---
class BillView(discord.ui.View):
    def __init__(self, cog, amount, requester):
        super().__init__(timeout=3600)
        self.cog = cog
        self.amount = amount
        self.requester = requester

    @discord.ui.button(label="支払う", style=discord.ButtonStyle.danger)
    async def pay(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        data = self.cog.load_data()
        payer_id = str(interaction.user.id)
        receiver_id = str(self.requester.id)
        payer_money = data.get(payer_id, {}).get('money', 0)

        if payer_money < self.amount:
            await interaction.followup.send(f"所持金が足りないため支払えません！", ephemeral=True)
            return

        if receiver_id not in data: data[receiver_id] = {'money': 0}
        data[payer_id]['money'] -= self.amount
        data[receiver_id]['money'] += self.amount
        self.cog.save_data(data)
        self.cog.update_web_data()

        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        await interaction.followup.send(f"✅ {self.requester.display_name} さんに **{self.amount}{self.cog.currency}** 支払いました！")
        try:
            await self.requester.send(f"💰 **{interaction.user.display_name}** さんが請求書（{self.amount}{self.cog.currency}）を支払いました！")
        except:
            pass

# --- ロール購入確定用のボタン ---
class ShopBillView(discord.ui.View):
    def __init__(self, cog, role_id, price, role_name):
        super().__init__(timeout=3600)
        self.cog = cog
        self.role_id = role_id
        self.price = price
        self.role_name = role_name

    @discord.ui.button(label="購入を確定して支払う", style=discord.ButtonStyle.green)
    async def pay(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        data = self.cog.load_data()
        user_id = str(interaction.user.id)
        user_money = data.get(user_id, {}).get('money', 0)

        if user_money < self.price:
            await interaction.followup.send(f"所持金が足りません！ (必要: {self.price}{self.cog.currency})", ephemeral=True)
            return

        data[user_id]['money'] -= self.price
        expiry_date = (datetime.now() + timedelta(days=30)).isoformat()
        if 'subscriptions' not in data[user_id]: data[user_id]['subscriptions'] = {}
        data[user_id]['subscriptions'][str(self.role_id)] = expiry_date
        self.cog.save_data(data)
        self.cog.update_web_data()

        role = interaction.guild.get_role(int(self.role_id))
        if role:
            try:
                await interaction.user.add_roles(role)
                await interaction.followup.send(f"✅ 「{self.role_name}」を購入しました！有効期限は30日間です。", ephemeral=False)
            except:
                await interaction.followup.send("❌ ロール付与権限がボットにありません。", ephemeral=True)
        else:
            await interaction.followup.send("❌ ロールが見つかりませんでした。", ephemeral=True)

# --- デイリー報酬用のボタン ---
class DailyButton(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="デイリー報酬を受け取る", style=discord.ButtonStyle.green, custom_id="daily_reward_button")
    async def receive_daily(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        data = self.cog.load_data()
        user_id = str(interaction.user.id)
        now = datetime.now()
        if user_id not in data: data[user_id] = {'money': 0, 'last_daily': None}
        last_daily_str = data[user_id].get('last_daily')

        if last_daily_str:
            last_daily = datetime.fromisoformat(last_daily_str)
            if now < last_daily + timedelta(days=1):
                wait_time = (last_daily + timedelta(days=1)) - now
                h, m = divmod(int(wait_time.total_seconds()), 3600)
                await interaction.followup.send(f"あと {h}時間{m//60}分 待ってください。", ephemeral=True)
                return

        reward = random.randint(500, 1000)
        data[user_id]['money'] += reward
        data[user_id]['last_daily'] = now.isoformat()
        self.cog.save_data(data)
        self.cog.update_web_data()
        await interaction.followup.send(f"💰 **{reward}{self.cog.currency}** 受け取りました！所持金: {data[user_id]['money']}{self.cog.currency}", ephemeral=True)

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_subs.start()
        self._load_config()

    def _load_config(self):
        if not os.path.exists(CONFIG_FILE):
            self.config = {"currency_name": "円"}
            self._save_config()
        else:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                self.config = json.load(f)

    def _save_config(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    @property
    def currency(self):
        return self.config.get("currency_name", "円")

    def load_data(self):
        if not os.path.exists(DATA_FILE): return {}
        with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)

    def save_data(self, data):
        with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2, ensure_ascii=False)

    def load_shop(self):
        if not os.path.exists(SHOP_FILE): return []
        with open(SHOP_FILE, 'r', encoding='utf-8') as f: return json.load(f)

    def save_shop(self, shop_data):
        with open(SHOP_FILE, 'w', encoding='utf-8') as f: json.dump(shop_data, f, indent=2, ensure_ascii=False)

    def load_gacha(self):
        if not os.path.exists(GACHA_FILE): return []
        with open(GACHA_FILE, 'r', encoding='utf-8') as f: return json.load(f)

    def save_gacha(self, gacha_data):
        with open(GACHA_FILE, 'w', encoding='utf-8') as f: json.dump(gacha_data, f, indent=2, ensure_ascii=False)

    def load_auth(self):
        if not os.path.exists(AUTH_FILE): return {}
        with open(AUTH_FILE, 'r', encoding='utf-8') as f: return json.load(f)

    def update_web_data(self):
        try:
            shop_data = self.load_shop()
            gacha_data = self.load_gacha()
            user_data = self.load_data()
            auth_data = self.load_auth()
            profiles = {}

            for user_id, info in user_data.items():
                pwd = auth_data.get(user_id)
                if pwd:
                    member = None
                    for guild in self.bot.guilds:
                        member = guild.get_member(int(user_id))
                        if member: break

                    display_name = member.display_name if member else f"User_{user_id[-4:]}"
                    avatar_url = str(member.display_avatar.url) if member else "https://discord.com/assets/f78426a064bc98b57351.png"

                    profiles[pwd] = {
                        "name": display_name,
                        "avatar": avatar_url,
                        "money": info.get('money', 0),
                        "subs_count": len(info.get('subscriptions', {}))
                    }

            web_json_content = {
                "SHOP_DATA": shop_data,
                "GACHA_DATA": gacha_data,
                "CURRENCY_NAME": self.currency,
                "USER_PROFILES": profiles
            }

            # --- Firebaseへ送信 ---
            ref = db.reference('/') # ルートに保存
            ref.set(web_json_content)

            # ローカルにも念のため保存
            with open(WEB_JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(web_json_content, f, indent=4, ensure_ascii=False)

            print(f"✅ Firebaseへのリアルタイム送信が完了しました。")
            return True
        except Exception as e:
            print(f"Firebase Update Error: {e}")
            return False

    @app_commands.command(name="ガチャ追加", description="Webサイト用のガチャロールを登録します")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(種別=[
        app_commands.Choice(name="通常", value="normal"),
        app_commands.Choice(name="期間限定", value="limited_time"),
        app_commands.Choice(name="数量限定", value="limited_stock")
    ])
    async def add_gacha(self, interaction: discord.Interaction, 種別: str, ロール: discord.Role, シリーズ名: str, 在庫数: int = -1):
        await interaction.response.defer(ephemeral=True)
        if 種別 == "limited_stock" and 在庫数 <= 0:
            await interaction.followup.send("❌ 「数量限定」の場合は、在庫数を1以上に設定してください。", ephemeral=True)
            return

        gacha_data = self.load_gacha()
        gacha_data.append({
            "id": str(ロール.id),
            "name": ロール.name,
            "type": 種別,
            "series": シリーズ名,
            "stock": 在庫数 if 種別 == "limited_stock" else -1
        })
        self.save_gacha(gacha_data)
        self.update_web_data()
        await interaction.followup.send(f"✅ ガチャに「{シリーズ名}：{ロール.name}」を登録しました。", ephemeral=True)

    @app_commands.command(name="通貨発行", description="指定したユーザーに通貨を付与します（管理者専用）")
    @app_commands.checks.has_permissions(administrator=True)
    async def mint_money(self, interaction: discord.Interaction, 相手: discord.Member, 金額: int):
        await interaction.response.defer(ephemeral=True)
        if 金額 <= 0:
            await interaction.followup.send("1以上の金額を指定してください。", ephemeral=True)
            return
        data = self.load_data()
        rid = str(相手.id)
        if rid not in data: data[rid] = {'money': 0}
        data[rid]['money'] += 金額
        self.save_data(data)
        self.update_web_data()
        await interaction.followup.send(f"✅ {相手.display_name} さんに **{金額}{self.currency}** を発行しました。", ephemeral=True)

    @app_commands.command(name="通貨名変更", description="通貨の単位を変更します（管理者専用）")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_currency_name(self, interaction: discord.Interaction, 新名称: str):
        await interaction.response.defer(ephemeral=True)
        self.config["currency_name"] = 新名称
        self._save_config()
        self.update_web_data()
        await interaction.followup.send(f"✅ 通貨単位を **{新名称}** に変更しました。", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot and message.content.startswith("!pay_req"):
            try:
                parts = message.content.split()
                if len(parts) < 5: return
                input_password, role_id, price = parts[1], int(parts[2]), int(parts[3])
                item_name = " ".join(parts[4:])

                auth_data = self.load_auth()
                target_user_id = next((uid for uid, pwd in auth_data.items() if pwd == input_password), None)

                if not target_user_id:
                    await message.channel.send(f"⚠️ パスワードに一致するユーザーが見つかりません。")
                    return

                data = self.load_data()
                if target_user_id not in data: data[target_user_id] = {'money': 0}

                if data[target_user_id].get('money', 0) < price:
                    await message.channel.send(f"❌ <@{target_user_id}> さんの残高が足りません。")
                    return

                data[target_user_id]['money'] -= price
                expiry_date = (datetime.now() + timedelta(days=30)).isoformat()
                if 'subscriptions' not in data[target_user_id]: data[target_user_id]['subscriptions'] = {}
                data[target_user_id]['subscriptions'][str(role_id)] = expiry_date
                self.save_data(data)
                self.update_web_data()

                member = None
                for guild in self.bot.guilds:
                    member = guild.get_member(int(target_user_id))
                    if member: break

                if member:
                    role = member.guild.get_role(role_id)
                    if role: await member.add_roles(role)

                embed = discord.Embed(title="💳 自動決済完了", color=0x43b581)
                embed.add_field(name="購入者", value=f"<@{target_user_id}>")
                embed.add_field(name="商品", value=item_name)
                await message.channel.send(embed=embed)
            except Exception as e: print(f"Error: {e}")

    @tasks.loop(hours=24)
    async def check_subs(self):
        data = self.load_data()
        now = datetime.now()
        changed = False
        for user_id, info in data.items():
            subs = info.get('subscriptions', {})
            for role_id, expiry_str in list(subs.items()):
                if now > datetime.fromisoformat(expiry_str):
                    for guild in self.bot.guilds:
                        member = guild.get_member(int(user_id))
                        role = guild.get_role(int(role_id))
                        if member and role:
                            try: await member.remove_roles(role)
                            except: pass
                    del data[user_id]['subscriptions'][role_id]
                    changed = True
        if changed: 
            self.save_data(data)
            self.update_web_data()

    @app_commands.command(name="設置_デイリー", description="デイリー報酬のボタンを設置します")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_daily(self, interaction: discord.Interaction, 画像: discord.Attachment = None):
        view = DailyButton(self)
        embed = discord.Embed(title="✨ デイリー報酬 ✨", description="ボタンを押して報酬をゲット！", color=discord.Color.gold())
        if 画像: embed.set_image(url=画像.url)
        await interaction.response.send_message("設置完了", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)

    @app_commands.command(name="所持金", description="所持金を確認します")
    async def wallet(self, interaction: discord.Interaction):
        data = self.load_data()
        money = data.get(str(interaction.user.id), {}).get('money', 0)
        await interaction.response.send_message(f'あなたの所持金は **{money}{self.currency}** です。', ephemeral=True)

    @app_commands.command(name="働く", description="お金を稼ぎます")
    async def work(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = self.load_data()
        u_id = str(interaction.user.id)
        if u_id not in data: data[u_id] = {'money': 0}
        earned = random.randint(10, 100)
        data[u_id]['money'] += earned
        self.save_data(data)
        self.update_web_data()
        await interaction.followup.send(f'**{earned}{self.currency}** 稼ぎました！', ephemeral=True)

    @app_commands.command(name="送金", description="相手にお金を送ります")
    async def send_money(self, interaction: discord.Interaction, 相手: discord.Member, 金額: int):
        await interaction.response.defer(ephemeral=True)
        if 金額 <= 0 or 相手.id == interaction.user.id:
            await interaction.followup.send("無効な操作です。", ephemeral=True)
            return
        data = self.load_data()
        sid, rid = str(interaction.user.id), str(相手.id)
        if data.get(sid, {}).get('money', 0) < 金額:
            await interaction.followup.send("残高不足です。", ephemeral=True)
            return
        if rid not in data: data[rid] = {'money': 0}
        data[sid]['money'] -= 金額
        data[rid]['money'] += 金額
        self.save_data(data)
        self.update_web_data()
        await interaction.followup.send(f"✅ {相手.display_name} さんに **{金額}{self.currency}** 送金しました！", ephemeral=True)

    @app_commands.command(name="請求書", description="相手にDMで請求書を送ります")
    async def bill(self, interaction: discord.Interaction, 相手: discord.Member, 金額: int):
        if 金額 <= 0 or 相手.id == interaction.user.id: return
        view = BillView(self, 金額, interaction.user)
        embed = discord.Embed(title="📄 請求書", description=f"金額: {金額}{self.currency}\n請求者: {interaction.user.display_name}", color=discord.Color.red())
        try:
            await 相手.send(embed=embed, view=view)
            await interaction.response.send_message(f"✅ {相手.display_name} さんに送信しました。", ephemeral=True)
        except:
            await interaction.response.send_message("❌ DM送信に失敗しました。", ephemeral=True)

    @app_commands.command(name="ショップ追加", description="Webサイト用の販売ロールを登録します")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_shop(self, interaction: discord.Interaction, ロール: discord.Role, 価格: int, 説明: str):
        await interaction.response.defer(ephemeral=True)
        shop_data = self.load_shop()
        shop_data.append({"id": str(ロール.id), "name": ロール.name, "price": 価格, "desc": 説明})
        self.save_shop(shop_data)
        self.update_web_data()
        await interaction.followup.send(f"✅ 「{ロール.name}」を登録しました。", ephemeral=True)

    @app_commands.command(name="購入案内送信", description="手動でロール購入ボタンをDMします")
    @app_commands.checks.has_permissions(administrator=True)
    async def send_shop_bill(self, interaction: discord.Interaction, 相手: discord.Member, ロールid: str):
        shop_data = self.load_shop()
        item = next((i for i in shop_data if i['id'] == ロールid), None)
        if not item: return
        view = ShopBillView(self, item['id'], item['price'], item['name'])
        embed = discord.Embed(title="🛒 購入手続き", description=f"商品: **{item['name']}**\n価格: **{item['price']}{self.currency}**", color=discord.Color.green())
        try:
            await 相手.send(embed=embed, view=view)
            await interaction.response.send_message(f"✅ {相手.display_name} さんに送信しました。", ephemeral=True)
        except:
            await interaction.response.send_message("❌ DM送信に失敗しました。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Auth(bot))
    await bot.add_cog(Economy(bot))
