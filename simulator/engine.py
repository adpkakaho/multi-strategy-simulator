"""멀티전략 DAY 시뮬레이터 계산 엔진 — Streamlit에 의존하지 않는 순수 로직."""

import random

DEFAULT_SEED = 42
INITIAL_MONEY = 100_000_000

STRATEGIES = {
    "A": {
        "삼성전자": 0.20,
        "SK하이닉스": 0.20,
        "NAVER": 0.20,
        "현대차": 0.20,
        "LG에너지솔루션": 0.20,
    },
    "B": {
        "삼성전자": 0.20,
        "KB금융": 0.20,
        "현대차": 0.20,
        "POSCO홀딩스": 0.20,
        "한화에어로스페이스": 0.20,
    },
    "C": {
        "SK하이닉스": 0.20,
        "NAVER": 0.20,
        "셀트리온": 0.20,
        "삼성바이오로직스": 0.20,
        "카카오": 0.20,
    },
}

INITIAL_BASE_PRICES = {
    "삼성전자": 70_000,
    "SK하이닉스": 200_000,
    "NAVER": 190_000,
    "현대차": 250_000,
    "LG에너지솔루션": 380_000,
    "KB금융": 82_000,
    "POSCO홀딩스": 420_000,
    "한화에어로스페이스": 320_000,
    "셀트리온": 185_000,
    "삼성바이오로직스": 820_000,
    "카카오": 48_000,
}


def r10(x: float) -> int:
    return int(round(x / 10) * 10)


def fmt_int(x: float) -> str:
    return f"{int(round(x)):,}"


def accumulate_return(prev_cum_return, daily_return):
    if prev_cum_return is None:
        return None
    return (1 + prev_cum_return) * (1 + daily_return) - 1


def make_execution_prices(base_prices: dict[str, int], rng: random.Random) -> dict[str, int]:
    return {
        stock: r10(base_price * (1 + rng.uniform(-0.005, 0.005)))
        for stock, base_price in base_prices.items()
    }


def make_changed_prices(exec_prices: dict[str, int], rng: random.Random):
    returns: dict[str, float] = {}
    changed_prices: dict[str, int] = {}
    for stock, exec_price in exec_prices.items():
        daily_ret = rng.gauss(0.005, 0.02)
        returns[stock] = daily_ret
        changed_prices[stock] = r10(exec_price * (1 + daily_ret))
    return returns, changed_prices


def build_mp(weights: dict[str, int], strategies: dict) -> dict[str, float]:
    mp: dict[str, float] = {}
    for strategy_name, strategy_weight in weights.items():
        for stock, stock_weight in strategies[strategy_name].items():
            mp[stock] = mp.get(stock, 0.0) + (strategy_weight / 100) * stock_weight
    return mp


def build_contrib(weights: dict[str, int], strategies: dict) -> dict[str, dict[str, float]]:
    contrib: dict[str, dict[str, float]] = {}
    for strategy_name in strategies:
        for stock, stock_weight in strategies[strategy_name].items():
            contrib.setdefault(stock, {})[strategy_name] = (weights[strategy_name] / 100) * stock_weight
    return contrib


def calc_strategy_theoretical_returns(stock_returns: dict[str, float], strategies: dict) -> dict[str, float]:
    result: dict[str, float] = {}
    for strategy_name, portfolio in strategies.items():
        strategy_ret = 0.0
        for stock, stock_weight in portfolio.items():
            strategy_ret += stock_weight * stock_returns[stock]
        result[strategy_name] = strategy_ret
    return result


def calc_snapshot_strategy_split(
    qty: dict[str, int],
    close_prices: dict[str, int],
    stock_pnl: dict[str, int],
    weights: dict[str, int],
    strategies: dict,
    cash_after_trade: int,
):
    contrib = build_contrib(weights, strategies)
    strategy_eval = {k: 0.0 for k in strategies}
    strategy_pnl = {k: 0.0 for k in strategies}

    for stock in qty:
        stock_eval = qty[stock] * close_prices[stock]
        stock_total_contrib = sum(contrib.get(stock, {}).values())
        if stock_total_contrib == 0:
            continue
        for strategy_name, strategy_contrib in contrib[stock].items():
            share = strategy_contrib / stock_total_contrib
            strategy_eval[strategy_name] += stock_eval * share
            strategy_pnl[strategy_name] += stock_pnl[stock] * share

    strategy_est_ret: dict[str, float] = {}
    for strategy_name in strategies:
        base_value = strategy_eval[strategy_name] - strategy_pnl[strategy_name]
        strategy_est_ret[strategy_name] = strategy_pnl[strategy_name] / base_value if base_value != 0 else 0.0

    return strategy_eval, strategy_pnl, strategy_est_ret

def run_day(
    day_name: str,
    weights: dict[str, int],
    base_prices: dict[str, int],
    starting_cash: int,
    starting_qty: dict[str, int],
    seed: int,
) -> dict:
    """하루치 시뮬레이션(주문 → 체결 → 가격변동 → 마감)을 계산한다. 같은 입력과 seed면 결과가 같다."""
    rng = random.Random(seed)
    mp = build_mp(weights, STRATEGIES)
    exec_prices = make_execution_prices(base_prices, rng)

    order_qty: dict[str, int] = {}
    order_amount: dict[str, int] = {}
    ending_qty: dict[str, int] = dict(starting_qty)
    cash_after_trade = starting_cash

    # 주문 기준금액: 체결가 기준 당일 총자산 (현금 + 보유주식 × 체결가)
    # 전일 종가가 아닌 당일 체결가 기준으로 재계산해야 현금 누적 방지
    order_base = starting_cash + sum(
        starting_qty.get(s, 0) * exec_prices[s] for s in exec_prices
    )

    REBALANCE_THRESHOLD = 0.01  # 1% 미만 갭은 리밸런싱 생략

    for stock, weight in mp.items():
        target_amount = int(order_base * weight)
        target_qty = target_amount // exec_prices[stock]
        current_qty = starting_qty.get(stock, 0)
        current_amount = current_qty * exec_prices[stock]
        # 현재 비중과 목표 비중 차이가 임계값 미만이면 주문 생략
        current_weight = current_amount / order_base if order_base > 0 else 0
        if abs(weight - current_weight) < REBALANCE_THRESHOLD:
            order_qty[stock] = 0
            order_amount[stock] = 0
            ending_qty[stock] = current_qty
            continue
        oq = target_qty - current_qty

        if oq > 0:
            # 매수: 현금 부족 시 살 수 있는 만큼만
            max_affordable_qty = cash_after_trade // exec_prices[stock]
            oq = min(oq, max_affordable_qty)
        # oq < 0이면 매도 (현금 회수), oq == 0이면 주문 없음

        oa = oq * exec_prices[stock]
        order_qty[stock] = oq
        order_amount[stock] = oa
        ending_qty[stock] = current_qty + oq
        cash_after_trade -= oa

    stock_returns, close_prices = make_changed_prices(exec_prices, rng)

    stock_pnl: dict[str, int] = {}
    ap_rows: list[dict[str, str]] = []
    ap_before = cash_after_trade
    ap_after = cash_after_trade

    for stock in ending_qty:
        before_value = ending_qty[stock] * exec_prices[stock]
        after_value = ending_qty[stock] * close_prices[stock]
        pnl = after_value - before_value
        stock_pnl[stock] = pnl
        ap_before += before_value
        ap_after += after_value
        ap_rows.append(
            {
                "종목": stock,
                "보유수량": fmt_int(ending_qty[stock]),
                "당일종가": fmt_int(close_prices[stock]),
                "평가금액": fmt_int(after_value),
            }
        )

    ap_pnl = ap_after - ap_before
    ap_ret = ap_pnl / ap_before if ap_before != 0 else 0.0

    strategy_theoretical_ret = calc_strategy_theoretical_returns(stock_returns, STRATEGIES)
    strategy_eval, strategy_pnl, strategy_est_ret = calc_snapshot_strategy_split(
        ending_qty, close_prices, stock_pnl, weights, STRATEGIES, cash_after_trade
    )

    return {
        "day_name": day_name,
        "weights": weights,
        "mp": mp,
        "exec_prices": exec_prices,
        "order_qty": order_qty,
        "order_amount": order_amount,
        "cash_after_trade": cash_after_trade,
        "stock_returns": stock_returns,
        "close_prices": close_prices,
        "stock_pnl": stock_pnl,
        "strategy_theoretical_ret": strategy_theoretical_ret,
        "ap_rows": ap_rows,
        "ap_before": ap_before,
        "ap_after": ap_after,
        "ap_pnl": ap_pnl,
        "ap_ret": ap_ret,
        "strategy_eval": strategy_eval,
        "strategy_pnl": strategy_pnl,
        "strategy_est_ret": strategy_est_ret,
        "ending_qty": ending_qty,
    }
