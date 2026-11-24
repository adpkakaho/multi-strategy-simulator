"""화면 공통 스타일 — PLUS Design System v1.0의 토큰을 따른다. 규칙 요약은 DESIGN.md."""

from html import escape

import streamlit as st

# PLUS Design System v1.0 컬러 토큰
INK = "#121212"
TEAL = "#86BFBF"
CAMEL = "#CDAA8F"
TEAL_200 = "#B6E1E3"
TEAL_100 = "#D6EEF0"
SAND_300 = "#D7CAB7"
SAND_100 = "#F1EBDF"
GRAY_700 = "#333333"
GRAY_500 = "#888888"
GRAY_400 = "#A4A3A3"
GRAY_200 = "#CECECE"
GRAY_100 = "#ECECEC"
INK2 = GRAY_700
INK3 = GRAY_500
LINE = GRAY_200

# 전략(카드)별 차트 색. 카드 순서대로 고정 배정하며, 전략비중을 바꿔도 색은 바뀌지 않는다.
# PLUS Teal·Camel은 서로 구분이 어려워(색각 검증 실패) 같은 계열을 진하게 한 값을 쓴다. 근거는 DESIGN.md.
SERIES_COLORS = ["#12a3a3", "#c97b3f", "#6250d6", "#eda100", "#e34948", "#2a78d6"]
MAX_CARDS = len(SERIES_COLORS)

CSS = """
<style>
@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
@import url("https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap");
:root { --ink:#121212; --ink2:#333333; --ink3:#888888; --line:#CECECE; --line2:#ECECEC; --teal:#86BFBF; --teal200:#B6E1E3; --teal100:#D6EEF0; --camel:#CDAA8F; --sand100:#F1EBDF; }
.stApp, .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp td, .stApp th, .stApp div[data-testid="stMarkdownContainer"], .stApp div[data-testid="stMetricValue"] { font-family:"Pretendard","Malgun Gothic","맑은 고딕","Apple SD Gothic Neo",sans-serif; letter-spacing:-0.01em; }
.stApp [data-testid="stIconMaterial"] { font-family:"Material Symbols Rounded" !important; }
.block-container { max-width:1080px; padding-top:2.4rem; padding-bottom:4rem; }

.cover { background:var(--ink); color:#fff; padding:24px 30px 22px; margin-bottom:18px; }
.cover .org { font-family:"Bebas Neue","Pretendard",sans-serif; font-size:30px; line-height:1; letter-spacing:.04em; color:var(--teal); }
.cover h1 { font-size:27px; font-weight:700; margin:8px 0 4px; padding:0; color:#fff; letter-spacing:-0.02em; }
.cover .sub { font-size:14px; opacity:.8; }

.sec-head { border-top:2px solid var(--ink); padding-top:12px; margin:8px 0 18px; }
.sec-head .crumb { font-size:12px; font-weight:700; letter-spacing:.04em; color:#4f9a9a; margin-bottom:6px; }
.sec-head .h { font-size:21px; font-weight:700; line-height:1.4; letter-spacing:-0.02em; color:var(--ink); }
.sec-head .desc { margin-top:6px; color:var(--ink2); font-size:14px; }
.h3 { font-size:16px; font-weight:700; margin:26px 0 10px; padding-left:11px; border-left:4px solid var(--teal); color:var(--ink); }
.note { font-size:12.5px; color:var(--ink3); line-height:1.55; margin:4px 0 12px; }
.note::before { content:"※ "; }

.pill { display:inline-block; border:1.5px solid var(--ink); border-radius:999px; padding:0 10px; font-size:12px; font-weight:600; line-height:1.7; }
.pill.fill { background:var(--ink); color:#fff; }
.pill.teal { background:var(--teal); border-color:var(--teal); color:var(--ink); }
.pill.dim { border-color:var(--line); color:var(--ink3); }

.card { border:1px solid var(--line); border-radius:10px; padding:12px 14px 10px; min-height:190px; background:#fff; }
.card.off { background:#fafafa; color:var(--ink3); }
.card .k { font-size:11.5px; letter-spacing:.1em; color:var(--ink3); display:flex; align-items:center; gap:6px; }
.card .sw { display:inline-block; width:10px; height:10px; border-radius:2px; }
.card .n { font-size:16px; font-weight:700; margin:3px 0 0; }
.card .e { font-size:12px; color:var(--ink2); margin-bottom:8px; }
.card.off .e { color:var(--ink3); }
.card .row { display:flex; justify-content:space-between; font-size:13px; line-height:1.65; border-bottom:1px solid var(--line2); }
.card .row span:last-child { font-variant-numeric:tabular-nums; }

table.tb { width:100%; border-collapse:collapse; margin:6px 0 14px; font-size:13.5px; }
table.tb th { text-align:left; font-weight:700; padding:8px 10px; border-top:1.5px solid var(--ink); border-bottom:1px solid var(--ink); background:#fafafa; white-space:nowrap; }
table.tb td { padding:7px 10px; border-bottom:1px solid var(--line2); vertical-align:top; }
table.tb tr.total td { border-top:1px solid var(--ink); border-bottom:1.5px solid var(--ink); background:#fafafa; font-weight:600; }
table.tb .num { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
table.tb .muted { color:var(--ink3); }
.tbwrap { overflow-x:auto; }

.box { background:var(--sand100); border-radius:12px; padding:16px 22px; margin:10px 0 16px; font-size:13.5px; line-height:1.7; }
.box .t { font-weight:700; margin-bottom:4px; }
.band { background:var(--ink); color:#fff; padding:14px 20px; margin:16px 0; font-size:14px; line-height:1.7; }
.band .t { font-size:11.5px; letter-spacing:.12em; opacity:.7; margin-bottom:4px; }

.stages { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin:10px 0 14px; }
.stage { background:var(--line2); border-radius:10px; padding:12px 13px; font-size:12.5px; line-height:1.5; }
.stage:nth-child(2) { background:var(--sand100); }
.stage:nth-child(3) { background:var(--teal100); }
.stage.last { background:var(--ink); color:#fff; }
.stage .k { font-size:11px; letter-spacing:.1em; color:var(--ink3); }
.stage.last .k { color:rgba(255,255,255,.7); }
.stage .n { font-size:15.5px; font-weight:700; margin:3px 0 6px; }
@media (max-width:760px) { .stages { grid-template-columns:1fr 1fr; } }

div[data-testid="stMetric"] { border:1px solid var(--line); border-radius:10px; padding:10px 14px; }
div[data-testid="stMetricLabel"] p { font-size:12.5px; color:var(--ink2); }
div[data-testid="stMetricValue"] { font-size:22px; font-weight:700; }
button[data-baseweb="tab"] p { font-size:14.5px; font-weight:600; }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def cover(title: str, sub: str) -> None:
    html(f'<div class="cover"><div class="org">PLUS</div><h1>{escape(title)}</h1><div class="sub">{escape(sub)}</div></div>')


def section(crumb: str, headline: str, desc: str = "") -> None:
    desc_html = f'<div class="desc">{escape(desc)}</div>' if desc else ""
    html(f'<div class="sec-head"><div class="crumb">{escape(crumb)}</div><div class="h">{escape(headline)}</div>{desc_html}</div>')


def h3(title: str) -> None:
    html(f'<div class="h3">{escape(title)}</div>')


def note(text: str) -> None:
    html(f'<div class="note">{escape(text)}</div>')


def pct(value: float) -> str:
    """14.0 → '14%', 12.5 → '12.5%'"""
    return f"{value:.2f}".rstrip("0").rstrip(".") + "%"
