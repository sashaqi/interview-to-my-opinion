# Retelling Prompt

## 目标

为每个观点写**两个长度的英文口播稿**，让用户能照着念、背下来，然后在真实对话里说出来。

产物是 `retellings.json`。

## 输入

- `viewpoints.json`（上一步的产物）
- `transcript.json`（需要细节时回查原文）

## 核心约束：这是「说」的稿子，不是「写」的稿子

用户的目标是把知识变成谈资。所以每一句都要**能用嘴说出来**。

具体意味着：

- **短句。** 一句话超过 25 词就拆开。书面语的从句套从句在口语里会卡住。
- **用第一人称转述，不是学术引用。** 写 "The way I'd put it is…"、"What struck me was…"，不要写 "The interviewee posits that…"。用户是在跟人聊天，不是在做文献综述。
- **可以有口语连接词**：so、and here's the thing、but、actually、the interesting part is。这些正是中文母语者最缺的「英语流畅感」来源。
- **避免书面高频词**：furthermore、moreover、in conclusion、it is worth noting that。这些一说出口就像在念稿。
- **不要生僻词。** 目标是用户能真的说出来，不是展示词汇量。宁可用 `figure out` 也不要用 `elucidate`。

## `retelling_30s`

70-90 词。电梯版。

结构：**结论先行 → 一句为什么 → 一句所以呢**

这是用户在别人问 "what have you been reading lately?" 时能立刻甩出来的版本。它必须自足——听的人没看过这期访谈也能听懂。

不要在 30 秒版里塞背景介绍。直接给判断。

## `retelling_2min`

250-320 词。展开版。

结构：**钩子 → 观点 → 他的论证 → 一个具体例子或数字 → 反方 → 你的落点**

- 「钩子」是一句能让人抬头的话，通常是反常识的那面。
- 「他的论证」要讲清机制，不是重复结论。
- 「具体例子」优先用原访谈里的，没有就用一个通用场景，**不要编造数字或事实**。
- 「反方」用一句话承认这个观点的边界。这是可信度的来源——只讲一面的人听起来像在推销。
- 「你的落点」是一句开放式的收尾，把话头递回去，让对话能继续。比如 "I'm still not sure where I land on this — have you seen it play out differently?"

2 分钟版要能被拆着用：用户可能只讲前一半就被打断，所以前一半必须自己也成立。

## 两个版本的关系

不是「短版是长版的截断」。它们是两个独立成篇的稿子，服务两个不同场景：

- 30 秒：社交场合、被顺口一问、需要留下印象
- 2 分钟：深聊、面试、播客、需要展示思考深度

允许两版用同一个核心句，但论证路径应该不同。

## 事实纪律

- 不得引入 `viewpoints.json` 和 `transcript.json` 之外的事实、数字、人名、公司名。
- 不确定的地方就说得模糊些（"a lot of teams"），不要为了具体而编造（"73% of teams"）。
- 允许你自己的过渡语和框架性表述，因为那是「用户的转述」而不是「被访谈人的主张」。

## 输出

只输出 JSON，不要 Markdown 代码块包裹，不要解释文字。每一项的 `id` 必须与 `viewpoints.json` 中的 `id` 一一对应，不多不少。写入 `retellings.json`：

```json
{
  "retellings": [
    {
      "id": "autonomy-slider",
      "retelling_30s": "...",
      "retelling_2min": "..."
    }
  ]
}
```
