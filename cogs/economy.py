
import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
import random
from datetime import datetime, timedelta
# --- Firebase用のライブラリ ---
from firebase_admin import db
# ------------------------------

DATA_FILE = 'data.json'
SHOP_FILE = 'shop_items.json'
GACHA_FILE = 'gacha_items.json' 
SHOP_JS_FILE = 'shop_items.js'
AUTH_FILE = 'user_auth.json' 
CONFIG_FILE = 'config.json'  
WEB_JSON_FILE = 'shop_item.json' 
MISSION_FILE = 'missions.json'

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
            await interaction.followup.send(f"✅ パスワードを設定し、Webサイトへ同期しました。", ephemeral=True)
        else:
            await interaction.followup.send(f"✅ パスワードを設定しました。", ephemeral=True)

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
            await interaction.followup.send(f"所持金が足りません！", ephemeral=True)
            return
        if receiver_id not in data: data[receiver_id] = self.cog.get_default_user_data()

        # お金の移動
        data[payer_id]['money'] -= self.amount
        data[receiver_id]['money'] += self.amount

        # 送金累計の加算
        data[payer_id]['send_money_total'] = data[payer_id].get('send_money_total', 0) + self.amount

        self.cog.save_data(data); self.cog.update_web_data()
        for item in self.children: item.disabled = True
        await interaction.message.edit(view=self)
        await interaction.followup.send(f"✅ {self.requester.display_name} さんに支払いました！")

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
            await interaction.followup.send(f"所持金が足りません！", ephemeral=True)
            return
        data[user_id]['money'] -= self.price
        expiry_date = (datetime.now() + timedelta(days=30)).isoformat()
        data[user_id].setdefault('subscriptions', {})[str(self.role_id)] = expiry_date
        self.cog.save_data(data); self.cog.update_web_data()
        role = interaction.guild.get_role(int(self.role_id))
        if role:
            try:
                await interaction.user.add_roles(role)
                await interaction.followup.send(f"✅ 「{self.role_name}」を購入しました！", ephemeral=False)
            except: await interaction.followup.send("❌ ロール付与権限がありません。", ephemeral=True)

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
        if user_id not in data: data[user_id] = self.cog.get_default_user_data()
        last_daily_str = data[user_id].get('last_daily')
        if last_daily_str:
            last_daily = datetime.fromisoformat(last_daily_str)
            if now < last_daily + timedelta(days=1):
                await interaction.followup.send(f"本日は既に受け取り済みです。", ephemeral=True); return
        reward = random.randint(500, 1000)
        data[user_id]['money'] += reward
        data[user_id]['last_daily'] = now.isoformat()
        self.cog.save_data(data); self.cog.update_web_data()
        await interaction.followup.send(f"💰 **{reward}{self.cog.currency}** 獲得！", ephemeral=True)

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_subs.start()
        self.vc_tracking.start()
        self.daily_reset_task.start()
        self._load_config()

    def _load_config(self):
        if not os.path.exists(CONFIG_FILE):
            self.config = {"currency_name": "円", "last_reset_date": datetime.now().date().isoformat()}
            self._save_config()
        else:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f: self.config = json.load(f)

    def _save_config(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(self.config, f, indent=2, ensure_ascii=False)

    def get_default_user_data(self):
        return {
            'money': 0, 'last_daily': None, 'subscriptions': {}, 'inventory': [],
            'chat_chars': 0, 'vc_minutes': 0, 'gacha_count': 0, 'send_money_total': 0,
            'daily_chat': 0, 'daily_vc': 0, 'completed_missions': [], 'claimed_missions': []
        }

    @property
    def currency(self): return self.config.get("currency_name", "円")

    def load_data(self):
        if not os.path.exists(DATA_FILE): return {}
        with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)

    def save_data(self, data):
        with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2, ensure_ascii=False)

    def load_shop(self): return json.load(open(SHOP_FILE, 'r', encoding='utf-8')) if os.path.exists(SHOP_FILE) else []
    def save_shop(self, data): json.dump(data, open(SHOP_FILE, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    def load_gacha(self): return json.load(open(GACHA_FILE, 'r', encoding='utf-8')) if os.path.exists(GACHA_FILE) else []
    def save_gacha(self, data): json.dump(data, open(GACHA_FILE, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    def load_auth(self): return json.load(open(AUTH_FILE, 'r', encoding='utf-8')) if os.path.exists(AUTH_FILE) else {}
    def load_missions(self): return json.load(open(MISSION_FILE, 'r', encoding='utf-8')) if os.path.exists(MISSION_FILE) else {}
    def save_missions(self, data): json.dump(data, open(MISSION_FILE, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)

    def update_web_data(self):
        try:
            shop_data, gacha_data, user_data = self.load_shop(), self.load_gacha(), self.load_data()
            auth_data, missions = self.load_auth(), self.load_missions()
            profiles = {}
            for user_id, info in user_data.items():
                pwd = auth_data.get(user_id)
                if pwd:
                    member = None
                    for g in self.bot.guilds:
                        member = g.get_member(int(user_id))
                        if member: break
                    profiles[pwd] = {
                        "name": member.display_name if member else f"User_{user_id[-4:]}",
                        "avatar": str(member.display_avatar.url) if member else "",
                        "money": info.get('money', 0),
                        "stats": {
                            "chat": info.get('chat_chars', 0), "vc": info.get('vc_minutes', 0),
                            "daily_chat": info.get('daily_chat', 0), "daily_vc": info.get('daily_vc', 0),
                            "send_money_total": info.get('send_money_total', 0)
                        },
                        # インベントリをWebに送る際にも重複を排除
                        "inventory": list(dict.fromkeys(info.get('inventory', []))),
                        "subscriptions": info.get('subscriptions', {}),
                        "completed_missions": info.get('completed_missions', []),
                        "claimed_missions": info.get('claimed_missions', [])
                    }
            web_json = {"SHOP_DATA": shop_data, "GACHA_DATA": gacha_data, "MISSIONS": missions, "CURRENCY_NAME": self.currency, "USER_PROFILES": profiles}
            db.reference('/').set(web_json)
            with open(WEB_JSON_FILE, 'w', encoding='utf-8') as f: json.dump(web_json, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e: print(f"Update Error: {e}"); return False

    @tasks.loop(minutes=30)
    async def daily_reset_task(self):
        current_date = datetime.now().date().isoformat()
        if self.config.get("last_reset_date") != current_date:
            data, missions = self.load_data(), self.load_missions()
            daily_ids = [m_id for m_id, m in missions.items() if m.get('is_daily')]
            for uid in data:
                data[uid]['daily_chat'] = 0
                data[uid]['daily_vc'] = 0
                if 'completed_missions' in data[uid]:
                    data[uid]['completed_missions'] = [m_id for m_id in data[uid]['completed_missions'] if m_id not in daily_ids]
            self.save_data(data)
            self.config["last_reset_date"] = current_date
            self._save_config(); self.update_web_data()
            print("📅 デイリー進捗をリセットしました。")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            if message.content.startswith("!pay_req"): await self.handle_web_payment(message)
            elif message.content.startswith("!mission_pay"): await self.handle_mission_reward(message)
            return
        data = self.load_data()
        uid = str(message.author.id)
        if uid not in data: data[uid] = self.get_default_user_data()
        length = len(message.content)
        data[uid]['chat_chars'] = data[uid].get('chat_chars', 0) + length
        data[uid]['daily_chat'] = data[uid].get('daily_chat', 0) + length
        await self.silent_mission_check(uid, data)
        self.save_data(data)

    async def silent_mission_check(self, uid, data):
        missions = self.load_missions()
        u_data = data[uid]
        completed = u_data.get('completed_missions', [])
        for m_id, m_info in missions.items():
            if m_id in completed: continue
            current = u_data.get(m_info['type'], 0)
            if current >= m_info['goal']:
                if m_id not in completed:
                    completed.append(m_id)
                    u_data['completed_missions'] = completed

    async def handle_mission_reward(self, message):
        try:
            parts = message.content.split()
            pwd, m_id = parts[1], parts[2]
            uid = next((u for u, p in self.load_auth().items() if p == pwd), None)
            if not uid: return
            data, missions = self.load_data(), self.load_missions()
            u_data = data[uid]
            claimed = u_data.get('claimed_missions', [])
            if m_id in claimed: return
            if m_id not in missions: return
            m_info = missions[m_id]
            current = u_data.get(m_info['type'], 0)
            if current >= m_info['goal']:
                u_data['money'] += m_info['reward']
                u_data.setdefault('claimed_missions', []).append(m_id)
                if m_id not in u_data.get('completed_missions', []):
                    u_data.setdefault('completed_missions', []).append(m_id)
                self.save_data(data); self.update_web_data()
                await message.channel.send(f"💰 <@{uid}> がミッション「{m_info['name']}」の報酬獲得！")
        except: pass

    async def handle_web_payment(self, message):
        try:
            parts = message.content.split()
            pwd, role_id, price = parts[1], int(parts[2]), int(parts[3])
            item_name = " ".join(parts[4:])
            uid = next((u for u, p in self.load_auth().items() if p == pwd), None)
            if not uid: return
            data = self.load_data()
            if data.get(uid, {}).get('money', 0) < price: return
            data[uid]['money'] -= price

            if "ガチャ" in item_name:
                data[uid]['gacha_count'] = data[uid].get('gacha_count', 0) + 1
                inventory = data[uid].get('inventory', [])
                target_id_str = str(role_id)
                # インベントリ追加時の重複チェックを強化
                if target_id_str not in inventory:
                    inventory.append(target_id_str)
                    data[uid]['inventory'] = inventory

            expiry = (datetime.now() + timedelta(days=30)).isoformat()
            data[uid].setdefault('subscriptions', {})[str(role_id)] = expiry
            self.save_data(data); self.update_web_data()
            for g in self.bot.guilds:
                m = g.get_member(int(uid))
                r = g.get_role(role_id)
                if m and r: await m.add_roles(r)
            await message.channel.send(f"💳 <@{uid}> が {item_name} を購入！")
        except: pass

    @tasks.loop(minutes=1)
    async def vc_tracking(self):
        data, updated = self.load_data(), False
        for g in self.bot.guilds:
            for vc in g.voice_channels:
                for m in vc.members:
                    if m.bot: continue
                    uid = str(m.id)
                    if uid not in data: data[uid] = self.get_default_user_data()
                    data[uid]['vc_minutes'] = data[uid].get('vc_minutes', 0) + 1
                    data[uid]['daily_vc'] = data[uid].get('daily_vc', 0) + 1
                    await self.silent_mission_check(uid, data)
                    updated = True
        if updated: self.save_data(data); self.update_web_data()

    @tasks.loop(hours=24)
    async def check_subs(self):
        data, now, changed = self.load_data(), datetime.now(), False
        for uid, info in data.items():
            subs = info.get('subscriptions', {})
            for rid, exp in list(subs.items()):
                if now > datetime.fromisoformat(exp):
                    for g in self.bot.guilds:
                        m, r = g.get_member(int(uid)), g.get_role(int(rid))
                        if m and r:
                            try: await m.remove_roles(r)
                            except: pass
                    del data[uid]['subscriptions'][rid]; changed = True
        if changed: self.save_data(data); self.update_web_data()

    # --- 管理者限定コマンド（一般ユーザーには見えない設定） ---

    @app_commands.command(name="図鑑掃除", description="全ユーザーのカード重複を削除します（管理者のみ）")
    @app_commands.default_permissions(administrator=True)
    async def cleanup_inventory_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = self.load_data()
        total_removed = 0
        for uid in data:
            if 'inventory' in data[uid] and isinstance(data[uid]['inventory'], list):
                old_list = data[uid]['inventory']
                new_list = list(dict.fromkeys(old_list))
                diff = len(old_list) - len(new_list)
                if diff > 0:
                    data[uid]['inventory'] = new_list
                    total_removed += diff
        if total_removed > 0:
            self.save_data(data); self.update_web_data()
            await interaction.followup.send(f"✅ 合計 {total_removed} 個の重複アイテムを掃除しました。", ephemeral=True)
        else:
            await interaction.followup.send("重複は見つかりませんでした。", ephemeral=True)

    @app_commands.command(name="ミッション追加", description="新しいミッションと報酬を登録します（管理者のみ）")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(タイプ=[
        app_commands.Choice(name="累計チャット文字数", value="chat_chars"),
        app_commands.Choice(name="デイリーチャット文字数", value="daily_chat"),
        app_commands.Choice(name="累計VC時間(分)", value="vc_minutes"),
        app_commands.Choice(name="デイリーVC時間(分)", value="daily_vc"),
        app_commands.Choice(name="累計ガチャ回数", value="gacha_count")
    ])
    async def add_mission(self, interaction: discord.Interaction, 名前: str, 報酬金額: int, 目標値: int, タイプ: str, デイリー設定: bool):
        await interaction.response.defer(ephemeral=True)
        missions = self.load_missions()
        m_id = f"m_{タイプ}_{random.randint(1000, 9999)}"
        missions[m_id] = {"name": 名前, "reward": 報酬金額, "goal": 目標値, "type": タイプ, "is_daily": デイリー設定}
        self.save_missions(missions); self.update_web_data()
        await interaction.followup.send(f"✅ ミッション「{名前}」を追加しました。\n報酬: {報酬金額} {self.currency} / 目標: {目標値}", ephemeral=True)

    @app_commands.command(name="ミッション削除", description="ミッションを削除します（管理者のみ）")
    @app_commands.default_permissions(administrator=True)
    async def delete_mission(self, interaction: discord.Interaction, ミッション名: str):
        await interaction.response.defer(ephemeral=True)
        missions = self.load_missions()
        target_id = next((m_id for m_id, m in missions.items() if m['name'] == ミッション名), None)
        if target_id:
            del missions[target_id]
            self.save_missions(missions); self.update_web_data()
            await interaction.followup.send(f"✅ ミッション「{ミッション名}」を削除しました。", ephemeral=True)
        else: await interaction.followup.send("❌ 見つかりませんでした。", ephemeral=True)

    @delete_mission.autocomplete('ミッション名')
    async def mission_autocomplete(self, interaction: discord.Interaction, current: str):
        missions = self.load_missions()
        return [app_commands.Choice(name=m['name'], value=m['name']) for m in missions.values() if current.lower() in m['name'].lower()][:25]

    @app_commands.command(name="ガチャ追加", description="Web用ガチャを登録します（管理者のみ）")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(種別=[
        app_commands.Choice(name="通常", value="normal"),
        app_commands.Choice(name="期間限定", value="limited_time"),
        app_commands.Choice(name="数量限定", value="limited_stock")
    ])
    async def add_gacha(self, interaction: discord.Interaction, 種別: str, ロール: discord.Role, シリーズ名: str, 在庫数: int = -1):
        await interaction.response.defer(ephemeral=True)
        gacha_data = self.load_gacha()
        gacha_data.append({"id": str(ロール.id), "name": ロール.name, "type": 種別, "series": シリーズ名, "stock": 在庫数})
        self.save_gacha(gacha_data); self.update_web_data()
        await interaction.followup.send(f"✅ ガチャに「{ロール.name}」を登録しました。", ephemeral=True)

    @app_commands.command(name="通貨発行", description="指定したユーザーに通貨を付与します（管理者のみ）")
    @app_commands.default_permissions(administrator=True)
    async def mint_money(self, interaction: discord.Interaction, 相手: discord.Member, 金額: int):
        await interaction.response.defer(ephemeral=True)
        data = self.load_data()
        rid = str(相手.id)
        if rid not in data: data[rid] = self.get_default_user_data()
        data[rid]['money'] += 金額
        self.save_data(data); self.update_web_data()
        await interaction.followup.send(f"✅ {相手.display_name} に {金額}{self.currency} 発行しました。", ephemeral=True)

    @app_commands.command(name="通貨名変更", description="通貨の単位を変更します（管理者のみ）")
    @app_commands.default_permissions(administrator=True)
    async def set_currency_name(self, interaction: discord.Interaction, 新名称: str):
        self.config["currency_name"] = 新名称
        self._save_config(); self.update_web_data()
        await interaction.response.send_message(f"✅ 通貨単位を {新名称} に変更しました。", ephemeral=True)

    @app_commands.command(name="設置_デイリー", description="デイリー報酬ボタンを設置します（管理者のみ）")
    @app_commands.default_permissions(administrator=True)
    async def setup_daily(self, interaction: discord.Interaction, 画像: discord.Attachment = None):
        view = DailyButton(self)
        embed = discord.Embed(title="✨ デイリー報酬 ✨", description="ボタンを押して報酬をゲット！", color=discord.Color.gold())
        if 画像: embed.set_image(url=画像.url)
        await interaction.response.send_message("設置完了", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)

    @app_commands.command(name="ショップ追加", description="Webサイト用販売ロールを登録します（管理者のみ）")
    @app_commands.default_permissions(administrator=True)
    async def add_shop(self, interaction: discord.Interaction, ロール: discord.Role, 価格: int, 説明: str):
        await interaction.response.defer(ephemeral=True)
        shop_data = self.load_shop()
        shop_data.append({"id": str(ロール.id), "name": ロール.name, "price": 価格, "desc": 説明})
        self.save_shop(shop_data); self.update_web_data()
        await interaction.followup.send(f"✅ 「{ロール.name}」を登録しました。", ephemeral=True)

    @app_commands.command(name="購入案内送信", description="手動でロール購入ボタンをDMします（管理者のみ）")
    @app_commands.default_permissions(administrator=True)
    async def send_shop_bill(self, interaction: discord.Interaction, 相手: discord.Member, ロールid: str):
        shop_data = self.load_shop()
        item = next((i for i in shop_data if i['id'] == ロールid), None)
        if not item: return
        view = ShopBillView(self, item['id'], item['price'], item['name'])
        embed = discord.Embed(title="🛒 購入手続き", description=f"商品: **{item['name']}**\n価格: **{item['price']}{self.currency}**", color=discord.Color.green())
        try:
            await 相手.send(embed=embed, view=view)
            await interaction.response.send_message(f"✅ {相手.display_name} さんに送信しました。", ephemeral=True)
        except: await interaction.response.send_message("❌ DM送信に失敗しました。", ephemeral=True)

    # --- 一般ユーザー向けコマンド ---

    @app_commands.command(name="所持金", description="所持金を確認します")
    async def wallet(self, interaction: discord.Interaction):
        data = self.load_data()
        money = data.get(str(interaction.user.id), {}).get('money', 0)
        await interaction.response.send_message(f'残高: **{money}{self.currency}**', ephemeral=True)

    @app_commands.command(name="働く", description="お金を稼ぎます")
    async def work(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = self.load_data()
        u_id = str(interaction.user.id)
        if u_id not in data: data[u_id] = self.get_default_user_data()
        earned = random.randint(10, 100)
        data[u_id]['money'] += earned
        self.save_data(data); self.update_web_data()
        await interaction.followup.send(f'**{earned}{self.currency}** 稼ぎました！', ephemeral=True)

    @app_commands.command(name="送金", description="相手にお金を送ります")
    async def send_money(self, interaction: discord.Interaction, 相手: discord.Member, 金額: int):
        await interaction.response.defer(ephemeral=True)
        data = self.load_data()
        sid, rid = str(interaction.user.id), str(相手.id)
        if 金額 <= 0 or sid == rid or data.get(sid, {}).get('money', 0) < 金額:
            await interaction.followup.send("無効な操作です。", ephemeral=True); return
        if rid not in data: data[rid] = self.get_default_user_data()
        data[sid]['money'] -= 金額
        data[rid]['money'] += 金額
        data[sid]['send_money_total'] = data[sid].get('send_money_total', 0) + 金額
        self.save_data(data); self.update_web_data()
        await interaction.followup.send(f"✅ {相手.display_name} へ送金しました。", ephemeral=True)

    @app_commands.command(name="請求書", description="相手にDMで請求書を送ります")
    async def bill(self, interaction: discord.Interaction, 相手: discord.Member, 金額: int):
        # 請求書は管理者以外も使う可能性があるためそのまま（必要なら permission を追加してください）
        if 金額 <= 0 or 相手.id == interaction.user.id: return
        view = BillView(self, 金額, interaction.user)
        embed = discord.Embed(title="📄 請求書", description=f"金額: {金額}{self.currency}\n請求者: {interaction.user.display_name}", color=discord.Color.red())
        try:
            await 相手.send(embed=embed, view=view)
            await interaction.response.send_message(f"✅ {相手.display_name} さんに送信しました。", ephemeral=True)
        except: await interaction.response.send_message("❌ DM送信に失敗しました。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Auth(bot))
    await bot.add_cog(Economy(bot))
