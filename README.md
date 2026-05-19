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

## 中文释义词库

中文释义主要来自 `data/ecdict.csv`。这个文件现在已经提交到 git，所以新电脑只要先 `git clone` 或 `git pull` 到最新版，就会带上完整中文释义词库。

`pip install -e ".[ui]"` 和 `pip install -e ".[full]"` 都不会单独下载词库；它们只负责安装 Python 依赖。区别是：

- `.[ui]`：安装运行网页界面需要的轻量依赖。
- `.[full]`：额外安装 spaCy、wordfreq、cefrpy，让分词、词形还原、词频和 CEFR 覆盖更好。

也就是说，中文释义是否完整，关键看项目目录里有没有 `data/ecdict.csv`，不是看装的是 `.[ui]` 还是 `.[full]`。

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
