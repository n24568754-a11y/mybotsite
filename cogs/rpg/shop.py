import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from firebase_admin import db

class ShopView(discord.ui.View):
    """ショップメインビュー"""
    def __init__(self, cog, user_id):
        super().__init__(timeout=120)
        self.cog = cog
        self.user_id = user_id
    
    @discord.ui.button(label="⚔️ 武器", style=discord.ButtonStyle.primary, emoji="⚔️", row=0)
    async def weapons(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたの操作ではありません", ephemeral=True)
        await self.cog.show_category(interaction, "weapons")
    
    @discord.ui.button(label="🛡️ 防具", style=discord.ButtonStyle.primary, emoji="🛡️", row=0)
    async def armors(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたの操作ではありません", ephemeral=True)
        await self.cog.show_category(interaction, "armors")
    
    @discord.ui.button(label="💍 アクセサリー", style=discord.ButtonStyle.primary, emoji="💍", row=0)
    async def accessories(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたの操作ではありません", ephemeral=True)
        await self.cog.show_category(interaction, "accessories")
    
    @discord.ui.button(label="🧪 アイテム", style=discord.ButtonStyle.success, emoji="🧪", row=1)
    async def items(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたの操作ではありません", ephemeral=True)
        await self.cog.show_category(interaction, "items")
    
    @discord.ui.button(label="📊 残高確認", style=discord.ButtonStyle.secondary, emoji="📊", row=1)
    async def balance(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたの操作ではありません", ephemeral=True)
        await self.cog.show_balance(interaction)
    
    @discord.ui.button(label="🚪 閉じる", style=discord.ButtonStyle.danger, emoji="🚪", row=1)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="ショップを閉じました", embed=None, view=None)


class ConfirmBuyView(discord.ui.View):
    """購入確認ビュー"""
    def __init__(self, cog, user_id, item_id, item_data, price):
        super().__init__(timeout=60)
        self.cog = cog
        self.user_id = user_id
        self.item_id = item_id
        self.item_data = item_data
        self.price = price
    
    @discord.ui.button(label="✅ 購入する", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたの操作ではありません", ephemeral=True)
        await self.cog.process_purchase(interaction, self.item_id, self.item_data, self.price)
    
    @discord.ui.button(label="❌ キャンセル", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="購入をキャンセルしました", embed=None, view=None)


class ShopSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.shop_path = "cogs/rpg/data/shop.json"
        self.load_shop_data()
    
    def load_shop_data(self):
        """ショップデータを読み込み"""
        if os.path.exists(self.shop_path):
            with open(self.shop_path, 'r', encoding='utf-8') as f:
                self.shop_data = json.load(f)
        else:
            self.shop_data = self.create_default_shop()
            # デフォルトデータを保存
            with open(self.shop_path, 'w', encoding='utf-8') as f:
                json.dump(self.shop_data, f, indent=2, ensure_ascii=False)
    
    def create_default_shop(self):
        """デフォルトのショップデータを作成"""
        return {
            "categories": {
                "weapons": {
                    "name": "⚔️ 武器",
                    "emoji": "⚔️",
                    "items": ["bronze_sword", "iron_sword", "flame_sword", "ice_dagger", "thunder_hammer"]
                },
                "armors": {
                    "name": "🛡️ 防具",
                    "emoji": "🛡️",
                    "items": ["leather_armor", "iron_armor", "flame_robe"]
                },
                "accessories": {
                    "name": "💍 アクセサリー",
                    "emoji": "💍",
                    "items": ["power_ring", "magic_ring", "life_necklace"]
                },
                "items": {
                    "name": "🧪 アイテム",
                    "emoji": "🧪",
                    "items": ["potion", "antidote"]
                }
            },
            "shop_npc": {
                "name": "カリーナ",
                "icon": "🛒",
                "greeting": "いらっしゃい！何かお探し？",
                "farewell": "また来てね！"
            }
        }
    
    def get_economy_cog(self):
        """エコノミーCogを取得"""
        return self.bot.get_cog("Economy")
    
    def get_equipment_cog(self):
        """装備Cogを取得"""
        return self.bot.get_cog("EquipmentSystem")
    
    def get_player_money_from_firebase(self, user_id):
        """Firebaseからプレイヤーの所持金を直接取得"""
        try:
            # FirebaseからUSER_PROFILESを取得
            ref = db.reference('USER_PROFILES')
            profiles = ref.get()
            
            if not profiles:
                return 0
            
            # auth_data.json からパスワードを取得
            auth_path = "user_auth.json"
            if os.path.exists(auth_path):
                with open(auth_path, 'r', encoding='utf-8') as f:
                    auth_data = json.load(f)
                
                uid = str(user_id)
                password = auth_data.get(uid)
                
                if password and password in profiles:
                    return profiles[password].get('money', 0)
            
            return 0
        except Exception as e:
            print(f"Firebase読み込みエラー: {e}")
            return 0
    
    def get_currency_from_firebase(self):
        """Firebaseから通貨単位を取得"""
        try:
            ref = db.reference('CURRENCY_NAME')
            currency = ref.get()
            return currency if currency else "星"
        except:
            return "星"
    
    def get_player_money(self, user_id):
        """プレイヤーの所持金を取得（Firebase優先）"""
        # まずFirebaseから取得
        money = self.get_player_money_from_firebase(user_id)
        if money > 0:
            return money
        
        # 次にエコノミーCogを試す
        economy = self.get_economy_cog()
        if economy:
            data = economy.load_data()
            uid = str(user_id)
            return data.get(uid, {}).get('money', 0)
        
        return 0
    
    def get_currency(self):
        """通貨単位を取得"""
        currency = self.get_currency_from_firebase()
        if currency:
            return currency
        
        economy = self.get_economy_cog()
        if economy:
            return economy.currency
        
        return "星"
    
    def add_money(self, user_id, amount):
        """プレイヤーにお金を追加"""
        economy = self.get_economy_cog()
        if economy:
            data = economy.load_data()
            uid = str(user_id)
            if uid not in data:
                data[uid] = economy.get_default_user_data()
            data[uid]['money'] += amount
            economy.save_data(data)
            economy.update_web_data()
            return True
        return False
    
    def remove_money(self, user_id, amount):
        """プレイヤーからお金を減らす"""
        if self.get_player_money(user_id) >= amount:
            economy = self.get_economy_cog()
            if economy:
                data = economy.load_data()
                uid = str(user_id)
                data[uid]['money'] -= amount
                economy.save_data(data)
                economy.update_web_data()
                return True
        return False
    
    async def show_balance(self, interaction: discord.Interaction):
        """残高表示"""
        money = self.get_player_money(interaction.user.id)
        currency = self.get_currency()
        
        embed = discord.Embed(
            title="💰 残高確認",
            description=f"あなたの所持金: **{money}{currency}**",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def show_category(self, interaction: discord.Interaction, category_key: str):
        """カテゴリ内の商品を表示"""
        category = self.shop_data["categories"].get(category_key)
        if not category:
            return
        
        equipment_cog = self.get_equipment_cog()
        if not equipment_cog:
            await interaction.response.send_message("❌ 装備システムが読み込まれていません", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"{category['emoji']} {category['name']} ショップ",
            description=f"{self.shop_data['shop_npc']['greeting']}",
            color=discord.Color.blue()
        )
        
        # 商品リストを作成
        items_text = ""
        for item_id in category["items"]:
            item = equipment_cog.get_equipment_by_id(item_id)
            if item:
                price = item.get("value", 0)
                items_text += f"**{item['emoji']} {item['name']}**\n"
                items_text += f"   📝 {item['description']}\n"
                items_text += f"   💰 {price}{self.get_currency()} | Lv.{item['required_level']}\n"
                items_text += f"   `/rpg_buy {item_id}` で購入\n\n"
        
        if items_text:
            embed.description = items_text
        else:
            embed.description = "このカテゴリには商品がありません"
        
        embed.set_footer(text=f"{self.shop_data['shop_npc']['name']} 🛒")
        
        view = ShopView(self, interaction.user.id)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def process_purchase(self, interaction: discord.Interaction, item_id: str, item_data: dict, price: int):
        """購入処理"""
        await interaction.response.defer(ephemeral=True)
        
        # 所持金チェック
        if self.get_player_money(interaction.user.id) < price:
            await interaction.followup.send(f"❌ 所持金が足りません！ (必要: {price}{self.get_currency()})", ephemeral=True)
            return
        
        equipment_cog = self.get_equipment_cog()
        if not equipment_cog:
            await interaction.followup.send("❌ 装備システムが読み込まれていません", ephemeral=True)
            return
        
        # インベントリに追加
        if equipment_cog.add_equipment_to_inventory(interaction.user.id, item_id):
            # お金を減らす
            self.remove_money(interaction.user.id, price)
            
            embed = discord.Embed(
                title="✅ 購入完了！",
                description=f"**{item_data['name']}** を購入しました！\n"
                           f"💰 支払い: {price}{self.get_currency()}\n"
                           f"💼 所持金残高: {self.get_player_money(interaction.user.id)}{self.get_currency()}",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(f"❌ アイテムの追加に失敗しました", ephemeral=True)
    
    @app_commands.command(name="rpg_shop", description="ショップを開く")
    async def shop(self, interaction: discord.Interaction):
        """ショップを開く"""
        equipment_cog = self.get_equipment_cog()
        if not equipment_cog:
            return await interaction.response.send_message("❌ 装備システムが読み込まれていません", ephemeral=True)
        
        # メインのショップ画面
        embed = discord.Embed(
            title="🛒 RPGショップ",
            description=f"{self.shop_data['shop_npc']['greeting']}\n\n"
                       f"カテゴリを選んでください:",
            color=discord.Color.gold()
        )
        
        # カテゴリ一覧
        for key, cat in self.shop_data["categories"].items():
            embed.add_field(
                name=f"{cat['emoji']} {cat['name']}",
                value=f"{len(cat['items'])}種類の商品",
                inline=True
            )
        
        embed.add_field(
            name="💰 残高",
            value=f"{self.get_player_money(interaction.user.id)}{self.get_currency()}",
            inline=False
        )
        
        embed.set_footer(text=f"店主: {self.shop_data['shop_npc']['name']}")
        
        view = ShopView(self, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="rpg_buy", description="アイテムを購入する（ID指定）")
    async def buy(self, interaction: discord.Interaction, item_id: str, quantity: int = 1):
        """アイテムを購入"""
        await interaction.response.defer(ephemeral=True)
        
        equipment_cog = self.get_equipment_cog()
        if not equipment_cog:
            await interaction.followup.send("❌ 装備システムが読み込まれていません", ephemeral=True)
            return
        
        item = equipment_cog.get_equipment_by_id(item_id)
        if not item:
            await interaction.followup.send(f"❌ アイテム `{item_id}` が見つかりません", ephemeral=True)
            return
        
        price = item.get("value", 0) * quantity
        total_price = price
        
        if self.get_player_money(interaction.user.id) < total_price:
            await interaction.followup.send(f"❌ 所持金が足りません！ (必要: {total_price}{self.get_currency()})", ephemeral=True)
            return
        
        # 購入確認
        embed = discord.Embed(
            title="🛒 購入確認",
            description=f"**{item['name']}** を **{quantity}個** 購入しますか？\n"
                       f"💰 合計金額: **{total_price}{self.get_currency()}**\n"
                       f"📦 現在の所持金: **{self.get_player_money(interaction.user.id)}{self.get_currency()}**",
            color=discord.Color.blue()
        )
        
        view = ConfirmBuyView(self, interaction.user.id, item_id, item, total_price)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ShopSystem(bot))