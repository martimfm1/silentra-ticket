import asyncio
import os
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

from services.translation_service import load_translations
from views.ticket_view import TicketView
from views.ticket_buttons import TicketButtons
from database.repository import get_all_server_ids

logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("Falha Crítica: A variável de ambiente 'DISCORD_TOKEN' está em falta no ficheiro .env")


class SilentraTicket(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True 
        
        intents.message_content = True 
        
        super().__init__(
            command_prefix='101', 
            intents=intents, 
            max_messages=200,
            activity=discord.Activity(type=discord.ActivityType.watching, name="o suporte | 101help")
        )

    async def setup_hook(self):
        load_translations()

        initial_extensions = ["cogs.tickets", "cogs.config", "cogs.events"]
        
        for extension in initial_extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"Extension Gateway: Módulo '{extension}' carregado com sucesso.")
            except Exception as e:
                logger.error(f"Falha Crítica de Extensão: Não foi possível carregar o módulo '{extension}': {e}")

        try:
            server_ids = get_all_server_ids()
            
            registered_count = 0
            for g_id in server_ids:
                self.add_view(TicketView(guild_id=g_id))
                self.add_view(TicketButtons(guild_id=g_id))
                registered_count += 1
            
            logger.info(f"Infraestrutura de UI: Reidratadas {registered_count} Persistent Views com sucesso via Supabase.")
        except Exception:
            logger.exception("Falha Crítica de Infraestrutura: Erro ao reidratar Persistent Views no setup_hook.")

        try:
            logger.info("Tree Sync: A iniciar sincronização global de comandos com a API do Discord...")
            await self.tree.sync()
            logger.info("Tree Sync: Árvore de Comandos Sincronizada com Sucesso!")
        except discord.HTTPException as http_err:
            logger.error(f"Tree Sync Falhou: Bloqueio por Rate-Limit ou Erro de API do Discord: {http_err}")
        except Exception:
            logger.exception("Tree Sync Falhou: Erro inesperado ao sincronizar comandos.")

    async def on_ready(self):
        logger.info("=========================================================")
        logger.info(f" SISTEMA ONLINE :: Conectado como: {self.user.name} ({self.user.id})")
        logger.info(f" INFRAESTRUTURA :: A monitorizar {len(self.guilds)} servidores em simultâneo.")
        logger.info("=========================================================")

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    bot = SilentraTicket()
    
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot desligado manualmente via sinal de interrupção (Ctrl+C).")