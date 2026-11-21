"""Warehouse adapter: the same loader code writes to local DuckDB or to Google BigQuery.

Switch with the WAREHOUSE env var (duckdb | bigquery | bq-emulator).

BigQuery-sandbox-safe by design: the sandbox (free, no card) does not allow DML
(INSERT/UPDATE/DELETE/MERGE) or streaming inserts, so every write here is a *load job*
(WRITE_TRUNCATE to replace a table, WRITE_APPEND for the load log), and dbt only
uses `table` and `view` materialisations (DDL), never incremental MERGE.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from .config import Settings

# Logical column types shared by both backends
RAW_POS_SCHEMA = {
    "source": "STRING",
    "starting_date": "DATE",
    "indicator": "STRING",
    "sector_raw": "STRING",
    "city_raw": "STRING",
    "value": "FLOAT",
    "_file_sha256": "STRING",
    "_loaded_at": "TIMESTAMP",
}
CALENDAR_SCHEMA = {
    "week_start": "DATE",
    "week_end": "DATE",
    "year": "INTEGER",
    "quarter": "INTEGER",
    "month": "INTEGER",
    "hijri_year": "INTEGER",
    "hijri_month": "INTEGER",
    "ramadan_days_in_week": "INTEGER",
    "is_ramadan_week": "BOOLEAN",
    "is_eid_fitr_week": "BOOLEAN",
    "is_eid_adha_week": "BOOLEAN",
    "is_national_day_week": "BOOLEAN",
    "is_founding_day_week": "BOOLEAN",
}
LOAD_LOG_SCHEMA = {
    "run_id": "STRING",
    "source_key": "STRING",
    "raw_table": "STRING",
    "file_sha256": "STRING",
    "rows_loaded": "INTEGER",
    "status": "STRING",
    "message": "STRING",
    "warehouse": "STRING",
    "started_at": "TIMESTAMP",
    "finished_at": "TIMESTAMP",
}

_DUCK_TYPES = {"STRING": "VARCHAR", "DATE": "DATE", "FLOAT": "DOUBLE", "TIMESTAMP": "TIMESTAMPTZ",
               "INTEGER": "BIGINT", "BOOLEAN": "BOOLEAN"}


class Warehouse(ABC):
    kind: str

    def __init__(self, settings: Settings):
        self.settings = settings
        self.raw = settings.raw_dataset

    @abstractmethod
    def ensure_dataset(self, name: str) -> None: ...

    @abstractmethod
    def table_exists(self, table: str) -> bool: ...

    @abstractmethod
    def load_dataframe(self, table: str, df: pd.DataFrame, schema: dict, mode: str = "truncate") -> int:
        """Replace (mode='truncate') or append to raw.<table>. Returns rows written."""

    @abstractmethod
    def query_df(self, sql: str) -> pd.DataFrame: ...

    @abstractmethod
    def fq(self, dataset: str, table: str) -> str:
        """Fully-qualified, quoted table name for SQL."""

    def last_successful_sha(self, source_key: str) -> str | None:
        if not self.table_exists("load_log"):
            return None
        df = self.query_df(
            f"SELECT file_sha256, finished_at FROM {self.fq(self.raw, 'load_log')} "
            f"WHERE source_key = '{source_key}' AND status IN ('loaded', 'skipped_unchanged') "
            "ORDER BY finished_at DESC LIMIT 1"
        )
        return None if df.empty else str(df.iloc[0, 0])

    def close(self) -> None:  # pragma: no cover - trivial
        pass


class DuckDBWarehouse(Warehouse):
    kind = "duckdb"

    def __init__(self, settings: Settings):
        super().__init__(settings)
        import duckdb

        settings.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(settings.duckdb_path))

    def ensure_dataset(self, name: str) -> None:
        self.con.execute(f'CREATE SCHEMA IF NOT EXISTS "{name}"')

    def table_exists(self, table: str) -> bool:
        n = self.con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
            [self.raw, table],
        ).fetchone()[0]
        return n > 0

    def fq(self, dataset: str, table: str) -> str:
        return f'"{dataset}"."{table}"'

    def load_dataframe(self, table: str, df: pd.DataFrame, schema: dict, mode: str = "truncate") -> int:
        self.ensure_dataset(self.raw)
        cols = ", ".join(f'"{c}" {_DUCK_TYPES[t]}' for c, t in schema.items())
        select = ", ".join(f'CAST("{c}" AS {_DUCK_TYPES[t]}) AS "{c}"' for c, t in schema.items())
        target = self.fq(self.raw, table)
        self.con.register("_incoming", df[list(schema)])
        try:
            self.con.execute("BEGIN")
            if mode == "truncate":
                self.con.execute(f"CREATE OR REPLACE TABLE {target} ({cols})")
            else:
                self.con.execute(f"CREATE TABLE IF NOT EXISTS {target} ({cols})")
            self.con.execute(f"INSERT INTO {target} SELECT {select} FROM _incoming")
            self.con.execute("COMMIT")
        except Exception:
            self.con.execute("ROLLBACK")
            raise
        finally:
            self.con.unregister("_incoming")
        return len(df)

    def query_df(self, sql: str) -> pd.DataFrame:
        return self.con.execute(sql).df()

    def close(self) -> None:
        self.con.close()


class BigQueryWarehouse(Warehouse):
    """Google BigQuery (real) or the open-source goccy/bigquery-emulator (bq-emulator)."""

    def __init__(self, settings: Settings):
        super().__init__(settings)
        from google.cloud import bigquery

        self.bq = bigquery
        self.kind = settings.kind
        kwargs = {"project": settings.bq_project, "location": settings.bq_location}
        if settings.bq_api_endpoint:  # local emulator: no Google account, anonymous credentials
            from google.api_core.client_options import ClientOptions
            from google.auth.credentials import AnonymousCredentials

            kwargs["client_options"] = ClientOptions(api_endpoint=settings.bq_api_endpoint)
            kwargs["credentials"] = AnonymousCredentials()
        # Real BigQuery: credentials come from Application Default Credentials
        # (GOOGLE_APPLICATION_CREDENTIALS -> service-account key, set by google-github-actions/auth in CI)
        self.client = bigquery.Client(**kwargs)
        self.project = settings.bq_project
        self._datasets: set[str] = set()

    def fq(self, dataset: str, table: str) -> str:
        return f"`{self.project}.{dataset}.{table}`"

    def ensure_dataset(self, name: str) -> None:
        # get-then-create (the emulator answers an existing-dataset create with HTTP 500,
        # which the client would retry with back-off)
        from google.api_core.exceptions import NotFound

        if name in self._datasets:
            return
        try:
            self.client.get_dataset(f"{self.project}.{name}")
        except NotFound:
            ds = self.bq.Dataset(f"{self.project}.{name}")
            ds.location = self.settings.bq_location
            self.client.create_dataset(ds, exists_ok=True)
        self._datasets.add(name)

    def table_exists(self, table: str) -> bool:
        from google.api_core.exceptions import NotFound

        try:
            self.client.get_table(f"{self.project}.{self.raw}.{table}")
            return True
        except NotFound:
            return False

    def _schema(self, schema: dict):
        return [self.bq.SchemaField(c, t) for c, t in schema.items()]

    def load_dataframe(self, table: str, df: pd.DataFrame, schema: dict, mode: str = "truncate") -> int:
        self.ensure_dataset(self.raw)
        disposition = (self.bq.WriteDisposition.WRITE_TRUNCATE if mode == "truncate"
                       else self.bq.WriteDisposition.WRITE_APPEND)
        cfg = self.bq.LoadJobConfig(schema=self._schema(schema), write_disposition=disposition)
        out = df[list(schema)].copy()
        for c, t in schema.items():
            if t == "DATE":
                out[c] = pd.to_datetime(out[c]).dt.date
        if self.settings.bq_api_endpoint:
            # The emulator's Parquet loader is incomplete; newline-delimited JSON is the
            # most compatible load format. Real BigQuery uses the faster Parquet path.
            records = out.astype(object).where(out.notna(), None).to_dict("records")
            for r in records:
                for c, t in schema.items():
                    v = r[c]
                    if v is not None and t in ("DATE", "TIMESTAMP"):
                        r[c] = v.isoformat()
            # Resumable upload (no `size`): the emulator does not parse multipart job uploads.
            import io
            import json

            buf = io.BytesIO("\n".join(json.dumps(r) for r in records).encode("utf-8"))
            cfg.source_format = self.bq.SourceFormat.NEWLINE_DELIMITED_JSON
            job = self.client.load_table_from_file(buf, f"{self.project}.{self.raw}.{table}", job_config=cfg)
        else:
            job = self.client.load_table_from_dataframe(out, f"{self.project}.{self.raw}.{table}", job_config=cfg)
        job.result()
        return len(out)

    def query_df(self, sql: str) -> pd.DataFrame:
        rows = self.client.query(sql).result()
        return pd.DataFrame([dict(r.items()) for r in rows], columns=[f.name for f in rows.schema])


def get_warehouse(settings: Settings) -> Warehouse:
    if settings.kind == "duckdb":
        return DuckDBWarehouse(settings)
    return BigQueryWarehouse(settings)
