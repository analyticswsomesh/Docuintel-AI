from collections.abc import Iterable
from html import escape
from typing import Any

import streamlit as st


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root { --ivory:#F3F0D7; --sage:#CEE5D0; --gold:#F7D59C; --plum:#5E454B; --plum-deep:#49343A; --ink:#33272A; --muted:#765F63; --line:#D8CCB9; --surface:#FBF9EF; --surface-soft:#EEE8D8; }
        .stApp { background:var(--ivory); color:var(--ink); font-family:Inter,ui-sans-serif,system-ui,sans-serif; }
        [data-testid='stHeader'] { background:transparent; }
        [data-testid='stSidebar'] { background:var(--plum); border-right:0; }
        [data-testid='stSidebar'] > div:first-child { padding-top:1.1rem; }
        [data-testid='stSidebar'] * { color:#FFF8E8; }
        [data-testid='stSidebar'] .stButton { margin:.18rem 0; }
        [data-testid='stSidebar'] .stButton > button { color:#FFF8E8 !important; background:transparent; border:1px solid transparent; border-radius:.55rem; text-align:left; white-space:nowrap; overflow:visible; padding:.6rem .75rem; }
        [data-testid='stSidebar'] .stButton > button:hover { background:rgba(206,229,208,.18); border-color:rgba(206,229,208,.5); color:#FFFFFF !important; }
        [data-testid='stSidebar'] .stButton > button[kind='primary'] { background:var(--sage); color:var(--plum) !important; border-color:var(--sage); box-shadow:0 5px 14px rgba(35,20,25,.18); }
        [data-testid='stSidebar'] .stButton > button[kind='primary']:hover { background:#DDF0DE; color:var(--plum) !important; }
        [data-testid='stSidebar'] .di-nav-hint { color:#E7D9D0; font-size:.7rem; letter-spacing:.08em; margin:.4rem .75rem .7rem; text-transform:uppercase; }
        h1,h2,h3 { color:var(--plum) !important; letter-spacing:-.035em; }
        h1 { font-size:clamp(2.2rem,4vw,4rem) !important; line-height:1.02 !important; margin:0 0 .7rem !important; }
        h2 { font-size:1.65rem !important; } h3 { font-size:1.2rem !important; }
        .di-brand { padding:.55rem .25rem 1.65rem; }
        .di-mark { display:inline-flex; width:2.15rem; height:2.15rem; align-items:center; justify-content:center; margin-right:.65rem; border:1px solid var(--sage); color:var(--sage); font-size:.78rem; font-weight:800; letter-spacing:.08em; vertical-align:middle; }
        .di-brand-title { color:#FFF8E8; font-size:1.2rem; font-weight:750; vertical-align:middle; letter-spacing:-.03em; }
        .di-brand-subtitle { color:#D8C8C5; font-size:.68rem; letter-spacing:.16em; margin-top:.7rem; }
        .di-kicker,.di-section-label { color:var(--plum); font-size:.69rem; font-weight:800; letter-spacing:.16em; text-transform:uppercase; }
        .di-kicker { margin-bottom:.7rem; } .di-section-label { margin:2rem 0 .75rem; }
        .di-subtitle { color:var(--muted); font-size:1.04rem; line-height:1.6; max-width:48rem; }
        .di-hero,.di-panel { background:var(--surface); border:1px solid var(--line); box-shadow:0 12px 30px rgba(94,69,75,.06); }
        .di-hero { padding:2.1rem 2.2rem; border-left:5px solid var(--plum); }
        .di-hero-copy { color:var(--muted); font-size:1rem; line-height:1.6; max-width:42rem; }
        .di-panel { padding:1.2rem 1.35rem; }
        .di-stat { border-top:3px solid var(--sage); padding:.8rem 0 .55rem; }
        .di-stat-label { color:var(--muted); font-size:.7rem; font-weight:750; letter-spacing:.12em; text-transform:uppercase; }
        .di-stat-value { color:var(--plum); font-size:1.85rem; font-weight:800; margin-top:.3rem; }
        .di-stat-note { color:var(--muted); font-size:.76rem; }
        .di-empty { border:1px dashed #BDAE9C; background:rgba(251,249,239,.64); padding:2.3rem 1.5rem; text-align:center; }
        .di-empty-title { color:var(--plum); font-size:1.12rem; font-weight:750; }
        .di-empty-copy { color:var(--muted); font-size:.9rem; line-height:1.55; margin:.5rem auto 0; max-width:34rem; }
        .di-status { display:inline-block; border:1px solid var(--line); border-radius:999px; color:var(--muted); font-size:.66rem; font-weight:800; letter-spacing:.1em; padding:.27rem .58rem; text-transform:uppercase; }
        .di-status-indexed,.di-status-approved { background:var(--sage); border-color:#AAC9AE; color:#31583D; }
        .di-status-pending_review,.di-status-processing { background:var(--gold); border-color:#DDBB7C; color:#694C24; }
        .di-status-failed,.di-status-rejected { background:#F0D8D1; border-color:#D2A9A1; color:#793D3A; }
        .di-row { background:var(--surface); border-bottom:1px solid var(--line); padding:.9rem 0; }
        .di-row-title { color:var(--plum); font-weight:750; } .di-row-meta,.di-caption { color:var(--muted); font-size:.78rem; }
        .di-chip { background:var(--sage); border:1px solid #A9C7AC; color:var(--plum); display:inline-block; font-size:.75rem; margin:.15rem .25rem .15rem 0; padding:.32rem .58rem; }
        .di-chip-muted { background:var(--surface-soft); border-color:var(--line); }
        .di-citation { background:#F7F1DF; border-left:3px solid var(--gold); padding:.8rem 1rem; margin:.5rem 0; }
        .di-citation-title { color:var(--plum); font-weight:750; } .di-citation-meta { color:var(--muted); font-size:.78rem; margin-top:.25rem; }
        .di-callout { background:#F8E6C1; border:1px solid #E0BE7C; color:#694C24; padding:.85rem 1rem; }
        .di-footer { border-top:1px solid var(--line); color:var(--muted); font-size:.74rem; margin-top:3rem; padding-top:1rem; }
        .di-guide { background:var(--ivory); border:1px solid var(--plum); padding:.85rem; }
        .di-guide-grid { display:grid; gap:.65rem; grid-template-columns:1fr; }
        .di-guide-step { align-items:center; background:var(--ivory); border:1px solid var(--sage); border-left:4px solid var(--sage); box-shadow:0 5px 12px rgba(94,69,75,.06); display:flex; gap:1rem; min-height:5.5rem; padding:.8rem 1rem; transition:background .16s ease,transform .16s ease; }
        .di-guide-step:hover { background:var(--sage); transform:translateX(3px); }
        .di-guide-step:nth-child(2),.di-guide-step:nth-child(4) { border-color:var(--gold); border-left-color:var(--gold); }
        .di-guide-step:nth-child(2):hover,.di-guide-step:nth-child(4):hover { background:var(--gold); }
        .di-guide-number { align-items:center; background:var(--plum); color:var(--ivory); display:flex; flex:0 0 2.5rem; font-size:.72rem; font-weight:800; height:2.5rem; justify-content:center; }
        .di-guide-icon { color:var(--plum); flex:0 0 1.2rem; font-size:1.2rem; font-weight:800; text-align:center; }
        .di-guide-title { color:var(--plum); font-weight:800; } .di-guide-copy { color:var(--muted); font-size:.82rem; line-height:1.45; margin-top:.2rem; }
        @media (max-width:700px) { .di-guide-step { align-items:flex-start; flex-wrap:wrap; } .di-guide-copy { flex-basis:100%; margin-left:3.7rem; margin-top:-.65rem; } }
        .di-step-nav { border-top:1px solid var(--line); margin-top:3.3rem; padding-top:1.2rem; }
        .stButton > button { background:var(--plum); border:1px solid var(--plum); border-radius:.35rem; color:#FFF8E8; font-weight:700; min-height:2.45rem; }
        .stButton > button:hover { background:var(--plum-deep); border-color:var(--plum-deep); color:#FFF8E8; }
        .stTextInput input,.stTextArea textarea,[data-baseweb='select'] > div { background:var(--surface) !important; border-color:var(--line) !important; color:var(--ink) !important; }
        .stTextInput input::placeholder,.stTextArea textarea::placeholder { color:var(--muted) !important; opacity:1 !important; }
        .stFileUploader section { background:var(--surface) !important; border:1px dashed #BDAE9C; }
        .stFileUploader label,.stFileUploader label p,.stFileUploader section p,.stFileUploader section small { color:var(--plum) !important; }
        .stFileUploader section button { background:var(--plum) !important; border:1px solid var(--plum) !important; color:var(--ivory) !important; min-width:7rem !important; }
        .stFileUploader section button p,.stFileUploader section button span { color:var(--ivory) !important; display:inline !important; opacity:1 !important; visibility:visible !important; }
        .stFileUploader section button div[data-testid='stMarkdownContainer'] p { color:var(--ivory) !important; }
        [data-testid='stFileUploaderDropzone'] button { background:var(--plum) !important; border:1px solid var(--plum) !important; color:var(--ivory) !important; min-width:7rem !important; }
        [data-testid='stFileUploaderDropzone'] button p,[data-testid='stFileUploaderDropzone'] button div[data-testid='stMarkdownContainer'] p { color:var(--ivory) !important; }
        .stFileUploader section button:hover { background:var(--plum-deep) !important; color:#FFFFFF !important; }
        [data-testid='stPopover'] > button { background:var(--plum) !important; border:1px solid var(--plum) !important; color:var(--ivory) !important; }
        [data-testid='stPopover'] > button:hover { background:var(--plum-deep) !important; color:#FFFFFF !important; }
        [data-testid='stPopoverBody'] button { background:var(--plum) !important; border:1px solid var(--plum) !important; color:var(--ivory) !important; }
        [data-testid='stPopoverBody'] button p,[data-testid='stPopoverBody'] button span { color:var(--ivory) !important; }
        [data-testid='stPopoverBody'] button:hover { background:var(--plum-deep) !important; color:#FFFFFF !important; }
        </style>
        """, unsafe_allow_html=True,
    )


def render_brand() -> None:
    st.markdown('<div class="di-brand"><span class="di-mark">DI</span><span class="di-brand-title">DocuIntel AI</span><div class="di-brand-subtitle">LOCAL DOCUMENT INTELLIGENCE</div></div>', unsafe_allow_html=True)


def render_page_header(kicker: str, title: str, description: str) -> None:
    st.markdown(f'<div class="di-kicker">{escape(kicker)}</div><h1>{escape(title)}</h1><div class="di-subtitle">{escape(description)}</div>', unsafe_allow_html=True)


def render_section_label(label: str) -> None:
    st.markdown(f'<div class="di-section-label">{escape(label)}</div>', unsafe_allow_html=True)


def render_metric(label: str, value: str, note: str) -> None:
    st.markdown(f'<div class="di-stat"><div class="di-stat-label">{escape(label)}</div><div class="di-stat-value">{escape(value)}</div><div class="di-stat-note">{escape(note)}</div></div>', unsafe_allow_html=True)


def render_empty(title: str, copy: str) -> None:
    st.markdown(f'<div class="di-empty"><div class="di-empty-title">{escape(title)}</div><div class="di-empty-copy">{escape(copy)}</div></div>', unsafe_allow_html=True)


def render_status(status: str) -> None:
    value = str(status or "unknown")
    css_status = value.lower().replace(" ", "-")
    st.markdown(f'<span class="di-status di-status-{escape(css_status)}">{escape(value)}</span>', unsafe_allow_html=True)


def render_citation_card(citation: dict[str, Any]) -> None:
    source = citation.get("source_name") or citation.get("document_id") or "Unknown document"
    page = citation.get("page_number") or "page unavailable"
    chunk = citation.get("chunk_id") or "unknown chunk"
    st.markdown(f'<div class="di-citation"><div class="di-citation-title">{escape(str(source))}</div><div class="di-citation-meta">{escape(str(page))} · chunk {escape(str(chunk))}</div></div>', unsafe_allow_html=True)


def toggle_selection(current: Iterable[str], value: str) -> list[str]:
    selected = list(dict.fromkeys(str(item) for item in current))
    if value in selected:
        selected.remove(value)
    else:
        selected.append(value)
    return selected


def status_counts(documents: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = {"uploaded": 0, "processing": 0, "indexed": 0, "failed": 0}
    for document in documents:
        status = str(document.get("status", "")).lower()
        if status in counts:
            counts[status] += 1
    return counts
