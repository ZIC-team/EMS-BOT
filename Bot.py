import os
import json
import logging
import discord
from discord.ext import commands

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)

# Load settings
with open('settings.json', 'r', encoding='utf-8') as f:
    settings = json.load(f)
BOT_TOKEN = settings['token']
PREFIX = settings.get('prefix', '!')

intents = discord.Intents.default()
intents.message_content = True

class ModularBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(PREFIX),
            intents=intents
        )

    async def setup_hook(self):
        base_dir = os.path.dirname(__file__)
        # Create modules folder and default files
        modules_dir = os.path.join(base_dir, 'modules')
        os.makedirs(modules_dir, exist_ok=True)
        init_py = os.path.join(modules_dir, '__init__.py')
        if not os.path.exists(init_py): open(init_py, 'w').close()
        # variables.json
        vars_path = os.path.join(modules_dir, 'variables.json')
        default_vars = {'custom_var': 'value', 'another_var': 123}
        if not os.path.exists(vars_path):
            with open(vars_path, 'w', encoding='utf-8') as vf:
                json.dump(default_vars, vf, indent=2, ensure_ascii=False)
        # example module template
        example_path = os.path.join(modules_dir, 'example_module.py')
        if not os.path.exists(example_path):
            with open(example_path, 'w', encoding='utf-8') as f:
                f.write('''import os
import json
from discord.ext import commands

class ExampleModule(commands.Cog, name="Example Module"):
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
    await bot.add_cog(ExampleModule(bot))\n''')
        # Load cogs
        cogs_dir = os.path.join(base_dir, 'cogs')
        logger.info(f"Loading cogs from {cogs_dir}...")
        for fn in os.listdir(cogs_dir):
            if fn.endswith('.py') and fn != '__init__.py':
                mod = fn[:-3]
                try:
                    await self.load_extension(f'cogs.{mod}')
                    logger.info(f'Loaded cog: {mod}')
                except Exception as e:
                    logger.error(f'Failed to load cog {mod}: {e}')
        # Load user modules
        logger.info(f"Loading user modules from {modules_dir}...")
        for fn in os.listdir(modules_dir):
            if fn.endswith('.py') and fn != '__init__.py':
                mod = fn[:-3]
                try:
                    await self.load_extension(f'modules.{mod}')
                    logger.info(f'Loaded module: {mod}')
                except Exception as e:
                    logger.error(f'Failed to load module {mod}: {e}')

bot = ModularBot()

@bot.event
async def on_ready():
    logger.info(f'Bot logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound): return
    logger.error(f"Error in command {ctx.command}: {error}")
    await ctx.send(f':warning: Произошла ошибка: `{error}`')

if __name__ == '__main__':
    bot.run(BOT_TOKEN)