from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Localizer:
    locales_dir: Path
    fallback_locale: str = "fa"

    def __post_init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}

    def _load(self, locale: str) -> dict[str, Any]:
        if locale not in self._cache:
            self._cache[locale] = json.loads((self.locales_dir / f"{locale}.json").read_text(encoding="utf-8"))
        return self._cache[locale]

    def get(self, locale: str | None, key: str, **kwargs: Any) -> str:
        locale = locale or self.fallback_locale
        data: Any = self._load(locale)
        for part in key.split("."):
            if not isinstance(data, dict) or part not in data:
                data = None
                break
            data = data[part]
        if data is None and locale != self.fallback_locale:
            return self.get(self.fallback_locale, key, **kwargs)
        if not isinstance(data, str):
            return key
        return data.format(**kwargs) if kwargs else data
