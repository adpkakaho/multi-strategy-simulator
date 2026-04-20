import random
import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="멀티전략 DAY 시뮬레이터", layout="wide")

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

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1200px;
        padding-top: 1rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
    }
    .section-box {
        border: 3px solid #4b5563;
        border-radius: 16px;
        padding: 16px 14px 8px 14px;
        margin-top: 12px;
        margin-bottom: 18px;
        background: #ffffff;
    }
    div[data-testid="stNumberInput"] input {
        background-color: #ecfccb !important;
        border: 2px solid #84cc16 !important;
        font-weight: 700;
        color: #1a2e05 !important;
    }
    div[data-testid="stNumberInput"] input:focus {
        background-color: #d9f99d !important;
        border: 2px solid #65a30d !important;
        box-shadow: 0 0 0 3px rgba(132,204,22,0.3) !important;
    }
    .section-title {
        font-size: 1.45rem;
        font-weight: 800;
        margin-bottom: 12px;
        color: #111827;
    }
    .subsection-title {
        font-size: 1.15rem;
        font-weight: 700;
        margin-top: 6px;
        margin-bottom: 8px;
        color: #1f2937;
    }
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        padding: 10px;
        border-radius: 14px;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.95rem;
        font-weight: 600;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 800;
    }
    button[kind="secondary"] {
        min-height: 42px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def r10(x: float) -> int:
    return int(round(x / 10) * 10)


def won(x: float) -> str:
    return f"{int(round(x)):,}원"


def fmt_int(x: float) -> str:
    return f"{int(round(x)):,}"


def fmt_float(x: float, d: int = 2) -> str:
    return f"{x:,.{d}f}"


def pct(x):
    if x is None:
        return "N/A"
    return f"{x * 100:.2f}%"


def accumulate_return(prev_cum_return, daily_return):
    if prev_cum_return is None:
        return None
    return (1 + prev_cum_return) * (1 + daily_return) - 1


def get_rng() -> random.Random:
    return random.Random(st.session_state.seed)


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

    total_weight = sum(weights.values())
    if total_weight > 0:
        for strategy_name in strategies:
            cash_share = weights[strategy_name] / total_weight
            strategy_eval[strategy_name] += cash_after_trade * cash_share

    strategy_est_ret: dict[str, float] = {}
    for strategy_name in strategies:
        base_value = strategy_eval[strategy_name] - strategy_pnl[strategy_name]
        strategy_est_ret[strategy_name] = strategy_pnl[strategy_name] / base_value if base_value != 0 else 0.0

    return strategy_eval, strategy_pnl, strategy_est_ret


def next_default_weight(strategy_name: str) -> int:
    if st.session_state.day_no == 1:
        return 0
    return int(st.session_state.last_weights.get(strategy_name, 0))


def run_day(day_name: str, weights: dict[str, int], base_prices: dict[str, int], starting_cash: int, starting_qty: dict[str, int], order_reference_value: int):
    rng = get_rng()
    mp = build_mp(weights, STRATEGIES)
    exec_prices = make_execution_prices(base_prices, rng)

    order_qty: dict[str, int] = {}
    order_amount: dict[str, int] = {}
    ending_qty: dict[str, int] = dict(starting_qty)
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


def reset_simulation():
    st.session_state.day_no = 1
    st.session_state.base_prices = dict(INITIAL_BASE_PRICES)
    st.session_state.current_cash = INITIAL_MONEY
    st.session_state.current_qty = {stock: 0 for stock in INITIAL_BASE_PRICES}
    st.session_state.order_reference_value = INITIAL_MONEY
    st.session_state.strategy_theoretical_cum = {k: 0.0 for k in STRATEGIES}
    st.session_state.strategy_est_cum = {k: None for k in STRATEGIES}
    st.session_state.strategy_tracking_active = {k: False for k in STRATEGIES}
    st.session_state.ap_cum = 0.0
    st.session_state.history = []
    st.session_state.seed = DEFAULT_SEED
    st.session_state.last_weights = {k: 0 for k in STRATEGIES}


if "history" not in st.session_state:
    reset_simulation()

st.title("멀티전략 DAY 시뮬레이터")
st.caption("전략 비중 입력 → DAY 실행 → 주문표 / 가격변동 / AP 잔고 / 전략 분해")
st.markdown(f"### 현재 기준일: DAY{st.session_state.day_no - 1}")

with st.sidebar:
    st.subheader("설정")
    st.write(f"현재 실행 예정 DAY: DAY{st.session_state.day_no}")
    if st.button("시뮬레이션 초기화", use_container_width=True):
        reset_simulation()
        st.rerun()

    st.subheader("전략 구성")
    for name, portfolio in STRATEGIES.items():
        st.write(f"Strategy {name}")
        for stock, weight in portfolio.items():
            st.caption(f"- {stock}: {int(weight * 100)}%")

st.markdown('<div class="section-box">', unsafe_allow_html=True)
st.markdown('<div class="section-title">DAY 비중 입력</div>', unsafe_allow_html=True)
input_cols = st.columns(len(STRATEGIES))
weights: dict[str, int] = {}
total = 0
for idx, name in enumerate(STRATEGIES):
    with input_cols[idx]:
        weights[name] = int(
            st.number_input(
                f"Strategy {name} (%)",
                min_value=0,
                max_value=100,
                value=next_default_weight(name),
                step=10,
                format="%d",
                key=f"weight_{name}_{st.session_state.day_no}",
            )
        )
        total += weights[name]

cash_weight = 100 - total
m1, m2, m3 = st.columns(3)
m1.metric("전략 비중 합계", f"{total:.2f}%")
m2.metric("현금 비중", f"{cash_weight:.2f}%")
m3.metric("AP 누적수익률", pct(st.session_state.ap_cum))

if total > 100:
    st.error("전략 비중 합계는 100% 이하여야 합니다.")

if st.button("DAY 실행", disabled=total > 100, use_container_width=True):
    result = run_day(
        day_name=f"DAY{st.session_state.day_no}",
        weights=weights,
        base_prices=st.session_state.base_prices,
        starting_cash=st.session_state.current_cash,
        starting_qty=st.session_state.current_qty,
        order_reference_value=st.session_state.order_reference_value,
    )

    for strategy_name in STRATEGIES:
        st.session_state.strategy_theoretical_cum[strategy_name] = accumulate_return(
            st.session_state.strategy_theoretical_cum[strategy_name],
            result["strategy_theoretical_ret"][strategy_name],
        )

        if weights[strategy_name] == 0:
            st.session_state.strategy_tracking_active[strategy_name] = False
            st.session_state.strategy_est_cum[strategy_name] = None
        else:
            if not st.session_state.strategy_tracking_active[strategy_name]:
                st.session_state.strategy_tracking_active[strategy_name] = True
                st.session_state.strategy_est_cum[strategy_name] = result["strategy_est_ret"][strategy_name]
            else:
                prev_est = st.session_state.strategy_est_cum[strategy_name]
                if prev_est is None:
                    st.session_state.strategy_est_cum[strategy_name] = result["strategy_est_ret"][strategy_name]
                else:
                    st.session_state.strategy_est_cum[strategy_name] = accumulate_return(
                        prev_est,
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
    st.session_state.last_weights = dict(weights)
    st.session_state.day_no += 1
    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="section-box">', unsafe_allow_html=True)
st.markdown('<div class="section-title">통합MP</div>', unsafe_allow_html=True)

if st.session_state.history:
    latest = st.session_state.history[-1]
    # 보유비중: 전일 종가 기준 각 종목 평가금액 / 총자산
    ap_total = latest["ap_after"]
    mp_rows = []
    for stock, target_w in latest["mp"].items():
        holding_value = latest["ending_qty"].get(stock, 0) * latest["close_prices"][stock]
        holding_w = holding_value / ap_total if ap_total else 0.0
        gap = target_w - holding_w
        mp_rows.append({"종목": stock, "목표비중": pct(target_w), "보유비중": pct(holding_w), "갭": pct(gap)})
    mp_df = pd.DataFrame(mp_rows)
    st.dataframe(mp_df, use_container_width=True, hide_index=True)
else:
    st.info("DAY 실행 후 통합MP가 표시됩니다.")

st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.history:
    latest = st.session_state.history[-1]
    st.markdown(f"### 운용 / 마감 기준일: {latest['day_name']}")

    st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">운용</div>', unsafe_allow_html=True)
    st.markdown('<div class="subsection-title">주문표</div>', unsafe_allow_html=True)
    order_df = pd.DataFrame(
        [
            {
                "종목": stock,
                "목표비중(%)": fmt_float(latest["mp"][stock] * 100, 2),
                "체결가격": fmt_int(latest["exec_prices"][stock]),
                "주문수량": fmt_int(latest["order_qty"][stock]),
                "주문금액": fmt_int(latest["order_amount"][stock]),
            }
            for stock in latest["mp"]
        ]
    )
    st.dataframe(order_df, use_container_width=True, hide_index=True)
    st.write("주문 후 현금:", won(latest["cash_after_trade"]))

    st.markdown('<div class="subsection-title">일간 종목별 가격변동</div>', unsafe_allow_html=True)
    stock_df = pd.DataFrame(
        [
            {
                "종목": stock,
                "보유수량": fmt_int(latest["ending_qty"][stock]),
                "당일종가": fmt_int(latest["close_prices"][stock]),
                "일간등락률": pct(latest["stock_returns"][stock]),
                "손익": fmt_int(latest["stock_pnl"][stock]),
            }
            for stock in latest["ending_qty"]
        ]
    )
    st.dataframe(stock_df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">마감</div>', unsafe_allow_html=True)

    st.markdown('<div class="subsection-title">전략별 MP수익률(이론값)</div>', unsafe_allow_html=True)
    theo_df = pd.DataFrame(
        [
            {
                "전략": name,
                "일간": pct(latest["strategy_theoretical_ret"][name]),
                "누적": pct(latest["strategy_theoretical_cum"][name]),
            }
            for name in STRATEGIES
        ]
    )
    st.dataframe(theo_df, use_container_width=True, hide_index=True)

    st.markdown('<div class="subsection-title">AP 잔고 리포팅</div>', unsafe_allow_html=True)
    ap_df = pd.DataFrame(latest["ap_rows"])
    st.dataframe(ap_df, use_container_width=True, hide_index=True)
    x1, x2, x3 = st.columns(3)
    x4, x5, x6 = st.columns(3)
    x1.metric("평가금액(SUM)", won(latest["ap_after"]))
    x2.metric("AP 일간 손익", won(latest["ap_pnl"]))
    x3.metric("AP 누적 손익", won(latest["ap_after"] - INITIAL_MONEY))
    x4.metric("현금", won(latest["cash_after_trade"]))
    x5.metric("AP 일간 수익률", pct(latest["ap_ret"]))
    x6.metric("AP 누적 수익률", pct(latest["ap_cum"]))

    st.markdown('<div class="subsection-title">AP 잔고 전략별 분해</div>', unsafe_allow_html=True)
    split_df = pd.DataFrame(
        [
            {
                "전략": name,
                "평가금액(현금포함)": fmt_int(latest["strategy_eval"][name]),
                "기여손익": fmt_int(latest["strategy_pnl"][name]),
                "전략별 추정 수익률": pct(latest["strategy_est_ret"][name]),
                "전략별 추정 누적 수익률": pct(latest["strategy_est_cum"][name]),
            }
            for name in STRATEGIES
        ]
    )
    st.dataframe(split_df, use_container_width=True, hide_index=True)
    st.write("전략별 평가금액 합계:", won(sum(latest["strategy_eval"].values())))
    st.write("전략별 기여손익 합계:", won(sum(latest["strategy_pnl"].values())))
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="subsection-title">DAY 히스토리</div>', unsafe_allow_html=True)
    hist_df = pd.DataFrame(
        [
            {
                "DAY": item["day_name"],
                "A 비중": fmt_float(item["weights"].get("A", 0), 2),
                "B 비중": fmt_float(item["weights"].get("B", 0), 2),
                "C 비중": fmt_float(item["weights"].get("C", 0), 2),
                "AP 일간 수익률": pct(item["ap_ret"]),
                "AP 누적 수익률": pct(item["ap_cum"]),
                "총자산": won(item["ap_after"]),
            }
            for item in st.session_state.history
        ]
    )
    st.dataframe(hist_df, use_container_width=True, hide_index=True)

    st.markdown('<div class="subsection-title">누적수익률 그래프</div>', unsafe_allow_html=True)
    chart_source = pd.DataFrame(
        [
            {
                "DAY": item["day_name"],
                "AP 누적수익률": (item["ap_cum"] or 0) * 100,
                "전략A 이론 누적수익률": (item["strategy_theoretical_cum"].get("A") or 0) * 100,
                "전략B 이론 누적수익률": (item["strategy_theoretical_cum"].get("B") or 0) * 100,
                "전략C 이론 누적수익률": (item["strategy_theoretical_cum"].get("C") or 0) * 100,
            }
            for item in st.session_state.history
        ]
    )
    chart_long = chart_source.melt("DAY", var_name="구분", value_name="누적수익률(%)")
    day_order = chart_source["DAY"].tolist()
    line_chart = (
        alt.Chart(chart_long)
        .mark_line(point=True)
        .encode(
            x=alt.X("DAY:N", title="DAY", sort=day_order),
            y=alt.Y("누적수익률(%):Q", title="누적수익률(%)"),
            color=alt.Color("구분:N", title="구분"),
            tooltip=["DAY", "구분", alt.Tooltip("누적수익률(%):Q", format=".2f")],
        )
        .properties(height=320)
    )
    st.altair_chart(line_chart, use_container_width=True)
else:
    st.info("전략별 초기 비중은 0%로 설정되어 있습니다. 비중을 입력하고 DAY 실행을 누르세요.")
