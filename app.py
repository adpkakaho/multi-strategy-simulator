import random
import streamlit as st
import pandas as pd
import altair as alt

from simulator.engine import (
    DEFAULT_SEED,
    INITIAL_BASE_PRICES,
    INITIAL_MONEY,
    STRATEGIES,
    accumulate_return,
    build_contrib,
    fmt_int,
    run_day,
)

st.set_page_config(page_title="멀티전략 DAY 시뮬레이터", layout="wide")

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


def won(x: float) -> str:
    return f"{int(round(x)):,}원"


def df_height(df: pd.DataFrame) -> int:
    """행 수에 맞게 height 계산 (헤더 35px + 행당 35px)"""
    return 35 + len(df) * 35 + 3


def fmt_float(x: float, d: int = 2) -> str:
    return f"{x:,.{d}f}"


def pct(x):
    if x is None:
        return "N/A"
    return f"{x * 100:.2f}%"


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
    st.session_state.preset_weights = None  # 동일비중/랜덤 프리셋
    st.session_state.day0_snapshot = {
        "ending_qty": {stock: 0 for stock in INITIAL_BASE_PRICES},
        "close_prices": dict(INITIAL_BASE_PRICES),
        "ap_after": INITIAL_MONEY,
    }


if "history" not in st.session_state:
    reset_simulation()
if "preset_weights" not in st.session_state:
    st.session_state.preset_weights = None

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
        seed=st.session_state.seed,
    )
    st.session_state.seed += 1
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

# 동일비중 / 랜덤 버튼
pb1, pb2, pb3 = st.columns([1, 1, 2])
with pb1:
    if st.button("동일비중 (33/33/33)", use_container_width=True):
        st.session_state.preset_weights = {"A": 33, "B": 33, "C": 33}
        st.rerun()
with pb2:
    if st.button("랜덤 배분", use_container_width=True):
        _rng = random.Random()
        _names = list(STRATEGIES.keys())
        _w: dict[str, int] = {}
        _remaining = 100
        for i, _n in enumerate(_names):
            if i == len(_names) - 1:
                _w[_n] = _remaining
            else:
                _lo = max(10, _remaining - 50 * (len(_names) - i - 1))
                _hi = min(50, _remaining - 10 * (len(_names) - i - 1))
                _lo = min(_lo, _hi)
                _pick = _rng.randrange(_lo, _hi + 1, 10) if _lo <= _hi else _lo
                _w[_n] = _pick
                _remaining -= _pick
        st.session_state.preset_weights = _w
        st.rerun()

# 프리셋 적용
_preset = st.session_state.get("preset_weights") or {}

input_cols = st.columns(len(STRATEGIES))
weights: dict[str, int] = {}
total = 0
for idx, name in enumerate(STRATEGIES):
    with input_cols[idx]:
        _default = _preset.get(name, next_default_weight(name))
        _val = st.number_input(
            f"Strategy {name} (%)",
            min_value=0, max_value=100,
            value=int(_default) if _default else None,
            placeholder="0", step=10, format="%d",
            key=f"weight_{name}_{st.session_state.day_no}_{_preset.get(name, '')}",
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
        st.session_state.preset_weights = None
        execute_one_day(weights)
        st.rerun()
with btn_col2:
    if st.button("3일 연속 실행", disabled=total > 100, use_container_width=True):
        st.session_state.preset_weights = None
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
    c2.metric("AP 일간 손익", won(ap_pnl_val))
    c3.metric("AP 누적 손익", won(ap_cum_pnl))
    c4.metric("현금", won(latest["cash_after_trade"]))
    c5.metric("AP 일간 수익률", pct(ap_ret_val))
    c6.metric("AP 누적 수익률", pct(ap_cum_val))

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

    # ── 전략별 수익기여도 막대차트 ──
    sub_header("전략별 수익기여도 (일간 기여손익)")
    contrib_rows = []
    for item in st.session_state.history:
        for sname in strategy_names:
            contrib_rows.append({
                "DAY": item["day_name"],
                "전략": f"전략{sname}",
                "기여손익(원)": item["strategy_pnl"].get(sname, 0),
            })
    contrib_src = pd.DataFrame(contrib_rows)
    contrib_chart = (
        alt.Chart(contrib_src)
        .mark_bar()
        .encode(
            x=alt.X("DAY:N", title="DAY", sort=day_order2),
            y=alt.Y("기여손익(원):Q", title="기여손익(원)", stack=True),
            color=alt.Color("전략:N", title="전략",
                            scale=alt.Scale(scheme="tableau10")),
            tooltip=["DAY", "전략", alt.Tooltip("기여손익(원):Q", format=",.0f")],
        )
        .properties(height=220, title="전략별 일간 기여손익 (누적 스택 막대)")
    )
    zero_line = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
        color="gray", strokeWidth=0.8, strokeDash=[3, 3]
    ).encode(y="y:Q")
    st.altair_chart(contrib_chart + zero_line, use_container_width=True)

    # ── 전략별 손익 인식 ──
    st.divider()
    sec_header("전략별 손익 인식", "gray")
    st.caption(f"최신 DAY({latest['day_name']}) 기준 — 종목별 손익이 각 전략에 귀속되는 비율과 금액을 분해합니다.")

    # contrib_map: {종목: {전략: 기여비중}} — run_day와 동일한 build_contrib 사용
    contrib_map = build_contrib(latest["weights"], STRATEGIES)

    # attrib_data: 숫자값 보존 (문자열 변환 없이)
    attrib_data: list[dict] = []
    for stock in latest["ending_qty"]:
        stock_pnl_val = latest["stock_pnl"].get(stock, 0)   # run_day의 stock_pnl과 동일
        total_c = sum(contrib_map.get(stock, {}).values())
        for sname in strategy_names:
            c = contrib_map.get(stock, {}).get(sname, 0)
            share = c / total_c if total_c > 0 else 0
            if share == 0:
                continue
            attrib_data.append({
                "전략": f"전략{sname}",
                "종목": stock,
                "_mp_share": share,              # 숫자 원본 보존
                "_stock_pnl": stock_pnl_val,     # 숫자 원본 보존
                "_attrib_pnl": stock_pnl_val * share,  # 숫자 원본 보존
            })

    # 표시용 DataFrame — 컬럼 순서: 종목/전략/MP점유율/종목손익/전략인식손익
    attrib_display = pd.DataFrame([
        {
            "종목": d["종목"],
            "전략": d["전략"],
            "MP점유율": f"{d['_mp_share']*100:.1f}%",
            "종목손익": fmt_int(d["_stock_pnl"]),
            "전략인식손익": fmt_int(d["_attrib_pnl"]),
        }
        for d in attrib_data
    ])
    if attrib_data:
        st.dataframe(
            style_df(attrib_display, ["전략인식손익", "종목손익"]),
            use_container_width=True, hide_index=True,
            height=df_height(attrib_display),   # 스크롤 없이 전체 표시
        )
    else:
        st.caption("전략 비중이 모두 0%라 전략에 귀속되는 손익이 없습니다.")

    # ── 전략별 손익 인식률 ──
    sub_header("전략별 손익 인식률")

    # DAY t-1 잔고: latest 바로 이전 히스토리 or INITIAL_MONEY
    hist = st.session_state.history
    prev_ap = hist[-2]["ap_after"] if len(hist) >= 2 else INITIAL_MONEY

    sum_rows = []
    for sname in strategy_names:
        # 인식손익 합계 — attrib_data 숫자값 직접 합산 (문자열 파싱 없음)
        recog_pnl = sum(d["_attrib_pnl"] for d in attrib_data if d["전략"] == f"전략{sname}")
        # DAY t 잔고: strategy_eval[sname] (주식 평가금액, 현금 미포함)
        day_t = latest["strategy_eval"].get(sname, 0)
        # DAY t-1 잔고: 전 DAY의 strategy_eval, 없으면 초기 비중 비례
        if len(hist) >= 2:
            day_t1 = hist[-2]["strategy_eval"].get(sname, 0)
        else:
            day_t1 = INITIAL_MONEY * (latest["weights"].get(sname, 0) / 100)
        # 추정수익률 = 인식손익 / (DAY t 잔고 - 인식손익)  → strategy_est_ret와 동일 산식
        base = day_t - recog_pnl
        est_ret = recog_pnl / base if base != 0 else 0.0
        sum_rows.append({
            "전략": f"전략{sname}",
            "인식손익 합계": fmt_int(recog_pnl),
            f"DAY t-1 잔고": fmt_int(day_t1),
            f"DAY t 잔고": fmt_int(day_t),
            "추정수익률": pct(est_ret),
        })

    sum_df = pd.DataFrame(sum_rows)
    st.dataframe(
        style_df(sum_df, ["인식손익 합계", "추정수익률"]),
        use_container_width=True, hide_index=True, height=df_height(sum_df),
    )

else:
    st.info("전략별 초기 비중은 0%로 설정되어 있습니다. 비중을 입력하고 DAY 실행을 누르세요.")
