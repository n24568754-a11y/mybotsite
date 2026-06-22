import discord
from discord import app_commands
from discord.ext import commands
import json
import os

class CraftView(discord.ui.View):
    """クラフトメインビュー"""
    def __init__(self, cog, user_id):
        super().__init__(timeout=120)
        self.cog = cog
        self.user_id = user_id
    
    @discord.ui.button(label="⚔️ 武器クラフト", style=discord.ButtonStyle.primary, emoji="⚔️", row=0)
    async def weapons(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたの操作ではありません", ephemeral=True)
        await self.cog.show_recipes(interaction, "weapons")
    
    @discord.ui.button(label="🛡️ 防具クラフト", style=discord.ButtonStyle.primary, emoji="🛡️", row=0)
    async def armors(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたの操作ではありません", ephemeral=True)
        await self.cog.show_recipes(interaction, "armors")
    
    @discord.ui.button(label="🧪 アイテムクラフト", style=discord.ButtonStyle.success, emoji="🧪", row=0)
    async def items(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたの操作ではありません", ephemeral=True)
        await self.cog.show_recipes(interaction, "items")
    
    @discord.ui.button(label="📦 素材一覧", style=discord.ButtonStyle.secondary, emoji="📦", row=1)
    async def materials(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたの操作ではありません", ephemeral=True)
        await self.cog.show_materials(interaction)
    
    @discord.ui.button(label="🔍 レシピ検索", style=discord.ButtonStyle.secondary, emoji="🔍", row=1)
    async def search(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたの操作ではありません", ephemeral=True)
        await self.cog.search_recipe_modal(interaction)
    
    @discord.ui.button(label="🚪 閉じる", style=discord.ButtonStyle.danger, emoji="🚪", row=1)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="クラフトメニューを閉じました", embed=None, view=None)


class CraftConfirmView(discord.ui.View):
    """クラフト確認ビュー"""
    def __init__(self, cog, user_id, recipe_id, recipe_data, category):
        super().__init__(timeout=60)
        self.cog = cog
        self.user_id = user_id
        self.recipe_id = recipe_id
        self.recipe_data = recipe_data
        self.category = category
    
    @discord.ui.button(label="✅ クラフトする", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたの操作ではありません", ephemeral=True)
        await self.cog.process_craft(interaction, self.recipe_id, self.recipe_data, self.category)
    
    @discord.ui.button(label="❌ キャンセル", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="クラフトをキャンセルしました", embed=None, view=None)


class CraftSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recipes_path = "cogs/rpg/data/recipes.json"
        self.drop_items_path = "cogs/rpg/data/drop_items.json"
        self.load_data()
    
    def load_data(self):
        """データ読み込み"""
        if os.path.exists(self.recipes_path):
            with open(self.recipes_path, 'r', encoding='utf-8') as f:
                self.recipes = json.load(f)
        else:
            self.recipes = {"weapons": {}, "armors": {}, "items": {}}
        
        if os.path.exists(self.drop_items_path):
            with open(self.drop_items_path, 'r', encoding='utf-8') as f:
                self.drop_items = json.load(f)
        else:
            self.drop_items = {"materials": {}, "enemy_drops": {}}
    
    def load_players(self):
        players_path = "cogs/rpg/data/players.json"
        with open(players_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_players(self, data):
        players_path = "cogs/rpg/data/players.json"
        with open(players_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_materials(self, user_id):
        """プレイヤーの素材を取得"""
        players = self.load_players()
        uid = str(user_id)
        if uid not in players:
            return {}
        return players[uid].get("materials", {})
    
    def add_material(self, user_id, material_id, quantity):
        """素材を追加"""
        players = self.load_players()
        uid = str(user_id)
        if uid not in players:
            players[uid] = {"materials": {}}
        
        if "materials" not in players[uid]:
            players[uid]["materials"] = {}
        
        current = players[uid]["materials"].get(material_id, 0)
        players[uid]["materials"][material_id] = current + quantity
        self.save_players(players)
        return True
    
    def remove_materials(self, user_id, materials):
        """素材を消費"""
        players = self.load_players()
        uid = str(user_id)
        if uid not in players or "materials" not in players[uid]:
            return False
        
        for mat_id, quantity in materials.items():
            current = players[uid]["materials"].get(mat_id, 0)
            if current < quantity:
                return False
            players[uid]["materials"][mat_id] = current - quantity
            if players[uid]["materials"][mat_id] <= 0:
                del players[uid]["materials"][mat_id]
        
        self.save_players(players)
        return True
    
    def check_materials(self, user_id, required_materials):
        """素材が足りるかチェック"""
        materials = self.get_materials(user_id)
        for req in required_materials:
            current = materials.get(req["item"], 0)
            if current < req["quantity"]:
                return False, req["item"], req["quantity"] - current
        return True, None, 0
    
    def get_equipment_cog(self):
        """装備Cogを取得"""
        return self.bot.get_cog("EquipmentSystem")
    
    async def show_materials(self, interaction: discord.Interaction):
        """素材一覧を表示"""
        materials = self.get_materials(interaction.user.id)
        if not materials:
            await interaction.response.send_message("📦 素材を持っていません", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📦 所持素材一覧",
            color=discord.Color.blue()
        )
        
        material_data = self.drop_items.get("materials", {})
        
        # ランクごとにソート
        def get_rank_order(item):
            rank = material_data.get(item[0], {}).get("rank", "C")
            return {"S": 1, "A": 2, "B": 3, "C": 4}.get(rank, 5)
        
        sorted_materials = sorted(materials.items(), key=get_rank_order)
        
        for mat_id, count in sorted_materials:
            mat = material_data.get(mat_id, {})
            rank_emoji = {"S": "🟧", "A": "🟣", "B": "🔵", "C": "🟢"}.get(mat.get("rank", "C"), "⚪")
            embed.add_field(
                name=f"{rank_emoji} {mat.get('name', mat_id)}",
                value=f"個数: {count}\n{mat.get('description', '')[:40]}",
                inline=True
            )
        
        embed.set_footer(text="素材を集めて装備を作ろう！")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def show_recipes(self, interaction: discord.Interaction, category: str):
        """レシピ一覧を表示"""
        recipes = self.recipes.get(category, {})
        if not recipes:
            await interaction.response.send_message(f"❌ {category}のレシピがありません", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"🔨 {self.get_category_name(category)} クラフト",
            color=discord.Color.gold()
        )
        
        material_data = self.drop_items.get("materials", {})
        
        for recipe_id, recipe in recipes.items():
            # 必要素材の表示
            materials_text = ""
            for mat in recipe.get("materials", []):
                mat_info = material_data.get(mat["item"], {})
                mat_name = mat_info.get("name", mat["item"])
                rank_emoji = {"S": "🟧", "A": "🟣", "B": "🔵", "C": "🟢"}.get(mat_info.get("rank", "C"), "⚪")
                materials_text += f"{rank_emoji} {mat_name} ×{mat['quantity']}\n"
            
            # ステータス表示
            stats_text = ""
            for stat, value in recipe.get("stats", {}).items():
                stat_name = {"atk": "⚔️攻撃", "def": "🛡️防御", "mag": "🔮魔法", "agi": "💨素早さ", "hp": "❤️HP", "mp": "✨MP"}
                stats_text += f"{stat_name.get(stat, stat)} +{value} "
            
            element_text = f" 🔥[{recipe['element']}]" if recipe.get("element") else ""
            resist_text = f" 🛡️耐性:{recipe['element_resist']}" if recipe.get("element_resist") else ""
            
            embed.add_field(
                name=f"{recipe['emoji']} {recipe['name']}{element_text}{resist_text} (Lv.{recipe['required_level']})",
                value=f"📝 {recipe['description']}\n📊 {stats_text}\n📦 必要素材:\n{materials_text}`/rpg_craft {recipe_id}` で作成",
                inline=False
            )
        
        view = CraftView(self, interaction.user.id)
        await interaction.response.edit_message(embed=embed, view=view)
    
    def get_category_name(self, category: str) -> str:
        return {"weapons": "武器", "armors": "防具", "items": "アイテム"}.get(category, category)
    
    async def search_recipe_modal(self, interaction: discord.Interaction):
        """レシピ検索モーダル"""
        modal = RecipeSearchModal(self)
        await interaction.response.send_modal(modal)
    
    async def process_craft(self, interaction: discord.Interaction, recipe_id: str, recipe_data: dict, category: str):
        """クラフト処理"""
        await interaction.response.defer(ephemeral=True)
        
        # レベルチェック
        players = self.load_players()
        uid = str(interaction.user.id)
        player_level = players.get(uid, {}).get("level", 1)
        
        if player_level < recipe_data.get("required_level", 1):
            await interaction.followup.send(f"❌ レベル{recipe_data['required_level']}以上が必要です", ephemeral=True)
            return
        
        # 素材チェック
        required_materials = {}
        for mat in recipe_data.get("materials", []):
            required_materials[mat["item"]] = mat["quantity"]
        
        has_materials, missing_item, missing_amount = self.check_materials(
            interaction.user.id,
            recipe_data.get("materials", [])
        )
        
        if not has_materials:
            material_data = self.drop_items.get("materials", {})
            missing_name = material_data.get(missing_item, {}).get("name", missing_item)
            await interaction.followup.send(f"❌ 素材が足りません！\n不足: {missing_name} ×{missing_amount}", ephemeral=True)
            return
        
        # 素材消費
        self.remove_materials(interaction.user.id, required_materials)
        
        # アイテム追加（インベントリと装備両方に追加）
        equipment_cog = self.get_equipment_cog()
        print(f"🔍 [DEBUG] equipment_cog = {equipment_cog}")
        print(f"🔍 [DEBUG] recipe_id = {recipe_id}")
        
        if equipment_cog:
            # インベントリに追加
            result = equipment_cog.add_equipment_to_inventory(interaction.user.id, recipe_id)
            print(f"🔍 [DEBUG] add_equipment_to_inventory 結果 = {result}")
            
            # 装備データとしても追加（必要に応じて）
            if result:
                # クラフト履歴に追加
                if "crafted_items" not in players[uid]:
                    players[uid]["crafted_items"] = []
                if recipe_id not in players[uid]["crafted_items"]:
                    players[uid]["crafted_items"].append(recipe_id)
                
                # 念のため inventory.equipment にも追加（重複チェック）
                if "inventory" not in players[uid]:
                    players[uid]["inventory"] = {"items": {}, "equipment": []}
                if recipe_id not in players[uid]["inventory"]["equipment"]:
                    players[uid]["inventory"]["equipment"].append(recipe_id)
                    print(f"🔍 [DEBUG] inventory.equipment に直接追加: {recipe_id}")
                
                self.save_players(players)
                
                embed = discord.Embed(
                    title="✅ クラフト成功！",
                    description=f"**{recipe_data['name']}** を作成しました！\n\n📦 使用した素材:\n" + "\n".join([f"• {self.drop_items['materials'].get(m, {}).get('name', m)} ×{q}" for m, q in required_materials.items()]),
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send("❌ アイテムの追加に失敗しました（インベントリ問題）", ephemeral=True)
        else:
            await interaction.followup.send("❌ 装備システムが見つかりません", ephemeral=True)
    
    @app_commands.command(name="rpg_craft", description="クラフトメニューを開く")
    async def craft(self, interaction: discord.Interaction, recipe_id: str = None):
        """クラフトメニューを開く"""
        if recipe_id:
            # 直接レシピID指定でクラフト
            await self.craft_by_id(interaction, recipe_id)
            return
        
        embed = discord.Embed(
            title="🔨 クラフトメニュー",
            description="作成したいカテゴリを選んでください",
            color=discord.Color.gold()
        )
        embed.add_field(name="⚔️ 武器クラフト", value="武器を作成します", inline=True)
        embed.add_field(name="🛡️ 防具クラフト", value="防具を作成します", inline=True)
        embed.add_field(name="🧪 アイテムクラフト", value="アイテムを作成します", inline=True)
        embed.add_field(name="📦 素材一覧", value="所持素材を確認します", inline=True)
        
        view = CraftView(self, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def craft_by_id(self, interaction: discord.Interaction, recipe_id: str):
        """レシピID指定でクラフト"""
        for category in ["weapons", "armors", "items"]:
            if recipe_id in self.recipes.get(category, {}):
                recipe = self.recipes[category][recipe_id]
                
                # 必要素材の表示
                material_data = self.drop_items.get("materials", {})
                materials_text = ""
                for mat in recipe.get("materials", []):
                    mat_info = material_data.get(mat["item"], {})
                    mat_name = mat_info.get("name", mat["item"])
                    materials_text += f"• {mat_name} ×{mat['quantity']}\n"
                
                # ステータス表示
                stats_text = ""
                for stat, value in recipe.get("stats", {}).items():
                    stat_name = {"atk": "⚔️攻撃力", "def": "🛡️防御力", "mag": "🔮魔法力", "agi": "💨素早さ", "hp": "❤️HP", "mp": "✨MP"}
                    stats_text += f"{stat_name.get(stat, stat)} +{value}\n"
                
                embed = discord.Embed(
                    title=f"🔨 {recipe['name']} をクラフト",
                    description=f"📝 {recipe['description']}\n\n📊 {stats_text}\n\n📦 必要素材:\n{materials_text}\n🔰 必要レベル: Lv.{recipe.get('required_level', 1)}",
                    color=discord.Color.blue()
                )
                
                view = CraftConfirmView(self, interaction.user.id, recipe_id, recipe, category)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                return
        
        await interaction.response.send_message(f"❌ レシピ `{recipe_id}` が見つかりません", ephemeral=True)
    
    @app_commands.command(name="rpg_materials", description="所持素材を確認")
    async def materials(self, interaction: discord.Interaction):
        """所持素材一覧"""
        await self.show_materials(interaction)
    
    @app_commands.command(name="rpg_recipes", description="レシピ一覧を表示")
    async def recipes(self, interaction: discord.Interaction, category: str = None):
        """レシピ一覧"""
        if not category:
            embed = discord.Embed(
                title="📖 レシピ一覧",
                description="表示したいカテゴリを選択してください",
                color=discord.Color.gold()
            )
            embed.add_field(name="⚔️ weapons", value="武器レシピ", inline=True)
            embed.add_field(name="🛡️ armors", value="防具レシピ", inline=True)
            embed.add_field(name="🧪 items", value="アイテムレシピ", inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if category not in ["weapons", "armors", "items"]:
            await interaction.response.send_message("❌ カテゴリは weapons, armors, items から選んでください", ephemeral=True)
            return
        
        await self.show_recipes(interaction, category)


class RecipeSearchModal(discord.ui.Modal, title="レシピ検索"):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
        
        self.recipe_name = discord.ui.TextInput(
            label="レシピ名",
            placeholder="検索するレシピ名を入力",
            required=True,
            max_length=50
        )
        self.add_item(self.recipe_name)
    
    async def on_submit(self, interaction: discord.Interaction):
        search_term = self.recipe_name.value.lower()
        results = []
        
        for category in ["weapons", "armors", "items"]:
            for recipe_id, recipe in self.cog.recipes.get(category, {}).items():
                if search_term in recipe["name"].lower() or search_term in recipe_id.lower():
                    results.append((category, recipe_id, recipe))
        
        if not results:
            await interaction.response.send_message(f"❌ 「{self.recipe_name.value}」が見つかりませんでした", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"🔍 検索結果: {self.recipe_name.value}",
            color=discord.Color.gold()
        )
        
        material_data = self.cog.drop_items.get("materials", {})
        
        for category, recipe_id, recipe in results[:10]:  # 最大10件
            materials_text = ""
            for mat in recipe.get("materials", []):
                mat_info = material_data.get(mat["item"], {})
                mat_name = mat_info.get("name", mat["item"])
                materials_text += f"• {mat_name} ×{mat['quantity']}\n"
            
            embed.add_field(
                name=f"{recipe['emoji']} {recipe['name']} ({category})",
                value=f"📦 {materials_text}`/rpg_craft {recipe_id}` で作成",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(CraftSystem(bot))