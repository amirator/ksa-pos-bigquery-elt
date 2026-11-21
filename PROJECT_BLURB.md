# Project blurb (for CV / LinkedIn)

**KSA POS cloud ELT (personal portfolio project, public data)**: github.com/amirator/ksa-pos-bigquery-elt

One-line pitch: a weekly-scheduled ELT pipeline that loads 45,430 rows of official SAMA point-of-sale data into a BigQuery-ready warehouse and serves 5 tested SQL KPI views.

Current state, worded honestly: runs end to end on DuckDB and on the open-source BigQuery emulator in CI with identical results; not yet run on real BigQuery (needs the owner's free sandbox project + `GCP_SA_KEY` secret).

Learnings:
- Designing for the BigQuery sandbox (no DML): load jobs with WRITE_TRUNCATE/APPEND and DDL-only dbt models.
- Keeping one dbt project portable across DuckDB and BigQuery with adapter-dispatched macros.
- Proving portability with a parity test instead of assuming it.
- Emulator gaps found and handled: no unary minus in views, no routines.list, multipart uploads, slow joins.
