# Daily Paper Recommender / 每日论文推荐

基于本地 Zotero 文献库构建研究画像，并在 Codex 中推荐每日新增的 arXiv 论文。

Build a research profile from your local Zotero library and receive daily arXiv recommendations in Codex.

## 功能 / Features

- 从 Zotero 最近修改的论文中推断研究方向和关键词；
- 从上次成功推荐的时间开始检索新论文，避免重复推荐；
- 输出带摘要、相关性理由和链接的中文 Top 10；
- 支持手动运行，也支持 Codex 每日自动化。

The skill infers your research interests from Zotero, finds newly added arXiv papers, avoids repeated recommendations, and returns a ranked Top 10 with summaries and reasons.

Skill 源码和完整排错说明位于 [`daily-paper-recommender/`](daily-paper-recommender/README.md)。

## 安装到 Codex / Install In Codex

将 skill 安装到用户级 skills 目录，使其可在任意 Codex 项目和自动化中使用：

Install the skill at user scope so it is available to every Codex project and automation:

```bash
git clone https://github.com/Zheng-Chong/Daily-Paper-Skill.git
cd Daily-Paper-Skill
mkdir -p ~/.agents/skills
cp -R daily-paper-recommender ~/.agents/skills/
```

Codex 通常会自动发现 skill。如果 `$daily-paper-recommender` 没有出现在 skill 选择器中，请重启 Codex。

Codex normally detects skill changes automatically. Restart Codex if `$daily-paper-recommender` does not appear in the skill picker.

更新已安装版本：

```bash
rm -rf ~/.agents/skills/daily-paper-recommender
cp -R daily-paper-recommender ~/.agents/skills/
```

## 首次运行 / First Run

创建自动化之前，先在普通 Codex 对话中手动运行一次，以确认 Zotero 可访问并初始化研究画像：

Before scheduling the automation, run the skill once in a regular Codex thread to verify Zotero access and initialize your profile:

```text
$daily-paper-recommender
用我最近修改过的 80 篇 Zotero 论文建立研究画像，并推荐从过去 24 小时到现在的新 arXiv 论文 Top 10。用中文输出。
```

该 skill 会尝试自动启用 Zotero Local API，并优先访问：

```text
http://127.0.0.1:23119/api/
```

如果首次运行失败，请确认 Zotero 已安装并至少启动过一次。详细排错步骤见 [`daily-paper-recommender/README.md`](daily-paper-recommender/README.md)。

## 加入 Codex 自动化 / Add A Codex Automation

每日论文推荐应创建为**独立自动化（standalone automation）**：每次运行都是独立任务，推荐结果会出现在 Codex 的 **Triage** 收件箱中。

Daily recommendations work best as a **standalone automation**. Each run starts independently and reports its results in the Codex **Triage** inbox.

在 Codex App 的普通对话中发送下面的请求，即可让 Codex 创建自动化：

```text
创建一个独立自动化，每天上午 8:30（Asia/Shanghai）运行。

自动化任务：
$daily-paper-recommender
使用最近修改过的 80 篇 Zotero 论文维护我的研究画像，推荐从上次成功推荐到现在新增的 arXiv 论文 Top 10。用中文输出每篇论文的标题、作者、arXiv 分类、链接、简短摘要和与我研究画像相关的具体推荐理由。如果 Zotero 或 arXiv 不可用，报告明确原因，不要编造推荐。
```

也可以打开 Codex App 侧边栏的 **Automations**，新建一个每日运行的独立自动化，并将上面的“自动化任务”作为 prompt。首次创建后，建议立即测试一次并检查输出。

You can also create a daily standalone task from **Automations** in the Codex App sidebar and use the automation task above as its prompt. Test the first run before relying on the schedule.

### 自动化运行条件 / Automation Requirements

- 计划运行时，电脑必须开机，Codex App 必须保持运行；
- Zotero 必须已安装并至少启动过一次，自动化需要访问本机 Zotero Local API；
- 自动化需要网络访问 arXiv，并需要写入 skill 的 `resources/state.json`；
- 请检查 Codex 的 sandbox 设置。只读或仅 workspace-write 模式可能阻止网络、本机应用访问或用户级 skill 状态写入；
- 自动化按无人值守方式运行，授予 full access 前请评估安全风险。

At run time, the computer and Codex App must be running. The automation also needs access to Zotero's local API, the arXiv network endpoint, and the skill's state file. Review Codex sandbox permissions carefully before enabling unattended full access.

## 手动使用 / Manual Usage

在 Codex 中显式调用：

```text
$daily-paper-recommender
使用最近修改过的 80 篇 Zotero 论文作为研究画像，推荐从上次推荐到现在的新 arXiv 论文 Top 10。
```

或直接在仓库根目录运行脚本：

```bash
python3 daily-paper-recommender/scripts/recommend_daily_papers.py \
  --profile-papers 80 \
  --top-n 10
```

不写入推荐历史的 dry run：

```bash
python3 daily-paper-recommender/scripts/recommend_daily_papers.py \
  --profile-papers 80 \
  --top-n 10 \
  --no-write-state
```

## 状态与去重 / State And Deduplication

skill 使用 `resources/state.json` 保存研究画像更新时间、上次成功推荐时间和已推荐的 arXiv ID。画像超过 7 天时会刷新，成功推荐过的论文默认不会重复出现。

The skill stores profile freshness, the last successful recommendation time, and previously recommended arXiv IDs in `resources/state.json`.
