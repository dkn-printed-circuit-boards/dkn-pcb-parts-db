# STATUS — dkn-pcb-parts-db (2026-11-14)

**Phase:** design talk. No code, no installs, nothing pushed. Hub advice lives in the hub repo
(`dkn-pcb-hub`) at `briefs/dkn-pcb-parts-db.md`: what David decided, what the hub leans toward, what's open.

**Engine lean (not locked):** SQLite as truth plus a sorted text dump in git, so changes read as diffs.
Dolt is the fallback. A bake-off on 3 test parts decides.

**Test parts: placeholders.** David (2026-11-14): "let's give it as an example". Settle them in the design talk.
| Slot | Placeholder | Tests |
|---|---|---|
| Resistor family | Yageo RC series | one datasheet → many MPNs; inherited family facts with per-MPN overrides; required core facts |
| Regulator | LM1117, or a buck David has used | datasheet revisions; facts with conditions; conflicting values from second sources; SPICE model |
| MCU + eval board | open: David's pick | pin table, errata, ref design + ref BOM |

**Bake-off compares:** how a superseded fact reads in a git diff; the 5 real queries; a clean clone
on another OS; CI rebuild time. Dolt is a separate binary install, so it costs every stranger something.

**First check-in done (2026-11-16):** rohm:ESR03EZPF1002 plus the ESR03 EZP family, 4 documents,
14 facts, 1 conflict (Digi-Key says 1/4 W, Rohm says 0.33 W), 2 open gaps (pulse rating, Digi-Key part number).
The format is plain YAML files as the master copy (draft, SCHEMA.md). `uv run parts-db validate` checks the data (14 tests, CI on Linux, Windows, and macOS).

**Earlier next step:** David opens a full `dkn-pcb-parts-db` session (`claude -n dkn-pcb-parts-db`) for the design talk.
Start from this file and LOG.md. First ask: the MCU + eval board pick.

**On GitHub:** `main` pushed (STATUS, LOG, LICENSE). Secret scanning and push protection on.

**Commit identity:** repo-local git config uses David's GitHub noreply address (2026-11-14).
Never commit with a personal email or the machine default.

## NEEDS DAVID
- RULING: MCU + eval board pick. Gates the bake-off.
- RULING (hub, not this repo): pushed hub commits carry a machine-default author email (macOS
  username + hostname). Rewriting that history is David's call. See hub BULLETIN B-261114-9.
- INSTALL (later): Dolt, when the bake-off starts.
