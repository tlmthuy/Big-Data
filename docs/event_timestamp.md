# Chuyển event_time sang timestamp UTC

Notebook 01 cell 12 chuyển `event_time` thành `event_time_ts`. Hàm
`create_parsed_events` trong `pipeline/event_timestamp.py` tạo cột BIGINT biểu
diễn giây Unix UTC. Timestamp lỗi được biểu diễn bằng NULL để kiểm tra trước khi
xử lý tiếp.

[Log chuyển timestamp](../data/manifests/event_timestamp.json) được trích từ
bước chuyển đổi trong lần chạy DuckDB CPU trên CSV toàn tháng. Cả trước và sau
chuyển đổi đều có 42.448.764 dòng. Không có lỗi parse. Hai mốc UTC là
2019-10-01 00:00:00 và 2019-10-31 23:59:59.

Lệnh kiểm tra mẫu từ gốc repo, dùng DuckDB trong `pipeline/requirements-audit.txt`:

```bash
PYTHONPATH=pipeline .venv/bin/python - <<'PY'
from pathlib import Path
import duckdb
from event_timestamp import create_parsed_events

with duckdb.connect() as db:
    create_parsed_events(db, Path('data/subset/raw_week/raw_week_010.csv'))
    print(db.execute('SELECT count(*), count(*) - count(event_time_ts), min(event_time_ts), max(event_time_ts) FROM parsed').fetchone())
PY
```
