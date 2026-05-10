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


def cad_url_for(county: str, address: Optional[str]) -> Optional[str]:
    """Best-effort direct CAD search URL for a property."""
    src = CAD_SOURCES.get(county)
    if not src:
        return None
    if not address:
        return src["esearch"]
    # Strip leading number; pass the remaining street name to eSearch
    m = re.match(r"^\s*\d+\s+(.+?)(?:,|$)", address.strip())
    street = (m.group(1) if m else address.split(",")[0]).strip()
    # Use the longest non-directional token for best fuzzy match
    tokens = [t for t in street.split() if t.upper() not in {"N", "S", "E", "W", "NE", "NW", "SE", "SW", "ST", "AVE", "RD", "DR", "BLVD", "LN", "WAY", "CT"}]
    keyword = max(tokens, key=len) if tokens else street
    return src["search_template"].format(street=quote(keyword))


def cad_source_name(county: str) -> Optional[str]:
    src = CAD_SOURCES.get(county)
    return src["name"] if src else None


async def enrich_property_from_cad(prop: dict) -> dict:
    """Attempt a live CAD lookup via Playwright. Returns dict of new fields.

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
    if not src or not address:
        return update

    # Attempt live fetch with Playwright (best-effort; many CADs use anti-bot)
    try:
        scraped = await _live_cad_fetch(src["esearch"], address, prop.get("owner"))
        if scraped:
            update.update(scraped)
            update["cad_data_source"] = f"{src['name']} (live)"
    except Exception as exc:  # noqa: BLE001
        logger.info("Live CAD fetch failed for %s/%s: %s", county, address, exc)

    return update


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
