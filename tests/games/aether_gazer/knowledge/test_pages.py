"""Tests for knowledge.pages module."""
from anime_game_afk.games.aether_gazer.knowledge.pages import (
    ALL_PAGES,
    SAFE_PAGES,
    UNSAFE_PAGES,
    find_element,
    get_page,
)


def test_total_page_count():
    """All 23 pages defined (15 top-level + 7 sub-pages + 1 stamina panel)."""
    assert len(ALL_PAGES) == 23


def test_main_hub_exists():
    hub = get_page("main_hub")
    assert hub is not None
    assert hub.name_en == "Main Hub"
    assert hub.parent_page == ""


def test_main_hub_elements():
    hub = get_page("main_hub")
    assert hub is not None
    assert len(hub.elements) == 12


def test_unsafe_pages():
    assert "gacha" in UNSAFE_PAGES
    assert "inventory" in UNSAFE_PAGES
    assert "main_hub" not in UNSAFE_PAGES


def test_safe_pages_excludes_hub():
    assert "main_hub" not in SAFE_PAGES


def test_find_element_exists():
    elem = find_element("main_hub", "Battle")
    assert elem is not None
    assert elem.coord.x == 1465
    assert elem.coord.y == 850
    assert elem.target_page == "battle_select"


def test_find_element_missing():
    assert find_element("main_hub", "NonExistent") is None
    assert find_element("no_such_page", "Battle") is None


def test_all_pages_have_unique_ids():
    ids = [p.page_id for p in ALL_PAGES.values()]
    assert len(ids) == len(set(ids))


def test_character_page_has_back():
    elem = find_element("character", "Back")
    assert elem is not None
    assert elem.target_page == "main_hub"
