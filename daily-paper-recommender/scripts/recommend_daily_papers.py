#!/usr/bin/env python3
"""Recommend recent arXiv papers from a local Zotero-derived profile."""

from __future__ import annotations

import argparse
import configparser
import datetime as dt
import html
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

ZOTERO_API_ROOT = "http://127.0.0.1:23119/api"
ZOTERO_LIBRARY_PREFIX = "users/0"
ZOTERO_LOCAL_API_PREF = "extensions.zotero.httpServer.localAPI.enabled"
ARXIV_BASE = "https://export.arxiv.org/api/query"
ATOM = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "based", "by", "for", "from", "in", "into",
    "is", "it", "its", "learning", "method", "model", "models", "of", "on", "or",
    "paper", "study", "the", "to", "towards", "using", "via", "with", "without",
}

CATEGORY_RULES = [
    ({"vision", "image", "images", "visual", "detection", "segmentation", "diffusion", "video", "object"}, ["cs.CV"]),
    ({"language", "llm", "llms", "transformer", "retrieval", "alignment", "reasoning", "agent", "agents", "text"}, ["cs.CL", "cs.AI"]),
    ({"optimization", "representation", "contrastive", "neural", "deep", "training", "generalization"}, ["cs.LG", "stat.ML"]),
    ({"robot", "robotics", "manipulation", "navigation", "slam", "planning"}, ["cs.RO"]),
    ({"audio", "speech", "music", "sound", "acoustic"}, ["cs.SD", "eess.AS"]),
    ({"graph", "graphs", "network", "node", "knowledge"}, ["cs.SI", "cs.LG"]),
    ({"security", "privacy", "attack", "adversarial", "robustness"}, ["cs.CR"]),
    ({"system", "systems", "database", "distributed", "compiler", "programming"}, ["cs.DC", "cs.DB", "cs.PL"]),
]


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def parse_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return dt.datetime.fromisoformat(value).astimezone(dt.timezone.utc)


def iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_state(path: Path) -> dict:
    if not path.exists():
        return {
            "profile_updated_at": None,
            "profile_source": None,
            "profile": None,
            "last_recommended_at": None,
            "recommended_arxiv_ids": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def http_json(url: str, timeout: int = 8) -> object:
    req = urllib.request.Request(url, headers={"Zotero-API-Version": "3", "User-Agent": "daily-paper-recommender/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def zotero_roots() -> list[Path]:
    home = Path.home()
    system = platform.system()
    roots: list[Path] = []

    if system == "Darwin":
        roots.append(home / "Library/Application Support/Zotero")
    elif system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            roots.extend([Path(appdata) / "Zotero/Zotero", Path(appdata) / "Zotero"])
    else:
        roots.extend([
            home / ".zotero/zotero",
            home / ".var/app/org.zotero.Zotero/data/zotero",
        ])

    roots.append(home / "Library/Application Support/Zotero")
    return list(dict.fromkeys(roots))


def zotero_profiles_ini() -> Path | None:
    for root in zotero_roots():
        candidate = root / "profiles.ini"
        if candidate.exists():
            return candidate
    return None


def zotero_profile_dir() -> Path | None:
    ini = zotero_profiles_ini()
    if ini is None:
        return None

    parser = configparser.RawConfigParser()
    parser.read(ini)
    root = ini.parent
    candidates: list[tuple[int, Path]] = []

    for section in parser.sections():
        if not section.lower().startswith("profile") or not parser.has_option(section, "Path"):
            continue
        raw_path = parser.get(section, "Path")
        path = root / raw_path if parser.get(section, "IsRelative", fallback="1") == "1" else Path(raw_path)
        score = 0
        if parser.get(section, "Default", fallback="0") == "1":
            score += 10
        if (path / "prefs.js").exists():
            score += 5
        candidates.append((score, path))

    if candidates:
        return max(candidates, key=lambda item: item[0])[1]

    profiles = sorted((root / "Profiles").glob("*.default*"))
    return profiles[0] if profiles else None


def zotero_prefs_file() -> Path | None:
    profile = zotero_profile_dir()
    if profile is None:
        return None
    candidate = profile / "prefs.js"
    return candidate if candidate.exists() else None


def zotero_pref_pattern() -> re.Pattern[str]:
    return re.compile(r'user_pref\("' + re.escape(ZOTERO_LOCAL_API_PREF) + r'",\s*(true|false)\s*\);')


def read_zotero_local_api_pref() -> bool | None:
    prefs = zotero_prefs_file()
    if prefs is None:
        return None
    match = zotero_pref_pattern().search(prefs.read_text(encoding="utf-8", errors="replace"))
    if match is None:
        return None
    return match.group(1) == "true"


def enable_zotero_local_api_pref() -> Path | None:
    prefs = zotero_prefs_file()
    if prefs is None:
        return None

    backup = prefs.with_suffix(prefs.suffix + f".daily-paper-backup-{int(time.time())}")
    shutil.copy2(prefs, backup)

    text = prefs.read_text(encoding="utf-8", errors="replace")
    new_line = f'user_pref("{ZOTERO_LOCAL_API_PREF}", true);'
    pattern = zotero_pref_pattern()
    if pattern.search(text):
        text = pattern.sub(new_line, text, count=1)
    else:
        text = text.rstrip("\n") + "\n" + new_line + "\n"
    prefs.write_text(text, encoding="utf-8")
    return backup


def zotero_api_root_url(api_root: str) -> str:
    return api_root.rstrip("/") + "/"


def zotero_root_available(api_root: str) -> bool:
    try:
        req = urllib.request.Request(zotero_api_root_url(api_root), headers={"Zotero-API-Version": "3"})
        with urllib.request.urlopen(req, timeout=2):
            return True
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return False


def restart_zotero_and_wait(api_root: str) -> bool:
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(
                ["osascript", "-e", 'tell application "Zotero" to quit'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
            time.sleep(1)
            subprocess.run(["open", "-a", "Zotero"], check=False)
        elif system == "Windows":
            subprocess.run(
                ["taskkill", "/IM", "zotero.exe", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            time.sleep(1)
            subprocess.Popen(["zotero.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(
                ["pkill", "-f", "zotero"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            time.sleep(1)
            subprocess.Popen(["zotero"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return False

    for _ in range(30):
        if zotero_root_available(api_root):
            return True
        time.sleep(0.5)
    return False


def ensure_zotero_local_api(api_root: str) -> dict:
    before_pref = read_zotero_local_api_pref()
    if zotero_root_available(api_root):
        return {
            "attempted": False,
            "local_api_enabled_pref_before": before_pref,
            "local_api_enabled_pref_after": before_pref,
            "restarted": False,
            "api_running": True,
            "backup": None,
        }

    backup = None
    if before_pref is not True:
        backup = enable_zotero_local_api_pref()

    restarted = restart_zotero_and_wait(api_root)
    after_pref = read_zotero_local_api_pref()
    return {
        "attempted": True,
        "local_api_enabled_pref_before": before_pref,
        "local_api_enabled_pref_after": after_pref,
        "restarted": restarted,
        "api_running": zotero_root_available(api_root),
        "backup": str(backup) if backup else None,
        "prefs_file": str(zotero_prefs_file()) if zotero_prefs_file() else None,
    }


def zotero_url(api_root: str, library_prefix: str, path: str, params: dict[str, str] | None = None) -> str:
    root = api_root.rstrip("/")
    prefix = library_prefix.strip("/")
    item_path = path.lstrip("/")
    url = f"{root}/{prefix}/{item_path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    return url


def zotero_available(api_root: str, library_prefix: str) -> bool:
    try:
        http_json(zotero_url(api_root, library_prefix, "items", {"limit": "1"}))
        return True
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return False


def fetch_zotero_items(api_root: str, library_prefix: str, profile_days: int | None, profile_papers: int | None) -> list[dict]:
    limit = profile_papers or 100
    params = {
        "sort": "dateModified",
        "direction": "desc",
        "limit": str(min(max(limit, 1), 200)),
        "format": "json",
    }
    url = zotero_url(api_root, library_prefix, "items", params)
    items = http_json(url)
    cutoff = now_utc() - dt.timedelta(days=profile_days) if profile_days else None
    papers = []
    for item in items:
        data = item.get("data", {})
        title = clean_text(data.get("title", ""))
        if not title:
            continue
        modified = parse_time(data.get("dateModified"))
        if cutoff and modified and modified < cutoff:
            continue
        if data.get("itemType") in {"attachment", "note", "annotation"}:
            continue
        papers.append({
            "title": title,
            "dateModified": data.get("dateModified"),
            "dateAdded": data.get("dateAdded"),
            "creators": data.get("creators", []),
            "itemType": data.get("itemType"),
        })
    return papers


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def tokens(text: str) -> list[str]:
    found = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", text.lower())
    return [token.strip("-") for token in found if token.strip("-") not in STOPWORDS]


def infer_categories(words: list[str]) -> list[str]:
    counts = Counter(words)
    scored: list[tuple[int, str]] = []
    for keys, cats in CATEGORY_RULES:
        hit = sum(counts[key] for key in keys)
        for cat in cats:
            if hit:
                scored.append((hit, cat))
    cats = [cat for _, cat in sorted(scored, reverse=True)]
    if not cats:
        cats = ["cs.AI", "cs.LG", "cs.CV"]
    deduped = []
    for cat in cats:
        if cat not in deduped:
            deduped.append(cat)
    return deduped[:8]


def build_profile(items: list[dict]) -> dict:
    title_tokens = [(item["title"], tokens(item["title"])) for item in items]
    global_counts = Counter(token for _, words in title_tokens for token in words)
    anchors = [word for word, count in global_counts.most_common(12) if count >= 2] or [word for word, _ in global_counts.most_common(8)]
    clusters: dict[str, list[tuple[str, list[str]]]] = defaultdict(list)
    for title, words in title_tokens:
        key = next((anchor for anchor in anchors if anchor in words), words[0] if words else "general")
        clusters[key].append((title, words))

    directions = []
    for key, rows in sorted(clusters.items(), key=lambda kv: len(kv[1]), reverse=True)[:6]:
        words = [word for _, row_words in rows for word in row_words]
        keywords = [word for word, _ in Counter(words).most_common(10)]
        label = " ".join(word.capitalize() for word in keywords[:3]) or key.capitalize()
        directions.append({
            "label": label,
            "summary": f"Focus on papers around {', '.join(keywords[:5])}.",
            "keywords": keywords,
            "seed_titles": [title for title, _ in rows[:5]],
            "arxiv_categories": infer_categories(keywords),
        })

    all_keywords = [word for direction in directions for word in direction["keywords"]]
    categories = infer_categories(all_keywords)
    for direction in directions:
        for cat in direction["arxiv_categories"]:
            if cat not in categories:
                categories.append(cat)

    return {
        "directions": directions,
        "all_keywords": [word for word, _ in Counter(all_keywords).most_common(30)],
        "arxiv_categories": categories[:10],
        "source_title_count": len(items),
    }


def arxiv_date(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).strftime("%Y%m%d%H%M")


def fetch_arxiv(category: str, start: dt.datetime, end: dt.datetime, max_results: int) -> list[dict]:
    query = f"cat:{category} AND submittedDate:[{arxiv_date(start)} TO {arxiv_date(end)}]"
    params = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "start": "0",
        "max_results": str(max_results),
    }
    url = f"{ARXIV_BASE}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "daily-paper-recommender/1.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        root = ET.fromstring(response.read())
    papers = []
    for entry in root.findall("atom:entry", ATOM):
        arxiv_id = clean_text(entry.findtext("atom:id", default="", namespaces=ATOM)).rsplit("/", 1)[-1]
        papers.append({
            "id": arxiv_id,
            "title": clean_text(entry.findtext("atom:title", default="", namespaces=ATOM)),
            "summary": clean_text(entry.findtext("atom:summary", default="", namespaces=ATOM)),
            "published": clean_text(entry.findtext("atom:published", default="", namespaces=ATOM)),
            "updated": clean_text(entry.findtext("atom:updated", default="", namespaces=ATOM)),
            "authors": [clean_text(author.findtext("atom:name", default="", namespaces=ATOM)) for author in entry.findall("atom:author", ATOM)],
            "primary_category": entry.find("arxiv:primary_category", ATOM).attrib.get("term", category) if entry.find("arxiv:primary_category", ATOM) is not None else category,
            "link": clean_text(entry.findtext("atom:id", default="", namespaces=ATOM)),
        })
    return papers


def score_paper(paper: dict, profile: dict) -> dict:
    text_words = tokens(f"{paper['title']} {paper['summary']}")
    counts = Counter(text_words)
    reasons = []
    direction_scores = []
    for direction in profile.get("directions", []):
        overlap = [word for word in direction.get("keywords", []) if counts[word]]
        if overlap:
            score = sum(counts[word] for word in overlap) / math.sqrt(len(text_words) + 1)
            direction_scores.append((score, direction["label"], overlap[:6]))
    direction_scores.sort(reverse=True)
    score = sum(score for score, _, _ in direction_scores[:3])
    if paper.get("primary_category") in profile.get("arxiv_categories", []):
        score += 0.4
    for _, label, overlap in direction_scores[:2]:
        reasons.append(f"Matches profile direction '{label}' via keywords: {', '.join(overlap)}")
    return {"score": round(score, 4), "reasons": reasons or ["Weak lexical match; included for category relevance."]}


def recommend(profile: dict, start: dt.datetime, end: dt.datetime, seen_ids: set[str], per_category: int) -> list[dict]:
    by_id = {}
    for category in profile.get("arxiv_categories", ["cs.AI", "cs.LG", "cs.CV"]):
        try:
            for paper in fetch_arxiv(category, start, end, per_category):
                by_id.setdefault(paper["id"], paper)
            time.sleep(0.5)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            print(f"warning: failed to fetch {category}: {exc}", file=sys.stderr)
    ranked = []
    for paper in by_id.values():
        if paper["id"] in seen_ids:
            continue
        scoring = score_paper(paper, profile)
        paper.update(scoring)
        ranked.append(paper)
    ranked.sort(key=lambda row: (row["score"], row.get("published", "")), reverse=True)
    return ranked


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-days", type=int)
    parser.add_argument("--profile-papers", type=int)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--state-dir", type=Path, default=Path(__file__).resolve().parents[1] / "resources")
    parser.add_argument("--since")
    parser.add_argument("--until")
    parser.add_argument("--per-category", type=int, default=50)
    parser.add_argument("--zotero-api-root", default=ZOTERO_API_ROOT)
    parser.add_argument("--zotero-library-prefix", default=ZOTERO_LIBRARY_PREFIX)
    parser.add_argument("--no-auto-enable-zotero", action="store_true")
    parser.add_argument("--no-write-state", action="store_true")
    args = parser.parse_args()

    state_path = args.state_dir / "state.json"
    state = load_state(state_path)
    current = now_utc()
    profile_updated = parse_time(state.get("profile_updated_at"))
    stale_profile = not profile_updated or current - profile_updated > dt.timedelta(days=7)

    if stale_profile and not (args.profile_days or args.profile_papers):
        print(json.dumps({
            "status": "ok",
            "needs_profile_input": True,
            "next_action": "Profile is missing or older than 7 days. Ask the user for recent modified days or recent modified paper count, then rerun with --profile-days or --profile-papers.",
        }, ensure_ascii=False, indent=2))
        return 0

    if (stale_profile or args.profile_days or args.profile_papers):
        zotero_auto_setup = None
        if not args.no_auto_enable_zotero:
            zotero_auto_setup = ensure_zotero_local_api(args.zotero_api_root)
        if not zotero_available(args.zotero_api_root, args.zotero_library_prefix):
            next_action = (
                "Zotero local API could not be reached after auto-setup. Start Zotero once, confirm the app is installed, or rerun with --zotero-api-root http://127.0.0.1:23119/api."
            )
            if args.no_auto_enable_zotero:
                next_action = (
                    "Zotero local API could not be reached. Rerun without --no-auto-enable-zotero to allow automatic setup, or use --zotero-api-root http://127.0.0.1:23119/api."
                )
            print(json.dumps({
                "status": "zotero_unavailable",
                "checked_url": zotero_url(args.zotero_api_root, args.zotero_library_prefix, "items", {"limit": "1"}),
                "zotero_auto_setup": zotero_auto_setup,
                "next_action": next_action,
            }, ensure_ascii=False, indent=2))
            return 0
        items = fetch_zotero_items(args.zotero_api_root, args.zotero_library_prefix, args.profile_days, args.profile_papers)
        state["profile"] = build_profile(items)
        state["profile_updated_at"] = iso(current)
        state["profile_source"] = {
            "profile_days": args.profile_days,
            "profile_papers": args.profile_papers,
            "title_count": len(items),
        }

    profile = state.get("profile")
    if not profile:
        print(json.dumps({
            "status": "ok",
            "needs_profile_input": True,
            "next_action": "No cached profile exists. Ask the user for --profile-days or --profile-papers.",
        }, ensure_ascii=False, indent=2))
        return 0

    start = parse_time(args.since) or parse_time(state.get("last_recommended_at")) or current - dt.timedelta(days=1)
    end = parse_time(args.until) or current
    seen_ids = set(state.get("recommended_arxiv_ids", []))
    recommendations = recommend(profile, start, end, seen_ids, args.per_category)[: args.top_n]

    if not args.no_write_state:
        state["last_recommended_at"] = iso(end)
        state["recommended_arxiv_ids"] = sorted(seen_ids | {paper["id"] for paper in recommendations})[-1000:]
        save_state(state_path, state)

    print(json.dumps({
        "status": "ok",
        "needs_profile_input": False,
        "profile": profile,
        "window": {"start": iso(start), "end": iso(end)},
        "recommendations": recommendations,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
