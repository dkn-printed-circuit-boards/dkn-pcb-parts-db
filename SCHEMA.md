# SCHEMA — draft (schema_version 0)

Plain YAML text files are the master copy. A SQLite copy for fast lookups gets built from them later.
Version 0 is a draft from the first check-in (ESR03EZPF1002) and will change.

## Layout
```
data/documents/<first 16 hex of sha256>.yaml   one per source file (datasheet, app note, ...)
data/families/<maker>/<series>.yaml            ordering code, shared facts, gaps, reviews
data/parts/<maker>/<MPN>.yaml                  decoded fields, part-only facts, distributors, conflicts, gaps
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

## Rules
- Store facts, short notes, and citations. Never copy datasheet text or tables in bulk (vendor copyright).
