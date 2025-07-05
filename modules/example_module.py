import os
import json
from discord.ext import commands

class ExampleModule(commands.Cog):
    """Пример пользовательского модуля, читающего свои переменные из variables.json"""
    def __init__(self, bot):
        self.bot = bot
        vars_path = os.path.join(os.path.dirname(__file__), 'variables.json')
        with open(vars_path, 'r', encoding='utf-8') as vf:
            cfg = json.load(vf)
        # Merge into bot settings
        if hasattr(self.bot, 'settings'):
            self.bot.settings.update(cfg)
        else:
            self.bot.settings = cfg

    @commands.command(name='showcustom')
    async def show_custom(self, ctx):
        cv = self.bot.settings.get('custom_var')
        av = self.bot.settings.get('another_var')
        await ctx.send(f'Custom Var: {cv}, Another Var: {av}')

async def setup(bot):
    await bot.add_cog(ExampleModule(bot))
