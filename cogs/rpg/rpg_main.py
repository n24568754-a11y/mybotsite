import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
from . import rpg_battle
from . import rpg_walk
from firebase_admin import db

class RPG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_path = "cogs/rpg/data/players.json"
        self.enemies_path = "cogs/rpg/data/enemies.json"
        self.areas_path = "cogs/rpg/data/areas.json"
        self.world_map_path = "cogs/rpg/data/world_map.json"
        self.jobs_path = "cogs/rpg/data/jobs.json"
        self._ensure_files()
        
        # ストーリーシステムとクエストボードのインスタンスを保持
        self.story_system = None
        self.quest_board = None
        self.equipment_system = None
        self.craft_system = None
    
    def get_economy(self):
        """エコノミーCogを取得"""
        return self.bot.get_cog("Economy")
    
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
        economy = self.get_economy()
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
        
        economy = self.get_economy()
        if economy:
            return economy.currency
        
        return "星"
    
    def add_player_money(self, user_id, amount):
        """プレイヤーにお金を追加（エコノミーシステム）"""
        economy = self.get_economy()
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
    
    def remove_player_money(self, user_id, amount):
        """プレイヤーからお金を減らす（エコノミーシステム）"""
        if self.get_player_money(user_id) >= amount:
            economy = self.get_economy()
            if economy:
                data = economy.load_data()
                uid = str(user_id)
                data[uid]['money'] -= amount
                economy.save_data(data)
                economy.update_web_data()
                return True
        return False
    
    async def cog_load(self):
        """Cogがロードされた時に実行"""
        # ストーリーシステムとクエストボードと装備システムを取得
        self.story_system = self.bot.get_cog("StorySystem")
        self.quest_board = self.bot.get_cog("QuestBoard")
        self.equipment_system = self.bot.get_cog("EquipmentSystem")
        self.craft_system = self.bot.get_cog("CraftSystem")
        self.admin_creator = self.bot.get_cog("AdminCreator")  # ← 追加
        
        print(f"🔍 [DEBUG] craft_system = {self.craft_system}")
        print(f"🔍 [DEBUG] admin_creator = {self.admin_creator}")
        
        # 新規プレイヤーのクエスト初期化
        if self.quest_board:
            players = self.load_players()
            for uid in players:
                self.quest_board.init_player_quests(int(uid))
                print(f"✅ プレイヤー {uid} のクエストデータを初期化")
        
        # エコノミーシステムと同期（RPGプレイヤーをエコノミーに登録）
        economy = self.get_economy()
        if economy:
            data = economy.load_data()
            players = self.load_players()
            updated = False
            for uid in players:
                if uid not in data:
                    data[uid] = economy.get_default_user_data()
                    updated = True
                    print(f"✅ プレイヤー {uid} をエコノミーシステムに登録")
            if updated:
                economy.save_data(data)
                economy.update_web_data()

    def _ensure_files(self):
        """データファイルが存在することを確認"""
        # players.json
        if not os.path.exists(self.data_path):
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2)
        else:
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError:
                with open(self.data_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, indent=2)

        # enemies.json
        if not os.path.exists(self.enemies_path):
            default_enemies = {
                "slime": {
                    "name": "スライム",
                    "image_url": "https://game-icons.net/icons/ffffff/000000/1x1/delapouite/slime.svg",
                    "level": 1, "hp": 20, "max_hp": 20,
                    "atk": 8, "def": 5, "exp": 10, "gold": 5,
                    "message": "ぷにぷにした体で体当たりしてきた！"
                },
                "goblin": {
                    "name": "ゴブリン",
                    "image_url": "https://game-icons.net/icons/ffffff/000000/1x1/lorc/goblin-head.svg",
                    "level": 3, "hp": 45, "max_hp": 45,
                    "atk": 15, "def": 8, "exp": 25, "gold": 15,
                    "message": "ゲヘヘ… 金目のものをよこせ！"
                },
                "wolf": {
                    "name": "ウルフ",
                    "image_url": "https://game-icons.net/icons/ffffff/000000/1x1/lorc/wolf-head.svg",
                    "level": 5, "hp": 65, "max_hp": 65,
                    "atk": 22, "def": 12, "exp": 45, "gold": 30,
                    "message": "遠吠えが聞こえる… 襲いかかってきた！"
                },
                "bat": {
                    "name": "コウモリ",
                    "image_url": "https://game-icons.net/icons/ffffff/000000/1x1/lorc/bat.svg",
                    "level": 4, "hp": 35, "max_hp": 35,
                    "atk": 18, "def": 8, "exp": 30, "gold": 20,
                    "message": "キィッ！ 鋭い爪で襲いかかってきた！"
                },
                "scorpion": {
                    "name": "サソリ",
                    "image_url": "https://game-icons.net/icons/ffffff/000000/1x1/lorc/scorpion.svg",
                    "level": 8, "hp": 70, "max_hp": 70,
                    "atk": 28, "def": 15, "exp": 60, "gold": 40,
                    "message": "毒針を振りかざして襲いかかってきた！"
                },
                "crab": {
                    "name": "クラブ",
                    "image_url": "https://game-icons.net/icons/ffffff/000000/1x1/lorc/crab.svg",
                    "level": 10, "hp": 85, "max_hp": 85,
                    "atk": 25, "def": 20, "exp": 75, "gold": 50,
                    "message": "大きなハサミで挟もうとしている！"
                },
                "fishman": {
                    "name": "フィッシュマン",
                    "image_url": "https://game-icons.net/icons/ffffff/000000/1x1/lorc/fish-monster.svg",
                    "level": 12, "hp": 100, "max_hp": 100,
                    "atk": 32, "def": 18, "exp": 90, "gold": 60,
                    "message": "ぬめぬめした体で襲いかかってきた！"
                }
            }
            with open(self.enemies_path, 'w', encoding='utf-8') as f:
                json.dump(default_enemies, f, indent=2, ensure_ascii=False)
        else:
            try:
                with open(self.enemies_path, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError:
                with open(self.enemies_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, indent=2)

        # areas.json
        if not os.path.exists(self.areas_path):
            default_areas = {
                "草原": {
                    "name": "🌿 草原",
                    "level_range": [1, 3],
                    "enemies": ["slime", "goblin"],
                    "encounter_rate": 0.12,
                    "description": "のどかな草原。スライムやゴブリンが現れる。",
                    "color": 5777400
                },
                "森林": {
                    "name": "🌲 森林",
                    "level_range": [3, 6],
                    "enemies": ["goblin", "wolf"],
                    "encounter_rate": 0.15,
                    "description": "薄暗い森。ゴブリンやウルフが潜んでいる。",
                    "color": 3383603
                },
                "村": {
                    "name": "🏘️ 村",
                    "level_range": [1, 99],
                    "enemies": [],
                    "encounter_rate": 0,
                    "description": "平和な村。宿屋やショップがある。",
                    "color": 16755027
                },
                "街": {
                    "name": "🏙️ 街",
                    "level_range": [1, 99],
                    "enemies": [],
                    "encounter_rate": 0,
                    "description": "賑やかな商業都市。",
                    "color": 16755027
                },
                "城": {
                    "name": "🏰 城",
                    "level_range": [5, 99],
                    "enemies": [],
                    "encounter_rate": 0,
                    "description": "王都。国王がいる。",
                    "color": 16755027
                },
                "山": {
                    "name": "⛰️ 山",
                    "level_range": [5, 9],
                    "enemies": ["wolf", "bat"],
                    "encounter_rate": 0.18,
                    "description": "険しい山道。",
                    "color": 11184810
                },
                "洞窟": {
                    "name": "🕳️ 洞窟",
                    "level_range": [7, 12],
                    "enemies": ["bat", "goblin"],
                    "encounter_rate": 0.2,
                    "description": "暗く湿った洞窟。",
                    "color": 8947914
                },
                "砂漠": {
                    "name": "🏜️ 砂漠",
                    "level_range": [8, 15],
                    "enemies": ["wolf", "scorpion"],
                    "encounter_rate": 0.16,
                    "description": "灼熱の砂漠。",
                    "color": 16755027
                },
                "海岸": {
                    "name": "🏖️ 海岸",
                    "level_range": [10, 18],
                    "enemies": ["crab", "fishman"],
                    "encounter_rate": 0.14,
                    "description": "潮風が吹き抜ける海岸。",
                    "color": 4507391
                }
            }
            with open(self.areas_path, 'w', encoding='utf-8') as f:
                json.dump(default_areas, f, indent=2, ensure_ascii=False)

        # world_map.json
        if not os.path.exists(self.world_map_path):
            default_world_map = {
                "width": 10,
                "height": 10,
                "grid": [
                    ["砂漠", "砂漠", "砂漠", "砂漠", "草原", "草原", "海岸", "海岸", "海岸", "海岸"],
                    ["砂漠", "砂漠", "砂漠", "草原", "草原", "草原", "海岸", "海岸", "海岸", "海岸"],
                    ["砂漠", "砂漠", "草原", "草原", "草原", "草原", "海岸", "海岸", "海岸", "海岸"],
                    ["砂漠", "草原", "草原", "村", "村", "草原", "草原", "海岸", "海岸", "海岸"],
                    ["草原", "草原", "草原", "村", "街", "草原", "草原", "森林", "海岸", "海岸"],
                    ["草原", "草原", "草原", "街", "城", "街", "草原", "森林", "森林", "山"],
                    ["草原", "草原", "草原", "街", "街", "草原", "森林", "森林", "山", "山"],
                    ["草原", "草原", "草原", "草原", "草原", "森林", "森林", "山", "山", "洞窟"],
                    ["草原", "草原", "草原", "草原", "森林", "森林", "山", "山", "洞窟", "洞窟"],
                    ["草原", "草原", "草原", "草原", "森林", "山", "山", "洞窟", "洞窟", "洞窟"]
                ]
            }
            with open(self.world_map_path, 'w', encoding='utf-8') as f:
                json.dump(default_world_map, f, indent=2, ensure_ascii=False)

        # jobs.json
        if not os.path.exists(self.jobs_path):
            default_jobs = {
                "戦士": {
                    "name": "⚔️ 戦士",
                    "description": "高い攻撃力と防御力を持つ前衛職",
                    "base_stats": {"hp": 60, "mp": 15, "atk": 15, "def": 12, "mag": 5, "agi": 8, "luk": 8},
                    "growth": {"hp": 12, "mp": 2, "atk": 4, "def": 3, "mag": 1, "agi": 2, "luk": 1},
                    "starting_skills": ["通常攻撃", "かばう"],
                    "starting_spells": []
                },
                "魔法使い": {
                    "name": "🔮 魔法使い",
                    "description": "強力な魔法で敵を殲滅する後衛職",
                    "base_stats": {"hp": 40, "mp": 30, "atk": 8, "def": 6, "mag": 18, "agi": 10, "luk": 8},
                    "growth": {"hp": 6, "mp": 8, "atk": 1, "def": 1, "mag": 5, "agi": 2, "luk": 1},
                    "starting_skills": ["通常攻撃"],
                    "starting_spells": ["ファイア"]
                },
                "盗賊": {
                    "name": "🗡️ 盗賊",
                    "description": "素早さと運を活かした攻撃が特徴",
                    "base_stats": {"hp": 50, "mp": 20, "atk": 12, "def": 8, "mag": 6, "agi": 15, "luk": 15},
                    "growth": {"hp": 8, "mp": 4, "atk": 3, "def": 1, "mag": 1, "agi": 4, "luk": 3},
                    "starting_skills": ["通常攻撃", "スティール"],
                    "starting_spells": []
                },
                "僧侶": {
                    "name": "🙏 僧侶",
                    "description": "回復魔法と補助魔法を扱う",
                    "base_stats": {"hp": 55, "mp": 25, "atk": 10, "def": 10, "mag": 12, "agi": 8, "luk": 10},
                    "growth": {"hp": 9, "mp": 6, "atk": 2, "def": 2, "mag": 4, "agi": 1, "luk": 2},
                    "starting_skills": ["通常攻撃"],
                    "starting_spells": ["ヒール"]
                },
                "狩人": {
                    "name": "🏹 狩人",
                    "description": "高い命中率と状態異常攻撃が得意",
                    "base_stats": {"hp": 52, "mp": 18, "atk": 14, "def": 9, "mag": 7, "agi": 12, "luk": 10},
                    "growth": {"hp": 9, "mp": 4, "atk": 3, "def": 2, "mag": 2, "agi": 3, "luk": 2},
                    "starting_skills": ["通常攻撃", "毒矢"],
                    "starting_spells": []
                }
            }
            with open(self.jobs_path, 'w', encoding='utf-8') as f:
                json.dump(default_jobs, f, indent=2, ensure_ascii=False)

    def load_players(self):
        with open(self.data_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_players(self, data):
        import traceback
        import os
        
        # ===== スタックトレースを出力（どこから呼ばれたか特定） =====
        print("🔍 [DEBUG] ===== save_players 呼び出し元 =====")
        traceback.print_stack()
        print("🔍 [DEBUG] ===================================")
        
        abs_path = os.path.abspath(self.data_path)
        print(f"🔍 [DEBUG] save_players: 絶対パス = {abs_path}")
        print(f"🔍 [DEBUG] 保存する materials = {data.get('1368428956214100062', {}).get('materials', {})}")
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"🔍 [DEBUG] 保存完了")
        
        # 保存後すぐに読み込んで確認
        with open(self.data_path, 'r', encoding='utf-8') as f:
            check_data = json.load(f)
        print(f"🔍 [DEBUG] 保存後確認: materials = {check_data.get('1368428956214100062', {}).get('materials', {})}")

    def load_enemies(self):
        try:
            with open(self.enemies_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self._ensure_files()
            with open(self.enemies_path, 'r', encoding='utf-8') as f:
                return json.load(f)

    def load_areas(self):
        with open(self.areas_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_world_map(self):
        with open(self.world_map_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_jobs(self):
        with open(self.jobs_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def migrate_player_data(self, uid, player):
        """古いデータを新しい形式に移行"""
        modified = False
        if "x" not in player:
            loc_map = {"草原": (4, 5), "森林": (7, 5), "洞窟": (9, 8)}
            x, y = loc_map.get(player.get("location", "草原"), (4, 5))
            player["x"] = x
            player["y"] = y
            modified = True
        if "steps" not in player:
            player["steps"] = 0
            modified = True
        if "job" not in player:
            player["job"] = None
            modified = True
        if "mag" not in player:
            player["mag"] = 5
            modified = True
        if "agi" not in player:
            player["agi"] = 8
            modified = True
        if "luk" not in player:
            player["luk"] = 8
            modified = True
        if "skills" not in player:
            player["skills"] = ["通常攻撃"]
            modified = True
        if "spells" not in player:
            player["spells"] = []
            modified = True
        
        # 装備データの移行（新規追加）
        if "equipment" not in player:
            player["equipment"] = {"weapon": None, "armor": None, "accessory": None}
            modified = True
        
        if "inventory" not in player:
            player["inventory"] = {"items": {}, "equipment": []}
            modified = True
        elif "equipment" not in player["inventory"]:
            player["inventory"]["equipment"] = []
            modified = True
        
        # 古いgoldフィールドがあれば削除（もう使わない）
        if "gold" in player:
            del player["gold"]
            modified = True
        
        return modified

    async def after_move(self, interaction: discord.Interaction, x: int, y: int, area: str):
        """移動後の処理（ストーリートリガーチェックなど）"""
        # ストーリーイベントチェック
        if self.story_system:
            await self.story_system.check_location_trigger(interaction, x, y, area)
        
        # 歩数クエスト更新
        if self.quest_board:
            self.quest_board.update_progress(interaction.user.id, "walk", amount=1)

    async def after_battle(self, interaction: discord.Interaction, enemy_key: str, victory: bool, enemy_level: int = None):
        """戦闘後の処理"""
        if victory and self.quest_board:
            # 討伐クエスト更新
            self.quest_board.update_progress(interaction.user.id, "defeat", enemy_key, 1)
            
            # レベル条件討伐クエストのため、プレイヤーレベルもチェック
            players = self.load_players()
            uid = str(interaction.user.id)
            if uid in players:
                player_level = players[uid].get("level", 1)
                if enemy_level is None:
                    enemies = self.load_enemies()
                    if enemy_key in enemies:
                        enemy_level = enemies[enemy_key].get("level", 1)
                self.quest_board.update_progress(interaction.user.id, "defeat_min_level", None, 1, extra_data={"player_level": player_level, "enemy_level": enemy_level})

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"🎮 RPG Cog 準備完了")
        commands_list = [cmd.name for cmd in self.bot.tree.get_commands()]
        print(f"📋 登録コマンド: {commands_list}")

    @app_commands.command(name="rpg_sync", description="コマンドを強制同期する（管理者用）")
    @app_commands.default_permissions(administrator=True)
    async def rpg_sync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            self.bot.tree.copy_global_to(guild=interaction.guild)
            await self.bot.tree.sync(guild=interaction.guild)
            commands = [cmd.name for cmd in self.bot.tree.get_commands(guild=interaction.guild)]
            await interaction.followup.send(f"✅ 同期完了！\n登録済みコマンド: {', '.join(commands)}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ エラー: {e}", ephemeral=True)

    @app_commands.command(name="rpg_start", description="冒険を始める")
    async def rpg_start(self, interaction: discord.Interaction, 名前: str):
        await interaction.response.defer()
        players = self.load_players()
        uid = str(interaction.user.id)

        if uid in players:
            return await interaction.followup.send("❌ あなたは既に冒険者です！")

        players[uid] = {
            "name": 名前[:20],
            "job": None,
            "level": 1,
            "exp": 0,
            "hp": 50, "max_hp": 50,
            "mp": 20, "max_mp": 20,
            "atk": 10, "def": 5,
            "mag": 5, "agi": 8, "luk": 8,
            "skills": ["通常攻撃"],
            "spells": [],
            "x": 4,
            "y": 5,
            "steps": 0,
            "equipment": {"weapon": None, "armor": None, "accessory": None},
            "inventory": {"items": {}, "equipment": []}
        }
        self.save_players(players)
        
        # エコノミーシステムにも登録
        economy = self.get_economy()
        if economy:
            data = economy.load_data()
            if uid not in data:
                data[uid] = economy.get_default_user_data()
                economy.save_data(data)
                economy.update_web_data()
        
        # クエストデータを初期化
        if self.quest_board:
            self.quest_board.init_player_quests(interaction.user.id)

        embed = discord.Embed(
            title="🎉 冒険者登録完了！",
            description=f"ようこそ、**{名前}**！\nあなたの冒険が今始まります。\n職業は `/rpg_job` で選んでください。",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="rpg_job", description="職業を選択する")
    @app_commands.choices(職業=[
        app_commands.Choice(name="⚔️ 戦士", value="戦士"),
        app_commands.Choice(name="🔮 魔法使い", value="魔法使い"),
        app_commands.Choice(name="🗡️ 盗賊", value="盗賊"),
        app_commands.Choice(name="🙏 僧侶", value="僧侶"),
        app_commands.Choice(name="🏹 狩人", value="狩人")
    ])
    async def rpg_job(self, interaction: discord.Interaction, 職業: str):
        players = self.load_players()
        uid = str(interaction.user.id)

        if uid not in players:
            return await interaction.response.send_message("❌ `/rpg_start` で冒険者になりましょう！", ephemeral=True)

        if players[uid].get("job"):
            return await interaction.response.send_message(f"❌ あなたの職業は既に **{players[uid]['job']}** です。変更できません。", ephemeral=True)

        jobs = self.load_jobs()
        if 職業 not in jobs:
            return await interaction.response.send_message("❌ その職業は存在しません", ephemeral=True)

        job_data = jobs[職業]
        base = job_data["base_stats"]

        players[uid]["job"] = 職業
        players[uid]["max_hp"] = base["hp"]
        players[uid]["hp"] = base["hp"]
        players[uid]["max_mp"] = base["mp"]
        players[uid]["mp"] = base["mp"]
        players[uid]["atk"] = base["atk"]
        players[uid]["def"] = base["def"]
        players[uid]["mag"] = base["mag"]
        players[uid]["agi"] = base["agi"]
        players[uid]["luk"] = base["luk"]
        players[uid]["skills"] = job_data.get("starting_skills", [])
        players[uid]["spells"] = job_data.get("starting_spells", [])

        self.save_players(players)

        embed = discord.Embed(
            title="🌟 職業決定！",
            description=f"あなたは **{job_data['name']}** になった！\n{job_data['description']}",
            color=discord.Color.purple()
        )
        embed.add_field(name="❤️ HP", value=str(base["hp"]), inline=True)
        embed.add_field(name="✨ MP", value=str(base["mp"]), inline=True)
        embed.add_field(name="⚔️ 攻撃力", value=str(base["atk"]), inline=True)
        embed.add_field(name="🛡️ 防御力", value=str(base["def"]), inline=True)
        embed.add_field(name="🔮 魔法力", value=str(base["mag"]), inline=True)
        embed.add_field(name="💨 素早さ", value=str(base["agi"]), inline=True)
        embed.add_field(name="🍀 運", value=str(base["luk"]), inline=True)
        embed.add_field(name="✨ 覚えた魔法", value=", ".join(players[uid]["spells"]) if players[uid]["spells"] else "なし", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rpg_status", description="ステータスを確認")
    async def rpg_status(self, interaction: discord.Interaction):
        players = self.load_players()
        uid = str(interaction.user.id)

        if uid not in players:
            return await interaction.response.send_message("❌ `/rpg_start` で冒険者になりましょう！", ephemeral=True)

        p = players[uid]

        # 現在のエリアを取得
        world = self.load_world_map()
        areas = self.load_areas()
        x = p.get("x", 4)
        y = p.get("y", 5)
        area_key = world["grid"][y][x]
        current_area = areas.get(area_key, {"name": "🌿 草原"})

        # 装備ボーナスを取得
        equipment_bonus = {"atk": 0, "def": 0, "mag": 0, "agi": 0, "luk": 0, "hp": 0, "mp": 0}
        equipment_names = {"weapon": "なし", "armor": "なし", "accessory": "なし"}
        
        if self.equipment_system:
            bonus, elements, equipment_list = self.equipment_system.get_player_equipment_stats(interaction.user.id)
            equipment_bonus = bonus
            
            # 装備中のアイテム名を取得
            equipment = p.get("equipment", {})
            for slot, item_id in equipment.items():
                if item_id:
                    item = self.equipment_system.get_equipment_by_id(item_id)
                    if item:
                        slot_name = {"weapon": "武器", "armor": "防具", "accessory": "アクセサリー"}
                        equipment_names[slot] = f"{item['emoji']} {item['name']}"
                        if item.get("element"):
                            equipment_names[slot] += f" [{item['element']}]"

        # エコノミーシステムから所持金を取得（Firebase優先）
        player_money = self.get_player_money(interaction.user.id)
        currency = self.get_currency()

        # 装備込みのステータス計算
        total_atk = p['atk'] + equipment_bonus.get('atk', 0)
        total_def = p['def'] + equipment_bonus.get('def', 0)
        total_mag = p.get('mag', 5) + equipment_bonus.get('mag', 0)
        total_agi = p.get('agi', 8) + equipment_bonus.get('agi', 0)
        total_luk = p.get('luk', 8) + equipment_bonus.get('luk', 0)
        total_hp = p['hp']
        total_max_hp = p['max_hp'] + equipment_bonus.get('hp', 0)
        total_mp = p['mp']
        total_max_mp = p['max_mp'] + equipment_bonus.get('mp', 0)

        exp_needed = p['level'] * 100
        exp_percent = min(1.0, p['exp'] / exp_needed)
        bar_length = 15
        filled = int(bar_length * exp_percent)
        exp_bar = "█" * filled + "░" * (bar_length - filled)

        hp_percent = total_hp / total_max_hp if total_max_hp > 0 else 0
        hp_filled = int(bar_length * hp_percent)
        hp_bar = "█" * hp_filled + "░" * (bar_length - hp_filled)

        mp_percent = total_mp / total_max_mp if total_max_mp > 0 else 0
        mp_filled = int(bar_length * mp_percent)
        mp_bar = "█" * mp_filled + "░" * (bar_length - mp_filled)

        job_name = p.get("job", "未選択")

        # 装備情報の文字列作成
        equipment_text = f"🗡️ 武器: {equipment_names['weapon']}\n🛡️ 防具: {equipment_names['armor']}\n💍 アクセ: {equipment_names['accessory']}"

        embed = discord.Embed(
            title=f"📊 {p['name']} のステータス",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="職業", value=job_name, inline=True)
        embed.add_field(name="レベル", value=f"**Lv.{p['level']}**", inline=True)
        embed.add_field(name="経験値", value=f"{p['exp']}/{exp_needed}\n`{exp_bar}`", inline=True)
        embed.add_field(name="現在地", value=current_area["name"], inline=True)
        embed.add_field(name="📍 座標", value=f"({x}, {y})", inline=True)
        embed.add_field(name="🔰 装備", value=equipment_text, inline=False)
        embed.add_field(name="❤️ HP", value=f"{total_hp}/{total_max_hp}\n`{hp_bar}`", inline=False)
        embed.add_field(name="✨ MP", value=f"{total_mp}/{total_max_mp}\n`{mp_bar}`", inline=False)
        
        # 基本ステータスと装備ボーナスを分けて表示
        base_stats = f"⚔️ 攻撃力: {p['atk']}"
        if equipment_bonus.get('atk', 0) > 0:
            base_stats += f" +{equipment_bonus['atk']} = **{total_atk}**"
        else:
            base_stats += f" = **{total_atk}**"
        
        base_stats += f"\n🛡️ 防御力: {p['def']}"
        if equipment_bonus.get('def', 0) > 0:
            base_stats += f" +{equipment_bonus['def']} = **{total_def}**"
        else:
            base_stats += f" = **{total_def}**"
        
        base_stats += f"\n🔮 魔法力: {p.get('mag', 5)}"
        if equipment_bonus.get('mag', 0) > 0:
            base_stats += f" +{equipment_bonus['mag']} = **{total_mag}**"
        else:
            base_stats += f" = **{total_mag}**"
        
        base_stats += f"\n💨 素早さ: {p.get('agi', 8)}"
        if equipment_bonus.get('agi', 0) > 0:
            base_stats += f" +{equipment_bonus['agi']} = **{total_agi}**"
        else:
            base_stats += f" = **{total_agi}**"
        
        base_stats += f"\n🍀 運: {p.get('luk', 8)}"
        if equipment_bonus.get('luk', 0) > 0:
            base_stats += f" +{equipment_bonus['luk']} = **{total_luk}**"
        else:
            base_stats += f" = **{total_luk}**"
        
        embed.add_field(name="📊 ステータス", value=base_stats, inline=False)
        embed.add_field(name="💰 所持金", value=f"{player_money}{currency}", inline=False)
        
        # 装備ボーナスがある場合のみ強調表示
        if any(equipment_bonus.values()):
            embed.set_footer(text="✨ 装備ボーナスが反映されています")
        else:
            embed.set_footer(text="冒険を続けて強くなろう！")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="rpg_hello", description="RPG Botが動いているか確認")
    async def rpg_hello(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎮 RPG Bot",
            description="RPG Bot は正常に動作しています！\n`/rpg_start` で冒険を始めよう！",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rpg_work", description="働いてお金を稼ぐ")
    async def rpg_work(self, interaction: discord.Interaction):
        players = self.load_players()
        uid = str(interaction.user.id)

        if uid not in players:
            return await interaction.response.send_message("❌ `/rpg_start` で冒険者になりましょう！", ephemeral=True)

        earnings = random.randint(30, 80)
        
        # エコノミーシステムにお金を追加
        self.add_player_money(interaction.user.id, earnings)
        
        # ゴールド獲得クエスト更新（クエストシステムはRPGのゴールドを見ているので維持）
        if self.quest_board:
            self.quest_board.update_progress(interaction.user.id, "earn_gold", None, earnings)

        currency = self.get_currency()

        embed = discord.Embed(
            title="💼 日雇い仕事",
            description=f"{players[uid]['name']} は雑貨屋で働いた！",
            color=discord.Color.gold()
        )
        embed.add_field(name="💰 獲得金額", value=f"+{earnings}{currency}", inline=True)
        embed.add_field(name="📦 所持金", value=f"{self.get_player_money(interaction.user.id)}{currency}", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="rpg_train", description="訓練して経験値を獲得")
    async def rpg_train(self, interaction: discord.Interaction):
        players = self.load_players()
        uid = str(interaction.user.id)

        if uid not in players:
            return await interaction.response.send_message("❌ `/rpg_start` で冒険者になりましょう！", ephemeral=True)

        exp_gain = random.randint(10, 30)
        players[uid]["exp"] += exp_gain

        level_up = False
        old_level = players[uid]["level"]

        while players[uid]["exp"] >= players[uid]["level"] * 100:
            players[uid]["exp"] -= players[uid]["level"] * 100
            players[uid]["level"] += 1
            players[uid]["max_hp"] += 10
            players[uid]["max_mp"] += 5
            players[uid]["atk"] += 3
            players[uid]["def"] += 2
            players[uid]["hp"] = players[uid]["max_hp"]
            players[uid]["mp"] = players[uid]["max_mp"]
            level_up = True

        self.save_players(players)
        
        # トレーニングクエスト更新
        if self.quest_board:
            self.quest_board.update_progress(interaction.user.id, "command", "train", 1)

        embed = discord.Embed(
            title="🏋️ 訓練",
            description=f"{players[uid]['name']} は訓練に励んだ！",
            color=discord.Color.blue()
        )
        embed.add_field(name="✨ 獲得経験値", value=f"+{exp_gain} EXP", inline=True)

        if level_up:
            embed.add_field(
                name="🎉 レベルアップ！",
                value=f"Lv.{old_level} → **Lv.{players[uid]['level']}**\n"
                      f"❤️ HP +10\n✨ MP +5\n⚔️ 攻撃力 +3\n🛡️ 防御力 +2",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="rpg_walk", description="周囲を歩き回る")
    async def rpg_walk(self, interaction: discord.Interaction):
        players = self.load_players()
        uid = str(interaction.user.id)

        if uid not in players:
            return await interaction.response.send_message("❌ `/rpg_start` で冒険者になりましょう！", ephemeral=True)

        # データ移行
        player = players[uid]
        if self.migrate_player_data(uid, player):
            players[uid] = player
            self.save_players(players)

        await rpg_walk.start_walk(self, interaction)

    @app_commands.command(name="rpg_battle", description="モンスターと戦う")
    @app_commands.choices(敵=[
        app_commands.Choice(name="スライム", value="slime"),
        app_commands.Choice(name="ゴブリン", value="goblin"),
        app_commands.Choice(name="ウルフ", value="wolf"),
        app_commands.Choice(name="コウモリ", value="bat"),
        app_commands.Choice(name="サソリ", value="scorpion"),
        app_commands.Choice(name="クラブ", value="crab"),
        app_commands.Choice(name="フィッシュマン", value="fishman")
    ])
    async def rpg_battle(self, interaction: discord.Interaction, 敵: str):
        players = self.load_players()
        uid = str(interaction.user.id)

        if uid not in players:
            return await interaction.response.send_message("❌ `/rpg_start` で冒険者になりましょう！", ephemeral=True)

        enemies = self.load_enemies()
        if 敵 not in enemies:
            return await interaction.response.send_message("❌ その敵はいません", ephemeral=True)

        player = players[uid]
        enemy = enemies[敵].copy()

        await rpg_battle.start_battle(self, interaction, enemy)

    @app_commands.command(name="rpg_heal", description="宿屋で回復する")
    async def rpg_heal(self, interaction: discord.Interaction):
        players = self.load_players()
        uid = str(interaction.user.id)

        if uid not in players:
            return await interaction.response.send_message("❌ `/rpg_start` で冒険者になりましょう！", ephemeral=True)

        cost = 20
        if self.get_player_money(interaction.user.id) < cost:
            currency = self.get_currency()
            return await interaction.response.send_message(f"❌ お金が足りません！ (必要: {cost}{currency})", ephemeral=True)

        # エコノミーシステムからお金を減らす
        self.remove_player_money(interaction.user.id, cost)
        
        # HP/MPを回復
        players[uid]["hp"] = players[uid]["max_hp"]
        players[uid]["mp"] = players[uid]["max_mp"]
        self.save_players(players)

        currency = self.get_currency()

        embed = discord.Embed(
            title="🏨 宿屋",
            description=f"{players[uid]['name']} は宿屋で休んだ！",
            color=discord.Color.green()
        )
        embed.add_field(name="❤️ HP/MP", value="全回復した！", inline=True)
        embed.add_field(name="💰 支払い", value=f"-{cost}{currency}", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="rpg_map", description="全体マップを表示")
    async def rpg_map(self, interaction: discord.Interaction):
        players = self.load_players()
        uid = str(interaction.user.id)

        if uid not in players:
            return await interaction.response.send_message("❌ `/rpg_start` で冒険者になりましょう！", ephemeral=True)

        world = self.load_world_map()
        areas = self.load_areas()
        p = players[uid]
        px = p.get("x", 4)
        py = p.get("y", 5)

        # マップの範囲を表示（現在地を中心に5x5）
        map_lines = []
        for y in range(max(0, py-2), min(world["height"], py+3)):
            line = ""
            for x in range(max(0, px-2), min(world["width"], px+3)):
                area_key = world["grid"][y][x]
                area = areas.get(area_key, {"name": "???"})
                if x == px and y == py:
                    line += f"📍 "
                else:
                    emoji_map = {"草原": "🌿", "森林": "🌲", "村": "🏘️", "街": "🏙️", "城": "🏰", "山": "⛰️", "洞窟": "🕳️", "砂漠": "🏜️", "海岸": "🏖️"}
                    emoji = emoji_map.get(area_key, "❓")
                    line += f"{emoji} "
            map_lines.append(line)

        embed = discord.Embed(
            title="🗺️ ワールドマップ",
            description=f"現在地: {areas.get(world['grid'][py][px], {}).get('name', '???)')}\n```\n" + "\n".join(map_lines) + "\n```",
            color=discord.Color.blue()
        )
        embed.set_footer(text="📍 = 現在地 | 🌿草原 🏘️村 🏙️街 🏰城 🌲森林 ⛰️山 🕳️洞窟 🏜️砂漠 🏖️海岸")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="rpg_debug_path", description="保存先パスを確認")
    async def debug_path(self, interaction: discord.Interaction):
        import os
        abs_path = os.path.abspath(self.data_path)
        await interaction.response.send_message(f"保存先: `{abs_path}`", ephemeral=True)


async def setup(bot):
    await bot.add_cog(RPG(bot))