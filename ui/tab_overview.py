"""개요 탭 — 전체 흐름과 각 탭의 구현 상태."""

from html import escape

from ui import theme

# (탭 이름, 다루는 내용, 구축방안 대응 절, 구현 여부)
STEPS = [
    ("1 믹스", "전략카드 선택·전략비중 지정 → 합성 MP", "4.1", True),
    ("2 주문·귀속", "계좌 주문(정수 수량)과 전략별 귀속수량·현금", "4.2", False),
    ("3 일별 평가", "귀속수량 × 종가로 전략별 평가·일수익률, 항등식", "4.3", False),
    ("4 이벤트", "입출금, 자문사 MP 변경, 고객 전략 교체, 배당·수수료", "4.4~4.6, 4.8", False),
    ("5 성과·화면", "누적수익률(TWR), 전략카드·내 랩 잔고 화면", "4.7", False),
    ("검증", "일일 대사, 사후 비례배분과의 비교", "3.1, 3.2", False),
]


def render() -> None:
    theme.section(
        "개요 ㅣ 이 시뮬레이터가 보여주는 것",
        "고객이 조합한 전략별 성과가 어떻게 계산되는지, 가입부터 전략 교체까지 한 계좌를 따라가며 확인합니다",
        "각 탭은 「멀티자문형랩 구축방안」 4장의 한 단계에 대응합니다. 위쪽은 고객에게 보이는 화면, 아래쪽은 그 숫자가 나온 계산 과정입니다.",
    )
    theme.html(
        '<div class="stages">'
        '<div class="stage"><div class="k">STAGE 1</div><div class="n">싱글자문</div>자문사 1곳의 MP를 계좌에 복제</div>'
        '<div class="stage"><div class="k">STAGE 2</div><div class="n">믹스</div>복수 전략카드를 비중대로 섞어 합성 MP 하나로 계산</div>'
        '<div class="stage"><div class="k">STAGE 3</div><div class="n">멀티자문 운용</div>자문사별 MP 변경을 계좌 단위로 넷팅·집행</div>'
        '<div class="stage last"><div class="k">STAGE 4</div><div class="n">성과분해</div>전략별 귀속수량·현금으로 전략별 수익률 산출</div>'
        "</div>"
    )
    theme.h3("탭 구성과 구현 상태")
    rows = "".join(
        f"<tr><td><b>{escape(name)}</b></td><td>{escape(what)}</td><td>{escape(ref)}</td>"
        f'<td><span class="pill {"teal" if done else "dim"}">{"구현" if done else "예정"}</span></td></tr>'
        for name, what, ref, done in STEPS
    )
    theme.html(
        '<div class="tbwrap"><table class="tb"><thead><tr><th>탭</th><th>다루는 내용</th><th>구축방안</th><th>상태</th></tr></thead>'
        f"<tbody>{rows}</tbody></table></div>"
    )
    theme.html(
        '<div class="band"><div class="t">DESIGN PRINCIPLE</div>'
        "<b>계좌가 유일한 원장.</b> 전략별 수치는 계좌 수치를 '귀속수량'으로 나눈 참고 지표이며, "
        "매입단가·거래내역·결제는 계좌 레벨에만 둡니다. 전략 간 비중은 고객이 다시 조정하기 전까지 되돌리지 않습니다(바이앤홀드).</div>"
    )
    theme.note("화면의 종목·비중·가격은 산식 설명을 위한 가상 예시이며 실제 시세·추천과 무관합니다.")


def render_placeholder(name: str) -> None:
    what, ref = next((what, ref) for step, what, ref, _ in STEPS if step == name)
    theme.section(f"{name} ㅣ 구현 예정", what, f"구축방안 {ref}절의 숫자를 그대로 재현하는 것을 완료 기준으로 합니다.")
    theme.html('<span class="pill dim">구현 예정</span>')
