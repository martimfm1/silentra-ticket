import json
import logging
from pathlib import Path
from database.repository import get_server_config

logger = logging.getLogger(__name__)

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"

DEFAULT_LANGUAGE = "en"
TRANSLATION_FILES = {
    "en": "traducao-en.json",
    "pt-PT": "traducao-pt-pt.json",
    "pt-BR": "traducao-pt-br.json",
}
TRANSLATIONS: dict[str, dict[str, str]] = {}


def load_translations():
    logger.info(f"I18n: A inicializar carregamento de locais a partir de: {LOCALES_DIR}")
    
    if not LOCALES_DIR.exists():
        logger.warning(f"I18n: O diretório {LOCALES_DIR} não existe. A criá-lo automaticamente.")
        LOCALES_DIR.mkdir(parents=True, exist_ok=True)

    for lang_code, file_name in TRANSLATION_FILES.items():
        file_path = LOCALES_DIR / file_name
        
        try:
            if not file_path.exists():
                logger.error(f"I18n: Ficheiro de tradução obrigatório em falta: '{file_path}'")
                TRANSLATIONS[lang_code] = {}
                continue

            with file_path.open("r", encoding="utf-8") as file:
                TRANSLATIONS[lang_code] = json.load(file)
                
            logger.info(f"I18n: Idioma '{lang_code}' carregado com sucesso. ({len(TRANSLATIONS[lang_code])} chaves)")
            
        except json.JSONDecodeError as exc:
            logger.exception(f"I18n: Erro crítico de sintaxe (JSON Inválido) no ficheiro {file_name}: {exc}")
            TRANSLATIONS[lang_code] = {}
        except Exception:
            logger.exception(f"I18n: Erro inesperado de I/O ao ler o ficheiro {file_path}")
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
        logger.error(f"I18n: Falha ao resolver idioma para Guild {guild_id}. A usar fallback de emergência: {DEFAULT_LANGUAGE}")
        return DEFAULT_LANGUAGE


def tr(guild_id: int, key: str, **kwargs) -> str:

    language = get_language(guild_id)
    
    text = (
        TRANSLATIONS.get(language, {}).get(key)
        or TRANSLATIONS.get(DEFAULT_LANGUAGE, {}).get(key)
    )

    if text is None:
        logger.warning(f"I18n Missing Key: A chave '{key}' não foi encontrada nos pacotes de idioma (Guild: {guild_id}).")
        text = key

    try:
        return text.format(**kwargs)
    except KeyError as k_err:
        logger.error(f"I18n Format Error: Falta o argumento {k_err} para processar o template da chave '{key}' ({language})")
        return text
    except Exception:
        logger.exception(f"I18n Format Error: Erro inesperado ao formatar parâmetros na string '{key}'")
        return text