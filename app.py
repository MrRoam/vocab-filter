from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import streamlit as st

from vocab_filter.export_md import rows_to_markdown
from vocab_filter.level_mapping import CEFR_OPTIONS, score_to_cefr
from vocab_filter.pipeline import analyze_content
from vocab_filter.placement import estimate_level, sample_test_words
from vocab_filter.ui_state import QUICK_PLACEMENT_SOURCE, should_show_level_settings_placement

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None


st.set_page_config(
    page_title="Vocab Filter",
    page_icon="📘",
    layout="wide",
    menu_items={"Get Help": None, "Report a bug": None, "About": None},
)


RESULT_LABELS = {
    "target": "待学习词汇",
    "review": "可选复习词汇",
    "known": "低优先级词汇",
    "ungraded": "词库未收录词",
    "proper": "专有名词",
    "all": "全部分析结果",
}
EXPORT_DETAIL_OPTIONS = ["仅单词", "单词 + 翻译", "完整字段"]
CATEGORY_HELP = {
    "target": "明显高于当前水平或较低频，优先学习。",
    "review": "接近当前水平边界，可能认识但不稳，可按需要复习。",
    "known": "按当前水平和常见度判断，暂时不用优先处理。",
    "ungraded": "CEFR 词库没有收录的词，常见于术语、派生词或作者造词，建议单独人工判断。",
    "proper": "人名、地名、机构名等，默认不进入背词清单。",
}

PLACEMENT_WORDS_PER_LEVEL = 5
PROFILE_PATH = Path("data/user_profile.json")


def apply_style() -> None:
    theme = st.session_state.get("theme_mode", "深色")
    if theme == "浅色":
        tokens = """
  --vf-bg: #f8f7f3;
  --vf-bg-end: #eeece6;
  --vf-surface: rgba(255, 255, 255, 0.72);
  --vf-surface-solid: #ffffff;
  --vf-dialog-bg: #ffffff;
  --vf-dialog-text: #171717;
  --vf-dialog-muted: #57534e;
  --vf-dialog-subtle: #f6f4ef;
  --vf-surface-soft: rgba(28, 25, 23, 0.045);
  --vf-panel-2: #f3f1eb;
  --vf-line: rgba(28, 25, 23, 0.12);
  --vf-line-strong: rgba(28, 25, 23, 0.18);
  --vf-text: #171717;
  --vf-muted: #68635c;
  --vf-faint: #a8a29e;
  --vf-accent: #18181b;
  --vf-accent-contrast: #ffffff;
  --vf-accent-soft: rgba(24, 24, 27, 0.08);
  --vf-warm: #2563eb;
  --vf-success: #15803d;
  --vf-shadow: 0 24px 48px -24px rgba(28, 25, 23, 0.32);
  --vf-shadow-soft: 0 1px 2px rgba(28, 25, 23, 0.06);
  --vf-shell: #ffffff;
  --vf-shell-text: #171717;
  --vf-shell-muted: #746f68;
  --vf-shell-line: rgba(28, 25, 23, 0.12);
  --vf-shell-ring: rgba(28, 25, 23, 0.10);
  --vf-shell-button: #18181b;
  --vf-shell-button-text: #ffffff;
        """
        app_background = """
  background:
    linear-gradient(112deg, rgba(37, 99, 235, 0.08), transparent 32rem),
    linear-gradient(180deg, rgba(28, 25, 23, 0.035), transparent 22rem),
    linear-gradient(180deg, #faf9f6 0%, var(--vf-bg) 46%, var(--vf-bg-end) 100%);
        """
    else:
        tokens = """
  --vf-bg: #08090b;
  --vf-bg-end: #111214;
  --vf-surface: rgba(255, 255, 255, 0.055);
  --vf-surface-solid: #171719;
  --vf-dialog-bg: #171719;
  --vf-dialog-text: #fcfbf8;
  --vf-dialog-muted: rgba(252, 251, 248, 0.62);
  --vf-dialog-subtle: rgba(255, 255, 255, 0.055);
  --vf-surface-soft: rgba(255, 255, 255, 0.07);
  --vf-panel-2: #202023;
  --vf-line: rgba(255, 255, 255, 0.09);
  --vf-line-strong: rgba(255, 255, 255, 0.16);
  --vf-text: #fcfbf8;
  --vf-muted: rgba(252, 251, 248, 0.64);
  --vf-faint: rgba(252, 251, 248, 0.42);
  --vf-accent: rgba(255, 255, 255, 0.96);
  --vf-accent-contrast: #111214;
  --vf-accent-soft: rgba(255, 255, 255, 0.10);
  --vf-warm: #6aa7ff;
  --vf-success: #7dd3a7;
  --vf-shadow: 0 32px 80px -42px rgba(0, 0, 0, 0.92);
  --vf-shadow-soft: 0 1px 2px rgba(0, 0, 0, 0.34);
  --vf-shell: #272725;
  --vf-shell-text: #fcfbf8;
  --vf-shell-muted: rgba(252, 251, 248, 0.62);
  --vf-shell-line: rgba(255, 255, 255, 0.08);
  --vf-shell-ring: rgba(0, 0, 0, 0.42);
  --vf-shell-button: rgba(255, 255, 255, 0.96);
  --vf-shell-button-text: #111214;
        """
        app_background = """
  background:
    linear-gradient(110deg, rgba(37, 99, 235, 0.18), transparent 34rem),
    linear-gradient(250deg, rgba(252, 251, 248, 0.06), transparent 30rem),
    linear-gradient(180deg, #121315 0%, var(--vf-bg) 48%, var(--vf-bg-end) 100%);
        """

    st.markdown(
        """
<style>
:root {
__TOKENS__
  --vf-radius-sm: 8px;
  --vf-radius-md: 12px;
  --vf-radius-lg: 16px;
  --vf-radius-xl: 22px;
  --vf-radius-2xl: 30px;
}
.stApp {
__APP_BACKGROUND__
  color: var(--vf-text);
}
.stApp::before {
  content: "";
  pointer-events: none;
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(120, 113, 108, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(120, 113, 108, 0.05) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: linear-gradient(to bottom, black, transparent 70%);
  z-index: 0;
}
.block-container {
  position: relative;
  z-index: 1;
  padding-top: 1.05rem;
  padding-left: 2.8rem;
  padding-right: 2.8rem;
  max-width: 1320px;
}
[data-testid="stSidebar"] {
  display: none;
}
[data-testid="stCaptionContainer"] {
  color: var(--vf-muted);
}
h1, h2, h3 {
  letter-spacing: 0;
  color: var(--vf-text);
}
h1 {
  font-size: 1.3rem;
  margin-bottom: 0;
}
h2, h3 {
  margin-top: 1.4rem;
}
p, li, label, span {
  color: inherit;
}
.stApp [data-testid="stWidgetLabel"],
.stApp [data-testid="stWidgetLabel"] *,
.stApp label {
  color: var(--vf-text) !important;
  opacity: 1 !important;
}
.stApp [data-testid="stCaptionContainer"],
.stApp [data-testid="stCaptionContainer"] * {
  color: var(--vf-muted) !important;
  opacity: 1 !important;
}
[data-testid="stDeployButton"],
[data-testid="stToolbar"],
#MainMenu,
footer,
header {
  visibility: hidden;
  height: 0;
}
div[data-testid="stMetric"] {
  background: var(--vf-surface);
  border: 1px solid var(--vf-line);
  border-radius: var(--vf-radius-lg);
  padding: .95rem 1rem;
  box-shadow: var(--vf-shadow-soft);
  backdrop-filter: blur(18px);
}
div[data-testid="stMetricValue"] {
  color: var(--vf-text);
  font-size: 1.85rem;
  font-weight: 680;
}
div[data-testid="stMetricLabel"] {
  color: var(--vf-muted);
}
.stTabs [data-baseweb="tab-list"] {
  gap: .8rem;
  border-bottom: 1px solid var(--vf-line);
}
.stTabs [data-baseweb="tab"] {
  border-radius: 999px 999px 0 0;
  padding-left: .4rem;
  padding-right: .4rem;
  color: var(--vf-muted);
}
.stTabs [aria-selected="true"] {
  color: var(--vf-text);
}
.stTabs [data-baseweb="tab-highlight"] {
  background: var(--vf-warm);
}
.stButton > button,
.stDownloadButton > button {
  border-radius: var(--vf-radius-md);
  border: 1px solid var(--vf-line);
  background: var(--vf-surface-solid);
  color: var(--vf-text);
  min-height: 42px;
  font-weight: 620;
  box-shadow: var(--vf-shadow-soft);
  transition:
    transform 180ms ease-out,
    box-shadow 180ms ease-out,
    border-color 180ms ease-out,
    background 180ms ease-out;
}
.stButton > button:hover,
.stDownloadButton > button:hover {
  border-color: var(--vf-line-strong);
  background: var(--vf-panel-2);
  color: var(--vf-text);
  transform: translateY(-1px);
  box-shadow: var(--vf-shadow);
}
.stButton > button:active,
.stDownloadButton > button:active {
  transform: scale(.98);
}
.stButton > button[kind="primary"] {
  background: var(--vf-accent);
  border-color: var(--vf-accent);
  color: var(--vf-accent-contrast);
}
.stButton > button *,
.stDownloadButton > button * {
  color: inherit !important;
}
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
textarea,
input {
  border-color: var(--vf-line) !important;
  border-radius: var(--vf-radius-md) !important;
  background-color: var(--vf-surface-solid) !important;
  color: var(--vf-text) !important;
}
div[data-baseweb="input"] > div *,
textarea::placeholder,
input::placeholder {
  color: var(--vf-faint) !important;
  opacity: 1 !important;
}
div[data-baseweb="select"] > div * {
  color: var(--vf-text) !important;
  opacity: 1 !important;
}
div[data-baseweb="select"] span,
div[data-baseweb="select"] input,
div[data-baseweb="input"] input,
textarea,
input:not([type="checkbox"]):not([type="radio"]) {
  color: var(--vf-text) !important;
  -webkit-text-fill-color: var(--vf-text) !important;
  opacity: 1 !important;
}
div[data-baseweb="select"] svg,
div[data-baseweb="input"] svg {
  color: var(--vf-muted) !important;
  fill: var(--vf-muted) !important;
}
textarea:focus,
input:focus,
div[data-baseweb="select"] > div:focus-within {
  border-color: var(--vf-warm) !important;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--vf-warm) 18%, transparent) !important;
}
[data-testid="stFileUploaderDropzone"] {
  border: 1px dashed var(--vf-line-strong);
  border-radius: var(--vf-radius-xl);
  background: var(--vf-surface);
}
[data-testid="stFileUploaderDropzone"] *,
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] p {
  color: var(--vf-muted) !important;
  opacity: 1 !important;
}
[data-testid="stFileUploaderDropzone"] button {
  background: var(--vf-accent) !important;
  border-color: var(--vf-accent) !important;
  color: var(--vf-accent-contrast) !important;
}
[data-testid="stFileUploaderDropzone"] button * {
  color: var(--vf-accent-contrast) !important;
}
[data-testid="stDataFrame"] {
  border: 1px solid var(--vf-line);
  border-radius: var(--vf-radius-xl);
  overflow: hidden;
  box-shadow: var(--vf-shadow-soft);
}
div[data-baseweb="popover"] > div {
  border: 1px solid var(--vf-line) !important;
  border-radius: var(--vf-radius-xl) !important;
  background: var(--vf-surface-solid) !important;
  color: var(--vf-text) !important;
  box-shadow: var(--vf-shadow) !important;
}
div[data-testid="stDialog"],
div[data-testid="stDialog"] div[role="dialog"],
div[role="dialog"] {
  color: var(--vf-dialog-text) !important;
}
div[data-testid="stDialog"] div[role="dialog"],
div[role="dialog"] {
  border: 1px solid rgba(28, 25, 23, 0.14) !important;
  border-radius: var(--vf-radius-2xl);
  background: var(--vf-dialog-bg) !important;
  color: var(--vf-dialog-text) !important;
  box-shadow: var(--vf-shadow);
}
div[data-testid="stDialog"] h1,
div[data-testid="stDialog"] h2,
div[data-testid="stDialog"] h3,
div[data-testid="stDialog"] p,
div[data-testid="stDialog"] label,
div[data-testid="stDialog"] span,
div[data-testid="stDialog"] li,
div[data-testid="stDialog"] div[data-testid="stMarkdownContainer"],
div[role="dialog"] h1,
div[role="dialog"] h2,
div[role="dialog"] h3,
div[role="dialog"] p,
div[role="dialog"] label,
div[role="dialog"] span,
div[role="dialog"] li,
div[role="dialog"] div[data-testid="stMarkdownContainer"] {
  color: var(--vf-dialog-text) !important;
}
html body .stApp div[role="dialog"] p,
html body .stApp div[role="dialog"] span,
html body .stApp div[role="dialog"] label,
html body .stApp div[role="dialog"] li,
html body .stApp div[role="dialog"] h1,
html body .stApp div[role="dialog"] h2,
html body .stApp div[role="dialog"] h3,
html body .stApp div[role="dialog"] h4,
html body .stApp div[role="dialog"] div[data-testid="stMarkdownContainer"],
html body .stApp div[role="dialog"] [data-testid="stWidgetLabel"],
html body .stApp div[role="dialog"] [data-testid="stMarkdownContainer"] p,
html body .stApp div[role="dialog"] [data-testid="stMarkdownContainer"] span {
  color: var(--vf-dialog-text) !important;
  opacity: 1 !important;
}
div[data-testid="stDialog"] [data-testid="stCaptionContainer"],
div[data-testid="stDialog"] .vf-dialog-heading p,
div[data-testid="stDialog"] .vf-nav-note,
div[role="dialog"] [data-testid="stCaptionContainer"],
div[role="dialog"] .vf-dialog-heading p,
div[role="dialog"] .vf-nav-note {
  color: var(--vf-dialog-muted) !important;
}
html body .stApp div[role="dialog"] [data-testid="stCaptionContainer"],
html body .stApp div[role="dialog"] .vf-dialog-heading p,
html body .stApp div[role="dialog"] .vf-nav-note {
  color: var(--vf-dialog-muted) !important;
  opacity: 1 !important;
}
div[data-testid="stDialog"] .vf-section-label,
div[role="dialog"] .vf-section-label {
  color: #a84e0a !important;
}
html body .stApp div[role="dialog"] .vf-section-label {
  color: #a84e0a !important;
  opacity: 1 !important;
}
html body .stApp div[role="dialog"] .stButton > button,
html body .stApp div[role="dialog"] .stDownloadButton > button {
  background: #ffffff !important;
  border-color: rgba(28, 25, 23, 0.14) !important;
  color: var(--vf-dialog-text) !important;
  box-shadow: 0 1px 2px rgba(28, 25, 23, 0.06) !important;
}
html body .stApp div[role="dialog"] .stButton > button:hover,
html body .stApp div[role="dialog"] .stDownloadButton > button:hover {
  background: var(--vf-dialog-subtle) !important;
  border-color: rgba(28, 25, 23, 0.24) !important;
}
html body .stApp div[role="dialog"] .stButton > button p,
html body .stApp div[role="dialog"] .stButton > button span,
html body .stApp div[role="dialog"] .stDownloadButton > button p,
html body .stApp div[role="dialog"] .stDownloadButton > button span {
  color: var(--vf-dialog-text) !important;
}
html body .stApp div[role="dialog"] .stButton > button[kind="primary"],
html body .stApp div[role="dialog"] .stDownloadButton > button[kind="primary"] {
  background: #171717 !important;
  border-color: #171717 !important;
  color: #ffffff !important;
}
html body .stApp div[role="dialog"] .stButton > button[kind="primary"] p,
html body .stApp div[role="dialog"] .stButton > button[kind="primary"] span,
html body .stApp div[role="dialog"] .stDownloadButton > button[kind="primary"] p,
html body .stApp div[role="dialog"] .stDownloadButton > button[kind="primary"] span {
  color: #ffffff !important;
}
html body .stApp div[role="dialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"],
html body .stApp div[data-testid="stDialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"] {
  background: #ffffff !important;
  border-color: rgba(28, 25, 23, 0.16) !important;
  color: var(--vf-dialog-text) !important;
}
html body .stApp div[role="dialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"] *,
html body .stApp div[data-testid="stDialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"] * {
  color: var(--vf-dialog-text) !important;
}
html body .stApp div[role="dialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-primary"],
html body .stApp div[data-testid="stDialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] {
  background: #171717 !important;
  border-color: #171717 !important;
  color: #ffffff !important;
}
html body .stApp div[role="dialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] *,
html body .stApp div[data-testid="stDialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] * {
  color: #ffffff !important;
}
div[role="dialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"],
div[data-testid="stDialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"] {
  background: #ffffff !important;
  border-color: rgba(28, 25, 23, 0.16) !important;
  color: var(--vf-dialog-text) !important;
}
div[role="dialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"] *,
div[data-testid="stDialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"] * {
  color: var(--vf-dialog-text) !important;
}
div[role="dialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-primary"],
div[data-testid="stDialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] {
  background: #171717 !important;
  border-color: #171717 !important;
  color: #ffffff !important;
}
div[role="dialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] *,
div[data-testid="stDialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] * {
  color: #ffffff !important;
}
div[data-testid="stDialog"] div[data-baseweb="select"] > div,
div[data-testid="stDialog"] div[data-baseweb="input"] > div,
div[data-testid="stDialog"] textarea,
div[data-testid="stDialog"] input,
div[role="dialog"] div[data-baseweb="select"] > div,
div[role="dialog"] div[data-baseweb="input"] > div,
div[role="dialog"] textarea,
div[role="dialog"] input {
  background-color: #ffffff !important;
  color: var(--vf-dialog-text) !important;
  border-color: rgba(28, 25, 23, 0.16) !important;
}
div[data-testid="stDialog"] div[data-baseweb="radio"] label,
div[data-testid="stDialog"] div[data-baseweb="radio"] span,
div[role="dialog"] div[data-baseweb="radio"] label,
div[role="dialog"] div[data-baseweb="radio"] span {
  color: var(--vf-dialog-text) !important;
}
div[data-testid="stDialog"] .vf-dialog-heading,
div[role="dialog"] .vf-dialog-heading {
  border-bottom-color: rgba(28, 25, 23, 0.12) !important;
}
div[data-testid="stDialog"] .vf-level-pill,
div[role="dialog"] .vf-level-pill {
  background: var(--vf-dialog-subtle) !important;
  border-color: rgba(28, 25, 23, 0.12) !important;
  color: var(--vf-dialog-muted) !important;
}
div[data-testid="stDialog"] .vf-level-pill strong,
div[role="dialog"] .vf-level-pill strong {
  color: var(--vf-dialog-text) !important;
}
.vf-topbar {
  min-height: 56px;
  padding-bottom: .75rem;
  border-bottom: 1px solid var(--vf-line);
  margin-bottom: .85rem;
}
.vf-brand {
  display: inline-flex;
  align-items: center;
  gap: .65rem;
  color: var(--vf-text);
  font-size: 1.02rem;
  font-weight: 720;
}
.vf-brand-mark {
  width: 34px;
  height: 34px;
  display: inline-grid;
  place-items: center;
  border-radius: 12px;
  background: var(--vf-accent);
  color: var(--vf-accent-contrast);
  font-size: .8rem;
  box-shadow: var(--vf-shadow-soft);
}
.vf-status {
  color: var(--vf-muted);
  font-size: .82rem;
  line-height: 1.25;
  text-align: right;
  white-space: nowrap;
}
.vf-status strong {
  color: var(--vf-text);
  font-size: 1rem;
  font-weight: 720;
}
.vf-top-rule {
  display: none;
}
.vf-settings-panel {
  padding: .15rem .1rem .3rem;
}
.vf-dialog-heading {
  margin: 0 0 .9rem;
  padding-bottom: .75rem;
  border-bottom: 1px solid var(--vf-line);
}
.vf-dialog-heading h2 {
  margin: 0;
  font-size: 1.45rem;
  letter-spacing: 0;
}
.vf-dialog-heading p {
  margin: .25rem 0 0;
  color: var(--vf-muted);
  font-size: .92rem;
}
.vf-nav-note {
  color: var(--vf-muted);
  font-size: .8rem;
  line-height: 1.5;
  padding: .75rem .2rem 0;
}
.vf-analysis-shell {
  border: 1px solid var(--vf-line);
  border-radius: var(--vf-radius-2xl);
  background: var(--vf-surface);
  padding: 1.35rem;
  box-shadow: var(--vf-shadow);
  backdrop-filter: blur(22px);
}
.vf-workspace-heading {
  margin-bottom: 1rem;
}
.vf-workspace-heading h2 {
  margin: 0;
  font-size: clamp(1.5rem, 2.8vw, 2.25rem);
  line-height: 1.12;
}
.vf-workspace-heading p {
  max-width: 720px;
  margin: .45rem 0 0;
  color: var(--vf-muted);
  font-size: .96rem;
  line-height: 1.7;
}
.vf-section-label {
  color: var(--vf-warm);
  font-size: .76rem;
  font-weight: 740;
  letter-spacing: .09em;
  text-transform: uppercase;
  margin-bottom: .45rem;
}
.vf-export {
  margin-top: 1.2rem;
  padding-top: 1rem;
  border-top: 1px solid var(--vf-line);
}
.vf-note {
  color: var(--vf-muted);
  font-size: .92rem;
  line-height: 1.55;
}
.vf-level-pill {
  display: inline-flex;
  align-items: baseline;
  gap: .45rem;
  border: 1px solid var(--vf-line);
  border-radius: 999px;
  background: var(--vf-surface);
  padding: .45rem .75rem;
  color: var(--vf-muted);
  font-size: .84rem;
  box-shadow: var(--vf-shadow-soft);
}
.vf-level-pill strong {
  color: var(--vf-text);
  font-size: .98rem;
}
.stApp {
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.stApp::after {
  content: "";
  pointer-events: none;
  position: fixed;
  inset: 0;
  background: linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.08) 100%);
  z-index: 0;
}
.block-container {
  max-width: 1230px;
  padding-top: 2rem;
}
.vf-topbar {
  display: flex;
  align-items: center;
  padding-bottom: 1.35rem;
  border-bottom: 0;
  margin-bottom: clamp(2.5rem, 7vh, 5rem);
}
.vf-brand {
  font-size: .96rem;
  font-weight: 680;
}
.vf-brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  box-shadow: 0 0 0 .5px rgba(255, 255, 255, .14), var(--vf-shadow-soft);
}
.vf-status {
  color: var(--vf-muted);
  font-size: .72rem;
  text-transform: uppercase;
  letter-spacing: .06em;
}
.vf-status strong {
  display: inline-block;
  margin-top: .12rem;
  color: var(--vf-text);
  font-size: .98rem;
  letter-spacing: 0;
}
.vf-workspace-heading {
  width: min(760px, 100%);
  margin: 0 auto 1rem;
  text-align: center;
  animation: vf-rise 420ms cubic-bezier(.165, .84, .44, 1) both;
}
.vf-workspace-heading h2 {
  font-size: clamp(1.75rem, 4vw, 2.55rem);
  font-weight: 660;
  line-height: 1;
}
.vf-workspace-heading p {
  margin: .45rem auto 0;
  max-width: 520px;
  color: var(--vf-muted);
  font-size: clamp(.92rem, 1.8vw, 1rem);
  line-height: 1.35;
}
.vf-level-onboarding-copy {
  width: min(768px, 100%);
  margin: 0 auto .8rem;
  padding: 1rem;
  border: 1px solid var(--vf-line);
  border-radius: 24px;
  background: var(--vf-surface);
  box-shadow: var(--vf-shadow-soft);
  backdrop-filter: blur(18px);
  animation: vf-rise 460ms cubic-bezier(.165, .84, .44, 1) 40ms both;
}
.vf-level-onboarding-copy h3 {
  margin: 0;
  font-size: 1.18rem;
  line-height: 1.25;
}
.vf-level-onboarding-copy p {
  margin: .35rem 0 .85rem;
  color: var(--vf-muted);
  font-size: .94rem;
  line-height: 1.5;
}
.vf-level-current {
  width: min(768px, 100%);
  margin: 0 auto 1rem;
  text-align: center;
}
.vf-composer {
  width: min(768px, 100%);
  margin: 0 auto .85rem;
  text-align: center;
  animation: vf-rise 420ms cubic-bezier(.165, .84, .44, 1) both;
}
.vf-composer h2 {
  margin: 0;
  color: var(--vf-text) !important;
  opacity: 1 !important;
  font-size: clamp(1.72rem, 4vw, 2.65rem);
  font-weight: 560;
  line-height: 1.06;
}
.vf-composer p {
  margin: .72rem auto 0;
  max-width: 36rem;
  color: var(--vf-muted);
  font-size: .95rem;
  line-height: 1.55;
}
.vf-composer-meta {
  display: inline-flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: .5rem;
  margin-top: .9rem;
}
.vf-composer-meta span {
  min-height: 30px;
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--vf-line);
  border-radius: 999px;
  padding: .28rem .66rem;
  background: var(--vf-surface-soft);
  color: var(--vf-muted);
  font-size: .76rem;
  font-weight: 560;
}
.vf-composer-action-align {
  height: 0;
}
.vf-composer-toolbar-anchor {
  display: none;
}
.vf-workspace-kicker {
  display: inline-flex;
  align-items: center;
  gap: .5rem;
  margin-bottom: .65rem;
  padding: .42rem .68rem .42rem .48rem;
  border-radius: 999px;
  background: var(--vf-surface-soft);
  color: var(--vf-muted);
  box-shadow: 0 0 0 .5px var(--vf-line), var(--vf-shadow-soft);
  backdrop-filter: blur(10px);
  font-size: .84rem;
  font-weight: 520;
}
.vf-workspace-kicker strong {
  display: inline-flex;
  align-items: center;
  min-height: 1.55rem;
  padding: .18rem .48rem;
  border-radius: 999px;
  background: var(--vf-warm);
  color: #ffffff;
  font-size: .72rem;
  font-weight: 700;
}
.vf-analysis-shell {
  width: min(768px, 100%);
  margin: 0 auto;
  padding: .75rem;
  border: 1px solid var(--vf-shell-line);
  border-radius: 28px;
  background: var(--vf-shell);
  color: var(--vf-shell-text);
  box-shadow: 0 0 0 1px rgba(0, 0, 0, .42), var(--vf-shadow);
  backdrop-filter: blur(18px);
  animation: vf-rise 520ms cubic-bezier(.165, .84, .44, 1) 80ms both;
}
.vf-analysis-shell:hover {
  border-color: var(--vf-line-strong);
  transform: translateY(-1px);
}
.vf-analysis-shell [data-testid="stWidgetLabel"] {
  min-height: 0;
}
.vf-analysis-shell [data-testid="stWidgetLabel"] p {
  display: none;
}
.vf-analysis-shell [data-testid="stTextArea"],
.vf-analysis-shell [data-testid="stFileUploader"] {
  margin-bottom: .35rem;
}
.vf-analysis-shell [data-testid="stFileUploaderDropzone"] {
  min-height: 148px;
  padding: .85rem .7rem;
  border-style: solid;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.035);
}
.vf-analysis-shell [data-testid="stFileUploaderDropzone"] button {
  min-height: 34px;
  border-radius: 999px;
}
.vf-analysis-shell textarea {
  min-height: 148px !important;
  max-height: max(35svh, 13rem);
  padding: .75rem .85rem !important;
  border: 0 !important;
  border-radius: 20px !important;
  background: transparent !important;
  color: var(--vf-shell-text) !important;
  -webkit-text-fill-color: var(--vf-shell-text) !important;
  box-shadow: none !important;
  resize: vertical;
}
.vf-analysis-shell textarea::placeholder {
  color: var(--vf-shell-muted) !important;
}
.vf-analysis-shell .stButton > button {
  min-height: 42px;
  border-radius: 999px;
  background: var(--vf-shell-button) !important;
  border-color: transparent !important;
  color: var(--vf-shell-button-text) !important;
  box-shadow: var(--vf-shadow-soft);
}
.vf-analysis-shell .stButton > button:hover {
  transform: translateY(-1px);
  box-shadow: var(--vf-shadow);
}
div[data-testid="stHorizontalBlock"]:has(.vf-composer-action-align):not(:has([data-testid="stFileUploader"])) {
  width: min(768px, 100%) !important;
  margin-left: auto;
  margin-right: auto;
}
[data-testid="stFileUploader"],
[data-testid="stTextArea"] {
  width: min(768px, 100%) !important;
  margin-left: auto;
  margin-right: auto;
}
div[data-testid="stElementContainer"]:has([data-testid="stFileUploader"]) {
  margin-bottom: 0 !important;
}
div[data-testid="stElementContainer"]:has([data-testid="stTextArea"]) {
  margin-top: -1rem !important;
  margin-bottom: 0 !important;
  position: relative;
}
div[data-testid="stElementContainer"]:has([data-testid="stTextArea"])::before {
  content: "";
  position: absolute;
  top: -1px;
  left: 50%;
  width: min(768px, 100%);
  height: 4px;
  background: var(--vf-shell);
  transform: translateX(-50%);
  pointer-events: none;
  z-index: 20;
}
div[data-testid="stElementContainer"]:has(.vf-composer-toolbar-anchor) {
  height: 0 !important;
  margin: 0 !important;
  overflow: hidden !important;
}
[data-testid="stFileUploader"] {
  margin-bottom: 0 !important;
}
[data-testid="stFileUploaderDropzone"] {
  min-height: 62px !important;
  padding: .58rem .72rem .58rem .82rem !important;
  border-style: solid !important;
  border-bottom: 0 !important;
  border-radius: 30px 30px 0 0 !important;
  background: var(--vf-shell) !important;
  box-shadow: none !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
  border-color: var(--vf-line-strong);
}
[data-testid="stFileUploaderDropzone"] > div {
  min-width: 0;
}
[data-testid="stFileUploaderDropzone"] p {
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
[data-testid="stFileUploaderDropzone"] button {
  width: 44px !important;
  min-width: 44px !important;
  height: 44px !important;
  min-height: 44px !important;
  border-radius: 999px !important;
  font-size: 0 !important;
  padding: 0 !important;
}
[data-testid="stFileUploaderDropzone"] button * {
  display: none !important;
}
[data-testid="stFileUploaderDropzone"] button::after {
  content: "+";
  color: var(--vf-accent-contrast);
  font-size: 1.45rem;
  font-weight: 360;
  line-height: 1;
}
[data-testid="stFileChips"] {
  flex: 1 1 auto;
  min-width: 0;
}
[data-testid="stFileChip"] {
  max-width: 100% !important;
  min-height: 42px;
  border-radius: 12px !important;
  background: var(--vf-surface-soft) !important;
}
[data-testid="stFileChipName"] {
  max-width: none !important;
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
  color: transparent !important;
  font-size: 0 !important;
  line-height: 0 !important;
}
[data-testid="stFileChipName"]::after {
  content: attr(title);
  display: block;
  color: var(--vf-shell-text);
  font-size: .92rem;
  font-weight: 650;
  line-height: 1.25;
  overflow-wrap: anywhere;
  word-break: break-word;
  white-space: normal;
}
[data-testid="stFileChipDeleteBtn"] button {
  width: 34px !important;
  min-width: 34px !important;
  height: 34px !important;
  min-height: 34px !important;
  background: color-mix(in srgb, var(--vf-shell) 72%, transparent) !important;
  border: 1px solid var(--vf-shell-line) !important;
  color: var(--vf-shell-text) !important;
}
[data-testid="stFileChipDeleteBtn"] button:hover {
  background: var(--vf-accent-soft) !important;
}
[data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChip"]) button[aria-label="Add files"] {
  display: none !important;
}
[data-testid="stTextArea"] {
  margin-top: -1.25rem !important;
}
[data-testid="stTextArea"] textarea {
  min-height: 138px !important;
  max-height: max(38svh, 12rem);
  padding: 1.05rem 1.1rem !important;
  border-radius: 0 !important;
  background-color: var(--vf-shell) !important;
  border-color: var(--vf-shell-line) !important;
  border-top-color: transparent !important;
  border-bottom-color: transparent !important;
  color: var(--vf-shell-text) !important;
  -webkit-text-fill-color: var(--vf-shell-text) !important;
  box-shadow: none !important;
}
[data-testid="stTextArea"] textarea::placeholder {
  color: var(--vf-shell-muted) !important;
}
div[data-testid="stButton"]:has(button[kind="primary"]) {
  width: min(768px, 100%) !important;
  margin-left: auto;
  margin-right: auto;
}
div[data-testid="stButton"]:has(button[kind="primary"]) > button {
  border-radius: 999px;
}
div[data-testid="stHorizontalBlock"]:has(.vf-composer-action-align):not(:has([data-testid="stFileUploader"])) {
  margin-top: -3.25rem;
  padding: .72rem .78rem .78rem;
  border: 1px solid var(--vf-shell-line);
  border-top: 0;
  border-radius: 0 0 30px 30px;
  background: var(--vf-shell);
  box-shadow: 0 0 0 1px var(--vf-shell-ring), var(--vf-shadow);
  position: relative;
}
div[data-testid="stHorizontalBlock"]:has(.vf-composer-action-align):not(:has([data-testid="stFileUploader"]))::before {
  content: "";
  position: absolute;
  top: -1px;
  left: 0;
  width: 100%;
  height: 4px;
  background: var(--vf-shell);
  pointer-events: none;
  z-index: 20;
}
div[data-testid="stHorizontalBlock"]:has(.vf-composer-action-align):not(:has([data-testid="stFileUploader"])) [data-testid="stSelectbox"] {
  margin-bottom: 0;
}
div[data-testid="stHorizontalBlock"]:has(.vf-composer-action-align):not(:has([data-testid="stFileUploader"])) .stButton > button {
  min-height: 44px;
}
.st-key-composer_shell,
div[class*="st-key-composer_shell"] {
  width: min(768px, 100%);
  margin: 0 auto;
  padding: .58rem .72rem .68rem !important;
  border: 1px solid var(--vf-shell-line);
  border-radius: 30px;
  background: var(--vf-shell);
  box-shadow: 0 0 0 1px var(--vf-shell-ring), var(--vf-shadow);
  overflow: hidden;
}
.vf-composer-shell-marker {
  display: none;
}
.st-key-composer_shell [data-testid="stFileUploader"],
.st-key-composer_shell [data-testid="stTextArea"],
div[class*="st-key-composer_shell"] [data-testid="stFileUploader"],
div[class*="st-key-composer_shell"] [data-testid="stTextArea"] {
  width: 100% !important;
  margin: 0 !important;
}
.st-key-composer_shell div[data-testid="stElementContainer"]:has([data-testid="stFileUploader"]),
.st-key-composer_shell div[data-testid="stElementContainer"]:has([data-testid="stTextArea"]),
.st-key-composer_shell div[data-testid="stElementContainer"]:has(.vf-composer-toolbar-anchor),
div[class*="st-key-composer_shell"] div[data-testid="stElementContainer"]:has([data-testid="stFileUploader"]),
div[class*="st-key-composer_shell"] div[data-testid="stElementContainer"]:has([data-testid="stTextArea"]),
div[class*="st-key-composer_shell"] div[data-testid="stElementContainer"]:has(.vf-composer-toolbar-anchor) {
  margin: 0 !important;
  height: auto !important;
  overflow: visible !important;
}
.st-key-composer_shell div[data-testid="stElementContainer"]:has([data-testid="stTextArea"])::before,
.st-key-composer_shell div[data-testid="stHorizontalBlock"]:has(.vf-composer-action-align)::before,
div[class*="st-key-composer_shell"] div[data-testid="stElementContainer"]:has([data-testid="stTextArea"])::before,
div[class*="st-key-composer_shell"] div[data-testid="stHorizontalBlock"]:has(.vf-composer-action-align)::before {
  content: none !important;
}
.st-key-composer_shell [data-testid="stFileUploaderDropzone"],
div[class*="st-key-composer_shell"] [data-testid="stFileUploaderDropzone"] {
  min-height: 46px !important;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}
.st-key-composer_shell [data-testid="stTextArea"],
div[class*="st-key-composer_shell"] [data-testid="stTextArea"] {
  margin-top: .05rem !important;
}
.st-key-composer_shell [data-testid="stTextArea"] textarea,
div[class*="st-key-composer_shell"] [data-testid="stTextArea"] textarea {
  height: 154px !important;
  min-height: 132px !important;
  padding: .1rem .1rem .42rem !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}
.st-key-composer_shell div[data-testid="stHorizontalBlock"]:has(.vf-composer-action-align),
div[class*="st-key-composer_shell"] div[data-testid="stHorizontalBlock"]:has(.vf-composer-action-align) {
  width: 100% !important;
  margin: 0 !important;
  padding: .5rem 0 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}
.st-key-composer_shell div[data-testid="stHorizontalBlock"]:has(.vf-composer-action-align) .stButton > button,
div[class*="st-key-composer_shell"] div[data-testid="stHorizontalBlock"]:has(.vf-composer-action-align) .stButton > button {
  min-height: 44px;
}
div[role="dialog"] div[data-testid="stButton"]:has(button[kind="primary"]),
div[data-testid="stDialog"] div[data-testid="stButton"]:has(button[kind="primary"]) {
  width: fit-content !important;
  max-width: 100% !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
}
div[role="dialog"] div[data-testid="stButton"]:has(button[kind="primary"]) > button,
div[data-testid="stDialog"] div[data-testid="stButton"]:has(button[kind="primary"]) > button {
  min-width: 0;
  width: auto !important;
  padding-left: 1.15rem !important;
  padding-right: 1.15rem !important;
}
.vf-settings-panel {
  padding: .2rem 0 .6rem;
}
.vf-dialog-heading {
  margin: 0 0 1.2rem;
  padding-bottom: 1rem;
}
.vf-dialog-heading h2 {
  font-size: 1.72rem;
  line-height: 1.1;
  font-weight: 720;
}
.vf-dialog-heading p {
  max-width: 560px;
  font-size: .95rem;
  line-height: 1.5;
}
.vf-section-label {
  margin: 0 0 .75rem;
  color: var(--vf-warm);
  font-size: .68rem;
  font-weight: 760;
  letter-spacing: .14em;
}
.vf-setting-summary {
  display: flex;
  flex-wrap: wrap;
  gap: .55rem;
  margin-bottom: 1.2rem;
}
.vf-level-pill {
  min-height: 34px;
  border: 1px solid var(--vf-line);
  background: var(--vf-surface-soft);
  box-shadow: var(--vf-shadow-soft);
}
.vf-nav-note {
  display: none;
}
.vf-export {
  margin-top: 1.35rem;
  border-top-color: var(--vf-line);
}
.vf-export-action-label {
  min-height: 1.5rem;
  margin-bottom: .35rem;
  color: var(--vf-text);
  font-size: .9rem;
  font-weight: 640;
}
.vf-side-panel {
  padding: 1rem;
  border: 1px solid var(--vf-line);
  border-radius: 22px;
  background: var(--vf-surface);
  box-shadow: var(--vf-shadow-soft);
}
[data-testid="stDataFrame"] {
  font-size: 1.02rem;
}
div[data-testid="stMetric"] {
  border-radius: 16px;
  background: var(--vf-surface-soft);
}
.stTabs [data-baseweb="tab-list"] {
  border-bottom-color: var(--vf-line);
}
.stTabs [data-baseweb="tab"] {
  border-radius: 999px;
}
div[data-testid="stDialog"] div[role="dialog"],
div[role="dialog"] {
  border-color: var(--vf-line) !important;
  background: var(--vf-dialog-bg) !important;
  color: var(--vf-dialog-text) !important;
  box-shadow: 0 32px 100px -48px rgba(0, 0, 0, .88) !important;
}
html body .stApp div[role="dialog"] .stButton > button,
html body .stApp div[role="dialog"] .stDownloadButton > button,
div[role="dialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"],
div[data-testid="stDialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"] {
  background: var(--vf-dialog-subtle) !important;
  border-color: var(--vf-line) !important;
  color: var(--vf-dialog-text) !important;
}
html body .stApp div[role="dialog"] .stButton > button:hover,
html body .stApp div[role="dialog"] .stDownloadButton > button:hover {
  background: var(--vf-surface-soft) !important;
}
html body .stApp div[role="dialog"] .stButton > button[kind="primary"],
html body .stApp div[role="dialog"] .stDownloadButton > button[kind="primary"],
div[role="dialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-primary"],
div[data-testid="stDialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] {
  background: var(--vf-accent) !important;
  border-color: transparent !important;
  color: var(--vf-accent-contrast) !important;
}
html body .stApp div[role="dialog"] .stButton > button[kind="primary"] *,
html body .stApp div[role="dialog"] .stDownloadButton > button[kind="primary"] *,
div[role="dialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] *,
div[data-testid="stDialog"] div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] * {
  color: var(--vf-accent-contrast) !important;
}
div[data-testid="stDialog"] div[data-baseweb="select"] > div,
div[data-testid="stDialog"] div[data-baseweb="input"] > div,
div[data-testid="stDialog"] textarea,
div[data-testid="stDialog"] input,
div[role="dialog"] div[data-baseweb="select"] > div,
div[role="dialog"] div[data-baseweb="input"] > div,
div[role="dialog"] textarea,
div[role="dialog"] input {
  background-color: var(--vf-dialog-subtle) !important;
  color: var(--vf-dialog-text) !important;
  border-color: var(--vf-line) !important;
}
div[data-testid="stRadio"] > div {
  gap: .45rem;
}
div[data-testid="stRadio"] label {
  padding: .2rem .35rem;
  border-radius: 999px;
}
div[data-testid="stRadio"] [data-baseweb="radio"] {
  margin-right: .2rem;
}
div[data-baseweb="select"] input {
  border: 0 !important;
  outline: 0 !important;
  box-shadow: none !important;
  background: transparent !important;
  color: transparent !important;
  -webkit-text-fill-color: transparent !important;
  caret-color: transparent !important;
}
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
textarea,
input:not([type="checkbox"]):not([type="radio"]) {
  outline: 0 !important;
  box-shadow: none !important;
}
div[data-baseweb="select"] > div:focus-within,
div[data-baseweb="input"] > div:focus-within,
textarea:focus,
input:not([type="checkbox"]):not([type="radio"]):focus {
  border-color: var(--vf-warm) !important;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--vf-warm) 16%, transparent) !important;
}
div[data-baseweb="popover"] [role="listbox"],
div[data-baseweb="popover"] ul {
  background: var(--vf-surface-solid) !important;
  color: var(--vf-text) !important;
}
div[data-baseweb="popover"] [role="option"],
div[data-baseweb="popover"] li {
  color: var(--vf-text) !important;
}
div[data-baseweb="popover"] [aria-selected="true"] {
  background: var(--vf-accent-soft) !important;
  color: var(--vf-text) !important;
}
.vf-analysis-shell {
  box-shadow: 0 0 0 1px var(--vf-shell-ring), var(--vf-shadow);
}
[data-testid="stTextArea"] textarea,
.vf-analysis-shell textarea {
  border: 1px solid var(--vf-shell-line) !important;
  outline: 0 !important;
  box-shadow: none !important;
}
[data-testid="stTextArea"] textarea {
  border-top-color: transparent !important;
  border-bottom-color: transparent !important;
  box-shadow: none !important;
}
[data-testid="stTextAreaRootElement"],
[data-testid="stTextAreaRootElement"] > div {
  border-color: transparent !important;
  background: transparent !important;
  box-shadow: none !important;
}
[data-testid="stTextArea"] textarea:focus,
.vf-analysis-shell textarea:focus {
  border-color: var(--vf-warm) !important;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--vf-warm) 14%, transparent) !important;
}
.st-key-composer_shell [data-testid="stTextAreaRootElement"],
.st-key-composer_shell [data-testid="stTextAreaRootElement"] > div,
div[class*="st-key-composer_shell"] [data-testid="stTextAreaRootElement"],
div[class*="st-key-composer_shell"] [data-testid="stTextAreaRootElement"] > div {
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}
.st-key-composer_shell [data-testid="stTextArea"] textarea:focus,
div[class*="st-key-composer_shell"] [data-testid="stTextArea"] textarea:focus {
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}
div[role="dialog"] {
  font-size: 1rem;
}
div[role="dialog"] [data-testid="stWidgetLabel"] p {
  font-size: .96rem;
  font-weight: 640;
}
div[role="dialog"] div[data-baseweb="select"] > div,
div[role="dialog"] div[data-baseweb="input"] > div,
div[role="dialog"] textarea,
div[role="dialog"] input:not([type="checkbox"]):not([type="radio"]) {
  font-size: .98rem !important;
}
div[data-testid="stNumberInput"] button,
div[role="dialog"] div[data-testid="stNumberInput"] button {
  background: var(--vf-dialog-subtle) !important;
  border-color: var(--vf-line) !important;
  color: var(--vf-dialog-text) !important;
}
div[data-testid="stNumberInput"] button:hover,
div[role="dialog"] div[data-testid="stNumberInput"] button:hover {
  background: var(--vf-surface-soft) !important;
}
div[data-testid="stNumberInput"] button *,
div[role="dialog"] div[data-testid="stNumberInput"] button * {
  color: var(--vf-dialog-text) !important;
  fill: var(--vf-dialog-text) !important;
}
div[data-testid="stNumberInput"] div[data-baseweb="input"] > div,
div[role="dialog"] div[data-testid="stNumberInput"] div[data-baseweb="input"] > div {
  border-color: var(--vf-line) !important;
  box-shadow: none !important;
}
div[data-testid="stNumberInputContainer"],
div[data-testid="stNumberInput"] div[data-baseweb="input"],
div[role="dialog"] div[data-testid="stNumberInputContainer"],
div[role="dialog"] div[data-testid="stNumberInput"] div[data-baseweb="input"] {
  background: var(--vf-dialog-subtle) !important;
  border-color: var(--vf-line) !important;
  box-shadow: none !important;
}
div[data-testid="stRadio"] > div {
  gap: .55rem;
}
div[data-testid="stRadio"] label:has(input[type="radio"]) {
  min-height: 36px;
  margin: 0 .25rem .35rem 0;
  padding: .46rem .75rem !important;
  border: 1px solid var(--vf-line);
  border-radius: 999px;
  background: var(--vf-surface-solid);
  color: var(--vf-muted) !important;
  box-shadow: var(--vf-shadow-soft);
}
div[data-testid="stRadio"] label:has(input[type="radio"]) * {
  color: inherit !important;
}
div[data-testid="stRadio"] label:has(input[type="radio"]:checked) {
  background: var(--vf-accent);
  border-color: var(--vf-accent);
  color: var(--vf-accent-contrast) !important;
}
div[data-testid="stRadio"] [data-baseweb="radio"] {
  width: auto !important;
  min-width: auto !important;
  margin-right: .35rem !important;
  opacity: 1 !important;
  overflow: visible !important;
}
div[data-testid="stRadio"] label:not(:has(input[type="radio"]:checked)) [data-baseweb="radio"] {
  opacity: .35 !important;
}
div[role="dialog"] div[data-testid="stRadio"] label:has(input[type="radio"]) {
  background: var(--vf-dialog-subtle);
  border-color: var(--vf-line);
  color: var(--vf-dialog-muted) !important;
  font-size: .98rem;
}
div[role="dialog"] div[data-testid="stRadio"] label:has(input[type="radio"]:checked) {
  background: var(--vf-accent);
  border-color: var(--vf-accent);
  color: var(--vf-accent-contrast) !important;
}
div[role="dialog"] div[data-testid="stRadio"] label:has(input[type="radio"]:checked) * {
  color: var(--vf-accent-contrast) !important;
}
@keyframes vf-rise {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
@media (max-width: 820px) {
  .block-container {
    padding-left: 1rem;
    padding-right: 1rem;
  }
  .vf-topbar {
    margin-bottom: 1.2rem;
  }
  .vf-workspace-heading {
    text-align: left;
  }
  .vf-workspace-heading h2 {
    font-size: 2.2rem;
  }
  .vf-composer h2 {
    font-size: 1.85rem;
  }
  .vf-analysis-shell {
    padding: .6rem;
    border-radius: 24px;
  }
  .st-key-composer_shell,
  div[class*="st-key-composer_shell"] {
    padding: .52rem .6rem .58rem !important;
  }
  .st-key-composer_shell [data-testid="stTextArea"] textarea,
  div[class*="st-key-composer_shell"] [data-testid="stTextArea"] textarea {
    height: 90px !important;
    min-height: 64px !important;
  }
}
</style>
        """.replace("__TOKENS__", tokens).replace("__APP_BACKGROUND__", app_background),
        unsafe_allow_html=True,
    )


def load_user_profile() -> dict:
    if not PROFILE_PATH.exists():
        return {}
    try:
        return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_user_profile() -> None:
    profile = {
        "level_source": st.session_state.get("level_source"),
        "exam_type": st.session_state.get("exam_type"),
        "exam_score": st.session_state.get("exam_score"),
        "measured_level": st.session_state.get("measured_level"),
        "manual_cefr": st.session_state.get("manual_cefr"),
    }
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")


def init_state() -> None:
    if not st.session_state.get("_profile_loaded"):
        profile = load_user_profile()
        for key in ["level_source", "exam_type", "exam_score", "measured_level", "manual_cefr"]:
            value = profile.get(key)
            if value is not None and key not in st.session_state:
                st.session_state[key] = value
        st.session_state["_profile_loaded"] = True

    st.session_state.theme_mode = "深色"
    st.session_state.setdefault("level_source", None)
    st.session_state.setdefault("exam_type", "CET-6 六级")
    st.session_state.setdefault("exam_score", None)
    st.session_state.setdefault("measured_level", None)
    st.session_state.setdefault("placement_notice", "")
    st.session_state.setdefault("manual_cefr", None)
    st.session_state.setdefault("cefr_source", "自动选择")
    st.session_state.setdefault("settings_menu_section", "常规")
    st.session_state.setdefault("level_settings_show_placement", False)
    st.session_state.setdefault("draft_exam_type", st.session_state.get("exam_type", "CET-6 六级"))
    if "draft_exam_score" not in st.session_state:
        st.session_state.draft_exam_score = (
            st.session_state.exam_score
            if st.session_state.get("exam_score") is not None
            else default_exam_score(st.session_state.draft_exam_type)
        )


def default_exam_score(exam: str) -> float | int:
    if exam == "IELTS 雅思":
        return 6.0
    if exam == "TOEFL iBT 托福":
        return 80
    if exam == "Duolingo English Test":
        return 115
    if exam == "高考英语":
        return 120
    return 500


def current_level_from_state() -> tuple[str | None, str, str]:
    level_source = st.session_state.get("level_source")

    if level_source == "考试成绩换算":
        exam = st.session_state.get("exam_type", "CET-6 六级")
        score = st.session_state.get("exam_score")
        if score is None:
            return None, "missing", "尚未确定英语水平。"
        estimate = score_to_cefr(exam, float(score))
        return estimate.level, "exam", estimate.note

    if level_source == "快速测评结果":
        measured = st.session_state.get("measured_level")
        if measured:
            return measured, "placement", "来自快速测评。"
        return None, "missing", "尚未完成测评。"

    if level_source == "手动选择 CEFR":
        user_level = st.session_state.get("manual_cefr")
        if user_level:
            return user_level, "manual", "手动选择。"

    return None, "missing", "尚未确定英语水平。"


def cefr_runtime_settings() -> tuple[str, str]:
    source = st.session_state.get("cefr_source", "自动选择")
    if source == "本地 CEFR 词库":
        return "cefrpy", "data/cefr_seed.csv"
    return "auto", "data/cefr_seed.csv"


def decode_upload(uploaded_file) -> str:
    raw = uploaded_file.getvalue()
    for enc in ["utf-8", "utf-8-sig", "gbk", "latin-1"]:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def rows_to_csv_bytes(rows: list[dict]) -> bytes:
    if not rows:
        return b""
    if pd is not None:
        return pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


def compact_rows(rows: list[dict], include_score: bool = False, include_surface: bool = True) -> list[dict]:
    compact: list[dict] = []
    for row in rows:
        word = row.get("lemma") or row.get("word") or ""
        surface = row.get("word") or ""
        item = {
            "词汇": word,
            "CEFR": row.get("cefr") or "未知",
            "中文释义": row.get("meaning_zh") or "暂无释义",
            "原文句子": row.get("sentence") or "",
        }
        if include_surface and surface and surface != word:
            item = {"词汇": word, "原文形式": surface, **{k: v for k, v in item.items() if k != "词汇"}}
        if include_score:
            item["评分"] = row.get("score", "")
        compact.append(item)
    return compact


def proper_rows(rows: list[dict]) -> list[dict]:
    return [
        {
            "词汇": row.get("word") or row.get("lemma") or "",
            "原文句子": row.get("sentence") or "",
        }
        for row in rows
    ]


def show_table(rows: list[dict], height: int | None = None) -> None:
    if pd is None:
        st.write(rows)
        return

    df = pd.DataFrame(rows)
    if not df.empty:
        for column in ["原文句子", "原文形式"]:
            if column in df.columns and df[column].fillna("").astype(str).str.strip().eq("").all():
                df = df.drop(columns=[column])
    if height is None:
        height = min(520, max(190, 44 + 35 * max(1, len(df))))

    column_config = {
        "词汇": st.column_config.TextColumn("词汇", width="small"),
        "原文形式": st.column_config.TextColumn("原文形式", width="small"),
        "CEFR": st.column_config.TextColumn("CEFR", width="small"),
        "评分": st.column_config.NumberColumn("评分", width="small"),
        "中文释义": st.column_config.TextColumn("中文释义", width="medium"),
        "原文句子": st.column_config.TextColumn("原文句子", width="large"),
    }
    st.dataframe(
        df,
        use_container_width=True,
        height=height,
        hide_index=True,
        column_config=column_config,
    )


def get_export_rows(result, scope: str) -> list[dict]:
    if scope == RESULT_LABELS["target"]:
        return result.likely_unknown
    if scope == RESULT_LABELS["review"]:
        return result.borderline
    if scope == RESULT_LABELS["known"]:
        return result.likely_known
    if scope == RESULT_LABELS["ungraded"]:
        return result.ungraded
    if scope == RESULT_LABELS["proper"]:
        return result.proper_nouns
    return result.all_rows


def export_word(row: dict) -> str:
    return row.get("word") or row.get("lemma") or ""


def simple_export_rows(rows: list[dict], detail: str) -> list[dict]:
    if detail == "完整字段":
        return rows
    simple: list[dict] = []
    for row in rows:
        item = {"单词": export_word(row)}
        if detail == "单词 + 翻译":
            item["中文释义"] = row.get("meaning_zh") or ""
        simple.append(item)
    return simple


def rows_to_simple_markdown(rows: list[dict], title: str, detail: str) -> str:
    lines: list[str] = []
    for row in rows:
        word = export_word(row)
        if not word:
            continue
        lines.append(word)
    return "\n".join(lines)


def get_export_bytes(rows: list[dict], scope: str, fmt: str, detail: str) -> tuple[bytes, str, str]:
    slug = {
        RESULT_LABELS["target"]: "target_vocabulary",
        RESULT_LABELS["review"]: "review_candidates",
        RESULT_LABELS["known"]: "excluded_vocabulary",
        RESULT_LABELS["ungraded"]: "ungraded_vocabulary",
        RESULT_LABELS["proper"]: "named_entities",
        RESULT_LABELS["all"]: "all_results",
    }[scope]
    export_rows = simple_export_rows(rows, detail)
    if fmt == "Markdown (.md)":
        markdown = rows_to_markdown(rows, scope) if detail == "完整字段" else rows_to_simple_markdown(rows, scope, detail)
        return markdown.encode("utf-8"), f"{slug}.md", "text/markdown"
    return rows_to_csv_bytes(export_rows), f"{slug}.csv", "text/csv"


def coerce_exam_score(exam: str, raw_score) -> float | int:
    fallback = default_exam_score(exam)
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        score = float(fallback)
    if exam == "IELTS 雅思":
        return min(9.0, max(0.0, float(score)))
    if exam == "TOEFL iBT 托福":
        return min(120, max(0, int(round(score))))
    if exam == "Duolingo English Test":
        return min(160, max(10, int(round(score))))
    if exam == "高考英语":
        return min(150, max(0, int(round(score))))
    return min(710, max(0, int(round(score))))


def render_exam_score_input(exam: str, *, key: str) -> float:
    st.session_state[key] = coerce_exam_score(exam, st.session_state.get(key, default_exam_score(exam)))
    if exam == "IELTS 雅思":
        st.number_input("成绩", min_value=0.0, max_value=9.0, step=0.5, format="%.1f", key=key)
    elif exam == "TOEFL iBT 托福":
        st.number_input("成绩", min_value=0, max_value=120, step=1, format="%d", key=key)
    elif exam == "Duolingo English Test":
        st.number_input("成绩", min_value=10, max_value=160, step=5, format="%d", key=key)
    elif exam == "高考英语":
        st.number_input("成绩", min_value=0, max_value=150, step=1, format="%d", key=key)
    else:
        st.number_input("成绩", min_value=0, max_value=710, step=1, format="%d", key=key)
    return float(st.session_state[key])


def render_level_settings() -> None:
    st.markdown('<div class="vf-section-label">LEVEL</div>', unsafe_allow_html=True)
    level_options = [QUICK_PLACEMENT_SOURCE, "考试成绩换算", "手动选择 CEFR"]
    current_source = st.session_state.get("level_source")
    if "level_source_choice" not in st.session_state:
        st.session_state.level_source_choice = current_source if current_source in level_options else QUICK_PLACEMENT_SOURCE
    level_source = st.radio(
        "确定方式",
        level_options,
        key="level_source_choice",
        horizontal=True,
    )

    if st.session_state.placement_notice:
        st.success(st.session_state.placement_notice)
        st.session_state.placement_notice = ""

    show_placement = should_show_level_settings_placement(
        level_source,
        st.session_state.get("level_settings_show_placement", False),
    )
    if level_source != QUICK_PLACEMENT_SOURCE and st.session_state.get("level_settings_show_placement"):
        st.session_state.level_settings_show_placement = False

    if level_source == "考试成绩换算":
        exam_options = ["CET-4 四级", "CET-6 六级", "IELTS 雅思", "TOEFL iBT 托福", "Duolingo English Test", "高考英语"]
        current_exam = st.session_state.get("draft_exam_type") or st.session_state.get("exam_type", "CET-6 六级")
        exam = st.selectbox(
            "考试类型",
            exam_options,
            index=exam_options.index(current_exam) if current_exam in exam_options else 1,
            key="draft_exam_type",
        )
        if st.session_state.get("_draft_exam_score_for") != exam:
            saved_score = st.session_state.get("exam_score") if st.session_state.get("exam_type") == exam else None
            st.session_state.draft_exam_score = saved_score if saved_score is not None else default_exam_score(exam)
            st.session_state._draft_exam_score_for = exam
        score = render_exam_score_input(exam, key="draft_exam_score")
        estimate = score_to_cefr(exam, score)
        st.markdown(
            f'<div class="vf-setting-summary"><span class="vf-level-pill">换算结果 <strong>{estimate.level}</strong></span></div>',
            unsafe_allow_html=True,
        )
        if st.button("使用这个水平", type="primary", key="apply_exam_level"):
            st.session_state.exam_type = exam
            st.session_state.exam_score = st.session_state.draft_exam_score
            st.session_state.level_source = "考试成绩换算"
            st.session_state.analysis_cefr_level = estimate.level
            st.session_state.level_settings_show_placement = False
            st.session_state.placement_notice = f"已按 {exam} {st.session_state.draft_exam_score:g} 应用：{estimate.level}。"
            save_user_profile()
            st.rerun()

    elif level_source == QUICK_PLACEMENT_SOURCE:
        if not st.session_state.get("measured_level"):
            st.info("还没有测评结果，先完成一次测评。")
        if st.button("开始测评", type="primary", key="start_placement_from_level"):
            st.session_state.level_settings_show_placement = True
            show_placement = True
        if show_placement:
            render_placement_settings(show_heading=False)
        elif st.session_state.get("measured_level"):
            if st.button("使用测评结果", type="primary", key="apply_measured_level"):
                st.session_state.level_source = QUICK_PLACEMENT_SOURCE
                st.session_state.analysis_cefr_level = st.session_state.measured_level
                st.session_state.placement_notice = f"已应用测评结果：{st.session_state.measured_level}。"
                save_user_profile()
                st.rerun()

    elif level_source == "手动选择 CEFR":
        selected = st.session_state.get("manual_cefr") or "B1"
        st.selectbox(
            "CEFR 等级",
            CEFR_OPTIONS,
            index=CEFR_OPTIONS.index(selected) if selected in CEFR_OPTIONS else 2,
            key="manual_cefr_choice",
        )
        if st.button("使用这个等级", type="primary", key="apply_manual_level"):
            st.session_state.manual_cefr = st.session_state.manual_cefr_choice
            st.session_state.level_source = "手动选择 CEFR"
            st.session_state.analysis_cefr_level = st.session_state.manual_cefr
            st.session_state.level_settings_show_placement = False
            st.session_state.placement_notice = f"已应用手动等级：{st.session_state.manual_cefr}。"
            save_user_profile()
            st.rerun()


def open_dialog(title: str, renderer, *, width: str = "large") -> bool:
    dialog = getattr(st, "dialog", getattr(st, "experimental_dialog", None))
    if dialog is None:
        return False

    st.session_state["_dialog_opened_this_run"] = True
    try:
        decorator = dialog(title, width=width)
    except TypeError:
        decorator = dialog(title)

    @decorator
    def dialog_body() -> None:
        renderer()

    dialog_body()
    return True


def render_about_panel() -> None:
    st.markdown(
        """
按你的英语水平，从文章里筛出更值得优先学习的英文词。

Vocab Filter 会结合 CEFR 等级和词频，把文本中的词汇分成待学习、可复习、低优先级和未收录等类别。

这个项目是开源的，仓库地址：[github.com/MrRoam/vocab-filter](https://github.com/MrRoam/vocab-filter)。
        """
    )


def render_topbar(user_level: str | None) -> None:
    left, level_col, about_col = st.columns([6, 1.8, 1.1])
    with left:
        st.markdown(
            '<div class="vf-brand"><span class="vf-brand-mark">VF</span><span>Vocab Filter</span></div>',
            unsafe_allow_html=True,
        )
    with level_col:
        level_label = f"LEVEL {user_level}" if user_level else "LEVEL 待设置"
        if st.button(level_label, use_container_width=True, key="topbar_level"):
            if not open_dialog("英语水平设置", render_level_settings, width="medium"):
                st.session_state.level_settings_inline_open = True
                st.rerun()
    with about_col:
        if st.button("关于", use_container_width=True):
            if not open_dialog("关于", render_about_panel, width="small"):
                st.session_state.about_inline_open = True
                st.rerun()
    st.markdown('<div class="vf-top-rule"></div>', unsafe_allow_html=True)


def render_level_picker(user_level: str | None, level_note: str, *, centered: bool = False) -> None:
    if user_level:
        st.markdown('<div class="vf-section-label">LEVEL</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="vf-setting-summary"><span class="vf-level-pill">当前 <strong>{user_level}</strong></span></div>',
            unsafe_allow_html=True,
        )
        st.caption(level_note)
    else:
        if centered:
            st.markdown(
                """
<div class="vf-level-onboarding-copy">
  <div class="vf-section-label">LEVEL</div>
  <h3>先确定你的英语水平</h3>
  <p>可以先做一次快速测评，也可以直接按 CEFR 或考试成绩设置。</p>
</div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="vf-section-label">LEVEL</div>', unsafe_allow_html=True)
            st.info("先选择一个英语水平；不想测评也可以直接按考试成绩或 CEFR 等级设置。")

    level_options = ["快速测评结果", "手动选择 CEFR", "考试成绩换算"] if centered else ["手动选择 CEFR", "考试成绩换算", "快速测评结果"]
    current_source = st.session_state.get("level_source")
    if "analysis_level_source_choice" not in st.session_state:
        default_source = "快速测评结果" if centered else "手动选择 CEFR"
        st.session_state.analysis_level_source_choice = current_source if current_source in level_options else default_source
    level_source = st.radio(
        "确定方式",
        level_options,
        key="analysis_level_source_choice",
        horizontal=centered,
    )

    if level_source == "手动选择 CEFR":
        selected = st.session_state.get("manual_cefr") or user_level or "B1"
        st.selectbox(
            "CEFR 等级",
            CEFR_OPTIONS,
            index=CEFR_OPTIONS.index(selected) if selected in CEFR_OPTIONS else 2,
            key="analysis_manual_cefr_choice",
        )
        if st.button("应用水平", type="primary", use_container_width=True, key="analysis_apply_manual_level"):
            st.session_state.manual_cefr = st.session_state.analysis_manual_cefr_choice
            st.session_state.level_source = "手动选择 CEFR"
            st.session_state.analysis_cefr_level = st.session_state.manual_cefr
            st.session_state.placement_notice = f"已应用手动等级：{st.session_state.manual_cefr}。"
            save_user_profile()
            st.rerun()

    elif level_source == "考试成绩换算":
        exam_options = ["CET-4 四级", "CET-6 六级", "IELTS 雅思", "TOEFL iBT 托福", "Duolingo English Test", "高考英语"]
        current_exam = st.session_state.get("analysis_exam_type") or st.session_state.get("exam_type", "CET-6 六级")
        exam = st.selectbox(
            "考试类型",
            exam_options,
            index=exam_options.index(current_exam) if current_exam in exam_options else 1,
            key="analysis_exam_type",
        )
        if st.session_state.get("_analysis_exam_score_for") != exam:
            saved_score = st.session_state.get("exam_score") if st.session_state.get("exam_type") == exam else None
            st.session_state.analysis_exam_score = saved_score if saved_score is not None else default_exam_score(exam)
            st.session_state._analysis_exam_score_for = exam
        score = render_exam_score_input(exam, key="analysis_exam_score")
        estimate = score_to_cefr(exam, score)
        st.markdown(
            f'<div class="vf-setting-summary"><span class="vf-level-pill">换算 <strong>{estimate.level}</strong></span></div>',
            unsafe_allow_html=True,
        )
        st.caption(estimate.note)
        if st.button("应用水平", type="primary", use_container_width=True, key="analysis_apply_exam_level"):
            st.session_state.exam_type = exam
            st.session_state.exam_score = st.session_state.analysis_exam_score
            st.session_state.level_source = "考试成绩换算"
            st.session_state.analysis_cefr_level = estimate.level
            st.session_state.placement_notice = f"已按 {exam} {st.session_state.analysis_exam_score:g} 应用：{estimate.level}。"
            save_user_profile()
            st.rerun()

    else:
        measured = st.session_state.get("measured_level")
        if measured:
            st.markdown(
                f'<div class="vf-setting-summary"><span class="vf-level-pill">测评结果 <strong>{measured}</strong></span></div>',
                unsafe_allow_html=True,
            )
            if st.button("应用测评结果", type="primary", use_container_width=True, key="analysis_apply_measured_level"):
                st.session_state.level_source = "快速测评结果"
                st.session_state.analysis_cefr_level = measured
                st.session_state.placement_notice = f"已应用测评结果：{measured}。"
                save_user_profile()
                st.rerun()
        if st.button("开始快速测评", use_container_width=True, key="analysis_start_placement"):
            if not open_dialog("英语水平测评", render_placement_settings):
                st.session_state.placement_inline_open = True
                st.rerun()


def render_analysis(
    user_level: str | None,
    level_note: str,
    backend: str,
    default_cefr_path: str,
) -> None:
    if st.session_state.placement_notice:
        st.success(st.session_state.placement_notice)
        st.session_state.placement_notice = ""

    _, center_col, _ = st.columns([.12, 5, .12])
    with center_col:
        if user_level is None:
            render_level_picker(user_level, level_note, centered=True)

        st.markdown(
            """
<div class="vf-composer">
  <h2>今天要筛哪段英文？</h2>
</div>
            """,
            unsafe_allow_html=True,
        )
        with st.container(key="composer_shell"):
            st.markdown('<div class="vf-composer-shell-marker"></div>', unsafe_allow_html=True)
            uploaded = st.file_uploader(
                "上传文件",
                type=["txt", "md", "csv"],
                accept_multiple_files=False,
                key="analysis_upload",
                help="支持 txt、md、csv；如果同时上传文件和粘贴文本，会优先分析上传文件。",
                label_visibility="collapsed",
            )
            pasted_text = st.text_area(
                "粘贴文章或词汇表",
                height=170,
                placeholder="粘贴文章、笔记或词表...",
                key="analysis_text",
                label_visibility="collapsed",
            )

            default_analysis_level = user_level if user_level in CEFR_OPTIONS else "B1"
            analysis_level_key = "analysis_cefr_level"
            if st.session_state.get(analysis_level_key) not in CEFR_OPTIONS:
                st.session_state.pop(analysis_level_key, None)
            analyze_label = "重新分析" if st.session_state.get("last_result") else "分析"
            st.markdown('<div class="vf-composer-toolbar-anchor"></div>', unsafe_allow_html=True)
            level_col, analyze_col = st.columns([.55, 2.45], gap="small")
            with level_col:
                level_select_kwargs = {
                    "key": analysis_level_key,
                    "help": "只影响这次文章分析，可以临时切到 A1、B1 等水平查看筛词差异。",
                }
                if analysis_level_key not in st.session_state:
                    level_select_kwargs["index"] = CEFR_OPTIONS.index(default_analysis_level)
                analysis_level = st.selectbox(
                    "分析水平",
                    CEFR_OPTIONS,
                    **level_select_kwargs,
                )
            with analyze_col:
                st.markdown('<div class="vf-composer-action-align"></div>', unsafe_allow_html=True)
                analyze_btn = st.button(analyze_label, type="primary", use_container_width=True, key="analyze_button")

    if analyze_btn:
        if uploaded is None and not pasted_text.strip():
            st.warning("请上传文件或粘贴文本。")
        else:
            content = decode_upload(uploaded) if uploaded is not None else pasted_text
            with st.spinner("正在分析..."):
                result = analyze_content(
                    content,
                    user_level=analysis_level,
                    input_mode="auto",
                    cefr_backend=backend,
                    cefr_csv=default_cefr_path,
                    unknown_path=None,
                )

            st.session_state["last_result"] = result
            st.session_state["last_analysis_level"] = analysis_level
            st.success("分析完成")

    result = st.session_state.get("last_result")
    if not result:
        return

    s = result.summary
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(RESULT_LABELS["target"], s["likely_unknown"])
    c2.metric(RESULT_LABELS["review"], s["borderline"])
    c3.metric(RESULT_LABELS["known"], s["likely_known"])
    c4.metric(RESULT_LABELS["ungraded"], s["ungraded"])
    c5.metric("专有名词", s["proper_nouns"])

    if st.session_state.get("last_analysis_level") and st.session_state.get("last_analysis_level") != analysis_level:
        st.info("分析水平已切换，点击上方“重新分析”可按新水平刷新结果。")

    out1, out2, out3, out4, out5 = st.tabs([
        RESULT_LABELS["target"],
        RESULT_LABELS["review"],
        RESULT_LABELS["known"],
        RESULT_LABELS["ungraded"],
        "专有名词",
    ])
    show_surface = s.get("input_mode") != "words"
    with out1:
        st.caption(CATEGORY_HELP["target"])
        show_table(compact_rows(result.likely_unknown, include_surface=show_surface))
    with out2:
        st.caption(CATEGORY_HELP["review"])
        show_table(compact_rows(result.borderline, include_surface=show_surface))
    with out3:
        st.caption(CATEGORY_HELP["known"])
        show_table(compact_rows(result.likely_known, include_surface=show_surface), height=330)
    with out4:
        st.caption(CATEGORY_HELP["ungraded"])
        show_table(compact_rows(result.ungraded, include_surface=show_surface), height=330)
    with out5:
        st.caption(CATEGORY_HELP["proper"])
        show_table(proper_rows(result.proper_nouns), height=330)

    st.markdown('<div class="vf-export">', unsafe_allow_html=True)
    ec1, ec2, ec3, ec4 = st.columns([1, 1, 1, 1])
    with ec1:
        export_scope = st.selectbox("导出范围", list(RESULT_LABELS.values()))
    with ec2:
        export_detail = st.selectbox("导出内容", EXPORT_DETAIL_OPTIONS)
    with ec3:
        export_fmt = st.selectbox("导出格式", ["Markdown (.md)", "CSV (.csv)"])
    export_rows = get_export_rows(result, export_scope)
    data, filename, mime = get_export_bytes(export_rows, export_scope, export_fmt, export_detail)
    with ec4:
        st.markdown('<div class="vf-export-action-label">导出操作</div>', unsafe_allow_html=True)
        st.download_button("导出", data, file_name=filename, mime=mime, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_placement_settings(*, show_heading: bool = True) -> None:
    if show_heading:
        st.markdown(
            """
<div class="vf-dialog-heading">
  <h2>英语水平</h2>
  <p>完成 30 个词后应用筛词等级。</p>
</div>
        """,
            unsafe_allow_html=True,
        )
    st.markdown('<div class="vf-section-label">PLACEMENT</div>', unsafe_allow_html=True)

    if st.button("换一组词") or "placement_words" not in st.session_state:
        st.session_state.placement_words = sample_test_words(per_level=PLACEMENT_WORDS_PER_LEVEL)

    responses = []
    with st.form("placement_form"):
        for row_start in range(0, len(st.session_state.placement_words), 2):
            cols = st.columns(2)
            for offset, col in enumerate(cols):
                item_index = row_start + offset
                if item_index >= len(st.session_state.placement_words):
                    continue
                item = st.session_state.placement_words[item_index]
                idx = item_index + 1
                with col:
                    answer = st.radio(
                        f"{idx}. {item['word']}",
                        ["认识", "模糊", "不认识"],
                        index=2,
                        horizontal=True,
                        key=f"placement_{idx}_{item['word']}",
                    )
                    responses.append({"word": item["word"], "level": item["level"], "answer": answer})
        submitted = st.form_submit_button("应用结果", type="primary")

    if submitted:
        est = estimate_level(responses)
        st.session_state.measured_level = est["suggested_level"]
        st.session_state.level_source = "快速测评结果"
        st.session_state.level_source_choice = "快速测评结果"
        st.session_state.analysis_cefr_level = est["suggested_level"]
        st.session_state.placement_notice = f"测评完成，已自动应用：{est['suggested_level']}。"
        st.session_state.placement_rates = est["rates"]
        st.session_state.placement_inline_open = False
        st.session_state.level_settings_show_placement = False
        save_user_profile()
        st.rerun()

    if st.session_state.get("placement_rates"):
        st.markdown('<div class="vf-section-label">LAST RESULT</div>', unsafe_allow_html=True)
        rates = st.session_state["placement_rates"]
        display_rates = [{"CEFR": k, "认识率": f"{v:.0%}"} for k, v in rates.items()]
        show_table(display_rates, height=250)


def render_inline_dialog_fallback() -> None:
    if st.session_state.get("placement_inline_open"):
        if st.button("关闭水平测评", key="close_placement_fallback"):
            st.session_state.placement_inline_open = False
            st.rerun()
        render_placement_settings()

    if st.session_state.get("level_settings_inline_open"):
        if st.button("关闭英语水平设置", key="close_level_settings_fallback"):
            st.session_state.level_settings_inline_open = False
            st.rerun()
        render_level_settings()

    if st.session_state.get("about_inline_open"):
        if st.button("关闭关于", key="close_about_fallback"):
            st.session_state.about_inline_open = False
            st.rerun()
        render_about_panel()


init_state()
apply_style()
st.session_state["_dialog_opened_this_run"] = False

user_level, level_mode, level_note = current_level_from_state()
backend, default_cefr_path = cefr_runtime_settings()

render_topbar(user_level)
render_inline_dialog_fallback()

render_analysis(user_level, level_note, backend, default_cefr_path)
