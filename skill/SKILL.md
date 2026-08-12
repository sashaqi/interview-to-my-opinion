---
name: interview-to-my-opinion
description: 把 YouTube 访谈或播客转成 Obsidian 笔记——提取被访谈人的观点，生成英文分层复述稿、关键表达、苏格拉底追问卡，用于把他人的知识变成自己能开口说的谈资。当用户给出访谈链接、说「做成访谈笔记」「提取观点」「我想练着讲这个」时使用。
---

# Interview to My Opinion

## 这个 Skill 做什么

输入一个访谈，输出一套让用户**能开口把它讲出来**的 Obsidian 笔记。

不是摘要工具，不是单词本。目标是把别人的观点变成用户自己的谈资：他能在饭桌上讲出来，被追问时还能接住。

## 何时使用

用户给出 YouTube 链接、播客 RSS 地址或本地文字稿，并且意图是学习/复述/提炼观点时。触发说法包括：

- 「帮我把这个访谈做成笔记」
- 「提取一下这个人的观点」
- 「我想练着用英文讲这个」
- 直接粘贴一个访谈链接

## 何时不用

- 用户只想要一份摘要或翻译 → 直接做，不要跑这套流程
- 内容不是访谈（纯讲座、教程、新闻播报）→ 观点提取会很勉强，先问用户是否仍要继续
- 用户在做与学习无关的开发任务

## 关键约束（先说清楚，避免中途卡住）

**只从字幕/文字稿提取，不下载音频、不做语音转写。** 这意味着：

- YouTube：绝大多数访谈有字幕，直接可用
- 播客：只有 RSS 里带 `<podcast:transcript>` 标签的才行，多数不行
- 拿不到文字稿时：告诉用户用 `--transcript-file` 喂一份，不要试图绕开

**YouTube 字幕不含说话人标签。** 区分主持人和被访谈人靠内容推断，必须如实标注置信度。

## 工作流程

在本项目根目录下执行。所有命令用 `uv run`。

### 第 0 步：首次使用时自检

```bash
uv run itmo doctor
```

有 FAIL 项先修。没有 `.env` 就从 `.env.example` 复制一份。

### 第 1 步：采集文字稿

```bash
uv run itmo fetch "<URL>"
```

播客 RSS 可加 `--episode "关键词"` 选单集。本地文字稿用 `--transcript-file <路径>`。

成功后会打印 transcript.json 的路径，记下来，后面每步都要用。

如果这一步失败：
- 没有英文字幕 → 告诉用户，并说明可以用 `--transcript-file`
- HTTP 429 → 等几分钟重试，不要连续重跑
- 不要自己想办法下载音频，那不在 v1 范围内

### 第 2 步：读文字稿，做四份分析

把 transcript.json 读进来（`paragraphs` 数组是分析单位，每段带 `index` 和 `timestamp`）。

依次执行四个 prompt，各产出一个 JSON 文件到同一个片段目录（建议 `data/fragments/<名字>/`）：

| 顺序 | Prompt | 产物 |
| --- | --- | --- |
| 1 | `skill/prompts/viewpoints_prompt.md` | `viewpoints.json` |
| 2 | `skill/prompts/retelling_prompt.md` | `retellings.json` |
| 3 | `skill/prompts/expressions_prompt.md` | `expressions.json` |
| 4 | `skill/prompts/socratic_prompt.md` | `socratic.json` |

**逐个读 prompt 文件再执行，不要凭记忆写。** 每个 prompt 里的取舍标准才是这个产品的价值所在。

retelling 依赖 viewpoints 的 `id`，必须先做 viewpoints。

用户明确说了被访谈人是谁时，直接用，`attribution` 标 `stated`。

### 第 3 步：合并校验

```bash
uv run itmo build --transcript <transcript.json> --fragments <片段目录>
```

校验器会核对**每一条引文是否真的在文字稿里出现**。报错就是编造了引文或改写过头——回去改对应片段，重跑这一步。不要放宽校验，不要手改 analysis.json 来绕过。

警告（提醒开头的行）不阻断流程，但要如实转达给用户，尤其是「N 条观点归属置信度偏低」。

### 第 4 步：先预览，再入库

**第一次给某个用户做时，先写到项目内目录让他看：**

```bash
uv run itmo publish --transcript <transcript.json> --analysis <analysis.json> --out-dir preview
```

把生成的主笔记读给用户看，确认格式满意后再写进 vault：

```bash
uv run itmo publish --transcript <transcript.json> --analysis <analysis.json>
```

vault 已启用 obsidian-git，写入会进版本控制。

### 第 5 步：向用户汇报

说清楚：提取了几个观点、有没有归属待确认的、笔记写在哪、有没有孤儿笔记需要处理。

## 重跑的安全保证

笔记里 `<!-- itmo:mine:start -->` 和 `<!-- itmo:mine:end -->` 之间是用户写的内容，重跑只替换生成区，用户区逐字保留。frontmatter 里 `status` 和 `tags` 写一次之后也不再覆盖。

如果 publish 报「找不到 itmo 生成区标记」，说明那个文件的标记被删了。**不要删文件重来**，先问用户——那个文件里可能有他写的东西。

## 不要做的事

- 不要为了让输出好看而编造引文。校验器会拦，但更重要的是这会毁掉用户对整套笔记的信任。
- 不要在说话人归属不确定时假装确定。低置信度是有用的信息，笔记里会标出来。
- 不要跳过 prompt 文件直接凭印象生成。
- 不要手动编辑 vault 里的笔记。所有写入走 `itmo publish`。
- 不要自动删除孤儿笔记，只报告。
