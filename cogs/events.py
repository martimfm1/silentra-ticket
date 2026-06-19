import asyncio
import logging
import discord
from discord.ext import commands, tasks

from database.database import validate_db_connection
from database.repository import get_server_config
from services.translation_service import load_translations, tr
from views.ticket_buttons import TicketButtons
from views.ticket_view import TicketView

logger = logging.getLogger(__name__)

class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.persistent_views_added = False
        self.status_index = 0

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("Ciclo de vida: 'on_ready' disparado pelo gateway do Discord.")
        
        try:
            load_translations()
            logger.info("Traduções carregadas com sucesso no sistema local.")
        except Exception:
            logger.exception("Falha crítica ao carregar ficheiros de tradução internacional.")

        try:
            validate_db_connection()
            logger.info("Ligação à Base de Dados validada com sucesso.")
        except Exception:
            logger.exception("Falha na integridade da ligação com a Base de Dados de Produção.")

        if not self.change_status.is_running():
            self.change_status.start()
            logger.info("Loop de rotação de presenças (Status) inicializado.")

        if not self.persistent_views_added:
            logger.info(f"A inicializar registo de Views Persistentes para {len(self.bot.guilds)} servidores.")
            
            for guild in self.bot.guilds:
                try:
                    config = get_server_config(guild.id) or {}
                    admin_role = config.get("ADMIN_ROLE_NAME")

                    self.bot.add_view(TicketView(guild.id))
                    
                    self.bot.add_view(TicketButtons(guild.id, admin_role_name=admin_role))
                    
                    logger.debug(f"Views persistentes registadas com sucesso para a Guild ID: {guild.id}")
                except Exception:
                    logger.exception(f"Erro de isolamento ao registar views persistentes para a Guild ID {guild.id}. A saltar...")

            self.persistent_views_added = True
            logger.info("Processo de injeção de Views Persistentes concluído.")

        logger.info(f"🚀 Sistema operacional completo. Bot autenticado como: {self.bot.user}")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        try:
            config = get_server_config(guild.id) or {}
            admin_role = config.get("ADMIN_ROLE_NAME")
            
            self.bot.add_view(TicketView(guild.id))
            self.bot.add_view(TicketButtons(guild.id, admin_role_name=admin_role))
            
            logger.info(f"Segurança Dinâmica: Novas Views injetadas via on_guild_join para o servidor {guild.name} ({guild.id})")
        except Exception:
            logger.exception(f"Falha ao processar registo dinâmico de views no novo servidor {guild.id}")

    @tasks.loop(seconds=10)
    async def change_status(self):
        server_count = len(self.bot.guilds)

        activities = [
            discord.Activity(type=discord.ActivityType.watching, name=tr(0, "activity_dev")),
            discord.Activity(type=discord.ActivityType.watching, name=tr(0, "activity_manage_servers", server_count=server_count)),
            discord.Activity(type=discord.ActivityType.watching, name=tr(0, "activity_free_bot"))
        ]

        current_activity = activities[self.status_index % len(activities)]
        
        try:
            await self.bot.change_presence(activity=current_activity)
            logger.debug(f"Presença atualizada com sucesso para o estado índice {self.status_index}")
        except Exception as e:
            logger.error(f"Erro ao interagir com a API de gateway do Discord para atualizar presença: {e}")
        
        self.status_index += 1

    @change_status.before_loop
    async def before_change_status(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))