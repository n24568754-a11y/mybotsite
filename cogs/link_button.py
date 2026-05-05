import discord
from discord import app_commands
from discord.ext import commands

class LinkButtonView(discord.ui.View):
    """
    URLへジャンプするボタンを表示するViewクラス
    """
    def __init__(self, label: str, url: str):
        super().__init__(timeout=None)  # 永続的に表示させる場合はtimeout=None
        # ボタンを追加
        self.add_item(discord.ui.Button(label=label, url=url))

class LinkButton(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="send_link",
        description="指定したチャンネルにボタン付きリンクメッセージを送信します（管理者用）"
    )
    @app_commands.describe(
        channel="送信先のチャンネル",
        link="ジャンプ先のURL",
        text="メッセージ本文",
        button_label="ボタンに表示する文字"
    )
    @app_commands.default_permissions(administrator=True)  # 管理者権限を持つユーザーのみ表示・実行可能
    async def send_link(
        self,
        interaction: discord.Interaction,
        channel: discord.abc.GuildChannel,
        link: str,
        text: str = "下のボタンを押してリンクを開いてください。",
        button_label: str = "リンクを開く"
    ):
        # 指定されたチャンネルがテキスト送受信可能かチェック
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("テキストチャンネルを指定してください。", ephemeral=True)
            return

        # ボタンViewを作成
        view = LinkButtonView(label=button_label, url=link)

        try:
            # 指定されたチャンネルにメッセージを送信
            await channel.send(content=text, view=view)
            # 実行者には完了報告を（自分にしか見えないメッセージ）
            await interaction.response.send_message(f"✅ {channel.mention} にメッセージを送信しました。", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Botに対象チャンネルでの送信権限がありません。", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(LinkButton(bot))
