from __future__ import annotations

import csv
import io
import tempfile
from pathlib import Path

import streamlit as st

from vocab_filter.export_md import rows_to_markdown
from vocab_filter.level_mapping import CEFR_OPTIONS, score_to_cefr
from vocab_filter.pipeline import analyze_content
from vocab_filter.placement import estimate_level, sample_test_words

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None


st.set_page_config(
    page_title="Vocab Filter",
    page_icon="📘",
    layout="wide",
)


RESULT_LABELS = {
    "target": "建议学习词汇",
    "review": "待确认词汇",
    "known": "暂不处理词汇",
    "proper": "专有名词",
    "all": "全部分析结果",
}

TEST_MODES = {
    "简洁版（约 2 分钟）": 4,
    "标准版（约 5 分钟）": 8,
    "完整版（约 8-10 分钟）": 12,
}

CEFR_SOURCE_OPTIONS = ["自动", "内置词库", "上传词库"]


def init_state() -> None:
    st.session_state.setdefault("level_source", "考试成绩换算")
    st.session_state.setdefault("exam_type", "CET-6 六级")
    st.session_state.setdefault("measured_level", None)
    st.session_state.setdefault("placement_notice", "")
    st.session_state.setdefault("manual_cefr", "B2")


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


def compact_rows(rows: list[dict], include_score: bool = False) -> list[dict]:
    compact: list[dict] = []
    for row in rows:
        item = {
            "词汇": row.get("lemma") or row.get("word") or "",
            "原文形式": row.get("word") or "",
            "CEFR": row.get("cefr") or "未知",
            "原文句子": row.get("sentence") or "",
        }
        if include_score:
            item["系统评分"] = row.get("score", "")
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


def show_table(rows: list[dict], height: int = 420) -> None:
    if pd is not None:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, height=height, hide_index=True)
    else:
        st.write(rows)


def get_export_rows(result, scope: str) -> list[dict]:
    if scope == RESULT_LABELS["target"]:
        return result.likely_unknown
    if scope == RESULT_LABELS["review"]:
        return result.borderline
    if scope == RESULT_LABELS["known"]:
        return result.likely_known
    if scope == RESULT_LABELS["proper"]:
        return result.proper_nouns
    return result.all_rows


def get_export_bytes(rows: list[dict], scope: str, fmt: str) -> tuple[bytes, str, str]:
    slug = {
        RESULT_LABELS["target"]: "target_vocabulary",
        RESULT_LABELS["review"]: "review_candidates",
        RESULT_LABELS["known"]: "excluded_vocabulary",
        RESULT_LABELS["proper"]: "named_entities",
        RESULT_LABELS["all"]: "all_results",
    }[scope]
    if fmt == "Markdown (.md)":
        title = scope
        return rows_to_markdown(rows, title).encode("utf-8"), f"{slug}.md", "text/markdown"
    return rows_to_csv_bytes(rows), f"{slug}.csv", "text/csv"


def level_settings() -> tuple[str, str]:
    st.sidebar.subheader("水平设置")
    level_source = st.sidebar.radio(
        "确定方式",
        ["考试成绩换算", "快速测评结果", "手动选择 CEFR"],
        key="level_source",
    )

    if st.session_state.placement_notice:
        st.sidebar.success(st.session_state.placement_notice)
        st.session_state.placement_notice = ""

    if level_source == "考试成绩换算":
        exam = st.sidebar.selectbox(
            "考试类型",
            ["CET-4 四级", "CET-6 六级", "IELTS 雅思", "TOEFL iBT 托福", "Duolingo English Test", "高考英语"],
            key="exam_type",
        )
        if exam == "IELTS 雅思":
            score = st.sidebar.number_input("成绩", min_value=0.0, max_value=9.0, value=6.0, step=0.5)
        elif exam == "TOEFL iBT 托福":
            score = st.sidebar.number_input("成绩", min_value=0, max_value=120, value=80, step=1)
        elif exam == "Duolingo English Test":
            score = st.sidebar.number_input("成绩", min_value=10, max_value=160, value=115, step=5)
        elif exam == "高考英语":
            score = st.sidebar.number_input("成绩", min_value=0, max_value=150, value=120, step=1)
        else:
            score = st.sidebar.number_input("成绩", min_value=0, max_value=710, value=500, step=1)
        estimate = score_to_cefr(exam, float(score))
        user_level = estimate.level
        st.sidebar.info(f"当前筛词等级：{user_level}\n\n{estimate.note}")
        with st.sidebar.expander("查看换算规则"):
            st.markdown(
                """
- 四级：425-549 → B1；550+ → B2  
- 六级：425-599 → B2；600+ → C1  
- 雅思：5.5-6.5 → B2；7.0-8.0 → C1  
- 托福 iBT：72-94 → B2；95-113 → C1  
- Duolingo：110-125 → B2；130-145 → C1  

这些规则只用于筛词阈值，不代表正式语言能力认证。
"""
            )
        return user_level, "exam"

    if level_source == "快速测评结果":
        measured = st.session_state.get("measured_level")
        if measured:
            st.sidebar.info(f"当前筛词等级：{measured}\n\n来自快速测评。")
            return measured, "placement"
        st.sidebar.warning("还没有测评结果。请到“词汇水平测评”完成一次测试。暂按 B2 处理。")
        return "B2", "placement"

    user_level = st.sidebar.selectbox("CEFR 等级", CEFR_OPTIONS, index=CEFR_OPTIONS.index(st.session_state.get("manual_cefr", "B2")), key="manual_cefr")
    st.sidebar.info(f"当前筛词等级：{user_level}")
    return user_level, "manual"


def cefr_settings() -> tuple[str, str, object | None]:
    st.sidebar.subheader("词库设置")
    source = st.sidebar.selectbox("CEFR 词库", CEFR_SOURCE_OPTIONS)
    uploaded_csv = None

    if source == "自动":
        backend = "auto"
        cefr_path = "data/cefr_seed.csv"
        st.sidebar.caption("自动选择可用词库。")
    elif source == "内置词库":
        backend = "cefrpy"
        cefr_path = "data/cefr_seed.csv"
        st.sidebar.caption("使用项目依赖提供的 A1-C2 词库；不可用时退回本地备用词库。")
    else:
        backend = "csv"
        uploaded_csv = st.sidebar.file_uploader("上传 CSV：word,level", type=["csv"], key="cefr_csv")
        cefr_path = "data/cefr_seed.csv"

    return backend, cefr_path, uploaded_csv


init_state()

st.title("📘 Vocab Filter")
st.caption("上传英文材料，按你的实际水平筛出更值得优先处理的词汇。")

user_level, level_mode = level_settings()
backend, default_cefr_path, custom_cefr = cefr_settings()

with st.sidebar.expander("个人词库（可选）"):
    known_file = st.file_uploader("已掌握词 known_words.txt", type=["txt"], key="known")
    unknown_file = st.file_uploader("需复习词 unknown_words.txt", type=["txt"], key="unknown")

analysis_tab, placement_tab, help_tab = st.tabs(["材料分析", "词汇水平测评", "说明"])

with analysis_tab:
    st.subheader("材料输入")
    uploaded = st.file_uploader(
        "拖入 TXT / MD / CSV 文件",
        type=["txt", "md", "csv"],
        accept_multiple_files=False,
    )
    pasted_text = st.text_area(
        "或者直接粘贴英文文章 / 词表",
        height=180,
        placeholder="Paste an article, notes, or a word list here...",
    )
    analyze_btn = st.button("开始分析", type="primary", use_container_width=True)

    if analyze_btn:
        if uploaded is None and not pasted_text.strip():
            st.warning("请上传文件或粘贴文本。")
        elif backend == "csv" and custom_cefr is None:
            st.warning("你选择了“上传词库”，请上传包含 word,level 两列的 CSV 文件。")
        else:
            content = decode_upload(uploaded) if uploaded is not None else pasted_text
            cefr_path = default_cefr_path
            tmp_paths: list[str] = []
            if custom_cefr is not None:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
                tmp.write(custom_cefr.getvalue())
                tmp.close()
                cefr_path = tmp.name
                tmp_paths.append(tmp.name)

            known_extra = set()
            unknown_extra = set()
            if known_file is not None:
                known_extra = {w.strip().lower() for w in decode_upload(known_file).splitlines() if w.strip() and not w.strip().startswith("#")}
            if unknown_file is not None:
                unknown_extra = {w.strip().lower() for w in decode_upload(unknown_file).splitlines() if w.strip() and not w.strip().startswith("#")}

            with st.spinner("正在分析..."):
                result = analyze_content(
                    content,
                    user_level=user_level,
                    input_mode="auto",
                    cefr_backend=backend,
                    cefr_csv=cefr_path,
                    known_words_extra=known_extra,
                    unknown_words_extra=unknown_extra,
                )

            st.session_state["last_result"] = result
            st.success("分析完成")

    result = st.session_state.get("last_result")
    if result:
        s = result.summary
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("建议学习词汇", s["likely_unknown"])
        c2.metric("待确认词汇", s["borderline"])
        c3.metric("暂不处理词汇", s["likely_known"])
        c4.metric("专有名词", s["proper_nouns"])

        out1, out2, out3, out4 = st.tabs(["建议学习词汇", "待确认词汇", "暂不处理词汇", "专有名词"])
        with out1:
            show_table(compact_rows(result.likely_unknown, include_score=False))
        with out2:
            show_table(compact_rows(result.borderline, include_score=False))
        with out3:
            show_table(compact_rows(result.likely_known, include_score=False), height=320)
        with out4:
            show_table(proper_rows(result.proper_nouns), height=320)

        st.subheader("导出结果")
        ec1, ec2, ec3 = st.columns([1, 1, 1])
        with ec1:
            export_scope = st.selectbox("导出范围", list(RESULT_LABELS.values()))
        with ec2:
            export_fmt = st.selectbox("导出格式", ["Markdown (.md)", "CSV (.csv)"])
        export_rows = get_export_rows(result, export_scope)
        data, filename, mime = get_export_bytes(export_rows, export_scope, export_fmt)
        with ec3:
            st.download_button("导出", data, file_name=filename, mime=mime, use_container_width=True)

with placement_tab:
    st.subheader("词汇水平测评")
    st.write("根据不同 CEFR 层级抽样。你只需要判断：认识 / 模糊 / 不认识。测评完成后，系统会自动把结果应用到左侧水平设置。")

    mode = st.selectbox("测试完整度", list(TEST_MODES.keys()), index=1)
    per_level = TEST_MODES[mode]

    if st.button("开始 / 重新抽题") or "placement_words" not in st.session_state or st.session_state.get("placement_mode") != mode:
        st.session_state.placement_words = sample_test_words(per_level=per_level)
        st.session_state.placement_mode = mode

    responses = []
    with st.form("placement_form"):
        for idx, item in enumerate(st.session_state.placement_words, start=1):
            answer = st.radio(
                f"{idx}. {item['word']}",
                ["认识", "模糊", "不认识"],
                index=2,
                horizontal=True,
                key=f"placement_{mode}_{idx}_{item['word']}",
            )
            responses.append({"word": item["word"], "level": item["level"], "answer": answer})
        submitted = st.form_submit_button("完成测评并应用", type="primary")

    if submitted:
        est = estimate_level(responses)
        st.session_state.measured_level = est["suggested_level"]
        st.session_state.level_source = "快速测评结果"
        st.session_state.placement_notice = f"测评完成，已自动应用：{est['suggested_level']}。"
        st.session_state.placement_rates = est["rates"]
        st.rerun()

    if st.session_state.get("placement_rates"):
        st.markdown("#### 最近一次测评结果")
        rates = st.session_state["placement_rates"]
        display_rates = [{"CEFR": k, "认识率": f"{v:.0%}"} for k, v in rates.items()]
        show_table(display_rates, height=250)

with help_tab:
    st.markdown(
        """
### 使用流程

1. 在左侧通过考试成绩、快速测评或手动选择确定筛词等级。  
2. 选择词库来源。多数情况下保持“自动”即可。  
3. 拖入 `.txt` / `.md` / `.csv`，或直接粘贴文本。  
4. 点击“开始分析”。  
5. 在“建议学习词汇”中查看结果，并在“导出结果”中选择范围和格式。

### 结果分类

- **建议学习词汇**：系统判断更值得优先处理的词。  
- **待确认词汇**：接近当前水平，建议人工确认。  
- **暂不处理词汇**：基础词、已掌握词或暂时不建议投入时间的词。  
- **专有名词**：人名、地名、机构名等，不计入普通词汇学习。

### 关于“原文句子”

原文句子来自你上传或粘贴的材料，用来帮助你在上下文里回看这个词。
"""
    )
