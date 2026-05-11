"""County Appraisal District (CAD) data enrichment.

For pre-supported counties we know:
  - The eSearch base URL
  - The direct property-view URL pattern (where available)
  - Real deed references from the underlying tax-sale PDFs (which is CAD data)

For live enrichment we use Playwright with a real browser to navigate the
BIS Consultants eSearch tools that protect Hill, Bosque, and McLennan CADs.
Failures degrade gracefully — we always return at least the search URL so the
user can verify in their own browser.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


CAD_SOURCES = {
    "Hill County": {
        "name": "Hill CAD",
        "esearch": "https://esearch.hillcad.org",
        "main": "https://hillcad.org",
        "gis": "https://gis.bisclient.com/hillcad/",
        "search_template": "https://esearch.hillcad.org/?StreetName={street}",
    },
    "McLennan County": {
        "name": "McLennan CAD",
        "esearch": "https://esearch.mclennancad.org",
        "main": "https://mclennancad.org",
        "gis": "https://gis.bisclient.com/mclennancad/",
        "search_template": "https://esearch.mclennancad.org/?StreetName={street}",
    },
    "Bosque County": {
        "name": "Bosque CAD",
        "esearch": "https://esearch.bosquecad.com",
        "main": "https://bosquecad.com",
        "gis": "https://gis.bisclient.com/bosquecad/",
        "search_template": "https://esearch.bosquecad.com/?StreetName={street}",
    },
}


def _slugify_county(county: str) -> str:
    """McLennan County -> mclennan"""
    return county.replace(" County", "").replace(" ", "").lower()


def cad_url_for(county: str, address: Optional[str]) -> Optional[str]:
    """Best-effort direct CAD search URL for any Texas county.

    Pre-supported counties use the verified URL templates; everything else falls
    back to the common BIS Consultants pattern `https://esearch.{slug}cad.org`.
    """
    if not address:
        address = ""
    src = CAD_SOURCES.get(county)
    if src is None:
        slug = _slugify_county(county)
        src = {"search_template": f"https://esearch.{slug}cad.org/?StreetName={{street}}"}
    # Strip leading number; pass the remaining street name to eSearch
    m = re.match(r"^\s*\d+\s+(.+?)(?:,|$)", address.strip())
    street = (m.group(1) if m else address.split(",")[0]).strip()
    # Use the longest non-directional token for best fuzzy match
    tokens = [t for t in street.split() if t.upper() not in {"N", "S", "E", "W", "NE", "NW", "SE", "SW", "ST", "AVE", "RD", "DR", "BLVD", "LN", "WAY", "CT"}]
    keyword = max(tokens, key=len) if tokens else (street or address)
    return src["search_template"].format(street=quote(keyword or ""))


def cad_source_name(county: str) -> Optional[str]:
    src = CAD_SOURCES.get(county)
    if src:
        return src["name"]
    slug = _slugify_county(county)
    return f"{county.replace(' County', '')} CAD (esearch.{slug}cad.org)"


# ----------- ArcGIS REST endpoint discovery -----------

# Common ArcGIS hosting patterns for Texas CADs
_ARCGIS_PATTERNS = [
    "https://gis.bisclient.com/{slug}cad/rest/services?f=json",
    "https://gis.{slug}cad.org/arcgis/rest/services?f=json",
    "https://maps.{slug}cad.org/arcgis/rest/services?f=json",
    "https://services.arcgis.com/{slug}cad/arcgis/rest/services?f=json",
]


async def discover_arcgis_endpoint(county: str) -> Optional[dict]:
    """Probe common Texas CAD ArcGIS REST URL patterns and return the live one.

    Returns ``{"endpoint": "<url>", "services": [...]}`` or ``None``.
    """
    import httpx

    slug = _slugify_county(county)
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        for pattern in _ARCGIS_PATTERNS:
            url = pattern.format(slug=slug)
            try:
                r = await client.get(url)
                if r.status_code != 200:
                    continue
                ctype = r.headers.get("content-type", "")
                if "json" not in ctype.lower():
                    continue
                data = r.json()
                if isinstance(data, dict) and ("services" in data or "folders" in data):
                    return {
                        "endpoint": url.split("?")[0],
                        "services": [s.get("name") for s in data.get("services", [])][:20],
                        "folders": data.get("folders", []),
                    }
            except Exception:  # noqa: BLE001
                continue
    return None


async def query_arcgis_parcel(endpoint: str, address: str) -> Optional[dict]:
    """Best-effort: query a discovered ArcGIS parcel layer by address.

    Tries any layer named like 'Parcels', 'Parcel', 'PropertyAccess'.
    """
    import httpx

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        # List services / find parcel layer
        try:
            r = await client.get(endpoint + "?f=json")
            data = r.json() if r.status_code == 200 else {}
        except Exception:
            return None
        candidates: list[str] = []
        for svc in data.get("services", []) or []:
            name = svc.get("name", "")
            if any(k in name.lower() for k in ("parcel", "property")):
                candidates.append(f"{endpoint}/{name}/MapServer")
        # Probe each candidate's first layer
        for cand in candidates:
            try:
                layer_url = f"{cand}/0/query"
                params = {
                    "where": f"SITUS LIKE '%{address.upper()[:40]}%' OR ADDRESS LIKE '%{address.upper()[:40]}%'",
                    "outFields": "*",
                    "returnGeometry": "false",
                    "f": "json",
                    "resultRecordCount": "1",
                }
                r = await client.get(layer_url, params=params)
                if r.status_code != 200:
                    continue
                d = r.json()
                feats = d.get("features", [])
                if feats:
                    return {"layer": cand, "attributes": feats[0].get("attributes", {})}
            except Exception:
                continue
    return None


async def enrich_property_from_cad(prop: dict) -> dict:
    """Attempt a live CAD lookup. Tries ArcGIS REST first, then Playwright.

    Returns at minimum the search/property URLs so the user can verify.
    Adds appraised_value, year_built, sqft, deed_reference when available.
    """
    county = prop.get("county")
    address = prop.get("address")
    src = CAD_SOURCES.get(county)
    update: dict = {
        "cad_search_url": cad_url_for(county, address),
        "cad_data_source": cad_source_name(county),
        "cad_enriched_at": datetime.now(timezone.utc),
    }
    if not address:
        return update

    # Path 1: ArcGIS REST (fast, JSON, no anti-bot)
    try:
        arc = await discover_arcgis_endpoint(county)
        if arc:
            update["arcgis_endpoint"] = arc["endpoint"]
            result = await query_arcgis_parcel(arc["endpoint"], address)
            if result and result.get("attributes"):
                update.update(_map_arcgis_attributes(result["attributes"]))
                update["cad_data_source"] = f"{cad_source_name(county)} (ArcGIS REST)"
                update["cad_property_url"] = arc["endpoint"]
                return update
    except Exception as exc:  # noqa: BLE001
        logger.info("ArcGIS lookup failed for %s/%s: %s", county, address, exc)

    # Path 2: Playwright on BIS eSearch (slower, anti-bot risk)
    if src:
        try:
            scraped = await _live_cad_fetch(src["esearch"], address, prop.get("owner"))
            if scraped:
                update.update(scraped)
                update["cad_data_source"] = f"{src['name']} (live eSearch)"
        except Exception as exc:  # noqa: BLE001
            logger.info("Live CAD fetch failed for %s/%s: %s", county, address, exc)

    return update


def _map_arcgis_attributes(attrs: dict) -> dict:
    """Translate common ArcGIS parcel attribute keys -> our schema."""
    out: dict = {}
    # Normalize keys
    norm = {k.upper(): v for k, v in attrs.items() if v not in (None, "", " ")}
    for key, target in [
        ("APPRAISED", "appraised_value"), ("MARKETVALUE", "appraised_value"),
        ("MARKET_VAL", "appraised_value"), ("TOTAL_MKT", "appraised_value"),
        ("LANDVALUE", "land_value"), ("LAND_VAL", "land_value"),
        ("IMPVALUE", "improvement_value"), ("IMPRV_VAL", "improvement_value"),
        ("YEARBUILT", "year_built"), ("YR_BUILT", "year_built"),
        ("SQFT", "sqft"), ("LIVAREA", "sqft"), ("LIV_AREA", "sqft"),
        ("OWNER", "owner_mailing_address"), ("OWNER_NAME", "owner_mailing_address"),
        ("DEED", "deed_reference"), ("DEED_REF", "deed_reference"),
    ]:
        if key in norm and target not in out:
            v = norm[key]
            try:
                if target in ("appraised_value", "land_value", "improvement_value"):
                    out[target] = float(v)
                elif target in ("year_built", "sqft"):
                    out[target] = int(float(v))
                else:
                    out[target] = str(v)
            except (TypeError, ValueError):
                pass
    return out


async def _live_cad_fetch(esearch_base: str, address: str, owner: Optional[str]) -> Optional[dict]:
    """Best-effort live fetch from BIS Consultants eSearch via Playwright."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return None

    street_match = re.match(r"^\s*(\d+)?\s*(.+?)(?:,|$)", address.strip())
    street_num = (street_match.group(1) or "").strip() if street_match else ""
    street_name_full = (street_match.group(2) or "").strip() if street_match else address
    # Use just the dominant word (most reliable on eSearch fuzzy match)
    street_name = street_name_full.split()[0] if street_name_full else address

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True, executable_path="/root/bin/chromium")
        except Exception:
            browser = await p.chromium.launch(headless=True)
        try:
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            )
            page = await ctx.new_page()
            page.set_default_timeout(15000)
            await page.goto(esearch_base, wait_until="domcontentloaded")
            await page.wait_for_timeout(1200)

            # Open "By Address" tab
            try:
                await page.locator("a:has-text('By Address')").first.click(timeout=4000)
                await page.wait_for_timeout(500)
            except Exception:
                pass

            # Fill the visible street fields
            try:
                if street_num:
                    await page.locator('#StreetNumber:visible').first.fill(street_num)
                await page.locator('#StreetName:visible').first.fill(street_name)
            except Exception:
                return None

            # Submit by pressing Enter in StreetName
            await page.locator('#StreetName:visible').first.press('Enter')
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass

            # Look for the first property link
            link_loc = page.locator('a[href*="/Property/View/"]').first
            if await link_loc.count() == 0:
                return None
            prop_url = await link_loc.get_attribute("href")
            if prop_url and not prop_url.startswith("http"):
                prop_url = esearch_base.rstrip("/") + prop_url

            # Navigate to property detail
            if prop_url:
                await page.goto(prop_url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(1500)
                body_text = await page.locator("body").inner_text()
                return {
                    "cad_property_url": prop_url,
                    **_parse_cad_detail_text(body_text),
                }
        finally:
            await browser.close()
    return None


def _parse_cad_detail_text(text: str) -> dict:
    """Heuristic regex extraction from BIS eSearch property detail text."""
    out: dict = {}
    # Year Built
    m = re.search(r"Year\s*Built[:\s]+(\d{4})", text, re.IGNORECASE)
    if m:
        out["year_built"] = int(m.group(1))
    # Living / Improvement Sqft
    m = re.search(r"(?:Living|Heated)\s*(?:Area|Sqft)[:\s]+([\d,]+)", text, re.IGNORECASE)
    if m:
        out["sqft"] = int(m.group(1).replace(",", ""))
    # Appraised value (most CADs label this 'Market' or 'Total Market')
    m = re.search(r"(?:Total\s*Market|Market\s*Value|Appraised\s*Value)[:\s$]+([\d,]+)", text, re.IGNORECASE)
    if m:
        out["appraised_value"] = float(m.group(1).replace(",", ""))
    # Land value
    m = re.search(r"Land\s*Value[:\s$]+([\d,]+)", text, re.IGNORECASE)
    if m:
        out["land_value"] = float(m.group(1).replace(",", ""))
    # Improvement value
    m = re.search(r"Improvement\s*Value[:\s$]+([\d,]+)", text, re.IGNORECASE)
    if m:
        out["improvement_value"] = float(m.group(1).replace(",", ""))
    # Deed reference V###/P###
    m = re.search(r"\bV\.?\s*(\d{2,5})\s*\/?\s*P\.?\s*(\d{1,5})", text)
    if m:
        out["deed_reference"] = f"V{m.group(1)}/P{m.group(2)}"
    # Deed date
    m = re.search(r"Deed\s*Date[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text, re.IGNORECASE)
    if m:
        out["deed_date"] = m.group(1)
    return out
