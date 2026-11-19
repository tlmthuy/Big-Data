"""Notebook 01 conversion to integer UTC epoch seconds."""

from export_raw_subsets import read_csv


def create_parsed_events(db, source):
    """Create the timestamp column without dropping input rows."""
    db.execute("SET TimeZone='UTC'")
    db.execute(f"""CREATE TEMP TABLE parsed AS
            SELECT * EXCLUDE (event_time),
              epoch(try_strptime(event_time, '%Y-%m-%d %H:%M:%S UTC'))::BIGINT AS event_time_ts
            FROM {read_csv(source)}""")
