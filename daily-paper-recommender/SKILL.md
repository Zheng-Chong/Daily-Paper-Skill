---
name: daily-paper-recommender
description: Build or refresh a user's research profile from the local Zotero API, infer relevant arXiv categories, fetch papers added since the last recommendation, and return a daily Top 10 with recommendation reasons. Use when the user asks for daily paper recommendations, arXiv recommendations, Zotero-based research profiling, or incremental literature push summaries.
---

# Daily Paper Recommender

## Workflow

Use `scripts/recommend_daily_papers.py` as the reliable execution path. It reads the local Zotero API, maintains state in `resources/state.json`, fetches arXiv papers, and emits JSON that can be summarized in the conversation.

1. Check whether Zotero's local API is reachable.
2. If it is not reachable, guide the user to open Zotero and enable local API access:
   - Zotero 7: Settings/Preferences -> Advanced -> enable local application communication/local API.
   - The settings page advertises the API root as `http://localhost:23119/api/`, but Codex execution environments may need `http://127.0.0.1:23119/api`.
   - Personal library item reads use `http://127.0.0.1:23119/api/users/0/items?...`.
   - Keep Zotero running while the recommendation command runs.
3. Ask the user how to build the profile when the script needs a refresh:
   - recent modified days, such as 30 or 90 days; or
   - recent modified paper count, such as 50 or 100 papers.
4. Run the script with the chosen profile scope.
5. Read the JSON output and respond with a Chinese Top 10 list: title, authors, arXiv category, link, concise abstract summary, and a specific recommendation reason tied to the user's profile.

## State Rules

Store persistent state under `resources/state.json` in this skill folder unless the user asks for another state directory.

- Refresh the Zotero-derived profile when `profile_updated_at` is missing or older than 7 days.
- Fetch recommendation candidates from `last_recommended_at` to the current conversation time.
- If `last_recommended_at` is missing, default to the last 24 hours unless the user requests a wider window.
- Update `last_recommended_at` only after recommendations are successfully presented.
- Keep `recommended_arxiv_ids` so repeated runs do not re-recommend the same paper unless the user explicitly asks.

## Commands

Profile by recently modified days:

```bash
python3 scripts/recommend_daily_papers.py --profile-days 60 --top-n 10
```

Profile by recently modified paper count:

```bash
python3 scripts/recommend_daily_papers.py --profile-papers 80 --top-n 10
```

Dry run without writing recommendation history:

```bash
python3 scripts/recommend_daily_papers.py --profile-days 60 --no-write-state
```

Use `--state-dir <path>` if running outside the skill folder or when the user wants project-local state.

If Zotero works in the user's terminal but Codex reports it unavailable, force the numeric loopback address:

```bash
python3 scripts/recommend_daily_papers.py --profile-papers 80 --zotero-api-root http://127.0.0.1:23119/api
```

## Interpreting Output

The script emits JSON with these top-level keys:

- `status`: `ok` or `zotero_unavailable`.
- `needs_profile_input`: true when the profile is stale and neither `--profile-days` nor `--profile-papers` was provided.
- `profile`: inferred directions, keywords, source titles, and candidate arXiv categories.
- `window`: recommendation start and end timestamps.
- `recommendations`: ranked arXiv papers with score signals and reasons.
- `next_action`: user-facing guidance when more input or Zotero setup is required.

When `status` is `zotero_unavailable`, do not invent recommendations from an old profile unless the user approves using cached state.

## References

Read `references/zotero-arxiv-notes.md` when adjusting API behavior, category mappings, or state semantics.
