import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os

# --- 設定保存用のファイルパス（実行ファイルと同じ場所に固定） ---
current_dir = os.path.dirname(os.path.abspath(__file__))
# cogsフォルダの外（メインのbotファイルと同じ階層）に保存する場合
PANELS_FILE = os.path.join(os.path.dirname(current_dir), "panels.json")

def load_panels():
    if os.path.exists(PANELS_FILE):
        try:
            with open(PANELS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ ファイル読み込みエラー: {e}")
    return {}

def save_panels(data):
    try:
        with open(PANELS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"✅ 設定を保存しました: {PANELS_FILE}")
    except Exception as e:
        print(f"❌ ファイル保存エラー: {e}")

class VCPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="VC作成", style=discord.ButtonStyle.green, custom_id="create_vc_btn_persistent")
    async def create_vc(self, interaction: discord.Interaction, button: discord.ui.Button):
        economy_cog = interaction.client.get_cog("Economy")
        if not economy_cog:
            return await interaction.response.send_message("❌ 経済システムが見つかりません。", ephemeral=True)

        panels = load_panels()
        config = panels.get(str(interaction.message.id), {})

        vc_base = config.get("vc_name", "vc")
        limit = config.get("user_limit", 0)
        cost = config.get("cost", 0)

        user_id = str(interaction.user.id)
        data = economy_cog.load_data()
        if user_id not in data:
            data[user_id] = economy_cog.get_default_user_data()

        current_money = data[user_id].get('money', 0)
        if current_money < cost:
            return await interaction.response.send_message(f"❌ 所持金が足りません！", ephemeral=True)

        data[user_id]['money'] -= cost
        economy_cog.save_data(data)
        if hasattr(economy_cog, 'update_web_data'):
            economy_cog.update_web_data()

        category = interaction.channel.category
        if not category:
            return await interaction.response.send_message("カテゴリー内で実行してください。", ephemeral=True)

        existing_count = len([vc for vc in category.voice_channels if vc.name.startswith(vc_base)])
        new_name = f"{vc_base}{existing_count + 1}"

        try:
            channel = await interaction.guild.create_voice_channel(name=new_name, category=category, user_limit=limit)
            await interaction.response.send_message(f"✅ {channel.mention} を作成しました！", ephemeral=True)

            if cost <= 0:
                await asyncio.sleep(120)
                try:
                    current_channel = interaction.guild.get_channel(channel.id)
                    if current_channel and len(current_channel.members) == 0:
                        await current_channel.delete()
                except:
                    pass
        except Exception as e:
            data[user_id]['money'] += cost
            economy_cog.save_data(data)
            await interaction.response.send_message(f"❌ 作成失敗: {e}", ephemeral=True)

class PanelConfigModal(discord.ui.Modal, title="パネル設置設定"):
    p_title = discord.ui.TextInput(label="タイトル", default="自動VC作成")
    p_desc = discord.ui.TextInput(label="説明文", style=discord.TextStyle.paragraph, default="ボタンを押すとVCを作成します。")
    vc_name = discord.ui.TextInput(label="VC名", default="vc")
    vc_limit = discord.ui.TextInput(label="人数制限", default="0")
    vc_cost = discord.ui.TextInput(label="費用", default="0")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            limit = int(self.vc_limit.value)
            cost = int(self.vc_cost.value)
        except:
            return await interaction.response.send_message("数値を入れてください。", ephemeral=True)

        economy_cog = interaction.client.get_cog("Economy")
        currency = economy_cog.currency if economy_cog else "星"

        embed = discord.Embed(title=self.p_title.value, description=f"{self.p_desc.value}\n\n**費用:** `{cost}` {currency}", color=0xFFD700)
        view = VCPanelView()
        message = await interaction.channel.send(embed=embed, view=view)

        # 保存処理
        panels = load_panels()
        panels[str(message.id)] = {
            "vc_name": self.vc_name.value,
            "user_limit": limit,
            "cost": cost
        }
        save_panels(panels)

        await interaction.response.send_message("✅ 設置完了", ephemeral=True)

class Panel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_panel", description="パネル設置")
    @app_commands.default_permissions(administrator=True)
    async def set_panel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PanelConfigModal())

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(VCPanelView())

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel and len(before.channel.members) == 0:
            await asyncio.sleep(300)
            try:
                current_channel = self.bot.get_channel(before.channel.id)
                if current_channel and len(current_channel.members) == 0:
                    await current_channel.delete()
            except:
                pass

async def setup(bot):
    await bot.add_cog(Panel(bot))
