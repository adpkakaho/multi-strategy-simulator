"""계산 엔진 단위 테스트 — Streamlit 없이 실행된다."""

import pytest

from simulator.engine import (
    INITIAL_BASE_PRICES,
    INITIAL_MONEY,
    STRATEGIES,
    accumulate_return,
    build_contrib,
    build_mp,
    run_day,
)

ZERO_QTY = {stock: 0 for stock in INITIAL_BASE_PRICES}


def first_day(weights, seed=42):
    return run_day("DAY1", weights, dict(INITIAL_BASE_PRICES), INITIAL_MONEY, dict(ZERO_QTY), seed)


def test_strategy_weights_sum_to_one():
    for portfolio in STRATEGIES.values():
        assert sum(portfolio.values()) == pytest.approx(1.0)


def test_build_mp_sums_to_total_strategy_weight():
    weights = {"A": 40, "B": 30, "C": 20}
    mp = build_mp(weights, STRATEGIES)
    assert sum(mp.values()) == pytest.approx(0.90)
    # 삼성전자는 A, B 두 전략에 20%씩 들어 있다
    assert mp["삼성전자"] == pytest.approx(0.4 * 0.2 + 0.3 * 0.2)


def test_build_contrib_matches_mp():
    weights = {"A": 40, "B": 30, "C": 20}
    mp = build_mp(weights, STRATEGIES)
    contrib = build_contrib(weights, STRATEGIES)
    for stock, target in mp.items():
        assert sum(contrib[stock].values()) == pytest.approx(target)


def test_same_seed_is_deterministic():
    weights = {"A": 40, "B": 30, "C": 20}
    assert first_day(weights) == first_day(weights)
    assert first_day(weights, seed=1)["close_prices"] != first_day(weights, seed=2)["close_prices"]


def test_cash_and_holdings_reconcile():
    r = first_day({"A": 40, "B": 30, "C": 20})
    assert r["cash_after_trade"] >= 0
    # 현금 = 시작 현금 - 주문금액 합계
    assert r["cash_after_trade"] == INITIAL_MONEY - sum(r["order_amount"].values())
    # 마감 총자산 = 현금 + 보유수량 × 종가
    holdings = sum(r["ending_qty"][s] * r["close_prices"][s] for s in r["ending_qty"])
    assert r["ap_after"] == r["cash_after_trade"] + holdings
    assert r["ap_pnl"] == sum(r["stock_pnl"].values())
    assert r["ap_ret"] == pytest.approx(r["ap_pnl"] / r["ap_before"])


def test_strategy_split_adds_up_to_portfolio():
    r = first_day({"A": 40, "B": 30, "C": 20})
    holdings = sum(r["ending_qty"][s] * r["close_prices"][s] for s in r["ending_qty"])
    assert sum(r["strategy_eval"].values()) == pytest.approx(holdings)
    assert sum(r["strategy_pnl"].values()) == pytest.approx(r["ap_pnl"])


def test_zero_weights_stay_in_cash():
    r = first_day({"A": 0, "B": 0, "C": 0})
    assert all(q == 0 for q in r["ending_qty"].values())
    assert r["cash_after_trade"] == INITIAL_MONEY
    assert r["ap_after"] == INITIAL_MONEY
    assert r["ap_ret"] == 0.0
    assert all(v == 0 for v in r["strategy_eval"].values())


def test_prices_are_rounded_to_ten_won():
    r = first_day({"A": 40, "B": 30, "C": 20})
    assert all(p % 10 == 0 for p in r["exec_prices"].values())
    assert all(p % 10 == 0 for p in r["close_prices"].values())


def test_multi_day_never_overdraws_cash():
    cash, qty, prices = INITIAL_MONEY, dict(ZERO_QTY), dict(INITIAL_BASE_PRICES)
    plans = [{"A": 40, "B": 30, "C": 30}, {"A": 0, "B": 100, "C": 0}, {"A": 30, "B": 30, "C": 40}, {"A": 0, "B": 0, "C": 0}]
    for day, weights in enumerate(plans * 5, start=1):
        r = run_day(f"DAY{day}", weights, prices, cash, qty, seed=day)
        assert r["cash_after_trade"] >= 0
        assert all(q >= 0 for q in r["ending_qty"].values())
        cash, qty, prices = r["cash_after_trade"], r["ending_qty"], r["close_prices"]


def test_accumulate_return():
    assert accumulate_return(0.10, 0.10) == pytest.approx(0.21)
    assert accumulate_return(None, 0.10) is None
