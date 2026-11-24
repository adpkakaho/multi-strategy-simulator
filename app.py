"""멀티자문형 랩 시뮬레이터 — 「멀티자문형랩 구축방안」의 계산 흐름을 단계별 탭으로 보여준다."""

import streamlit as st

from ui import tab_mix, tab_overview, theme

st.set_page_config(page_title="멀티자문형 랩 시뮬레이터", layout="wide")
theme.inject_css()

with st.sidebar:
    st.page_link("app.py", label="멀티자문형 랩 시뮬레이터")
    st.page_link("pages/legacy_day_simulator.py", label="초기 기획 시뮬레이터")
    st.divider()
    show_calc = st.toggle("계산 과정 표시", value=True, help="끄면 고객에게 보이는 화면만 남습니다.")
    st.caption("화면의 종목·비중·가격은 가상 예시이며 실제 시세·추천과 무관합니다.")

theme.cover("멀티자문형 랩 시뮬레이터", "싱글자문 → 믹스 → 멀티자문 → 성과분해 ㅣ 고객 화면과 계산 과정")

TABS = ["개요", "1 믹스", "2 주문·귀속", "3 일별 평가", "4 이벤트", "5 성과·화면", "검증"]
tabs = st.tabs(TABS)
with tabs[0]:
    tab_overview.render()
with tabs[1]:
    tab_mix.render(show_calc)
for tab, name in zip(tabs[2:], TABS[2:]):
    with tab:
        tab_overview.render_placeholder(name)
