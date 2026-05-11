"""Tests for new features in iteration 3:
- GET /api/leaderboard (deal leaderboard with filters)
- GET /api/properties/{id}/comparables (comp sales panel)
- GET /api/cad/discover/{county} (ArcGIS REST discovery)
- GET /api/cad/jobs (recent CAD jobs)
- cad_url_for() fallback for any county
"""
from __future__ import annotations

import os
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
TIMEOUT = 60


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# -------- Leaderboard --------
class TestLeaderboard:
    def test_leaderboard_default(self, session):
        r = session.get(f"{API}/leaderboard", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        body = r.json()
        # Shape
        assert body.get("period") == "all"
        assert "generated_at" in body
        assert "total_eligible" in body
        assert "items" in body and isinstance(body["items"], list)
        # Eligible = properties with adjudged_value AND minimum_bid > 0.
        # Per request context, expected 15 (McLennan) from current seed.
        assert body["total_eligible"] == 15, f"expected 15 eligible got {body['total_eligible']}"
        # Default limit is 10
        assert len(body["items"]) == 10

    def test_leaderboard_item_shape(self, session):
        r = session.get(f"{API}/leaderboard", timeout=TIMEOUT)
        assert r.status_code == 200
        items = r.json()["items"]
        assert items, "leaderboard returned no items"
        required = {
            "id", "address", "city", "county", "minimum_bid", "adjudged_value",
            "discount_amount", "discount_pct", "ai_score", "ai_grade", "deal_score",
        }
        for it in items:
            missing = required - it.keys()
            assert not missing, f"leaderboard item missing keys: {missing}"
            # Discount math sanity
            assert it["minimum_bid"] > 0
            assert it["adjudged_value"] > 0
            assert it["discount_amount"] == pytest.approx(
                it["adjudged_value"] - it["minimum_bid"], rel=1e-3
            )
            # discount_pct is 0..100
            assert 0 <= it["discount_pct"] <= 100

    def test_leaderboard_sorted_desc(self, session):
        r = session.get(f"{API}/leaderboard?limit=15", timeout=TIMEOUT)
        assert r.status_code == 200
        items = r.json()["items"]
        scores = [it["deal_score"] for it in items]
        assert scores == sorted(scores, reverse=True), "leaderboard not sorted by deal_score desc"

    def test_leaderboard_limit_param(self, session):
        r = session.get(f"{API}/leaderboard?limit=5", timeout=TIMEOUT)
        assert r.status_code == 200
        body = r.json()
        assert len(body["items"]) == 5
        # total_eligible should be unchanged by limit
        assert body["total_eligible"] >= 5

    def test_leaderboard_period_week(self, session):
        r = session.get(f"{API}/leaderboard?period=week", timeout=TIMEOUT)
        assert r.status_code == 200
        body = r.json()
        assert body["period"] == "week"
        # Could be 0..15 depending on scraped_at; just verify shape
        assert isinstance(body["items"], list)
        assert isinstance(body["total_eligible"], int)


# -------- Comparables --------
def _first_property(session, county: str):
    r = session.post(
        f"{API}/properties/search?page_size=5",
        json={"counties": [county]},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200
    results = r.json()["results"]
    assert results, f"no properties for {county}"
    return results[0]


class TestComparables:
    def test_comps_basic_shape(self, session):
        prop = _first_property(session, "McLennan County")
        pid = prop["id"]
        r = session.get(f"{API}/properties/{pid}/comparables", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "target" in body and body["target"]["id"] == pid
        assert "comparables" in body and isinstance(body["comparables"], list)
        assert body["scope"] in ("zip", "county")
        assert "area_avg_price_per_sqft" in body  # may be None
        # Excludes target itself
        comp_ids = [c["id"] for c in body["comparables"]]
        assert pid not in comp_ids

    def test_comps_item_fields(self, session):
        prop = _first_property(session, "McLennan County")
        r = session.get(f"{API}/properties/{prop['id']}/comparables?limit=3", timeout=TIMEOUT)
        assert r.status_code == 200
        comps = r.json()["comparables"]
        assert len(comps) <= 3 and len(comps) >= 1
        required = {"id", "address", "city", "property_type",
                    "tax_owed", "minimum_bid", "adjudged_value"}
        for c in comps:
            missing = required - c.keys()
            assert not missing, f"comparable missing keys: {missing}"

    def test_comps_bosque_fallback(self, session):
        """Bosque has a 'mixed_use' property (only 1 in DB). County fallback must
        ensure comparables[] is non-empty."""
        # Find the mixed_use property if present, otherwise just take first
        r = session.post(
            f"{API}/properties/search?page_size=50",
            json={"counties": ["Bosque County"]},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        bosque = r.json()["results"]
        mixed = next((p for p in bosque if p.get("property_type") == "mixed_use"), None)
        target = mixed or bosque[0]
        r = session.get(f"{API}/properties/{target['id']}/comparables", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["target"]["id"] == target["id"]
        # Bosque has 9 properties; non-target same-county comps must exist
        assert len(body["comparables"]) >= 1, (
            f"comparables empty for {target.get('property_type')} property "
            f"{target['id']} (fallback failed)"
        )

    def test_comps_not_found(self, session):
        r = session.get(f"{API}/properties/nonexistent-xyz/comparables", timeout=TIMEOUT)
        assert r.status_code == 404


# -------- CAD discover --------
class TestCadDiscover:
    def test_discover_returns_search_url_and_label(self, session):
        # Test a county that's not pre-supported to exercise fallback
        r = session.get(f"{API}/cad/discover/Harris County", timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["county"] == "Harris County"
        # Fallback URL must be produced regardless of ArcGIS discovery
        assert body["esearch_search_url"]
        assert "esearch.harriscad.org" in body["esearch_search_url"]
        assert "StreetName=" in body["esearch_search_url"]
        assert body["source_label"]
        # arcgis may legitimately be None
        assert "arcgis" in body

    def test_discover_presupported_county(self, session):
        r = session.get(f"{API}/cad/discover/Hill County", timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert "esearch.hillcad.org" in body["esearch_search_url"]
        # arcgis can be null - acceptable
        assert "arcgis" in body


# -------- CAD Jobs listing --------
class TestCadJobs:
    def test_list_cad_jobs(self, session):
        r = session.get(f"{API}/cad/jobs", timeout=TIMEOUT)
        assert r.status_code == 200
        body = r.json()
        assert "items" in body and isinstance(body["items"], list)

    def test_cad_job_not_found(self, session):
        r = session.get(f"{API}/cad/jobs/nonexistent-job-id", timeout=TIMEOUT)
        assert r.status_code == 404
