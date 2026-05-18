# vocab-filter

一个规则主导的个人英语词汇过滤器。

它会从英文文章、Markdown 笔记、CSV 或词表里提取词汇，再结合你的 CEFR 水平、词频、CEFR 词库和个人已掌握词表，把词分成更适合学习、复习、跳过或人工判断的几类。

核心判断由本地规则完成，不让 AI 猜“你认不认识这个词”。

---

## 当前状态

- 默认安装已经轻量化：`pip install -e ".[ui]"` 只安装 `streamlit` 和 `pandas`。
- `spacy`、`wordfreq`、`cefrpy` 都是可选增强依赖，不再随 UI 默认安装。
- 不装增强依赖也能运行，只是分词、词频、CEFR 覆盖会更粗。
- UI 当前支持上传/粘贴文本、快速测评、考试成绩换算、手动 CEFR、已掌握词上传、结果导出。
- CLI 支持文章文件和词表文件输入，适合批处理或最小环境验证。

---

## 安装

建议在虚拟环境里安装。Windows PowerShell 示例：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 最小命令行版

只安装项目本身，下载最少：

```bash
pip install -e .
```

验证：

```bash
python -m vocab_filter.cli --text examples/article.txt --level B2 --backend csv --out output
```

### 轻量 UI 版

安装 UI 必需依赖：

```bash
pip install -e ".[ui]"
```

启动：

```bash
streamlit run app.py
```

如果不想让程序尝试导入 spaCy，可以在当前 PowerShell 里启用轻量分词：

```powershell
$env:VOCAB_FILTER_NO_SPACY="1"
streamlit run app.py
```

轻量 UI 的代价：

- 不装 `spacy`：使用正则分词和简单词形还原，专有名词识别会粗一些。
- 不装 `wordfreq`：使用内置粗略词频表，词频判断不如完整库细。
- 不装 `cefrpy`：使用项目自带 `data/cefr_seed.csv`，CEFR 覆盖更小。

### 完整增强版

需要更好的分词、词形还原、词频和 CEFR 覆盖时再安装：

```bash
pip install -e ".[full]"
python -m spacy download en_core_web_sm
```

也可以只给 CLI 增强 NLP 能力：

```bash
pip install -e ".[nlp]"
python -m spacy download en_core_web_sm
```

---

## 启动 UI

```bash
streamlit run app.py
```

使用流程：

1. 先设置英语水平：快速测评、手动 CEFR，或考试成绩换算。
2. 上传 `.txt` / `.md` / `.csv`，或直接粘贴文章、笔记、词表。
3. 选择本次分析使用的 CEFR 水平。
4. 点击“分析”。
5. 在结果页查看分类，或导出 Markdown / CSV。

---

## UI 功能

### 英语水平

支持三种方式：

| 方式 | 说明 |
| --- | --- |
| 快速测评结果 | 每个 CEFR 等级抽样 5 个词，共 30 个词；回答“认识 / 模糊 / 不认识”后给出建议等级 |
| 手动选择 CEFR | 直接选择 A1、A2、B1、B2、C1、C2 |
| 考试成绩换算 | 根据考试成绩粗略换算为筛词等级 |

考试成绩换算目前支持：

| 考试 | 换算范围 |
| --- | --- |
| CET-4 四级 | 低于 425 按 B1；425-549 按 B1；550+ 按 B2 |
| CET-6 六级 | 低于 425 按 B1；425-599 按 B2；600+ 按 C1 |
| IELTS 雅思 | 4.0 以下 A2；4.0-5.0 B1；5.5-6.5 B2；7.0-8.0 C1；8.5-9.0 C2 |
| TOEFL iBT 托福 | 42 以下 A2；42-71 B1；72-94 B2；95-113 C1；114+ C2 |
| Duolingo English Test | 80 以下 A2；80-105 B1；110-125 B2；130-145 C1；150+ C2 |
| 高考英语 | 低于 60% A2；60%-82% B1；较高分段 B2 |

这些规则只用于筛词阈值，不代表正式语言能力认证。

### 个性化词表

UI 当前支持上传“已掌握词”：

- 支持 `.txt` / `.md`。
- 不要求一行一个词，程序会扫描英文单词。
- 以 `#` 开头的整行会被忽略。
- 命中的词会优先归入“已掌握/低优先级词汇”。

CLI 还支持 `--known` 和 `--unknown` 两个文件参数；其中 `--unknown` 可强制把指定词归入待学习方向。

### 结果分类

| 分类 | 含义 |
| --- | --- |
| 待学习词汇 | 高于当前水平、低频，或被个人生词规则强制标记的词 |
| 可选复习词汇 | 接近当前水平边界，可能认识但不稳 |
| 已掌握/低优先级词汇 | 基础词、常见词、低于当前水平的词，或已掌握词表命中的词 |
| 词库未收录词 | CEFR 词库没有收录的词，建议人工判断 |
| 专有名词 | 人名、地名、机构名、产品名等，默认不进入普通背词清单 |

默认展示字段：

```text
词汇 / 原文形式 / CEFR / 中文释义 / 原文句子
```

导出时可以选择：

- 导出范围：单个分类或全部结果。
- 导出内容：仅单词、单词 + 翻译、完整字段。
- 导出格式：Markdown 或 CSV。

---

## 词库和释义

### CEFR 词库

程序有两种 CEFR 来源：

| 后端 | 说明 |
| --- | --- |
| `csv` | 只使用项目自带或指定的 CSV 词库 |
| `auto` / `cefrpy` | 如果安装了 `cefrpy`，优先使用它；不可用时回退到 CSV |

项目自带的 `data/cefr_seed.csv` 是轻量备用词库，覆盖有限。完整增强版会通过 `cefrpy` 使用更大的 CEFR 数据集。

自定义 CEFR CSV 可以在 CLI 中通过 `--cefr` 指定，格式如下：

```csv
word,level
house,A1
ability,A2
academic,B1
abandon,B2
intricate,C1
ubiquitous,C1
```

也可以带中文释义：

```csv
word,level,meaning_zh
intricate,C1,复杂精细的
ubiquitous,C1,无处不在的
```

### 中文释义

中文释义会按优先级读取：

1. `data/ecdict.csv`
2. `data/word_meanings_extra_zh.csv`
3. `data/word_meanings_zh.csv`

`data/ecdict.csv` 可放 ECDICT 的完整离线英汉词典。这个文件通常较大，已在 `.gitignore` 中忽略，不随仓库提交。没有完整词典时，项目自带的小型补充词表会兜底；查不到释义时 UI 会显示“暂无释义”。

---

## 命令行使用

文章输入：

```bash
python -m vocab_filter.cli \
  --text examples/article.txt \
  --level B2 \
  --backend csv \
  --known data/known_words.txt \
  --unknown data/unknown_words.txt \
  --out output
```

单词列表输入：

```bash
python -m vocab_filter.cli \
  --words examples/words.txt \
  --level B2 \
  --backend csv \
  --out output_words
```

可选参数：

```text
--level      用户 CEFR 等级：A1/A2/B1/B2/C1/C2
--cefr       CEFR CSV 路径，默认 data/cefr_seed.csv
--backend    CEFR 后端：auto / cefrpy / csv
--known      已掌握词文件，默认 data/known_words.txt
--unknown    生词文件，默认 data/unknown_words.txt
--out        输出目录
```

输出文件包括：

```text
all_tokens.csv
likely_unknown.csv
borderline.csv
likely_known.csv
ungraded.csv
proper_nouns.csv
likely_unknown.md
borderline.md
ungraded.md
```

---

## 项目结构

```text
vocab-filter/
├── app.py                         # Streamlit UI
├── pyproject.toml                 # 安装配置和可选依赖组
├── requirements-ui.txt            # 轻量 UI 依赖
├── vocab_filter/
│   ├── pipeline.py                # UI 和 CLI 复用的分析流程
│   ├── preprocess.py              # 分词、词形还原、专有名词识别
│   ├── scorer.py                  # 规则评分
│   ├── frequency.py               # wordfreq / fallback 词频
│   ├── lexicon.py                 # cefrpy / CSV CEFR 后端
│   ├── cefr.py                    # CEFR CSV 读取和等级规范化
│   ├── meanings.py                # 中文释义读取
│   ├── level_mapping.py           # 考试成绩到 CEFR 的映射
│   ├── placement.py               # 快速测评
│   ├── export_md.py               # Markdown 导出
│   ├── io_utils.py                # 文件读写工具
│   ├── cli.py                     # 命令行入口
│   └── ui_state.py                # UI 状态辅助逻辑
├── data/
│   ├── cefr_seed.csv              # 轻量 CEFR 备用词库
│   ├── placement_test_words.csv   # 快速测评词表
│   ├── known_words.txt            # 默认已掌握词
│   ├── unknown_words.txt          # 默认生词
│   ├── word_meanings_zh.csv       # 小型中文释义表
│   ├── word_meanings_extra_zh.csv # 额外中文释义表
│   └── ECDICT_LICENSE
├── examples/
│   ├── article.txt
│   └── words.txt
└── tests/
    ├── test_selftest.py
    └── test_ui_state.py
```

本地生成或较大的文件不会随仓库提交：

```text
data/user_profile.json
data/ecdict.csv
output/*.csv
output_words/*.csv
```

---

## 测试

```bash
python -m unittest discover -s tests
```
