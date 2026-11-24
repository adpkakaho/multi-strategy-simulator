"""STEP 1 믹스 — 구축방안 4.1 표의 숫자를 그대로 재현하는지 확인한다."""

import pytest

from simulator.mix import blend, contributions, overlap, pairwise_overlap, shared_stocks
from simulator.scenario import DOC_CARDS, DOC_STRATEGY_WEIGHTS

CARDS = {card["id"]: card["holdings"] for card in DOC_CARDS}


def test_doc_4_1_blended_weights():
    mp = blend(contributions(DOC_STRATEGY_WEIGHTS, CARDS))
    assert mp == pytest.approx(
        {"삼성전자": 22, "한미반도체": 18, "SK하이닉스": 14, "KB금융": 12,
         "현대차": 10, "KT&G": 10, "네이버": 8, "카카오": 6}
    )
    assert sum(mp.values()) == pytest.approx(100)


def test_doc_4_1_contributions_of_shared_stocks():
    contrib = contributions(DOC_STRATEGY_WEIGHTS, CARDS)
    assert contrib["삼성전자"] == pytest.approx({"A": 14, "B": 8})
    assert contrib["한미반도체"] == pytest.approx({"A": 12, "C": 6})
    assert sorted(shared_stocks(contrib)) == ["삼성전자", "한미반도체"]


def test_blend_sums_to_total_strategy_weight():
    weights = {"A": 50, "B": 30, "C": 0}
    contrib = contributions(weights, CARDS)
    assert sum(blend(contrib).values()) == pytest.approx(80)
    assert all("C" not in by_card for by_card in contrib.values())
    assert "네이버" not in contrib


def test_overlap():
    assert overlap(CARDS["A"], CARDS["B"]) == pytest.approx(20)  # 삼성전자 min(35, 20)
    assert overlap(CARDS["A"], CARDS["C"]) == pytest.approx(30)  # 한미반도체 min(30, 30)
    assert overlap(CARDS["B"], CARDS["C"]) == 0
    assert overlap(CARDS["A"], CARDS["A"]) == pytest.approx(100)
    assert pairwise_overlap(CARDS)[("A", "B")] == pytest.approx(20)
