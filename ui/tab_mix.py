"""1 믹스 탭 — 전략카드 선택·전략비중 지정 → 합성 MP (구축방안 4.1)."""

from html import escape

import altair as alt
import pandas as pd
import streamlit as st

from simulator.mix import blend, contributions, pairwise_overlap, shared_stocks
from simulator.scenario import DOC_CARDS, DOC_STRATEGY_WEIGHTS
from ui import theme
from ui.theme import pct


def init_state() -> None:
    if "cards" not in st.session_state:
        reset_to_doc_example()


def reset_to_doc_example() -> None:
    st.session_state.cards = [
        {"id": c["id"], "name": c["name"], "advisor": c["advisor"], "holdings": dict(c["holdings"])}
        for c in DOC_CARDS
    ]
    # nonce를 바꾸면 입력 위젯이 새로 만들어져 기본값으로 돌아간다
    st.session_state.mix_nonce = st.session_state.get("mix_nonce", 0) + 1


def add_card() -> None:
    cards = st.session_state.cards
    used = {card["id"] for card in cards}
    new_id = next(ch for ch in "ABCDEFGHIJ" if ch not in used)
    cards.append({"id": new_id, "name": "새 전략", "advisor": "자문사", "holdings": {}})


def color_of(card_id: str) -> str:
    ids = [card["id"] for card in st.session_state.cards]
    return theme.SERIES_COLORS[ids.index(card_id) % len(theme.SERIES_COLORS)]


def edit_cards() -> None:
    """전략카드(MP) 편집 — 편집 결과를 session_state.cards에 반영한다."""
    nonce = st.session_state.mix_nonce
    cards = st.session_state.cards
    for tab, card in zip(st.tabs([f"{card['id']} {card['name']}" for card in cards]), cards):
        with tab:
            c1, c2 = st.columns(2)
            card["name"] = c1.text_input("전략카드 이름", card["name"], key=f"name_{card['id']}_{nonce}")
            card["advisor"] = c2.text_input("자문사", card["advisor"], key=f"adv_{card['id']}_{nonce}")
            # 편집기에는 처음 값만 넘긴다(매번 바뀐 값을 넘기면 편집 상태가 초기화된다)
            seed = st.session_state.setdefault(f"seed_{card['id']}_{nonce}", dict(card["holdings"]))
            edited = st.data_editor(
                pd.DataFrame({"종목": list(seed.keys()), "비중(%)": [float(v) for v in seed.values()]}),
                num_rows="dynamic",
                hide_index=True,
                width="stretch",
                key=f"mp_{card['id']}_{nonce}",
                column_config={
                    "종목": st.column_config.TextColumn(required=True),
                    "비중(%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=1.0, format="%.1f"),
                },
            )
            holdings: dict[str, float] = {}
            for stock, weight in zip(edited["종목"], edited["비중(%)"]):
                if isinstance(stock, str) and stock.strip() and pd.notna(weight) and weight > 0:
                    holdings[stock.strip()] = holdings.get(stock.strip(), 0.0) + float(weight)
            card["holdings"] = holdings
    b1, b2, _ = st.columns([1, 1, 2])
    if b1.button("전략카드 추가", disabled=len(cards) >= theme.MAX_CARDS, width="stretch"):
        add_card()
        st.rerun()
    if b2.button("문서 예시로 되돌리기", width="stretch"):
        reset_to_doc_example()
        st.rerun()
    theme.note(f"전략카드는 최대 {theme.MAX_CARDS}개까지 둘 수 있습니다. 종목 비중 합계는 100%여야 합니다.")


def card_html(card: dict, weight: float) -> str:
    rows = "".join(
        f'<div class="row"><span>{escape(stock)}</span><span>{pct(w)}</span></div>'
        for stock, w in card["holdings"].items()
    ) or '<div class="row"><span>종목 없음</span><span></span></div>'
    return (
        f'<div class="card{"" if weight > 0 else " off"}">'
        f'<div class="k"><span class="sw" style="background:{color_of(card["id"])}"></span>전략카드 {escape(card["id"])}</div>'
        f'<div class="n">{escape(card["name"])}</div><div class="e">{escape(card["advisor"])}</div>{rows}</div>'
    )


def chart(contrib: dict, mp: dict, cards: list[dict]) -> alt.LayerChart:
    label = {card["id"]: f"{card['id']} {card['name']}" for card in cards}
    order = list(mp.keys())
    rows = []
    for stock in order:
        start = 0.0
        for card in cards:
            value = contrib[stock].get(card["id"], 0)
            if value > 0:
                rows.append({"종목": stock, "전략": label[card["id"]], "기호": card["id"], "x0": start, "x1": start + value,
                             "mid": start + value / 2, "기여도": value, "합성비중": mp[stock]})
                start += value
    data = pd.DataFrame(rows)
    active = [card for card in cards if any(card["id"] in contrib[s] for s in contrib)]
    y = alt.Y("종목:N", sort=order, title=None,
              axis=alt.Axis(labelFontSize=13, labelColor=theme.INK, ticks=False, domain=False, labelPadding=8))
    bars = (
        alt.Chart(data)
        .mark_bar(height=20, stroke="#ffffff", strokeWidth=2, cornerRadius=3)
        .encode(
            y=y,
            x=alt.X("x0:Q", title="합성 목표비중(%)",
                    axis=alt.Axis(grid=True, gridColor=theme.GRAY_100, tickMinStep=5, tickCount=6, domain=False, ticks=False,
                                  labelColor=theme.GRAY_400, titleColor=theme.GRAY_500, titleFontWeight="normal")),
            x2="x1:Q",
            color=alt.Color(
                "전략:N",
                scale=alt.Scale(domain=[label[c["id"]] for c in active], range=[color_of(c["id"]) for c in active]),
                legend=alt.Legend(orient="top", title=None, labelFontSize=12.5, labelColor=theme.INK, symbolType="square"),
            ),
            tooltip=[alt.Tooltip("종목:N"), alt.Tooltip("전략:N"), alt.Tooltip("기여도:Q", format=".2f", title="기여도(%)"),
                     alt.Tooltip("합성비중:Q", format=".2f", title="합성 목표비중(%)")],
        )
    )
    # 조각이 충분히 넓을 때만 전략 기호를 넣는다
    inside = (
        alt.Chart(data[data["기여도"] >= max(mp.values()) * 0.06])
        .mark_text(fontSize=11.5, fontWeight=700, color="#ffffff")
        .encode(y=alt.Y("종목:N", sort=order), x=alt.X("mid:Q"), text="기호:N")
    )
    totals = (
        alt.Chart(pd.DataFrame({"종목": order, "합성비중": [mp[s] for s in order], "표시": [pct(mp[s]) for s in order]}))
        .mark_text(align="left", dx=6, fontSize=12.5, fontWeight=600, color=theme.INK)
        .encode(y=alt.Y("종목:N", sort=order), x=alt.X("합성비중:Q"), text="표시:N")
    )
    return (bars + inside + totals).properties(height=max(120, 34 * len(order) + 40)).configure_view(stroke=None)


def formula_table(contrib: dict, mp: dict, cards: list[dict], weights: dict) -> str:
    active = [card for card in cards if weights[card["id"]] > 0]
    head = "".join(
        f'<th class="num">{escape(c["id"])} {escape(c["name"])} ({pct(weights[c["id"]])})</th>' for c in active
    )
    body = ""
    for stock, total in mp.items():
        cells = ""
        for c in active:
            value = contrib[stock].get(c["id"])
            cells += (
                f'<td class="num">{pct(weights[c["id"]])}×{pct(c["holdings"][stock])} = <b>{pct(value)}</b></td>'
                if value else '<td class="num muted">–</td>'
            )
        body += f'<tr><td>{escape(stock)}</td>{cells}<td class="num"><b>{pct(total)}</b></td></tr>'
    foot = "".join(f'<td class="num">{pct(weights[c["id"]])}</td>' for c in active)
    return (
        '<div class="tbwrap"><table class="tb"><thead><tr><th>종목</th>' + head + '<th class="num">합성 목표비중</th></tr></thead>'
        f'<tbody>{body}<tr class="total"><td>합계</td>{foot}<td class="num"><b>{pct(sum(mp.values()))}</b></td></tr></tbody></table></div>'
    )


def render(show_calc: bool) -> None:
    init_state()
    cards = st.session_state.cards
    nonce = st.session_state.mix_nonce
    st.session_state.mix_result = None  # 입력이 유효할 때만 아래에서 채운다

    theme.section(
        "STEP 1 ㅣ MP 등록 → 믹스",
        "전략카드를 고르고 비중을 정하면, 종목 단위의 합성 MP 하나로 합쳐집니다",
        "합성 목표비중 = Σ 전략비중 × 전략내 종목비중. 여러 전략에 겹치는 종목은 합산됩니다.",
    )

    theme.h3("전략카드와 전략비중")
    weights: dict[str, float] = {}
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            weights[card["id"]] = float(st.number_input(
                f"{card['id']} 전략비중(%)", min_value=0, max_value=100, step=5,
                value=int(DOC_STRATEGY_WEIGHTS.get(card["id"], 0)), key=f"sw_{card['id']}_{nonce}",
            ))
    with st.expander("전략카드(MP) 편집"):
        edit_cards()
    card_slots = st.columns(len(cards))
    for col, card in zip(card_slots, cards):
        with col:
            theme.html(card_html(card, weights[card["id"]]))

    # ── 입력 검증 ──
    total_weight = sum(weights.values())
    bad_cards = [c for c in cards if weights[c["id"]] > 0 and abs(sum(c["holdings"].values()) - 100) > 1e-6]
    if total_weight > 100:
        st.error(f"전략비중 합계가 {pct(total_weight)}입니다. 100% 이하로 맞춰주세요.")
        return
    if bad_cards:
        for c in bad_cards:
            st.error(f"전략카드 {c['id']} {c['name']}의 종목 비중 합계가 {pct(sum(c['holdings'].values()))}입니다. 100%로 맞춰주세요.")
        return
    if total_weight == 0:
        st.info("전략비중을 입력하면 합성 MP가 계산됩니다.")
        return
    if total_weight < 100:
        st.warning(f"전략비중 합계가 {pct(total_weight)}입니다. 남는 {pct(100 - total_weight)}는 현금으로 둡니다.")

    card_holdings = {c["id"]: c["holdings"] for c in cards}
    contrib = contributions(weights, card_holdings)
    mp = blend(contrib)
    shared = shared_stocks(contrib)
    st.session_state.mix_result = {
        "weights": weights, "contrib": contrib, "mp": mp,
        "cards": [{"id": c["id"], "name": c["name"], "advisor": c["advisor"]} for c in cards],
    }  # 다음 단계(주문·귀속)의 입력

    # ── 고객에게 보이는 것 ──
    theme.h3("합성 MP ㅣ 고객에게 보이는 조합 결과")
    top_stock = next(iter(mp))
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("선택한 전략", f"{sum(1 for w in weights.values() if w > 0)}개")
    m2.metric("합성 종목 수", f"{len(mp)}개")
    m3.metric("겹치는 종목", f"{len(shared)}개")
    m4.metric("최대 종목 비중", pct(mp[top_stock]), help=f"{top_stock}")
    st.altair_chart(chart(contrib, mp, cards), width="stretch")
    if shared:
        theme.note("겹치는 종목: " + ", ".join(
            f"{s} {pct(mp[s])} (" + " + ".join(f"{cid} {pct(v)}" for cid, v in contrib[s].items()) + ")" for s in shared
        ))

    if not show_calc:
        return

    # ── 계산 과정 ──
    theme.h3("계산 과정 ㅣ 전략비중 × 전략내 종목비중")
    theme.html(formula_table(contrib, mp, cards, weights))
    ok = abs(sum(mp.values()) - total_weight) < 1e-6
    theme.html(
        '<div class="box"><div class="t">검증</div>'
        f"합성 목표비중 합계 {pct(sum(mp.values()))} = 전략비중 합계 {pct(total_weight)} {'✓' if ok else '✗'}"
        + (f" ㅣ 현금 {pct(100 - total_weight)}" if total_weight < 100 else "")
        + "<br>각 칸의 기여도 비율이 다음 단계에서 겹치는 종목의 수량을 전략별로 나누는 비율이 됩니다."
        + ("" if not shared else " 예: " + escape(shared[0]) + " → "
           + " : ".join(f"{cid} {pct(v)}" for cid, v in contrib[shared[0]].items()))
        + "</div>"
    )

    active = {cid: h for cid, h in card_holdings.items() if weights[cid] > 0}
    if len(active) >= 2:
        theme.h3("전략 간 중복률")
        names = {c["id"]: f"{c['id']} {c['name']}" for c in cards}
        rows = "".join(
            f'<tr><td>{escape(names[x])} ↔ {escape(names[y])}</td><td class="num"><b>{pct(v)}</b></td>'
            f"<td>{escape(', '.join(sorted(active[x].keys() & active[y].keys())) or '겹치는 종목 없음')}</td></tr>"
            for (x, y), v in pairwise_overlap(active).items()
        )
        theme.html(
            '<div class="tbwrap"><table class="tb"><thead><tr><th>전략 쌍</th><th class="num">중복률</th><th>겹치는 종목</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div>"
        )
        theme.note("중복률 = 두 MP에서 같은 종목의 전략내 비중 중 작은 값의 합. 0%면 겹치는 종목이 없고 100%면 같은 MP입니다. 중복률이 높을수록 전략을 나눠 담는 분산 효과가 작습니다.")
