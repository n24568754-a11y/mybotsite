import discord
from discord.ext import commands
import yt_dlp
import asyncio
from collections import deque

# yt-dlpのオプション設定
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': False, # プレイリスト対応のためFalseに
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'extract_flat': True, # プレイリスト解析を高速化
}

# FFmpegのオプション設定
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loop_mode = {}    # 0:OFF, 1:1曲ループ, 2:全曲ループ
        self.queues = {}      # サーバーごとの再生待ちリスト
        self.current_song = {} # ループ用に現在再生中の曲を保持

    def get_queue(self, guild_id):
        """サーバーごとのキューを取得または作成"""
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        return self.queues[guild_id]

    async def auto_disconnect(self, ctx):
        """5分間再生がなければ自動で退室する"""
        await asyncio.sleep(300)
        vc = ctx.voice_client
        if vc and not vc.is_playing() and not vc.is_paused():
            queue = self.get_queue(ctx.guild.id)
            if len(queue) == 0:
                await vc.disconnect()
                await ctx.send("⌛ 再生待ちがないため、自動退室しました。")

    async def is_same_vc(self, ctx):
        """コマンド実行者とBotが同じボイスチャンネルにいるかチェック"""
        if not ctx.voice_client:
            return False
        if not ctx.author.voice or ctx.author.voice.channel != ctx.voice_client.channel:
            return False
        return True

    def play_next(self, ctx):
        """曲が終了した後に呼ばれる。次の曲があれば再生する。"""
        vc = ctx.voice_client
        if not vc:
            return

        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)
        mode = self.loop_mode.get(guild_id, 0)
        last_song = self.current_song.get(guild_id)

        # --- ループ処理 ---
        if last_song:
            if mode == 1: # 1曲ループ
                queue.appendleft(last_song)
            elif mode == 2: # 全曲ループ
                queue.append(last_song)

        if len(queue) > 0:
            next_song = queue.popleft()
            self.bot.loop.create_task(self.start_playing(ctx, next_song))
        else:
            self.current_song[guild_id] = None
            self.bot.loop.create_task(self.auto_disconnect(ctx))

    async def start_playing(self, ctx, song_info):
        """FFmpegで実際に再生を開始する"""
        vc = ctx.voice_client
        if not vc: return

        guild_id = ctx.guild.id
        self.current_song[guild_id] = song_info # 再生開始時に現在の曲をセット

        try:
            # extract_flatを使っているため、再生直前に詳細URLを取得
            loop = self.bot.loop
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(song_info['url'], download=False))

            song_url = data['url']
            title = data.get('title', '不明なタイトル')

            vc.play(discord.FFmpegPCMAudio(song_url, **FFMPEG_OPTIONS), 
                    after=lambda e: self.play_next(ctx))

            await ctx.send(f"🎵 **[{self.bot.user.name}] 再生中:** {title}")

        except Exception as e:
            await ctx.send(f"⚠️ 再生エラーが発生しました。次の曲へ移ります。")
            self.play_next(ctx)

    @commands.command(name="再生")
    async def play_audio(self, ctx, url: str):
        """指定されたURLをキューに追加し、再生します"""
        if ctx.author.voice is None:
            return await ctx.send("❌ 先にボイスチャンネルに入ってください。")

        target_channel = ctx.author.voice.channel

        if ctx.voice_client:
            if ctx.voice_client.channel != target_channel and ctx.voice_client.is_playing():
                return 

        await asyncio.sleep(self.bot.delay_time)

        if not ctx.voice_client or ctx.voice_client.channel != target_channel:
            for member in target_channel.members:
                if member.bot and member.id != self.bot.user.id:
                    return

        vc = ctx.voice_client or await target_channel.connect()
        if vc.channel != target_channel:
            await vc.move_to(target_channel)

        async with ctx.typing():
            try:
                loop = self.bot.loop
                # プレイリストのフラット取得
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

                queue = self.get_queue(ctx.guild.id)
                added_count = 0

                if 'entries' in data:
                    # プレイリストの場合
                    for entry in data['entries']:
                        queue.append({'url': entry['url'], 'title': entry.get('title', '不明')})
                        added_count += 1
                else:
                    # 単一動画の場合
                    queue.append({'url': data['webpage_url'], 'title': data.get('title', '不明')})
                    added_count = 1

                if vc.is_playing() or vc.is_paused():
                    await ctx.send(f"✅ **[{self.bot.user.name}]** {added_count}曲を予約リストに追加しました。")
                else:
                    next_song = queue.popleft()
                    await self.start_playing(ctx, next_song)

            except Exception as e:
                await ctx.send(f"⚠️ 読み込みに失敗しました。")
                print(e)

    @commands.command(name="ループ")
    async def toggle_loop(self, ctx, mode: int = None):
        """0:オフ, 1:1曲ループ, 2:全曲ループ を切り替えます"""
        if await self.is_same_vc(ctx):
            guild_id = ctx.guild.id

            # 引数がない場合は順繰りに切り替え
            if mode is None:
                current = self.loop_mode.get(guild_id, 0)
                mode = (current + 1) % 3

            if mode not in [0, 1, 2]:
                return await ctx.send("❌ 0:オフ, 1:1曲, 2:全曲 で指定してください。")

            self.loop_mode[guild_id] = mode
            status = ["OFF", "🔂 1曲ループ", "🔁 全曲ループ"]
            await ctx.send(f"✅ **[{self.bot.user.name}]** ループ設定を **{status[mode]}** にしました。")

    @commands.command(name="停止")
    async def stop_audio(self, ctx):
        """再生を中止し、キューを空にして退室します"""
        if await self.is_same_vc(ctx):
            guild_id = ctx.guild.id
            self.get_queue(guild_id).clear()
            self.current_song[guild_id] = None # ループ情報も消去
            await ctx.voice_client.disconnect()
            await ctx.send(f"👋 **[{self.bot.user.name}]** 予約を全消去して退室しました。")

    @commands.command(name="スキップ")
    async def skip_song(self, ctx):
        """再生中の曲を飛ばして次の曲へ行きます"""
        if await self.is_same_vc(ctx) and ctx.voice_client.is_playing():
            # スキップ時は「今再生していた曲」をループ対象にしないようクリア
            self.current_song[ctx.guild.id] = None
            ctx.voice_client.stop() 
            await ctx.send(f"⏭ **[{self.bot.user.name}]** 曲をスキップしました。")

    @commands.command(name="一時停止")
    async def pause(self, ctx):
        if await self.is_same_vc(ctx) and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send(f"⏸ **[{self.bot.user.name}]** 一時停止しました。")

    @commands.command(name="再開")
    async def resume(self, ctx):
        if await self.is_same_vc(ctx) and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send(f"▶ **[{self.bot.user.name}]** 再生を再開しました。")

async def setup(bot):
    await bot.add_cog(Music(bot))
