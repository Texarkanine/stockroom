# Load the Warehouse

Getting your harness history into the warehouse and keeping it fresh. When search feels stale, catch up:

```bash
stockroom ingest
stockroom embed
```

## In This Section

* **[Ingest & Embed](basic.md)** — what those two commands do, their flags, and how to check the warehouse is populated.
* **[Scheduling](schedule.md)** — the nightly job that runs both so you are not doing it by hand.
* **[Harness Sources](sources.md)** — where each harness's history is read from, and how to point stockroom somewhere else.
* **[Backfill Legacy History](backfill/index.md)** — a one-shot excavation of old stores that ordinary ingest never reads.
