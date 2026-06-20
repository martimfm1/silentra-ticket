import os
from dotenv import load_dotenv
from services.logs import logger
from supabase import create_client, Client


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.critical("Infrastructure: SUPABASE_URL or SUPABASE_KEY variables are missing in the .env file!")
    raise ValueError("Supabase environment variables are not configured.")

def validate_db_connection() -> bool:
    try:
        supabase.table("servers").select("guild_id").limit(1).execute()
        return True
    except Exception as e:
        logger.critical(f"DB Connection Error: Handshake with the Supabase failed: {e}")
        return False

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
logger.info("Infrastructure: Connection to the Supabase gateway established.")