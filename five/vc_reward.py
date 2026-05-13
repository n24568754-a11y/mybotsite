import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
from datetime import datetime

DATA_FILE = 'data.json'
CONFIG_FILE = 'config.json'

class VCReward(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._load_config()
        self.vc_reward_task.start()
        self.weekly_reset_task.start()

    def _load_config(self):
        """設定ファイルを読み込み、必要なキーを初期化する"""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {}

        if "reward_categories" not in self.config:
            self.config["reward_categories"] = []
        if "evaluators" not in self.config:
            self.config["evaluators"] = []
        if "authorized_users" not in self.config:
            self.config["authorized_users"] = []

    def _save_config(self):
        """設定ファイルを保存する"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def load_data(self):
        if not os.path.exists(DATA_FILE): return {}
        with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)

    def save_data(self, data):
        with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2, ensure_ascii=False)

    def get_default_user_data(self):
        return {
            'money': 0, 'last_daily': None, 'subscriptions': {}, 'inventory': [],
            'chat': 0, 'vc': 0, 'gacha_count': 0, 'send_money_total': 0,
            'daily_chat': 0, 'daily_vc': 0, 'completed_missions': [], 'claimed_missions': [],
            'weekly_vc_minutes': 0,
            'evaluator_total_minutes': 0
        }

    def is_authorized(self, interaction: discord.Interaction):
        """管理者、または許可されたユーザーかどうかを判定"""
        return interaction.user.guild_permissions.administrator or interaction.user.id in self.config.get("authorized_users", [])

    # --- 評価員・権限管理系コマンド ---

    @app_commands.command(name="評価員滞在確認", description="評価員の滞在時間一覧を表示します")
    async def check_evaluators(self, interaction: discord.Interaction):
        if not self.is_authorized(interaction):
            await interaction.response.send_message("❌ このコマンドを実行する権限がありません。", ephemeral=True)
            return

        data = self.load_data()
        evaluator_ids = self.config.get("evaluators", [])

        if not evaluator_ids:
            await interaction.response.send_message("📋 評価員が登録されていません。", ephemeral=True)
            return

        embed = discord.Embed(title="📊 評価員 滞在時間一覧", color=discord.Color.green())
        lines = []
        for uid_str in evaluator_ids:
            stats = data.get(str(uid_str), self.get_default_user_data())
            total_mins = stats.get('evaluator_total_minutes', 0)
            member = interaction.guild.get_member(int(uid_str))
            name = member.display_name if member else f"UserID: {uid_str}"
            h, m = divmod(total_mins, 60)
            lines.append(f"👤 **{name}**: `{h}時間{m}分`")

        embed.description = "\n".join(lines)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="評価員追加", description="滞在時間を記録する評価員を追加します")
    @app_commands.describe(ユーザー="記録対象にするユーザー")
    async def add_evaluator(self, interaction: discord.Interaction, ユーザー: discord.Member):
        if not self.is_authorized(interaction):
            await interaction.response.send_message("❌ このコマンドを実行する権限がありません。", ephemeral=True)
            return

        if ユーザー.id in self.config["evaluators"]:
            await interaction.response.send_message(f"⚠️ {ユーザー.display_name} は既に登録されています。", ephemeral=True)
            return

        self.config["evaluators"].append(ユーザー.id)
        self._save_config()
        await interaction.response.send_message(f"✅ {ユーザー.display_name} を評価員として登録しました。", ephemeral=True)

    @app_commands.command(name="評価員削除", description="評価員リストからユーザーを削除します")
    @app_commands.describe(ユーザー名="削除する評価員の名前を入力してください")
    async def remove_evaluator(self, interaction: discord.Interaction, ユーザー名: str):
        if not self.is_authorized(interaction):
            await interaction.response.send_message("❌ このコマンドを実行する権限がありません。", ephemeral=True)
            return

        # 名前(またはID)から該当するIDを探す
        target_id = None
        for uid in self.config["evaluators"]:
            member = interaction.guild.get_member(uid)
            if member and member.display_name == ユーザー名:
                target_id = uid
                break
            if str(uid) == ユーザー名:
                target_id = uid
                break

        if target_id:
            self.config["evaluators"].remove(target_id)
            self._save_config()
            await interaction.response.send_message(f"🗑️ {ユーザー名} を評価員リストから削除しました。", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ 登録されている評価員が見つかりません。", ephemeral=True)

    @remove_evaluator.autocomplete('ユーザー名')
    async def evaluator_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = []
        for uid in self.config["evaluators"]:
            member = interaction.guild.get_member(uid)
            name = member.display_name if member else str(uid)
            if current.lower() in name.lower():
                choices.append(app_commands.Choice(name=name, value=name))
        return choices[:25]

    @app_commands.command(name="滞在確認設定", description="評価員管理コマンドを使えるユーザーを設定します")
    @app_commands.describe(ユーザー="権限を操作するユーザー", 状態="付与するか削除するか")
    @app_commands.choices(状態=[
        app_commands.Choice(name="付与", value="add"),
        app_commands.Choice(name="削除", value="remove")
    ])
    @app_commands.default_permissions(administrator=True)
    async def setup_authorized_user(self, interaction: discord.Interaction, ユーザー: discord.Member, 状態: str):
        if 状態 == "add":
            if ユーザー.id not in self.config["authorized_users"]:
                self.config["authorized_users"].append(ユーザー.id)
            msg = f"✅ {ユーザー.display_name} に評価員管理の権限を付与しました。"
        else:
            if ユーザー.id in self.config["authorized_users"]:
                self.config["authorized_users"].remove(ユーザー.id)
            msg = f"🗑️ {ユーザー.display_name} から権限を削除しました。"

        self._save_config()
        await interaction.response.send_message(msg, ephemeral=True)

    # --- 既存の一般ユーザー向けコマンド ---

    @app_commands.command(name="vcランキング", description="今週のVC滞在時間ランキングを表示します")
    async def vc_ranking(self, interaction: discord.Interaction):
        data = self.load_data()
        ranking_list = [(uid, s.get('weekly_vc_minutes', 0)) for uid, s in data.items() if s.get('weekly_vc_minutes', 0) > 0]
        ranking_list.sort(key=lambda x: x[1], reverse=True)
        top_10 = ranking_list[:10]

        if not top_10:
            await interaction.response.send_message("📊 現在ランキング対象のデータがありません。", ephemeral=True)
            return

        embed = discord.Embed(title="🏆 週間VC滞在時間ランキング", color=discord.Color.blue())
        rank_text = ""
        for i, (uid, mins) in enumerate(top_10, 1):
            member = interaction.guild.get_member(int(uid))
            name = member.display_name if member else f"User({uid[-4:]})"
            h, m = divmod(mins, 60)
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}位"
            rank_text += f"{medal} **{name}**: `{h}時間{m}分`\n"

        embed.add_field(name="順位 / 名前 / 滞在時間", value=rank_text, inline=False)
        embed.set_footer(text="※毎週月曜日の午前0時にリセットされます")
        await interaction.response.send_message(embed=embed)

    # --- 既存の管理者用カテゴリー管理コマンド ---

    @app_commands.command(name="報酬カテゴリー追加", description="仮想通貨が付与されるカテゴリーを設定します")
    @app_commands.default_permissions(administrator=True)
    async def add_category(self, interaction: discord.Interaction, カテゴリー名: str):
        category = discord.utils.get(interaction.guild.categories, name=カテゴリー名)
        if not category:
            await interaction.response.send_message(f"❌ カテゴリー「{カテゴリー名}」が見つかりません。", ephemeral=True)
            return
        if category.id not in self.config["reward_categories"]:
            self.config["reward_categories"].append(category.id)
            self._save_config()
            await interaction.response.send_message(f"✅ カテゴリー「{category.name}」を報酬対象に追加しました。", ephemeral=True)

    @app_commands.command(name="報酬カテゴリー削除", description="報酬対象からカテゴリーを外します")
    @app_commands.default_permissions(administrator=True)
    async def remove_category(self, interaction: discord.Interaction, カテゴリー名: str):
        target_id = None
        for cat_id in self.config["reward_categories"]:
            cat = interaction.guild.get_channel(cat_id)
            if cat and cat.name == カテゴリー名:
                target_id = cat_id
                break
        if target_id:
            self.config["reward_categories"].remove(target_id)
            self._save_config()
            await interaction.response.send_message(f"🗑️ カテゴリー「{カテゴリー名}」を報酬対象から削除しました。", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ 登録されているカテゴリーが見つかりません。", ephemeral=True)

    @remove_category.autocomplete('カテゴリー名')
    async def category_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = []
        for cat_id in self.config["reward_categories"]:
            cat = interaction.guild.get_channel(cat_id)
            if cat and current.lower() in cat.name.lower():
                choices.append(app_commands.Choice(name=cat.name, value=cat.name))
        return choices[:25]

    # --- ループタスク ---

    @tasks.loop(minutes=1)
    async def vc_reward_task(self):
        data = self.load_data()
        updated = False
        REWARD_PER_MINUTE = 10 
        evaluator_ids = self.config.get("evaluators", [])

        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                if not vc.category or vc.category.id not in self.config.get("reward_categories", []):
                    continue
                for member in vc.members:
                    if member.bot or member.voice.self_deaf or member.voice.deaf:
                        continue

                    uid = str(member.id)
                    if uid not in data: data[uid] = self.get_default_user_data()

                    data[uid]['money'] += REWARD_PER_MINUTE
                    data[uid]['weekly_vc_minutes'] = data[uid].get('weekly_vc_minutes', 0) + 1

                    if member.id in evaluator_ids:
                        data[uid]['evaluator_total_minutes'] = data[uid].get('evaluator_total_minutes', 0) + 1

                    updated = True
        if updated: self.save_data(data)

    @tasks.loop(hours=1)
    async def weekly_reset_task(self):
        now = datetime.now()
        if now.weekday() == 0 and now.hour == 0:
            data = self.load_data()
            for uid in data:
                data[uid]['weekly_vc_minutes'] = 0
            self.save_data(data)
            print("📅 週間ランキングデータをリセットしました")

async def setup(bot):
    await bot.add_cog(VCReward(bot))
