"""End-to-end backend tests for TX Back Taxes & HOA Liens scraper API."""
from __future__ import annotations

import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    # Fall back to reading frontend .env (so tests work from container)
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

TIMEOUT = 60


# -------------- Fixtures --------------
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def auth_token(session):
    """Register or login the test user and return the JWT token."""
    creds = {
        "email": f"tester+{uuid.uuid4().hex[:8]}@lien.tx",
        "password": "test1234",
        "name": "Lien Tester",
    }
    r = session.post(f"{API}/auth/register", json=creds, timeout=TIMEOUT)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and isinstance(data["token"], str) and len(data["token"]) > 20
    assert data["user"]["email"] == creds["email"]
    pytest.test_user_email = creds["email"]
    pytest.test_user_password = creds["password"]
    return data["token"]


@pytest.fixture(scope="session")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def sample_property_id(session):
    """Get a property id from the search endpoint (Hill County)."""
    r = session.post(
        f"{API}/properties/search",
        json={"counties": ["Hill County"]},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    return body["results"][0]["id"]


# -------------- Health & Counties --------------
class TestHealthAndCounties:
    def test_health(self, session):
        r = session.get(f"{API}/", timeout=TIMEOUT)
        assert r.status_code == 200
        body = r.json()
        assert body.get("status") == "ok"

    def test_counties(self, session):
        r = session.get(f"{API}/counties", timeout=TIMEOUT)
        assert r.status_code == 200
        body = r.json()
        pre_names = [c["name"] for c in body["presupported"]]
        assert "Hill County" in pre_names
        assert "Bosque County" in pre_names
        assert "McLennan County" in pre_names
        # Available list should include presupported + 36 extras (~39 total)
        assert len(body["available"]) >= 36
        for c in body["presupported"]:
            assert c["source_url"], "presupported county missing source_url"


# -------------- Dashboard --------------
class TestDashboard:
    def test_dashboard_seed(self, session):
        r = session.get(f"{API}/stats/dashboard", timeout=TIMEOUT)
        assert r.status_code == 200
        body = r.json()
        assert body["total_properties"] == 36
        assert body["counties_covered"] == 3
        names = {c["county"]: c["total_properties"] for c in body["counties"]}
        assert names.get("Hill County") == 12
        assert names.get("Bosque County") == 9
        assert names.get("McLennan County") == 15
        assert body["total_value_at_risk"] > 0


# -------------- Auth --------------
class TestAuth:
    def test_register_duplicate(self, session, auth_token):
        # Use same email as registered user
        r = session.post(
            f"{API}/auth/register",
            json={"email": pytest.test_user_email, "password": "test1234", "name": "Dup"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 400

    def test_login_success(self, session):
        r = session.post(
            f"{API}/auth/login",
            json={"email": pytest.test_user_email, "password": pytest.test_user_password},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["token"]
        assert body["user"]["email"] == pytest.test_user_email

    def test_login_invalid(self, session):
        r = session.post(
            f"{API}/auth/login",
            json={"email": pytest.test_user_email, "password": "wrongpass"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 401

    def test_me_requires_auth(self, session):
        r = session.get(f"{API}/auth/me", timeout=TIMEOUT)
        assert r.status_code in (401, 403)

    def test_me_with_token(self, session, auth_headers):
        r = session.get(f"{API}/auth/me", headers=auth_headers, timeout=TIMEOUT)
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == pytest.test_user_email


# -------------- Property Search --------------
class TestPropertySearch:
    def test_search_no_filter(self, session):
        r = session.post(f"{API}/properties/search", json={}, timeout=TIMEOUT)
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 36
        assert len(body["results"]) > 0
        assert all("id" in p and "_id" not in p for p in body["results"])

    def test_search_by_county(self, session):
        r = session.post(
            f"{API}/properties/search",
            json={"counties": ["Hill County"]},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 12
        for p in body["results"]:
            assert p["county"] == "Hill County"

    def test_search_amount_range(self, session):
        r = session.post(
            f"{API}/properties/search",
            json={"min_amount": 1000, "max_amount": 5000},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        body = r.json()
        for p in body["results"]:
            assert 1000 <= p["tax_owed"] <= 5000

    def test_search_query_text(self, session):
        r = session.post(
            f"{API}/properties/search",
            json={"query": "Waco"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        # Waco is in McLennan County
        body = r.json()
        assert body["total"] >= 0  # at minimum doesn't error

    def test_search_pagination(self, session):
        r = session.post(
            f"{API}/properties/search?page=1&page_size=5",
            json={},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["page"] == 1
        assert body["page_size"] == 5
        assert len(body["results"]) <= 5


# -------------- Get single property --------------
class TestPropertyGet:
    def test_get_single_property(self, session, sample_property_id):
        r = session.get(f"{API}/properties/{sample_property_id}", timeout=TIMEOUT)
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == sample_property_id
        assert body["county"] == "Hill County"

    def test_get_property_not_found(self, session):
        r = session.get(f"{API}/properties/does-not-exist-xyz", timeout=TIMEOUT)
        assert r.status_code == 404


# -------------- AI Insights & NL Parse (Claude via Emergent) --------------
class TestAI:
    def test_ai_insights(self, session, sample_property_id):
        r = session.post(
            f"{API}/properties/{sample_property_id}/ai-insights",
            timeout=120,
        )
        assert r.status_code == 200, f"AI insights failed: {r.text[:500]}"
        body = r.json()
        assert body["ai_score"] is not None
        assert body["ai_grade"] in ("A", "B", "C", "D", "F")
        assert isinstance(body["ai_summary"], str) and len(body["ai_summary"]) > 0
        assert isinstance(body["ai_pros"], list)
        assert isinstance(body["ai_cons"], list)
        first_score = body["ai_score"]

        # Second call should hit cache and return the same score/grade
        r2 = session.post(
            f"{API}/properties/{sample_property_id}/ai-insights",
            timeout=30,
        )
        assert r2.status_code == 200
        assert r2.json()["ai_score"] == first_score

    def test_nl_parse(self, session):
        r = session.post(
            f"{API}/search/nl-parse",
            json={"query": "Waco residential properties under 10000"},
            timeout=120,
        )
        assert r.status_code == 200, f"NL parse failed: {r.text[:500]}"
        body = r.json()
        assert isinstance(body.get("interpreted"), str)
        assert isinstance(body.get("filters"), dict)


# -------------- Export CSV --------------
class TestExport:
    def test_export_csv(self, session):
        r = session.post(
            f"{API}/properties/export",
            json={"counties": ["Hill County"]},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        text = r.text
        # Header row + at least one data row
        lines = text.strip().split("\n")
        assert len(lines) >= 2
        assert "parcel_id" in lines[0]


# -------------- Saved Searches --------------
class TestSavedSearches:
    def test_create_list_delete(self, session, auth_headers):
        # CREATE
        payload = {"name": "TEST_my-search", "filters": {"counties": ["Hill County"], "min_amount": 1000}}
        r = session.post(f"{API}/saved-searches", json=payload, headers=auth_headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        created = r.json()
        sid = created["id"]
        assert created["name"] == "TEST_my-search"

        # LIST
        r = session.get(f"{API}/saved-searches", headers=auth_headers, timeout=TIMEOUT)
        assert r.status_code == 200
        items = r.json()["items"]
        assert any(it["id"] == sid for it in items)

        # DELETE
        r = session.delete(f"{API}/saved-searches/{sid}", headers=auth_headers, timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.json().get("deleted") is True

        # DELETE again -> 404
        r = session.delete(f"{API}/saved-searches/{sid}", headers=auth_headers, timeout=TIMEOUT)
        assert r.status_code == 404

    def test_requires_auth(self, session):
        r = session.get(f"{API}/saved-searches", timeout=TIMEOUT)
        assert r.status_code in (401, 403)


# -------------- Scraping & Idempotency --------------
class TestScraping:
    def test_scrape_idempotent_hill(self, session):
        # Get count before
        before = session.post(
            f"{API}/properties/search", json={"counties": ["Hill County"]}, timeout=TIMEOUT
        ).json()["total"]
        assert before == 12

        # Scrape again
        r = session.post(
            f"{API}/scrape", json={"counties": ["Hill County"]}, timeout=120
        )
        assert r.status_code == 200, r.text
        job = r.json()
        assert job["status"] == "completed"
        assert len(job["results"]) == 1
        res = job["results"][0]
        assert res["county"] == "Hill County"
        # idempotency: all should be updates, not inserts
        assert res["properties_inserted"] == 0
        assert res["properties_updated"] == 12

        # Verify count unchanged
        after = session.post(
            f"{API}/properties/search", json={"counties": ["Hill County"]}, timeout=TIMEOUT
        ).json()["total"]
        assert after == 12

    def test_list_scrape_jobs(self, session):
        r = session.get(f"{API}/scrape/jobs", timeout=TIMEOUT)
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body.get("items"), list)
        assert len(body["items"]) >= 1
