"""Guards for the cloud set-up: sandbox-safe SQL, three dbt targets, CI gating and schedule."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_no_dml_or_incremental_models():
    """BigQuery sandbox rejects DML (INSERT/UPDATE/DELETE/MERGE); keep every model DDL-only."""
    for f in (ROOT / "dbt").rglob("*.sql"):
        if "target" in f.parts:
            continue
        sql = f.read_text().lower()
        assert "incremental" not in sql, f
        assert not re.search(r"\b(insert\s+into|delete\s+from|merge\s+into|update\s+\w+\s+set)\b", sql), f
    proj = (ROOT / "dbt" / "dbt_project.yml").read_text()
    assert "incremental" not in proj.split("# BigQuery sandbox")[1].split("\n", 1)[1]


def test_profiles_have_three_targets():
    prof = yaml.safe_load((ROOT / "dbt" / "profiles.yml").read_text())["ksa_pos"]["outputs"]
    assert set(prof) == {"duckdb", "bigquery", "bq_emulator"}
    assert prof["bigquery"]["method"] == "service-account"
    assert "api_endpoint" in prof["bq_emulator"] and "api_endpoint" not in prof["bigquery"]


def test_ci_schedule_and_secret_gate():
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / "elt.yml").read_text())
    on = wf.get("on", wf.get(True))
    assert on["schedule"][0]["cron"]
    jobs = wf["jobs"]
    assert {"local-duckdb", "bigquery-emulator", "bigquery-cloud"} <= set(jobs)
    cloud = jobs["bigquery-cloud"]
    assert "has_key" in cloud["if"]
    text = (ROOT / ".github" / "workflows" / "elt.yml").read_text()
    assert "secrets.GCP_SA_KEY" in text and "google-github-actions/auth@" in text


def test_requirements_pinned():
    for line in (ROOT / "requirements.txt").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            assert "==" in line, line
