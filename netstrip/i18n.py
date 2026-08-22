"""
Lightweight internationalization layer for NetStrip.

Usage:
    from netstrip.i18n import t
    label = t("nav.dashboard")          # returns translated or English fallback

Catalogs live in netstrip/locales/<lang>.json as flat "key": "text" maps.
English keys double as the source strings, so missing translations degrade
gracefully to the key's English text.

Language selection order: NETSTRIP_LANG env var → Windows registry → OS locale.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_LOCALES_DIR = Path(__file__).parent / "locales"
_fallback_lang = "en"
_current_lang = None
_catalog = {}


def available_languages():
    langs = ["en"]
    if _LOCALES_DIR.exists():
        langs += sorted(p.stem for p in _LOCALES_DIR.glob("*.json") if p.stem != "en")
    return langs


def detect_language() -> str:
    """Best-effort OS language detection (no GUI dependency)."""
    env = os.environ.get("NETSTRIP_LANG")
    if env:
        return env[:2].lower()

    if sys.platform.startswith("win"):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Control Panel\International") as k:
                name = winreg.QueryValueEx(k, "LocaleName")[0]
                return name[:2].lower()
        except Exception:
            pass

    lang = os.environ.get("LC_ALL") or os.environ.get("LANG") or ""
    return lang.split("_")[0].split(".")[0][:2].lower() or "en"


import sys  # noqa: E402


# Native display names (shown in the Settings picker)
LANGUAGE_NAMES = {
    "en": "English", "es": "Español", "de": "Deutsch", "fr": "Français",
    "it": "Italiano", "pt": "Português", "nl": "Nederlands", "pl": "Polski",
    "tr": "Türkçe", "ru": "Русский", "uk": "Українська", "ja": "日本語",
    "ko": "한국어", "zh-cn": "简体中文", "zh-tw": "繁體中文", "hi": "हिन्दी",
    "id": "Bahasa Indonesia", "vi": "Tiếng Việt", "ar": "العربية",
    "sv": "Svenska", "da": "Dansk", "fi": "Suomi", "cs": "Čeština",
    "el": "Ελληνικά", "hu": "Magyar", "ro": "Română",
}


def language_name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, code.capitalize())


RTL_LANGUAGES = {"ar", "he", "fa", "ur"}


def is_rtl() -> bool:
    return get_language() in RTL_LANGUAGES


def has(key: str) -> bool:
    return key in _catalog


def tooltip_for(english_key: str):
    """Translated hovertip for a TOOLTIP_MAP key, or None (English fallback)."""
    return _catalog.get("tooltip." + english_key)


def tr(english: str) -> str:
    """Translate a literal English UI string (gettext-style flat lookup).
    Falls back to the English text when no translation exists — safe to wrap
    every string without inventing keys."""
    return _catalog.get(english, english)


def set_language(lang: str):
    global _current_lang, _catalog
    lang = (lang or "en").lower()
    path = _LOCALES_DIR / f"{lang}.json"
    if not path.exists() and "-" in lang:
        # 'pt-br' -> 'pt' style fallback before giving up
        primary = lang.split("-")[0]
        p2 = _LOCALES_DIR / f"{primary}.json"
        if p2.exists():
            lang, path = primary, p2
    if not path.exists():
        logger.debug(f"no catalog for '{lang}', falling back to English")
        lang = "en"
        path = _LOCALES_DIR / f"{lang}.json"
    _current_lang = lang
    _catalog = {}
    if path.exists():
        try:
            _catalog = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"failed to load catalog {path}: {e}")


def get_language() -> str:
    return _current_lang or "en"


def t(key: str, **kwargs) -> str:
    """Translate a dotted key; kwargs format the result. Falls back to the
    final path segment of the key (the English source string)."""
    text = _catalog.get(key)
    if text is None:
        text = key.rsplit(".", 1)[-1]
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    return text


# Initialize on import
set_language(detect_language())
