"""CAD (County Appraisal District) enrichment endpoint tests.

Covers the new endpoints introduced in this iteration:
  - GET  /api/cad/sources
  - POST /api/properties/{id}/cad-enrich
  - POST /api/cad/bulk-enrich

Plus property-overlay verifications:
  - Hill County deed_reference values from the PDF
  - McLennan County pre-populated year_built, sqft, appraised_value
  - Bosque County appraised_value present
  - cad_search_url auto-populated on every property
"""
from __future__ import annotations

import os
import re
import pytest
import requests

# Resolve BASE_URL the same way backend_test.py does
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
CAD_TIMEOUT = 180  # Playwright live fetch may take a while


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# -------- CAD: /api/cad/sources --------
class TestCadSources:
    def test_cad_sources_returns_three_counties(self, session):
        r = session.get(f"{API}/cad/sources", timeout=TIMEOUT)
        assert r.status_code == 200
        body = r.json()
        assert "sources" in body and isinstance(body["sources"], list)
        names = {s["county"]: s for s in body["sources"]}
        assert "Hill County" in names
        assert "McLennan County" in names
        assert "Bosque County" in names

        # Each source should have the canonical eSearch URL fields
        for src in body["sources"]:
            assert src["name"].endswith("CAD")
            assert src["esearch"].startswith("https://esearch.")
            assert "search_template" in src and "{street}" in src["search_template"]

        # Spot check specific URLs
        assert names["Hill County"]["esearch"] == "https://esearch.hillcad.org"
        assert names["McLennan County"]["esearch"] == "https://esearch.mclennancad.org"
        assert names["Bosque County"]["esearch"] == "https://esearch.bosquecad.com"


# -------- Overlay verification on existing properties --------
def _fetch_county(session, county: str, page_size: int = 50) -> list[dict]:
    r = session.post(
        f"{API}/properties/search?page_size={page_size}",
        json={"counties": [county]},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text
    return r.json()["results"]


class TestCadOverlayOnSeededProperties:
    def test_all_properties_have_cad_search_url(self, session):
        # Pull a sample across all counties via no filter
        r = session.post(
            f"{API}/properties/search?page_size=100", json={}, timeout=TIMEOUT
        )
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) >= 36
        missing = [p["id"] for p in results if not p.get("cad_search_url")]
        # cad_search_url should be present for ALL pre-supported county properties
        assert not missing, f"properties missing cad_search_url: {missing[:5]}"
        # Sanity: URL should point to BIS eSearch
        sample = next(p["cad_search_url"] for p in results if p.get("cad_search_url"))
        assert "esearch." in sample and "StreetName=" in sample

    def test_hill_county_has_real_deed_references(self, session):
        props = _fetch_county(session, "Hill County")
        assert len(props) == 12
        deed_refs = [p.get("deed_reference") for p in props if p.get("deed_reference")]
        # At least 10 of 12 PDF-extracted deed refs should be populated
        assert len(deed_refs) >= 10, f"Only {len(deed_refs)} deed references found"
        # Validate V###/P### format
        pattern = re.compile(r"^V\d+/P\d+$")
        bad = [d for d in deed_refs if not pattern.match(d)]
        assert not bad, f"deed_reference values not in V###/P### form: {bad}"
        # Spot-check known values from the PDF
        by_parcel = {p["parcel_id"]: p for p in props}
        assert by_parcel.get("T078-22", {}).get("deed_reference") == "V917/P8"
        assert by_parcel.get("T028-23", {}).get("deed_reference") == "V1715/P495"

    def test_mclennan_county_has_cad_value_overlay(self, session):
        props = _fetch_county(session, "McLennan County")
        assert len(props) == 15
        # Most McLennan props should have appraised_value populated
        priced = [p for p in props if p.get("appraised_value")]
        assert len(priced) >= 12
        # At least some should have year_built and sqft
        with_year = [p for p in props if p.get("year_built")]
        with_sqft = [p for p in props if p.get("sqft")]
        assert len(with_year) >= 10, f"only {len(with_year)} with year_built"
        assert len(with_sqft) >= 10, f"only {len(with_sqft)} with sqft"
        # land + improvement should be present too
        with_land = [p for p in props if p.get("land_value") is not None]
        with_imp = [p for p in props if p.get("improvement_value") is not None]
        assert len(with_land) >= 12
        assert len(with_imp) >= 12

    def test_bosque_county_appraised_values_present(self, session):
        props = _fetch_county(session, "Bosque County")
        assert len(props) == 9
        priced = [p for p in props if p.get("appraised_value")]
        assert len(priced) == 9, f"only {len(priced)}/9 Bosque properties priced"
        # appraised_value should be a positive number
        for p in priced:
            assert isinstance(p["appraised_value"], (int, float))
            assert p["appraised_value"] > 0


# -------- POST /api/properties/{id}/cad-enrich --------
class TestCadEnrichSingle:
    @pytest.fixture(scope="class")
    def hill_property(self):
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        r = s.post(
            f"{API}/properties/search?page_size=5",
            json={"counties": ["Hill County"]},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        return r.json()["results"][0]

    def test_cad_enrich_returns_200_with_metadata(self, session, hill_property):
        pid = hill_property["id"]
        r = session.post(f"{API}/properties/{pid}/cad-enrich", json={}, timeout=CAD_TIMEOUT)
        assert r.status_code == 200, f"cad-enrich failed: {r.status_code} {r.text[:400]}"
        body = r.json()
        # Endpoint must always set these three (best-effort contract)
        assert body.get("cad_search_url"), "cad_search_url missing"
        assert body.get("cad_data_source"), "cad_data_source missing"
        assert body.get("cad_enriched_at"), "cad_enriched_at missing"
        # Identity preserved
        assert body["id"] == pid
        assert body["county"] == "Hill County"
        # cad_search_url should target Hill eSearch
        assert "esearch.hillcad.org" in body["cad_search_url"]

    def test_cad_enrich_not_found(self, session):
        r = session.post(f"{API}/properties/does-not-exist-xyz/cad-enrich", timeout=30)
        assert r.status_code == 404

    def test_cad_enrich_persists(self, session, hill_property):
        """After enrichment, GET should reflect cad_enriched_at timestamp."""
        pid = hill_property["id"]
        # Trigger (idempotent)
        session.post(f"{API}/properties/{pid}/cad-enrich", json={}, timeout=CAD_TIMEOUT)
        # Verify via GET
        r = session.get(f"{API}/properties/{pid}", timeout=TIMEOUT)
        assert r.status_code == 200
        body = r.json()
        assert body.get("cad_enriched_at") is not None
        assert body.get("cad_search_url") is not None


# -------- POST /api/cad/bulk-enrich (now backgrounded) --------
class TestCadBulkEnrich:
    def test_bulk_enrich_returns_job_id_immediately(self, session):
        """Bulk-enrich is now backgrounded; should return job_id within ~1s."""
        import time as _t
        t0 = _t.time()
        r = session.post(
            f"{API}/cad/bulk-enrich",
            json={"counties": ["Bosque County"]},
            timeout=30,
        )
        elapsed = _t.time() - t0
        assert r.status_code == 200, r.text
        body = r.json()
        assert "job_id" in body and isinstance(body["job_id"], str)
        assert body.get("status") == "queued"
        assert body["counties"] == ["Bosque County"]
        # Must return quickly (well under the synchronous Playwright loop time)
        assert elapsed < 10, f"bulk-enrich did not return immediately (took {elapsed:.1f}s)"

        # Poll the job status endpoint
        job_id = body["job_id"]
        deadline = _t.time() + 600
        last_status = None
        while _t.time() < deadline:
            j = session.get(f"{API}/cad/jobs/{job_id}", timeout=30)
            assert j.status_code == 200, j.text
            jb = j.json()
            last_status = jb.get("status")
            if last_status == "completed":
                # Verify progress shape
                progress = jb.get("progress") or {}
                assert progress.get("total") == 9
                assert progress.get("processed") == 9
                assert progress.get("enriched", 0) + progress.get("failed", 0) == 9
                return
            _t.sleep(5)
        pytest.fail(f"CAD job did not complete within 10 min; last status={last_status}")


# -------- Property model accepts CAD fields (regression) --------
class TestPropertyModelWithCadFields:
    def test_single_property_returns_all_cad_fields(self, session):
        r = session.post(
            f"{API}/properties/search?page_size=1",
            json={"counties": ["McLennan County"]},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        pid = r.json()["results"][0]["id"]
        r2 = session.get(f"{API}/properties/{pid}", timeout=TIMEOUT)
        assert r2.status_code == 200
        body = r2.json()
        # New CAD fields must be present in the model (may be None for some)
        for field in [
            "appraised_value", "improvement_value", "land_value", "sqft",
            "deed_reference", "cad_property_url", "cad_search_url",
            "cad_data_source", "cad_enriched_at", "exemptions",
        ]:
            assert field in body, f"CAD field {field} missing from Property schema"
        # exemptions should be a list (may be empty)
        assert isinstance(body["exemptions"], list)
