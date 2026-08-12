# Socratic Prompt

## 目标

生成别人在听完你转述后**最可能反问你的英文问题**，以及应对角度。

练的不是「把观点讲出来」，是「被追问时还能接住」。这是谈资和背稿之间的分界线。

产物是 `socratic.json`。

## 输入

- `viewpoints.json`
- `transcript.json`

## 什么是好问题

想象用户在一场晚宴或面试里，刚讲完 2 分钟版复述稿。对面那个人**懂行、不太买账、而且愿意较真**。他会问什么？

好问题的特征：

- **打在论证的软处**，不是问细节。不要问 "when did he say that?"，要问 "what would have to be true for that to hold?"
- **用户答不上来会尴尬**。如果随口就能答，这题没有练习价值。
- **不能靠复述原访谈解决**。需要用户自己有判断。
- **是真的会有人问的**，不是逻辑课练习题。

三种最有杀伤力的追问，尽量各覆盖一些：

1. **反例型**：`But X seems to be doing exactly the opposite and doing fine — how do you square that?`
2. **归因型**：`Isn't that just survivorship bias / a function of them having capital?`
3. **落地型**：`Okay, so what would you actually do differently on Monday morning?`

## 数量

3-6 个。**质量优先。** 三个真能问倒人的，胜过六个泛泛的。

## 字段

- `question_en`：问题本身。写成**真人会说出口的样子**——可以有口语的犹疑和铺垫（"I mean, isn't it also true that…"），不要写成考卷题干。
- `why_hard_zh`：中文说明这题难在哪。一到两句。要具体指出它戳中了哪个薄弱环节，不要写「这题需要深入思考」这种废话。
- `angle_en`：建议的回应**角度**，不是完整答案。

## `angle_en` 的边界

给骨架，不给稿子。

不合格（给了完整答案，用户只会背）：
`You should say that the exception proves the rule because their capital structure allows them to absorb losses that others cannot, and therefore…`

合格（给角度，用户自己填）：
`Concede the counterexample first — don't fight it. Then narrow your claim to the conditions where it holds, and name what makes their situation different. Ending with what would change your mind buys you a lot of credibility.`

要求：
- 说清**怎么组织回应**，而不是回应内容本身
- 30 字符以上
- 允许给一两个可用的英文句型（"That's fair, and I'd narrow it to…"）
- **不要编造事实或数据**让用户拿去当论据

## 输出

只输出 JSON，不要 Markdown 代码块包裹，不要解释文字。写入 `socratic.json`：

```json
{
  "socratic_questions": [
    {
      "question_en": "I mean, isn't that just survivorship bias? We only hear from the teams that made it work.",
      "why_hard_zh": "直接质疑论据的采样方式。如果只会复述原访谈的案例，会被这一问彻底噎住。",
      "angle_en": "Grant the bias openly — arguing against it looks defensive. Then shift the claim from 'this causes success' to 'the absence of this reliably predicts failure', which survivorship bias doesn't undermine. Name one failure case you know of if you have one."
    }
  ]
}
```
