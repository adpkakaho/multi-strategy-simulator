"""2 주문·귀속 탭 — 계좌 주문(정수 수량)과 전략별 귀속수량·현금 (구축방안 4.2)."""

from html import escape

import pandas as pd
import streamlit as st

from simulator.orders import OrderResult, initial_orders, reconcile
from simulator.scenario import DOC_CAPITAL, DOC_PRICES_T0
from ui import theme
from ui.theme import pct


def won(value: int) -> str:
    return f"{value:,}"


def table(head: list[tuple[str, bool]], body: str) -> str:
    """head: (열 이름, 숫자 열 여부)"""
    ths = "".join(f'<th{" class=\'num\'" if num else ""}>{escape(name)}</th>' for name, num in head)
    return f'<div class="tbwrap"><table class="tb"><thead><tr>{ths}</tr></thead><tbody>{body}</tbody></table></div>'


def edit_prices(stocks: list[str]) -> dict[str, int]:
    """기준가 편집. 문서 예시에 없는 종목은 직접 입력해야 한다."""
    seed = pd.DataFrame({"종목": stocks, "기준가(원)": [DOC_PRICES_T0.get(s) for s in stocks]})
    edited = st.data_editor(
        seed,
        hide_index=True,
        width="stretch",
        key=f"prices_{st.session_state.mix_nonce}_{'|'.join(stocks)}",
        disabled=["종목"],
        column_config={"기준가(원)": st.column_config.NumberColumn(min_value=1, step=100, format="%d")},
    )
    return {
        stock: int(price) for stock, price in zip(edited["종목"], edited["기준가(원)"]) if pd.notna(price) and price > 0
    }


def strategy_card_html(card: dict, book, prices: dict[str, int], color: str) -> str:
    rows = "".join(
        f'<div class="row"><span>{escape(stock)} {won(qty)}주</span><span>{won(qty * prices[stock])}</span></div>'
        for stock, qty in book.qty.items()
    )
    return (
        '<div class="card">'
        f'<div class="k"><span class="sw" style="background:{color}"></span>전략 {escape(card["id"])}</div>'
        f'<div class="n">{escape(card["name"])}</div><div class="e">{escape(card["advisor"])} ㅣ 배정 {won(book.allocated)}원</div>'
        f"{rows}"
        f'<div class="row"><span>현금</span><span>{won(book.cash)}</span></div>'
        f'<div class="row sum"><span>평가금액</span><span>{won(book.stock_value + book.cash)}</span></div>'
        "</div>"
    )


def order_table(result: OrderResult) -> str:
    body = "".join(
        f'<tr><td>{escape(l.stock)}</td><td class="num">{pct(l.weight)}</td><td class="num">{won(l.target_amount)}</td>'
        f'<td class="num">{won(l.price)}</td><td class="num"><b>{won(l.qty)}주</b></td>'
        f'<td class="num">{won(l.amount)}</td><td class="num">{won(l.residual)}</td></tr>'
        for l in result.lines
    )
    total_weight = sum(l.weight for l in result.lines)
    body += (
        f'<tr class="total"><td>합계</td><td class="num">{pct(total_weight)}</td>'
        f'<td class="num">{won(sum(l.target_amount for l in result.lines))}</td><td></td><td></td>'
        f'<td class="num">{won(result.buy_amount)}</td><td class="num"><b>{won(sum(l.residual for l in result.lines))}</b></td></tr>'
    )
    return table(
        [("종목", False), ("목표비중", True), ("목표금액", True), ("기준가", True), ("주문수량", True), ("매수금액", True), ("잔여", True)],
        body,
    )


def split_table(result: OrderResult, names: dict[str, str]) -> str:
    body = ""
    for line in result.lines:
        if len(line.split) < 2:
            continue
        for i, row in enumerate(line.split):
            first = f'<td rowspan="{len(line.split)}"><b>{escape(line.stock)}</b><br><span class="muted">계좌 {won(line.qty)}주</span></td>' if i == 0 else ""
            body += (
                f"<tr>{first}<td>{escape(names[row.card_id])}</td><td class='num'>{pct(row.contribution)}</td>"
                f"<td class='num'>{row.quota:,.2f}</td><td class='num'>{won(row.base)}</td>"
                f"<td class='num'>{row.quota - row.base:.2f}</td>"
                f"<td class='num'>{'+1' if row.extra else '<span class=muted>–</span>'}</td>"
                f"<td class='num'><b>{won(row.qty)}주</b></td></tr>"
            )
    return table(
        [("종목", False), ("전략", False), ("기여도", True), ("비례수량", True), ("내림", True), ("소수부", True), ("잔여 배정", True), ("귀속수량", True)],
        body,
    )


def book_table(result: OrderResult, names: dict[str, str], prices: dict[str, int]) -> str:
    body = ""
    for card_id, book in result.books.items():
        holdings = "<br>".join(
            f"{escape(stock)} {won(qty)}주 × {won(prices[stock])} = {won(qty * prices[stock])}" for stock, qty in book.qty.items()
        )
        cash_cls = "num neg" if book.cash < 0 else "num"
        body += (
            f"<tr><td><b>{escape(names[card_id])}</b></td><td class='num'>{won(book.allocated)}</td><td class='small'>{holdings}</td>"
            f"<td class='num'>{won(book.stock_value)}</td><td class='{cash_cls}'>{won(book.cash)}</td></tr>"
        )
    if result.unallocated_cash:
        body += (
            f"<tr><td>미배정 현금</td><td class='num'>{won(result.unallocated_cash)}</td><td class='small muted'>전략비중 합계가 100% 미만인 부분</td>"
            f"<td class='num'>–</td><td class='num'>{won(result.unallocated_cash)}</td></tr>"
        )
    body += (
        f'<tr class="total"><td>계좌 합계</td><td class="num">{won(result.capital)}</td><td></td>'
        f'<td class="num">{won(result.buy_amount)}</td><td class="num">{won(result.account_cash)}</td></tr>'
    )
    return table([("전략", False), ("배정금액", True), ("보유 (수량 × 기준가)", False), ("주식 평가", True), ("현금", True)], body)


def render(show_calc: bool) -> None:
    theme.section(
        "STEP 2 ㅣ 주문 → 귀속",
        "계좌 주문은 정수 수량으로 한 번에 집행하고, 겹치는 종목은 기여도 비율로 전략에 나눠 기록합니다",
        "주문수량 = 내림(가입금액 × 합성 목표비중 ÷ 기준가). 전략별로는 수량과 현금만 귀속하며 매입단가는 계좌에만 둡니다.",
    )
    st.session_state.order_result = None
    mix = st.session_state.get("mix_result")
    if not mix:
        st.info("'1 믹스' 탭에서 전략비중과 전략카드 입력을 먼저 완료해 주세요.")
        return
    cards = {card["id"]: card for card in mix["cards"]}
    names = {cid: f"{cid} {card['name']}" for cid, card in cards.items()}
    stocks = list(mix["mp"].keys())

    theme.h3("가입금액과 기준가")
    c1, _ = st.columns([1, 2])
    capital = int(c1.number_input("가입금액(원)", min_value=1_000_000, max_value=100_000_000_000, value=DOC_CAPITAL, step=1_000_000, format="%d"))
    with st.expander("기준가 편집"):
        prices = edit_prices(stocks)
        theme.note("가정: 체결가 = 기준가, 수수료·세금 생략. 문서 예시에 없는 종목은 기준가를 직접 입력해야 합니다.")
    missing = [s for s in stocks if s not in prices]
    if missing:
        st.error("기준가가 없는 종목이 있습니다: " + ", ".join(missing) + ". '기준가 편집'에서 입력해 주세요.")
        return

    result = initial_orders(capital, mix["weights"], mix["contrib"], prices)
    st.session_state.order_result = {"result": result, "prices": prices}  # 다음 단계(일별 평가)의 입력
    checks = reconcile(result)

    # ── 고객에게 보이는 것 ──
    theme.h3("내 랩 잔고 ㅣ 가입 직후")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("가입금액", f"{won(capital)}원")
    m2.metric("주식 매수금액", f"{won(result.buy_amount)}원")
    m3.metric("현금", f"{won(result.account_cash)}원")
    m4.metric("현금 비중", pct(result.account_cash / capital * 100))
    for col, (card_id, book) in zip(st.columns(len(result.books)), result.books.items()):
        with col:
            theme.html(strategy_card_html(cards[card_id], book, prices, theme.SERIES_COLORS[list(cards).index(card_id) % theme.MAX_CARDS]))
    theme.note("전략별 평가금액은 귀속수량 × 기준가 + 귀속현금입니다. 전략별 거래내역과 매입단가는 제공하지 않습니다.")

    negative = [names[cid] for cid, book in result.books.items() if book.cash < 0]
    if negative:
        st.warning(
            "귀속현금이 음수인 전략이 있습니다: " + ", ".join(negative)
            + ". 겹치는 종목의 남는 1주를 받은 전략이 배정금액보다 조금 더 산 경우입니다. 계좌 현금은 부족하지 않습니다."
        )

    if not show_calc:
        return

    # ── 계산 과정 ──
    theme.h3("계산 과정 ① 계좌 주문")
    theme.html(order_table(result))
    theme.note("주문은 종목당 한 번, 계좌 단위로 나갑니다. 잔여는 정수 수량으로 내림하면서 남는 금액입니다.")

    if any(len(line.split) > 1 for line in result.lines):
        theme.h3("계산 과정 ② 겹치는 종목의 수량 나누기 (최대잔여법)")
        theme.html(split_table(result, names))
        theme.note("비례수량 = 계좌 주문수량 × 기여도 ÷ 기여도 합. 먼저 내림하고, 남는 주식은 소수부가 큰 전략부터 1주씩 줍니다. 소수부가 같으면 앞 순서 전략이 받습니다.")

    theme.h3("계산 과정 ③ 전략별 귀속 결과")
    theme.html(book_table(result, names, prices))
    theme.note("전략별 현금 = 배정금액 − 귀속수량 × 기준가. 한 전략에만 있는 종목은 그 전략이 전량 보유합니다.")

    mark = lambda ok: "✓" if ok else "✗"  # noqa: E731
    cash_sum = sum(book.cash for book in result.books.values()) + result.unallocated_cash
    theme.html(
        '<div class="box"><div class="t">일일 대사 (두 항등식)</div>'
        f"① 종목마다 Σ 전략별 귀속수량 = 계좌 수량 {mark(checks['qty'])}<br>"
        f"② Σ 전략별 현금{' + 미배정 현금' if result.unallocated_cash else ''} {won(cash_sum)}원 = 계좌 현금 {won(result.account_cash)}원 {mark(checks['cash'])}"
        "</div>"
    )

    theme.h3("허용 오차 ㅣ 정수 수량 때문에 생기는 현금")
    rounding_cash = result.account_cash - result.unallocated_cash
    body = "".join(
        f"<tr><td>{escape(names[cid])}</td><td class='num'>{won(book.allocated)}</td>"
        f"<td class='{'num neg' if book.cash < 0 else 'num'}'>{won(book.cash)}</td>"
        f"<td class='num'>{pct(book.cash / book.allocated * 100)}</td></tr>"
        for cid, book in result.books.items()
    )
    invested = capital - result.unallocated_cash
    body += (
        f'<tr class="total"><td>합계</td><td class="num">{won(invested)}</td><td class="num">{won(rounding_cash)}</td>'
        f'<td class="num">{pct(rounding_cash / invested * 100)}</td></tr>'
    )
    theme.html(table([("전략", False), ("배정금액", True), ("라운딩 잔여현금", True), ("배정금액 대비", True)], body))
    theme.note("종목당 1주 미만의 금액이 현금으로 남습니다. 가입금액이 작거나 고가주가 많을수록 비율이 커집니다. 가입금액을 바꿔 보면 확인할 수 있습니다.")
