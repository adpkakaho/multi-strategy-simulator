import random
import streamlit as st
import pandas as pd

st.set_page_config(page_title="멀티전략 DAY 시뮬레이터", layout="wide")

# -----------------------------
# 설정
# -----------------------------
DEFAULT_SEED = 42
INITIAL_MONEY = 100_000_000

STRATEGIES = {
    "A": {"삼성전자": 0.5, "SK하이닉스": 0.5},
    "B": {"삼성전자": 0.5, "현대차": 0.5},
    "C": {"SK하이닉스": 0.5, "현대차": 0.5},
}

INITIAL_BASE_PRICES = {
    "삼성전자": 70000,
    "SK하이닉스": 200000,
    "현대차": 250000,
}


# -----------------------------
# 유틸
# -----------------------------
def r10(x: float) -> int:
    return int(round(x / 10) * 10)


def won(x: float) -> str:
    return f"{int(round(x)):,}원"


def pct(x):
    if x is None:
        return "N/A"
    return f"{x * 100:.2f}%"


def accumulate_return(prev_cum_return, daily_return):
    if prev_cum_return is None:
        return None
    return (1 + prev_cum_return) * (1 + daily_return) - 1


def get_rng():
    return random.Random(st.session_state.seed)


def make_execution_prices(base_prices, rng):
    return {
        stock: r10(base_price * (1 + rng.uniform(-0.005, 0.005)))
        for stock, base_price in base_prices.items()
    }


def make_changed_prices(exec_prices, rng):
    returns = {}
    changed_prices = {}
    for stock, exec_price in exec_prices.items():
        daily_ret = rng.gauss(0.005, 0.02)
        returns[stock] = daily_ret
        changed_prices[stock] = r10(exec_price * (1 + daily_ret))
    return returns, changed_prices


def build_mp(weights, strategies):
    mp = {}
    for strategy_name, strategy_weight in weights.items():
        for stock, stock_weight in strategies[strategy_name].items():
            mp[stock] = mp.get(stock, 0) + (strategy_weight / 100) * stock_weight
    return mp


def build_contrib(weights, strategies):
    contrib = {}
    for strategy_name in strategies:
        for stock, stock_weight in strategies[strategy_name].items():
            contrib.setdefault(stock, {})[strategy_name] = (weights[strategy_name] / 100) * stock_weight
    return contrib


def calc_strategy_theoretical_returns(stock_returns, strategies):
    result = {}
    for strategy_name, portfolio in strategies.items():
        strategy_ret = 0
        for stock, stock_weight in portfolio.items():
            strategy_ret += stock_weight * stock_returns[stock]
        result[strategy_name] = strategy_ret
    return result


def calc_snapshot_strategy_split(qty, close_prices, stock_pnl, weights, strategies, cash_after_trade):
    contrib = build_contrib(weights, strategies)
    strategy_eval = {k: 0.0 for k in strategies}
    strategy_pnl = {k: 0.0 for k in strategies}

    for stock in qty:
        total = sum(contrib[stock].values())
        stock_eval = qty[stock] * close_prices[stock]
        for strategy_name in contrib[stock]:
            share = contrib[stock][strategy_name] / total if total != 0 else 0
            strategy_eval[strategy_name] += stock_eval * share
            strategy_pnl[strategy_name] += stock_pnl[stock] * share

    total_weight = sum(weights.values())
    if total_weight > 0:
        for strategy_name in strategies:
            cash_share = weights[strategy_name] / total_weight
            strategy_eval[strategy_name] += cash_after_trade * cash_share

    strategy_est_ret = {}
    for strategy_name in strategies:
        base_value = strategy_eval[strategy_name] - strategy_pnl[strategy_name]
        strategy_est_ret[strategy_name] = strategy_pnl[strategy_name] / base_value if base_value != 0 else 0

    return strategy_eval, strategy_pnl, strategy_est_ret


def run_day(day_name, weights, base_prices, starting_cash, starting_qty, order_reference_value):
    rng = get_rng()
    mp = build_mp(weights, STRATEGIES)
    exec_prices = make_execution_prices(base_prices, rng)

    order_qty = {}
    order_amount = {}
    ending_qty = {}
    cash_after_trade = starting_cash

    for stock, weight in mp.items():
        target_amount = int(order_reference_value * weight)
        target_qty = target_amount // exec_prices[stock]
        current_qty = starting_qty.get(stock, 0)
        oq = target_qty - current_qty

        if oq > 0:
            max_affordable_qty = cash_after_trade // exec_prices[stock]
            oq = min(oq, max_affordable_qty)

        oa = oq * exec_prices[stock]
        order_qty[stock] = oq
        order_amount[stock] = oa
        ending_qty[stock] = current_qty + oq
        cash_after_trade -= oa

    stock_returns, close_prices = make_changed_prices(exec_prices, rng)

    stock_pnl = {}
    ap_rows = []
    ap_before = cash_after_trade
    ap_after = cash_after_trade

    for stock in ending_qty:
        before_value = ending_qty[stock] * exec_prices[stock]
        after_value = ending_qty[stock] * close_prices[stock]
        pnl = after_value - before_value

        stock_pnl[stock] = pnl
        ap_before += before_value
        ap_after += after_value
        ap_rows.append({
            "종목": stock,
            "수량": ending_qty[stock],
            "변동후가격": close_prices[stock],
            "평가금액": after_value,
        })

    ap_pnl = ap_after - ap_before
    ap_ret = ap_pnl / ap_before if ap_before != 0 else 0

    strategy_theoretical_ret = calc_strategy_theoretical_returns(stock_returns, STRATEGIES)
    strategy_eval, strategy_pnl, strategy_est_ret = calc_snapshot_strategy_split(
        ending_qty, close_prices, stock_pnl, weights, STRATEGIES, cash_after_trade
    )

    st.session_state.seed += 1

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


# -----------------------------
# 상태 초기화
# -----------------------------
def reset_simulation():
    st.session_state.day_no = 1
    st.session_state.base_prices = dict(INITIAL_BASE_PRICES)
    st.session_state.current_cash = INITIAL_MONEY
    st.session_state.current_qty = {stock: 0 for stock in INITIAL_BASE_PRICES}
    st.session_state.order_reference_value = INITIAL_MONEY
    st.session_state.strategy_theoretical_cum = {k: 0.0 for k in STRATEGIES}
    st.session_state.strategy_est_cum = {k: 0.0 for k in STRATEGIES}
    st.session_state.strategy_tracking_active = {k: True for k in STRATEGIES}
    st.session_state.ap_cum = 0.0
    st.session_state.history = []
    st.session_state.seed = DEFAULT_SEED


if "history" not in st.session_state:
    reset_simulation()


# -----------------------------
# UI
# -----------------------------
st.title("멀티전략 DAY 시뮬레이터")
st.caption("전략 비중 입력 → DAY 실행 → 주문표/가격변동/AP 잔고/전략 분해 리포트")

with st.sidebar:
    st.subheader("설정")
    st.write(f"현재 DAY: {st.session_state.day_no}")
    if st.button("시뮬레이션 초기화", use_container_width=True):
        reset_simulation()
        st.rerun()

    st.subheader("전략 구성")
    for name, portfolio in STRATEGIES.items():
        st.write(f"Strategy {name}: {portfolio}")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader(f"DAY{st.session_state.day_no} 비중 입력")
    weights = {}
    total = 0.0
    for name in STRATEGIES:
        weights[name] = st.number_input(
            f"Strategy {name} 비중 (%)",
            min_value=0.0,
            max_value=100.0,
            value=0.0 if not st.session_state.strategy_tracking_active[name] else (100.0 / len(STRATEGIES)),
            step=5.0,
            key=f"weight_{name}_{st.session_state.day_no}",
        )
        total += weights[name]

    cash_weight = 100.0 - total
    st.metric("전략 비중 합계", f"{total:.2f}%")
    st.metric("현금 비중", f"{cash_weight:.2f}%")

    can_run = total <= 100.0
    if not can_run:
        st.error("전략 비중 합계는 100% 이하여야 합니다.")

    if st.button("DAY 실행", disabled=not can_run, use_container_width=True):
        result = run_day(
            day_name=f"DAY{st.session_state.day_no}",
            weights=weights,
            base_prices=st.session_state.base_prices,
            starting_cash=st.session_state.current_cash,
            starting_qty=st.session_state.current_qty,
            order_reference_value=st.session_state.order_reference_value,
        )

        for strategy_name in STRATEGIES:
            if st.session_state.strategy_tracking_active[strategy_name] and weights[strategy_name] == 0:
                st.session_state.strategy_tracking_active[strategy_name] = False
                st.session_state.strategy_theoretical_cum[strategy_name] = None
                st.session_state.strategy_est_cum[strategy_name] = None
                continue

            if st.session_state.strategy_tracking_active[strategy_name]:
                st.session_state.strategy_theoretical_cum[strategy_name] = accumulate_return(
                    st.session_state.strategy_theoretical_cum[strategy_name],
                    result["strategy_theoretical_ret"][strategy_name],
                )
                st.session_state.strategy_est_cum[strategy_name] = accumulate_return(
                    st.session_state.strategy_est_cum[strategy_name],
                    result["strategy_est_ret"][strategy_name],
                )

        st.session_state.ap_cum = accumulate_return(st.session_state.ap_cum, result["ap_ret"])

        result["strategy_theoretical_cum"] = dict(st.session_state.strategy_theoretical_cum)
        result["strategy_est_cum"] = dict(st.session_state.strategy_est_cum)
        result["ap_cum"] = st.session_state.ap_cum
        st.session_state.history.append(result)

        st.session_state.current_cash = result["cash_after_trade"]
        st.session_state.current_qty = result["ending_qty"]
        st.session_state.base_prices = result["close_prices"]
        st.session_state.order_reference_value = result["ap_after"]
        st.session_state.day_no += 1
        st.rerun()

with col2:
    st.subheader("현재 상태")
    m1, m2, m3 = st.columns(3)
    m1.metric("현금", won(st.session_state.current_cash))
    m2.metric("기준 총자산", won(st.session_state.order_reference_value))
    m3.metric("AP 누적수익률", pct(st.session_state.ap_cum))

    qty_df = pd.DataFrame([
        {"종목": k, "수량": v, "기준가격": st.session_state.base_prices[k]}
        for k, v in st.session_state.current_qty.items()
    ])
    st.dataframe(qty_df, use_container_width=True)


# -----------------------------
# 결과 리포트
# -----------------------------
if st.session_state.history:
    latest = st.session_state.history[-1]

    st.divider()
    st.header(f"{latest['day_name']} 리포트")

    a, b, c = st.columns(3)
    a.metric("AP 일간 손익", won(latest["ap_pnl"]))
    b.metric("AP 일간 수익률", pct(latest["ap_ret"]))
    c.metric("AP 누적수익률", pct(latest["ap_cum"]))

    st.subheader("통합 MP")
    mp_df = pd.DataFrame([
        {"종목": k, "목표비중": pct(v)} for k, v in latest["mp"].items()
    ])
    st.dataframe(mp_df, use_container_width=True)

    left, right = st.columns(2)

    with left:
        st.subheader("주문표")
        order_df = pd.DataFrame([
            {
                "종목": stock,
                "목표비중(%)": round(latest["mp"][stock] * 100, 2),
                "체결가격": latest["exec_prices"][stock],
                "주문수량": latest["order_qty"][stock],
                "주문금액": latest["order_amount"][stock],
            }
            for stock in latest["mp"]
        ])
        st.dataframe(order_df, use_container_width=True)
        st.write("주문 후 현금:", won(latest["cash_after_trade"]))

    with right:
        st.subheader("일간 종목별 가격변동")
        stock_df = pd.DataFrame([
            {
                "종목": stock,
                "체결가격": latest["exec_prices"][stock],
                "변동후가격": latest["close_prices"][stock],
                "일간등락률": pct(latest["stock_returns"][stock]),
                "손익": latest["stock_pnl"][stock],
            }
            for stock in latest["ending_qty"]
        ])
        st.dataframe(stock_df, use_container_width=True)

    st.subheader("전략의 일간 변동 리포팅 (이론값)")
    theo_df = pd.DataFrame([
        {
            "전략": name,
            "일간": pct(latest["strategy_theoretical_ret"][name]),
            "누적": pct(latest["strategy_theoretical_cum"][name]),
        }
        for name in STRATEGIES
    ])
    st.dataframe(theo_df, use_container_width=True)

    st.subheader("AP 잔고 리포팅")
    ap_df = pd.DataFrame(latest["ap_rows"])
    st.dataframe(ap_df, use_container_width=True)
    x, y, z = st.columns(3)
    x.metric("현금", won(latest["cash_after_trade"]))
    y.metric("SUM", won(latest["ap_after"]))
    z.metric("AP 일간 손익", won(latest["ap_pnl"]))

    st.subheader("AP 잔고 전략별 분해 리포팅")
    split_df = pd.DataFrame([
        {
            "전략": name,
            "평가금액(현금포함)": round(latest["strategy_eval"][name]),
            "기여손익": round(latest["strategy_pnl"][name]),
            "전략별 추정 수익률": pct(latest["strategy_est_ret"][name]),
            "전략별 추정 누적 수익률": pct(latest["strategy_est_cum"][name]),
        }
        for name in STRATEGIES
    ])
    st.dataframe(split_df, use_container_width=True)
    st.write("전략별 평가금액 합계:", won(sum(latest["strategy_eval"].values())))
    st.write("전략별 기여손익 합계:", won(sum(latest["strategy_pnl"].values())))

    st.subheader("DAY 히스토리")
    hist_df = pd.DataFrame([
        {
            "DAY": item["day_name"],
            "AP 일간 수익률": pct(item["ap_ret"]),
            "AP 누적 수익률": pct(item["ap_cum"]),
            "총자산": won(item["ap_after"]),
        }
        for item in st.session_state.history
    ])
    st.dataframe(hist_df, use_container_width=True)
else:
    st.info("좌측에서 전략 비중을 입력하고 DAY 실행을 누르세요.")
