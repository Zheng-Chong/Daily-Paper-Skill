# Daily Paper Recommender / 每日论文推荐器

这个 skill 会根据你的本地 Zotero 文献库生成研究画像，并推荐每日 arXiv 论文。

This skill recommends daily arXiv papers from a research profile built from your local Zotero library.

它会通过 Zotero Local API 读取最近修改过的论文标题，推断你的研究方向，从上次推荐时间开始抓取新的 arXiv 论文，并返回带推荐理由的 Top 10 列表。

It uses Zotero's local API to read recently modified paper titles, infer your research directions, fetch new arXiv papers since the last recommendation, and return a Top 10 list with recommendation reasons.

## 安装 / Install

把 skill 目录复制到 Codex 的 skills 目录：

Copy the skill folder into Codex's skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R /Users/[your-username]/Documents/Daily-Paper-Skill/daily-paper-recommender ~/.codex/skills/
```

安装后重启 Codex，让它重新发现这个 skill。

Restart Codex after installing so it can discover the skill.

## 启用 Zotero Local API / Enable Zotero Local API

打开 Zotero，进入：

Open Zotero and go to:

```text
Settings / Preferences -> Advanced
```

启用：

Enable:

```text
Allow other applications on this computer to communicate with Zotero
```

Zotero 设置页显示的本地 API 根地址是：

Zotero shows the local API root as:

```text
http://localhost:23119/api/
```

在 Codex 中，建议优先使用数字回环地址：

In Codex, prefer the numeric loopback address:

```text
http://127.0.0.1:23119/api/
```

可以用下面的命令验证 Zotero API 是否可访问：

You can verify Zotero from a terminal:

```bash
curl "http://127.0.0.1:23119/api/users/0/items?sort=dateModified&direction=desc&limit=3&format=json"
```

## 在 Codex 中使用 / Use In Codex

示例 prompt：

Example prompt:

```text
[$daily-paper-recommender] 用我最近 60 天修改过的 Zotero 论文建立画像，然后推荐今天的 arXiv Top 10。
```

另一个示例：

Another example:

```text
[$daily-paper-recommender] 用我最近修改过的 80 篇论文作为用户画像，推荐从上次推荐到现在的新 arXiv 论文。
```

English examples:

```text
[$daily-paper-recommender] Build my profile from Zotero papers modified in the last 60 days, then recommend today's arXiv Top 10.
```

```text
[$daily-paper-recommender] Use my 80 most recently modified Zotero papers as my profile and recommend new arXiv papers since the last recommendation.
```

## 手动运行 / Run Manually

在本项目目录运行：

From this project:

```bash
python3 daily-paper-recommender/scripts/recommend_daily_papers.py --profile-days 60 --top-n 10
```

或者使用最近修改过的固定篇数论文：

Or use a fixed number of recently modified Zotero papers:

```bash
python3 daily-paper-recommender/scripts/recommend_daily_papers.py --profile-papers 80 --top-n 10
```

如果 Codex 无法通过 `localhost` 连接 Zotero，强制使用 `127.0.0.1`：

If Codex cannot reach Zotero through `localhost`, force `127.0.0.1`:

```bash
python3 daily-paper-recommender/scripts/recommend_daily_papers.py \
  --profile-papers 80 \
  --top-n 10 \
  --zotero-api-root http://127.0.0.1:23119/api
```

不写入推荐历史的 dry run：

Dry run without writing recommendation history:

```bash
python3 daily-paper-recommender/scripts/recommend_daily_papers.py --profile-days 60 --no-write-state
```

## 状态文件 / State

该 skill 会把状态保存在：

The skill stores state in:

```text
daily-paper-recommender/resources/state.json
```

状态文件记录：

It records:

- 研究画像上次更新时间 / when the research profile was last updated;
- 画像构建方式 / how the profile was built;
- 上次生成推荐的时间 / when recommendations were last generated;
- 已经推荐过的 arXiv ID / arXiv IDs that have already been recommended.

当画像不存在或超过一周未更新时，skill 会刷新画像。候选论文范围是从上次推荐时间到当前运行时间。

The profile is refreshed when it is missing or older than one week. Recommendation candidates are fetched from the previous recommendation time to the current run.

## 排错 / Troubleshooting

如果脚本返回 `zotero_unavailable`：

If the script says `zotero_unavailable`:

1. 确认 Zotero 已打开。 / Confirm Zotero is open.
2. 确认 Zotero 设置中已启用本地应用通信。 / Confirm local application communication is enabled in Zotero settings.
3. 用 `127.0.0.1` 和 `curl` 测试 API。 / Test the API with `curl` using `127.0.0.1`.
4. 使用 `--zotero-api-root http://127.0.0.1:23119/api` 重新运行。 / Rerun with `--zotero-api-root http://127.0.0.1:23119/api`.

如果推荐数量太少，可以删除或编辑 `resources/state.json` 里的 `last_recommended_at`，或者使用显式的 `--since` 时间戳扩大检索窗口。

If the script returns too few recommendations, increase the window by deleting or editing `last_recommended_at` in `resources/state.json`, or run with an explicit `--since` timestamp.

示例 / Example:

```bash
python3 daily-paper-recommender/scripts/recommend_daily_papers.py \
  --profile-papers 80 \
  --since 2026-05-24T00:00:00Z
```
