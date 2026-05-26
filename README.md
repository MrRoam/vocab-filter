# vocab-filter

从英文文章里筛出更值得优先学习的单词。

你可以上传文章、笔记或词表，选择自己的英语水平，然后导出待学习词汇。

## 演示

[查看演示视频](docs/assets/vocab-filter-demo.mp4)

---

## 快速开始

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[full]"
python -m spacy download en_core_web_sm
streamlit run app.py
```

中文释义词库随仓库提供在 `data/ecdict.csv`。新电脑先 `git clone` 或 `git pull` 到最新版，再按上面的命令安装依赖即可。

打开浏览器后：

1. 设置英语水平：快速测评、手动 CEFR，或考试成绩换算。
2. 上传 `.txt` / `.md` / `.csv`，或直接粘贴英文内容。
3. 点击“分析”。
4. 查看待学习词、可复习词、低优先级词、未收录词和专有名词。
5. 按需导出 Markdown 或 CSV。
