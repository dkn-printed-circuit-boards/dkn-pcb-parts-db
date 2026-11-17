# dkn-pcb-parts-db

A knowledge base for PCB parts that works with any CAD tool. Every fact carries its source document
and page, a trust level, and its history. Unknowns are recorded as gaps instead of guessed.
Datasheets stay out of git: the repo keeps facts and citations, and the PDFs live in cold storage,
named by their SHA-256.

Status: early draft (`schema_version` 0). One part is checked in: Rohm ESR03EZPF1002. See
[SCHEMA.md](SCHEMA.md) for the file format.

## Use
Needs [uv](https://docs.astral.sh/uv/) and Python 3.12+. Works on Linux, macOS, and Windows.

```
uv sync
uv run parts-db validate          # check every data file: links, IDs, trust levels, arithmetic
uv run parts-db lookup rohm:ESR03EZPF1002 power.rated   # cached answer: 0 current, 1 none, 2 stale
uv run pytest                     # run the tests
```

Optional: to also check that each document's PDF is present in cold storage and matches its
SHA-256, set the `PCB_COLD_STORAGE` environment variable (see `.env.example`), then:

```
uv run parts-db validate --cold
```

Without cold storage you still get every fact. The PDFs can be downloaded again from the `url` in
each `data/documents/*.yaml` file and checked against its `sha256`.

## Layout
```
data/documents/   one record per source document
data/families/    ordering codes and shared facts (one datasheet often covers many parts)
data/parts/       part-only facts, distributor listings, conflicts, gaps
data/answers/     answer cache: questions other sessions asked, and the records each answer used
src/dkn_pcb_parts_db/   the parts-db command
```

## License
MIT. Vendor documents belong to their vendors and are never stored in this repo.
