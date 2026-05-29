import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import traceback
from dotenv import load_dotenv

# --- Firebase用のライブラリ ---
import firebase_admin
from firebase_admin import credentials

load_dotenv()

# --- Firebaseの初期化 ---
if not firebase_admin._apps:
    try:
        # main.pyから見たパスを指定
        cred_path = "./serviceAccountKey.json" 
        if not os.path.exists(cred_path):
            # 親ディレクトリも探す（既存ロジック維持）
            cred_path = "../serviceAccountKey.json"

        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(
                cred, {"databaseURL": "https://mybot-4e6b1-default-rtdb.firebaseio.com/"}
            )
            print(f"✅ Firebaseを初期化しました (Path: {cred_path})")
        else:
            print(f"⚠️ Firebase設定ファイルが見つかりません。")
    except Exception as e:
        print(f"Firebaseの初期化に失敗しました: {e}")

# --- Botクラスの定義 ---
class MyBot(commands.Bot):
    def __init__(self, delay_time, bot_index):
        intents = discord.Intents.all()
        super().__init__(command_prefix="t!", intents=intents)
        self.delay_time = delay_time 
        self.bot_index = bot_index

        # スラッシュコマンドのエラーハンドリング
        self.tree.on_error = self.on_tree_error

    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """スラッシュコマンド実行時のエラーを詳細に表示"""
        print(f"❌ [Command Error - Bot Index {self.bot_index}] {interaction.user.name}: {error}")
        traceback.print_exc()

        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"内部エラーが発生しました (Bot Index: {self.bot_index})", ephemeral=True)
            else:
                await interaction.followup.send("内部エラーが発生しました。", ephemeral=True)
        except:
            pass

    async def setup_hook(self):
        # 起動直後のAPI負荷分散
        await asyncio.sleep(self.delay_time)

        # --- 各インデックスに応じたCogのロード ---
        try:
            # Index 0: メイン機能 (panel.py以外をロード)
            if self.bot_index == 0:
                if os.path.exists("./cogs"):
                    for filename in os.listdir("./cogs"):
                        if filename.endswith(".py") and filename != "panel.py":
                            await self.load_extension(f"cogs.{filename[:-3]}")
                            print(f"✅ メインBot ({self.bot_index}): {filename} をロード")

            # Index 3: パネル・経済専用機
            elif self.bot_index == 3:
                # 依存関係があるため economy -> panel の順でロード
                await self.load_extension("cogs.economy")
                await self.load_extension("cogs.panel")

                # パネルBotが保持するコマンドのホワイトリスト
                allowed_commands = ["set_panel", "set_log_channel", "set_premium_panel", "sync"]

                # パネルBotは指定以外のコマンドを表示させない（整理）
                for cmd in list(self.tree.get_commands()):
                    if cmd.name not in allowed_commands:
                        self.tree.remove_command(cmd.name)
                print(f"📋 パネルBot ({self.bot_index}): Economy & Panel ロード完了 (許可コマンド: {', '.join(allowed_commands)})")

            # Index 4: 特殊ディレクトリ 'five'
            elif self.bot_index == 4:
                target_dir = "./five"
                if os.path.exists(target_dir):
                    for filename in os.listdir(target_dir):
                        if filename.endswith(".py"):
                            await self.load_extension(f"five.{filename[:-3]}")
                            print(f"🌟 5台目Bot ({self.bot_index}): {filename} をロード")

            # Index 5: 特殊ディレクトリ 'six' (6体目)
            elif self.bot_index == 5:
                target_dir = "./six"
                if os.path.exists(target_dir):
                    for filename in os.listdir(target_dir):
                        if filename.endswith(".py"):
                            await self.load_extension(f"six.{filename[:-3]}")
                            print(f"⚙️ 6台目Bot ({self.bot_index}): {filename} をロード")

            # Index 1, 2 等: 音楽機能
            else:
                try:
                    await self.load_extension("cogs.music")
                    print(f"🎵 サブBot ({self.bot_index}): 音楽機能をロード")
                except:
                    print(f"ℹ️ サブBot ({self.bot_index}): music cogが見つかりません。")

        except Exception as e:
            print(f"❌ [Load Error - Bot Index {self.bot_index}]: {e}")
            traceback.print_exc()

        # 同期間隔を広げてレート制限を回避
        sync_delay = self.bot_index * 4.0 
        # 6体目の場合はさらに少し待つ
        await asyncio.sleep(sync_delay)

        try:
            await self.tree.sync()
            print(f"🔄 {self.user.name} (Index {self.bot_index}): コマンド同期完了")
        except Exception as e:
            print(f"❌ {self.user.name} (Index {self.bot_index}): 同期エラー: {e}")

    async def on_ready(self):
        print(f"✅ ログイン完了: {self.user.name} (Bot Index: {self.bot_index})")

        # Index 0 のみ Firebase へのデータ送信を試行
        if self.bot_index == 0:
            economy_cog = self.get_cog("Economy")
            if economy_cog and hasattr(economy_cog, 'update_web_data'):
                try:
                    await asyncio.sleep(5)
                    success = economy_cog.update_web_data()
                    if success:
                        print(f"✅ {self.user.name}: Firebaseへの初期データ送信成功")
                except Exception as e:
                    print(f"⚠️ {self.user.name}: Firebase送信失敗: {e}")

async def start_bots():
    tokens = [
        os.getenv("TOKEN1") or os.getenv("DISCORD_TOKEN"), 
        os.getenv("TOKEN2"),                              
        os.getenv("TOKEN3"),
        os.getenv("TOKEN4"), # bot_index 3
        os.getenv("TOKEN5"),
        os.getenv("TOKEN6")  # 6体目
    ]

    valid_tokens = [(i, t) for i, t in enumerate(tokens) if t]

    if not valid_tokens:
        print("⚠️ 有効なトークンが環境変数に見つかりません。")
        return

    tasks = []
    for i, token in valid_tokens:
        # 起動間隔を調整して負荷を軽減
        bot = MyBot(delay_time=i * 2.0, bot_index=i)
        tasks.append(bot.start(token))

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(start_bots())
    except KeyboardInterrupt:
        print("\nシステムを終了します...")
    except Exception as e:
        print(f"致命的なエラー: {e}")
        traceback.print_exc()