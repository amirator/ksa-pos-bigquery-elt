# Project blurb (for CV / LinkedIn)

**KSA POS cloud ELT (personal portfolio project, public data)**: github.com/amirator/ksa-pos-bigquery-elt

One-line pitch: a weekly-scheduled ELT pipeline that loads 45,430 rows of official SAMA point-of-sale data into Google BigQuery (sandbox) and serves 5 tested SQL KPI views.

Current state: live on Google BigQuery (free sandbox, project `ksa-pos-elt`, US) via GitHub Actions, refreshed weekly. All 39 dbt tests pass there, and the 5 views equal the DuckDB and emulator builds (parity tests). Evidence: docs/bigquery/evidence.md.

Learnings:
- Designing for the BigQuery sandbox (no DML): load jobs with WRITE_TRUNCATE/APPEND and DDL-only dbt models.
- Keeping one dbt project portable across DuckDB and BigQuery with adapter-dispatched macros.
- Proving portability with a parity test instead of assuming it.
- Real-BigQuery gaps found at go-live: the reserved `_FILE_` column prefix and the sandbox's 60-day expiry cap (no billing → HTTP 403 above 60 days).
- Emulator gaps found and handled: no unary minus in views, no routines.list, multipart uploads, slow joins.
