# Viewpoints Prompt

## 目标

从访谈文字稿中提取**被访谈人的观点**。不是摘要，不是知识点罗列，是「这个人主张什么，以及他凭什么这么主张」。

产物是 `viewpoints.json`。

## 输入

`transcript.json`，形状：

```json
{
  "meta": { "title": "...", "channel": "...", "description": "...", "source_url": "..." },
  "has_timestamps": true,
  "paragraphs": [{ "index": 0, "timestamp": "1:23", "text": "..." }]
}
```

## 第一步：确定说话人

**字幕不含说话人标签。** 文字稿是一条没有标注的文本流，你必须自己判断哪些话是被访谈人说的。

判据，按可靠性排序：

1. **外部给定**：用户通过 `--interviewee` 明确指定了姓名 → `attribution: "stated"`，置信度 0.95 以上。
2. **文字稿内的明确线索**：主持人报出全名（"please welcome…"、"joining me today is…"）、被访谈人自我介绍。→ `attribution: "stated"`。
3. **角色推断**：
   - 主持人问、被访谈人答。连续的疑问句、"tell me about…"、"so you're saying…"、"how did you…" 属于主持人。
   - 长段落的第一人称经历叙述（"when I was at…"、"what we built…"）属于被访谈人。
   - 主持人会做串场和总结（"that's fascinating"、"let's switch gears"），被访谈人不会。
   - → `attribution: "inferred"`，置信度按线索强度给 0.6-0.9。

**不确定就如实标低置信度，不要为了让输出好看而假装确定。** 低于 0.7 的观点会在笔记里被标注「归属待确认」，这是正常的、有用的。

姓名从 `meta.title`、`meta.channel`、`meta.description` 中找。**找不到就写 `Unknown speaker`，绝不编造姓名。**

## 第二步：提取观点

一个「观点」必须满足：

- 是**主张**，不是事实陈述。"GPT-4 came out in 2023" 不是观点；"the bottleneck was never compute, it was evaluation" 是观点。
- 是**这个人的**判断，不是他转述的行业共识。
- 有**可争议性**。如果没人会反对，它就不值得成为谈资。
- 你能想象在饭桌上把它讲给别人听。

提取 4-10 个。宁少勿滥——两个真正锋利的观点，胜过八个正确的废话。

覆盖整份文字稿，不要只取开头。访谈的后半段往往才是被访谈人放松下来说真话的地方。

## 第三步：为每个观点填字段

- `id`：小写连字符短标识，如 `evaluation-is-the-bottleneck`。跨次运行应尽量稳定。
- `title_en`：观点短标题，5-80 字符。**这会成为 Obsidian 文件名**，所以要具体、可检索，不要用 "On AI" 这种。
- `title_zh`：中文短标题，2-40 字。
- `claim_en`：一句英文断言。读完这句就知道他主张什么。
- `reasoning_en`：他的论据或机制。回答「他凭什么这么认为」。不少于 40 字符，说清推理链条而不是复述结论。
- `evidence_quote`：**原文引证**。
  - 必须是文字稿里真实出现的话。校验器会逐条核对，编造会导致整个产物被拒。
  - 允许去掉 "uh"、"you know" 这类口头禅和修正重复，允许补标点。
  - **不允许改写、意译、拼接不相邻的两段话。**
  - 长度控制在 15-60 词，取最锋利的那一句。
- `paragraph_index`：引文所在段落的 `index`，用于生成回跳原视频的时间戳链接。
- `speaker` / `attribution` / `speaker_confidence`：见第一步。
- `counterpoint_en`：反方视角。这个观点最站不住的地方在哪，或者什么情况下它会失效。**这不是敷衍的免责声明**——它是让用户在被追问时还能接住的弹药。
- `tags`：最多 5 个小写连字符标签。
- `retelling_30s` / `retelling_2min` 这一步**留空不填**，由 retelling prompt 负责。

## 第四步：填 meta

- `interviewee` / `interviewer`：姓名，未知分别写 `Unknown speaker` 和空字符串。
- `thesis_en`：把所有观点收敛成一句英文核心主张。这是整期访谈的「如果只能记住一句话」。
- `thesis_zh`：同一主张的中文表述。不是逐字翻译，是用中文说清楚。
- `domain_tags`：1-5 个小写连字符领域标签。

## 输出

只输出 JSON，不要 Markdown 代码块包裹，不要任何解释文字。写入 `viewpoints.json`：

```json
{
  "meta": {
    "interviewee": "Andrej Karpathy",
    "interviewer": "Stephanie Zhan",
    "thesis_en": "...",
    "thesis_zh": "...",
    "domain_tags": ["ai", "software-engineering"]
  },
  "viewpoints": [
    {
      "id": "autonomy-slider",
      "title_en": "Agents need an autonomy slider, not full autonomy",
      "title_zh": "智能体需要的是自主度滑块",
      "claim_en": "...",
      "reasoning_en": "...",
      "evidence_quote": "...",
      "paragraph_index": 7,
      "speaker": "Andrej Karpathy",
      "attribution": "inferred",
      "speaker_confidence": 0.88,
      "counterpoint_en": "...",
      "tags": ["agents", "tooling"]
    }
  ]
}
```

## 拒绝清单

出现以下情况，不要把它当作观点：

- 主持人的提问或串场
- 被访谈人转述的他人观点（除非他明确表示认同并加了自己的判断）
- 纯事实、纯履历、纯产品介绍
- 正确但无信息量的话（"AI will change everything"）
- 你无法在文字稿里找到支撑引文的任何主张
