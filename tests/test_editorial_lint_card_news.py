from __future__ import annotations

import pytest

from pipeline import editorial_lint


@pytest.mark.card_news
def test_card_news_structure_cases(fixture_json: callable) -> None:
    passed = editorial_lint.check_card_news_structure(fixture_json("slides", "slides_pass.json")["slides"])
    failed = editorial_lint.check_card_news_structure(fixture_json("slides", "slides_hook_missing.json")["slides"])
    cta_missing = editorial_lint.check_card_news_structure(
        fixture_json("slides", "slides_pass.json")["slides"][:-1]
    )
    assert passed["status"] == "pass"
    assert failed["status"] == "fail"
    assert cta_missing["status"] == "fail"


@pytest.mark.card_news
def test_card_news_density_cases(fixture_json: callable) -> None:
    passed = editorial_lint.check_card_news_density(fixture_json("slides", "slides_pass.json")["slides"])
    failed = editorial_lint.check_card_news_density(fixture_json("slides", "slides_low_density.json")["slides"])
    assert passed["status"] == "pass"
    assert failed["status"] == "fail"


@pytest.mark.card_news
def test_source_fidelity_cases(fixture_json: callable) -> None:
    slides = fixture_json("slides", "slides_pass.json")["slides"]
    source_md = (
        "Alpha Corp shipped a new assistant and explained the rollout plan in detail.\n"
        "Admins can phase adoption team by team with enterprise controls.\n"
        "Governance, cost control, and workflow are all covered clearly.\n"
    )
    passed = editorial_lint.check_source_fidelity(slides, source_md)
    failed = editorial_lint.check_source_fidelity(
        slides,
        (
            "Volcanic geology studies describe basaltic magma transport in island arcs.\n"
            "Marine biology reports focus on coral spawning cycles and reef recovery.\n"
        ),
    )
    assert passed["status"] == "pass"
    assert failed["status"] == "fail"


@pytest.mark.card_news
def test_slide_count_cases(fixture_json: callable) -> None:
    slides = fixture_json("slides", "slides_pass.json")["slides"]
    passed = editorial_lint.check_slide_count(slides + slides, 800)
    failed = editorial_lint.check_slide_count(slides[:2], 1800)
    assert passed["status"] == "pass"
    assert failed["status"] == "fail"


@pytest.mark.card_news
def test_card_news_edge_cases() -> None:
    empty = editorial_lint.check_card_news_structure([])
    fidelity_warn = editorial_lint.check_source_fidelity(
        [{"idx": 1, "role": "hook", "main_copy": "Only hook", "sub_copy": "", "highlight": ""}],
        "",
    )
    summary = editorial_lint.lint_card_news(
        [{"idx": 1, "role": "hook", "main_copy": "Only hook", "sub_copy": "", "highlight": ""}],
        "",
    )
    assert empty["status"] == "fail"
    assert fidelity_warn["status"] == "warn"
    assert summary["failed"] >= 1
