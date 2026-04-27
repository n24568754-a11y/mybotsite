import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# --- 追加: Firebase用のライブラリ ---
import firebase_admin
from firebase_admin import credentials
# ------------------------------

load_dotenv()

# --- 修正: Firebaseの初期化設定 ---
# serviceAccountKey.json をGitHub管理フォルダの「1つ外」に移動した場合のパス指定
# ../ は「1つ上の階層」という意味です
try:
    cred = credentials.Certificate("../serviceAccountKey.json")
    firebase_admin.initialize_app(
        cred, {"databaseURL": "https://mybot-4e6b1-default-rtdb.firebaseio.com/"}
    )
except Exception as e:
    print(f"Firebaseの初期化に失敗しました。パスを確認してください: {e}")
# ------------------------------


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        # 管理者のみが使用できるコマンドを隠す設定はCog側の各コマンドで行うのが一般的ですが、
        # ここでは基本設定を定義します。
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # cogsフォルダ内の各機能を読み込む
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                await self.load_extension(f"cogs.{filename[:-3]}")
        await self.tree.sync()

    async def on_ready(self):
        print(f"ログインしました: {self.user.name}")

        # Economy Cogを取得して起動時にFirebaseへデータを同期
        economy_cog = self.get_cog("Economy")
        if economy_cog:
            success = economy_cog.update_web_data()
            if success:
                print("✅ Firebaseへデータを正常に送信しました。")
            else:
                print(
                    "⚠️ データの送信に失敗しました。Economy Cogのupdate_web_dataを確認してください。"
                )


bot = MyBot()
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
