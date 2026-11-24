"""STEP 1 믹스 — 전략카드(MP)들을 전략비중으로 섞어 합성 MP를 만든다.

모든 비중은 퍼센트(%) 단위다. 예: 전략비중 40, 전략내 종목비중 35 → 기여도 14.
"""

from itertools import combinations

Holdings = dict[str, float]  # 종목 → 전략내 비중(%)


def contributions(
    strategy_weights: dict[str, float], cards: dict[str, Holdings]
) -> dict[str, dict[str, float]]:
    """기여도[종목][전략] = 전략비중 × 전략내 종목비중. 전략비중이 0인 전략은 제외한다."""
    result: dict[str, dict[str, float]] = {}
    for card_id, holdings in cards.items():
        strategy_weight = strategy_weights.get(card_id, 0)
        if strategy_weight <= 0:
            continue
        for stock, stock_weight in holdings.items():
            if stock_weight <= 0:
                continue
            result.setdefault(stock, {})[card_id] = strategy_weight * stock_weight / 100
    return result


def blend(contrib: dict[str, dict[str, float]]) -> dict[str, float]:
    """합성 목표비중[종목] = Σ 기여도. 비중이 큰 종목부터 정렬한다."""
    totals = {stock: sum(by_card.values()) for stock, by_card in contrib.items()}
    return dict(sorted(totals.items(), key=lambda item: -item[1]))


def shared_stocks(contrib: dict[str, dict[str, float]]) -> list[str]:
    """둘 이상의 전략에 들어 있는 종목."""
    return [stock for stock, by_card in contrib.items() if len(by_card) > 1]


def overlap(a: Holdings, b: Holdings) -> float:
    """두 MP의 중복률(%) = Σ min(전략내 비중). 0이면 겹치는 종목 없음, 100이면 동일한 MP."""
    return sum(min(a[stock], b[stock]) for stock in a.keys() & b.keys())


def pairwise_overlap(cards: dict[str, Holdings]) -> dict[tuple[str, str], float]:
    return {(x, y): overlap(cards[x], cards[y]) for x, y in combinations(cards, 2)}
