import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os
import traceback
from datetime import datetime

# --- 設定保存用のファイルパス ---
current_dir = os.path.dirname(os.path.abspath(__file__))
# panels.json にログチャンネル設定も保存します
PANELS_FILE = os.path.join(os.path.dirname(current_dir), "panels.json")
TEMP_VCS_FILE = os.path.join(os.path.dirname(current_dir), "temp_vcs.json")

def load_json(path, default_type=dict):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ ファイル読み込みエラー({path}): {e}")
    return default_type()

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"❌ ファイル保存エラー({path}): {e}")

# --- 招待用のユーザー選択メニュー ---
class VCInviteSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="招待したいユーザーを選択してください", min_values=1, max_values=5)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            for user in self.values:
                await interaction.channel.set_permissions(user, connect=True, view_channel=True)
            users_str = ", ".join([u.display_name for u in self.values])
            await interaction.followup.send(f"✅ {users_str} を招待しました。", ephemeral=True)
        except Exception as e:
            print(f"❌ [招待エラー]: {traceback.format_exc()}")

# --- VC内の操作用パネル ---
class VCManageView(discord.ui.View):
    def __init__(self, owner_id=None):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        if self.owner_id and interaction.user.id != self.owner_id:
            await interaction.response.send_message("作成者のみ操作可能です。", ephemeral=True)
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
        new_name_input = discord.ui.TextInput(label="新しい名前", placeholder="部屋の名前を入力")
        modal.add_item(new_name_input)

        async def modal_submit(it: discord.Interaction):
            await it.response.defer(ephemeral=True)
            try:
                await interaction.channel.edit(name=new_name_input.value)
                await it.followup.send(f"名前を `{new_name_input.value}` に変更しました。", ephemeral=True)
            except:
                print(f"❌ [名前変更エラー]: {traceback.format_exc()}")

        modal.on_submit = modal_submit
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="公開にする", style=discord.ButtonStyle.green, custom_id="vc_manage_public")
    async def make_public(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            await interaction.channel.set_permissions(interaction.guild.default_role, connect=True, view_channel=True)
            await interaction.followup.send("チャンネルを全員に公開しました！", ephemeral=True)
        except:
            print(f"❌ [公開化エラー]: {traceback.format_exc()}")

    @discord.ui.button(label="削除", style=discord.ButtonStyle.red, custom_id="vc_manage_delete")
    async def delete_now(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

# --- 設置されたパネルのボタン ---
class VCPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="VC作成", style=discord.ButtonStyle.green, custom_id="idx3_create_vc_persistent")
    async def create_vc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            economy_cog = interaction.client.get_cog("Economy")
            if not economy_cog:
                return await interaction.followup.send("❌ 経済システムが非アクティブです。", ephemeral=True)

            panels = load_json(PANELS_FILE)
            config = panels.get(str(interaction.message.id), {})
            if not config:
                return await interaction.followup.send("❌ パネルデータが見つかりません。", ephemeral=True)

            cost = config.get("cost", 0)
            user_id = str(interaction.user.id)
            data = economy_cog.load_data()

            if user_id not in data:
                data[user_id] = economy_cog.get_default_user_data()

            if data[user_id].get('money', 0) < cost:
                return await interaction.followup.send(f"❌ 所持金が足りません！ (必要: {cost})", ephemeral=True)

            data[user_id]['money'] -= cost
            economy_cog.save_data(data)
            if hasattr(economy_cog, 'update_web_data'):
                economy_cog.update_web_data()

            category = interaction.channel.category
            if not category:
                return await interaction.followup.send("❌ カテゴリー内で実行してください。", ephemeral=True)

            is_private = config.get("is_private", False)
            overwrites = {interaction.guild.default_role: discord.PermissionOverwrite(connect=True, view_channel=True)}
            if is_private:
                overwrites = {
                    interaction.guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=False),
                    interaction.user: discord.PermissionOverwrite(connect=True, view_channel=True)
                }

            vc_base = config.get("vc_name", "vc")
            existing_count = len([vc for vc in category.voice_channels if vc.name.startswith(vc_base)])
            channel = await interaction.guild.create_voice_channel(
                name=f"{vc_base}{existing_count + 1}", 
                category=category, 
                user_limit=config.get("user_limit", 0),
                overwrites=overwrites
            )

            temp_vcs = load_json(TEMP_VCS_FILE, list)
            temp_vcs.append(channel.id)
            save_json(TEMP_VCS_FILE, temp_vcs)

            if is_private:
                embed = discord.Embed(title="⚙️ VC管理パネル", description="作成者専用パネルです。", color=0x2b2d31)
                await channel.send(content=interaction.user.mention, embed=embed, view=VCManageView(interaction.user.id))

            # --- ログ送信処理の追加 ---
            panel_cog = interaction.client.get_cog("Panel")
            if panel_cog:
                await panel_cog.send_vc_log(
                    guild=interaction.guild,
                    user=interaction.user,
                    channel=channel,
                    cost=cost,
                    is_private=is_private
                )

            await interaction.followup.send(f"✅ {channel.mention} を作成しました！", ephemeral=True)

        except Exception:
            print(f"❌ [作成エラー]: {traceback.format_exc()}")
            await interaction.followup.send(f"❌ 作成に失敗しました。", ephemeral=True)

# --- 安定版: 単一モーダル (項目を5つに絞りエラーを回避) ---
class PanelConfigModal(discord.ui.Modal, title="パネル設置設定"):
    vc_name = discord.ui.TextInput(label="VC名の接頭辞", default="部屋-", placeholder="例: 部屋-")
    vc_limit = discord.ui.TextInput(label="人数制限 (0で無制限)", default="0")
    vc_cost = discord.ui.TextInput(label="作成費用", default="0")
    is_private = discord.ui.TextInput(label="非公開設定 (yes/no)", default="no")
    p_title = discord.ui.TextInput(label="パネルのタイトル", default="自動VC作成パネル")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            limit = int(self.vc_limit.value)
            cost = int(self.vc_cost.value)
            private_val = self.is_private.value.lower() == "yes"

            economy_cog = interaction.client.get_cog("Economy")
            currency = economy_cog.currency if economy_cog else "星"

            type_label = "プライベート" if private_val else "公開"
            desc = (
                f"ボタンを押すとボイスチャンネルを作成します。\n\n"
                f"**費用:** `{cost}` {currency}\n"
                f"**タイプ:** `{type_label}`\n"
                f"**制限:** `{'無制限' if limit == 0 else f'{limit}人'}`"
            )

            embed = discord.Embed(title=self.p_title.value, description=desc, color=0xFFD700)
            message = await interaction.channel.send(embed=embed, view=VCPanelView())

            panels = load_json(PANELS_FILE)
            panels[str(message.id)] = {
                "vc_name": self.vc_name.value,
                "user_limit": limit,
                "cost": cost,
                "is_private": private_val
            }
            save_json(PANELS_FILE, panels)
            await interaction.followup.send("✅ パネルを設置しました。", ephemeral=True)
        except Exception:
            print(f"❌ [パネル設置エラー]: {traceback.format_exc()}")
            await interaction.followup.send("❌ 数値の入力が正しくありません。やり直してください。", ephemeral=True)

class Panel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_panel", description="VC作成パネルを設置します")
    @app_commands.default_permissions(administrator=True)
    async def set_panel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PanelConfigModal())

    # --- ログチャンネル設定コマンドを追加 ---
    @app_commands.command(name="set_log_channel", description="VC作成のログ送信先を設定します")
    @app_commands.describe(channel="ログを送信するテキストチャンネル")
    @app_commands.default_permissions(administrator=True)
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        try:
            panels = load_json(PANELS_FILE)
            if "log_config" not in panels:
                panels["log_config"] = {}

            panels["log_config"][str(interaction.guild.id)] = channel.id
            save_json(PANELS_FILE, panels)

            await interaction.followup.send(f"✅ ログ送信先を {channel.mention} に設定しました。", ephemeral=True)
        except Exception:
            print(f"❌ [ログ設定エラー]: {traceback.format_exc()}")
            await interaction.followup.send("❌ 設定の保存に失敗しました。", ephemeral=True)

    # --- ログ送信用の内部メソッド ---
    async def send_vc_log(self, guild, user, channel, cost, is_private):
        panels = load_json(PANELS_FILE)
        log_channel_id = panels.get("log_config", {}).get(str(guild.id))

        if not log_channel_id:
            return

        log_channel = guild.get_channel(log_channel_id)
        if not log_channel:
            return

        economy_cog = self.bot.get_cog("Economy")
        currency = economy_cog.currency if economy_cog else "単位"

        embed = discord.Embed(
            title="🔊 ボイスチャンネル作成ログ", 
            color=0x2ecc71, 
            timestamp=datetime.now()
        )
        embed.add_field(name="実行者", value=f"{user.mention}\nID: `{user.id}`", inline=False)
        embed.add_field(name="作成チャンネル", value=f"{channel.name}\nID: `{channel.id}`", inline=True)
        embed.add_field(name="設定タイプ", value="🔒 非公開" if is_private else "🔓 公開", inline=True)
        embed.add_field(name="支払い費用", value=f"{cost} {currency}", inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)

        try:
            await log_channel.send(embed=embed)
        except:
            print(f"❌ [ログ送信失敗]: チャンネルへのメッセージ送信権限を確認してください。")

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(VCPanelView())
        self.bot.add_view(VCManageView())
        print(f"✅ Panel Cog: 永続View登録完了")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel and len(before.channel.members) == 0:
            temp_vcs = load_json(TEMP_VCS_FILE, list)
            if before.channel.id in temp_vcs:
                await asyncio.sleep(300) 
                chan = self.bot.get_channel(before.channel.id)
                if chan and len(chan.members) == 0:
                    try:
                        await chan.delete()
                        if before.channel.id in temp_vcs:
                            temp_vcs.remove(before.channel.id)
                        save_json(TEMP_VCS_FILE, temp_vcs)
                    except: pass

async def setup(bot):
    await bot.add_cog(Panel(bot))
