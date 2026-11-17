# AI Frontier Research Agent

AI 视频、AI 音乐、世界模型的研究 Agent：项目知识库、人物与论文规范、本地交互工作台，以及每周自动更新的 **行业动态**。

## 使用入口

- [Agent 执行规范](agent.md)：模块、研究方法、证据等级及发布标准。
- [完整 Skill](skills/ai-frontier-research/SKILL.md)：覆盖、交互和本地保存要求。
- [行业动态 HTML](site/index.html)：可下载后直接打开，无外部 JS 依赖。
- [最新周报](reports/latest.md) / [结构化报告](reports/latest.json)。
- [本地研究工作台](workbench/ai-frontier-atlas.html)：原项目的交互 HTML；联网采集用 `workbench/启动工作台.cmd` 启动。

## 运行

Python 3.10+，仅标准库，无必填模型密钥。

```sh
python -m unittest discover -s tests -v
python agent.py
python agent.py --check
```

运行读取 `config/sources.json`，检索过去七天，生成 Markdown、JSON 和可搜索筛选的 HTML。可用 `--now 2026-11-19T09:00:00+08:00` 固定报告时间用于回测。新闻搜索只提供发现线索；自动报告保留来源摘要，不自动宣称已核验事实。

## 每周四发布

工作流 `.github/workflows/weekly.yml` 在 **北京时间周四 09:00（UTC 01:00）** 执行。报告提交到仓库 `reports/` 和 `site/`，也可从 Actions 下载工件。`pages.yml` 随后构建并部署 HTML 到 GitHub Pages；首次需要在 Settings → Pages 中选择 GitHub Actions。不是 GitHub Release。

审核入口：运行 `python build_review.py`，打开 `public/index.html`。这里包含完整 Skill、Agent 规范、交互预览、行业动态、实现缺口和新建仓库发布步骤。构建仅复制公开页面与报告，不复制私人状态。

推送到 GitHub 后，在 Actions 中启用工作流，并允许工作流写入仓库；可选择“Run workflow”首次执行。定时任务仅在默认分支运行，GitHub 调度可能延迟；公开仓库长期没有活动时定时任务可能被停用，需检查 Actions 状态。若启用分支保护阻止机器人推送，需要按仓库策略改为 PR 流程。

## 公开与私人数据

云端仅检索公开来源，发布短摘要和原文链接。`data/`、备注、浏览器登录状态、扩展配对码、API 密钥不发布。X、小红书、公众号不是本项目已验证的云端自动采集源；现有本地扩展只能作为后续开发基础。无登录不表示该平台没有新闻。

`workbench/` 中的项目档案为既有资料快照，未经本次全面事实复核；周报生成不会自动认证或更改其版本和人物信息。完整覆盖与关系图谱要求见 Skill，当前自动化不是这些功能全部完成的证明。

## 配置

`config/sources.json` 支持 `rss`、`github`、`hf`。来源可限定领域、标记 `discovery` 或 `primary`。新闻条目保留原始来源等级和核验状态。发布时间缺失的内容单列为待核验；所有源失效会失败退出，已有报告保留。

可在支持读取 `AGENTS.md` 的编码 Agent 中使用：

> 按 agent.md 完成本周研究，检查国内外创业项目遗漏，核验人物与论文关系；运行周报流水线，补充有证据的分析并报告覆盖缺口。仅将公开材料提交到 GitHub。
