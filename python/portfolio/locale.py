from __future__ import annotations

from http.cookies import SimpleCookie

SUPPORTED_LOCALES = {"en", "vi"}
DEFAULT_LOCALE = "en"
COOKIE_NAME = "qport_lang"


def normalize_locale(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    if raw.startswith("vi"):
        return "vi"
    if raw.startswith("en"):
        return "en"
    return DEFAULT_LOCALE


def _cookie_locale(cookie_header: str | None) -> str | None:
    if not cookie_header:
        return None
    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header)
    except Exception:
        return None
    morsel = cookie.get(COOKIE_NAME)
    if not morsel:
        return None
    value = str(morsel.value or "").strip().lower()
    return value if value in SUPPORTED_LOCALES else None


def _accept_language_locale(accept_language: str | None) -> str | None:
    if not accept_language:
        return None
    weighted: list[tuple[float, int, str]] = []
    for index, item in enumerate(str(accept_language).split(",")):
        part = item.strip()
        if not part:
            continue
        pieces = [x.strip() for x in part.split(";") if x.strip()]
        language = pieces[0].lower()
        quality = 1.0
        for parameter in pieces[1:]:
            if parameter.startswith("q="):
                try:
                    quality = float(parameter[2:])
                except ValueError:
                    quality = 0.0
        normalized = normalize_locale(language)
        if language.startswith(("vi", "en")):
            weighted.append((quality, -index, normalized))
    if not weighted:
        return None
    weighted.sort(reverse=True)
    return weighted[0][2]


def resolve_locale(cookie_header: str | None = None, accept_language: str | None = None) -> str:
    """Resolve QPort UI locale without coupling locale to portfolio state.

    Explicit user preference stored in ``qport_lang`` wins. Browser language is
    only an initial default. Unsupported languages fall back to English.
    """

    return _cookie_locale(cookie_header) or _accept_language_locale(accept_language) or DEFAULT_LOCALE
