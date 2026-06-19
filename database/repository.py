import logging
from database.database import supabase

logger = logging.getLogger(__name__)

def get_server_config(guild_id: int) -> dict:
    try:
        response = supabase.table("servers").select("*").eq("guild_id", guild_id).execute()
        
        if response and hasattr(response, 'data') and response.data:
            return response.data[0]
            
        return {}
    except Exception as e:
        logger.error(f"DB Error: Falha ao ler configuração da Guild {guild_id}: {e}")
        return {}


def set_server_language(guild_id: int, language: str) -> bool:
    try:
        payload = {
            "guild_id": guild_id,
            "language": language
        }
        response = supabase.table("servers").upsert(payload).execute()
        
        logger.info(f"DB Audit: Idioma da Guild {guild_id} alterado para '{language}'.")
        return response and hasattr(response, 'data') and len(response.data) > 0
    except Exception as e:
        logger.error(f"DB Error: Falha ao definir idioma para a Guild {guild_id}: {e}")
        return False


def create_ticket_db(guild_id: int, channel_id: int, user_id: int, subject: str) -> bool:
    try:
        server_exists = get_server_config(guild_id)
        if not server_exists:
            supabase.table("servers").insert({"guild_id": guild_id}).execute()

        payload = {
            "channel_id": channel_id,
            "guild_id": guild_id,
            "user_id": user_id,
            "subject": subject
        }
        
        response = supabase.table("tickets").insert(payload).execute()
        return len(response.data) > 0
    except Exception as e:
        logger.error(f"DB Error: Falha ao inserir ticket do canal {channel_id} na Supabase: {e}")
        return False


def get_ticket_by_channel_id(channel_id: int) -> dict:
    try:
        response = supabase.table("tickets").select("*").eq("channel_id", channel_id).maybe_single().execute()
        return response.data or {}
    except Exception as e:
        logger.error(f"DB Error: Erro ao buscar ticket do canal {channel_id}: {e}")
        return {}
    
def close_ticket_db(channel_id: int):

    pass

def delete_ticket_by_channel_id(channel_id: int):
    try:
        supabase.table("tickets").delete().eq("channel_id", channel_id).execute()
        logger.info(f"DB Audit: Ticket do canal {channel_id} removido com sucesso da Supabase.")
    except Exception as e:
        logger.error(f"DB Error: Falha ao deletar ticket {channel_id}: {e}")


def get_all_server_ids() -> list[int]:
    try:
        response = supabase.table("servers").select("guild_id").execute()
        if response.data:
            return [int(row["guild_id"]) for row in response.data]
        return []
    except Exception as e:
        logger.error(f"DB Error: Falha ao listar IDs de servidores para reidratação: {e}")
        return []


def save_server_config(guild_id: int, config_data: dict) -> bool:
    try:
        payload = {"guild_id": guild_id, **config_data}

        response = supabase.table("servers").upsert(payload).execute()
        
        logger.info(f"DB Audit: Configurações da Guild {guild_id} atualizadas com sucesso.")
        return len(response.data) > 0
    except Exception as e:
        logger.error(f"DB Error: Falha ao executar upsert de configuração para a Guild {guild_id}: {e}")
        return False