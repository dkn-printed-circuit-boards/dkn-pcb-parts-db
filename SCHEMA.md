# SCHEMA — draft (schema_version 0)

Plain YAML text files are the master copy. A SQLite copy for fast lookups gets built from them later.
Version 0 is a draft from the first check-in (ESR03EZPF1002) and will change.

## Layout
```
data/documents/<first 16 hex of sha256>.yaml   one per source file (datasheet, app note, ...)
data/families/<maker>/<series>.yaml            ordering code, shared facts, gaps, reviews
data/parts/<maker>/<MPN>.yaml                  decoded fields, part-only facts, distributors, conflicts, gaps
data/answers/<maker>/<MPN or series>.yaml      answer cache: questions other sessions asked, per subject
```

## Keys
- Part: `<maker>:<MPN>`. A part number alone isn't unique across makers.
- Document: its SHA-256. The PDF lives in cold storage as `datasheets/<sha256>.pdf`, never in git.
- Fact: a readable, stable `id` (for example `rohm.esr03.power.rated`). Never a commit ID.

## Fact fields
`id`, `key`, `value`, `unit`, `conditions` / `applies_to`, `source` (doc, page, where),
`also_stated_by`, `method` (default extracted; `derived` lists its `inputs`), `trust`, `status`, `note`.

- **Trust,** weakest to strongest: extracted < cross-checked < simulated < human-reviewed < proven-on-hardware.
  `cross-checked` needs an independent pass that agreed, recorded under `reviews`.
  Only David marks a fact human-reviewed.
- **Status:** active, superseded, or disputed. Facts are only ever added. A fix is a new fact that
  supersedes the old one.

## Other records
- `conflicts`: competing claims, the winner, and why.
- `gaps`: what is unknown, what is known nearby, where was searched (with dates), and what's next.
  "Not stated" is recorded, never guessed.
- `reviews`: who checked what, how, and the result.

## Answer cache (`data/answers/`)
One file per subject. Top level: `schema_version`, `subject` (a part key `<maker>:<MPN>` or a family id),
and `answers`, a list. The file name is the MPN, or the family id after `<maker>.`.

Answer fields:
- `id`: stable and readable, unique across the database (for example `ans.rohm.ESR03EZPF1002.power.rated`).
- `question`: the question as asked, short.
- `key`: the fact key it maps to. `conditions` (optional) narrows it. Same subject + key + conditions
  is the same question, however it was worded.
- `answer`: a short summary for the asker. The ids below are the real answer.
- `facts`, `gaps`, `conflicts`: ids of the records used. At least one fact or gap.
- `documents_seen`: the family's `documents` list when the answer was written.
- `asked`: list of `{by: <session>, date}`. A repeat question adds a row.
- `answered`: date. `status`: active or superseded. `supersedes`: the answer it replaces.

Answers are only ever added, like facts. Stale is computed by `parts-db validate` and `parts-db lookup`,
never stored. An active answer is stale when:
1. a fact it used is missing or no longer `active`;
2. a gap or conflict it used is no longer `open`;
3. the subject (the part, or the family behind it) has an active fact with the answer's `key` that the
   answer does not list;
4. it used a gap and the family's `documents` now include one not in `documents_seen`.

## Rules
- Store facts, short notes, and citations. Never copy datasheet text or tables in bulk (vendor copyright).
