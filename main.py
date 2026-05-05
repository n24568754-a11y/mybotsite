import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# --- Firebase用のライブラリ ---
import firebase_admin
from firebase_admin import credentials

load_dotenv()

# --- Firebaseの初期化 (二重初期化防止ガード付き) ---
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate("../serviceAccountKey.json")
        firebase_admin.initialize_app(
            cred, {"databaseURL": "https://mybot-4e6b1-default-rtdb.firebaseio.com/"}
        )
        print("✅ Firebaseを初期化しました")
    except Exception as e:
        print(f"Firebaseの初期化に失敗しました: {e}")
else:
    # すでに初期化されている場合はスキップ
    pass

# --- Botクラスの定義 ---
class MyBot(commands.Bot):
    def __init__(self, delay_time, bot_index):
        intents = discord.Intents.all()
        super().__init__(command_prefix="t!", intents=intents)
        self.delay_time = delay_time 
        self.bot_index = bot_index # 何番目のBotか識別用

    async def setup_hook(self):
        # 1台目のメインBot
        if self.bot_index == 0:
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py"):
                    # panel.pyは4台目専用にするためメインからは除外
                    if filename == "panel.py": continue
                    try:
                        await self.load_extension(f"cogs.{filename[:-3]}")
                        print(f"✅ メインBot ({self.user.name}): {filename} をロードしました")
                    except Exception as e:
                        print(f"Failed to load {filename}: {e}")

        # 4台目のパネル専用Bot
        elif self.bot_index == 3:
            try:
                # 1. 経済システムをロード（ボタン処理でお金を使うため）
                await self.load_extension("cogs.economy")

                # 2. パネル機能をロード
                await self.load_extension("cogs.panel")

                # 3. 【修正ポイント】パネルBotからは /set_panel 以外の全コマンドを除去
                # これにより、パスワード設定コマンド等も含めて全て強制的に非表示にします
                for cmd in list(self.tree.get_commands()):
                    if cmd.name != "set_panel":
                        self.tree.remove_command(cmd.name)

                print(f"📋 パネルBot ({self.user.name}): コマンドを整理してロードしました")
            except Exception as e:
                print(f"Failed to load panel or economy cog: {e}")

        # 2台目・3台目のサブBot
        else:
            try:
                await self.load_extension("cogs.music")
                print(f"🎵 サブBot ({self.user.name}): 音楽機能のみロードしました")
            except Exception as e:
                print(f"Failed to load music for {self.user.name}: {e}")

        # コマンドの同期
        await self.tree.sync()

    async def on_ready(self):
        print(f"✅ ログインしました: {self.user.name} (反応遅延: {self.delay_time}秒)")

        # Firebaseへのデータ送信はメインBot(index 0)のみに限定（負荷軽減）
        if self.bot_index == 0:
            economy_cog = self.get_cog("Economy")
            if economy_cog:
                try:
                    success = economy_cog.update_web_data()
                    if success:
                        print(f"✅ {self.user.name}: Firebaseへデータを正常に送信しました。")
                except Exception as e:
                    print(f"⚠️ {self.user.name}: Firebase送信エラー: {e}")

# --- 複数Botの同時起動処理 ---
async def start_bots():
    tokens = [
        os.getenv("TOKEN1") or os.getenv("DISCORD_TOKEN"), 
        os.getenv("TOKEN2"),                              
        os.getenv("TOKEN3"),
        os.getenv("TOKEN4")  # 4台目のトークン
    ]

    tokens = [t for t in tokens if t]

    if not tokens:
        print("⚠️ 有効なトークンが.envに見つかりません。")
        return

    tasks = []
    for i, token in enumerate(tokens):
        bot = MyBot(delay_time=i * 0.8, bot_index=i)
        tasks.append(bot.start(token))

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(start_bots())
    except KeyboardInterrupt:
        print("Botを停止します...")
