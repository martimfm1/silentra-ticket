from services.logs import logger
from database.database import supabase

def get_server_config(guild_id: int) -> dict:
    try:
        response = supabase.table("servers").select("*").eq("guild_id", guild_id).execute()
        
        if response and hasattr(response, 'data') and response.data:
            return response.data[0]
            
        return {}
    except Exception as e:
        logger.error(f"DB Error: Failed to read configuration for Guild {guild_id}: {e}")
        return {}


def set_server_language(guild_id: int, language: str) -> bool:
    try:
        payload = {
            "guild_id": guild_id,
            "language": language
        }
        response = supabase.table("servers").upsert(payload).execute()
        
        logger.info(f"DB Audit: Guild language {guild_id} changed to '{language}'.")
        return response and hasattr(response, 'data') and len(response.data) > 0
    except Exception as e:
        logger.error(f"DB Error: Failed to set language for Guild {guild_id}: {e}")
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
        logger.error(f"DB Error: Failed to insert ticket from channel {channel_id} into Supabase: {e}")
        return False


def get_ticket_by_channel_id(channel_id: int) -> dict:
    try:
        response = supabase.table("tickets").select("*").eq("channel_id", channel_id).maybe_single().execute()
        return response.data or {}
    except Exception as e:
        logger.error(f"DB Error: Error retrieving ticket from channel {channel_id}: {e}")
        return {}
    
def close_ticket_db(channel_id: int):

    pass

def delete_ticket_by_channel_id(channel_id: int):
    try:
        supabase.table("tickets").delete().eq("channel_id", channel_id).execute()
        logger.info(f"DB Audit: Ticket for channel {channel_id} successfully removed from Supabase.")
    except Exception as e:
        logger.error(f"DB Error: Failed to delete ticket {channel_id}: {e}")


def get_all_server_ids() -> list[int]:
    try:
        response = supabase.table("servers").select("guild_id").execute()
        if response.data:
            return [int(row["guild_id"]) for row in response.data]
        return []
    except Exception as e:
        logger.error(f"DB Error: Failed to list server IDs for rehydration: {e}")
        return []


def save_server_config(guild_id: int, config_data: dict) -> bool:
    try:
        payload = {"guild_id": guild_id, **config_data}

        response = supabase.table("servers").upsert(payload).execute()
        
        logger.info(f"DB Audit: Guild {guild_id} settings updated successfully.")
        return len(response.data) > 0
    except Exception as e:
        logger.error(f"DB Error: Failed to execute configuration upsert for Guild {guild_id}: {e}")
        return False