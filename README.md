# Daily Paper Skill

This repository contains a Codex skill for daily arXiv paper recommendations based on a local Zotero research profile.

Skill folder:

```text
daily-paper-recommender/
```

See the skill README for installation and usage:

```text
daily-paper-recommender/README.md
```

## Install From This Repository

After cloning this repository, copy the skill into Codex's skill directory:

```bash
mkdir -p ~/.codex/skills
cp -R daily-paper-recommender ~/.codex/skills/
```

Restart Codex after installing.

## Zotero Requirement

Open Zotero and enable:

```text
Settings / Preferences -> Advanced -> Allow other applications on this computer to communicate with Zotero
```

The skill uses:

```text
http://127.0.0.1:23119/api/users/0/items
```

## Example Prompt

```text
[$daily-paper-recommender] 用我最近 60 天修改过的 Zotero 论文建立画像，然后推荐今天的 arXiv Top 10。
```
