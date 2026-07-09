import json
from pathlib import Path

_LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"
_SUPPORTED = ("fa", "en")
_DEFAULT = "fa"

_cache: dict[str, dict] = {}


def _load(lang: str) -> dict:
    if lang not in _cache:
        path = _LOCALES_DIR / f"{lang}.json"
        with open(path, encoding="utf-8") as f:
            _cache[lang] = json.load(f)
    return _cache[lang]


def t(lang: str | None, key: str, **kwargs) -> str:
    """Translate `key` into `lang` (falling back to the default language),
    formatting with kwargs if given."""
    lang = lang if lang in _SUPPORTED else _DEFAULT
    data = _load(lang)
    text = data.get(key)
    if text is None:
        # fall back to default language, then to the raw key as last resort
        text = _load(_DEFAULT).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


def t_raw(lang: str | None, key: str) -> str:
    """Like t(), but returns the string unformatted (no .format() applied) --
    useful when the string itself contains a literal placeholder that must
    be filled in later, e.g. a broadcast template applied per-recipient."""
    lang = lang if lang in _SUPPORTED else _DEFAULT
    data = _load(lang)
    text = data.get(key)
    if text is None:
        text = _load(_DEFAULT).get(key, key)
    return text


def is_supported(lang: str) -> bool:

    return lang in _SUPPORTED
