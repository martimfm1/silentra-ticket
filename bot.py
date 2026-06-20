import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from services.logs import logger

from services.translation_service import load_translations
from views.ticket_view import TicketView
from views.ticket_buttons import TicketButtons
from database.repository import get_all_server_ids

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("Critical Error: The environment variable 'DISCORD_TOKEN' is missing from the .env file.")


class SilentraTicket(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True 
        
        intents.message_content = True 
        
        super().__init__(
            command_prefix='101', 
            intents=intents, 
            max_messages=200,
            activity=discord.Activity(type=discord.ActivityType.watching, name="the suport")
        )

    async def setup_hook(self):
        load_translations()

        initial_extensions = ["cogs.tickets", "cogs.config", "cogs.events"]
        
        for extension in initial_extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"Extension Gateway: Module '{extension}' loaded successfully.")
            except Exception as e:
                logger.error(f"Critical Extension Failure: Could not load module '{extension}': {e}")

        try:
            server_ids = get_all_server_ids()
            
            registered_count = 0
            for g_id in server_ids:
                self.add_view(TicketView(guild_id=g_id))
                self.add_view(TicketButtons(guild_id=g_id))
                registered_count += 1
            
            logger.info(f"UI Infrastructure: Successfully rehydrated {registered_count} Persistent Views via Supabase.")
        except Exception:
            logger.exception("Critical Infrastructure Failure: Error rehydrating Persistent Views in setup_hook.")

        try:
            logger.info("Tree Sync: Starting global command synchronization with the Discord API...")
            await self.tree.sync()
            logger.info("Tree Sync: Command Tree Synchronized Successfully!")
        except discord.HTTPException as http_err:
            logger.error(f"Tree Sync Failed: Rate-Limit Blocking or Discord API Error: {http_err}")
        except Exception:
            logger.exception("Tree Sync Failed: Unexpected error while synchronizing commands.")

    async def on_ready(self):
        logger.info("=========================================================")
        logger.info(f" ONLINE SYSTEM :: Connected as: {self.user.name} ({self.user.id})")
        logger.info(f" INFRASTRUCTURE :: Monitoring {len(self.guilds)} servers simultaneously.")
        logger.info("=========================================================")

async def main():
    bot = SilentraTicket()
    
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("The bot was manually shut down via the interrupt signal (Ctrl+C).")