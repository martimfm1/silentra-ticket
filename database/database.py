import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

logger = logging.getLogger(__name__)
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.critical("Infraestrutura: Variáveis SUPABASE_URL ou SUPABASE_KEY ausentes no .env!")
    raise ValueError("Variáveis de ambiente da Supabase não configuradas.")

def validate_db_connection() -> bool:
    try:
        supabase.table("servers").select("guild_id").limit(1).execute()
        return True
    except Exception as e:
        logger.critical(f"DB Connection Error: Falha no handshake com a Supabase: {e}")
        return False

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
logger.info("Infraestrutura: Ligação ao gateway da Supabase estabelecida.")