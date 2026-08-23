from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend" / "src"


def test_mobile_scroll_contract_is_loaded_after_iphone_shell():
    entry = (FRONTEND / "entry-client.jsx").read_text(encoding="utf-8")
    assert "import './mobile-iphone.css';" in entry
    assert "import './mobile-scroll-fix.css';" in entry
    assert entry.index("import './mobile-scroll-fix.css';") > entry.index("import './mobile-iphone.css';")


def test_mobile_document_remains_the_vertical_scroller():
    css = (FRONTEND / "mobile-scroll-fix.css").read_text(encoding="utf-8")
    assert "@media (max-width: 719px)" in css
    assert "overflow-y: auto !important" in css
    assert "#root" in css
    assert ".page" in css
    assert "height: auto !important" in css
    assert "overflow: visible !important" in css
    assert "touch-action: pan-y pinch-zoom" in css
    assert "-webkit-overflow-scrolling: touch" in css


def test_only_open_mobile_sheet_locks_document_scroll():
    css = (FRONTEND / "mobile-scroll-fix.css").read_text(encoding="utf-8")
    entry = (FRONTEND / "entry-client.jsx").read_text(encoding="utf-8")
    assert "body:not(.mobile-sheet-open)" in css
    assert "body.mobile-sheet-open" in css
    assert "overflow: hidden !important" in css
    assert "document.body.classList.remove('mobile-sheet-open')" in entry
