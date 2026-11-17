# COLD_STORAGE — what lives outside git

Location: the `dkn-pcb-parts-db/` folder in the org's cold storage (env var `PCB_COLD_STORAGE` points
at the parent folder).

| Path | What | Rebuild |
|---|---|---|
| `datasheets/<sha256>.pdf` | Source documents named by fingerprint | Download from the `url` in `data/documents/*.yaml` and check the sha256. A mismatch means the vendor published a new revision. |
