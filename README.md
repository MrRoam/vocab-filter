# vocab-filter

一个**规则主导**的个人英语词汇过滤器。

目标：

> 上传英文文章、Markdown 笔记、CSV 或词表；  
> 根据考试成绩 / 快速测评 / CEFR 等级确定你的筛词水平；  
> 结合 CEFR、词频和个人词库，输出更值得优先处理的词汇。

核心判断由规则完成，不让 AI 猜“你认不认识这个词”。

---

## 安装

推荐安装 UI 版本：

```bash
pip install -e ".[ui]"
python -m spacy download en_core_web_sm
```

如果只想运行命令行最小版：

```bash
pip install -e .
```

---

## 启动 UI

```bash
streamlit run app.py
```

打开浏览器后：

1. 在左侧选择水平确定方式：考试成绩、快速测评结果，或手动 CEFR。
2. CEFR 词库多数情况下保持“自动”。
3. 拖入 `.txt` / `.md` / `.csv`，或直接粘贴文本。
4. 点击“开始分析”。
5. 在“导出结果”中选择导出范围和格式。

---

## UI 结果分类

| UI 名称  | 含义                   |
| ------ | -------------------- |
| 建议学习词汇 | 系统判断更值得优先处理的词        |
| 待确认词汇  | 接近当前水平，建议人工确认        |
| 暂不处理词汇 | 基础词、已掌握词或暂不建议投入时间的词  |
| 专有名词   | 人名、地名、机构名等，不计入普通词汇学习 |

UI 默认只显示必要字段：

```text
词汇 / 原文形式 / CEFR / 中文释义 / 原文句子
```

更细的内部字段，例如 lemma、POS、Zipf、reason，保留在底层 CSV / 调试逻辑中，不再默认展示在 UI 里。

---

## 水平设置

支持三种方式：

### 1. 考试成绩换算

当前内置近似规则：

| 考试       | 分数段     | 筛词等级 |
| -------- | -------:| ---- |
| 四级       | 425-549 | B1   |
| 四级       | 550+    | B2   |
| 六级       | 425-599 | B2   |
| 六级       | 600+    | C1   |
| 雅思       | 5.5-6.5 | B2   |
| 雅思       | 7.0-8.0 | C1   |
| 托福 iBT   | 72-94   | B2   |
| 托福 iBT   | 95-113  | C1   |
| Duolingo | 110-125 | B2   |
| Duolingo | 130-145 | C1   |

这些规则只用于筛词阈值，不代表正式语言能力认证。

### 2. 快速测评

提供三种完整度：

```text
简洁版：约 2 分钟
标准版：约 5 分钟
完整版：约 8-10 分钟
```

测评完成后，UI 会自动把建议 CEFR 等级应用到左侧设置。

### 3. 手动 CEFR

直接选择 A1-C2。

---

## CEFR 词库来源

UI 中提供三种简化选项：

| 选项         | 含义                                          |
| ---------- | ------------------------------------------- |
| 自动选择       | 优先使用本地 `cefrpy`，不可用时退回备用 CSV                |
| 本地 CEFR 词库 | 使用本机已安装的 `cefrpy` CEFR 数据，不可用时退回备用 CSV      |
| 上传 CEFR 词库 | 使用你上传的 CSV，格式为 `word,level`，可选 `meaning_zh` |

推荐依赖是 `cefrpy`，它封装了 Maximax67/Words-CEFR-Dataset。
`cefrpy` 和项目备用 CEFR 表负责“词汇等级”，并不等同于完整双语词典。
项目另带 `data/word_meanings_zh.csv`，用于给结果补充中文释义；查不到释义时 UI 会显示“暂无释义”。

自定义 CSV 格式：

```csv
word,level
house,A1
ability,A2
academic,B1
abandon,B2
intricate,C1
ubiquitous,C1
```

带中文释义的自定义 CSV：

```csv
word,level,meaning_zh
intricate,C1,复杂精细的
ubiquitous,C1,无处不在的
```

--- 

## 高级个性化

侧栏里的“已掌握词”和“需复习词”不是 CEFR 词库，而是个人覆盖规则：

| 文件   | 作用                   |
| ---- | -------------------- |
| 已掌握词 | 即使等级较高，也优先归入“暂不处理词汇” |
| 需复习词 | 即使等级较低，也优先归入“建议学习词汇” |

支持 `.txt` / `.md`。解析时会扫描英文单词，不要求一行一个；空格、换行、Markdown 列表都可以。以 `#` 开头的整行会被忽略。

---

## 命令行使用

文章输入：

```bash
python -m vocab_filter.cli \
  --text examples/article.txt \
  --level B2 \
  --backend auto \
  --known data/known_words.txt \
  --unknown data/unknown_words.txt \
  --out output
```

单词列表输入：

```bash
python -m vocab_filter.cli \
  --words examples/words.txt \
  --level B2 \
  --backend auto \
  --out output_words
```

---

## 项目结构

```text
vocab-filter/
├── app.py                         # Streamlit UI
├── vocab_filter/
│   ├── pipeline.py                # UI 和 CLI 复用的分析流程
│   ├── lexicon.py                 # cefrpy / CSV CEFR 后端
│   ├── level_mapping.py           # 考试成绩到 CEFR 的映射
│   ├── export_md.py               # Markdown 导出
│   ├── placement.py               # 词汇水平测评
│   ├── cli.py                     # 命令行入口
│   ├── preprocess.py              # 分词、词形还原、专有名词识别
│   ├── scorer.py                  # 规则评分
│   └── frequency.py               # wordfreq / fallback 词频
├── data/
│   ├── cefr_seed.csv              # fallback demo CEFR CSV
│   ├── placement_test_words.csv   # 测评词表
│   ├── known_words.txt
│   └── unknown_words.txt
└── examples/
    ├── article.txt
    └── words.txt
```
