from portfolio.locale import normalize_locale, resolve_locale


def test_normalize_locale_supports_en_vi_only():
    assert normalize_locale("vi") == "vi"
    assert normalize_locale("vi-VN") == "vi"
    assert normalize_locale("en-US") == "en"
    assert normalize_locale("fr") == "en"


def test_cookie_preference_wins_over_browser_language():
    assert resolve_locale("qport_lang=vi", "en-US,en;q=0.9") == "vi"
    assert resolve_locale("qport_lang=en", "vi-VN,vi;q=0.9") == "en"


def test_browser_language_is_initial_default():
    assert resolve_locale(None, "vi-VN,vi;q=0.9,en;q=0.8") == "vi"
    assert resolve_locale(None, "en-US,en;q=0.9") == "en"


def test_unsupported_language_falls_back_to_english():
    assert resolve_locale(None, "fr-FR,fr;q=0.9") == "en"
    assert resolve_locale("qport_lang=xx", "fr-FR") == "en"
