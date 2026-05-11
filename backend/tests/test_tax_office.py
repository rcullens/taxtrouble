"""Tests for the new Live Tax Office (ACT Tax) balance lookup endpoints.

Endpoints under test:
  - GET  /api/tax-office/sources
  - POST /api/properties/{id}/balance-check
  - POST /api/tax-office/bulk-balance-check
  - GET  /api/tax-office/jobs
  - GET  /api/tax-office/jobs/{job_id}

Plus regression on /api/properties/search for new filters:
  - min_current_balance
  - tax_status='current_due'
"""
from __future__ import annotations

import os
import time

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    env_path = "/app/frontend/.env"
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().strip('"')
                    break
assert BASE_URL, "REACT_APP_BACKEND_URL not set"
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"

TIMEOUT = 30          # general HTTP timeout
SCRAPE_TIMEOUT = 90   # for the single live scrape request


# -------------- Fixtures --------------
@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _county_property_id(session: requests.Session, county: str) -> str:
    r = session.post(
        f"{API}/properties/search",
        json={"counties": [county]},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, f"search failed for {county}: {r.text}"
    body = r.json()
    assert body["total"] >= 1, f"no seeded properties for {county}"
    return body["results"][0]["id"]


@pytest.fixture(scope="module")
def mclennan_property_id(session):
    return _county_property_id(session, "McLennan County")


@pytest.fixture(scope="module")
def hill_property_id(session):
    return _county_property_id(session, "Hill County")


# -------------- /tax-office/sources --------------
class TestTaxOfficeSources:
    EXPECTED = {
        "McLennan County", "Bosque County", "El Paso County", "Fort Bend County",
        "Galveston County", "Hidalgo County", "Upshur County",
    }

    def test_sources_returns_seven_counties(self, session):
        r = session.get(f"{API}/tax-office/sources", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "sources" in body
        items = body["sources"]
        assert isinstance(items, list)
        assert len(items) == 7
        names = {it["county"] for it in items}
        assert names == self.EXPECTED, f"unexpected counties: {names}"

    def test_sources_have_slug_and_url(self, session):
        r = session.get(f"{API}/tax-office/sources", timeout=TIMEOUT)
        body = r.json()
        for it in body["sources"]:
            assert it.get("slug"), f"missing slug: {it}"
            url = it.get("search_url")
            assert url and "actweb.acttax.com" in url, f"bad url: {url}"
            assert it["slug"] in url

    def test_sources_mclennan_slug(self, session):
        r = session.get(f"{API}/tax-office/sources", timeout=TIMEOUT)
        body = r.json()
        mcl = next(it for it in body["sources"] if it["county"] == "McLennan County")
        assert mcl["slug"] == "mclennan"
        assert mcl["search_url"].endswith("/mclennan/index.jsp")


# -------------- /properties/{id}/balance-check --------------
class TestBalanceCheck:
    def test_balance_check_mclennan(self, session, mclennan_property_id):
        r = session.post(
            f"{API}/properties/{mclennan_property_id}/balance-check",
            timeout=SCRAPE_TIMEOUT,
        )
        assert r.status_code == 200, f"balance-check 5xx: {r.status_code} {r.text[:300]}"
        body = r.json()
        # Mongo internals excluded
        assert "_id" not in body
        # Always-present fields
        assert body.get("tax_office_search_url"), "missing tax_office_search_url"
        assert "actweb.acttax.com" in body["tax_office_search_url"]
        assert "/mclennan/" in body["tax_office_search_url"]
        assert body.get("balance_checked_at"), "missing balance_checked_at"
        # Best-effort live-scrape fields — if present, they must be well-typed
        if "current_balance" in body and body["current_balance"] is not None:
            assert isinstance(body["current_balance"], (int, float))
            assert body["current_balance"] >= 0
        if "current_year_levy" in body and body["current_year_levy"] is not None:
            assert isinstance(body["current_year_levy"], (int, float))
        if body.get("tax_office_property_url"):
            assert "actweb.acttax.com" in body["tax_office_property_url"]
        if body.get("tax_office_account_number"):
            assert isinstance(body["tax_office_account_number"], str)

    def test_balance_check_hill_no_actweb(self, session, hill_property_id):
        """Hill County is not on ACT Tax — endpoint must still return 200
        with balance_checked_at but no tax_office_search_url."""
        r = session.post(
            f"{API}/properties/{hill_property_id}/balance-check",
            timeout=SCRAPE_TIMEOUT,
        )
        assert r.status_code == 200, f"non-ACT county 5xx: {r.status_code} {r.text[:300]}"
        body = r.json()
        assert body.get("balance_checked_at"), "missing balance_checked_at"
        # No actweb base for Hill — search_url should be null/missing
        assert not body.get("tax_office_search_url"), (
            f"Hill should not have tax_office_search_url, got {body.get('tax_office_search_url')}"
        )
        # And no live-scrape outputs
        assert not body.get("tax_office_property_url")
        assert not body.get("tax_office_account_number")

    def test_balance_check_404(self, session):
        r = session.post(f"{API}/properties/does-not-exist-xyz/balance-check", timeout=TIMEOUT)
        assert r.status_code == 404


# -------------- /tax-office/bulk-balance-check + job polling --------------
class TestBulkBalanceCheck:
    def test_bulk_job_lifecycle(self, session):
        # POST returns immediately
        t0 = time.time()
        r = session.post(
            f"{API}/tax-office/bulk-balance-check",
            json={"counties": ["McLennan County"]},
            timeout=TIMEOUT,
        )
        elapsed = time.time() - t0
        assert r.status_code == 200, r.text
        assert elapsed < 5, f"bulk endpoint did not return immediately ({elapsed:.1f}s)"
        body = r.json()
        assert body["status"] == "queued"
        assert body["counties"] == ["McLennan County"]
        job_id = body["job_id"]
        assert isinstance(job_id, str) and len(job_id) > 0

        # GET job status — initial
        r = session.get(f"{API}/tax-office/jobs/{job_id}", timeout=TIMEOUT)
        assert r.status_code == 200
        sd = r.json()
        assert sd["id"] == job_id
        assert sd["status"] in {"queued", "running", "completed"}
        assert "progress" in sd
        prog = sd["progress"]
        for k in ("total", "processed", "with_balance", "no_data", "failed"):
            assert k in prog, f"missing progress key {k}"
        assert sd.get("job_type") == "balance_check"

        # Poll up to 5 minutes for either completion OR progress > 0
        deadline = time.time() + 300
        last_processed = prog.get("processed", 0)
        completed = sd["status"] == "completed"
        progressed = False
        while time.time() < deadline:
            time.sleep(10)
            r = session.get(f"{API}/tax-office/jobs/{job_id}", timeout=TIMEOUT)
            assert r.status_code == 200
            sd = r.json()
            if sd["progress"]["processed"] > last_processed:
                progressed = True
                last_processed = sd["progress"]["processed"]
            if sd["status"] == "completed":
                completed = True
                break
        # We require AT LEAST progress increment (live scrape is ~10-15s/property, ~3-4min for 15)
        assert progressed or completed, (
            f"bulk job neither progressed nor completed in 5m: status={sd['status']} "
            f"progress={sd['progress']}"
        )
        # processed never exceeds total
        assert sd["progress"]["processed"] <= max(sd["progress"]["total"], 0) or sd["progress"]["total"] == 0

    def test_list_jobs(self, session):
        r = session.get(f"{API}/tax-office/jobs", timeout=TIMEOUT)
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert isinstance(body["items"], list)
        # At least the job we just created should be present
        assert len(body["items"]) >= 1
        item = body["items"][0]
        assert "id" in item and "status" in item and "progress" in item
        assert item.get("job_type") == "balance_check"

    def test_list_jobs_limit(self, session):
        r = session.get(f"{API}/tax-office/jobs?limit=1", timeout=TIMEOUT)
        assert r.status_code == 200
        body = r.json()
        assert len(body["items"]) <= 1

    def test_job_status_404(self, session):
        r = session.get(f"{API}/tax-office/jobs/no-such-job", timeout=TIMEOUT)
        assert r.status_code == 404


# -------------- /properties/search new filters --------------
class TestSearchNewFilters:
    def test_min_current_balance_filter(self, session):
        # First, verify the filter shape is accepted
        r = session.post(
            f"{API}/properties/search",
            json={"min_current_balance": 100},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # Every returned property (if any) must have current_balance >= 100
        for p in body["results"]:
            cb = p.get("current_balance")
            assert cb is not None and cb >= 100, (
                f"property leaked through min_current_balance filter: id={p.get('id')} cb={cb}"
            )

    def test_min_current_balance_zero_includes_all(self, session):
        # min=0 includes properties with current_balance >= 0 (excludes None)
        r = session.post(
            f"{API}/properties/search",
            json={"min_current_balance": 0},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        body = r.json()
        for p in body["results"]:
            assert p.get("current_balance") is not None
            assert p["current_balance"] >= 0

    def test_tax_status_current_due_accepted(self, session):
        # 'current_due' is a new enum value — must be accepted by the filter
        r = session.post(
            f"{API}/properties/search",
            json={"tax_status": "current_due"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, f"tax_status='current_due' rejected: {r.status_code} {r.text}"
        body = r.json()
        # Every result must have tax_status == 'current_due'
        for p in body["results"]:
            assert p.get("tax_status") == "current_due", (
                f"unexpected tax_status: {p.get('tax_status')}"
            )

    def test_tax_status_scheduled_for_sale_regression(self, session):
        # Regression: existing enum values still work. Seed uses 'scheduled_for_sale'.
        r = session.post(
            f"{API}/properties/search",
            json={"tax_status": "scheduled_for_sale"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1, "seed data should have scheduled_for_sale entries"
        for p in body["results"]:
            assert p["tax_status"] == "scheduled_for_sale"

    def test_tax_status_delinquent_accepted(self, session):
        # 'delinquent' is a valid enum value — filter must be accepted (count may be 0)
        r = session.post(
            f"{API}/properties/search",
            json={"tax_status": "delinquent"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        for p in r.json()["results"]:
            assert p["tax_status"] == "delinquent"
