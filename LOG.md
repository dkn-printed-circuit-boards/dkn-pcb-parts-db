# LOG — dkn-pcb-parts-db (finished work, newest first)

## 2026-11-17
- Repo CLAUDE.md: scope guard, truth rules, check-in procedure. STATUS rewritten for a clean restart.
- Added the `parts-db validate` command (uv package `dkn_pcb_parts_db`): IDs, citations, trust levels,
  derived arithmetic, and an optional cold-storage hash check. 14 pytest tests. CI on 3 OSes. README.

## 2026-11-16
- First check-in: rohm:ESR03EZPF1002 and the ESR03 EZP family. Four Rohm PDFs went to cold storage by
  sha256. A blind Sonnet second pass agreed on all 16 questions, so the checked facts are cross-checked.
  A one-off script checked that ids are unique, citations resolve, and the arithmetic adds up.
  Draft SCHEMA.md and COLD_STORAGE.md added.

## 2026-11-14
- Oriented on the hub rules, conventions, and the parts-db brief. Test parts recorded as placeholders in STATUS.md.
- Commit identity: git now uses David's GitHub noreply address (global and repo-local).
  The hub's pushed history was rewritten to match (hub BULLETIN B-261114-10).
- Secret scanning and push protection on for this repo and the hub, plus the org default for new repos
  (hub BULLETIN B-261114-11, -12).
- Added MIT LICENSE. First push, after fixing the hub's sync.sh so it can push a brand-new repo
  (hub BULLETIN B-261114-13, B-261115-1).
