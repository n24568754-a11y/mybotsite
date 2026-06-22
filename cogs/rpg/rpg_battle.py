import discord
from discord import app_commands
from discord.ext import commands
import random
import json
import os
from firebase_admin import db

class SpellSelectView(discord.ui.View):
    """魔法選択ビュー"""
    def __init__(self, battle_view, spells):
        super().__init__(timeout=30)
        self.battle_view = battle_view
        self.spells = spells

    async def on_timeout(self):
        await self.battle_view.update_message()

    @discord.ui.button(label="戻る", style=discord.ButtonStyle.secondary, row=2)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=self.battle_view.create_embed(), view=self.battle_view)


class ItemSelectView(discord.ui.View):
    """アイテム選択ビュー"""
    def __init__(self, battle_view, items):
        super().__init__(timeout=30)
        self.battle_view = battle_view
        self.items = items

    async def on_timeout(self):
        await self.battle_view.update_message()

    @discord.ui.button(label="戻る", style=discord.ButtonStyle.secondary, row=2)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=self.battle_view.create_embed(), view=self.battle_view)


class BattleView(discord.ui.View):
    """完全版戦闘ビュー（属性相性対応・エコノミー連携）"""
    def __init__(self, cog, interaction, player_data, enemy_data):
        super().__init__(timeout=60)
        self.cog = cog
        self.interaction = interaction
        self.player = player_data.copy()
        self.enemy = enemy_data.copy()
        self.battle_log = []
        self.player_hp = player_data["hp"]
        self.enemy_hp = enemy_data["hp"]
        self.defending = False
        self.turn = "player"
        self.critical_hit = False
        self.enemy_key = None

        self.player_buffs = {"atk": 0, "def": 0, "mag": 0, "agi": 0}
        self.enemy_buffs = {"atk": 0, "def": 0, "mag": 0, "agi": 0}
        self.player_status = []
        self.enemy_status = []
        
        # 装備ボーナスを取得
        self.equipment_bonus = {"atk": 0, "def": 0, "mag": 0, "agi": 0, "hp": 0, "mp": 0}
        self.player_elements = []
        self.player_resists = []
        self.equipment_names = {"weapon": "なし", "armor": "なし", "accessory": "なし"}
        self.load_equipment_stats()
        
        # 報酬上限設定
        self.daily_gold_limit = 10000  # 1日の獲得上限
        self.battle_gold_limit = 500   # 1回の戦闘での獲得上限

    def get_player_money_from_firebase(self, user_id):
        """Firebaseからプレイヤーの所持金を取得"""
        try:
            ref = db.reference('USER_PROFILES')
            profiles = ref.get()
            if not profiles:
                return 0
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

    def get_today_gold_earned(self, user_id):
        """今日の獲得ゴールドを取得"""
        try:
            ref = db.reference('USER_PROFILES')
            profiles = ref.get()
            if not profiles:
                return 0
            auth_path = "user_auth.json"
            if os.path.exists(auth_path):
                with open(auth_path, 'r', encoding='utf-8') as f:
                    auth_data = json.load(f)
                uid = str(user_id)
                password = auth_data.get(uid)
                if password and password in profiles:
                    return profiles[password].get('daily_gold_earned', 0)
            return 0
        except Exception as e:
            print(f"Firebase読み込みエラー: {e}")
            return 0

    def update_today_gold_earned(self, user_id, amount):
        """今日の獲得ゴールドを更新"""
        try:
            ref = db.reference('USER_PROFILES')
            profiles = ref.get()
            if not profiles:
                return False
            auth_path = "user_auth.json"
            if os.path.exists(auth_path):
                with open(auth_path, 'r', encoding='utf-8') as f:
                    auth_data = json.load(f)
                uid = str(user_id)
                password = auth_data.get(uid)
                if password and password in profiles:
                    current = profiles[password].get('daily_gold_earned', 0)
                    ref.child(password).update({'daily_gold_earned': current + amount})
                    return True
            return False
        except Exception as e:
            print(f"Firebase更新エラー: {e}")
            return False

    def get_currency_from_firebase(self):
        """Firebaseから通貨単位を取得"""
        try:
            ref = db.reference('CURRENCY_NAME')
            currency = ref.get()
            return currency if currency else "星"
        except:
            return "星"

    def add_player_money(self, user_id, amount):
        """Firebaseに書き込む（エコノミー連携はFirebaseのみに簡素化）"""
        try:
            print(f"🔍 [DEBUG] add_player_money 開始: user_id={user_id}, amount={amount}")
            
            # 1日の上限チェック
            today_earned = self.get_today_gold_earned(user_id)
            print(f"🔍 [DEBUG] 今日の獲得済み: {today_earned}")
            
            if today_earned >= self.daily_gold_limit:
                print(f"🔍 [DEBUG] デイリー上限到達")
                return False, "daily_limit"
            
            # 1回の戦闘での上限チェック
            actual_amount = min(amount, self.battle_gold_limit)
            remaining_daily = self.daily_gold_limit - today_earned
            if actual_amount > remaining_daily:
                actual_amount = remaining_daily
            
            if actual_amount <= 0:
                print(f"🔍 [DEBUG] actual_amount <= 0")
                return False, "daily_limit"
            
            print(f"🔍 [DEBUG] actual_amount: {actual_amount}")
            
            # ユーザーのパスワードを取得
            auth_path = "user_auth.json"
            print(f"🔍 [DEBUG] auth_path: {auth_path}, exists: {os.path.exists(auth_path)}")
            
            if not os.path.exists(auth_path):
                print("❌ user_auth.jsonが見つかりません")
                return False, 0
            
            with open(auth_path, 'r', encoding='utf-8') as f:
                auth_data = json.load(f)
            
            uid = str(user_id)
            password = auth_data.get(uid)
            print(f"🔍 [DEBUG] uid={uid}, password={password}")
            
            if not password:
                print(f"❌ ユーザー {user_id} のパスワードが見つかりません")
                return False, 0
            
            # ===== Firebaseに書き込む =====
            ref = db.reference(f'USER_PROFILES/{password}')
            current_data = ref.get()
            print(f"🔍 [DEBUG] Firebase current_data: {current_data}")
            
            if not current_data:
                print(f"❌ Firebaseにユーザーデータが見つかりません")
                return False, 0
            
            current_money = current_data.get('money', 0)
            new_money = current_money + actual_amount
            
            print(f"🔍 [DEBUG] current_money={current_money}, new_money={new_money}")
            
            ref.update({
                'money': new_money,
                'daily_gold_earned': today_earned + actual_amount
            })
            
            print(f"💰 {user_id} に {actual_amount} 追加！ 新残高: {new_money}")
            return True, actual_amount
            
        except Exception as e:
            print(f"❌ Firebase直接書き込みエラー: {e}")
            import traceback
            traceback.print_exc()
            return False, 0

    def remove_player_money(self, user_id, amount):
        """Firebaseから直接お金を減らす"""
        try:
            auth_path = "user_auth.json"
            if not os.path.exists(auth_path):
                return False
            
            with open(auth_path, 'r', encoding='utf-8') as f:
                auth_data = json.load(f)
            
            uid = str(user_id)
            password = auth_data.get(uid)
            if not password:
                return False
            
            # ===== Firebaseから減らす =====
            ref = db.reference(f'USER_PROFILES/{password}')
            current_data = ref.get()
            
            if not current_data:
                return False
            
            current_money = current_data.get('money', 0)
            if current_money < amount:
                return False
            
            new_money = current_money - amount
            ref.update({'money': new_money})
            
            print(f"💰 {user_id} から {amount} 減少！ 新残高: {new_money}")
            return True
            
        except Exception as e:
            print(f"❌ Firebase直接書き込みエラー: {e}")
            return False

    def load_equipment_stats(self):
        """装備ステータスを読み込む"""
        if hasattr(self.cog, 'equipment_system') and self.cog.equipment_system:
            bonus, elements, equipment_list = self.cog.equipment_system.get_player_equipment_stats(self.interaction.user.id)
            self.equipment_bonus = bonus
            self.player_elements = elements
            
            # 装備から耐性を収集
            for item in equipment_list:
                if item.get("element_resist"):
                    if isinstance(item["element_resist"], list):
                        self.player_resists.extend(item["element_resist"])
                    else:
                        self.player_resists.append(item["element_resist"])
            
            # 装備中のアイテム名を取得
            equipment = self.player.get("equipment", {})
            for slot, item_id in equipment.items():
                if item_id:
                    item = self.cog.equipment_system.get_equipment_by_id(item_id)
                    if item:
                        slot_name = {"weapon": "武器", "armor": "防具", "accessory": "アクセサリー"}
                        self.equipment_names[slot] = f"{item['emoji']} {item['name']}"
                        if item.get("element"):
                            self.equipment_names[slot] += f" [{item['element']}]"

    def load_spells(self):
        spells_path = "cogs/rpg/data/spells.json"
        if os.path.exists(spells_path):
            with open(spells_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def load_items(self):
        items_path = "cogs/rpg/data/items.json"
        if os.path.exists(items_path):
            with open(items_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def create_hp_bar(self, current, max_hp, length=15):
        percent = current / max_hp if max_hp > 0 else 0
        filled = int(length * percent)
        bar = "█" * filled + "░" * (length - filled)
        return f"`{bar}` {int(percent * 100)}%"

    def get_element_icon(self, element):
        icons = {
            "fire": "🔥", "water": "💧", "ice": "❄️", "thunder": "⚡",
            "wind": "🌪️", "earth": "🪨", "rock": "🪨", "wood": "🌿",
            "light": "✨", "dark": "🌑", "poison": "☠️"
        }
        return icons.get(element, "❓")

    def calculate_damage(self, attacker, defender, is_physical=True, power=1.0):
        # 攻撃者の情報
        if attacker == self.player:
            actual_atk = attacker.get("atk", 10) + self.equipment_bonus.get("atk", 0)
            actual_mag = attacker.get("mag", 10) + self.equipment_bonus.get("mag", 0)
            actual_agi = attacker.get("agi", 10) + self.equipment_bonus.get("agi", 0)
            attacker_elements = self.player_elements
        else:
            actual_atk = attacker.get("atk", 10)
            actual_mag = attacker.get("mag", 10)
            actual_agi = attacker.get("agi", 10)
            attacker_elements = []
            if attacker.get("element"):
                attacker_elements = [attacker.get("element")]
        
        # 防御側の情報
        if defender == self.player:
            actual_def = defender.get("def", 10) + self.equipment_bonus.get("def", 0)
            actual_mdef = defender.get("mag", 10) + self.equipment_bonus.get("mag", 0)
            defender_element = None
            defender_resists = self.player_resists
            defender_weaknesses = []
        else:
            actual_def = defender.get("def", 10)
            actual_mdef = defender.get("mag", 10)
            defender_element = defender.get("element")
            defender_resists = defender.get("element_resist", [])
            if isinstance(defender_resists, str):
                defender_resists = [defender_resists]
            defender_weaknesses = defender.get("element_weak", [])
            if isinstance(defender_weaknesses, str):
                defender_weaknesses = [defender_weaknesses]

        # 命中率計算
        hit_rate = 0.95
        hit_rate += (actual_agi - defender.get("agi", 10)) * 0.005
        hit_rate += (attacker.get("luk", 10) - defender.get("luk", 10)) * 0.003
        hit_rate = max(0.7, min(0.98, hit_rate))

        if random.random() > hit_rate:
            return 0, False, "回避", 1.0, ""

        # 会心率計算
        crit_rate = 0.05 + (attacker.get("luk", 10) * 0.005)
        crit_rate = min(0.3, crit_rate)
        is_critical = random.random() < crit_rate
        self.critical_hit = is_critical

        # 基本ダメージ計算
        if is_physical:
            base_damage = actual_atk * 2 - actual_def * 1.5
        else:
            base_damage = actual_mag * 2 - actual_mdef * 1.2

        # バフ補正
        if is_physical:
            atk_buff = attacker.get("atk_buff", 0)
            def_buff = defender.get("def_buff", 0)
            base_damage *= (1 + atk_buff * 0.1)
            base_damage *= (1 - def_buff * 0.1)
        else:
            mag_buff = attacker.get("mag_buff", 0)
            mdef_buff = defender.get("mdef_buff", 0)
            base_damage *= (1 + mag_buff * 0.1)
            base_damage *= (1 - mdef_buff * 0.1)

        # ランダム補正
        random_factor = random.uniform(0.85, 1.15)
        defend_factor = 0.5 if defender.get("defending", False) else 1.0
        status_factor = 1.0
        if "sleep" in defender.get("status", []):
            status_factor = 2.0
        if "burn" in attacker.get("status", []):
            power *= 0.5
        crit_factor = 1.5 if is_critical else 1.0

        damage = max(1, int(base_damage * random_factor * defend_factor * status_factor * crit_factor * power))
        
        # 属性相性計算（拡張版）
        element_multiplier = 1.0
        element_message = ""
        if hasattr(self.cog, 'equipment_system') and self.cog.equipment_system and attacker_elements:
            attacker_element = attacker_elements[0] if attacker_elements else None
            damage, element_multiplier, element_message = self.cog.equipment_system.calculate_element_damage(
                attacker_element,
                defender_element,
                defender_resists,
                defender_weaknesses,
                damage
            )
        
        return damage, is_critical, "命中", element_multiplier, element_message

    def get_status_text(self, status_list):
        if not status_list:
            return ""
        icons = {"poison": "☠️", "paralysis": "⚡", "sleep": "😴", "burn": "🔥", "freeze": "❄️", "curse": "👻"}
        texts = [icons.get(s, "❓") for s in status_list]
        return f" ({''.join(texts)})"

    def create_embed(self):
        embed = discord.Embed(
            title=f"⚔️ {self.enemy['name']} との戦闘 ⚔️",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=self.enemy.get("image_url", ""))

        # 敵情報（属性表示追加）
        enemy_element_text = ""
        if self.enemy.get("element"):
            element_icon = self.get_element_icon(self.enemy["element"])
            enemy_element_text = f" {element_icon} [{self.enemy['element']}]"
        
        enemy_hp_bar = self.create_hp_bar(self.enemy_hp, self.enemy["max_hp"])
        embed.add_field(
            name=f"🦴 Lv.{self.enemy['level']} {self.enemy['name']}{enemy_element_text}{self.get_status_text(self.enemy_status)}",
            value=f"❤️ {self.enemy_hp}/{self.enemy['max_hp']}\n{enemy_hp_bar}",
            inline=False
        )

        # 装備情報を表示
        equipment_text = f"🗡️ {self.equipment_names['weapon']}\n🛡️ {self.equipment_names['armor']}\n💍 {self.equipment_names['accessory']}"
        
        # 装備ボーナスがある場合
        bonus_text = ""
        if any(self.equipment_bonus.values()):
            bonus_parts = []
            if self.equipment_bonus.get('atk', 0) > 0:
                bonus_parts.append(f"⚔️+{self.equipment_bonus['atk']}")
            if self.equipment_bonus.get('def', 0) > 0:
                bonus_parts.append(f"🛡️+{self.equipment_bonus['def']}")
            if self.equipment_bonus.get('mag', 0) > 0:
                bonus_parts.append(f"🔮+{self.equipment_bonus['mag']}")
            if self.equipment_bonus.get('agi', 0) > 0:
                bonus_parts.append(f"💨+{self.equipment_bonus['agi']}")
            if bonus_parts:
                bonus_text = f"\n✨ 装備ボーナス: {', '.join(bonus_parts)}"

        player_hp_bar = self.create_hp_bar(self.player_hp, self.player["max_hp"] + self.equipment_bonus.get("hp", 0))
        player_mp_bar = self.create_hp_bar(self.player.get("mp", 0), self.player.get("max_mp", 20) + self.equipment_bonus.get("mp", 0))
        job_name = self.player.get("job", "なし")
        
        # プレイヤーの属性表示
        player_element_text = ""
        if self.player_elements:
            element_icon = self.get_element_icon(self.player_elements[0])
            player_element_text = f" {element_icon} [{self.player_elements[0]}]"
        
        # 装備込みのステータス表示
        total_atk = self.player.get("atk", 0) + self.equipment_bonus.get("atk", 0)
        total_def = self.player.get("def", 0) + self.equipment_bonus.get("def", 0)
        total_mag = self.player.get("mag", 0) + self.equipment_bonus.get("mag", 0)
        total_agi = self.player.get("agi", 0) + self.equipment_bonus.get("agi", 0)

        embed.add_field(
            name=f"👤 {self.player['name']} (Lv.{self.player['level']}) - {job_name}{player_element_text}{self.get_status_text(self.player_status)}",
            value=(
                f"🔰 **装備**\n{equipment_text}{bonus_text}\n\n"
                f"❤️ {self.player_hp}/{self.player['max_hp'] + self.equipment_bonus.get('hp', 0)}\n{player_hp_bar}\n"
                f"✨ MP: {self.player.get('mp', 0)}/{self.player.get('max_mp', 20) + self.equipment_bonus.get('mp', 0)}\n{player_mp_bar}\n"
                f"⚔️ 攻撃力: {self.player.get('atk', 0)} → **{total_atk}**\n"
                f"🛡️ 防御力: {self.player.get('def', 0)} → **{total_def}**\n"
                f"🔮 魔法力: {self.player.get('mag', 0)} → **{total_mag}**\n"
                f"💨 素早さ: {self.player.get('agi', 0)} → **{total_agi}**\n"
                f"🍀 運: {self.player.get('luk', 0)}"
            ),
            inline=False
        )

        if self.battle_log:
            embed.add_field(name="📊 戦闘ログ", value="\n".join(self.battle_log[-5:]), inline=False)
        else:
            embed.add_field(name="⚔️", value=f"{self.enemy['message']}", inline=False)

        return embed

    async def update_message(self):
        embed = self.create_embed()
        try:
            await self.interaction.edit_original_response(embed=embed, view=self)
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            pass

    async def show_spell_menu(self, interaction):
        player_spells = self.player.get("spells", [])
        if not player_spells:
            await interaction.response.send_message("❌ 覚えている魔法がありません！", ephemeral=True)
            return

        spells_data = self.load_spells()
        available_spells = {s: spells_data[s] for s in player_spells if s in spells_data}

        if not available_spells:
            await interaction.response.send_message("❌ 使用できる魔法がありません！", ephemeral=True)
            return

        view = SpellSelectView(self, available_spells)
        for spell_key, spell_data in available_spells.items():
            button = discord.ui.Button(
                label=f"{spell_data['name']} ({spell_data['mp_cost']}MP)",
                style=discord.ButtonStyle.primary,
                custom_id=f"spell_{spell_key}"
            )
            async def button_callback(interaction, s=spell_key, sd=spell_data):
                await self.cast_spell(interaction, s, sd)
            button.callback = button_callback
            view.add_item(button)

        embed = discord.Embed(title="✨ 魔法を選択", description="使用する魔法を選んでください", color=discord.Color.blue())
        await interaction.response.edit_message(embed=embed, view=view)

    async def show_item_menu(self, interaction):
        player_items = self.player.get("items", {})
        if not player_items:
            await interaction.response.send_message("❌ アイテムを持っていません！", ephemeral=True)
            return

        items_data = self.load_items()
        available_items = {k: v for k, v in items_data.items() if k in player_items and player_items[k] > 0}

        if not available_items:
            await interaction.response.send_message("❌ 使用できるアイテムがありません！", ephemeral=True)
            return

        view = ItemSelectView(self, available_items)
        for item_key, item_data in available_items.items():
            button = discord.ui.Button(
                label=f"{item_data['name']} ({player_items[item_key]}個)",
                style=discord.ButtonStyle.success,
                custom_id=f"item_{item_key}"
            )
            async def button_callback(interaction, k=item_key, d=item_data):
                await self.use_item(interaction, k, d)
            button.callback = button_callback
            view.add_item(button)

        embed = discord.Embed(title="🧪 アイテムを選択", description="使用するアイテムを選んでください", color=discord.Color.green())
        await interaction.response.edit_message(embed=embed, view=view)

    async def cast_spell(self, interaction, spell_key, spell_data):
        if self.turn != "player":
            await interaction.response.send_message("❌ あなたのターンではありません", ephemeral=True)
            return

        mp_cost = spell_data["mp_cost"]
        current_mp = self.player.get("mp", 0)

        if current_mp < mp_cost:
            await interaction.response.send_message(f"❌ MPが足りません！ (必要: {mp_cost}MP)", ephemeral=True)
            return

        self.player["mp"] = current_mp - mp_cost
        spell_type = spell_data["type"]
        message = ""

        if spell_type == "攻撃":
            damage, is_critical, hit_result, element_multiplier, element_message = self.calculate_damage(
                self.player, self.enemy, is_physical=False, power=spell_data.get("power", 10) / 10
            )
            if hit_result == "回避":
                message = f"🏃 **{self.enemy['name']}** は魔法を回避した！"
            else:
                self.enemy_hp -= damage
                crit_text = " 💥会心の一撃！" if is_critical else ""
                element_text = f" ({element_message})" if element_message and element_message != "通常" else ""
                message = f"✨ **{spell_data['name']}**！ {damage}ダメージ！{crit_text}{element_text}"
        elif spell_type == "回復":
            heal_amount = spell_data.get("power", 30)
            max_hp = self.player["max_hp"] + self.equipment_bonus.get("hp", 0)
            self.player_hp = min(self.player_hp + heal_amount, max_hp)
            message = f"💚 **{spell_data['name']}**！ {heal_amount}回復した！"
        elif spell_type == "状態異常":
            self.enemy_status.append("poison")
            message = f"☠️ **{spell_data['name']}**！ 敵に毒を付与した！"
        else:
            message = f"✨ **{spell_data['name']}**！ 効果を発動した！"

        self.battle_log.append(message)
        await self.update_message()

        if self.enemy_hp <= 0:
            await self.end_battle(True)
            return

        self.turn = "enemy"
        await self.enemy_turn()

    async def use_item(self, interaction, item_key, item_data):
        if self.turn != "player":
            await interaction.response.send_message("❌ あなたのターンではありません", ephemeral=True)
            return

        if "items" not in self.player:
            self.player["items"] = {}
        if self.player["items"].get(item_key, 0) <= 0:
            await interaction.response.send_message("❌ アイテムが足りません！", ephemeral=True)
            return

        self.player["items"][item_key] -= 1
        item_type = item_data["type"]
        message = ""

        if item_type == "回復":
            heal_hp = item_data.get("effect", {}).get("hp", 0)
            max_hp = self.player["max_hp"] + self.equipment_bonus.get("hp", 0)
            self.player_hp = min(self.player_hp + heal_hp, max_hp)
            message = f"💚 **{item_data['name']}** を使用！ {heal_hp}回復した！"
        elif item_type == "状態異常回復":
            cure = item_data.get("effect", {}).get("cure", [])
            for status in cure:
                if status in self.player_status:
                    self.player_status.remove(status)
            message = f"🌿 **{item_data['name']}** を使用！ 状態異常が治った！"
        else:
            message = f"🧪 **{item_data['name']}** を使用した！"

        self.battle_log.append(message)
        await self.update_message()

        self.turn = "enemy"
        await self.enemy_turn()

    async def end_battle(self, victory: bool):
        if victory:
            exp_gain = self.enemy["exp"]
            gold_gain = self.enemy["gold"]
            
            # 経験値追加
            self.player["exp"] += exp_gain
            
            # ゴールド追加（上限付きエコノミー連携）
            success, result = self.add_player_money(self.interaction.user.id, gold_gain)
            
            # ===== ドロップ処理 =====
            drop_results = []
            drop_items_path = "cogs/rpg/data/drop_items.json"
            
            print(f"🔍 [DEBUG] ドロップ処理開始 - enemy_key: {self.enemy_key}")
            print(f"🔍 [DEBUG] drop_items_path exists: {os.path.exists(drop_items_path)}")
            
            # プレイヤーデータを読み込み（保存は最後に1回だけ行う）
            players = self.cog.load_players()
            uid = str(self.interaction.user.id)
            print(f"🔍 [DEBUG] プレイヤーUID: {uid}")
            print(f"🔍 [DEBUG] プレイヤーデータ: {players.get(uid, {})}")
            
            if "materials" not in players[uid]:
                players[uid]["materials"] = {}
                print(f"🔍 [DEBUG] materialsフィールドを新規作成")
            
            if os.path.exists(drop_items_path):
                with open(drop_items_path, 'r', encoding='utf-8') as f:
                    drop_data = json.load(f)
                
                enemy_drops = drop_data.get("enemy_drops", {}).get(self.enemy_key, {})
                drops = enemy_drops.get("drops", [])
                print(f"🔍 [DEBUG] 敵のドロップテーブル: {drops}")
                
                for drop in drops:
                    rate = drop["rate"]
                    roll = random.random()
                    print(f"🔍 [DEBUG] ドロップ判定: {drop['item']} 確率{rate} 結果{roll}")
                    
                    if roll < rate:
                        quantity = random.randint(drop["min"], drop["max"])
                        print(f"🔍 [DEBUG] ドロップ成功！ {drop['item']} ×{quantity}")
                        
                        # 素材を追加（playersに直接反映）
                        current = players[uid]["materials"].get(drop["item"], 0)
                        players[uid]["materials"][drop["item"]] = current + quantity
                        print(f"🔍 [DEBUG] 素材追加後: {players[uid]['materials']}")
                        
                        material_data = drop_data.get("materials", {}).get(drop["item"], {})
                        rank_emoji = {"S": "🟧", "A": "🟣", "B": "🔵", "C": "🟢"}.get(material_data.get("rank", "C"), "⚪")
                        drop_results.append(f"{rank_emoji} {material_data.get('name', drop['item'])} ×{quantity}")
                    else:
                        print(f"🔍 [DEBUG] ドロップ失敗: {drop['item']}")
            else:
                print(f"🔍 [DEBUG] drop_items.json が見つかりません！")
            
            # 戦闘後のプレイヤーデータを更新
            self.player["hp"] = self.player_hp
            self.player["mp"] = self.player.get("mp", 0)

            level_up = False
            old_level = self.player["level"]
            while self.player["exp"] >= self.player["level"] * 100:
                self.player["exp"] -= self.player["level"] * 100
                self.player["level"] += 1
                self.player["max_hp"] += 10
                self.player["max_mp"] += 5
                self.player["atk"] += 3
                self.player["def"] += 2
                self.player["mag"] = self.player.get("mag", 5) + 2
                self.player["agi"] = self.player.get("agi", 8) + 2
                self.player["luk"] = self.player.get("luk", 8) + 1
                self.player["hp"] = self.player["max_hp"]
                self.player["mp"] = self.player["max_mp"]
                level_up = True

            # ★★★ 修正箇所 ★★★
            # materials を保持したまま players を更新
            original_materials = players[uid].get("materials", {}).copy()
            players[uid] = self.player
            players[uid]["materials"] = original_materials  # ドロップで増えた分を戻す
            # ★★★ 修正ここまで ★★★
            
            # ★★★★★ ここで1回だけ保存（ドロップ + レベルアップ反映済み） ★★★★★
            self.cog.save_players(players)
            print(f"🔍 [DEBUG] プレイヤーデータ保存完了（ドロップ + レベルアップ反映）")
            print(f"🔍 [DEBUG] 保存後確認: materials = {players[uid].get('materials', {})}")

            if hasattr(self.cog, 'after_battle') and self.enemy_key:
                await self.cog.after_battle(self.interaction, self.enemy_key, True, self.enemy.get("level", 1))

            currency = self.get_currency_from_firebase()
            
            embed = discord.Embed(title="🏆 勝利！", color=discord.Color.gold())
            embed.set_thumbnail(url=self.enemy.get("image_url", ""))
            embed.add_field(name="✨ 獲得経験値", value=f"+{exp_gain} EXP", inline=True)
            
            if success:
                actual_gold = result
                if actual_gold < gold_gain:
                    embed.add_field(name="💰 獲得金額", value=f"+{actual_gold}{currency}\n*(上限により {gold_gain - actual_gold}{currency} カット)*", inline=True)
                else:
                    embed.add_field(name="💰 獲得金額", value=f"+{actual_gold}{currency}", inline=True)
            else:
                if result == "daily_limit":
                    embed.add_field(name="💰 獲得金額", value=f"0{currency}\n*(本日の上限に達しました)*", inline=True)
                else:
                    embed.add_field(name="💰 獲得金額", value=f"+{gold_gain}{currency}", inline=True)
            
            if drop_results:
                embed.add_field(name="🎁 入手素材", value="\n".join(drop_results), inline=False)
            
            if level_up:
                embed.add_field(name="🎉 レベルアップ！", value=f"Lv.{old_level} → **Lv.{self.player['level']}**", inline=False)
            embed.add_field(name="📊 戦闘ログ", value="\n".join(self.battle_log[-5:]), inline=False)
            await self.interaction.edit_original_response(embed=embed, view=None)

        else:
            # 敗北時はペナルティ（所持金の10%減額、最大1000）
            current_money = self.get_player_money_from_firebase(self.interaction.user.id)
            penalty = min(int(current_money * 0.1), 1000)
            if penalty > 0:
                self.remove_player_money(self.interaction.user.id, penalty)
            
            self.player["hp"] = self.player["max_hp"]
            self.player["mp"] = self.player["max_mp"]
            players = self.cog.load_players()
            players[str(self.interaction.user.id)] = self.player
            self.cog.save_players(players)
            
            if hasattr(self.cog, 'after_battle') and self.enemy_key:
                await self.cog.after_battle(self.interaction, self.enemy_key, False, self.enemy.get("level", 1))
            
            currency = self.get_currency_from_firebase()
            penalty_text = f"\n💰 {penalty}{currency} 失った..." if penalty > 0 else ""
            embed = discord.Embed(title="💀 敗北...", description=f"宿屋で全回復した。{penalty_text}", color=discord.Color.red())
            await self.interaction.edit_original_response(embed=embed, view=None)

    async def player_turn(self, action: str):
        if self.turn != "player":
            return

        message = ""

        if action == "attack":
            damage, is_critical, hit_result, element_multiplier, element_message = self.calculate_damage(self.player, self.enemy, is_physical=True)
            if hit_result == "回避":
                message = f"🏃 **{self.enemy['name']}** は攻撃を回避した！"
            else:
                self.enemy_hp -= damage
                crit_text = " 💥会心の一撃！" if is_critical else ""
                element_text = f" ({element_message})" if element_message and element_message != "通常" else ""
                message = f"⚔️ **{self.player['name']}** の攻撃！ {damage}ダメージ！{crit_text}{element_text}"
        elif action == "defend":
            self.defending = True
            message = f"🛡️ **{self.player['name']}** は防御態勢をとった！"
        elif action == "escape":
            escape_rate = 0.3 + (self.player["level"] - self.enemy["level"]) * 0.1
            if random.random() < escape_rate:
                await self.end_battle(False)
                return
            else:
                message = f"🏃 逃げられなかった！"

        self.battle_log.append(message)

        if self.enemy_hp <= 0:
            await self.end_battle(True)
            return

        await self.update_message()
        self.turn = "enemy"
        await self.enemy_turn()

    async def enemy_turn(self):
        damage, is_critical, hit_result, element_multiplier, element_message = self.calculate_damage(self.enemy, self.player, is_physical=True)

        if hit_result == "回避":
            message = f"🏃 **{self.player['name']}** は攻撃を回避した！"
        else:
            if self.defending:
                damage = damage // 2
                message = f"🛡️ 防御したが、{damage}ダメージを受けた！"
                self.defending = False
            else:
                crit_text = " 💥会心の一撃！" if is_critical else ""
                element_text = f" ({element_message})" if element_message and element_message != "通常" else ""
                message = f"💥 **{self.enemy['name']}** の攻撃！ {damage}ダメージ！{crit_text}{element_text}"
            self.player_hp -= damage

        self.battle_log.append(message)
        await self.update_message()

        if self.player_hp <= 0:
            await self.end_battle(False)
            return

        self.turn = "player"
        await self.update_message()

    @discord.ui.button(label="⚔️ 攻撃", style=discord.ButtonStyle.danger, emoji="⚔️", row=0)
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("❌ あなたの戦闘ではありません", ephemeral=True)
        await interaction.response.defer()
        await self.player_turn("attack")

    @discord.ui.button(label="🛡️ 防御", style=discord.ButtonStyle.secondary, emoji="🛡️", row=0)
    async def defend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("❌ あなたの戦闘ではありません", ephemeral=True)
        await interaction.response.defer()
        await self.player_turn("defend")

    @discord.ui.button(label="🏃 逃げる", style=discord.ButtonStyle.secondary, emoji="🏃", row=1)
    async def escape_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("❌ あなたの戦闘ではありません", ephemeral=True)
        await interaction.response.defer()
        await self.player_turn("escape")

    @discord.ui.button(label="✨ 魔法", style=discord.ButtonStyle.primary, emoji="✨", row=1)
    async def magic_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("❌ あなたの戦闘ではありません", ephemeral=True)
        await self.show_spell_menu(interaction)

    @discord.ui.button(label="🧪 アイテム", style=discord.ButtonStyle.success, emoji="🧪", row=1)
    async def item_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("❌ あなたの戦闘ではありません", ephemeral=True)
        await self.show_item_menu(interaction)


async def start_battle(cog, interaction, enemy_data):
    players = cog.load_players()
    uid = str(interaction.user.id)
    player = players[uid]

    if "items" not in player:
        player["items"] = {"potion": 3}
        players[uid] = player
        cog.save_players(players)

    view = BattleView(cog, interaction, player, enemy_data)
    
    enemies = cog.load_enemies()
    for key, data in enemies.items():
        if data.get("name") == enemy_data.get("name"):
            view.enemy_key = key
            break
    
    embed = view.create_embed()

    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, view=view)
    else:
        await interaction.response.send_message(embed=embed, view=view)
    return view


async def start_battle_ephemeral(cog, interaction, enemy_data):
    """エピメラル戦闘を開始（同じinteraction内で完結、自分だけに見える）"""
    players = cog.load_players()
    uid = str(interaction.user.id)
    player = players[uid]

    if "items" not in player:
        player["items"] = {"potion": 3}
        players[uid] = player
        cog.save_players(players)

    view = BattleView(cog, interaction, player, enemy_data)
    
    enemies = cog.load_enemies()
    for key, data in enemies.items():
        if data.get("name") == enemy_data.get("name"):
            view.enemy_key = key
            break
    
    embed = view.create_embed()
    
    await interaction.edit_original_response(embed=embed, view=view)
    return view


async def setup(bot):
    # このファイルはBattleViewなどのクラスを提供するモジュールです
    pass