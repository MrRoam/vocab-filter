# vocab-filter

一个**规则主导**的个人英语生词过滤器。

目标：

> 输入一篇英文文章，或一批英文单词；  
> 根据你的英语水平、CEFR 词汇等级、词频、个人已知词库；  
> 输出你**大概率不认识**的词、边界词、专有名词，并可下载 Markdown。

它不是让 AI 猜“你认不认识这个词”。核心判断由规则完成。

---

## 第一性原理

人是否认识一个词，不能只靠 AI 猜。一个词是否可能陌生，主要取决于：

1. 词本身的等级：CEFR A1-C2
2. 真实英语中的常见程度：frequency
3. 你的个人历史标记：known / unknown

所以本项目第一版只做筛词，不做复杂学习系统。AI 以后只放在后处理：解释上下文、生成例句、生成 Anki 卡片。

---

## 推荐安装

```bash
pip install -e ".[ui]"
python -m spacy download en_core_web_sm
```

如果只想跑命令行最小版：

```bash
pip install -e .
```

说明：

- 安装了 `cefrpy`：优先使用 Maximax67/Words-CEFR-Dataset 进行 A1-C2 查询。
- 安装了 `wordfreq`：用真实词频。
- 安装了 `spaCy + en_core_web_sm`：文章分词、词形还原、专有名词识别更准。
- 没装这些增强依赖：仍然可以用内置 fallback 逻辑运行。

---

## UI 使用

启动本地网页：

```bash
streamlit run app.py
```

然后在浏览器里：

1. 上传 `.txt` / `.md` / `.csv`
2. 选择你的水平：四级、六级、雅思，或自定义 A1-C2
3. 选择 CEFR 后端：推荐 `自动：优先 cefrpy，失败则用 CSV`
4. 点击 `Analyze`
5. 下载 `likely_unknown.md` 或 CSV

UI 还包含一个 **5 分钟快速词汇水平测试**，会让你对一组词标记“认识 / 模糊 / 不认识”，然后估计建议筛词等级。

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

输出：

```text
output/
├── likely_unknown.csv
├── likely_unknown.md
├── borderline.csv
├── borderline.md
├── likely_known.csv
├── proper_nouns.csv
└── all_tokens.csv
```

---

## CEFR 词库来源

推荐使用：

```text
cefrpy / Maximax67/Words-CEFR-Dataset
```

代码里已经封装了 `cefrpy` 后端。如果安装失败，程序会自动回退到本地 CSV。

本地 CSV 格式仍然支持：

```csv
word,level
house,A1
ability,A2
academic,B1
abandon,B2
intricate,C1
ubiquitous,C1
```

运行时可以指定：

```bash
python -m vocab_filter.cli --text examples/article.txt --backend csv --cefr data/your_cefr.csv --level B2
```

---

## 规则

个人词库优先级最高：

```text
known_words.txt   -> 直接判为 likely_known
unknown_words.txt -> 直接判为 likely_unknown
```

然后看 CEFR：

```text
A1/A2/B1 低于 B2 用户水平 -> 大概率认识
B2 接近用户水平          -> 边界词
C1/C2 高于用户水平       -> 大概率不认识
```

再用词频修正：

```text
Zipf >= 5.0  降低陌生概率
Zipf >= 4.0  稍微降低陌生概率
Zipf < 3.0   提高陌生概率
```

最终分类：

```text
score < 40       likely_known
40 <= score < 65 borderline
score >= 65      likely_unknown
```

---

## 项目结构

```text
vocab-filter/
├── app.py                         # Streamlit UI
├── vocab_filter/
│   ├── pipeline.py                # UI 和 CLI 复用的分析流程
│   ├── lexicon.py                 # cefrpy / CSV CEFR 后端
│   ├── export_md.py               # Markdown 导出
│   ├── placement.py               # 5 分钟水平测试
│   ├── cli.py                     # 命令行入口
│   ├── preprocess.py              # 分词、词形还原、专有名词识别
│   ├── scorer.py                  # 规则评分
│   └── frequency.py               # wordfreq / fallback 词频
├── data/
│   ├── cefr_seed.csv              # fallback demo CEFR CSV
│   ├── placement_test_words.csv   # 快速水平测试词
│   ├── known_words.txt
│   └── unknown_words.txt
└── examples/
    ├── article.txt
    └── words.txt
```

---

## 下一步

1. 把测试结果写入本地配置文件，UI 自动记住你的等级。
2. 支持把 unknown_words 导出到 Anki / 欧路词典格式。
3. 给 likely_unknown.md 添加 AI 生成的上下文释义和例句。
