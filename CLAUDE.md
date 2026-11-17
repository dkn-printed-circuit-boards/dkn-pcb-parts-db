# dkn-pcb-parts-db — standing rules

The hub CLAUDE.md (one folder up) also applies. This file holds standing rules only;
where things stand is in STATUS.md, and finished work is in LOG.md.

## What this repo is
The source of truth for every part on every board in the org. It's a knowledge base about parts
that works with any CAD tool: facts with citations, trust levels, conflicts, gaps, and lessons.
Boards (`mypcb1`, ...) and support sessions ask parts-db; they never write to it.

## Scope: hold the line (David, 2026-11-17: "don't let anyone creep your scope")
**Owns:** part and family records, ordering-code decoding, the document list (PDFs in cold storage
by sha256), facts with citations and trust, conflicts, gaps, reviews, lessons, the check-in curation,
the `parts-db` command plus its published exports, and the **answer cache** (David, 2026-11-17, order
O-261117-1: "it is going to cache everything another session asks it about parts (so it does not have
to re-lookup something it was asked)").
**Does not own; say no and point to the right place:**
- Distributor search, prices, stock → digikey / mouser / octopart repos. Parts-db stores only their
  part numbers and "last seen" dates.
- Lifecycle and obsolescence status → lifecycle repo. Parts-db displays it and never writes it.
- Symbols, footprints, and files for any one CAD tool → per-tool converter repos that read parts-db's export.
- Running simulations → spice repo. Parts-db stores the results as facts.
- Board design decisions → the board's own session.
A request outside this scope gets a polite no and a pointer. If the scope should change, that's David's call.

## Truth rules
1. **"I don't know" is a result.** If no document states it, record a gap: what's unknown, what's
   known nearby, where was searched (with dates), and what's next. Never infer, borrow from a similar
   part, or fill from memory. (David: this is foundational.)
2. Every fact cites a document and page, or is `derived` with its inputs. No citation means it's a note.
3. Facts are only ever added. A fix supersedes the old fact; it never edits it in place.
4. Trust, weakest to strongest: extracted < cross-checked < simulated < human-reviewed < proven-on-hardware.
   Cross-checked needs an independent blind pass that agreed, recorded under `reviews`. Only David
   marks human-reviewed.
5. Source rank: datasheet and errata > user guide and app note > eval board files > white paper >
   distributor text > forum post. A lower source can dispute a fact but never overwrite it.

## Check-in procedure (one curator: only this session merges into `data/`)
1. Fingerprint each PDF (sha256), copy it to cold storage `datasheets/<sha256>.pdf`, and write
   `data/documents/<first 16 hex>.yaml`. Confirm the vendor URL serves the same hash.
2. Family first: the ordering code, then the required core facts for the category, with pages.
3. The part file holds only what's specific to that part: decoded fields, derived facts,
   distributors, conflicts, gaps.
4. Blind second pass: a separate agent (Sonnet) gets the documents and the questions, never the values.
   Agreement promotes facts to cross-checked; disagreement becomes a conflict.
5. `uv run parts-db validate` (add `--cold` when cold storage is mounted) must pass. Then run
   `../tools/check_portable.sh .`, commit, and push through `../tools/sync.sh`.

## Answer cache (every part question another session asks)
1. Look first: `uv run parts-db lookup <subject> <key>`. Exit 0 = current, answer from the record.
   Exit 2 = stale (it says why), re-answer. Exit 1 = not cached, answer it.
2. An answer is built only from records: it lists the fact, gap, and conflict ids it used. "I don't
   know" is an answer that lists a gap. No ids means no answer; record the gap first.
3. Record every answer in `data/answers/` (SCHEMA.md), with who asked and when. Asked again and
   current: add the asker to `asked`. Stale: write a new answer that supersedes the old one.
4. Stale is computed, never stored: a used fact is no longer active, a used gap or conflict is
   resolved, a newer active fact on the same subject and key exists, or (for gap answers) the
   family gained a document since. `validate` lists stale answers.

## Random walks (draft, David 2026-11-17: tune it as the data grows)
After each check-in batch, and whenever you want an audit:
1. `uv run parts-db walk pick --n 5 --out <scratchpad>/walkN`. Keep `key.yaml`; the walker never sees it.
2. A Sonnet agent reads only `tasks.yaml` and the listed PDFs, then writes `results.yaml`. Name the
   forbidden places by full path (this checkout, `key.yaml`). The cold storage folder is also named
   dkn-pcb-parts-db, so "don't open dkn-pcb-parts-db" confuses the walker (walk 1).
3. `uv run parts-db walk score key.yaml results.yaml --walker "Sonnet, blind" --write`.
4. Agreement promotes extracted to cross-checked and gets a family `reviews` entry. A disagreement
   becomes a conflict, settled by source rank. If it's ours that's wrong, a new fact supersedes it.

## Repo rules
- Public repo: facts, short notes, and citations only. Never copy datasheet text or tables in bulk,
  and never commit PDFs.
- Text YAML files are the master copy (SCHEMA.md). Never use commit IDs as identifiers; history
  should be safe to squash.
- Workers and helper sessions submit proposals; they never write to `data/` on main.
- Commits use David's GitHub noreply address (already set in global git config).
