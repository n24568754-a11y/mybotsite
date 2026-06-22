import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random

class WalkView(discord.ui.View):
    """移動用ボタンビュー"""
    def __init__(self, cog, interaction, player_data, x, y):
        super().__init__(timeout=120)
        self.cog = cog
        self.interaction = interaction
        self.player = player_data
        self.x = x
        self.y = y
        self.message = None

    async def move(self, dx, dy, direction_name):
        """移動処理"""
        new_x = self.x + dx
        new_y = self.y + dy

        world = self.cog.load_world_map()
        areas = self.cog.load_areas()

        # 移動可能チェック
        if new_x < 0 or new_x >= world["width"] or new_y < 0 or new_y >= world["height"]:
            embed = discord.Embed(
                title="🚫 移動できません",
                description="これ以上進めません。世界の果てです。",
                color=discord.Color.red()
            )
            await self.interaction.edit_original_response(embed=embed, view=self)
            return

        area_key = world["grid"][new_y][new_x]
        area = areas.get(area_key, {"name": "未知の地", "encounter_rate": 0, "enemies": [], "description": "何もない場所", "color": 0x2b2d31})

        # 移動
        self.x = new_x
        self.y = new_y

        # 歩数をカウント
        self.player["x"] = self.x
        self.player["y"] = self.y
        self.player["steps"] = self.player.get("steps", 0) + 1

        # データ保存
        players = self.cog.load_players()
        players[str(self.interaction.user.id)] = self.player
        self.cog.save_players(players)

        # ===== ストーリートリガーチェックを追加 =====
        # 移動後にストーリーイベントをチェック（RPG Cogのメソッドを呼び出す）
        if hasattr(self.cog, 'after_move'):
            await self.cog.after_move(self.interaction, self.x, self.y, area_key)

        # 結果表示用の埋め込み
        embed = discord.Embed(
            title=f"🚶 {area['name']}",
            description=f"**{direction_name}** へ移動した！",
            color=area.get("color", 0x2b2d31)
        )
        embed.add_field(name="📍 座標", value=f"({self.x}, {self.y})", inline=True)
        embed.add_field(name="🚶 総歩数", value=f"{self.player['steps']}歩", inline=True)
        embed.add_field(name="📖 説明", value=area.get("description", "特別な地形"), inline=False)

        # エンカウント判定
        if area["enemies"] and random.random() < area["encounter_rate"]:
            enemies = self.cog.load_enemies()
            enemy_key = random.choice(area["enemies"])
            enemy = enemies.get(enemy_key)
            if enemy:
                embed.add_field(
                    name="⚠️ モンスターが現れた！",
                    value=f"**{enemy['name']}** が襲いかかってきた！",
                    inline=False
                )
                await self.interaction.edit_original_response(embed=embed, view=None)
                # 戦闘を開始（エピメラル版を使用）
                from . import rpg_battle
                await rpg_battle.start_battle_ephemeral(self.cog, self.interaction, enemy)
                return

        # 周辺情報を取得
        surroundings = self.get_surroundings()
        embed.add_field(name="🧭 周辺", value=surroundings, inline=False)

        # 新しいViewを作成して更新
        new_view = WalkView(self.cog, self.interaction, self.player, self.x, self.y)
        await self.interaction.edit_original_response(embed=embed, view=new_view)

    def get_surroundings(self):
        """周辺4方向の地形を取得"""
        world = self.cog.load_world_map()
        areas = self.cog.load_areas()
        w, h = world["width"], world["height"]

        directions = [
            (0, -1, "⬆️ 北"),
            (0, 1, "⬇️ 南"),
            (-1, 0, "⬅️ 西"),
            (1, 0, "➡️ 東")
        ]

        result = []
        for dx, dy, name in directions:
            nx, ny = self.x + dx, self.y + dy
            if 0 <= nx < w and 0 <= ny < h:
                area_key = world["grid"][ny][nx]
                area = areas.get(area_key, {"name": "???"})
                emoji_map = {
                    "草原": "🌿", "森林": "🌲", "村": "🏘️", "街": "🏙️",
                    "城": "🏰", "山": "⛰️", "洞窟": "🕳️", "砂漠": "🏜️", "海岸": "🏖️"
                }
                emoji = emoji_map.get(area_key, "❓")
                result.append(f"{name}: {emoji} {area['name']}")
            else:
                result.append(f"{name}: 🌊 行き止まり")

        return "\n".join(result)

    @discord.ui.button(label="⬆️ 北", style=discord.ButtonStyle.primary, row=0)
    async def north(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("❌ あなたの移動ではありません", ephemeral=True)
        await interaction.response.defer()
        await self.move(0, -1, "北")

    @discord.ui.button(label="⬇️ 南", style=discord.ButtonStyle.primary, row=0)
    async def south(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("❌ あなたの移動ではありません", ephemeral=True)
        await interaction.response.defer()
        await self.move(0, 1, "南")

    @discord.ui.button(label="⬅️ 西", style=discord.ButtonStyle.secondary, row=1)
    async def west(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("❌ あなたの移動ではありません", ephemeral=True)
        await interaction.response.defer()
        await self.move(-1, 0, "西")

    @discord.ui.button(label="➡️ 東", style=discord.ButtonStyle.secondary, row=1)
    async def east(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("❌ あなたの移動ではありません", ephemeral=True)
        await interaction.response.defer()
        await self.move(1, 0, "東")

    @discord.ui.button(label="📊 ステータス", style=discord.ButtonStyle.success, emoji="📊", row=2)
    async def show_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("❌ あなたのステータスではありません", ephemeral=True)
        
        # deferしてから新しいメッセージとして送信
        await interaction.response.defer(ephemeral=True)
        
        # ステータス表示用の処理を直接ここに実装
        players = self.cog.load_players()
        uid = str(interaction.user.id)
        
        if uid not in players:
            return await interaction.followup.send("❌ 冒険者登録が必要です", ephemeral=True)
        
        p = players[uid]
        
        # 現在のエリアを取得
        world = self.cog.load_world_map()
        areas = self.cog.load_areas()
        x = p.get("x", 4)
        y = p.get("y", 5)
        area_key = world["grid"][y][x]
        current_area = areas.get(area_key, {"name": "🌿 草原"})
        
        exp_needed = p['level'] * 100
        exp_percent = min(1.0, p['exp'] / exp_needed)
        bar_length = 15
        filled = int(bar_length * exp_percent)
        exp_bar = "█" * filled + "░" * (bar_length - filled)
        
        hp_percent = p['hp'] / p['max_hp']
        hp_filled = int(bar_length * hp_percent)
        hp_bar = "█" * hp_filled + "░" * (bar_length - hp_filled)
        
        mp_percent = p['mp'] / p['max_mp']
        mp_filled = int(bar_length * mp_percent)
        mp_bar = "█" * mp_filled + "░" * (bar_length - mp_filled)
        
        job_name = p.get("job", "未選択")
        
        embed = discord.Embed(
            title=f"📊 {p['name']} のステータス",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="職業", value=job_name, inline=True)
        embed.add_field(name="レベル", value=f"**Lv.{p['level']}**", inline=True)
        embed.add_field(name="経験値", value=f"{p['exp']}/{exp_needed}\n`{exp_bar}`", inline=True)
        embed.add_field(name="現在地", value=current_area["name"], inline=True)
        embed.add_field(name="📍 座標", value=f"({x}, {y})", inline=True)
        embed.add_field(name="❤️ HP", value=f"{p['hp']}/{p['max_hp']}\n`{hp_bar}`", inline=False)
        embed.add_field(name="✨ MP", value=f"{p['mp']}/{p['max_mp']}\n`{mp_bar}`", inline=False)
        embed.add_field(name="⚔️ 攻撃力", value=str(p['atk']), inline=True)
        embed.add_field(name="🛡️ 防御力", value=str(p['def']), inline=True)
        embed.add_field(name="🔮 魔法力", value=str(p.get('mag', 5)), inline=True)
        embed.add_field(name="💨 素早さ", value=str(p.get('agi', 8)), inline=True)
        embed.add_field(name="🍀 運", value=str(p.get('luk', 8)), inline=True)
        embed.add_field(name="💰 所持金", value=f"{p['gold']} G", inline=False)
        embed.set_footer(text="冒険を続けて強くなろう！")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="🗺️ マップ", style=discord.ButtonStyle.secondary, emoji="🗺️", row=2)
    async def show_map(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("❌ マップを表示できません", ephemeral=True)
        
        # deferしてから新しいメッセージとして送信
        await interaction.response.defer(ephemeral=True)
        
        # マップ表示用の処理を直接ここに実装
        players = self.cog.load_players()
        uid = str(interaction.user.id)
        
        if uid not in players:
            return await interaction.followup.send("❌ 冒険者登録が必要です", ephemeral=True)
        
        world = self.cog.load_world_map()
        areas = self.cog.load_areas()
        p = players[uid]
        px = p.get("x", 4)
        py = p.get("y", 5)
        
        map_lines = []
        for y in range(max(0, py-2), min(world["height"], py+3)):
            line = ""
            for x in range(max(0, px-2), min(world["width"], px+3)):
                area_key = world["grid"][y][x]
                if x == px and y == py:
                    line += f"📍 "
                else:
                    emoji_map = {"草原": "🌿", "森林": "🌲", "村": "🏘️", "街": "🏙️", "城": "🏰", "山": "⛰️", "洞窟": "🕳️", "砂漠": "🏜️", "海岸": "🏖️"}
                    emoji = emoji_map.get(area_key, "❓")
                    line += f"{emoji} "
            map_lines.append(line)
        
        embed = discord.Embed(
            title="🗺️ ワールドマップ",
            description=f"現在地: {areas.get(world['grid'][py][px], {}).get('name', '???')}\n```\n" + "\n".join(map_lines) + "\n```",
            color=discord.Color.blue()
        )
        embed.set_footer(text="📍 = 現在地 | 🌿草原 🏘️村 🏙️街 🏰城 🌲森林 ⛰️山 🕳️洞窟 🏜️砂漠 🏖️海岸")
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def start_walk(cog, interaction):
    """移動を開始"""
    players = cog.load_players()
    uid = str(interaction.user.id)
    player = players[uid]

    # 初期位置（前回の位置を復元、なければデフォルト）
    x = player.get("x", 4)
    y = player.get("y", 5)

    # 現在のエリア情報
    world = cog.load_world_map()
    areas = cog.load_areas()
    area_key = world["grid"][y][x]
    area = areas.get(area_key, {"name": "草原", "description": "何もない場所", "color": 0x2b2d31})

    embed = discord.Embed(
        title=f"🚶 {area['name']} にいる",
        description=area.get("description", ""),
        color=area.get("color", 0x2b2d31)
    )
    embed.add_field(name="📍 座標", value=f"({x}, {y})", inline=True)
    embed.add_field(name="🚶 総歩数", value=f"{player.get('steps', 0)}歩", inline=True)

    # 周辺情報
    view = WalkView(cog, interaction, player, x, y)
    surroundings = view.get_surroundings()
    embed.add_field(name="🧭 周辺", value=surroundings, inline=False)

    # 自分だけに見えるように ephemeral=True を設定
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    return view