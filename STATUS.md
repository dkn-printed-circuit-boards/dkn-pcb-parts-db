# STATUS — dkn-pcb-parts-db (2026-11-17)

**Phase:** groundwork. One part is checked in end to end. David is standing up the support sessions
(digikey, mouser, octopart, lifecycle), then a real board to test the whole flow.

**Design in use (David, 2026-11-16/17):** a knowledge base that works with any CAD tool (scope is in
CLAUDE.md; don't let it creep). Text YAML files are the master copy (SCHEMA.md v0, draft); SQLite comes later.
Keys: part = maker:MPN, document = sha256, fact = a stable readable id. Gaps are records; never guess.
Reverse lookup (specs → MPN) gets built per family, only after that family is checked in.

**Checked in:** rohm:ESR03EZPF1002 + the ESR03 EZP family: 4 documents, 14 facts, 1 conflict (Digi-Key
1/4 W vs Rohm 0.33 W), 2 open gaps (pulse rating, Digi-Key SKU). The blind Sonnet check-in pass agreed.

**Tooling:** `parts-db validate [--cold]`, `lookup <subject> <key>`, `walk pick|score`. 29 tests.

**ACK O-261117-1 (DAVID, answer cache), done 2026-11-17:** scope, SCHEMA, validator, `lookup`. Answers
list the ids they used; stale is computed. The cache is empty: no session has asked a part question yet.

**Random walks (draft, David 2026-11-17):** walk 1 (seed 215024, 5 ESR03 records, blind Sonnet): 4 agree,
and the marking differs in wording only. Shape lessons: per-row facts without `applies_to` (range) leak
the row count; free-text values need a normalized form. Ruling (David): a walk that agrees promotes
`trust` in place. Done for the D/J rows of tcr and range, so every ESR03 fact is now cross-checked.

**Big-money keys (David, 2026-11-17):** resistor: power rating (I^2 R), tolerance, TCR, size. Capacitor:
voltage rating, rest depends on the use. Wait for real data and use cases before building on it. Then
they can set the required check-in facts per category and extra walk weight.

**Board flow (David):** schematic → ask parts-db → shop via distributors → request a check-in →
lifecycle check → the board commits its parts.lock.

**Next (my order):** 1. request inbox (one file per request). 2. part-list export for lifecycle and
distributors. 3. `parts.lock` format + `parts-db check`. 4. SQLite, once volume calls for it.
**Test parts:** resistor = ESR03 (done). Regulator and MCU + eval board: open, David's pick.

## NEEDS DAVID
- RULING: regulator and MCU + eval board test parts.
- TIME: pulse rating for ESR03 is not public. Ask Rohm (Contact Us) when a design needs it.
- From the hub: the shared distributor offer format, and the lifecycle output format.

**Hub notes:** BULLETIN B-261114-9..13, B-261115-1, B-261117-1.
