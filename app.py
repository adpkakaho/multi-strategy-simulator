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
        max-width: 960px;
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    .sec { border: 1px solid #d1d5db; border-radius: 12px; padding: 16px 18px 14px 18px; margin-bottom: 14px; background: #f9fafb; }
    .sec.blue  { border-color: #85B7EB; background: #E6F1FB; }
    .sec.green { border-color: #97C459; background: #EAF3DE; }
    .sec-title { font-size: 1.1rem; font-weight: 700; margin-bottom: 10px; color: #111827; }
    .sub-title { font-size: 0.78rem; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; margin: 14px 0 6px 0; }
    div[data-testid="stNumberInput"] input { background-color: #ecfccb !important; border: 1.5px solid #84cc16 !important; font-weight: 700; color: #1a2e05 !important; font-size: 1.15rem !important; }
    div[data-testid="stNumberInput"] input:focus { background-color: #d9f99d !important; border-color: #65a30d !important; box-shadow: 0 0 0 3px rgba(132,204,22,0.25) !important; }
    div[data-testid="stMetric"] { background: #ffffff; border: 0.5px solid #e5e7eb; padding: 10px 14px; border-radius: 10px; }
    div[data-testid="stMetricLabel"] p { font-size: 0.78rem !important; color: #6b7280; }
    div[data-testid="stMetricValue"] { font-size: 1.25rem !important; font-weight: 600; }
    .note { font-size: 0.82rem; color: #6b7280; margin-top: 4px; }
    .note.info { color: #1d4ed8; }
    </style>
    """,
    unsafe_allow_html=True,
)


def r10(x: float) -> int:
    return int(round(x / 10) * 10)


def won(x: float) -> str:
    return f"{int(round(x)):,}원"


def df_height(df: pd.DataFrame) -> int:
    """행 수에 맞게 height 계산 (헤더 35px + 행당 35px)"""
    return 35 + len(df) * 35 + 3


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

    strategy_est_ret: dict[str, float] = {}
    for strategy_name in strategies:
        base_value = strategy_eval[strategy_name] - strategy_pnl[strategy_name]
        strategy_est_ret[strategy_name] = strategy_pnl[strategy_name] / base_value if base_value != 0 else 0.0

    return strategy_eval, strategy_pnl, strategy_est_ret


def color_pct_col(val: str) -> str:
    """수익률/손익 문자열에 +/- 색상 적용 (Styler용)"""
    try:
        v = float(val.replace("%", "").replace(",", "").replace("원", "").strip())
        if v > 0:
            return "color: #166534; font-weight: 600"
        elif v < 0:
            return "color: #991b1b; font-weight: 600"
    except Exception:
        pass
    return ""


def style_df(df: pd.DataFrame, cols: list) -> object:
    try:
        return df.style.map(color_pct_col, subset=cols)
    except AttributeError:
        return df.style.applymap(color_pct_col, subset=cols)


def sec_header(title: str, color: str = "gray") -> None:
    palette = {
        "blue":  ("background:#dbeafe; border-left:4px solid #2563eb;", "color:#1e3a8a"),
        "green": ("background:#dcfce7; border-left:4px solid #16a34a;", "color:#14532d"),
        "gray":  ("background:#f3f4f6; border-left:4px solid #6b7280;", "color:#1f2937"),
    }
    bg, tc = palette.get(color, palette["gray"])
    st.markdown(
        f'<div style="{bg} padding:10px 16px; border-radius:8px; margin-bottom:12px;">'
        f'<span style="{tc}; font-size:1.05rem; font-weight:700;">{title}</span></div>',
        unsafe_allow_html=True,
    )


def sub_header(title: str) -> None:
    st.markdown(
        f'<div style="font-size:0.75rem; font-weight:600; color:#6b7280;'
        f' text-transform:uppercase; letter-spacing:0.05em; margin:14px 0 6px;">{title}</div>',
        unsafe_allow_html=True,
    )


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

    # 주문 기준금액: 체결가 기준 당일 총자산 (현금 + 보유주식 × 체결가)
    # 전일 종가가 아닌 당일 체결가 기준으로 재계산해야 현금 누적 방지
    order_base = starting_cash + sum(
        starting_qty.get(s, 0) * exec_prices[s] for s in exec_prices
    )

    for stock, weight in mp.items():
        target_amount = int(order_base * weight)
        target_qty = target_amount // exec_prices[stock]
        current_qty = starting_qty.get(stock, 0)
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
    # DAY0 스냅샷: 초기 현금 1억, 전 종목 0주
    st.session_state.day0_snapshot = {
        "ending_qty": {stock: 0 for stock in INITIAL_BASE_PRICES},
        "close_prices": dict(INITIAL_BASE_PRICES),
        "ap_after": INITIAL_MONEY,
    }


if "history" not in st.session_state:
    reset_simulation()

# ── 사이드바 ──
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

# ── 페이지 타이틀 ──
st.title("멀티전략 DAY 시뮬레이터")
st.caption("전략 비중 입력 → DAY 실행 → 주문표 / 가격변동 / AP 잔고 / 전략 분해")
st.markdown(f"**현재 기준일: DAY{st.session_state.day_no - 1}**")


def execute_one_day(weights: dict[str, int]):
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
                        prev_est, result["strategy_est_ret"][strategy_name],
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


# ══════════════════════════════════════════
# [1] DAY 비중 입력
# ══════════════════════════════════════════
sec_header("DAY 비중 입력", "blue")

input_cols = st.columns(len(STRATEGIES))
weights: dict[str, int] = {}
total = 0
for idx, name in enumerate(STRATEGIES):
    with input_cols[idx]:
        _default = next_default_weight(name)
        _val = st.number_input(
            f"Strategy {name} (%)",
            min_value=0, max_value=100,
            value=None if _default == 0 else _default,
            placeholder="0", step=10, format="%d",
            key=f"weight_{name}_{st.session_state.day_no}",
        )
        weights[name] = int(_val) if _val is not None else 0
        total += weights[name]

cash_weight = 100 - total
m1, m2, m3 = st.columns(3)
m1.metric("전략 비중 합계", f"{total:.2f}%")
m2.metric("현금 비중", f"{cash_weight:.2f}%")
m3.metric("AP 누적수익률", pct(st.session_state.ap_cum))

if total > 100:
    st.error("전략 비중 합계는 100% 이하여야 합니다.")

btn_col1, btn_col2 = st.columns([2, 1])
with btn_col1:
    if st.button("DAY 실행", disabled=total > 100, use_container_width=True):
        execute_one_day(weights)
        st.rerun()
with btn_col2:
    if st.button("3일 연속 실행", disabled=total > 100, use_container_width=True):
        for _ in range(3):
            execute_one_day(weights)
        st.rerun()

st.divider()

# ══════════════════════════════════════════
# [2] 통합MP + 히스토리 + 누적수익률 차트
# ══════════════════════════════════════════
sec_header("통합MP", "green")

day_no = st.session_state.day_no
prev_day_label = f"DAY{day_no - 2}"
prev_snap = st.session_state.day0_snapshot if day_no <= 2 else st.session_state.history[day_no - 3]
prev_total = prev_snap["ap_after"]

if st.session_state.history:
    latest = st.session_state.history[-1]
    mp_rows = []
    for stock, target_w in latest["mp"].items():
        holding_value = prev_snap["ending_qty"].get(stock, 0) * prev_snap["close_prices"][stock]
        holding_w = holding_value / prev_total if prev_total else 0.0
        gap = target_w - holding_w
        mp_rows.append({
            "종목": stock,
            "목표비중": pct(target_w),
            f"보유비중({prev_day_label})": pct(holding_w),
            "갭": pct(gap),
        })
    mp_df = pd.DataFrame(mp_rows)
    st.dataframe(
        style_df(mp_df, ["갭"]),
        use_container_width=True, hide_index=True, height=df_height(mp_df),
    )
else:
    all_stocks = list(dict.fromkeys(s for strat in STRATEGIES.values() for s in strat))
    mp_rows = [{"종목": s, "목표비중": "미확정", f"보유비중({prev_day_label})": "0.00%", "갭": "-"} for s in all_stocks]
    st.dataframe(pd.DataFrame(mp_rows), use_container_width=True, hide_index=True,
                 height=df_height(pd.DataFrame(mp_rows)))
    st.caption("비중 입력 후 DAY 실행 시 목표비중이 확정됩니다.")

if st.session_state.history:
    sub_header("DAY 히스토리")
    hist_df = pd.DataFrame([
        {
            "DAY": item["day_name"],
            "A 비중": fmt_float(item["weights"].get("A", 0), 0),
            "B 비중": fmt_float(item["weights"].get("B", 0), 0),
            "C 비중": fmt_float(item["weights"].get("C", 0), 0),
            "AP 일간": pct(item["ap_ret"]),
            "AP 누적": pct(item["ap_cum"]),
            "총자산": won(item["ap_after"]),
        }
        for item in st.session_state.history
    ])
    st.dataframe(
        style_df(hist_df, ["AP 일간", "AP 누적"]),
        use_container_width=True, hide_index=True, height=df_height(hist_df),
    )

    sub_header("누적수익률 그래프")
    chart_src = pd.DataFrame([
        {
            "DAY": item["day_name"],
            "AP 누적수익률": (item["ap_cum"] or 0) * 100,
            "전략A 이론": (item["strategy_theoretical_cum"].get("A") or 0) * 100,
            "전략B 이론": (item["strategy_theoretical_cum"].get("B") or 0) * 100,
            "전략C 이론": (item["strategy_theoretical_cum"].get("C") or 0) * 100,
        }
        for item in st.session_state.history
    ])
    day_order = chart_src["DAY"].tolist()
    chart_long = chart_src.melt("DAY", var_name="구분", value_name="누적수익률(%)")
    line_chart = (
        alt.Chart(chart_long)
        .mark_line(point=True)
        .encode(
            x=alt.X("DAY:N", title="DAY", sort=day_order),
            y=alt.Y("누적수익률(%):Q", title="누적수익률(%)"),
            color=alt.Color("구분:N", title="구분"),
            strokeDash=alt.condition(
                alt.datum["구분"] == "AP 누적수익률",
                alt.value([1, 0]),
                alt.value([4, 3]),
            ),
            tooltip=["DAY", "구분", alt.Tooltip("누적수익률(%):Q", format=".2f")],
        )
        .properties(height=260)
    )
    st.altair_chart(line_chart, use_container_width=True)

st.divider()

# ══════════════════════════════════════════
# [3] 운용 / 마감
# ══════════════════════════════════════════
if st.session_state.history:
    latest = st.session_state.history[-1]
    st.markdown(f"**운용 / 마감 기준일: {latest['day_name']}**")

    # ── 운용 ──
    sec_header("운용", "gray")

    sub_header("주문표")
    order_df = pd.DataFrame([
        {
            "종목": stock,
            "목표비중(%)": fmt_float(latest["mp"][stock] * 100, 2),
            "체결가격": fmt_int(latest["exec_prices"][stock]),
            "주문수량": fmt_int(latest["order_qty"][stock]),
            "주문금액": fmt_int(latest["order_amount"][stock]),
        }
        for stock in latest["mp"]
    ])
    st.dataframe(order_df, use_container_width=True, hide_index=True, height=df_height(order_df))
    st.caption(f"주문 후 현금: {won(latest['cash_after_trade'])}")

    sub_header("일간 종목별 가격변동")
    stock_rows = [
        {
            "종목": stock,
            "보유수량": fmt_int(latest["ending_qty"][stock]),
            "당일종가": fmt_int(latest["close_prices"][stock]),
            "일간등락률": pct(latest["stock_returns"][stock]),
            "손익": fmt_int(latest["stock_pnl"][stock]),
        }
        for stock in latest["ending_qty"]
    ]
    stock_df = pd.DataFrame(stock_rows)
    st.dataframe(
        style_df(stock_df, ["일간등락률", "손익"]),
        use_container_width=True, hide_index=True, height=df_height(stock_df),
    )

    st.divider()

    # ── 마감 ──
    sec_header("마감", "gray")

    sub_header("전략별 MP 수익률 (이론값)")
    theo_rows = [
        {
            "전략": name,
            "일간": pct(latest["strategy_theoretical_ret"][name]),
            "누적": pct(latest["strategy_theoretical_cum"][name]),
        }
        for name in STRATEGIES
    ]
    theo_df = pd.DataFrame(theo_rows)
    st.dataframe(
        style_df(theo_df, ["일간", "누적"]),
        use_container_width=True, hide_index=True, height=df_height(theo_df),
    )

    sub_header("AP 잔고 리포팅")
    ap_df = pd.DataFrame(latest["ap_rows"])
    st.dataframe(ap_df, use_container_width=True, hide_index=True, height=df_height(ap_df))

    ap_pnl_val = latest["ap_pnl"]
    ap_cum_pnl = latest["ap_after"] - INITIAL_MONEY
    ap_ret_val = latest["ap_ret"]
    ap_cum_val = latest["ap_cum"]
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)
    c1.metric("평가금액(SUM)", won(latest["ap_after"]))
    c2.metric("AP 일간 손익", won(ap_pnl_val), delta=won(ap_pnl_val))
    c3.metric("AP 누적 손익", won(ap_cum_pnl), delta=won(ap_cum_pnl))
    c4.metric("현금", won(latest["cash_after_trade"]))
    c5.metric("AP 일간 수익률", pct(ap_ret_val), delta=f"{ap_ret_val*100:.2f}%")
    c6.metric("AP 누적 수익률", pct(ap_cum_val), delta=f"{ap_cum_val*100:.2f}%")

    sub_header("AP 잔고 전략별 분해")
    split_rows = [
        {
            "전략": name,
            "주식 평가금액": fmt_int(latest["strategy_eval"][name]),
            "기여손익": fmt_int(latest["strategy_pnl"][name]),
            "추정 수익률": pct(latest["strategy_est_ret"][name]),
            "추정 누적 수익률": pct(latest["strategy_est_cum"][name]),
        }
        for name in STRATEGIES
    ]
    split_df = pd.DataFrame(split_rows)
    st.dataframe(
        style_df(split_df, ["기여손익", "추정 수익률", "추정 누적 수익률"]),
        use_container_width=True, hide_index=True, height=df_height(split_df),
    )
    stock_eval_sum = sum(latest["strategy_eval"].values())
    st.caption(f"전략별 주식 평가금액 합계: {won(stock_eval_sum)}　|　현금 (별도): {won(latest['cash_after_trade'])}")
    st.caption(f"전략 주식합계 + 현금 = {won(stock_eval_sum + latest['cash_after_trade'])}　/　AP 잔고: {won(latest['ap_after'])}")
    st.caption(f"전략별 기여손익 합계: {won(sum(latest['strategy_pnl'].values()))}")

    sub_header("전략별 AP 잔고 구성비 (영역형)")
    strategy_names = list(STRATEGIES.keys())
    area_rows = []
    day_order2 = [item["day_name"] for item in st.session_state.history]
    for item in st.session_state.history:
        ap_total = item["ap_after"]
        for sname in strategy_names:
            ratio = (item["strategy_eval"].get(sname, 0) / ap_total * 100) if ap_total else 0
            area_rows.append({"DAY": item["day_name"], "구성": f"전략{sname}", "비율(%)": ratio})
        cash_ratio = (item["cash_after_trade"] / ap_total * 100) if ap_total else 0
        area_rows.append({"DAY": item["day_name"], "구성": "현금", "비율(%)": cash_ratio})

    stack_order = [f"전략{n}" for n in strategy_names] + ["현금"]
    area_src = pd.DataFrame(area_rows)
    area_chart = (
        alt.Chart(area_src)
        .mark_area(opacity=0.78)
        .encode(
            x=alt.X("DAY:N", title="DAY", sort=day_order2),
            y=alt.Y("비율(%):Q", title="구성비율(%)", stack="normalize",
                    axis=alt.Axis(format=".0%")),
            color=alt.Color("구성:N", title="구성", sort=stack_order,
                            scale=alt.Scale(scheme="tableau10")),
            order=alt.Order("구성:N", sort="ascending"),
            tooltip=["DAY", "구성", alt.Tooltip("비율(%):Q", format=".2f")],
        )
        .properties(height=240, title="전략별 AP 잔고 구성비 (주식 기준, 현금 별도)")
    )
    st.altair_chart(area_chart, use_container_width=True)

else:
    st.info("전략별 초기 비중은 0%로 설정되어 있습니다. 비중을 입력하고 DAY 실행을 누르세요.")
