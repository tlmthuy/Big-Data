# References, versions and license notes

## Dataset

- M. Kechinov / REES46, *eCommerce behavior data from multi-category store*, `2019-Oct.csv`: [Kaggle dataset page](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store) and [REES46 datasets](https://rees46.com/en/datasets).
- **Dataset license: to confirm on the Kaggle page before redistribution.** The adjacent team repository's data dictionary and references identify the source but do not state a license.

## Official experiment package

- Team repository: [`tlmthuy/Big-Data`](https://github.com/tlmthuy/Big-Data).
- Package: `metrics/releases/tv2-20261124/`, package ID `tv2-20261124`; metrics, configs, registry, manifest and data dictionary were delivered by TV2. The demo displays the package values and does not recompute the benchmark metrics.
- The project-specific evaluation decisions are recorded in [`docs/modeling/model_protocol.md`](../../Big-Data/docs/modeling/model_protocol.md).

## NVIDIA Transformers4Rec reference

- Repository: [NVIDIA-Merlin/Transformers4Rec](https://github.com/NVIDIA-Merlin/Transformers4Rec).
- Pinned source commit: [`f0ca2b5343dd1e40b5d2422b942f014b224f5c20`](https://github.com/NVIDIA-Merlin/Transformers4Rec/tree/f0ca2b5343dd1e40b5d2422b942f014b224f5c20). The adjacent team repo keeps a hash-verified tutorial snapshot and its upstream `LICENSE` at `docs/vendor/nvidia-transformers4rec/`; the source license is Apache-2.0.
- NVIDIA container terms are separate from the source-code license: [NGC Deep Learning Container License](https://developer.nvidia.com/nvidia-deep-learning-container-license).

## Repositories and verified runtime

- Demo repository: [`callmeshinny/demo-big-data`](https://github.com/callmeshinny/demo-big-data).
- Team repository: [`tlmthuy/Big-Data`](https://github.com/tlmthuy/Big-Data); official package commit recorded by the demo: `88f7e02`.
- The package's E1 run configs report Python `3.10.12`, PyTorch `2.1.0a0+4136153`, Transformers4Rec `23.12.0`, Transformers `4.27.1`, Merlin Core `23.8.0`, and PyArrow `10.0.1.dev0+ga6eabc2b.d20230428`; GRU/XLNet ran on CUDA `12.1` and a Tesla T4.
- The separate TV3 runtime record in [`Big-Data/environment/README.md`](../../Big-Data/environment/README.md) lists cuDF `23.04.00`, CuPy `12.0.0b3`, NVTabular `23.08.00`, Merlin Core `23.08.00`, Merlin Models `23.12.00`, Docker `28.4.0`, and the `merlin-pytorch:23.12` image. These are environment-record versions, not additional per-run E1 fields.

## AI-use statement

> **DRAFT — confirm with the team before publication.** Generative AI tools assisted with development and wording of the demo. The displayed benchmark values are sourced from the official TV2 package `tv2-20261124`; the team should confirm the tools, scope of assistance and final wording before including this statement in the report.
