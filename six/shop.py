import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio

# ファイルパス
DATA_FILE = 'data.json'          # 所持金参照用
INVENTORY_FILE = 'inventory.json' # インベントリ保存用
SIX_SHOP_FILE = 'six_shop_items.json'
BLACKLIST_FILE = 'blacklist.json' # 抹消対象ID保存用

class ShopSix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.currency = "星"
        # 起動時にブラックリストを読み込む
        data = self.load_json(BLACKLIST_FILE)
        self.blacklist = data.get("ids", [])

    # --- 汎用データ操作 ---
    def load_json(self, filepath):
        if not os.path.exists(filepath): return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def save_json(self, filepath, data):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # --- 自動削除イベント (ブラックリストに入っているIDの発言を即消し) ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot and message.author.id == self.bot.user.id:
            return

        # 送信者がブラックリストに含まれている場合
        if message.author.id in self.blacklist:
            try:
                await message.delete()
            except:
                pass

    # --- 抹消コマンド (ID登録 + BAN + 過去ログ掃除) ---
    @app_commands.command(name="抹消", description="対象をブラックリストに入れ、BANとメッセージ削除を行います（管理者のみ）")
    @app_commands.describe(ターゲット="名前(サーバー内にいる場合)または18桁のID", 理由="BAN理由")
    @app_commands.default_permissions(administrator=True)
    async def eliminate(self, interaction: discord.Interaction, ターゲット: str, 理由: str = "スパム対策"):
        target_id = None

        if ターゲット.isdigit():
            target_id = int(ターゲット)
        else:
            member = discord.utils.get(interaction.guild.members, name=ターゲット) or discord.utils.get(interaction.guild.members, display_name=ターゲット)
            if member:
                target_id = member.id

        if not target_id:
            await interaction.response.send_message("❌ 対象が見つかりません。サーバーにいないアプリ等はIDを入力してください。", ephemeral=True)
            return

        if target_id == interaction.user.id:
            await interaction.response.send_message("自分自身を抹消することはできません。", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # ブラックリストに保存
        if target_id not in self.blacklist:
            self.blacklist.append(target_id)
            self.save_json(BLACKLIST_FILE, {"ids": self.blacklist})

        try:
            # BAN実行 (過去7日分のメッセージ削除依頼含む)
            await interaction.guild.ban(discord.Object(id=target_id), delete_message_seconds=604800, reason=理由)

            # チャンネル内のターゲットの投稿をピンポイント掃除
            def is_target(m): return m.author.id == target_id
            deleted = await interaction.channel.purge(limit=100, check=is_target)

            await interaction.followup.send(f"🔨 ID:`{target_id}` をブラックリストに登録し、抹消（BAN）しました。\n🧹 チャンネル内の既にある投稿 {len(deleted)} 件を削除しました。今後このIDの発言は自動削除されます。")
        except Exception as e:
            await interaction.followup.send(f"⚠️ ブラックリストには登録しました（発言は自動削除されます）が、BANには失敗しました。\nエラー: {e}")

    # --- 抹消解除コマンド ---
    @app_commands.command(name="抹消解除", description="指定したIDをブラックリストから削除します（管理者のみ）")
    @app_commands.default_permissions(administrator=True)
    async def unblacklist(self, interaction: discord.Interaction, ターゲットid: str):
        if not ターゲットid.isdigit():
            await interaction.response.send_message("数字のIDを入力してください。", ephemeral=True)
            return

        tid = int(ターゲットid)
        if tid in self.blacklist:
            self.blacklist.remove(tid)
            self.save_json(BLACKLIST_FILE, {"ids": self.blacklist})
            await interaction.response.send_message(f"✅ ID:`{tid}` をブラックリストから解除しました。")
        else:
            await interaction.response.send_message("そのIDは登録されていません。", ephemeral=True)

    # --- 商品追加コマンド ---
    @app_commands.command(name="商品追加", description="ショップに新しいアイテムを追加します（管理者のみ）")
    @app_commands.default_permissions(administrator=True)
    async def add_item(self, interaction: discord.Interaction, 名前: str, 値段: int):
        shop_items = self.load_json(SIX_SHOP_FILE)
        if not isinstance(shop_items, list): shop_items = []

        if any(item['name'] == 名前 for item in shop_items):
            await interaction.response.send_message(f"❌ 「{名前}」は既に登録されています。", ephemeral=True)
            return

        shop_items.append({"name": 名前, "price": 値段})
        self.save_json(SIX_SHOP_FILE, shop_items)
        await interaction.response.send_message(f"✅ 商品「{名前}」を {値段}{self.currency} で登録しました。", ephemeral=True)

    # --- ショップパネル追加コマンド ---
    @app_commands.command(name="ショップパネル追加", description="購入ボタン付きのショップパネルを設置します（管理者のみ）")
    @app_commands.default_permissions(administrator=True)
    async def setup_shop_panel(self, interaction: discord.Interaction):
        shop_items = self.load_json(SIX_SHOP_FILE)
        if not shop_items:
            await interaction.response.send_message("登録されている商品がありません。", ephemeral=True)
            return

        embed = discord.Embed(
            title="🛒 アイテムショップ", 
            description=f"下のボタンを押して商品リストを表示し、選択して購入してください。\n単位: **{self.currency}**", 
            color=discord.Color.blue()
        )

        item_list = "\n".join([f"・**{i['name']}** : {i['price']}{self.currency}" for i in shop_items])
        embed.add_field(name="ラインナップ", value=item_list)

        view = ShopLaunchView(self)
        await interaction.response.send_message("ショップパネルを設置しました。", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)

    # --- インベントリ確認コマンド ---
    @app_commands.command(name="インベントリ", description="自分の持ち物を確認します")
    async def inventory(self, interaction: discord.Interaction):
        inv_data = self.load_json(INVENTORY_FILE)
        uid = str(interaction.user.id)
        user_inv = inv_data.get(uid, [])

        if not user_inv:
            await interaction.response.send_message("インベントリは空です。", ephemeral=True)
            return

        item_counts = {}
        for item in user_inv:
            item_counts[item] = item_counts.get(item, 0) + 1

        item_list = "\n".join([f"・{name} x{count}" for name, count in item_counts.items()])
        embed = discord.Embed(title=f"🎒 あなたのインベントリ", description=item_list, color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- アイテム送信コマンド ---
    @app_commands.command(name="アイテム送信", description="インベントリ内のアイテムを他のユーザーに送ります")
    async def send_item(self, interaction: discord.Interaction, 相手: discord.Member, アイテム名: str):
        if 相手.bot:
            await interaction.response.send_message("Botにアイテムは送れません。", ephemeral=True)
            return

        inv_data = self.load_json(INVENTORY_FILE)
        sid, rid = str(interaction.user.id), str(相手.id)

        if sid not in inv_data or アイテム名 not in inv_data[sid]:
            await interaction.response.send_message(f"「{アイテム名}」を持っていません。", ephemeral=True)
            return

        inv_data[sid].remove(アイテム名)
        if rid not in inv_data: inv_data[rid] = []
        inv_data[rid].append(アイテム名)

        self.save_json(INVENTORY_FILE, inv_data)

        economy_cog = self.bot.get_cog('Economy')
        if economy_cog: economy_cog.update_web_data()

        await interaction.response.send_message(f"✅ {相手.mention} に「{アイテム名}」を送信しました！")

# --- ショップ起動ボタン ---
class ShopLaunchView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="商品一覧を開く", style=discord.ButtonStyle.primary, custom_id="six_shop_open")
    async def open_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        items = self.cog.load_json(SIX_SHOP_FILE)
        if not items:
            await interaction.response.send_message("現在、販売中の商品はありません。", ephemeral=True)
            return

        view = ShopDropdownView(self.cog, items)
        await interaction.response.send_message("購入したいアイテムを選択してください：", view=view, ephemeral=True)

# --- 商品選択ドロップダウン ---
class ShopDropdown(discord.ui.Select):
    def __init__(self, cog, items):
        self.cog = cog
        options = [
            discord.SelectOption(
                label=f"{item['name']}", 
                description=f"価格: {item['price']}{cog.currency}", 
                value=f"{item['name']}:{item['price']}"
            ) for item in items
        ]
        super().__init__(placeholder="アイテムを選んでください...", options=options)

    async def callback(self, interaction: discord.Interaction):
        item_name, price = self.values[0].split(":")
        price = int(price)
        uid = str(interaction.user.id)

        money_data = self.cog.load_json(DATA_FILE)
        user_money = money_data.get(uid, {}).get('money', 0)

        if user_money < price:
            await interaction.response.edit_message(content=f"❌ {self.cog.currency}が足りません！\n所持: {user_money}{self.cog.currency} / 価格: {price}{self.cog.currency}", view=None)
            return

        money_data[uid]['money'] -= price
        self.cog.save_json(DATA_FILE, money_data)

        inv_data = self.cog.load_json(INVENTORY_FILE)
        if uid not in inv_data: inv_data[uid] = []
        inv_data[uid].append(item_name)
        self.cog.save_json(INVENTORY_FILE, inv_data)

        economy_cog = self.cog.bot.get_cog('Economy')
        if economy_cog: economy_cog.update_web_data()

        await interaction.response.edit_message(content=f"🎉 「{item_name}」を購入しました！", view=None)

class ShopDropdownView(discord.ui.View):
    def __init__(self, cog, items):
        super().__init__(timeout=60)
        self.add_item(ShopDropdown(cog, items))

async def setup(bot):
    await bot.add_cog(ShopSix(bot))
