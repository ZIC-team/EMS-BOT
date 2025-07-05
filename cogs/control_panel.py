import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os

class ControlPanel(commands.Cog, name="Control Panel"):
    """Панель управления ботом через интерактивный интерфейс Discord"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='panel')
    @commands.check(lambda ctx: ctx.channel.id == ctx.bot.settings.get('config_channel_id'))
    async def panel(self, ctx):
        """Открыть панель управления ботом"""
        view = ControlPanelView(self.bot)
        # Получаем список человекочитаемых имён модулей
        names = []
        for key, cog in self.bot.cogs.items():
            # qualified_name — заданное имя или класс модуля
            name = getattr(cog, 'qualified_name', None) or key
            names.append(name)
        embed = discord.Embed(title='Control Panel', color=discord.Color.blurple())
        embed.add_field(name='Modules', value=', '.join(names) or 'None', inline=False)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(ControlPanel(bot))

class ControlPanelView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label='Show Settings', style=discord.ButtonStyle.primary, custom_id='control_show_settings')
    async def show_settings(self, interaction: discord.Interaction, button: Button):
        """Показать файл переменных modules/variables.json"""
        # Путь к файлу modules/variables.json
        vars_path = os.path.join(os.path.dirname(__file__), '..', 'modules', 'variables.json')
        try:
            with open(vars_path, 'r', encoding='utf-8') as vf:
                data = json.load(vf)
        except FileNotFoundError:
            await interaction.response.send_message(':x: Файл переменных не найден.', ephemeral=True)
            return
        formatted = json.dumps(data, indent=2, ensure_ascii=False)
        await interaction.response.send_message(f"""```json
{formatted}
```""", ephemeral=True)

    @discord.ui.button(label='Reload All', style=discord.ButtonStyle.secondary, custom_id='control_reload_all')
    async def reload_all(self, interaction: discord.Interaction, button: Button):
        """Перезагрузить все модули"""
        failed = []
        for ext in list(self.bot.extensions.keys()):
            try:
                await self.bot.reload_extension(ext)
            except Exception:
                failed.append(ext)
        msg = 'All modules reloaded successfully.' if not failed else f"Failed to reload: {', '.join(failed)}"
        await interaction.response.send_message(msg, ephemeral=True)