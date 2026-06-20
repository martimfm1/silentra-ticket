import json
from pathlib import Path
from services.logs import logger
from database.repository import get_server_config

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"

DEFAULT_LANGUAGE = "en"
TRANSLATION_FILES = {
    "en": "translation-en.json",
    "pt-PT": "translation-pt-pt.json",
    "pt-BR": "translation-pt-br.json",
}
TRANSLATIONS: dict[str, dict[str, str]] = {}


def load_translations():
    logger.info(f"I18n: Initializing loading of locations from: {LOCALES_DIR}")
    
    if not LOCALES_DIR.exists():
        logger.warning(f"I18n: The directory {LOCALES_DIR} does not exist. Create it automatically.")
        LOCALES_DIR.mkdir(parents=True, exist_ok=True)

    for lang_code, file_name in TRANSLATION_FILES.items():
        file_path = LOCALES_DIR / file_name
        
        try:
            if not file_path.exists():
                logger.error(f"I18n: Required translation file missing: '{file_path}'")
                TRANSLATIONS[lang_code] = {}
                continue

            with file_path.open("r", encoding="utf-8") as file:
                TRANSLATIONS[lang_code] = json.load(file)
                
            logger.info(f"I18n: Language '{lang_code}' loaded successfully. ({len(TRANSLATIONS[lang_code])} braces)")
            
        except json.JSONDecodeError as exc:
            logger.exception(f"I18n: Critical syntax error (Invalid JSON) in file {file_name}: {exc}")
            TRANSLATIONS[lang_code] = {}
        except Exception:
            logger.exception(f"I18n: Unexpected I/O error while reading file {file_path}")
            TRANSLATIONS[lang_code] = {}


def get_language(guild_id: int) -> str:

    try:
        if not guild_id or guild_id == 0:
            return DEFAULT_LANGUAGE
            
        config = get_server_config(guild_id) or {}
        language = config.get("LANGUAGE", DEFAULT_LANGUAGE)
        
        if language in TRANSLATIONS:
            return language
            
        return DEFAULT_LANGUAGE
    except Exception:
        logger.error(f"I18n: Failed to resolve language for Guild {guild_id}. Using emergency fallback: {DEFAULT_LANGUAGE}")
        return DEFAULT_LANGUAGE


def tr(guild_id: int, key: str, **kwargs) -> str:

    language = get_language(guild_id)
    
    text = (
        TRANSLATIONS.get(language, {}).get(key)
        or TRANSLATIONS.get(DEFAULT_LANGUAGE, {}).get(key)
    )

    if text is None:
        logger.warning(f"I18n Missing Key: The key '{key}' was not found in the language packs (Guild: {guild_id}).")
        text = key

    try:
        return text.format(**kwargs)
    except KeyError as k_err:
        logger.error(f"I18n Format Error: Missing argument {k_err} to process key template '{key}' ({language})")
        return text
    except Exception:
        logger.exception(f"I18n Format Error: Unexpected error while formatting parameters in string '{key}'")
        return text