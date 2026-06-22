import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class QuestBoardView(discord.ui.View):
    """クエストボードメインビュー"""
    def __init__(self, cog, user_id: int):
        super().__init__(timeout=120)
        self.cog = cog
        self.user_id = user_id
    
    @discord.ui.button(label="📅 デイリークエスト", style=discord.ButtonStyle.primary, emoji="📅", row=0)
    async def show_daily(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたのクエストボードではありません", ephemeral=True)
        await self.show_quest_list(interaction, "daily")
    
    @discord.ui.button(label="📆 ウィークリークエスト", style=discord.ButtonStyle.success, emoji="📆", row=0)
    async def show_weekly(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたのクエストボードではありません", ephemeral=True)
        await self.show_quest_list(interaction, "weekly")
    
    @discord.ui.button(label="🏆 達成状況", style=discord.ButtonStyle.secondary, emoji="🏆", row=1)
    async def show_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたのクエストボードではありません", ephemeral=True)
        await self.show_quest_status(interaction)
    
    @discord.ui.button(label="🔄 更新", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ あなたのクエストボードではありません", ephemeral=True)
        await self.show_main_board(interaction)
    
    async def show_main_board(self, interaction: discord.Interaction):
        """メインのクエストボードを表示"""
        players = self.cog.load_players()
        uid = str(interaction.user.id)
        
        if uid not in players:
            return await interaction.response.send_message("❌ 冒険者登録が必要です", ephemeral=True)
        
        embed = discord.Embed(
            title="📋 クエストボード",
            description="挑戦できるクエストを選んでください",
            color=discord.Color.gold()
        )
        
        daily_count = len(self.cog.quests.get("daily_quests", {}))
        weekly_count = len(self.cog.quests.get("weekly_quests", {}))
        
        embed.add_field(name="📅 デイリー", value=f"{daily_count}件", inline=True)
        embed.add_field(name="📆 ウィークリー", value=f"{weekly_count}件", inline=True)
        
        view = QuestBoardView(self.cog, self.user_id)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_quest_list(self, interaction: discord.Interaction, quest_type: str):
        """特定タイプのクエスト一覧を表示"""
        quests = self.cog.quests.get(f"{quest_type}_quests", {})
        player_quests = self.cog.load_player_quests()
        uid = str(self.user_id)
        
        embed = discord.Embed(
            title=f"📋 {self._get_type_name(quest_type)}クエスト一覧",
            color=discord.Color.blue()
        )
        
        has_quests = False
        for q_id, q_data in quests.items():
            has_quests = True
            status = "⬜ 未着手"
            
            if uid in player_quests and quest_type in player_quests[uid]:
                p_data = player_quests[uid][quest_type].get(q_id, {})
                if p_data.get("completed", False):
                    status = "✅ 達成済み"
                elif "progress" in p_data:
                    target_count = q_data["target"]["count"]
                    current = p_data["progress"]
                    progress_percent = int(current / target_count * 100)
                    bar = self._create_progress_bar(progress_percent)
                    status = f"📊 {current}/{target_count}\n{bar}"
            
            reward_text = f"EXP {q_data['reward']['exp']} / {q_data['reward']['gold']}G"
            if "item" in q_data["reward"]:
                reward_text += f" / 🎁 {q_data['reward']['item']}"
            
            embed.add_field(
                name=f"{status.split()[0]} {q_data['name']}",
                value=f"📝 {q_data['description']}\n🎁 報酬: {reward_text}",
                inline=False
            )
        
        if not has_quests:
            embed.description = "現在クエストはありません"
        
        # 戻るボタン付きのViewを作成
        view = BackView(self.cog, self.user_id)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_quest_status(self, interaction: discord.Interaction):
        """クエスト達成状況を表示"""
        player_quests = self.cog.load_player_quests()
        uid = str(self.user_id)
        
        embed = discord.Embed(
            title="🏆 クエスト達成状況",
            color=discord.Color.gold()
        )
        
        # デイリー達成数
        daily_completed = 0
        daily_total = len(self.cog.quests.get("daily_quests", {}))
        if uid in player_quests and "daily" in player_quests[uid]:
            daily_completed = sum(1 for q in player_quests[uid]["daily"].values() if q.get("completed", False))
        
        # ウィークリー達成数
        weekly_completed = 0
        weekly_total = len(self.cog.quests.get("weekly_quests", {}))
        if uid in player_quests and "weekly" in player_quests[uid]:
            weekly_completed = sum(1 for q in player_quests[uid]["weekly"].values() if q.get("completed", False))
        
        embed.add_field(
            name="📅 デイリークエスト",
            value=f"達成: {daily_completed}/{daily_total}\n{self._create_progress_bar(int(daily_completed/daily_total*100) if daily_total > 0 else 0)}",
            inline=False
        )
        
        embed.add_field(
            name="📆 ウィークリークエスト",
            value=f"達成: {weekly_completed}/{weekly_total}\n{self._create_progress_bar(int(weekly_completed/weekly_total*100) if weekly_total > 0 else 0)}",
            inline=False
        )
        
        # 戻るボタン付きのViewを作成
        view = BackView(self.cog, self.user_id)
        await interaction.response.edit_message(embed=embed, view=view)
    
    def _get_type_name(self, quest_type: str) -> str:
        return {"daily": "デイリー", "weekly": "ウィークリー"}.get(quest_type, quest_type)
    
    def _create_progress_bar(self, percent: int, length: int = 15) -> str:
        filled = int(length * percent / 100)
        return "`" + "█" * filled + "░" * (length - filled) + f" {percent}%`"


class BackView(discord.ui.View):
    """戻るボタン付きビュー"""
    def __init__(self, cog, user_id: int):
        super().__init__(timeout=60)
        self.cog = cog
        self.user_id = user_id
    
    @discord.ui.button(label="◀ 戻る", style=discord.ButtonStyle.secondary, emoji="◀")
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ 操作できません", ephemeral=True)
        
        # メインのクエストボードを表示
        players = self.cog.load_players()
        uid = str(interaction.user.id)
        
        if uid not in players:
            return await interaction.response.send_message("❌ 冒険者登録が必要です", ephemeral=True)
        
        embed = discord.Embed(
            title="📋 クエストボード",
            description="挑戦できるクエストを選んでください",
            color=discord.Color.gold()
        )
        
        daily_count = len(self.cog.quests.get("daily_quests", {}))
        weekly_count = len(self.cog.quests.get("weekly_quests", {}))
        
        embed.add_field(name="📅 デイリー", value=f"{daily_count}件", inline=True)
        embed.add_field(name="📆 ウィークリー", value=f"{weekly_count}件", inline=True)
        
        view = QuestBoardView(self.cog, self.user_id)
        await interaction.response.edit_message(embed=embed, view=view)


class QuestBoard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.quests_path = "cogs/rpg/data/quests.json"
        self.player_quests_path = "cogs/rpg/data/player_quests.json"
        self.load_quests()
        
        # デイリーリセットタスク開始
        self.daily_reset.start()
        self.weekly_reset.start()
    
    def load_quests(self):
        """クエストマスターデータを読み込み"""
        if os.path.exists(self.quests_path):
            with open(self.quests_path, 'r', encoding='utf-8') as f:
                self.quests = json.load(f)
        else:
            self.quests = {"daily_quests": {}, "weekly_quests": {}}
    
    def load_player_quests(self) -> dict:
        """プレイヤーのクエスト進捗を読み込み"""
        if os.path.exists(self.player_quests_path):
            with open(self.player_quests_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_player_quests(self, data: dict):
        with open(self.player_quests_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_players(self):
        players_path = "cogs/rpg/data/players.json"
        if os.path.exists(players_path):
            with open(players_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_players(self, data):
        players_path = "cogs/rpg/data/players.json"
        with open(players_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def init_player_quests(self, user_id: int):
        """新規プレイヤーのクエストデータを初期化"""
        player_quests = self.load_player_quests()
        uid = str(user_id)
        
        if uid not in player_quests:
            player_quests[uid] = {"daily": {}, "weekly": {}}
            
            # デイリークエストを初期化
            for q_id in self.quests.get("daily_quests", {}):
                player_quests[uid]["daily"][q_id] = {"progress": 0, "completed": False}
            
            # ウィークリークエストを初期化
            for q_id in self.quests.get("weekly_quests", {}):
                player_quests[uid]["weekly"][q_id] = {"progress": 0, "completed": False}
            
            self.save_player_quests(player_quests)
    
    def give_reward(self, user_id: int, reward: dict):
        """報酬を付与"""
        players = self.load_players()
        uid = str(user_id)
        
        if uid in players:
            if "exp" in reward:
                players[uid]["exp"] = players[uid].get("exp", 0) + reward["exp"]
            if "gold" in reward:
                players[uid]["gold"] = players[uid].get("gold", 0) + reward["gold"]
            # アイテム報酬（簡易実装）
            if "item" in reward:
                if "items" not in players[uid]:
                    players[uid]["items"] = {}
                players[uid]["items"][reward["item"]] = players[uid]["items"].get(reward["item"], 0) + 1
            
            self.save_players(players)
            return True
        return False
    
    def update_progress(self, user_id: int, action_type: str, target_name: str = None, amount: int = 1, extra_data: dict = None) -> Optional[dict]:
        """クエスト進捗を更新（完了したクエストの報酬を返す）"""
        player_quests = self.load_player_quests()
        uid = str(user_id)
        
        if uid not in player_quests:
            return None
        
        completed_rewards = []
        
        for quest_type in ["daily", "weekly"]:
            for q_id, quest_data in player_quests[uid].get(quest_type, {}).items():
                # 既に完了している場合はスキップ
                if quest_data.get("completed", False):
                    continue
                
                # クエストマスターデータを取得
                master_quest = self.quests.get(f"{quest_type}_quests", {}).get(q_id)
                if not master_quest:
                    continue
                
                target = master_quest.get("target", {})
                
                # アクションタイプチェック
                if target.get("type") != action_type:
                    continue
                
                # 敵名チェック（必要な場合）
                if "enemy" in target and target["enemy"] != target_name:
                    continue
                
                # 最小レベルチェック
                if "min_level" in target:
                    if extra_data and extra_data.get("enemy_level", 0) < target["min_level"]:
                        continue
                
                # 進捗更新
                quest_data["progress"] = quest_data.get("progress", 0) + amount
                
                # 完了チェック
                if quest_data["progress"] >= target["count"]:
                    quest_data["completed"] = True
                    # 報酬付与
                    reward = master_quest.get("reward", {})
                    self.give_reward(user_id, reward)
                    completed_rewards.append(reward)
                
                self.save_player_quests(player_quests)
        
        return completed_rewards if completed_rewards else None
    
    @tasks.loop(hours=24)
    async def daily_reset(self):
        """デイリークエストリセット"""
        now = datetime.now()
        if now.hour == 0:
            player_quests = self.load_player_quests()
            for uid in player_quests:
                if "daily" in player_quests[uid]:
                    for q_id in player_quests[uid]["daily"]:
                        player_quests[uid]["daily"][q_id] = {"progress": 0, "completed": False}
            self.save_player_quests(player_quests)
            print("✅ デイリークエストをリセットしました")
    
    @tasks.loop(hours=168)
    async def weekly_reset(self):
        """ウィークリークエストリセット"""
        if datetime.now().weekday() == 0:
            player_quests = self.load_player_quests()
            for uid in player_quests:
                if "weekly" in player_quests[uid]:
                    for q_id in player_quests[uid]["weekly"]:
                        player_quests[uid]["weekly"][q_id] = {"progress": 0, "completed": False}
            self.save_player_quests(player_quests)
            print("✅ ウィークリークエストをリセットしました")
    
    @app_commands.command(name="quest_board", description="クエストボードを開く")
    async def quest_board(self, interaction: discord.Interaction):
        """クエストボードを表示"""
        players = self.load_players()
        uid = str(interaction.user.id)
        
        if uid not in players:
            return await interaction.response.send_message("❌ `/rpg_start` で冒険者になりましょう！", ephemeral=True)
        
        embed = discord.Embed(
            title="📋 クエストボード",
            description="挑戦できるクエストを選んでください",
            color=discord.Color.gold()
        )
        
        daily_count = len(self.quests.get("daily_quests", {}))
        weekly_count = len(self.quests.get("weekly_quests", {}))
        
        embed.add_field(name="📅 デイリー", value=f"{daily_count}件", inline=True)
        embed.add_field(name="📆 ウィークリー", value=f"{weekly_count}件", inline=True)
        
        view = QuestBoardView(self, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(QuestBoard(bot))