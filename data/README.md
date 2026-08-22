# Runtime data snapshot

`airport_data.db` is the versioned, read-only runtime snapshot used by the API.
It is generated from the public US DOT DB1C Market dataset by
`backend/scripts/build_airport_database.py`.

The raw source file is intentionally not committed. Rebuild the snapshot from
the repository root with:

```powershell
python backend/scripts/build_airport_database.py
```

The API opens the snapshot with SQLite's read-only immutable mode. Runtime
code must not write to this file. Dataset provenance and import statistics are
stored in the `dataset_metadata` table.
