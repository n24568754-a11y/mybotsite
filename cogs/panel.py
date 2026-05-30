import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import json
import os
import traceback
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging

# --- ロギング設定 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ファイルパス ---
current_dir = os.path.dirname(os.path.abspath(__file__))
PANELS_FILE = os.path.join(os.path.dirname(current_dir), "panels.json")
TEMP_VCS_FILE = os.path.join(os.path.dirname(current_dir), "temp_vcs.json")
LOG_CONFIG_FILE = os.path.join(os.path.dirname(current_dir), "log_config.json")
PREMIUM_PANELS_FILE = os.path.join(os.path.dirname(current_dir), "premium_panels.json")

# --- ファイル管理クラス ---
class FileManager:
    @staticmethod
    def load_json(path: str, default_type: type = dict) -> Any:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, default_type):
                        return default_type()
                    return data
            except Exception as e:
                logger.error(f"ファイル読み込みエラー({path}): {e}")
        return default_type()

    @staticmethod
    def save_json(path: str, data: Any) -> bool:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"ファイル保存エラー({path}): {e}")
            return False

file_mgr = FileManager()


# --- 高級パネル設定用モーダル（シンプル版） ---
class PremiumPanelModal(discord.ui.Modal, title="高級パネル設置設定"):
    def __init__(self, opts: Dict[str, Any]):
        super().__init__()
        self.opts = opts

    vc_name = discord.ui.TextInput(label="VC名の接頭辞", default="🎤 ", placeholder="例: 🎤 ", max_length=50)
    vc_cost = discord.ui.TextInput(label="作成費用", default="500", max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            cost = int(self.vc_cost.value)
            if cost < 0:
                await interaction.followup.send("❌ 費用は0以上の数値を設定してください。", ephemeral=True)
                return

            economy_cog = interaction.client.get_cog("Economy")
            currency = economy_cog.currency if economy_cog else "星"

            desc = (
                f"**🌟 高級パネル**\n"
                f"ボタンを押してチャンネルを作成します。\n\n"
                f"**費用:** `{cost}` {currency}\n"
                f"作成後、管理パネルで設定変更が可能です。"
            )

            embed = discord.Embed(
                title="🌟 高級自動チャンネル作成パネル",
                description=desc,
                color=0xFF69B4
            )
            embed.set_footer(text="ボタンを押すとチャンネルが作成されます")

            view = PremiumVCPanelView(
                config_data={
                    "vc_name": self.vc_name.value,
                    "cost": cost,
                    "send_log": self.opts.get("send_log", True),
                    "specific_log_channel_id": self.opts.get("specific_log_channel_id")
                }
            )
            message = await interaction.channel.send(embed=embed, view=view)

            premium_panels = file_mgr.load_json(PREMIUM_PANELS_FILE, dict)
            premium_panels[str(message.id)] = {
                "vc_name": self.vc_name.value,
                "cost": cost,
                "send_log": self.opts.get("send_log", True),
                "specific_log_channel_id": self.opts.get("specific_log_channel_id")
            }
            file_mgr.save_json(PREMIUM_PANELS_FILE, premium_panels)

            await interaction.followup.send("✅ **高級パネル**を設置しました！", ephemeral=True)

        except ValueError:
            await interaction.followup.send("❌ 費用には整数を入力してください。", ephemeral=True)
        except Exception:
            logger.error(f"高級パネル設置エラー: {traceback.format_exc()}")
            await interaction.followup.send("❌ 高級パネルの設定に失敗しました。", ephemeral=True)


# --- 高級VC作成パネル（タイプ選択付き） ---
class PremiumVCPanelView(discord.ui.View):
    def __init__(self, config_data: Dict[str, Any]):
        super().__init__(timeout=None)
        self.config = config_data

    @discord.ui.button(label="🔊 ボイスチャンネル", style=discord.ButtonStyle.primary, custom_id="premium_create_voice", emoji="🔊", row=0)
    async def create_voice(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_channel(interaction, "voice")

    @discord.ui.button(label="🎭 ステージチャンネル", style=discord.ButtonStyle.success, custom_id="premium_create_stage", emoji="🎭", row=0)
    async def create_stage(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_channel(interaction, "stage")

    async def _create_channel(self, interaction: discord.Interaction, channel_type: str):
        await interaction.response.defer(ephemeral=True)

        try:
            economy_cog = interaction.client.get_cog("Economy")
            if not economy_cog:
                await interaction.followup.send("❌ 経済システムが非アクティブです。", ephemeral=True)
                return

            cost = self.config.get("cost", 500)
            user_id = str(interaction.user.id)
            data = economy_cog.load_data()

            if user_id not in data:
                data[user_id] = economy_cog.get_default_user_data()

            if data[user_id].get('money', 0) < cost:
                await interaction.followup.send(
                    f"❌ 所持金が足りません！ (必要: {cost} {economy_cog.currency})",
                    ephemeral=True
                )
                return

            data[user_id]['money'] -= cost
            economy_cog.save_data(data)
            if hasattr(economy_cog, 'update_web_data'):
                economy_cog.update_web_data()

            category = interaction.channel.category
            if not category:
                await interaction.followup.send("❌ カテゴリー内で実行してください。", ephemeral=True)
                return

            # デフォルトは公開設定（誰でも入れる）
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(connect=True, view_channel=True)
            }
            # 作成者には管理権限
            overwrites[interaction.user] = discord.PermissionOverwrite(
                connect=True, view_channel=True, manage_channels=True, move_members=True
            )

            vc_base = self.config.get("vc_name", "🎤 ")
            channel_name = f"{vc_base}{interaction.user.display_name[:20]}"[:100]

            channel = None
            if channel_type == "voice":
                # ボイスチャンネル: 最大256kbps
                channel = await interaction.guild.create_voice_channel(
                    name=channel_name,
                    category=category,
                    user_limit=0,  # 無制限
                    bitrate=64000,  # デフォルト64kbps
                    overwrites=overwrites,
                    reason=f"高級パネルによるVC作成 (作成者: {interaction.user})"
                )

            elif channel_type == "stage":
                # ステージチャンネル: 最大128kbps
                channel = await interaction.guild.create_stage_channel(
                    name=channel_name,
                    category=category,
                    user_limit=0,  # 無制限
                    bitrate=64000,  # デフォルト64kbps
                    overwrites=overwrites,
                    reason=f"高級パネルによるステージ作成 (作成者: {interaction.user})"
                )

            if not channel:
                await interaction.followup.send("❌ チャンネル作成に失敗しました。", ephemeral=True)
                return

            temp_vcs = file_mgr.load_json(TEMP_VCS_FILE, dict)
            temp_vcs[str(channel.id)] = {
                "owner_id": interaction.user.id,
                "created_at": datetime.now().isoformat(),
                "is_premium": True,
                "channel_type": channel_type
            }
            file_mgr.save_json(TEMP_VCS_FILE, temp_vcs)

            # すべての操作を許可（ユーザーが後で設定できるように）
            allowed_buttons = {
                "rename": True,
                "subtitle": True,
                "public": True,
                "private": True,
                "delete": True,
                "bitrate": True  # ビットレート変更も可能に
            }

            embed = discord.Embed(
                title="🌟 高級チャンネル管理パネル",
                description=f"作成者: {interaction.user.mention}\nこのパネルからチャンネルを管理できます。",
                color=0xFF69B4
            )
            embed.add_field(name="チャンネルタイプ", value="🔊 ボイスチャンネル" if channel_type == "voice" else "🎭 ステージチャンネル", inline=True)

            manage_view = VCManageView(interaction.user.id, allowed_buttons)
            manage_view.add_buttons_dynamically()
            await channel.send(content=interaction.user.mention, embed=embed, view=manage_view)

            if self.config.get("send_log", True):
                await self._send_premium_log(interaction, channel, cost, channel_type)

            await interaction.followup.send(f"✅ **高級チャンネル** {channel.mention} を作成しました！\n管理パネルはチャンネル内に表示されています。", ephemeral=True)

        except discord.Forbidden:
            await interaction.followup.send("❌ 権限不足のためチャンネルを作成できません。", ephemeral=True)
        except Exception:
            logger.error(f"高級チャンネル作成エラー: {traceback.format_exc()}")
            await interaction.followup.send("❌ チャンネルの作成に失敗しました。", ephemeral=True)

    async def _send_premium_log(self, interaction: discord.Interaction, channel, cost: int, channel_type: str):
        try:
            log_channel_id = self.config.get("specific_log_channel_id")
            if not log_channel_id:
                log_config = file_mgr.load_json(LOG_CONFIG_FILE, dict)
                log_channel_id = log_config.get(str(interaction.guild.id))

            if not log_channel_id:
                return

            log_channel = interaction.guild.get_channel(log_channel_id)
            if not log_channel:
                return

            economy_cog = interaction.client.get_cog("Economy")
            currency = economy_cog.currency if economy_cog else "単位"

            embed = discord.Embed(
                title="🌟 高級チャンネル作成ログ",
                color=0xFF69B4,
                timestamp=datetime.now()
            )
            embed.add_field(name="実行者", value=f"{interaction.user.mention}\nID: `{interaction.user.id}`", inline=False)
            embed.add_field(name="作成チャンネル", value=f"{channel.mention}\nID: `{channel.id}`", inline=True)
            embed.add_field(name="チャンネルタイプ", value="🔊 ボイスチャンネル" if channel_type == "voice" else "🎭 ステージチャンネル", inline=True)
            embed.add_field(name="支払い費用", value=f"{cost} {currency}", inline=True)
            embed.set_thumbnail(url=interaction.user.display_avatar.url)

            await log_channel.send(embed=embed)
        except Exception as e:
            logger.error(f"高級パネルログ送信エラー: {e}")


# --- 通常パネル用VC作成パネル ---
class VCPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="VC作成", style=discord.ButtonStyle.green, custom_id="create_vc_button")
    async def create_vc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        try:
            economy_cog = interaction.client.get_cog("Economy")
            if not economy_cog:
                await interaction.followup.send("❌ 経済システムが非アクティブです。", ephemeral=True)
                return

            panels = file_mgr.load_json(PANELS_FILE, dict)
            config = panels.get(str(interaction.message.id), {})
            if not config:
                await interaction.followup.send("❌ パネルデータが見つかりません。", ephemeral=True)
                return

            cost = config.get("cost", 0)
            user_id = str(interaction.user.id)
            data = economy_cog.load_data()

            if user_id not in data:
                data[user_id] = economy_cog.get_default_user_data()

            if data[user_id].get('money', 0) < cost:
                await interaction.followup.send(f"❌ 所持金が足りません！ (必要: {cost} {economy_cog.currency})", ephemeral=True)
                return

            data[user_id]['money'] -= cost
            economy_cog.save_data(data)
            if hasattr(economy_cog, 'update_web_data'):
                economy_cog.update_web_data()

            category = interaction.channel.category
            if not category:
                await interaction.followup.send("❌ カテゴリー内で実行してください。", ephemeral=True)
                return

            # デフォルトは公開設定
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(connect=True, view_channel=True),
                interaction.user: discord.PermissionOverwrite(connect=True, view_channel=True, manage_channels=True, move_members=True)
            }

            vc_base = config.get("vc_name", "部屋-")
            existing_count = len([vc for vc in category.voice_channels if vc.name.startswith(vc_base)])
            channel = await interaction.guild.create_voice_channel(
                name=f"{vc_base}{existing_count + 1}",
                category=category,
                user_limit=config.get("user_limit", 0),
                overwrites=overwrites,
                reason=f"パネルによるVC作成 (作成者: {interaction.user})"
            )

            duration_hours = config.get("duration", 0)
            expire_at = None
            if duration_hours > 0:
                expire_at = (datetime.now() + timedelta(hours=duration_hours)).isoformat()

            temp_vcs = file_mgr.load_json(TEMP_VCS_FILE, dict)
            temp_vcs[str(channel.id)] = {
                "owner_id": interaction.user.id,
                "expire_at": expire_at,
                "created_at": datetime.now().isoformat()
            }
            file_mgr.save_json(TEMP_VCS_FILE, temp_vcs)

            allowed_buttons = {
                "rename": config.get("allow_rename", True),
                "subtitle": config.get("allow_subtitle", True),
                "public": config.get("allow_public", True),
                "private": config.get("allow_private", True),
                "delete": config.get("allow_delete", True),
                "bitrate": False  # 通常パネルではビットレート変更は非表示
            }

            embed = discord.Embed(title="⚙️ VC管理パネル", description="作成者専用パネルです。", color=0x2b2d31)
            if expire_at:
                embed.description += f"\n\n⏳ このVCは **{duration_hours}時間後** に自動消去されます。"
            else:
                embed.description += "\n\n⏳ このVCの有効期限は **無制限** です。（無人時は5分後自動削除）"

            manage_view = VCManageView(interaction.user.id, allowed_buttons)
            manage_view.add_buttons_dynamically()
            await channel.send(content=interaction.user.mention, embed=embed, view=manage_view)

            if config.get("send_log", True):
                await self._send_vc_log(interaction, channel, cost, False)

            await interaction.followup.send(f"✅ {channel.mention} を作成しました！", ephemeral=True)

        except discord.Forbidden:
            await interaction.followup.send("❌ 権限不足のためVCを作成できません。", ephemeral=True)
        except Exception:
            logger.error(f"VC作成エラー: {traceback.format_exc()}")
            await interaction.followup.send("❌ 作成に失敗しました。", ephemeral=True)

    async def _send_vc_log(self, interaction: discord.Interaction, channel: discord.VoiceChannel, cost: int, is_private: bool):
        try:
            panels = file_mgr.load_json(PANELS_FILE, dict)
            config = panels.get(str(interaction.message.id), {})
            log_channel_id = config.get("specific_log_channel_id")
            if not log_channel_id:
                log_config = file_mgr.load_json(LOG_CONFIG_FILE, dict)
                log_channel_id = log_config.get(str(interaction.guild.id))

            if not log_channel_id:
                return

            log_channel = interaction.guild.get_channel(log_channel_id)
            if not log_channel:
                return

            perms = log_channel.permissions_for(interaction.guild.me)
            if not perms.send_messages or not perms.embed_links:
                logger.warning(f"ログチャンネル {log_channel.name} に送信権限がありません。")
                return

            economy_cog = interaction.client.get_cog("Economy")
            currency = economy_cog.currency if economy_cog else "単位"

            embed = discord.Embed(title="🔊 ボイスチャンネル作成ログ", color=0x2ecc71, timestamp=datetime.now())
            embed.add_field(name="実行者", value=f"{interaction.user.mention}\nID: `{interaction.user.id}`", inline=False)
            embed.add_field(name="作成チャンネル", value=f"{channel.mention}\nID: `{channel.id}`", inline=True)
            embed.add_field(name="設定タイプ", value="🔓 公開", inline=True)
            embed.add_field(name="支払い費用", value=f"{cost} {currency}", inline=True)
            embed.set_thumbnail(url=interaction.user.display_avatar.url)

            await log_channel.send(embed=embed)
        except Exception as e:
            logger.error(f"ログ送信エラー: {e}")


# --- 招待用ユーザー選択メニュー ---
class VCInviteSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="招待したいユーザーを選択してください", min_values=1, max_values=5)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            for user in self.values:
                await interaction.channel.set_permissions(user, connect=True, view_channel=True)
            users_str = ", ".join(u.display_name for u in self.values)
            await interaction.followup.send(f"✅ {users_str} を招待しました。", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ 権限不足のため招待できませんでした。", ephemeral=True)
        except Exception:
            logger.error(f"招待エラー: {traceback.format_exc()}")
            await interaction.followup.send("❌ 招待処理中にエラーが発生しました。", ephemeral=True)


# --- VC管理パネル（作成者専用） ---
class VCManageView(discord.ui.View):
    def __init__(self, owner_id: Optional[int] = None, allowed_buttons: Optional[Dict[str, bool]] = None):
        super().__init__(timeout=None)
        self.owner_id = owner_id

        # デフォルト設定
        if allowed_buttons is None:
            allowed_buttons = {
                "rename": True,
                "subtitle": True,
                "public": True,
                "private": True,
                "delete": True,
                "bitrate": False
            }

        # 各ボタンの表示/非表示を個別に設定するフラグとして保存
        self.allowed_buttons = allowed_buttons

    def add_buttons_dynamically(self):
        """許可されたボタンのみを動的に追加"""
        # 既存のボタンをクリア
        self.clear_items()

        # ユーザーを招待（常に表示）
        self.add_item(self.invite_user)

        if self.allowed_buttons.get("rename", True):
            self.add_item(self.rename)
        if self.allowed_buttons.get("subtitle", True):
            self.add_item(self.subtitle)
        if self.allowed_buttons.get("bitrate", False):
            self.add_item(self.change_bitrate)
        if self.allowed_buttons.get("public", True):
            self.add_item(self.public)
        if self.allowed_buttons.get("private", True):
            self.add_item(self.private)
        if self.allowed_buttons.get("delete", True):
            self.add_item(self.delete)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        if self.owner_id and interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ このチャンネルの作成者のみ操作可能です。", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="ユーザーを招待", style=discord.ButtonStyle.blurple, custom_id="vc_manage_invite")
    async def invite_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View()
        view.add_item(VCInviteSelect())
        await interaction.response.send_message("招待するメンバーを選んでください", view=view, ephemeral=True)

    @discord.ui.button(label="名前変更", style=discord.ButtonStyle.gray, custom_id="vc_manage_rename")
    async def rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = discord.ui.Modal(title="チャンネル名変更")
        new_name_input = discord.ui.TextInput(label="新しい名前", placeholder="チャンネル名を入力", max_length=100)
        modal.add_item(new_name_input)

        async def modal_submit(it: discord.Interaction):
            await it.response.defer(ephemeral=True)
            new_name = new_name_input.value.strip()
            if not new_name:
                await it.followup.send("❌ 名前が空です。", ephemeral=True)
                return
            try:
                await interaction.channel.edit(name=new_name)
                await it.followup.send(f"✅ 名前を `{new_name}` に変更しました。", ephemeral=True)
            except discord.Forbidden:
                await it.followup.send("❌ チャンネル名の変更権限がありません。", ephemeral=True)
            except Exception:
                logger.error(f"名前変更エラー: {traceback.format_exc()}")
                await it.followup.send("❌ 名前の変更に失敗しました。", ephemeral=True)

        modal.on_submit = modal_submit
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="サブタイトル変更", style=discord.ButtonStyle.gray, custom_id="vc_manage_subtitle")
    async def subtitle(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = discord.ui.Modal(title="サブタイトル変更")
        subtitle_input = discord.ui.TextInput(label="新しいサブタイトル", placeholder="ステータスを入力（空欄でクリア）", required=False, max_length=128)
        modal.add_item(subtitle_input)

        async def modal_submit(it: discord.Interaction):
            await it.response.defer(ephemeral=True)
            try:
                await interaction.channel.edit(status=subtitle_input.value or "")
                status_text = f"`{subtitle_input.value}`" if subtitle_input.value else "クリア"
                await it.followup.send(f"✅ サブタイトルを {status_text} に変更しました。", ephemeral=True)
            except Exception:
                logger.error(f"サブタイトル変更エラー: {traceback.format_exc()}")
                await it.followup.send("❌ サブタイトルの変更に失敗しました。", ephemeral=True)

        modal.on_submit = modal_submit
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="ビットレート変更", style=discord.ButtonStyle.gray, custom_id="vc_manage_bitrate")
    async def change_bitrate(self, interaction: discord.Interaction, button: discord.ui.Button):
        # チャンネルタイプを判定
        is_stage = isinstance(interaction.channel, discord.StageChannel)
        max_bitrate = 128 if is_stage else 256

        modal = discord.ui.Modal(title="ビットレート変更")
        bitrate_input = discord.ui.TextInput(
            label=f"ビットレート (kbps, 8-{max_bitrate})",
            placeholder=f"現在: {interaction.channel.bitrate // 1000} kbps",
            default=str(interaction.channel.bitrate // 1000),
            max_length=3
        )
        modal.add_item(bitrate_input)

        async def modal_submit(it: discord.Interaction):
            await it.response.defer(ephemeral=True)
            try:
                new_bitrate = int(bitrate_input.value)
                if new_bitrate < 8 or new_bitrate > max_bitrate:
                    await it.followup.send(f"❌ ビットレートは8〜{max_bitrate}の範囲で設定してください。", ephemeral=True)
                    return
                await interaction.channel.edit(bitrate=new_bitrate * 1000)
                await it.followup.send(f"✅ ビットレートを `{new_bitrate} kbps` に変更しました。", ephemeral=True)
            except ValueError:
                await it.followup.send("❌ 数値を入力してください。", ephemeral=True)
            except Exception:
                logger.error(f"ビットレート変更エラー: {traceback.format_exc()}")
                await it.followup.send("❌ ビットレートの変更に失敗しました。", ephemeral=True)

        modal.on_submit = modal_submit
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="公開にする", style=discord.ButtonStyle.green, custom_id="vc_manage_public")
    async def public(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            await interaction.channel.set_permissions(interaction.guild.default_role, connect=True, view_channel=True)
            await interaction.followup.send("✅ チャンネルを全員に公開しました！", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ 権限変更の権限がありません。", ephemeral=True)
        except Exception:
            logger.error(f"公開化エラー: {traceback.format_exc()}")
            await interaction.followup.send("❌ 公開設定に失敗しました。", ephemeral=True)

    @discord.ui.button(label="プライベートにする", style=discord.ButtonStyle.red, custom_id="vc_manage_private")
    async def private(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            await interaction.channel.set_permissions(interaction.guild.default_role, connect=False, view_channel=False)
            await interaction.channel.set_permissions(interaction.user, connect=True, view_channel=True)
            await interaction.followup.send("🔒 チャンネルをプライベートに設定しました！\nユーザーを招待するには「ユーザーを招待」ボタンを使ってください。", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ 権限変更の権限がありません。", ephemeral=True)
        except Exception:
            logger.error(f"プライベート化エラー: {traceback.format_exc()}")
            await interaction.followup.send("❌ プライベート設定に失敗しました。", ephemeral=True)

    @discord.ui.button(label="削除", style=discord.ButtonStyle.danger, custom_id="vc_manage_delete")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View()

        async def confirm_callback(it: discord.Interaction):
            await interaction.channel.delete()

        async def cancel_callback(it: discord.Interaction):
            await it.response.edit_message(content="キャンセルしました。", view=None)

        confirm_btn = discord.ui.Button(label="削除する", style=discord.ButtonStyle.danger, custom_id="vc_confirm_delete")
        confirm_btn.callback = confirm_callback
        cancel_btn = discord.ui.Button(label="キャンセル", style=discord.ButtonStyle.secondary, custom_id="vc_cancel_delete")
        cancel_btn.callback = cancel_callback

        view.add_item(cancel_btn)
        view.add_item(confirm_btn)

        await interaction.response.send_message("⚠️ このチャンネルを削除しますか？この操作は元に戻せません。", view=view, ephemeral=True)


# --- メインコグ ---
class Panel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cleanup_task.start()

    def cog_unload(self):
        self.cleanup_task.cancel()

    @tasks.loop(minutes=1)
    async def cleanup_task(self):
        try:
            temp_vcs = file_mgr.load_json(TEMP_VCS_FILE, dict)
            now = datetime.now()
            to_delete = []

            for vc_id_str, info in temp_vcs.items():
                if not isinstance(info, dict):
                    to_delete.append(vc_id_str)
                    continue

                channel = self.bot.get_channel(int(vc_id_str))
                if not channel:
                    to_delete.append(vc_id_str)
                    continue

                expire_at_str = info.get("expire_at")
                if expire_at_str:
                    expire_at = datetime.fromisoformat(expire_at_str)
                    if now >= expire_at:
                        try:
                            await channel.delete(reason="期限切れによる自動削除")
                            logger.info(f"期限切れチャンネルを削除: {channel.name}")
                            to_delete.append(vc_id_str)
                        except Exception as e:
                            logger.error(f"チャンネル削除エラー ({channel.name}): {e}")
                            to_delete.append(vc_id_str)

            if to_delete:
                for vc_id in to_delete:
                    temp_vcs.pop(vc_id, None)
                file_mgr.save_json(TEMP_VCS_FILE, temp_vcs)

        except Exception as e:
            logger.error(f"クリーンアップタスクエラー: {e}")

    @cleanup_task.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

    # --- 通常パネルコマンド ---
    @app_commands.command(name="set_panel", description="VC作成パネルを設置します")
    @app_commands.describe(
        allow_rename="作成者に部屋名の変更を許可するか",
        allow_subtitle="作成者にサブタイトルの変更を許可するか",
        allow_public="作成者に公開設定を許可するか",
        allow_private="作成者にプライベート設定を許可するか",
        allow_delete="作成者に部屋の即時削除を許可するか",
        send_log="ログを送信するか",
        log_channel="専用のログ送信先チャンネル"
    )
    @app_commands.default_permissions(administrator=True)
    async def set_panel(
        self,
        interaction: discord.Interaction,
        allow_rename: bool = True,
        allow_subtitle: bool = True,
        allow_public: bool = True,
        allow_private: bool = True,
        allow_delete: bool = True,
        send_log: bool = True,
        log_channel: Optional[discord.TextChannel] = None
    ):
        class NormalPanelModal(discord.ui.Modal, title="パネル設置設定"):
            vc_name = discord.ui.TextInput(label="VC名の接頭辞", default="部屋-", placeholder="例: 部屋-", max_length=50)
            vc_limit = discord.ui.TextInput(label="人数制限 (0で無制限)", default="0", max_length=3)
            vc_cost = discord.ui.TextInput(label="作成費用", default="0", max_length=10)
            vc_duration = discord.ui.TextInput(label="有効期限 (時間、0で無制限)", default="0", max_length=3)

            async def on_submit(self, modal_interaction: discord.Interaction):
                await modal_interaction.response.defer(ephemeral=True)
                try:
                    limit = int(self.vc_limit.value)
                    cost = int(self.vc_cost.value)
                    duration = int(self.vc_duration.value)

                    if limit < 0 or limit > 99:
                        await modal_interaction.followup.send("❌ 人数制限は0〜99の範囲で設定してください。", ephemeral=True)
                        return
                    if cost < 0:
                        await modal_interaction.followup.send("❌ 費用は0以上の数値を設定してください。", ephemeral=True)
                        return
                    if duration < 0:
                        await modal_interaction.followup.send("❌ 有効期限は0以上の数値を設定してください。", ephemeral=True)
                        return

                    economy_cog = modal_interaction.client.get_cog("Economy")
                    currency = economy_cog.currency if economy_cog else "星"

                    desc = f"ボタンを押すとボイスチャンネルを作成します。\n\n**費用:** `{cost}` {currency}\n**制限:** `{'無制限' if limit == 0 else f'{limit}人'}`\n**有効期限:** `{'無制限' if duration == 0 else f'{duration}時間'}`"
                    embed = discord.Embed(title="自動VC作成パネル", description=desc, color=0xFFD700)
                    message = await modal_interaction.channel.send(embed=embed, view=VCPanelView())

                    panels = file_mgr.load_json(PANELS_FILE, dict)
                    panels[str(message.id)] = {
                        "vc_name": self.vc_name.value, "user_limit": limit, "cost": cost,
                        "duration": duration,
                        "allow_rename": allow_rename, "allow_subtitle": allow_subtitle,
                        "allow_public": allow_public, "allow_private": allow_private,
                        "allow_delete": allow_delete, "send_log": send_log,
                        "specific_log_channel_id": log_channel.id if log_channel else None
                    }
                    file_mgr.save_json(PANELS_FILE, panels)
                    await modal_interaction.followup.send("✅ パネルを設置しました。", ephemeral=True)
                except ValueError:
                    await modal_interaction.followup.send("❌ 数値には整数を入力してください。", ephemeral=True)
                except Exception:
                    logger.error(f"パネル設置エラー: {traceback.format_exc()}")
                    await modal_interaction.followup.send("❌ パネルの設定に失敗しました。", ephemeral=True)

        await interaction.response.send_modal(NormalPanelModal())

    # --- 高級パネルコマンド（シンプル版） ---
    @app_commands.command(name="set_premium_panel", description="🌟 高級チャンネル作成パネルを設置します")
    @app_commands.describe(
        send_log="ログを送信するか",
        log_channel="専用のログ送信先チャンネル"
    )
    @app_commands.default_permissions(administrator=True)
    async def set_premium_panel(
        self,
        interaction: discord.Interaction,
        send_log: bool = True,
        log_channel: Optional[discord.TextChannel] = None
    ):
        opts = {
            "send_log": send_log,
            "specific_log_channel_id": log_channel.id if log_channel else None
        }
        await interaction.response.send_modal(PremiumPanelModal(opts))

    # --- 同期コマンド ---
    @app_commands.command(name="sync", description="スラッシュコマンドを手動同期します")
    @app_commands.default_permissions(administrator=True)
    async def sync_commands(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            self.bot.tree.copy_global_to(guild=interaction.guild)
            await self.bot.tree.sync(guild=interaction.guild)
            commands_list = [cmd.name for cmd in self.bot.tree.get_commands(guild=interaction.guild)]
            await interaction.followup.send(
                f"✅ このサーバーにコマンドを同期しました！\n登録済み: {', '.join(commands_list)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"❌ 同期エラー: {e}", ephemeral=True)

    # --- ログチャンネル設定コマンド ---
    @app_commands.command(name="set_log_channel", description="チャンネル作成の全体共通ログ送信先を設定します")
    @app_commands.describe(channel="ログを送信するテキストチャンネル")
    @app_commands.default_permissions(administrator=True)
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        try:
            perms = channel.permissions_for(interaction.guild.me)
            if not perms.send_messages or not perms.embed_links:
                await interaction.followup.send(f"❌ {channel.mention} にメッセージ送信または埋め込み送信の権限がありません。", ephemeral=True)
                return
            log_config = file_mgr.load_json(LOG_CONFIG_FILE, dict)
            log_config[str(interaction.guild.id)] = channel.id
            file_mgr.save_json(LOG_CONFIG_FILE, log_config)
            await interaction.followup.send(f"✅ 全体ログ送信先を {channel.mention} に設定しました。", ephemeral=True)
        except Exception:
            logger.error(f"ログ設定エラー: {traceback.format_exc()}")
            await interaction.followup.send("❌ 設定の保存に失敗しました。", ephemeral=True)

    # --- イベントリスナー ---
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(VCPanelView())
        self.bot.add_view(VCManageView())

        print("🔍 同期処理を開始します...")

        try:
            await self.bot.tree.sync()
            print("✅ グローバルコマンドを同期しました")
        except Exception as e:
            print(f"❌ グローバル同期エラー: {type(e).__name__}: {e}")
            traceback.print_exc()

        try:
            commands_list = [cmd.name for cmd in self.bot.tree.get_commands()]
            print(f"📋 登録コマンド一覧: {commands_list}")

            if "set_premium_panel" in commands_list:
                print("✅ set_premium_panel は登録済み")
            else:
                print("⚠️ set_premium_panel が未登録！")
        except Exception as e:
            print(f"❌ コマンド一覧取得エラー: {e}")

        logger.info("✅ Panel Cog: 永続View登録完了")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel and len(before.channel.members) == 0:
            temp_vcs = file_mgr.load_json(TEMP_VCS_FILE, dict)
            if str(before.channel.id) in temp_vcs:
                await asyncio.sleep(300)
                channel = self.bot.get_channel(before.channel.id)
                if channel and len(channel.members) == 0:
                    try:
                        await channel.delete(reason="無人状態が5分以上続いたため自動削除")
                        temp_vcs = file_mgr.load_json(TEMP_VCS_FILE, dict)
                        temp_vcs.pop(str(before.channel.id), None)
                        file_mgr.save_json(TEMP_VCS_FILE, temp_vcs)
                        logger.info(f"無人チャンネルを自動削除: {channel.name}")
                    except Exception as e:
                        logger.error(f"無人チャンネル削除エラー: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Panel(bot))