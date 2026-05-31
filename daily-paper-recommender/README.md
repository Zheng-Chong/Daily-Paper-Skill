# Daily Paper Recommender

This skill recommends daily arXiv papers from a research profile built from your local Zotero library.

It uses Zotero's local API to read recently modified papers, infers your research directions from paper titles, fetches new arXiv papers since the last recommendation, and returns a Top 10 list with recommendation reasons.

## Install

Copy the skill folder into Codex's skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R /Users/[your-username]/Documents/Daily-Paper-Skill/daily-paper-recommender ~/.codex/skills/
```

Restart Codex after installing so it can discover the skill.

## Enable Zotero Local API

Open Zotero and go to:

```text
Settings / Preferences -> Advanced
```

Enable:

```text
Allow other applications on this computer to communicate with Zotero
```

Zotero shows the local API root as:

```text
http://localhost:23119/api/
```

In Codex, prefer the numeric loopback address:

```text
http://127.0.0.1:23119/api/
```

You can verify Zotero from a terminal:

```bash
curl "http://127.0.0.1:23119/api/users/0/items?sort=dateModified&direction=desc&limit=3&format=json"
```

## Use In Codex

Example prompt:

```text
[$daily-paper-recommender] 用我最近 60 天修改过的 Zotero 论文建立画像，然后推荐今天的 arXiv Top 10。
```

Another example:

```text
[$daily-paper-recommender] 用我最近修改过的 80 篇论文作为用户画像，推荐从上次推荐到现在的新 arXiv 论文。
```

## Run Manually

From this project:

```bash
python3 daily-paper-recommender/scripts/recommend_daily_papers.py --profile-days 60 --top-n 10
```

Or use a fixed number of recently modified Zotero papers:

```bash
python3 daily-paper-recommender/scripts/recommend_daily_papers.py --profile-papers 80 --top-n 10
```

If Codex cannot reach Zotero through `localhost`, force `127.0.0.1`:

```bash
python3 daily-paper-recommender/scripts/recommend_daily_papers.py \
  --profile-papers 80 \
  --top-n 10 \
  --zotero-api-root http://127.0.0.1:23119/api
```

Dry run without writing recommendation history:

```bash
python3 daily-paper-recommender/scripts/recommend_daily_papers.py --profile-days 60 --no-write-state
```

## State

The skill stores state in:

```text
daily-paper-recommender/resources/state.json
```

It records:

- when the research profile was last updated;
- how the profile was built;
- when recommendations were last generated;
- arXiv IDs that have already been recommended.

The profile is refreshed when it is missing or older than one week. Recommendation candidates are fetched from the previous recommendation time to the current run.

## Troubleshooting

If the script says `zotero_unavailable`:

1. Confirm Zotero is open.
2. Confirm local application communication is enabled in Zotero settings.
3. Test the API with `curl` using `127.0.0.1`.
4. Rerun with `--zotero-api-root http://127.0.0.1:23119/api`.

If the script returns too few recommendations, increase the window by deleting or editing `last_recommended_at` in `resources/state.json`, or run with an explicit `--since` timestamp.

Example:

```bash
python3 daily-paper-recommender/scripts/recommend_daily_papers.py \
  --profile-papers 80 \
  --since 2026-05-24T00:00:00Z
```
