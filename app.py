from __future__ import annotations

import io
import tempfile
from pathlib import Path

import streamlit as st

from vocab_filter.export_md import rows_to_markdown
from vocab_filter.level_mapping import FRIENDLY_LEVELS, to_cefr_level
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

st.title("📘 Vocab Filter")
st.caption("规则主导的个人英语生词过滤器：上传文章或词表 → 选择水平 → 输出大概率不熟的词。")


def decode_upload(uploaded_file) -> str:
    raw = uploaded_file.getvalue()
    for enc in ["utf-8", "utf-8-sig", "gbk", "latin-1"]:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def rows_to_csv_bytes(rows: list[dict]) -> bytes:
    if pd is not None:
        return pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")
    import csv
    output = io.StringIO()
    if not rows:
        return b""
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


def show_table(rows: list[dict], height: int = 420) -> None:
    if pd is not None:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, height=height)
    else:
        st.write(rows)


with st.sidebar:
    st.header("设置")
    level_label = st.selectbox(
        "你的英语水平",
        list(FRIENDLY_LEVELS.keys()),
        index=list(FRIENDLY_LEVELS.keys()).index("六级 425-500：B2"),
    )
    user_level = to_cefr_level(level_label)
    st.info(f"当前筛词等级：{user_level}")

    backend_label = st.selectbox(
        "CEFR 词库来源",
        [
            "自动：优先 cefrpy，失败则用 CSV",
            "cefrpy：Maximax67/Words-CEFR-Dataset",
            "CSV：只用本地/上传词库",
        ],
    )
    backend = {
        "自动：优先 cefrpy，失败则用 CSV": "auto",
        "cefrpy：Maximax67/Words-CEFR-Dataset": "cefrpy",
        "CSV：只用本地/上传词库": "csv",
    }[backend_label]

    st.caption("推荐安装：`pip install -e .[ui]`，会包含 cefrpy、wordfreq、spaCy、Streamlit。")

    custom_cefr = st.file_uploader("可选：上传自定义 CEFR CSV（word,level）", type=["csv"], key="cefr_csv")
    known_file = st.file_uploader("可选：上传 known_words.txt", type=["txt"], key="known")
    unknown_file = st.file_uploader("可选：上传 unknown_words.txt", type=["txt"], key="unknown")


tab_analyze, tab_test, tab_help = st.tabs(["文件分析", "5 分钟测词汇水平", "说明"])

with tab_analyze:
    col_left, col_right = st.columns([1.2, 0.8])
    with col_left:
        uploaded = st.file_uploader(
            "拖入 TXT / MD / CSV 文件",
            type=["txt", "md", "csv"],
            accept_multiple_files=False,
        )
        pasted_text = st.text_area("或者直接粘贴英文文章/词表", height=180, placeholder="Paste an article or a word list here...")
        input_mode = st.radio("输入类型", ["自动判断", "文章", "词表"], horizontal=True)
        analyze_btn = st.button("Analyze", type="primary", use_container_width=True)

    with col_right:
        st.markdown("### 输出说明")
        st.write("- **大概率不熟**：优先复习或导出到 MD")
        st.write("- **边界词**：建议人工确认")
        st.write("- **大概率已知**：默认跳过")
        st.write("- **专有名词**：不计入普通生词")

    if analyze_btn:
        if uploaded is None and not pasted_text.strip():
            st.warning("请上传文件或粘贴文本。")
        else:
            content = decode_upload(uploaded) if uploaded is not None else pasted_text
            mode = {"自动判断": "auto", "文章": "text", "词表": "words"}[input_mode]

            cefr_path = "data/cefr_seed.csv"
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
                known_extra = {w.strip().lower() for w in decode_upload(known_file).splitlines() if w.strip() and not w.startswith("#")}
            if unknown_file is not None:
                unknown_extra = {w.strip().lower() for w in decode_upload(unknown_file).splitlines() if w.strip() and not w.startswith("#")}

            with st.spinner("正在分析..."):
                result = analyze_content(
                    content,
                    user_level=user_level,
                    input_mode=mode,
                    cefr_backend=backend,
                    cefr_csv=cefr_path,
                    known_words_extra=known_extra,
                    unknown_words_extra=unknown_extra,
                )

            st.success("分析完成")
            s = result.summary
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("大概率不熟", s["likely_unknown"])
            c2.metric("边界词", s["borderline"])
            c3.metric("大概率已知", s["likely_known"])
            c4.metric("专有名词", s["proper_nouns"])
            c5.metric("CEFR 后端", s["cefr_backend"])

            out1, out2, out3, out4 = st.tabs(["大概率不熟", "边界词", "大概率已知", "专有名词"])
            with out1:
                show_table(result.likely_unknown)
                st.download_button("下载 likely_unknown.md", result.likely_unknown_md.encode("utf-8"), "likely_unknown.md", "text/markdown")
                st.download_button("下载 likely_unknown.csv", rows_to_csv_bytes(result.likely_unknown), "likely_unknown.csv", "text/csv")
            with out2:
                show_table(result.borderline)
                st.download_button("下载 borderline.md", result.borderline_md.encode("utf-8"), "borderline.md", "text/markdown")
                st.download_button("下载 borderline.csv", rows_to_csv_bytes(result.borderline), "borderline.csv", "text/csv")
            with out3:
                show_table(result.likely_known)
            with out4:
                show_table(result.proper_nouns)

            st.download_button("下载 all_results.csv", rows_to_csv_bytes(result.all_rows), "all_results.csv", "text/csv", use_container_width=True)

with tab_test:
    st.markdown("### 5 分钟快速词汇水平测试")
    st.write("每个词只判断：认识 / 模糊 / 不认识。系统会按 A1-C2 各层级的认识率估计你的筛词等级。")

    per_level = st.slider("每个等级抽几个词", min_value=4, max_value=12, value=6)
    if "placement_words" not in st.session_state or st.button("重新抽题"):
        st.session_state.placement_words = sample_test_words(per_level=per_level)

    responses = []
    with st.form("placement_form"):
        for idx, item in enumerate(st.session_state.placement_words, start=1):
            answer = st.radio(
                f"{idx}. {item['word']}",
                ["认识", "模糊", "不认识"],
                index=2,
                horizontal=True,
                key=f"placement_{idx}_{item['word']}",
            )
            responses.append({"word": item["word"], "level": item["level"], "answer": answer})
        submitted = st.form_submit_button("计算我的词汇水平", type="primary")

    if submitted:
        est = estimate_level(responses)
        st.success(f"建议筛词等级：{est['suggested_level']}")
        st.write("各等级认识率：")
        st.json(est["rates"])
        st.info("你可以回到左侧设置，选择对应的自定义等级；之后版本可以把这个结果自动写入配置文件。")

with tab_help:
    st.markdown("""
### 推荐用法

1. 先安装完整依赖：

```bash
pip install -e ".[ui]"
python -m spacy download en_core_web_sm
```

2. 运行 UI：

```bash
streamlit run app.py
```

3. 上传 `.txt` / `.md` / `.csv`，选择四级/六级/雅思水平，点击 Analyze。

### 关于 CEFR 词库

默认推荐使用 `cefrpy`，它封装了 Maximax67/Words-CEFR-Dataset。项目仍然保留 CSV 后备词库；如果 `cefrpy` 没装上，程序会自动退回 `data/cefr_seed.csv`。

### 为什么还要 known_words / unknown_words？

因为你的领域词汇会明显偏科。比如 robotics、reinforcement、trajectory 对很多人难，但你可能很熟。把它们放入 known_words 后，系统会直接跳过。
""")
