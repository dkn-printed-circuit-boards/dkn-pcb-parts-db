# STATUS — dkn-pcb-parts-db (2026-11-17)

**Phase:** groundwork. One part is checked in end to end; David is standing up the support sessions
(digikey, mouser, octopart, lifecycle) and then a real board to test the whole flow.

**Design in use (from talks with David, 2026-11-16/17):**
- A knowledge base that works with any CAD tool (KiCad, Altium, Xpedition, ...). Scope is in CLAUDE.md; don't let it creep.
- Text YAML files are the master copy (SCHEMA.md, schema_version 0, draft). A SQLite copy for fast
  lookups comes later. The SQLite vs Dolt bake-off is moot unless the files stop scaling.
- Keys: part = maker:MPN; document = sha256; fact = a stable readable id.
- Gaps are records. "Not stated" is never guessed.
- Reverse lookup (specs → MPN) gets built per family, only once that family is checked in (David).

**Checked in:** rohm:ESR03EZPF1002 + the ESR03 EZP family: 4 documents, 14 facts, 1 conflict (Digi-Key
says 1/4 W, Rohm says 0.33 W), 2 open gaps (pulse rating, Digi-Key SKU). Blind Sonnet pass agreed; the
clock read about 2.5 min, excluding the earlier reading and search.

**Tooling:** `uv run parts-db validate [--cold]`, 14 tests, CI green on Linux, Windows, and macOS.

**Board flow (David):** schematic → ask parts-db → shop via distributors → request a check-in →
lifecycle check → the board commits its parts.lock.

**Next (my order):**
1. Request inbox: one file per request, so any session can ask without this one running.
2. Part-list export for the lifecycle and distributor sessions.
3. `parts.lock` format and `parts-db check` for boards.
4. SQLite copy, once data volume calls for it.

**Test parts:** resistor = ESR03 (done). Regulator and MCU + eval board: open, David's pick.

## NEEDS DAVID
- RULING: regulator and MCU + eval board test parts.
- TIME: pulse rating for ESR03 is not public. Ask Rohm (Contact Us) when a design needs it.
- From the hub: the shared distributor offer format, and the lifecycle output format.

**Hub notes from this session:** BULLETIN B-261114-9..13, B-261115-1, B-261117-1. Hub history was rewritten
to the noreply email, sync.sh got a first-push fix, and secret scanning plus the org default are on.
