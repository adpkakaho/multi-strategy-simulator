"""STEP 2 주문·귀속 — 구축방안 4.2 표의 숫자를 그대로 재현하는지 확인한다."""

import random

from simulator.mix import contributions
from simulator.orders import initial_orders, largest_remainder, reconcile
from simulator.scenario import DOC_CAPITAL, DOC_CARDS, DOC_PRICES_T0, DOC_STRATEGY_WEIGHTS

CARDS = {card["id"]: card["holdings"] for card in DOC_CARDS}


def doc_result():
    return initial_orders(DOC_CAPITAL, DOC_STRATEGY_WEIGHTS, contributions(DOC_STRATEGY_WEIGHTS, CARDS), DOC_PRICES_T0)


def test_doc_4_2_account_orders():
    r = doc_result()
    assert r.account_qty == {
        "삼성전자": 271, "한미반도체": 152, "SK하이닉스": 55, "KB금융": 123,
        "현대차": 40, "KT&G": 84, "네이버": 39, "카카오": 115,
    }
    by_stock = {line.stock: line for line in r.lines}
    assert (by_stock["삼성전자"].target_amount, by_stock["삼성전자"].amount, by_stock["삼성전자"].residual) == (22_000_000, 21_951_000, 49_000)
    assert by_stock["현대차"].residual == 160_000
    assert r.buy_amount == 99_466_000
    assert r.account_cash == 534_000


def test_doc_4_2_shared_stock_split():
    by_stock = {line.stock: line for line in doc_result().lines}
    assert {row.card_id: row.qty for row in by_stock["삼성전자"].split} == {"A": 172, "B": 99}
    assert {row.card_id: row.qty for row in by_stock["한미반도체"].split} == {"A": 101, "C": 51}


def test_doc_4_2_strategy_books():
    books = doc_result().books
    assert books["A"].qty == {"삼성전자": 172, "한미반도체": 101, "SK하이닉스": 55}
    assert books["B"].qty == {"삼성전자": 99, "KB금융": 123, "현대차": 40, "KT&G": 84}
    assert books["C"].qty == {"한미반도체": 51, "네이버": 39, "카카오": 115}
    assert [(b.allocated, b.stock_value, b.cash) for b in books.values()] == [
        (40_000_000, 39_765_000, 235_000),
        (40_000_000, 39_786_000, 214_000),
        (20_000_000, 19_915_000, 85_000),
    ]


def test_doc_4_2_reconciles():
    r = doc_result()
    assert reconcile(r) == {"qty": True, "cash": True}
    assert r.unallocated_cash == 0


def test_largest_remainder_basics():
    rows = largest_remainder(271, {"A": 14, "B": 8})
    assert [(r.base, r.extra) for r in rows] == [(172, 0), (98, 1)]  # 172.45 / 98.55 → 남는 1주는 B
    assert [r.qty for r in largest_remainder(10, {"A": 1, "B": 1, "C": 1})] == [4, 3, 3]  # 동률이면 카드 순서
    assert [r.qty for r in largest_remainder(0, {"A": 3, "B": 1})] == [0, 0]
    assert [r.qty for r in largest_remainder(7, {"A": 5})] == [7]


def test_partial_weights_leave_unallocated_cash():
    weights = {"A": 50, "B": 30, "C": 0}
    r = initial_orders(DOC_CAPITAL, weights, contributions(weights, CARDS), DOC_PRICES_T0)
    assert set(r.books) == {"A", "B"}
    assert r.unallocated_cash == 20_000_000
    assert reconcile(r) == {"qty": True, "cash": True}


def test_reconciles_for_random_inputs():
    rng = random.Random(7)
    for _ in range(200):
        weights = dict(zip("ABC", rng.choice([(40, 40, 20), (33, 33, 34), (70, 20, 10), (5, 5, 90), (25, 25, 25)])))
        prices = {stock: rng.randrange(1_000, 900_000, 100) for stock in DOC_PRICES_T0}
        capital = rng.randrange(3_000_000, 500_000_000, 10_000)
        r = initial_orders(capital, weights, contributions(weights, CARDS), prices)
        assert reconcile(r) == {"qty": True, "cash": True}
        assert r.account_cash >= 0
        assert all(q >= 0 for book in r.books.values() for q in book.qty.values())
