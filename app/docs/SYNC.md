# Sync with the team repo

This repo is a personal working copy for the demo. The team repo `tlmthuy/Big-Data` is the source of truth.

## 1. Folder setup

Keep both repos side by side:

```
workspace/
├── Big-Data/        # git clone https://github.com/tlmthuy/Big-Data
└── tv4-demo-web/    # this repo
```

## 2. Pull data into the demo (team repo → this repo)

1. Update the team repo:
   ```bash
   cd Big-Data && git pull
   ```
2. Take only artifacts that TV2 has delivered or confirmed: prediction run directories and the metrics package.
3. Generate the demo prediction sample and confirmed results JSON from the delivered artifacts:
   - `scripts/export_demo_data.py --run RUN_DIR=CATALOG ... --output public/demo-data.json`
     (any model with K = 20; the catalog must match the run's recorded SHA-256);
   - from the demo repo, `python3 scripts/export_official_results.py --package ../Big-Data/metrics/releases/tv2-20261124 --output public/official-results.json`.
   For real E1, use the fixed hash-sample exporter command documented in `docs/DEMO_DAY.md`.
4. Commit only the small JSON in `public/`. Note the source run ID and the team commit in the commit message.

## 3. Push the UI back (this repo → team repo)

The team expects the demo under `app/` on branch `feature/tv4-demo-documentation`. Push back only at milestones (for example 21/11 sample, 27/11 integration, 28/11 final), not after every change:

```bash
cd Big-Data
git checkout feature/tv4-demo-documentation && git pull
rsync -a --delete --exclude node_modules --exclude dist --exclude .git \
  --exclude AGENTS.md --exclude docs \
  ../tv4-demo-web/ app/
# keep app/output_contract.md, app/README.md, app/TODO.md in the team repo
git status    # review: only app/ should change
```

Then make one clean commit and push (or open a PR).

## 4. Contract changes

`docs/data_contract.md` is a pinned copy at team commit `5b2df90`. Edit the contract in the team repo (`app/output_contract.md`) first, then refresh the copy here. Never let the two drift.

## Product display lookup (optional, pending TV1)

Use the CSV export of the same subset week as the demo run. It must contain
original `product_id`, `brand`, `category_code`, `price` (USD) and
`event_time` (ISO date and time). The adapter picks the most recent event
for each product. For equal timestamps, the later CSV row wins. A blank
price on the selected event is exported as null.

```bash
python3 scripts/export_product_info.py /path/to/tv1-subset.csv \
  --source "TV1 artifact name and subset version" --data-kind real \
  --output public/product-info.json
```

Check the output size before committing. Keep the public lookup limited to
products used by the demo if the delivered subset is large.
