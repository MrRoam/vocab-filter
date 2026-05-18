# vocab-filter

从英文文章里筛出更值得优先学习的单词。

你可以上传文章、笔记或词表，选择自己的英语水平，然后导出待学习词汇。

---

## 快速开始

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[ui]"
streamlit run app.py
```

打开浏览器后：

1. 设置英语水平：快速测评、手动 CEFR，或考试成绩换算。
2. 上传 `.txt` / `.md` / `.csv`，或直接粘贴英文内容。
3. 点击“分析”。
4. 查看待学习词、可复习词、低优先级词、未收录词和专有名词。
5. 按需导出 Markdown 或 CSV。

---

## 轻量安装

默认 UI 安装是轻量版：

```powershell
pip install -e ".[ui]"
```

它只安装 UI 必需依赖，适合新电脑快速跑起来。

如果你不想让程序尝试加载 spaCy，可以这样启动：

```powershell
$env:VOCAB_FILTER_NO_SPACY="1"
streamlit run app.py
```

---

## 完整增强版

如果你希望分词、词形还原、词频和 CEFR 覆盖更好，再安装完整增强依赖：

```powershell
pip install -e ".[full]"
python -m spacy download en_core_web_sm
streamlit run app.py
```

完整增强版下载会更多。日常使用可以先用轻量版。

---

## 命令行用法

只想跑命令行，可以安装最小版：

```powershell
pip install -e .
```

分析文章：

```powershell
python -m vocab_filter.cli --text examples/article.txt --level B2 --backend csv --out output
```

分析词表：

```powershell
python -m vocab_filter.cli --words examples/words.txt --level B2 --backend csv --out output_words
```

常用参数：

```text
--level      A1/A2/B1/B2/C1/C2
--backend    csv / auto / cefrpy
--out        输出目录
```

---

## 中文释义

项目自带一个小型中文释义表。

如果你想使用更完整的离线词典，可以把 ECDICT 的 CSV 文件放到：

```text
data/ecdict.csv
```

这个文件通常比较大，不会提交到仓库。

---

## 测试

```powershell
python -m unittest discover -s tests
```
