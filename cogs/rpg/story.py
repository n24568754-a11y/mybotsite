import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from typing import Optional, Dict, Any

class StoryView(discord.ui.View):
    """ストーリー選択肢ビュー"""
    def __init__(self, cog, interaction: discord.Interaction, event_key: str, event_data: dict):
        super().__init__(timeout=60)
        self.cog = cog
        self.interaction = interaction
        self.event_key = event_key
        self.event_data = event_data
        
        # 選択肢ボタンを動的に追加
        choices = event_data.get("choices", [])
        for i, choice in enumerate(choices):
            button = discord.ui.Button(
                label=choice["text"],
                style=getattr(discord.ButtonStyle, choice.get("style", "primary")),
                row=i // 3,
                custom_id=f"story_choice_{i}"
            )
            # クロージャの問題を回避
            async def button_callback(interaction: discord.Interaction, c=choice):
                await self.make_choice(interaction, c)
            button.callback = button_callback
            self.add_item(button)
    
    async def make_choice(self, interaction: discord.Interaction, choice_data: dict):
        """選択肢処理"""
        await interaction.response.defer()
        
        effects = choice_data.get("effects", {})
        
        # 効果を適用
        for flag in effects.get("flags_add", []):
            self.cog.set_player_flag(interaction.user.id, flag, True)
        
        # 報酬付与
        players = self.cog.load_players()
        uid = str(interaction.user.id)
        
        if uid in players:
            if "reward_exp" in effects:
                players[uid]["exp"] = players[uid].get("exp", 0) + effects["reward_exp"]
            if "reward_gold" in effects:
                players[uid]["gold"] = players[uid].get("gold", 0) + effects["reward_gold"]
            self.cog.save_players(players)
        
        # クエスト開始
        if "quest_start" in effects:
            # クエスト開始処理は後で実装
            pass
        
        # 結果表示
        result_embed = discord.Embed(
            title="✅ 選択結果",
            description=f"「{choice_data['text']}」を選んだ。",
            color=discord.Color.green()
        )
        
        if effects.get("reward_exp"):
            result_embed.add_field(name="✨ 獲得経験値", value=f"+{effects['reward_exp']}", inline=True)
        if effects.get("reward_gold"):
            result_embed.add_field(name="💰 獲得ゴールド", value=f"+{effects['reward_gold']}", inline=True)
        
        await interaction.edit_original_response(embed=result_embed, view=None)
        
        # 次のイベントがあれば開始
        next_event = choice_data.get("next_event")
        if next_event:
            await self.cog.start_event(interaction, next_event)


class StorySystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.story_path = "cogs/rpg/data/story.json"
        self._load_story_data()
    
    def _load_story_data(self):
        """ストーリーデータを読み込み"""
        if os.path.exists(self.story_path):
            with open(self.story_path, 'r', encoding='utf-8') as f:
                self.story_data = json.load(f)
        else:
            self.story_data = {
                "chapters": {},
                "events": {},
                "quest_events": {},
                "flags": {"global_flags": {}, "player_flags": {}}
            }
            self._save_story_data()
    
    def _save_story_data(self):
        with open(self.story_path, 'w', encoding='utf-8') as f:
            json.dump(self.story_data, f, indent=2, ensure_ascii=False)
    
    def load_players(self):
        """プレイヤーデータ読み込み（RPG Cogから借用）"""
        players_path = "cogs/rpg/data/players.json"
        if os.path.exists(players_path):
            with open(players_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_players(self, data):
        players_path = "cogs/rpg/data/players.json"
        with open(players_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_player_flags(self, user_id: int) -> dict:
        """プレイヤーのフラグを取得"""
        uid = str(user_id)
        if uid not in self.story_data["flags"]["player_flags"]:
            self.story_data["flags"]["player_flags"][uid] = {}
        return self.story_data["flags"]["player_flags"][uid]
    
    def set_player_flag(self, user_id: int, flag_name: str, value: bool = True):
        """プレイヤーフラグを設定"""
        flags = self.get_player_flags(user_id)
        flags[flag_name] = value
        self._save_story_data()
    
    def check_event_conditions(self, user_id: int, event_data: dict) -> bool:
        """イベント発生条件をチェック"""
        conditions = event_data.get("conditions", {})
        player_flags = self.get_player_flags(user_id)
        
        # 必須フラグチェック
        for required in conditions.get("flags_required", []):
            if not player_flags.get(required, False):
                return False
        
        # 禁止フラグチェック
        for forbidden in conditions.get("flags_forbidden", []):
            if player_flags.get(forbidden, False):
                return False
        
        # レベルチェック
        min_level = conditions.get("level_min", 0)
        if min_level > 0:
            players = self.load_players()
            uid = str(user_id)
            if uid in players and players[uid].get("level", 1) < min_level:
                return False
        
        return True
    
    async def start_event(self, interaction: discord.Interaction, event_key: str):
        """イベントを開始"""
        if event_key not in self.story_data["events"]:
            return
        
        event = self.story_data["events"][event_key]
        
        # 一度だけのイベントチェック
        if event.get("once", False):
            player_flags = self.get_player_flags(interaction.user.id)
            completed_flag = f"completed_{event_key}"
            if player_flags.get(completed_flag, False):
                return
            # 完了フラグを事前に設定（重複防止）
            self.set_player_flag(interaction.user.id, completed_flag, True)
        
        # 会話表示用埋め込み
        dialogue = event.get("dialogue", {})
        embed = discord.Embed(
            title=f"📖 {event.get('name', 'イベント')}",
            color=discord.Color.purple()
        )
        
        # 会話メッセージを結合
        messages = dialogue.get("messages", [])
        dialogue_text = "\n".join([f"> {msg}" for msg in messages])
        
        embed.add_field(
            name=f"{dialogue.get('npc_icon', '✨')} {dialogue.get('npc_name', '???')}",
            value=dialogue_text,
            inline=False
        )
        
        # 自動効果
        auto_effects = event.get("auto_effects", {})
        
        # 自動フラグ追加
        for flag in auto_effects.get("flags_add", []):
            self.set_player_flag(interaction.user.id, flag, True)
        
        # 報酬付与（自動効果の場合）
        if auto_effects and not event.get("choices"):
            players = self.load_players()
            uid = str(interaction.user.id)
            if uid in players:
                if "reward_exp" in auto_effects:
                    players[uid]["exp"] = players[uid].get("exp", 0) + auto_effects["reward_exp"]
                    embed.add_field(name="✨ 獲得経験値", value=f"+{auto_effects['reward_exp']}", inline=True)
                if "reward_gold" in auto_effects:
                    players[uid]["gold"] = players[uid].get("gold", 0) + auto_effects["reward_gold"]
                    embed.add_field(name="💰 獲得ゴールド", value=f"+{auto_effects['reward_gold']}", inline=True)
                self.save_players(players)
        
        # 選択肢がある場合
        if event.get("choices"):
            view = StoryView(self, interaction, event_key, event)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            # 選択肢なしの場合はそのまま表示
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def check_location_trigger(self, interaction: discord.Interaction, x: int, y: int, area: str) -> bool:
        """座標到達時のトリガーチェック"""
        for event_key, event in self.story_data["events"].items():
            trigger = event.get("trigger", {})
            
            if trigger.get("type") == "location":
                tx = trigger.get("x")
                ty = trigger.get("y")
                radius = trigger.get("radius", 0)
                trigger_area = trigger.get("area")
                
                # エリア一致チェック
                if trigger_area and trigger_area != area:
                    continue
                
                # 座標一致チェック
                if tx is not None and ty is not None:
                    if radius > 0:
                        # 範囲内チェック
                        if abs(tx - x) <= radius and abs(ty - y) <= radius:
                            if self.check_event_conditions(interaction.user.id, event):
                                await self.start_event(interaction, event_key)
                                return True
                    else:
                        # 完全一致
                        if tx == x and ty == y:
                            if self.check_event_conditions(interaction.user.id, event):
                                await self.start_event(interaction, event_key)
                                return True
        
        return False
    
    # ========== スラッシュコマンド ==========
    
    @app_commands.command(name="rpg_story_flags", description="ストーリーフラグを確認する")
    async def story_flags(self, interaction: discord.Interaction):
        """プレイヤーのストーリーフラグを表示"""
        players = self.load_players()
        uid = str(interaction.user.id)
        
        if uid not in players:
            return await interaction.response.send_message("❌ `/rpg_start` で冒険者になりましょう！", ephemeral=True)
        
        flags = self.get_player_flags(interaction.user.id)
        
        if not flags:
            await interaction.response.send_message("📋 まだストーリーフラグはありません", ephemeral=True)
            return
        
        # フラグをカテゴリ分けして表示
        story_flags = {k: v for k, v in flags.items() if not k.startswith("completed_")}
        completed = {k: v for k, v in flags.items() if k.startswith("completed_")}
        
        embed = discord.Embed(
            title=f"📌 {players[uid]['name']} のストーリーフラグ",
            color=discord.Color.blue()
        )
        
        if story_flags:
            flag_list = "\n".join([f"• {k}: {'✅' if v else '❌'}" for k, v in story_flags.items()])
            embed.add_field(name="📋 進行中フラグ", value=flag_list, inline=False)
        
        if completed:
            comp_list = "\n".join([f"• {k.replace('completed_', '')}" for k in completed.keys()])
            embed.add_field(name="✅ 完了イベント", value=comp_list, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="rpg_story_chapters", description="ストーリーの章を確認する")
    async def story_chapters(self, interaction: discord.Interaction):
        """ストーリーの進行状況を表示"""
        players = self.load_players()
        uid = str(interaction.user.id)
        
        if uid not in players:
            return await interaction.response.send_message("❌ `/rpg_start` で冒険者になりましょう！", ephemeral=True)
        
        player_flags = self.get_player_flags(interaction.user.id)
        player_level = players[uid].get("level", 1)
        
        embed = discord.Embed(
            title="📖 ストーリー進行状況",
            description="各章の解放状況です",
            color=discord.Color.purple()
        )
        
        for chapter_key, chapter in self.story_data.get("chapters", {}).items():
            # 解放条件チェック
            prereq = chapter.get("prerequisites", {})
            level_ok = player_level >= prereq.get("min_level", 1)
            flags_ok = all(player_flags.get(f, False) for f in prereq.get("required_flags", []))
            
            is_unlocked = level_ok and flags_ok
            status = "🔓 解放済み" if is_unlocked else "🔒 未解放"
            
            # 条件表示
            conditions = []
            if prereq.get("min_level", 1) > 1:
                conditions.append(f"Lv.{prereq['min_level']}以上")
            if prereq.get("required_flags"):
                conditions.append(f"「{', '.join(prereq['required_flags'])}」達成")
            
            condition_text = f"\n*条件: {', '.join(conditions)}*" if conditions else ""
            
            embed.add_field(
                name=f"{'✅' if is_unlocked else '⏳'} {chapter['name']}",
                value=f"{chapter.get('description', '')}{condition_text}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="rpg_admin_story_trigger", description="ストーリーイベントを強制発生させる（管理者用）")
    @app_commands.default_permissions(administrator=True)
    async def admin_trigger_event(self, interaction: discord.Interaction, イベント名: str):
        """管理者用：指定したイベントを強制発生"""
        if イベント名 not in self.story_data["events"]:
            return await interaction.response.send_message(f"❌ イベント `{イベント名}` が見つかりません", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        await self.start_event(interaction, イベント名)
    
    @app_commands.command(name="rpg_admin_flag_set", description="プレイヤーフラグを設定する（管理者用）")
    @app_commands.default_permissions(administrator=True)
    async def admin_set_flag(self, interaction: discord.Interaction, ユーザー: discord.User, フラグ名: str, 値: bool = True):
        """管理者用：プレイヤーフラグを設定"""
        self.set_player_flag(ユーザー.id, フラグ名, 値)
        await interaction.response.send_message(
            f"✅ {ユーザー.mention} のフラグ `{フラグ名}` を {値} に設定しました",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(StorySystem(bot))