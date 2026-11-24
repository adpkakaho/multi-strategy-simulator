"""STEP 2 주문·귀속 — 합성 MP를 계좌 주문(정수 수량)으로 바꾸고, 수량과 현금을 전략별로 귀속한다.

구축방안 4.2. 계좌가 유일한 원장이다. 전략별로는 수량과 현금만 기록하고 매입단가는 두지 않는다.
비중은 퍼센트(%), 금액은 원, 수량은 주 단위다.
"""

from dataclasses import dataclass, field
from fractions import Fraction
from math import floor


def _frac(value: float) -> Fraction:
    return Fraction(value).limit_denominator(1_000_000)


@dataclass
class SplitRow:
    """최대잔여법의 중간 과정 한 줄(종목 × 전략)."""

    card_id: str
    contribution: float  # 기여도(%)
    quota: float  # 비례수량(소수 포함)
    base: int  # 내림한 수량
    extra: int  # 잔여 배정(0 또는 1)

    @property
    def qty(self) -> int:
        return self.base + self.extra


def largest_remainder(total_qty: int, contrib_by_card: dict[str, float]) -> list[SplitRow]:
    """수량을 기여도 비율로 나눈다. 내림한 뒤 남는 주식은 소수부가 큰 전략부터 1주씩 준다.

    소수부가 같으면 앞에 있는 전략(카드 순서)이 먼저 받는다.
    """
    total_contrib = sum(_frac(c) for c in contrib_by_card.values())
    quotas = {cid: total_qty * _frac(c) / total_contrib for cid, c in contrib_by_card.items()}
    bases = {cid: floor(q) for cid, q in quotas.items()}
    leftover = total_qty - sum(bases.values())
    by_remainder = sorted(quotas, key=lambda cid: -(quotas[cid] - bases[cid]))  # 안정 정렬 → 동률이면 카드 순서
    winners = set(by_remainder[:leftover])
    return [
        SplitRow(cid, contrib_by_card[cid], float(quotas[cid]), bases[cid], 1 if cid in winners else 0)
        for cid in contrib_by_card
    ]


@dataclass
class OrderLine:
    """계좌 주문 한 줄."""

    stock: str
    weight: float  # 합성 목표비중(%)
    target_amount: int
    price: int
    qty: int
    split: list[SplitRow] = field(default_factory=list)

    @property
    def amount(self) -> int:
        return self.qty * self.price

    @property
    def residual(self) -> int:
        return self.target_amount - self.amount


@dataclass
class StrategyBook:
    """전략 하나의 귀속 결과."""

    card_id: str
    allocated: int  # 배정금액 = 가입금액 × 전략비중
    qty: dict[str, int]  # 종목 → 귀속수량
    stock_value: int
    cash: int  # 귀속현금 = 배정금액 − 귀속수량 × 기준가


@dataclass
class OrderResult:
    capital: int
    lines: list[OrderLine]
    books: dict[str, StrategyBook]
    unallocated_cash: int  # 전략비중 합계가 100% 미만일 때 어느 전략에도 속하지 않는 현금

    @property
    def buy_amount(self) -> int:
        return sum(line.amount for line in self.lines)

    @property
    def account_cash(self) -> int:
        return self.capital - self.buy_amount

    @property
    def account_qty(self) -> dict[str, int]:
        return {line.stock: line.qty for line in self.lines}


def initial_orders(
    capital: int,
    strategy_weights: dict[str, float],
    contrib: dict[str, dict[str, float]],
    prices: dict[str, int],
) -> OrderResult:
    """가입 시점의 계좌 주문과 전략별 귀속.

    목표금액 = 가입금액 × 합성 목표비중, 주문수량 = 내림(목표금액 ÷ 기준가).
    겹치는 종목의 수량은 기여도 비율로 최대잔여법 배분한다.
    """
    lines: list[OrderLine] = []
    for stock, by_card in contrib.items():
        weight = sum(_frac(c) for c in by_card.values())
        target = capital * weight / 100
        qty = floor(target / prices[stock])
        lines.append(OrderLine(stock, float(weight), round(target), prices[stock], qty, largest_remainder(qty, by_card)))
    lines.sort(key=lambda line: -line.weight)

    books: dict[str, StrategyBook] = {}
    for card_id, strategy_weight in strategy_weights.items():
        if strategy_weight <= 0:
            continue
        qty = {
            line.stock: row.qty for line in lines for row in line.split if row.card_id == card_id and row.qty > 0
        }
        allocated = round(capital * _frac(strategy_weight) / 100)
        stock_value = sum(q * prices[stock] for stock, q in qty.items())
        books[card_id] = StrategyBook(card_id, allocated, qty, stock_value, allocated - stock_value)

    unallocated = capital - sum(book.allocated for book in books.values())
    return OrderResult(capital, lines, books, unallocated)


def reconcile(result: OrderResult) -> dict[str, bool]:
    """일일 대사 두 항목: Σ 귀속수량 = 계좌수량, Σ 전략 현금(+미배정) = 계좌 현금."""
    qty_ok = all(
        sum(book.qty.get(line.stock, 0) for book in result.books.values()) == line.qty for line in result.lines
    )
    cash_ok = sum(book.cash for book in result.books.values()) + result.unallocated_cash == result.account_cash
    return {"qty": qty_ok, "cash": cash_ok}
