# vocab-filter

一个**规则主导**的个人英语生词过滤器。

目标：

> 输入一篇英文文章，或一批英文单词；  
> 根据你的英语水平、CEFR 词汇等级、词频、个人已知词库；  
> 输出你**大概率不认识**的词、边界词、专有名词。

它不是让 AI 猜“你认不认识这个词”。核心判断由规则完成。

---

## 第一性原理

人是否认识一个词，不能只靠 AI 猜。一个词是否可能陌生，主要取决于：

1. 词本身的等级：CEFR A1-C2
2. 真实英语中的常见程度：frequency
3. 你的个人历史标记：known / unknown

所以本项目第一版只做筛词，不做复杂学习系统。AI 以后只放在后处理：解释上下文、生成例句、生成 Anki 卡片。

---

## 安装

最小安装：

```bash
pip install -e .
```

推荐安装，可复用更多开源能力：

```bash
pip install -e ".[full]"
python -m spacy download en_core_web_sm
```

说明：

- 安装了 `wordfreq`：用真实词频。
- 没安装 `wordfreq`：用项目内置 fallback 词频表，仍可运行。
- 安装了 `spaCy + en_core_web_sm`：文章分词、词形还原、专有名词识别更准。
- 没安装 spaCy 模型：自动退回正则分词 + 保守词形还原。

---

## 使用

文章输入：

```bash
python -m vocab_filter.cli \
  --text examples/article.txt \
  --level B2 \
  --known data/known_words.txt \
  --unknown data/unknown_words.txt \
  --out output
```

单词列表输入：

```bash
python -m vocab_filter.cli \
  --words examples/words.txt \
  --level B2 \
  --out output_words
```

输出：

```text
output/
├── likely_unknown.csv
├── borderline.csv
├── likely_known.csv
├── proper_nouns.csv
└── all_tokens.csv
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

## 替换完整 CEFR 词库

内置 `data/cefr_seed.csv` 只是 demo 词库。真实使用时，建议替换成完整 CEFR 数据集，例如 Words-CEFR-Dataset 或你自己整理的 Oxford 3000/5000 CSV。

CSV 至少需要：

```csv
word,level
intricate,C1
derive,B2
house,A1
```

运行：

```bash
python -m vocab_filter.cli --text examples/article.txt --cefr data/your_cefr.csv --level B2
```

---

## 后续最小扩展

1. 加完整 CEFR 词库
2. 加 60 词分层小测，估计用户水平
3. 导出 Anki / 欧路词典生词本格式
4. 给筛出的词调用 AI 生成上下文解释
