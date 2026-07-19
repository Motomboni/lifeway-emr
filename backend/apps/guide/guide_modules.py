"""Guide module toggles — org-scoped feature flags for articles and role launch."""

from __future__ import annotations

DEFAULT_GUIDE_MODULES: dict[str, bool] = {
    "core": True,
    "laboratory": True,
    "pharmacy": True,
    "radiology": True,
    "nhia": True,
    "anc": True,
    "telemedicine": True,
}

GUIDE_MODULE_KEYS = list(DEFAULT_GUIDE_MODULES.keys())


def normalize_guide_modules(raw: dict | None) -> dict[str, bool]:
    """Merge stored org settings with defaults."""
    result = dict(DEFAULT_GUIDE_MODULES)
    if raw:
        for key in GUIDE_MODULE_KEYS:
            if key in raw:
                result[key] = bool(raw[key])
    return result


def article_module_allowed(article: dict, modules: dict[str, bool]) -> bool:
    """Return True when the article's module is enabled for the org."""
    module = article.get("module")
    if module is None:
        return modules.get("core", True)
    return modules.get(module, True)
