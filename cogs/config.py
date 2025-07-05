from discord.ext import commands
import json
import os

class Config(commands.Cog, name="Configuration"):
    """Cog для просмотра и изменения настроек бота"""
    def __init__(self, bot):
        self.bot = bot
        path = os.path.join(os.path.dirname(__file__), '..', 'settings.json')
        self.bot.settings = json.load(open(path, 'r', encoding='utf-8'))

    @commands.command(name='showconfig')
    @commands.check(lambda ctx: ctx.channel.id == ctx.bot.settings.get('config_channel_id'))
    async def show_config(self, ctx):
        data = json.load(open(path, 'r', encoding='utf-8'))
        await ctx.send(f"```json\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```")

    @commands.command(name='set')
    @commands.check(lambda ctx: ctx.channel.id == ctx.bot.settings.get('config_channel_id'))
    async def set_config(self, ctx, key: str, *, value: str):
        data = json.load(open(path, 'r', encoding='utf-8'))
        if key not in data:
            return await ctx.send(f':x: Unknown key `{key}`')
        try: parsed = json.loads(value)
        except: parsed = value
        data[key] = parsed
        json.dump(data, open(path, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
        self.bot.settings[key] = parsed
        await ctx.send(f':white_check_mark: `{key}` = `{parsed}`')

async def setup(bot):
    await bot.add_cog(Config(bot))
