# Daily Paper Skill / 每日论文推荐 Skill

这个仓库包含一个 Codex skill：它会基于本地 Zotero 文献库生成研究画像，并推荐每日 arXiv 论文。

This repository contains a Codex skill that builds a research profile from your local Zotero library and recommends daily arXiv papers.

Skill 目录 / Skill folder:

```text
daily-paper-recommender/
```

完整安装和使用说明见 / See the full installation and usage guide:

```text
daily-paper-recommender/README.md
```

## 从本仓库安装 / Install From This Repository

克隆仓库后，把 skill 目录复制到 Codex 的 skills 目录：

After cloning this repository, copy the skill folder into Codex's skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R daily-paper-recommender ~/.codex/skills/
```

安装后重启 Codex，让它重新发现 skill。

Restart Codex after installing so it can discover the skill.

## Zotero 要求 / Zotero Requirement

打开 Zotero 并启用本地应用通信：

Open Zotero and enable local application communication:

```text
Settings / Preferences -> Advanced -> Allow other applications on this computer to communicate with Zotero
```

该 skill 默认使用：

The skill uses this endpoint by default:

```text
http://127.0.0.1:23119/api/users/0/items
```

## 示例 Prompt / Example Prompt

```text
[$daily-paper-recommender] 用我最近 60 天修改过的 Zotero 论文建立画像，然后推荐今天的 arXiv Top 10。
```

```text
[$daily-paper-recommender] Build my profile from Zotero papers modified in the last 60 days, then recommend today's arXiv Top 10.
```
