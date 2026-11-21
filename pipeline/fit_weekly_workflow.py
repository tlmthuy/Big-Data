"""Fit the pinned Notebook 02 graph once for each staged weekly subset."""
import argparse
import hashlib
import json
import time
from pathlib import Path

NOTEBOOK = 'examples/tutorial/02-ETL-with-NVTabular.ipynb'
GRAPH_CELLS = (20, 22, 24, 25, 28, 29, 30, 32, 33, 36, 37, 39, 40, 42, 44, 46, 48)


def digest(path):
    sha256 = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            sha256.update(block)
    return sha256.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--subset', type=int, choices=[10, 25, 50, 100], required=True)
    args = parser.parse_args()
    import cudf
    import numpy as np
    import nvtabular as nvt
    from merlin.dag import ColumnSelector
    from merlin.schema import Schema, Tags

    root = Path(__file__).resolve().parents[1] / 'docs/vendor/nvidia-transformers4rec'
    pin = json.loads((root / 'manifest.json').read_text())
    notebook = root / 'upstream' / NOTEBOOK
    if digest(notebook) != pin['files'][NOTEBOOK]:
        raise ValueError('Notebook checksum mismatch')
    cells = json.loads(notebook.read_text())['cells']
    inputs_manifest = args.inputs / 'manifest.json'
    entries = json.loads(inputs_manifest.read_text())['outputs']
    entry = next(e for e in entries if e['percent'] == args.subset)
    source = (args.inputs / entry['path']).resolve()
    if digest(source) != entry['sha256']:
        raise ValueError('Weekly input checksum mismatch')
    frame = cudf.read_parquet(source)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    namespace = dict(globals(), cudf=cudf, np=np, nvt=nvt, Schema=Schema,
                     Tags=Tags, ColumnSelector=ColumnSelector)
    for index in GRAPH_CELLS:
        exec(compile(''.join(cells[index]['source']), f'{notebook}#cell-{index}', 'exec'), namespace)
    # Isolate each run's Categorify and JoinGroupby statistics.
    import os
    os.chdir(output)
    workflow = nvt.Workflow(namespace['filtered_sessions'])
    start = time.perf_counter()
    dataset = nvt.Dataset(frame)
    workflow.fit(dataset)
    fit_seconds = time.perf_counter() - start

    # Encode the observed products with the actual fitted operator.
    encoder = namespace['cat_feats'].op
    products = frame[['product_id']].drop_duplicates().reset_index(drop=True)
    if products['product_id'].isnull().any() or len(products) != entry['products']:
        raise ValueError('Invalid input product population')
    selector = ColumnSelector(['product_id'])
    encoded = encoder.transform(selector, products)['product_id']
    products['encoded_id'] = encoded
    unknown = int(products['product_id'].min()) - 1
    probe = cudf.DataFrame({'product_id': cudf.Series([None, unknown], dtype='int64')})
    null_id, oov_id = map(int, encoder.transform(selector, probe)['product_id'].to_arrow().to_pylist())
    padding_probe = cudf.DataFrame({'product_id-list': [[int(encoded.iloc[0])]]})
    padded = nvt.ops.ListSlice(-20, pad=True).transform(
        ColumnSelector(['product_id-list']), padding_probe
    )['product_id-list'].to_arrow().to_pylist()[0]
    padding_id = int(padded[-1])
    if ((padding_id, null_id, oov_id) != (0, 1, 2)
            or padded != [int(encoded.iloc[0])] + [0] * 19
            or encoded.isnull().any() or encoded.nunique() != len(products)
            or int(encoded.min()) < 3):
        raise ValueError('Runtime encoding or right-padding contract mismatch')

    workflow.save(str(output / 'workflow'))
    workflow.transform(dataset).to_parquet(str(output / 'processed_nvt'))
    schema = output / 'processed_nvt/schema.pbtxt'
    if not schema.is_file():
        raise FileNotFoundError(schema)
    products = products.sort_values('encoded_id')
    products.to_parquet(str(output / 'product_mapping.parquet'), index=False)
    items = products.to_arrow().to_pylist()
    catalog = dict(subset=args.subset, technical_ids=dict(padding=padding_id, null=null_id, oov=oov_id),
                   items=items)
    (output / 'catalog.json').write_text(json.dumps(catalog) + '\n')
    report = dict(subset=args.subset, input_path=str(source), input_sha256=entry['sha256'],
                  notebook_commit=pin['commit'], input_events=entry['events'],
                  product_vocabulary_size=len(items), fit_seconds=fit_seconds,
                  cudf_version=cudf.__version__, nvtabular_version=nvt.__version__,
                  technical_ids=catalog['technical_ids'],
                  artifacts=dict(workflow='workflow/', schema='processed_nvt/schema.pbtxt',
                                 vocabulary='product_mapping.parquet', catalog='catalog.json'),
                  checksums={str(p.relative_to(output)): digest(p) for p in
                             [schema, output / 'catalog.json', output / 'product_mapping.parquet']})
    (output / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
