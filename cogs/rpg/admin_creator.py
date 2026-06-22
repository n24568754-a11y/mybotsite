import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import uuid

# ==================== カテゴリ選択 ====================
class CategorySelect(discord.ui.Select):
    def __init__(self, cog, modal_data):
        options = [
            discord.SelectOption(label="⚔️ 武器", value="weapon", emoji="⚔️", description="攻撃用装備"),
            discord.SelectOption(label="🛡️ 防具", value="armor", emoji="🛡️", description="防御用装備"),
            discord.SelectOption(label="💍 アクセサリー", value="accessory", emoji="💍", description="特殊効果付与"),
        ]
        super().__init__(placeholder="装備のカテゴリを選択", options=options, row=0)
        self.cog = cog
        self.modal_data = modal_data

    async def callback(self, interaction: discord.Interaction):
        self.modal_data["category"] = self.values[0]
        if self.values[0] == "weapon":
            view = WeaponTypeSelectView(self.cog, self.modal_data)
        elif self.values[0] == "armor":
            view = ArmorTypeSelectView(self.cog, self.modal_data)
        else:
            view = AccessoryTypeSelectView(self.cog, self.modal_data)
        await interaction.response.edit_message(view=view)


class CategorySelectView(discord.ui.View):
    def __init__(self, cog, modal_data):
        super().__init__(timeout=120)
        self.add_item(CategorySelect(cog, modal_data))


# ==================== 武器タイプ選択 ====================
class WeaponTypeSelect(discord.ui.Select):
    def __init__(self, cog, modal_data):
        options = [
            discord.SelectOption(label="剣", value="sword", emoji="⚔️", description="バランスの良い武器"),
            discord.SelectOption(label="大剣", value="greatsword", emoji="🗡️", description="高攻撃力・低素早さ"),
            discord.SelectOption(label="短剣", value="dagger", emoji="🔪", description="低攻撃力・高素早さ"),
            discord.SelectOption(label="弓", value="bow", emoji="🏹", description="命中率ボーナス"),
            discord.SelectOption(label="杖", value="staff", emoji="🔮", description="魔法力ボーナス"),
            discord.SelectOption(label="斧", value="axe", emoji="🪓", description="高会心率"),
            discord.SelectOption(label="槍", value="spear", emoji="🔱", description="防御無視"),
        ]
        super().__init__(placeholder="武器の種類を選択", options=options, row=0)
        self.cog = cog
        self.modal_data = modal_data

    async def callback(self, interaction: discord.Interaction):
        self.modal_data["item_type"] = self.values[0]
        view = ElementSelectView(self.cog, self.modal_data)
        await interaction.response.edit_message(view=view)


class WeaponTypeSelectView(discord.ui.View):
    def __init__(self, cog, modal_data):
        super().__init__(timeout=120)
        self.add_item(WeaponTypeSelect(cog, modal_data))


# ==================== 防具タイプ選択 ====================
class ArmorTypeSelect(discord.ui.Select):
    def __init__(self, cog, modal_data):
        options = [
            discord.SelectOption(label="兜", value="helmet", emoji="⛑️", description="頭防具"),
            discord.SelectOption(label="鎧", value="armor", emoji="🛡️", description="胴防具"),
            discord.SelectOption(label="小手", value="gauntlet", emoji="🧤", description="腕防具"),
            discord.SelectOption(label="脚甲", value="greaves", emoji="👖", description="脚防具"),
            discord.SelectOption(label="靴", value="boots", emoji="👢", description="足防具"),
            discord.SelectOption(label="盾", value="shield", emoji="🛡️", description="盾"),
        ]
        super().__init__(placeholder="防具の種類を選択", options=options, row=0)
        self.cog = cog
        self.modal_data = modal_data

    async def callback(self, interaction: discord.Interaction):
        self.modal_data["item_type"] = self.values[0]
        view = ElementSelectView(self.cog, self.modal_data)
        await interaction.response.edit_message(view=view)


class ArmorTypeSelectView(discord.ui.View):
    def __init__(self, cog, modal_data):
        super().__init__(timeout=120)
        self.add_item(ArmorTypeSelect(cog, modal_data))


# ==================== アクセサリータイプ選択 ====================
class AccessoryTypeSelect(discord.ui.Select):
    def __init__(self, cog, modal_data):
        options = [
            discord.SelectOption(label="指輪", value="ring", emoji="💍", description="ステータス上昇"),
            discord.SelectOption(label="ネックレス", value="necklace", emoji="📿", description="耐性付与"),
            discord.SelectOption(label="耳飾り", value="earring", emoji="💎", description="特殊効果"),
            discord.SelectOption(label="腕輪", value="bracelet", emoji="🔗", description="補助効果"),
        ]
        super().__init__(placeholder="アクセサリーの種類を選択", options=options, row=0)
        self.cog = cog
        self.modal_data = modal_data

    async def callback(self, interaction: discord.Interaction):
        self.modal_data["item_type"] = self.values[0]
        view = ElementSelectView(self.cog, self.modal_data)
        await interaction.response.edit_message(view=view)


class AccessoryTypeSelectView(discord.ui.View):
    def __init__(self, cog, modal_data):
        super().__init__(timeout=120)
        self.add_item(AccessoryTypeSelect(cog, modal_data))


# ==================== 属性選択 ====================
class ElementSelect(discord.ui.Select):
    def __init__(self, cog, modal_data):
        options = [
            discord.SelectOption(label="なし", value="none", emoji="⚪", description="属性なし"),
            discord.SelectOption(label="火", value="fire", emoji="🔥", description="炎属性"),
            discord.SelectOption(label="水", value="water", emoji="💧", description="水属性"),
            discord.SelectOption(label="氷", value="ice", emoji="❄️", description="氷属性"),
            discord.SelectOption(label="雷", value="thunder", emoji="⚡", description="雷属性"),
            discord.SelectOption(label="風", value="wind", emoji="🌪️", description="風属性"),
            discord.SelectOption(label="土", value="earth", emoji="🪨", description="土属性"),
            discord.SelectOption(label="光", value="light", emoji="✨", description="光属性"),
            discord.SelectOption(label="闇", value="dark", emoji="🌑", description="闇属性"),
        ]
        super().__init__(placeholder="属性を選択", options=options, row=0)
        self.cog = cog
        self.modal_data = modal_data

    async def callback(self, interaction: discord.Interaction):
        self.modal_data["element"] = None if self.values[0] == "none" else self.values[0]
        view = BasicSettingsView(self.cog, self.modal_data)
        await interaction.response.edit_message(view=view)


class ElementSelectView(discord.ui.View):
    def __init__(self, cog, modal_data):
        super().__init__(timeout=120)
        self.add_item(ElementSelect(cog, modal_data))


# ==================== 基本設定（レベル・レアリティ・価格） ====================
class BasicSettingsView(discord.ui.View):
    def __init__(self, cog, modal_data):
        super().__init__(timeout=120)
        self.cog = cog
        self.modal_data = modal_data

        # レベル設定ボタン
        level_btn = discord.ui.Button(label="📊 必要レベル", style=discord.ButtonStyle.secondary, row=0)
        level_btn.callback = self.set_level
        self.add_item(level_btn)

        # レアリティ選択（row=1 に移動）
        rarity_select = discord.ui.Select(
            placeholder="レアリティを選択",
            options=[
                discord.SelectOption(label="⬜ コモン", value="common", emoji="⬜", description="基本装備"),
                discord.SelectOption(label="🟩 アンコモン", value="uncommon", emoji="🟩", description="少しレア"),
                discord.SelectOption(label="🟦 レア", value="rare", emoji="🟦", description="レア装備"),
                discord.SelectOption(label="🟪 エピック", value="epic", emoji="🟪", description="非常にレア"),
                discord.SelectOption(label="🟧 レジェンド", value="legendary", emoji="🟧", description="伝説級"),
            ],
            row=1
        )
        rarity_select.callback = self.set_rarity
        self.add_item(rarity_select)

        # 価格設定ボタン（row=2）
        price_btn = discord.ui.Button(label="💰 価格設定", style=discord.ButtonStyle.secondary, row=2)
        price_btn.callback = self.set_price
        self.add_item(price_btn)

        # 次へボタン（row=3）
        next_btn = discord.ui.Button(label="✅ 次へ", style=discord.ButtonStyle.success, row=3)
        next_btn.callback = self.next_step
        self.add_item(next_btn)

    async def set_level(self, interaction: discord.Interaction):
        modal = LevelInputModal(self.cog, self.modal_data)
        await interaction.response.send_modal(modal)

    async def set_rarity(self, interaction: discord.Interaction):
        self.modal_data["rarity"] = interaction.data["values"][0]
        await interaction.response.edit_message(view=self)

    async def set_price(self, interaction: discord.Interaction):
        modal = PriceInputModal(self.cog, self.modal_data)
        await interaction.response.send_modal(modal)

    async def next_step(self, interaction: discord.Interaction):
        # デフォルト値設定
        if "required_level" not in self.modal_data:
            self.modal_data["required_level"] = 1
        if "rarity" not in self.modal_data:
            self.modal_data["rarity"] = "common"
        if "price" not in self.modal_data:
            self.modal_data["price"] = 100

        view = StatsSelectView(self.cog, self.modal_data)
        await interaction.response.edit_message(view=view)


class LevelInputModal(discord.ui.Modal, title="必要レベル設定"):
    def __init__(self, cog, modal_data):
        super().__init__()
        self.cog = cog
        self.modal_data = modal_data

        self.level_input = discord.ui.TextInput(
            label="必要レベル (1-99)",
            placeholder="例: 10",
            required=True,
            max_length=2
        )
        self.add_item(self.level_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            level = int(self.level_input.value)
            self.modal_data["required_level"] = level
            await interaction.response.edit_message(view=BasicSettingsView(self.cog, self.modal_data))
        except ValueError:
            await interaction.response.send_message("❌ 数字を入力してください", ephemeral=True)


class PriceInputModal(discord.ui.Modal, title="価格設定"):
    def __init__(self, cog, modal_data):
        super().__init__()
        self.cog = cog
        self.modal_data = modal_data

        self.price_input = discord.ui.TextInput(
            label="ショップでの販売価格",
            placeholder="例: 500",
            required=True,
            max_length=6
        )
        self.add_item(self.price_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            price = int(self.price_input.value)
            self.modal_data["price"] = price
            await interaction.response.edit_message(view=BasicSettingsView(self.cog, self.modal_data))
        except ValueError:
            await interaction.response.send_message("❌ 数字を入力してください", ephemeral=True)


# ==================== ステータス選択 ====================
class StatsSelectView(discord.ui.View):
    def __init__(self, cog, modal_data):
        super().__init__(timeout=120)
        self.cog = cog
        self.modal_data = modal_data
        if "stats" not in self.modal_data:
            self.modal_data["stats"] = {"atk": 0, "def": 0, "mag": 0, "agi": 0, "hp": 0, "mp": 0}
        self.add_stat_buttons()

    def add_stat_buttons(self):
        self.clear_items()
        
        stats = [
            ("⚔️ 攻撃力", "atk"),
            ("🛡️ 防御力", "def"),
            ("🔮 魔法力", "mag"),
            ("💨 素早さ", "agi"),
            ("❤️ HP", "hp"),
            ("✨ MP", "mp"),
        ]
        
        current_stats = self.modal_data["stats"]
        
        for i, (name, key) in enumerate(stats):
            current_value = current_stats.get(key, 0)
            button = discord.ui.Button(
                label=f"{name}: +{current_value}", 
                style=discord.ButtonStyle.secondary, 
                row=i // 3
            )
            async def button_callback(interaction: discord.Interaction, k=key, n=name):
                await self.open_stat_modal(interaction, k, n)
            button.callback = button_callback
            self.add_item(button)

        confirm = discord.ui.Button(label="✅ 次へ", style=discord.ButtonStyle.success, row=2)
        confirm.callback = self.next_step
        self.add_item(confirm)

    async def open_stat_modal(self, interaction: discord.Interaction, stat_key: str, stat_name: str):
        modal = StatInputModal(self.cog, self.modal_data, stat_key, stat_name)
        await interaction.response.send_modal(modal)

    async def next_step(self, interaction: discord.Interaction):
        stats_text = "\n".join([f"{name}: +{value}" for name, value in [
            ("攻撃力", self.modal_data["stats"].get("atk", 0)),
            ("防御力", self.modal_data["stats"].get("def", 0)),
            ("魔法力", self.modal_data["stats"].get("mag", 0)),
            ("素早さ", self.modal_data["stats"].get("agi", 0)),
            ("HP", self.modal_data["stats"].get("hp", 0)),
            ("MP", self.modal_data["stats"].get("mp", 0)),
        ] if value > 0])

        embed = discord.Embed(
            title="📊 ステータス確認",
            description=f"設定されたステータス:\n{stats_text if stats_text else 'なし'}",
            color=discord.Color.blue()
        )
        view = NameInputView(self.cog, self.modal_data)
        await interaction.response.edit_message(embed=embed, view=view)


class StatInputModal(discord.ui.Modal, title="ステータス入力"):
    def __init__(self, cog, modal_data, stat_key: str, stat_name: str):
        super().__init__()
        self.cog = cog
        self.modal_data = modal_data
        self.stat_key = stat_key
        self.stat_name = stat_name

        self.value_input = discord.ui.TextInput(
            label=f"{stat_name}の値 (0-999)",
            placeholder="例: 50",
            required=True,
            max_length=3
        )
        self.add_item(self.value_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = int(self.value_input.value)
            if "stats" not in self.modal_data:
                self.modal_data["stats"] = {}
            self.modal_data["stats"][self.stat_key] = value
            
            print(f"🔍 [DEBUG] {self.stat_name} を {value} に設定しました")
            print(f"🔍 [DEBUG] 現在のstats: {self.modal_data['stats']}")
            
            new_view = StatsSelectView(self.cog, self.modal_data)
            await interaction.response.edit_message(view=new_view)
        except ValueError:
            await interaction.response.send_message("❌ 数字を入力してください", ephemeral=True)


# ==================== 名前入力 ====================
class NameInputModal(discord.ui.Modal, title="装備名入力"):
    def __init__(self, cog, modal_data):
        super().__init__()
        self.cog = cog
        self.modal_data = modal_data

        self.name_input = discord.ui.TextInput(
            label="装備の名前",
            placeholder="例: 伝説の剣",
            required=True,
            max_length=50
        )
        self.add_item(self.name_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.modal_data["name"] = self.name_input.value
        view = MaterialSelectView(self.cog, self.modal_data, "craft")
        await interaction.response.edit_message(
            embed=discord.Embed(title="🔨 作成素材選択", description="作成に必要な素材を選んでください", color=discord.Color.green()),
            view=view
        )


class NameInputView(discord.ui.View):
    def __init__(self, cog, modal_data):
        super().__init__(timeout=120)
        self.cog = cog
        self.modal_data = modal_data

        button = discord.ui.Button(label="📝 名前を入力", style=discord.ButtonStyle.primary)
        button.callback = self.open_modal
        self.add_item(button)

    async def open_modal(self, interaction: discord.Interaction):
        modal = NameInputModal(self.cog, self.modal_data)
        await interaction.response.send_modal(modal)


# ==================== 素材選択 ====================
class MaterialSelect(discord.ui.Select):
    def __init__(self, cog, modal_data, mode: str, current_materials: dict, available_materials: list):
        self.cog = cog
        self.modal_data = modal_data
        self.mode = mode
        self.current_materials = current_materials

        options = []
        for mat_id, mat in available_materials[:25]:
            options.append(discord.SelectOption(
                label=mat["name"],
                value=mat_id,
                emoji={"S": "🟧", "A": "🟣", "B": "🔵", "C": "🟢"}.get(mat.get("rank", "C"), "⚪"),
                description=f"現在選択中: {current_materials.get(mat_id, 0)}個"
            ))
        super().__init__(placeholder="素材を選択", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        mat_id = self.values[0]
        modal = MaterialQuantityModal(self.cog, self.modal_data, self.mode, self.current_materials, mat_id)
        await interaction.response.send_modal(modal)


class MaterialQuantityModal(discord.ui.Modal, title="素材個数入力"):
    def __init__(self, cog, modal_data, mode: str, current_materials: dict, mat_id: str):
        super().__init__()
        self.cog = cog
        self.modal_data = modal_data
        self.mode = mode
        self.current_materials = current_materials
        self.mat_id = mat_id

        material_data = cog.load_materials()
        mat_name = material_data.get(mat_id, {}).get("name", mat_id)

        self.quantity_input = discord.ui.TextInput(
            label=f"{mat_name} の必要個数",
            placeholder="例: 5",
            required=True,
            max_length=3
        )
        self.add_item(self.quantity_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            quantity = int(self.quantity_input.value)
            self.current_materials[self.mat_id] = quantity
            view = MaterialSelectView(self.cog, self.modal_data, self.mode, self.current_materials)
            await interaction.response.edit_message(view=view)
        except ValueError:
            await interaction.response.send_message("❌ 数字を入力してください", ephemeral=True)


class MaterialSelectView(discord.ui.View):
    def __init__(self, cog, modal_data, mode: str, current_materials: dict = None):
        super().__init__(timeout=120)
        self.cog = cog
        self.modal_data = modal_data
        self.mode = mode
        self.current_materials = current_materials or {}

        self.available_materials = list(cog.load_materials().items())

        if self.available_materials:
            self.add_item(MaterialSelect(cog, modal_data, mode, self.current_materials, self.available_materials))

        confirm = discord.ui.Button(label="✅ 確定", style=discord.ButtonStyle.success, row=1)
        confirm.callback = self.confirm
        self.add_item(confirm)

        skip = discord.ui.Button(label="⏩ スキップ", style=discord.ButtonStyle.secondary, row=1)
        skip.callback = self.skip
        self.add_item(skip)

    async def confirm(self, interaction: discord.Interaction):
        if self.mode == "craft":
            self.modal_data["materials"] = self.current_materials
            view = MaterialSelectView(self.cog, self.modal_data, "upgrade")
            await interaction.response.edit_message(
                embed=discord.Embed(title="⬆️ 強化素材選択", description="強化に必要な素材を選んでください", color=discord.Color.blue()),
                view=view
            )
        else:
            self.modal_data["upgrade_materials"] = self.current_materials
            view = DescriptionInputView(self.cog, self.modal_data)
            await interaction.response.edit_message(
                embed=discord.Embed(title="📝 説明入力", description="装備の説明を入力してください", color=discord.Color.purple()),
                view=view
            )

    async def skip(self, interaction: discord.Interaction):
        if self.mode == "craft":
            self.modal_data["materials"] = {}
            view = MaterialSelectView(self.cog, self.modal_data, "upgrade")
            await interaction.response.edit_message(
                embed=discord.Embed(title="⬆️ 強化素材選択", description="強化に必要な素材を選んでください", color=discord.Color.blue()),
                view=view
            )
        else:
            self.modal_data["upgrade_materials"] = {}
            view = DescriptionInputView(self.cog, self.modal_data)
            await interaction.response.edit_message(
                embed=discord.Embed(title="📝 説明入力", description="装備の説明を入力してください", color=discord.Color.purple()),
                view=view
            )


# ==================== 説明入力 ====================
class DescriptionModal(discord.ui.Modal, title="装備説明入力"):
    def __init__(self, cog, modal_data):
        super().__init__()
        self.cog = cog
        self.modal_data = modal_data

        self.desc_input = discord.ui.TextInput(
            label="装備の説明",
            placeholder="例: 古の伝説に登場する神剣",
            required=True,
            max_length=200,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.desc_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.modal_data["description"] = self.desc_input.value
        await self.cog.save_equipment(interaction, self.modal_data)


class DescriptionInputView(discord.ui.View):
    def __init__(self, cog, modal_data):
        super().__init__(timeout=120)
        self.cog = cog
        self.modal_data = modal_data

        button = discord.ui.Button(label="📝 説明を入力", style=discord.ButtonStyle.primary)
        button.callback = self.open_modal
        self.add_item(button)

    async def open_modal(self, interaction: discord.Interaction):
        modal = DescriptionModal(self.cog, self.modal_data)
        await interaction.response.send_modal(modal)


# ==================== メイン管理コマンド ====================
class AdminCreator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.equipment_path = "cogs/rpg/data/equipment.json"
        self.materials_path = "cogs/rpg/data/drop_items.json"
        self.recipes_path = "cogs/rpg/data/recipes.json"
        self._ensure_files()

    def _ensure_files(self):
        for path in [self.equipment_path, self.materials_path, self.recipes_path]:
            if not os.path.exists(path):
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, indent=2)

    def load_equipment(self):
        with open(self.equipment_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_equipment_data(self, data):
        with open(self.equipment_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_materials(self):
        with open(self.materials_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("materials", {})

    def save_materials(self, materials):
        with open(self.materials_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data["materials"] = materials
        with open(self.materials_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_recipes(self):
        with open(self.recipes_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_recipes(self, data):
        with open(self.recipes_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def save_equipment(self, interaction: discord.Interaction, data: dict):
        equip_id = str(uuid.uuid4())[:8]
        
        # カテゴリとタイプに応じた保存先を決定
        category = "weapons"
        slot = "weapon"
        
        if data.get("category") == "weapon":
            category = "weapons"
            slot = data.get("item_type", "sword")
        elif data.get("category") == "armor":
            category = "armors"
            slot = data.get("item_type", "armor")
        elif data.get("category") == "accessory":
            category = "accessories"
            slot = data.get("item_type", "ring")

        equipment = self.load_equipment()
        if category not in equipment:
            equipment[category] = {}

        # レアリティに応じた絵文字
        rarity_emoji = {
            "common": "⬜", "uncommon": "🟩", "rare": "🟦", 
            "epic": "🟪", "legendary": "🟧"
        }.get(data.get("rarity", "common"), "⚪")

        equipment[category][equip_id] = {
            "name": data["name"],
            "description": data["description"],
            "emoji": rarity_emoji,
            "required_level": data.get("required_level", 1),
            "value": data.get("price", 100),
            "rarity": data.get("rarity", "common"),
            "stats": data["stats"],
            "slot": slot,
            "materials": data.get("materials", {}),
            "upgrade_materials": data.get("upgrade_materials", {})
        }

        if data.get("element"):
            equipment[category][equip_id]["element"] = data["element"]

        self._save_equipment_data(equipment)

        # レシピにも追加
        recipes = self.load_recipes()
        if category not in recipes:
            recipes[category] = {}
        recipes[category][equip_id] = {
            "name": data["name"],
            "description": data["description"],
            "emoji": rarity_emoji,
            "required_level": data.get("required_level", 1),
            "stats": data["stats"],
            "element": data.get("element"),
            "materials": [{"item": k, "quantity": v} for k, v in data.get("materials", {}).items()]
        }
        self.save_recipes(recipes)

        embed = discord.Embed(
            title="✅ 装備作成完了！",
            description=f"**{data['name']}** を作成しました\n"
                        f"📊 必要レベル: Lv.{data.get('required_level', 1)}\n"
                        f"💰 価格: {data.get('price', 100)}G\n"
                        f"🏷️ レアリティ: {data.get('rarity', 'common')}\n"
                        f"🆔 ID: `{equip_id}`",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)

    # ==================== 削除コマンド ====================

    @app_commands.command(name="rpg_admin_delete_equipment", description="装備を削除する（管理者用）")
    @app_commands.default_permissions(administrator=True)
    async def delete_equipment(self, interaction: discord.Interaction, item_id: str):
        equipment = self.load_equipment()
        found = False
        deleted_name = None
        
        for category in ["weapons", "armors", "accessories"]:
            if category in equipment and item_id in equipment[category]:
                deleted_name = equipment[category][item_id].get("name", item_id)
                del equipment[category][item_id]
                found = True
                break
        
        if not found:
            await interaction.response.send_message(f"❌ 装備ID `{item_id}` が見つかりません", ephemeral=True)
            return
        
        self._save_equipment_data(equipment)
        
        recipes = self.load_recipes()
        for category in ["weapons", "armors", "items"]:
            if category in recipes and item_id in recipes[category]:
                del recipes[category][item_id]
                self.save_recipes(recipes)
                break
        
        embed = discord.Embed(
            title="🗑️ 装備削除完了",
            description=f"**{deleted_name}** (`{item_id}`) を削除しました",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="rpg_admin_delete_material", description="素材を削除する（管理者用）")
    @app_commands.default_permissions(administrator=True)
    async def delete_material(self, interaction: discord.Interaction, material_id: str):
        materials = self.load_materials()
        
        if material_id not in materials:
            await interaction.response.send_message(f"❌ 素材ID `{material_id}` が見つかりません", ephemeral=True)
            return
        
        deleted_name = materials[material_id].get("name", material_id)
        del materials[material_id]
        self.save_materials(materials)
        
        embed = discord.Embed(
            title="🗑️ 素材削除完了",
            description=f"**{deleted_name}** (`{material_id}`) を削除しました",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="rpg_admin_list_equipment", description="装備一覧を表示する（管理者用）")
    @app_commands.default_permissions(administrator=True)
    async def list_equipment(self, interaction: discord.Interaction):
        equipment = self.load_equipment()
        
        embed = discord.Embed(
            title="📋 装備一覧 (管理者用)",
            description="削除するときはIDを使用します",
            color=discord.Color.blue()
        )
        
        for category in ["weapons", "armors", "accessories"]:
            if category in equipment and equipment[category]:
                items_text = ""
                for item_id, item in equipment[category].items():
                    items_text += f"• `{item_id}` - {item.get('name', '不明')}\n"
                    if len(items_text) > 800:
                        items_text += "..."
                        break
                embed.add_field(name=f"📦 {category}", value=items_text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="rpg_admin_list_materials", description="素材一覧を表示する（管理者用）")
    @app_commands.default_permissions(administrator=True)
    async def list_materials(self, interaction: discord.Interaction):
        materials = self.load_materials()
        
        if not materials:
            await interaction.response.send_message("📦 素材がありません", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📋 素材一覧 (管理者用)",
            description="削除するときはIDを使用します",
            color=discord.Color.green()
        )
        
        items_text = ""
        for mat_id, mat in materials.items():
            items_text += f"• `{mat_id}` - {mat.get('name', '不明')} (ランク: {mat.get('rank', 'C')})\n"
        
        embed.description = items_text[:1900] if len(items_text) > 1900 else items_text
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==================== 作成コマンド ====================

    @app_commands.command(name="rpg_admin_create_equipment", description="新しい装備を作成する（管理者用）")
    @app_commands.default_permissions(administrator=True)
    async def create_equipment(self, interaction: discord.Interaction):
        modal_data = {}
        embed = discord.Embed(
            title="🔨 装備作成ウィザード",
            description="装備のカテゴリを選んでください",
            color=discord.Color.gold()
        )
        view = CategorySelectView(self, modal_data)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="rpg_admin_create_materials", description="素材を一括作成する（管理者用）")
    @app_commands.default_permissions(administrator=True)
    async def create_materials(self, interaction: discord.Interaction):
        view = MaterialRankSelectView(self)
        embed = discord.Embed(
            title="📦 素材一括作成",
            description="作成する素材のランクを選択してください",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ==================== 素材ランク選択 ====================
class MaterialRankSelectView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=120)
        self.cog = cog

    @discord.ui.select(placeholder="素材のランクを選択", options=[
        discord.SelectOption(label="Cランク", value="C", emoji="🟢", description="基本素材"),
        discord.SelectOption(label="Bランク", value="B", emoji="🔵", description="中級素材"),
        discord.SelectOption(label="Aランク", value="A", emoji="🟣", description="上級素材"),
        discord.SelectOption(label="Sランク", value="S", emoji="🟧", description="レア素材"),
    ])
    async def rank_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        rank = select.values[0]
        modal = MaterialNameModal(self.cog, rank)
        await interaction.response.send_modal(modal)


class MaterialNameModal(discord.ui.Modal, title="素材情報入力"):
    def __init__(self, cog, rank: str):
        super().__init__()
        self.cog = cog
        self.rank = rank

        self.base_name = discord.ui.TextInput(
            label="素材の名前",
            placeholder="例: ドラゴンの鱗",
            required=True,
            max_length=30
        )
        self.add_item(self.base_name)

        self.description = discord.ui.TextInput(
            label="素材の説明（任意）",
            placeholder="例: 伝説のドラゴンから落ちる希少な鱗",
            required=False,
            max_length=100,
            style=discord.TextStyle.short
        )
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        base = self.base_name.value
        description = self.description.value if self.description.value else f"{base}から入手できる素材"
        
        rank_data = {
            "C": {"emoji": "🟢", "suffix": "", "range": ["C"]},
            "B": {"emoji": "🔵", "suffix": "", "range": ["C", "B"]},
            "A": {"emoji": "🟣", "suffix": "", "range": ["C", "B", "A"]},
            "S": {"emoji": "🟧", "suffix": "", "range": ["C", "B", "A", "S"]}
        }

        materials = self.cog.load_materials()
        created = []

        for r in rank_data[self.rank]["range"]:
            rank_name = {"C": "c", "B": "b", "A": "a", "S": "s"}[r]
            mat_id = f"{base.lower().replace(' ', '_')}_{rank_name}"
            mat_name = f"{base} ({r}ランク)"
            
            materials[mat_id] = {
                "name": mat_name,
                "rank": r,
                "emoji": rank_data[self.rank]["emoji"],
                "description": description,
                "value": {"C": 10, "B": 50, "A": 200, "S": 1000}[r]
            }
            created.append(f"{rank_data[self.rank]['emoji']} {mat_name} (`{mat_id}`)")

        self.cog.save_materials(materials)

        embed = discord.Embed(
            title="✅ 素材作成完了！",
            description="\n".join(created),
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== セットアップ ====================
async def setup(bot):
    await bot.add_cog(AdminCreator(bot))