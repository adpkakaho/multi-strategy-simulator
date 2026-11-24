"""화면 공통 스타일 — 「멀티자문형랩 구축방안」 문서의 흑백 톤을 따른다."""

from html import escape

import streamlit as st

INK = "#232323"
INK2 = "#555555"
INK3 = "#8a8a8a"
LINE = "#d9d9d9"

# 전략(카드)별 차트 색. 카드 순서대로 고정 배정하며, 전략비중을 바꿔도 색은 바뀌지 않는다.
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
MAX_CARDS = len(SERIES_COLORS)

CSS = """
<style>
@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
:root { --ink:#232323; --ink2:#555; --ink3:#8a8a8a; --line:#d9d9d9; --line2:#ececec; --bg2:#f6f6f6; }
.stApp, .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp td, .stApp th, .stApp div[data-testid="stMarkdownContainer"], .stApp div[data-testid="stMetricValue"] { font-family:"Pretendard","Malgun Gothic","맑은 고딕","Apple SD Gothic Neo",sans-serif; letter-spacing:-0.01em; }
.stApp [data-testid="stIconMaterial"] { font-family:"Material Symbols Rounded" !important; }
.block-container { max-width:1080px; padding-top:2.4rem; padding-bottom:4rem; }

.cover { background:#000; color:#fff; padding:26px 30px 22px; margin-bottom:18px; }
.cover .org { font-size:12.5px; letter-spacing:.14em; opacity:.8; }
.cover h1 { font-size:27px; font-weight:700; margin:8px 0 4px; padding:0; color:#fff; letter-spacing:-0.02em; }
.cover .sub { font-size:14px; opacity:.8; }

.sec-head { border-top:2px solid var(--ink); padding-top:12px; margin:8px 0 18px; }
.sec-head .crumb { font-size:12.5px; color:var(--ink3); margin-bottom:6px; }
.sec-head .h { font-size:21px; font-weight:700; line-height:1.4; letter-spacing:-0.02em; color:var(--ink); }
.sec-head .desc { margin-top:6px; color:var(--ink2); font-size:14px; }
.h3 { font-size:16px; font-weight:700; margin:26px 0 10px; padding-left:11px; border-left:3px solid var(--ink); color:var(--ink); }
.note { font-size:12.5px; color:var(--ink3); line-height:1.55; margin:4px 0 12px; }
.note::before { content:"※ "; }

.pill { display:inline-block; border:1.5px solid var(--ink); border-radius:999px; padding:0 10px; font-size:12px; font-weight:600; line-height:1.7; }
.pill.fill { background:var(--ink); color:#fff; }
.pill.dim { border-color:var(--line); color:var(--ink3); }

.card { border:1px solid var(--ink); padding:12px 14px 10px; min-height:168px; background:#fff; }
.card.off { border-color:var(--line); color:var(--ink3); }
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

.box { border:1px solid var(--ink); padding:13px 18px; margin:10px 0 16px; font-size:13.5px; line-height:1.7; }
.box .t { font-weight:700; margin-bottom:4px; }
.band { background:var(--ink); color:#fff; padding:14px 20px; margin:16px 0; font-size:14px; line-height:1.7; }
.band .t { font-size:11.5px; letter-spacing:.12em; opacity:.7; margin-bottom:4px; }

.stages { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin:10px 0 14px; }
.stage { border:1.5px solid var(--ink); padding:12px 13px; font-size:12.5px; line-height:1.5; }
.stage.last { background:var(--ink); color:#fff; }
.stage .k { font-size:11px; letter-spacing:.1em; color:var(--ink3); }
.stage.last .k { color:rgba(255,255,255,.7); }
.stage .n { font-size:15.5px; font-weight:700; margin:3px 0 6px; }
@media (max-width:760px) { .stages { grid-template-columns:1fr 1fr; } }

div[data-testid="stMetric"] { border:1px solid var(--line); padding:10px 14px; }
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
