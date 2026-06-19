import asyncio
import logging
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, View
from services.translation_service import tr
from views.ticket_view import TicketView

from database.repository import (
    get_server_config,
    save_server_config,
    set_server_language,
)

logger = logging.getLogger(__name__)

def panel_embed(guild_id: int) -> discord.Embed:
    embed = discord.Embed(
        title=tr(guild_id, "panel_title"),
        description=tr(guild_id, "panel_description"),
        color=discord.Color.dark_grey()
    )
    return embed

def config_embed(guild_id: int) -> discord.Embed:
    embed = discord.Embed(
        description=f"** ``` {tr(guild_id, 'config_menu_title')} ``` **",
        color=discord.Color.dark_grey()
    )
    return embed


class Config(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="configure-bot", description="Abrir menu de configuracao do bot de tickets")
    @app_commands.checks.has_permissions(administrator=True)
    async def configure_bot(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(tr(0, "server_only_command"), ephemeral=True)
            return

        logger.info(f"Segurança: Admin {interaction.user.id} iniciou configuração na Guild {guild.id}")
        view = ConfigMenu(guild.id)
        await interaction.response.send_message(embed=config_embed(guild.id), view=view, ephemeral=True)

    @configure_bot.error
    async def configure_bot_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.errors.MissingPermissions):
            logger.warning(f"Segurança: Utilizador não autorizado {interaction.user.id} tentou usar /configure-bot na Guild {interaction.guild_id}")
            await interaction.response.send_message("❌ Não tens permissões administrativas para usar este comando.", ephemeral=True)

class SecureView(View):
    def __init__(self):
        super().__init__(timeout=300)

    # MEDIDA DE SEGURANÇA 2: Impede que terceiros cliquem nas opções do menu exposto
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:
            logger.warning(f"Segurança: {interaction.user.id} tentou clicar numa View restrita na Guild {interaction.guild.id}")
            await interaction.response.send_message("❌ Apenas administradores do servidor podem interagir com este menu.", ephemeral=True)
            return False
        return True

class ConfigMenu(SecureView):
    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id

        options = [
            discord.SelectOption(label=tr(guild_id, "config_menu_option_open_category_label"), value="open_category", emoji="📁"),
            discord.SelectOption(label=tr(guild_id, "config_menu_option_admin_role_label"), value="admin_role", emoji="🛡️"),
            discord.SelectOption(label=tr(guild_id, "config_menu_option_transcript_channel_label"), value="transcript_channel", emoji="📄"),
            discord.SelectOption(label=tr(guild_id, "config_menu_option_language_label"), value="language", emoji="🌐"),
            discord.SelectOption(label=tr(guild_id, "config_menu_option_send_panel_label"), value="send_panel", emoji="🎫"),
        ]
        self.add_item(MainSelect(options=options, guild_id=guild_id))


class MainSelect(Select):
    def __init__(self, options, guild_id: int):
        super().__init__(
            placeholder=tr(guild_id, "config_menu_placeholder"),
            min_values=1, max_values=1, options=options,
        )
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        guild = interaction.guild
        
        try:
            config = get_server_config(guild.id) or {}
        except Exception:
            logger.exception(f"Erro na BD ao ler config da Guild {guild.id}")
            config = {}

        embed = discord.Embed(title=tr(guild.id, "config_menu_short_title"), color=discord.Color.dark_grey())

        if choice == "open_category":
            embed.description = tr(guild.id, "config_select_category_desc")
            await interaction.response.edit_message(embed=embed, view=CategorySelectView(guild, config))
            return

        if choice == "admin_role":
            embed.description = tr(guild.id, "config_select_admin_role_desc")
            await interaction.response.edit_message(embed=embed, view=RoleSelectView(guild, config))
            return

        if choice == "transcript_channel":
            embed.description = tr(guild.id, "config_select_transcript_desc")
            await interaction.response.edit_message(embed=embed, view=TranscriptSelectView(guild, config))
            return

        if choice == "language":
            embed.description = tr(guild.id, "config_select_language_desc")
            await interaction.response.edit_message(embed=embed, view=LanguageSelectView(guild, config))
            return

        if choice == "send_panel":
            logger.info(f"Audit: Painel de tickets gerado na Guild {guild.id} por {interaction.user.id}")
            await interaction.response.defer()
            await interaction.followup.send(embed=panel_embed(guild.id), view=TicketView(guild.id))


class CategorySelectView(SecureView):
    def __init__(self, guild: discord.Guild, config: dict):
        super().__init__()
        categories = [discord.SelectOption(label=f"📁 {c.name}", value=str(c.id)) for c in guild.categories[:25]]
        self.add_item(CategorySelect(categories, guild, config))


class CategorySelect(Select):
    def __init__(self, categories, guild, config):
        super().__init__(placeholder=tr(guild.id, "select_category_placeholder"), min_values=1, max_values=1, options=categories)
        self.guild = guild
        self.config = config

    async def callback(self, interaction: discord.Interaction):
        try:
            selected_id = int(self.values[0])
        except ValueError:
            await interaction.response.send_message("❌ Erro de validação de dados.", ephemeral=True)
            return

        if not any(c.id == selected_id for c in self.guild.categories):
            logger.error(f"Segurança: Tentativa de injeção de ID de categoria inválido ({selected_id}) na Guild {self.guild.id}")
            await interaction.response.send_message("❌ Erro: Esta categoria não pertence a este servidor.", ephemeral=True)
            return

        self.config["TICKET_CATEGORY_ID"] = selected_id
        save_server_config(self.guild.id, self.config)
        logger.info(f"Audit: Categoria de tickets alterada para {selected_id} na Guild {self.guild.id}")

        embed_ok = discord.Embed(description=f"** ``` {tr(self.guild.id, 'config_saved_category')} ``` **", color=discord.Color.dark_grey())
        await interaction.response.edit_message(embed=embed_ok, view=None)
        await asyncio.sleep(2)
        await interaction.edit_original_response(embed=config_embed(self.guild.id), view=ConfigMenu(self.guild.id))


class RoleSelectView(SecureView):
    def __init__(self, guild: discord.Guild, config: dict):
        super().__init__()
        sorted_roles = sorted([r for r in guild.roles if r.name != "@everyone"], key=lambda r: r.position, reverse=True)
        roles = [discord.SelectOption(label=f"🧑 {r.name}", value=str(r.id)) for r in sorted_roles[:25]]
        self.add_item(RoleSelect(roles, guild, config))


class RoleSelect(Select):
    def __init__(self, roles, guild, config):
        super().__init__(placeholder=tr(guild.id, "select_admin_role_placeholder"), min_values=1, max_values=1, options=roles)
        self.guild = guild
        self.config = config

    async def callback(self, interaction: discord.Interaction):
        try:
            role_id = int(self.values[0])
        except ValueError:
            await interaction.response.send_message("❌ Erro de validação de dados.", ephemeral=True)
            return

        role = self.guild.get_role(role_id)
        
        if not role:
            logger.error(f"Segurança: Cargo {role_id} não encontrado ou inválido na Guild {self.guild.id}")
            await interaction.response.send_message("❌ Erro: O cargo selecionado é inválido ou não existe.", ephemeral=True)
            return

        self.config["ADMIN_ROLE_NAME"] = role.name
        save_server_config(self.guild.id, self.config)
        logger.info(f"Audit: Cargo admin atualizado para '{role.name}' ({role_id}) na Guild {self.guild.id}")

        embed_ok = discord.Embed(description=f"** ``` {tr(self.guild.id, 'config_saved_admin_role')} ``` **", color=discord.Color.dark_grey())
        await interaction.response.edit_message(embed=embed_ok, view=None)
        await asyncio.sleep(2)
        await interaction.edit_original_response(embed=config_embed(self.guild.id), view=ConfigMenu(self.guild.id))


class TranscriptSelectView(SecureView):
    def __init__(self, guild: discord.Guild, config: dict):
        super().__init__()
        sorted_channels = sorted(guild.text_channels, key=lambda c: c.position)
        channels = [discord.SelectOption(label=f"📄 {c.name}", value=str(c.id)) for c in sorted_channels[:25]]
        self.add_item(TranscriptSelect(channels, guild, config))


class TranscriptSelect(Select):
    def __init__(self, channels, guild, config):
        super().__init__(placeholder=tr(guild.id, "select_transcript_placeholder"), min_values=1, max_values=1, options=channels)
        self.guild = guild
        self.config = config

    async def callback(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.values[0])
        except ValueError:
            await interaction.response.send_message("❌ Erro de validação de dados.", ephemeral=True)
            return

        if not self.guild.get_channel(channel_id):
            await interaction.response.send_message("❌ Erro: Canal de transcrição inválido.", ephemeral=True)
            return

        self.config["TRANSCRIPT_CHANNEL_ID"] = channel_id
        save_server_config(self.guild.id, self.config)
        logger.info(f"Audit: Canal de transcrição alterado para {channel_id} na Guild {self.guild.id}")

        embed_ok = discord.Embed(description=f"** ``` {tr(self.guild.id, 'config_saved_transcript')} ``` **", color=discord.Color.dark_grey())
        await interaction.response.edit_message(embed=embed_ok, view=None)
        await asyncio.sleep(2)
        await interaction.edit_original_response(embed=config_embed(self.guild.id), view=ConfigMenu(self.guild.id))


class LanguageSelectView(SecureView):
    def __init__(self, guild: discord.Guild, config: dict):
        super().__init__()
        options = [
            discord.SelectOption(label=tr(guild.id, "language_en_label"), value="en", emoji="\U0001F1FA\U0001F1F8"),
            discord.SelectOption(label=tr(guild.id, "language_ptpt_label"), value="pt-PT", emoji="\U0001F1F5\U0001F1F9"),
            discord.SelectOption(label=tr(guild.id, "language_ptbr_label"), value="pt-BR", emoji="\U0001F1E7\U0001F1F7"),
        ]
        self.add_item(LanguageSelect(options, guild, config))


class LanguageSelect(Select):
    def __init__(self, options, guild, config):
        super().__init__(placeholder=tr(guild.id, "select_language_placeholder"), min_values=1, max_values=1, options=options)
        self.guild = guild
        self.config = config

    async def callback(self, interaction: discord.Interaction):
        selected_lang = str(self.values[0])

        if selected_lang not in ["en", "pt-PT", "pt-BR"]:
            await interaction.response.send_message("❌ Idioma não suportado.", ephemeral=True)
            return

        self.config["LANGUAGE"] = selected_lang
        set_server_language(self.guild.id, selected_lang)
        logger.info(f"Audit: Idioma da Guild {self.guild.id} alterado para '{selected_lang}'")

        embed_ok = discord.Embed(description=f"** ``` {tr(self.guild.id, 'config_saved_language')} ``` **", color=discord.Color.dark_grey())
        await interaction.response.edit_message(embed=embed_ok, view=None)
        await asyncio.sleep(2)
        await interaction.edit_original_response(embed=config_embed(self.guild.id), view=ConfigMenu(self.guild.id))

async def setup(bot: commands.Bot):
    await bot.add_cog(Config(bot))