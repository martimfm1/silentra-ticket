import discord
from services.logs import logger
from discord.ext import commands, tasks

from database.database import validate_db_connection
from database.repository import get_server_config
from services.translation_service import load_translations, tr
from views.ticket_buttons import TicketButtons
from views.ticket_view import TicketView


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.persistent_views_added = False
        self.status_index = 0

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("Lifecycle: 'on_ready' triggered by the Discord gateway.")
        
        try:
            load_translations()
            logger.info("Translations successfully loaded into the local system.")
        except Exception:
            logger.exception("Critical error occurred while loading international translation files.")

        try:
            validate_db_connection()
            logger.info("Connection to the database successfully validated.")
        except Exception:
            logger.exception("Failure in the integrity of the connection to the Production Database.")

        if not self.change_status.is_running():
            self.change_status.start()
            logger.info("The presence rotation loop (Status) has been initialized.")

        if not self.persistent_views_added:
            logger.info(f"Initializing registration of Persistent Views for {len(self.bot.guilds)} servers.")
            
            for guild in self.bot.guilds:
                try:
                    config = get_server_config(guild.id) or {}
                    admin_role = config.get("ADMIN_ROLE_NAME")

                    self.bot.add_view(TicketView(guild.id))
                    
                    self.bot.add_view(TicketButtons(guild.id, admin_role_name=admin_role))
                    
                    logger.debug(f"Persistent views successfully registered for Guild ID: {guild.id}")
                except Exception:
                    logger.exception(f"Isolation error while registering persistent views for Guild ID {guild.id}. Skipping...")

            self.persistent_views_added = True
            logger.info("The process of injecting persistent views has been completed.")

        logger.info(f"🚀 Full operating system. Bot authenticated as: {self.bot.user}")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        try:
            config = get_server_config(guild.id) or {}
            admin_role = config.get("ADMIN_ROLE_NAME")
            
            self.bot.add_view(TicketView(guild.id))
            self.bot.add_view(TicketButtons(guild.id, admin_role_name=admin_role))
            
            logger.info(f"Dynamic Security: New Views injected via on_guild_join for the server {guild.name} ({guild.id})")
        except Exception:
            logger.exception(f"Failed to process dynamic view registration on the new server {guild.id}")

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
            logger.debug(f"Presence successfully updated for index state {self.status_index}")
        except Exception as e:
            logger.error(f"Error interacting with the Discord gateway API to update presence: {e}")
        
        self.status_index += 1

    @change_status.before_loop
    async def before_change_status(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))