# Zotero and arXiv Notes

## Zotero local API

Use Zotero's local web API root at `http://127.0.0.1:23119/api/` by default. Zotero's settings UI may display `http://localhost:23119/api/`, but Codex sandbox or app execution environments can resolve `localhost` differently; prefer numeric loopback for scripts.

The settings UI shows the root URL only. Reading the personal library still uses the Web API-style prefix `users/0`, so item requests look like:

`http://127.0.0.1:23119/api/users/0/items?limit=10&format=json`

Useful endpoints:

- `/users/0/items?sort=dateModified&direction=desc&limit=N`
- `/users/0/items?sort=dateAdded&direction=desc&limit=N`
- `/users/0/items?sort=dateModified&direction=desc&format=json`

Prefer `dateModified` for "newly added or recently read/edited" papers, because Zotero updates modified timestamps for many library interactions. Fall back to `dateAdded` only when requested.

## arXiv API

Use the public Atom API:

`https://export.arxiv.org/api/query?search_query=cat:cs.CV+AND+submittedDate:[YYYYMMDDHHMM+TO+YYYYMMDDHHMM]&sortBy=submittedDate&sortOrder=descending`

For multiple categories, query each category separately and deduplicate by arXiv id.

## Profile Semantics

Infer 3-6 research directions from Zotero paper titles. A direction should contain:

- a short label;
- a one-sentence summary;
- representative keywords;
- several seed titles from Zotero;
- likely arXiv categories.

The script uses lexical clustering. Codex should treat the generated profile as a draft and may rewrite labels/summaries for clarity, while preserving the source evidence.

## Category Mapping

Default category candidates:

- vision, image, detection, segmentation, diffusion, generative, video -> `cs.CV`
- language, llm, transformer, retrieval, alignment, reasoning, agent -> `cs.CL`, `cs.AI`
- learning, neural, optimization, representation, contrastive -> `cs.LG`, `stat.ML`
- robotics, manipulation, navigation, slam -> `cs.RO`
- audio, speech, music -> `cs.SD`, `eess.AS`
- graph, network, node, knowledge graph -> `cs.SI`, `cs.LG`
- security, privacy, attack, adversarial -> `cs.CR`
- systems, database, distributed, compiler -> `cs.DC`, `cs.DB`, `cs.PL`

If no strong mapping is found, query `cs.AI`, `cs.LG`, and `cs.CV`.
