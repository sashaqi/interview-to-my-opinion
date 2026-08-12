# Expressions Prompt

## 目标

提取被访谈人用过的**地道表达和可迁移句型**，用来替换用户现有的中式表达。

产物是 `expressions.json`。

## 输入

`transcript.json`。

## 筛选标准

用户是能读懂英文、但说出来像翻译腔的中文母语者。所以取舍标准只有一条：

> **这个表达，用户「看得懂但想不起来用」吗？**

看得懂 + 想不起来用 = 收。
看不懂 = 太生僻，不收（学了也用不上）。
张口就来 = 太基础，不收。

具体地：

**收**
- 地道动词短语：`walk back a position`、`take a swing at`、`get a read on`
- 专业搭配：`compounding advantage`、`load-bearing assumption`、`surface area`
- 可迁移句型：`The way I'd frame it is…`、`What that buys you is…`、`I keep coming back to…`
- 精确的领域术语（只在它真的帮助理解这期内容时）

**不收**
- `very important`、`I think that`、`for example` 这类谁都会的
- 只在这期话题里成立、换个场景就用不上的
- 生僻到说出来会让对方愣住的
- 语法结构本身（"过去完成时"不是表达）

## 数量

5-20 条。**按文字稿的实际密度给，不要凑数。**

一期干货密集的访谈可能有 18 条，一期泛泛而谈的可能只有 6 条。给出 6 条真货，比凑够 20 条掺水的有用得多。

扫完整份文字稿再选，不要在前三分之一就把名额用光。

## 字段

- `text`：表达本身。**保持原文用词**，只做最小的形态归一（把 `he walked back his position` 记成 `walk back a position`）。
- `type`：
  - `idiom` — 习语、比喻性表达
  - `collocation` — 固定搭配，必须整块记
  - `sentence_frame` — 可套用的句型骨架，用 `…` 标出可替换的位置
  - `term` — 领域术语
- `meaning_zh`：中文释义。说清**什么场合用**，不只是字面对应。
- `source_sentence`：原文中含有该表达的完整句子。**必须真实存在于文字稿中**，校验器会核对。允许去掉口头禅和补标点，不允许改写。
- `your_example`：**面向用户自身语境**的新例句。

## `your_example` 的要求

这是这份产物里最容易做砸的字段。

不合格：`The company walked back its position on remote work.`
——正确，但和原句几乎一样，用户读完没有任何「我可以这么用」的感觉。

合格：`I had to walk back my estimate once I saw how the data was actually collected.`
——放进了「我」的工作场景，用户能直接改两个词就说出去。

要求：
- 用第一人称或用户可能真的会谈到的场景（工作、技术判断、职业选择、投资、育儿）
- 不复述原句的话题
- 一句话，20 词以内，说得出口
- 不编造具体数字和事实

## 输出

只输出 JSON，不要 Markdown 代码块包裹，不要解释文字。写入 `expressions.json`：

```json
{
  "expressions": [
    {
      "text": "load-bearing assumption",
      "type": "collocation",
      "meaning_zh": "支撑整个论证的关键假设，一旦不成立结论就垮。用于拆解别人的方案时。",
      "source_sentence": "The load-bearing assumption there is that evaluation is cheap.",
      "your_example": "Before I commit to this plan, I want to know which assumption is load-bearing."
    }
  ]
}
```
