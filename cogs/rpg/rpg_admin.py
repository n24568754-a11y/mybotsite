
import discord
from discord import app_commands
from discord.ext import commands
import os
import shutil

class RPGAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.image_dir = "cogs/rpg/data/images/enemies"

    def ensure_image_dir(self):
        if not os.path.exists(self.image_dir):
            os.makedirs(self.image_dir)

    @app_commands.command(name="rpg_set_enemy_image", description="敵の画像を設定する")
    @app_commands.default_permissions(administrator=True)
    async def set_enemy_image(self, interaction: discord.Interaction, 敵名: str, 画像: discord.Attachment):
        await interaction.response.defer(ephemeral=True)

        self.ensure_image_dir()

        # 画像を保存
        file_ext = 画像.filename.split('.')[-1]
        save_path = os.path.join(self.image_dir, f"{敵名}.{file_ext}")
        await 画像.save(save_path)

        # enemies.json を更新
        enemies = self.load_enemies()
        if 敵名 in enemies:
            # Discordの添付ファイルURLを設定
            enemies[敵名]["image_url"] = f"attachment://{敵名}.{file_ext}"
            self.save_enemies(enemies)

            # ファイルを添付して送信
            file = discord.File(save_path, filename=f"{敵名}.{file_ext}")
            embed = discord.Embed(
                title="✅ 画像設定完了",
                description=f"**{enemies[敵名]['name']}** の画像を設定しました。",
                color=discord.Color.green()
            )
            embed.set_image(url=f"attachment://{敵名}.{file_ext}")
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
        else:
            await interaction.followup.send(f"❌ 敵 `{敵名}` が見つかりません", ephemeral=True)

    @app_commands.command(name="rpg_enemy_list", description="敵の一覧を表示")
    async def enemy_list(self, interaction: discord.Interaction):
        enemies = self.load_enemies()
        if not enemies:
            return await interaction.response.send_message("❌ 敵データがありません", ephemeral=True)

        enemy_list = "\n".join([f"- {key}: {data['name']} (Lv.{data['level']})" for key, data in enemies.items()])
        embed = discord.Embed(
            title="📋 敵一覧",
            description=enemy_list,
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    def load_enemies(self):
        with open("cogs/rpg/data/enemies.json", 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_enemies(self, data):
        with open("cogs/rpg/data/enemies.json", 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


async def setup(bot):
    await bot.add_cog(RPGAdmin(bot))