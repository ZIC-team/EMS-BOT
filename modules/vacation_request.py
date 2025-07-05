import os
import json
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from datetime import datetime, timedelta

class VacationRequestModule(commands.Cog, name="Vacation Request Module"):
    """Модуль для подачи заявок на отпуск и перерыва,
    интерактивная настройка каналов и карты упоминаний ролей"""
    def __init__(self, bot):
        self.bot = bot
        self.vars_path = os.path.join(os.path.dirname(__file__), 'variables.json')
        with open(self.vars_path, 'r', encoding='utf-8') as vf:
            self.cfg = json.load(vf)
        # Каналы для заявок
        keys = [
            'request_channel_id',
            'icc_vacation_channel_id',
            'oc_vacation_channel_id',
            'break_channel_id'
        ]
        self._queue = [k for k in keys if not self.cfg.get(k)]
        self._asking = False

    @commands.command(name='mention_config')
    @commands.check(lambda ctx: ctx.channel.id == ctx.bot.settings.get('config_channel_id'))
    async def mention_config(self, ctx):
        """Открыть GUI для настройки карты упоминаний ролей"""
        await ctx.send("Управление картой упоминаний:", view=MentionConfigView(self))

    @commands.command(name='mention_show')
    @commands.check(lambda ctx: ctx.channel.id == ctx.bot.settings.get('config_channel_id'))
    async def mention_show(self, ctx):
        """Показать текущую карту упоминаний"""
        mapping = self.cfg.get('mention_map', {})
        if not mapping:
            return await ctx.send(':information_source: Карта упоминаний пуста.')
        lines = [f"**{role}**: {', '.join(targets)}" for role, targets in mapping.items()]
        text = "**Карта упоминаний:**\n" + "\n".join(lines)
        await ctx.send(text)

    @commands.Cog.listener()
    async def on_ready(self):
        # При старте проверяем конфигурацию каналов
        await self._ask_next()
        if self._queue:
            return
        # Публикуем кнопки в канале заявок
        req = self.cfg.get('request_channel_id')
        if req:
            ch = self.bot.get_channel(req)
            if ch:
                await ch.send("Выберите тип заявки:", view=RequestButtons(self))

    async def _ask_next(self):
        if self._asking or not self._queue:
            return
        key = self._queue[0]
        prompts = {
            'request_channel_id': 'Укажите ID канала для подачи заявок:',
            'icc_vacation_channel_id': 'Укажите ID канала для уведомлений о ICC отпуске:',
            'oc_vacation_channel_id': 'Укажите ID канала для уведомлений о OC отпуске:',
            'break_channel_id': 'Укажите ID канала для уведомлений о перерыве:'
        }
        admin_ch = self.bot.get_channel(self.bot.settings.get('config_channel_id'))
        if admin_ch:
            await admin_ch.send(prompts[key])
            self._asking = True

    @commands.Cog.listener()
    async def on_message(self, message):
        # Обработка ответов администратора для настройки каналов
        if message.author.bot:
            return
        cfg_ch = self.bot.settings.get('config_channel_id')
        if message.channel.id != cfg_ch or not self._asking or not self._queue:
            return
        key = self._queue.pop(0)
        try:
            val = int(message.content.strip())
        except ValueError:
            await message.channel.send(f":x: Некорректный ID для `{key}`.")
            self._queue.insert(0, key)
            return
        self.cfg[key] = val
        with open(self.vars_path, 'w', encoding='utf-8') as vf:
            json.dump(self.cfg, vf, indent=2, ensure_ascii=False)
        await message.channel.send(f":white_check_mark: Установлено `{key}` = {val}")
        self._asking = False
        await self._ask_next()

# GUI для карты упоминаний
class MentionConfigView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label='Добавить/Обновить', style=discord.ButtonStyle.primary, custom_id='mention_add')
    async def add_map(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(MentionAddModal(self.cog))

    @discord.ui.button(label='Показать', style=discord.ButtonStyle.secondary, custom_id='mention_show')
    async def show_map(self, interaction: discord.Interaction, button: Button):
        mapping = self.cog.cfg.get('mention_map', {})
        if not mapping:
            return await interaction.response.send_message(':information_source: Карта пуста.', ephemeral=True)
        lines = [f"**{r}**: {', '.join(ts)}" for r, ts in mapping.items()]
        text = "**Карта упоминаний:**\n" + "\n".join(lines)
        await interaction.response.send_message(text, ephemeral=True)

    @discord.ui.button(label='Перезагрузить', style=discord.ButtonStyle.success, custom_id='mention_reload')
    async def reload_map(self, interaction: discord.Interaction, button: Button):
        # Перезагрузка карты из файла
        with open(self.cog.vars_path, 'r', encoding='utf-8') as vf:
            self.cog.cfg = json.load(vf)
        await interaction.response.send_message(':white_check_mark: Карта перезагружена', ephemeral=True)

# Модал для добавления упоминаний
class MentionAddModal(Modal):
    role_name = TextInput(label='Роль-ключ', placeholder='Fire Departament')
    targets   = TextInput(label='Упоминаемые роли (через запятую)', placeholder='АГВ FD, Зам.Зав FD')

    def __init__(self, cog):
        super().__init__(title='Добавить/Обновить упоминания')
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        mapping = self.cog.cfg.setdefault('mention_map', {})
        r = self.role_name.value.strip()
        mapping[r] = [t.strip() for t in self.targets.value.split(',')]
        with open(self.cog.vars_path, 'w', encoding='utf-8') as vf:
            json.dump(self.cog.cfg, vf, indent=2, ensure_ascii=False)
        await interaction.response.send_message(f":white_check_mark: Упоминания сохранены для `{r}`", ephemeral=True)

# Кнопки подачи заявок
class RequestButtons(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label='ICC Отпуск', style=discord.ButtonStyle.primary, custom_id='vac_icc')
    async def vac_icc(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(VacationModal(self.cog, 'icc_vacation_channel_id', 'ICC Отпуск'))

    @discord.ui.button(label='OC Отпуск', style=discord.ButtonStyle.primary, custom_id='vac_oc')
    async def vac_oc(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(VacationModal(self.cog, 'oc_vacation_channel_id', 'OC Отпуск'))

    @discord.ui.button(label='Перерыв', style=discord.ButtonStyle.secondary, custom_id='vac_break')
    async def vac_break(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BreakModal(self.cog, 'break_channel_id', 'Перерыв'))

# Кнопки одобрения/отклонения
class ApprovalView(View):
    def __init__(self, message, allowed_roles):
        super().__init__(timeout=None)
        self.message = message
        self.allowed = allowed_roles

    @discord.ui.button(label='Принять', style=discord.ButtonStyle.success, custom_id='approve')
    async def approve(self, interaction: discord.Interaction, button: Button):
        if not any(r.name in self.allowed for r in interaction.user.roles):
            return await interaction.response.send_message(':x: Нет прав', ephemeral=True)
        embed = self.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name='Статус', value='Одобрено', inline=False)
        embed.add_field(name='Решил', value=interaction.user.mention, inline=False)
        await self.message.edit(embed=embed, view=None)
        await interaction.response.send_message('Заявка одобрена', ephemeral=True)

    @discord.ui.button(label='Отказать', style=discord.ButtonStyle.danger, custom_id='deny')
    async def deny(self, interaction: discord.Interaction, button: Button):
        if not any(r.name in self.allowed for r in interaction.user.roles):
            return await interaction.response.send_message(':x: Нет прав', ephemeral=True)
        await interaction.response.send_modal(DenyModal(self.message))

# Модал для причины отказа
class DenyModal(Modal):
    reason = TextInput(label='Причина отказа', style=discord.TextStyle.long)

    def __init__(self, message):
        super().__init__(title='Причина отказа')
        self.message = message

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name='Статус', value='Отклонено', inline=False)
        embed.add_field(name='Решил', value=interaction.user.mention, inline=False)
        embed.add_field(name='Причина отказа', value=self.reason.value, inline=False)
        await self.message.edit(embed=embed, view=None)
        await interaction.response.send_message('Заявка отклонена', ephemeral=True)

# Модали подачи заявок
class VacationModal(Modal):
    start_date = TextInput(label='Дата начала (DD.MM.YYYY)')
    end_date   = TextInput(label='Дата окончания (DD.MM.YYYY)')
    reason     = TextInput(label='Причина', style=discord.TextStyle.long, required=False)

    def __init__(self, cog, channel_key: str, title: str):
        super().__init__(title=f'Заявка: {title}')
        self.cog = cog
        self.channel_key = channel_key
        self.title_short = title

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        sd = datetime.strptime(self.start_date.value, '%d.%m.%Y')
        ed = datetime.strptime(self.end_date.value, '%d.%m.%Y')
        days = (ed - sd).days + 1
        embed = discord.Embed(title=f'Новая заявка ({self.title_short})', color=discord.Color.blue())
        embed.set_footer(text='by ZICteam')
        embed.add_field(name='Пользователь', value=interaction.user.mention, inline=False)
        embed.add_field(name='С', value=self.start_date.value, inline=True)
        embed.add_field(name='По', value=self.end_date.value, inline=True)
        embed.add_field(name='Длительность', value=f'{days} дн.', inline=False)
        embed.add_field(name='Причина', value=self.reason.value or 'Не указана', inline=False)
        embed.add_field(name='Время заявки', value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), inline=False)
        notice = f"Поступила новая заявка на {self.title_short}. Пожалуйста рассмотрите."
        mapping = self.cog.cfg.get('mention_map', {})
        allowed, mentions = [], []
        for role in interaction.user.roles:
            for tgt in mapping.get(role.name, []):
                r = discord.utils.get(interaction.guild.roles, name=tgt)
                if r:
                    mentions.append(r.mention)
                    allowed.append(r.name)
        ch = self.cog.bot.get_channel(self.cog.cfg.get(self.channel_key))
        view = ApprovalView(None, allowed)
        if ch:
            msg = await ch.send(content=' '.join(dict.fromkeys(mentions)) + '\n' + notice, embed=embed, view=view)
            view.message = msg
        await interaction.followup.send('Заявка отправлена', ephemeral=True)

class BreakModal(Modal):
    """Модал для заявки на перерыв: указывает время начала и конца"""
    start_time = TextInput(label='Начало (HH:MM)', placeholder='09:00')
    end_time   = TextInput(label='Конец (HH:MM)', placeholder='09:15')
    reason     = TextInput(label='Причина', style=discord.TextStyle.long, required=False)

    def __init__(self, cog, channel_key: str, title: str):
        super().__init__(title=f'Заявка: {title}')
        self.cog = cog
        self.channel_key = channel_key
        self.title_short = title

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        fmt = '%H:%M'
        try:
            start = datetime.strptime(self.start_time.value, fmt)
            end = datetime.strptime(self.end_time.value, fmt)
            if end <= start:
                end += timedelta(days=1)
            delta = end - start
            minutes = delta.seconds // 60
        except Exception:
            minutes = 0
        embed = discord.Embed(title=f'Новая заявка ({self.title_short})', color=discord.Color.orange())
        embed.set_footer(text='by ZICteam')
        embed.add_field(name='Пользователь', value=interaction.user.mention, inline=False)
        embed.add_field(name='Начало', value=self.start_time.value, inline=True)
        embed.add_field(name='Конец', value=self.end_time.value, inline=True)        # Форматирование длительности: часы и минуты
        if minutes >= 60:
            hours = minutes // 60
            mins = minutes % 60
            duration_str = f'{hours} ч {mins} мин.' if mins else f'{hours} ч'
        else:
            duration_str = f'{minutes} мин.'
        embed.add_field(name='Длительность', value=duration_str, inline=False)
        embed.add_field(name='Причина', value=self.reason.value or 'Не указана', inline=False)
        embed.add_field(name='Время заявки', value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), inline=False)
        notice = f"Поступила новая заявка на {self.title_short}. Пожалуйста рассмотрите."
        mapping = self.cog.cfg.get('mention_map', {})
        allowed, mentions = [], []
        for role in interaction.user.roles:
            for tgt in mapping.get(role.name, []):
                r = discord.utils.get(interaction.guild.roles, name=tgt)
                if r:
                    mentions.append(r.mention)
                    allowed.append(r.name)
        ch = self.cog.bot.get_channel(self.cog.cfg.get(self.channel_key))
        view = ApprovalView(None, allowed)
        if ch:
            msg = await ch.send(content=' '.join(dict.fromkeys(mentions)) + '\n' + notice, embed=embed, view=view)
            view.message = msg
        await interaction.followup.send('Заявка на перерыв отправлена', ephemeral=True)

async def setup(bot):
    await bot.add_cog(VacationRequestModule(bot))
