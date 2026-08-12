# interview to my opinion

把访谈变成**你能开口讲出来的东西**。

输入一个 YouTube 访谈或播客，产出一组 Obsidian 笔记：被访谈人的观点、每个观点的 30 秒和 2 分钟英文复述稿、他用过的地道表达、以及别人可能反问你的问题。

目标不是记住这期节目，是能在饭桌上把它讲出来，并且被追问时还能接住。

## 它不是什么

- 不是摘要工具。摘要让你「知道」，这个工具让你「说得出」。
- 不是单词本。提取的是可迁移的表达和句型，不是生词。
- 不下载音频，不做语音转写。只从字幕和官方文字稿提取。

## 快速开始

```bash
uv sync --extra dev
cp .env.example .env   # 填入你的 vault 路径
uv run itmo doctor
```

跑一期访谈：

```bash
uv run itmo fetch "https://www.youtube.com/watch?v=..."
```

然后在 Claude Code 里说「用 interview-to-my-opinion 处理这个链接」，Skill 会接管后面的分析、校验和写入。

## 四个阶段

```
YouTube / 播客 RSS / 本地文字稿
    ↓  itmo fetch      取字幕，归一化成带时间戳的段落
    ↓  Claude 分析      读 skill/prompts/ 下四个 prompt，产出四份 JSON
    ↓  itmo build      合并 + 严格校验（引文必须真实存在于原文）
    ↓  itmo publish    渲染并写入 Obsidian vault
```

阶段之间靠文件衔接，可以单独重跑。复述稿不满意就只重跑 retelling，不用重新抓字幕。

## 产物

**主笔记** `06-Interviews/YYYY-MM-DD <标题>.md`
核心主张、观点索引（双链 + 回跳原视频的时间戳）、关键表达表格、苏格拉底追问卡、我的观点栏。

**观点原子笔记** `06-Interviews/Viewpoints/<观点标题>.md`
每个观点一篇：Claim、他的论证、原文引证、30 秒复述、2 分钟复述、反方视角、我的印证栏。

## 两个设计决定

**用户写的内容永不被覆盖。** 笔记分生成区和用户区，重跑只替换 `<!-- itmo:generated:* -->` 之间的部分。你在「我的观点」里写的字、改过的 `status`、自己加的 frontmatter 字段和章节，都逐字保留。标记损坏时程序拒绝写入而不是猜测合并。

**引文不能编造。** 每一条 `evidence_quote` 和 `source_sentence` 都要能在文字稿中找到，校验器用词级覆盖率核对（允许去掉口头禅和补标点，不允许改写或拼接）。核不过就整份产物拒收，不写 vault。

## 命令

```bash
uv run itmo doctor                                    # 环境自检
uv run itmo fetch <URL> [--episode 关键词]            # 采集文字稿
uv run itmo fetch --transcript-file <路径>            # 用现成文字稿
uv run itmo build --transcript X --fragments Y        # 合并校验
uv run itmo publish --transcript X --analysis Y       # 写入 vault
uv run itmo publish ... --out-dir preview             # 先预览不入库
uv run itmo publish ... --dry-run                     # 只看会写哪些文件
uv run pytest                                         # 测试
```

## 已知边界

- **播客覆盖面窄。** 只支持 RSS 里带 `<podcast:transcript>` 的节目，多数播客没有。拿不到文字稿时用 `--transcript-file` 自己喂一份。
- **字幕没有说话人标签。** 区分主持人和被访谈人靠内容推断。每个观点都带 `speaker_confidence`，低于阈值的会在笔记里标「⚠️ 归属待确认」。引用前值得回听确认。
- **yt-dlp 会遇到 429。** 字幕语言已收窄到 `en,en-orig,en-US,en-GB` 并串行下载，仍触发就等几分钟。不要放宽 `ITMO_SUB_LANGS`。
- **vault 在 iCloud。** 文件可能被逐出本地，`itmo doctor` 会检查。

## License

MIT，见 [LICENSE](LICENSE)。

## 致谢

分层架构参考了 [english-podcast-learning-agent](https://github.com/chenhanyue228-rgb/english-podcast-learning-agent)：Skill 负责语言判断、Python 负责编排与校验、外部系统存知识。本项目把发布目标从 Notion 换成 Obsidian，把学习重心从词汇表达换成观点提炼与复述，并重做了采集层以支持 YouTube。
