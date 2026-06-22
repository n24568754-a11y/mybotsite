import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random

class InventoryView(discord.ui.View):
    """インベントリ閲覧ビュー（ページネーション対応）"""
    def __init__(self, cog, user_id, items, materials, page=0, mode="equipment"):
        super().__init__(timeout=120)
        self.cog = cog
        self.user_id = user_id
        self.items = items  # 装備リスト
        self.materials = materials  # 素材辞書
        self.page = page
        self.mode = mode  # "equipment" or "materials"
        self.items_per_page = 5
        
        # ページネーション計算
        if mode == "equipment":
            self.total_pages = max(1, (len(self.items) + self.items_per_page - 1) // self.items_per_page)
        else:
            self.total_pages = max(1, (len(self.materials) + self.items_per_page - 1) // self.items_per_page)
    
    @discord.ui.button(label="🎒 装備一覧", style=discord.ButtonStyle.primary, row=3)
    async def show_equipment(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたのインベントリではありません", ephemeral=True)
        
        # 装備一覧を再取得
        players = self.cog.load_players()
        uid = str(self.user_id)
        inventory_ids = players[uid].get("inventory", {}).get("equipment", [])
        
        items = []
        for item_id in inventory_ids:
            item = self.cog.get_equipment_by_id(item_id)
            if item:
                items.append(item)
        
        materials = players[uid].get("materials", {})
        
        view = InventoryView(self.cog, self.user_id, items, materials, 0, "equipment")
        embed = view.create_embed()
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="📦 素材一覧", style=discord.ButtonStyle.success, row=3)
    async def show_materials(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたのインベントリではありません", ephemeral=True)
        
        # 素材一覧を再取得
        players = self.cog.load_players()
        uid = str(self.user_id)
        materials = players[uid].get("materials", {})
        inventory_ids = players[uid].get("inventory", {}).get("equipment", [])
        
        items = []
        for item_id in inventory_ids:
            item = self.cog.get_equipment_by_id(item_id)
            if item:
                items.append(item)
        
        view = InventoryView(self.cog, self.user_id, items, materials, 0, "materials")
        embed = view.create_embed()
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="◀ 前へ", style=discord.ButtonStyle.secondary, row=4, disabled=True)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたのインベントリではありません", ephemeral=True)
        
        self.page -= 1
        await self.refresh_view(interaction)
    
    @discord.ui.button(label="次へ ▶", style=discord.ButtonStyle.secondary, row=4, disabled=True)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたのインベントリではありません", ephemeral=True)
        
        self.page += 1
        await self.refresh_view(interaction)
    
    @discord.ui.button(label="🚪 閉じる", style=discord.ButtonStyle.danger, emoji="🚪", row=4)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="インベントリを閉じました", embed=None, view=None)
    
    async def refresh_view(self, interaction):
        """ビューを更新"""
        if self.mode == "equipment":
            self.total_pages = max(1, (len(self.items) + self.items_per_page - 1) // self.items_per_page)
        else:
            materials_list = list(self.materials.items())
            self.total_pages = max(1, (len(materials_list) + self.items_per_page - 1) // self.items_per_page)
        
        # ページ範囲を修正
        if self.page >= self.total_pages:
            self.page = self.total_pages - 1
        if self.page < 0:
            self.page = 0
        
        # 新しいビューを作成
        if self.mode == "equipment":
            new_view = InventoryView(self.cog, self.user_id, self.items, self.materials, self.page, "equipment")
        else:
            new_view = InventoryView(self.cog, self.user_id, self.items, self.materials, self.page, "materials")
        
        embed = new_view.create_embed()
        await interaction.response.edit_message(embed=embed, view=new_view)
    
    def create_embed(self):
        """埋め込みを作成"""
        embed = discord.Embed(
            title=f"🎒 {self.cog.get_player_name(self.user_id)} のインベントリ",
            color=discord.Color.blue()
        )
        
        if self.mode == "equipment":
            return self.create_equipment_embed(embed)
        else:
            return self.create_materials_embed(embed)
    
    def create_equipment_embed(self, embed):
        """装備一覧の埋め込み"""
        start = self.page * self.items_per_page
        end = min(start + self.items_per_page, len(self.items))
        
        # ページ情報
        embed.description = f"📄 {self.page + 1}/{self.total_pages}ページ"
        
        if not self.items:
            embed.add_field(name="📦 所持装備", value="装備を持っていません", inline=False)
        else:
            for i, item in enumerate(self.items[start:end], start=start + 1):
                # ステータス表示
                stats = []
                for stat, value in item.get("stats", {}).items():
                    stat_name = {"atk": "⚔️攻撃", "def": "🛡️防御", "mag": "🔮魔法", "agi": "💨素早さ", "hp": "❤️HP", "mp": "✨MP", "luk": "🍀運"}
                    stats.append(f"{stat_name.get(stat, stat)}+{value}")
                
                element_text = f" 🔥[{item['element']}]" if item.get("element") else ""
                embed.add_field(
                    name=f"{i}. {item['emoji']} {item['name']}{element_text} (Lv.{item.get('required_level', 1)})",
                    value=f"📝 {item['description']}\n📊 {', '.join(stats)}",
                    inline=False
                )
        
        embed.set_footer(text="装備は `/rpg_equip_select` で装備できます | 素材一覧で切り替え")
        return embed
    
    def create_materials_embed(self, embed):
        """素材一覧の埋め込み"""
        # drop_itemsを読み込み
        drop_items_path = "cogs/rpg/data/drop_items.json"
        material_data = {}
        if os.path.exists(drop_items_path):
            with open(drop_items_path, 'r', encoding='utf-8') as f:
                drop_data = json.load(f)
                material_data = drop_data.get("materials", {})
        
        # 素材をリスト化してソート
        materials_list = list(self.materials.items())
        # ランク順にソート
        def get_rank_order(item):
            rank = material_data.get(item[0], {}).get("rank", "C")
            return {"S": 1, "A": 2, "B": 3, "C": 4}.get(rank, 5)
        materials_list.sort(key=get_rank_order)
        
        start = self.page * self.items_per_page
        end = min(start + self.items_per_page, len(materials_list))
        
        # ページ情報
        embed.description = f"📄 {self.page + 1}/{self.total_pages}ページ"
        
        if not materials_list:
            embed.add_field(name="📦 所持素材", value="素材を持っていません", inline=False)
        else:
            total_materials = sum(self.materials.values())
            embed.add_field(name="📊 素材総数", value=f"{total_materials}個", inline=False)
            
            for mat_id, count in materials_list[start:end]:
                mat = material_data.get(mat_id, {})
                rank_emoji = {"S": "🟧", "A": "🟣", "B": "🔵", "C": "🟢"}.get(mat.get("rank", "C"), "⚪")
                
                embed.add_field(
                    name=f"{rank_emoji} {mat.get('name', mat_id)}",
                    value=f"個数: **{count}** 個\n📝 {mat.get('description', '')[:40]}",
                    inline=True
                )
        
        embed.set_footer(text="素材を集めてクラフトしよう！ | 装備一覧で切り替え")
        return embed


class EquipmentSelectView(discord.ui.View):
    """装備選択ビュー（ページネーション対応）"""
    def __init__(self, cog, user_id, items, page=0, sort_by="name"):
        super().__init__(timeout=120)
        self.cog = cog
        self.user_id = user_id
        self.items = items
        self.page = page
        self.sort_by = sort_by
        self.items_per_page = 5
        
        # ソート適用
        self.sorted_items = self.sort_items()
        self.total_pages = max(1, (len(self.sorted_items) + self.items_per_page - 1) // self.items_per_page)
        
        # ボタンを動的に追加
        self.add_equipment_buttons()
        self.add_navigation_buttons()
    
    def sort_items(self):
        """アイテムをソート"""
        if self.sort_by == "atk":
            return sorted(self.items, key=lambda x: x.get("stats", {}).get("atk", 0), reverse=True)
        elif self.sort_by == "def":
            return sorted(self.items, key=lambda x: x.get("stats", {}).get("def", 0), reverse=True)
        elif self.sort_by == "mag":
            return sorted(self.items, key=lambda x: x.get("stats", {}).get("mag", 0), reverse=True)
        elif self.sort_by == "level":
            return sorted(self.items, key=lambda x: x.get("required_level", 1))
        else:  # name
            return sorted(self.items, key=lambda x: x.get("name", ""))
    
    def add_equipment_buttons(self):
        """ページ内の装備ボタンを追加"""
        start = self.page * self.items_per_page
        end = min(start + self.items_per_page, len(self.sorted_items))
        
        # 既存の装備ボタンをクリア
        for item in self.children[:]:
            if hasattr(item, 'custom_id') and item.custom_id and item.custom_id.startswith("equip_"):
                self.remove_item(item)
        
        # 装備ボタンを追加
        for i, item in enumerate(self.sorted_items[start:end], start=start + 1):
            # ステータス表示用ラベル
            stats_str = ""
            for stat, value in item.get("stats", {}).items():
                stat_emoji = {"atk": "⚔️", "def": "🛡️", "mag": "🔮", "agi": "💨", "hp": "❤️", "mp": "✨", "luk": "🍀"}
                stats_str += f"{stat_emoji.get(stat, '')}{value} "
            
            button = discord.ui.Button(
                label=f"{item['emoji']} {item['name']} Lv.{item['required_level']}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"equip_{item['id']}",
                row=(i - start) // 2
            )
            
            async def button_callback(interaction, item_id=item['id'], item_name=item['name'], stats=stats_str):
                await self.confirm_equip(interaction, item_id, item_name, stats)
            
            button.callback = button_callback
            self.add_item(button)
    
    def add_navigation_buttons(self):
        """ナビゲーションボタンを追加"""
        # ソートボタン（row=3）
        sort_atk = discord.ui.Button(label="📊 攻撃力順", style=discord.ButtonStyle.primary, row=3, custom_id="sort_atk")
        sort_def = discord.ui.Button(label="🛡️ 防御力順", style=discord.ButtonStyle.primary, row=3, custom_id="sort_def")
        sort_mag = discord.ui.Button(label="🔮 魔法力順", style=discord.ButtonStyle.primary, row=3, custom_id="sort_mag")
        sort_name = discord.ui.Button(label="🔰 名前順", style=discord.ButtonStyle.secondary, row=3, custom_id="sort_name")
        
        # ページボタン（row=4）
        prev_page = discord.ui.Button(label="◀ 前へ", style=discord.ButtonStyle.secondary, row=4, custom_id="prev_page", disabled=(self.page == 0))
        next_page = discord.ui.Button(label="次へ ▶", style=discord.ButtonStyle.secondary, row=4, custom_id="next_page", disabled=(self.page >= self.total_pages - 1))
        close_btn = discord.ui.Button(label="🚪 閉じる", style=discord.ButtonStyle.danger, row=4, custom_id="close")
        
        self.add_item(sort_atk)
        self.add_item(sort_def)
        self.add_item(sort_mag)
        self.add_item(sort_name)
        self.add_item(prev_page)
        self.add_item(next_page)
        self.add_item(close_btn)
    
    async def confirm_equip(self, interaction, item_id, item_name, stats_str):
        """装備確認ダイアログ"""
        view = EquipConfirmView(self.cog, self.user_id, item_id, item_name, stats_str)
        embed = discord.Embed(
            title="🔰 装備確認",
            description=f"**{item_name}** を装備しますか？\n{stats_str}",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """ボタンインタラクションの処理"""
        custom_id = interaction.data.get("custom_id", "")
        
        if custom_id == "sort_atk":
            self.sort_by = "atk"
            await self.refresh_view(interaction)
            return False
        elif custom_id == "sort_def":
            self.sort_by = "def"
            await self.refresh_view(interaction)
            return False
        elif custom_id == "sort_mag":
            self.sort_by = "mag"
            await self.refresh_view(interaction)
            return False
        elif custom_id == "sort_name":
            self.sort_by = "name"
            await self.refresh_view(interaction)
            return False
        elif custom_id == "prev_page":
            if self.page > 0:
                self.page -= 1
                await self.refresh_view(interaction)
            return False
        elif custom_id == "next_page":
            if self.page < self.total_pages - 1:
                self.page += 1
                await self.refresh_view(interaction)
            return False
        elif custom_id == "close":
            await interaction.response.edit_message(content="装備選択を終了しました", embed=None, view=None)
            return False
        
        return True
    
    async def refresh_view(self, interaction):
        """ビューを更新"""
        # ソートとページネーションを再計算
        self.sorted_items = self.sort_items()
        self.total_pages = max(1, (len(self.sorted_items) + self.items_per_page - 1) // self.items_per_page)
        
        # ページ範囲を修正
        if self.page >= self.total_pages:
            self.page = self.total_pages - 1
        if self.page < 0:
            self.page = 0
        
        # 新しいビューを作成
        new_view = EquipmentSelectView(self.cog, self.user_id, self.items, self.page, self.sort_by)
        
        # 埋め込みを作成
        embed = new_view.create_embed()
        await interaction.response.edit_message(embed=embed, view=new_view)
    
    def create_embed(self):
        """埋め込みを作成"""
        start = self.page * self.items_per_page
        end = min(start + self.items_per_page, len(self.sorted_items))
        
        embed = discord.Embed(
            title="🔰 装備選択",
            description=f"装備するアイテムを選んでください\n`{self.page + 1}/{self.total_pages}ページ`",
            color=discord.Color.gold()
        )
        
        for i, item in enumerate(self.sorted_items[start:end], start=start + 1):
            stats = []
            for stat, value in item.get("stats", {}).items():
                stat_name = {"atk": "攻撃", "def": "防御", "mag": "魔法", "agi": "素早さ", "hp": "HP", "mp": "MP", "luk": "運"}
                stats.append(f"{stat_name.get(stat, stat)} +{value}")
            
            element_text = f"\n🔥 属性: {item['element']}" if item.get("element") else ""
            embed.add_field(
                name=f"{i}. {item['emoji']} {item['name']} (Lv.{item['required_level']})",
                value=f"📝 {item['description']}\n📊 {', '.join(stats)}{element_text}\n💰 {item['value']}G",
                inline=False
            )
        
        embed.set_footer(text="ソートボタンで並び替え | 装備をクリックで選択")
        return embed


class EquipConfirmView(discord.ui.View):
    """装備確認ビュー"""
    def __init__(self, cog, user_id, item_id, item_name, stats_str):
        super().__init__(timeout=60)
        self.cog = cog
        self.user_id = user_id
        self.item_id = item_id
        self.item_name = item_name
        self.stats_str = stats_str
    
    @discord.ui.button(label="✅ 装備する", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        success, message = self.cog.equip_item(self.user_id, self.item_id)
        
        if success:
            embed = discord.Embed(
                title="✅ 装備完了",
                description=f"{message}\n{self.stats_str}",
                color=discord.Color.green()
            )
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            embed = discord.Embed(
                title="❌ 装備失敗",
                description=message,
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="❌ キャンセル", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="キャンセルしました", embed=None, view=None)


class EquipmentSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.equipment_path = "cogs/rpg/data/equipment.json"
        self.load_equipment()
    
    def load_equipment(self):
        """装備データを読み込み"""
        if os.path.exists(self.equipment_path):
            with open(self.equipment_path, 'r', encoding='utf-8') as f:
                self.equipment_data = json.load(f)
        else:
            self.equipment_data = {"weapons": {}, "armors": {}, "accessories": {}, "element_chart": {}}
    
    def load_players(self):
        players_path = "cogs/rpg/data/players.json"
        with open(players_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_players(self, data):
        players_path = "cogs/rpg/data/players.json"
        with open(players_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"🔍 [DEBUG] save_players 実行: 保存先 = {players_path}")
    
    def get_player_name(self, user_id):
        """プレイヤー名を取得"""
        players = self.load_players()
        uid = str(user_id)
        if uid in players:
            return players[uid].get("name", "冒険者")
        return "冒険者"
    
    def get_all_equipment(self):
        """全ての装備をカテゴリ別に取得"""
        result = []
        for category in ["weapons", "armors", "accessories"]:
            for item_id, item in self.equipment_data.get(category, {}).items():
                result.append({
                    "id": item_id,
                    "category": category,
                    **item
                })
        return result
    
    def get_equipment_by_id(self, item_id):
        """IDから装備を検索"""
        for category in ["weapons", "armors", "accessories"]:
            if item_id in self.equipment_data.get(category, {}):
                return {
                    "id": item_id,
                    "category": category,
                    **self.equipment_data[category][item_id]
                }
        return None
    
    def get_player_equipment_stats(self, user_id):
        """装備からステータスボーナスを計算"""
        players = self.load_players()
        uid = str(user_id)
        
        if uid not in players:
            return {}, []
        
        equipment = players[uid].get("equipment", {})
        bonus = {"atk": 0, "def": 0, "mag": 0, "agi": 0, "luk": 0, "hp": 0, "mp": 0}
        elements = []
        equipment_list = []
        
        for slot, item_id in equipment.items():
            if item_id:
                item = self.get_equipment_by_id(item_id)
                if item:
                    equipment_list.append(item)
                    for stat, value in item.get("stats", {}).items():
                        bonus[stat] = bonus.get(stat, 0) + value
                    if item.get("element"):
                        elements.append(item["element"])
        
        return bonus, elements, equipment_list
    
    def get_player_inventory(self, user_id):
        """プレイヤーの所持装備リストを取得"""
        players = self.load_players()
        uid = str(user_id)
        
        if uid not in players:
            return []
        
        return players[uid].get("inventory", {}).get("equipment", [])
    
    def add_equipment_to_inventory(self, user_id, item_id):
        """プレイヤーに装備を追加"""
        players = self.load_players()
        uid = str(user_id)
        
        print(f"🔍 [DEBUG] add_equipment_to_inventory: uid={uid}, item_id={item_id}")
        
        if uid not in players:
            print(f"🔍 [DEBUG] プレイヤーが見つかりません")
            return False
        
        if "inventory" not in players[uid]:
            players[uid]["inventory"] = {"items": {}, "equipment": []}
        if "equipment" not in players[uid]["inventory"]:
            players[uid]["inventory"]["equipment"] = []
        
        if item_id not in players[uid]["inventory"]["equipment"]:
            players[uid]["inventory"]["equipment"].append(item_id)
            self.save_players(players)
            print(f"🔍 [DEBUG] 装備追加成功: {item_id}")
            return True
        
        print(f"🔍 [DEBUG] 装備は既に所持しています: {item_id}")
        return False
    
    def remove_equipment_from_inventory(self, user_id, item_id):
        """プレイヤーから装備を削除"""
        players = self.load_players()
        uid = str(user_id)
        
        if uid in players and item_id in players[uid].get("inventory", {}).get("equipment", []):
            players[uid]["inventory"]["equipment"].remove(item_id)
            self.save_players(players)
            return True
        return False
    
    def equip_item(self, user_id, item_id):
        """装備を装備する"""
        players = self.load_players()
        uid = str(user_id)
        
        if uid not in players:
            return False, "冒険者登録が必要です"
        
        item = self.get_equipment_by_id(item_id)
        if not item:
            return False, "その装備は存在しません"
        
        # 所持確認
        if item_id not in players[uid].get("inventory", {}).get("equipment", []):
            return False, "その装備を持っていません"
        
        # レベル要件確認
        if players[uid].get("level", 1) < item.get("required_level", 1):
            return False, f"レベル{item['required_level']}以上が必要です"
        
        # 装備スロットを決定
        slot_map = {"weapons": "weapon", "armors": "armor", "accessories": "accessory"}
        slot = slot_map.get(item["category"])
        
        if not slot:
            return False, "装備カテゴリが不正です"
        
        if "equipment" not in players[uid]:
            players[uid]["equipment"] = {}
        
        players[uid]["equipment"][slot] = item_id
        self.save_players(players)
        
        return True, f"{item['name']} を装備した！"
    
    def unequip_item(self, user_id, slot):
        """装備を外す"""
        players = self.load_players()
        uid = str(user_id)
        
        if uid not in players:
            return False, "冒険者登録が必要です"
        
        if "equipment" not in players[uid]:
            return False, "装備していません"
        
        if slot not in players[uid]["equipment"]:
            return False, "そのスロットには装備していません"
        
        players[uid]["equipment"][slot] = None
        self.save_players(players)
        
        return True, f"{slot}の装備を外した！"
    
    def calculate_element_damage(self, attacker_element, defender_element, defender_resists=None, defender_weaknesses=None, base_damage=0):
        """拡張版属性相性ダメージ計算"""
        if not attacker_element:
            return base_damage, 1.0, "通常"
        
        element_chart = self.equipment_data.get("element_chart", {})
        multiplier = 1.0
        messages = []
        
        # 防御側の情報を初期化
        if defender_resists is None:
            defender_resists = []
        if defender_weaknesses is None:
            defender_weaknesses = []
        
        # 弱点チェック（ダメージ1.5倍）
        if defender_element:
            chart = element_chart.get(defender_element, {})
            if attacker_element in chart.get("weak", []):
                multiplier *= 1.5
                messages.append(f"{chart.get('name', defender_element)}の弱点をついた！")
        
        # 追加の弱点チェック
        for weakness in defender_weaknesses:
            chart = element_chart.get(weakness, {})
            if attacker_element in chart.get("weak", []):
                multiplier *= 1.5
                messages.append(f"{chart.get('name', weakness)}の弱点をついた！")
        
        # 耐性チェック（ダメージ0.5倍）
        if defender_element:
            chart = element_chart.get(defender_element, {})
            if attacker_element in chart.get("resist", []):
                multiplier *= 0.5
                messages.append(f"{chart.get('name', defender_element)}に耐性がある！")
        
        # 追加の耐性チェック
        for resist in defender_resists:
            chart = element_chart.get(resist, {})
            if attacker_element in chart.get("resist", []):
                multiplier *= 0.5
                messages.append(f"{chart.get('name', resist)}に耐性がある！")
        
        # 免疫チェック（ダメージ0）
        if defender_element:
            chart = element_chart.get(defender_element, {})
            if attacker_element in chart.get("immune", []):
                multiplier = 0
                messages.append(f"{chart.get('name', defender_element)}には効かない！")
        
        # 最大2.25倍、最小0倍
        multiplier = max(0, min(2.25, multiplier))
        
        message = " | ".join(messages) if messages else "通常"
        return int(base_damage * multiplier), multiplier, message
    
    @app_commands.command(name="rpg_inventory", description="所持品を確認する（装備・素材）")
    async def inventory(self, interaction: discord.Interaction):
        """所持装備と素材を表示"""
        players = self.load_players()
        uid = str(interaction.user.id)
        
        if uid not in players:
            return await interaction.response.send_message("❌ `/rpg_start` で冒険者になりましょう！", ephemeral=True)
        
        # 装備一覧を取得
        inventory_ids = players[uid].get("inventory", {}).get("equipment", [])
        items = []
        for item_id in inventory_ids:
            item = self.get_equipment_by_id(item_id)
            if item:
                items.append(item)
        
        # 素材一覧を取得
        materials = players[uid].get("materials", {})
        
        view = InventoryView(self, interaction.user.id, items, materials, 0, "equipment")
        embed = view.create_embed()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="rpg_equip", description="装備を変更する（ID指定）")
    async def equip(self, interaction: discord.Interaction, item_id: str):
        """装備を装備する（ID指定）"""
        await interaction.response.defer(ephemeral=True)
        
        success, message = self.equip_item(interaction.user.id, item_id)
        
        if success:
            await interaction.followup.send(f"✅ {message}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {message}", ephemeral=True)
    
    @app_commands.command(name="rpg_equip_select", description="所持品から視覚的に装備を選択する")
    async def equip_select(self, interaction: discord.Interaction):
        """視覚的に装備を選択"""
        players = self.load_players()
        uid = str(interaction.user.id)
        
        if uid not in players:
            return await interaction.response.send_message("❌ `/rpg_start` で冒険者になりましょう！", ephemeral=True)
        
        # 所持装備を取得
        inventory_ids = players[uid].get("inventory", {}).get("equipment", [])
        
        if not inventory_ids:
            return await interaction.response.send_message("❌ 所持している装備がありません！", ephemeral=True)
        
        # 装備オブジェクトのリストを取得
        items = []
        for item_id in inventory_ids:
            item = self.get_equipment_by_id(item_id)
            if item:
                items.append(item)
        
        if not items:
            return await interaction.response.send_message("❌ 有効な装備が見つかりません", ephemeral=True)
        
        view = EquipmentSelectView(self, interaction.user.id, items)
        embed = view.create_embed()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="rpg_unequip", description="装備を外す")
    @app_commands.choices(slot=[
        app_commands.Choice(name="武器", value="weapon"),
        app_commands.Choice(name="防具", value="armor"),
        app_commands.Choice(name="アクセサリー", value="accessory")
    ])
    async def unequip(self, interaction: discord.Interaction, slot: str):
        """装備を外す"""
        await interaction.response.defer(ephemeral=True)
        
        success, message = self.unequip_item(interaction.user.id, slot)
        
        if success:
            await interaction.followup.send(f"✅ {message}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {message}", ephemeral=True)
    
    @app_commands.command(name="rpg_equipment_list", description="入手可能な装備一覧を表示")
    async def equipment_list(self, interaction: discord.Interaction):
        """全装備一覧を表示"""
        embed = discord.Embed(
            title="📚 装備図鑑",
            description="入手可能な装備一覧",
            color=discord.Color.gold()
        )
        
        categories = [
            ("⚔️ 武器", "weapons"),
            ("🛡️ 防具", "armors"),
            ("💍 アクセサリー", "accessories")
        ]
        
        for cat_name, cat_key in categories:
            items = self.equipment_data.get(cat_key, {})
            if items:
                item_text = ""
                for item_id, item in items.items():
                    rarity_emoji = {"common": "⬜", "uncommon": "🟩", "rare": "🟦", "epic": "🟪", "legendary": "🟧"}
                    rarity = rarity_emoji.get(item.get("rarity", "common"), "⬜")
                    element_text = f" [{item['element']}]" if item.get("element") else ""
                    item_text += f"{rarity} {item['emoji']} **{item['name']}**{element_text}\n"
                    item_text += f"   Lv.{item['required_level']} | {item['value']}G\n"
                embed.add_field(name=cat_name, value=item_text[:1020] if len(item_text) > 1020 else item_text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # ========== 管理者用コマンド ==========
    @app_commands.command(name="rpg_give_item", description="装備を付与する（管理者用）")
    @app_commands.default_permissions(administrator=True)
    async def give_item(self, interaction: discord.Interaction, item_id: str, target: discord.User = None):
        """装備を付与する（管理者用）"""
        user = target or interaction.user
        if self.add_equipment_to_inventory(user.id, item_id):
            item = self.get_equipment_by_id(item_id)
            if item:
                await interaction.response.send_message(f"✅ {user.display_name} に `{item['name']}` を付与しました", ephemeral=True)
            else:
                await interaction.response.send_message(f"✅ ID: {item_id} を付与しました", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ アイテムID `{item_id}` が見つからないか、既に所持しています", ephemeral=True)


async def setup(bot):
    await bot.add_cog(EquipmentSystem(bot))