# Figure captions

**Draft — to agree with TV5**

Regenerate from the demo repo with `python3 -m pip install -r scripts/requirements-figures.txt`
and `python3 scripts/make_figures.py`. The latter reads the sibling Big-Data
cuDF manifest by default. `--weekly-manifest` accepts a different local path
to that artifact. The figure CSVs in `figures/data/` are inputs for charts.

- **e1-ranking.svg** — Recall@20 and NDCG@20 compare Popularity, GRU and XLNet on the planned 10% weekly-session subset and final test split. The scores cover the evaluated sessions in the delivered TV2 E1 package, which is pending.
- **e1-training.svg** — Training time including the input scan compares the three models for the planned 10% weekly subset and final-test protocol. Source is `train_with_input_scan_seconds` in TV2 E1.
- **e2-runtime.svg** — Collector elapsed time covers the whole launched GRU command for each weekly subset under the final-test protocol. The x-axis uses measured TV1 cuDF event counts, and runtime comes from TV2 E2.
- **e2-rss.svg** — Peak RSS compares the GRU runs across the same subsets and final-test protocol using the TV1 cuDF event counts. TV2 E2 samples the sum of parent and child RSS, which can count shared pages more than once.
- **e3-training.svg** — Training time including input scan compares GRU batches of 32 and 128 for the planned 10% subset and validation protocol. Source is TV2 E3.
- **e3-throughput.svg** — Evaluation sessions per second compare the same GRU batches, subset and validation split. TV2 E3 uses `full_evaluation_wall_v1`, which includes I/O.
- **e3-cuda.svg** — Peak PyTorch CUDA allocator reservation compares the two GRU training batches for the planned 10% subset and validation protocol. Source is TV2 E3.
- **e4-size.svg** — File size in bytes compares CSV and Parquet on the same planned 10% weekly input before model splitting. Source is TV2 E4.
- **e4-read.svg** — CSV and Parquet read times cover full streamed decode, excluding pair verification, for the same planned 10% weekly input before model splitting. Source is TV2 E4.
- **e5-scaling.svg** — TV2 E5 reports composed time per million weekly events from the GRU E2 final-test runs across the four subsets. The preliminary shared monthly first-seen cost from the TV1 cuDF manifest is annotated separately.
- **e1-ranking-toy.svg** — Recall@20 and NDCG@20 compare the three models on the toy test split in partition 3. Source is the TV2 E1 collector smoke runs.
- **e1-training-toy.svg** — Training time including input scan compares the three E1 models using the toy input and test protocol. Source is the TV2 E1 collector smoke runs.
- **e3-training-toy.svg** — Training time including input scan compares GRU batches of 32 and 128 on the toy input with validation in partition 3. Source is the TV2 E3 collector smoke runs.
- **e3-throughput-toy.svg** — Sessions per second compare GRU training batches of 32 and 128 on the toy validation split in partition 3. Source is TV2 E3 collector smoke and `full_evaluation_wall_v1`, including I/O.
- **e3-cuda-toy.svg** — Peak PyTorch CUDA allocator reservation compares the two GRU batch sizes on the toy input with validation in partition 3. Source is the TV2 E3 collector smoke runs.
