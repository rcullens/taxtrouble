"""Live tax-office balance scraper.

Hits the County Tax Office (ACT Tax) site — separate from the appraisal
district (CAD) — to find the *current* unpaid balance on a parcel. This
includes the current year's billed taxes that have not yet gone delinquent,
plus any prior-year delinquencies.

The ACT Tax client subdomain follows the pattern:
    https://actweb.acttax.com/act_webdev/{county_slug}/index.jsp

McLennan, Bosque, and many other TX counties run on this platform.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ACT Tax client slugs for Texas counties (extensible)
ACTWEB_SLUGS: dict[str, str] = {
    "McLennan County": "mclennan",
    "Bosque County": "bosque",
    "El Paso County": "elpaso",
    "Fort Bend County": "fbc",
    "Galveston County": "galveston",
    "Hidalgo County": "hidalgo",
    "Upshur County": "upshur",
    # Hill County uses a different vendor (Tyler) — handled separately below.
}


def actweb_base(county: str) -> Optional[str]:
    slug = ACTWEB_SLUGS.get(county)
    if not slug:
        return None
    return f"https://actweb.acttax.com/act_webdev/{slug}"


def actweb_search_url(county: str) -> Optional[str]:
    base = actweb_base(county)
    return f"{base}/index.jsp" if base else None


async def lookup_balance(county: str, address: Optional[str], owner: Optional[str]) -> Optional[dict]:
    """Hit the live tax office and return the current balance + breakdown.

    Returns dict with: account_number, current_tax_levy, current_amount_due,
    prior_year_amount_due, total_amount_due, market_value, land_value,
    improvement_value, jurisdictions, tax_office_url, last_payment_amount.
    """
    base = actweb_base(county)
    if not base or (not address and not owner):
        return None

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return None

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True, executable_path="/root/bin/chromium")
        except Exception:
            browser = await p.chromium.launch(headless=True)
        try:
            ctx = await browser.new_context(user_agent="Mozilla/5.0 Chrome/126.0 Safari/537.36")
            page = await ctx.new_page()
            page.set_default_timeout(15000)
            await page.goto(f"{base}/index.jsp", wait_until="domcontentloaded")

            # Try address first (sc6), then owner (sc3)
            attempts = []
            if address:
                # Use the first part of address (street number + first street word)
                m = re.match(r"^\s*(\d+\s+\S+)", address.strip())
                attempts.append((m.group(1) if m else address[:30], "sc6"))
            if owner:
                attempts.append((owner.split(",")[0].strip()[:30], "sc3"))

            detail_link: Optional[str] = None
            for crit, radio_id in attempts:
                try:
                    await page.goto(f"{base}/index.jsp", wait_until="domcontentloaded")
                    await page.fill('#criteria', crit)
                    await page.check(f'#{radio_id}')
                    await page.click('input[type=submit][value=Search]')
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    links = await page.evaluate(
                        "Array.from(document.querySelectorAll('a[href*=showdetail]')).slice(0,1).map(a => a.href)"
                    )
                    if links:
                        detail_link = links[0]
                        break
                except Exception:
                    continue

            if not detail_link:
                return None

            await page.goto(detail_link, wait_until="networkidle", timeout=15000)
            text = await page.locator("body").inner_text()
            data = _parse_actweb_detail(text)
            data["tax_office_url"] = detail_link
            data["account_number"] = _extract_can(detail_link)
            return data
        finally:
            await browser.close()


def _extract_can(url: str) -> Optional[str]:
    m = re.search(r"can=([^&]+)", url)
    return m.group(1) if m else None


def _money(text: str, pattern: str) -> Optional[float]:
    m = re.search(pattern + r"\s*\$?\s*([\d,]+\.\d{2}|\d[\d,]*)", text, re.IGNORECASE)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def _parse_actweb_detail(text: str) -> dict:
    out: dict = {
        "current_tax_levy": _money(text, r"Current\s*Tax\s*Levy[:\s]+"),
        "current_amount_due": _money(text, r"Current\s*Amount\s*Due[:\s]+"),
        "prior_year_amount_due": _money(text, r"Prior\s*Year\s*Amount\s*Due[:\s]+"),
        "total_amount_due": _money(text, r"Total\s*Amount\s*Due[:\s]+"),
        "last_payment_amount": _money(text, r"Last\s*Payment\s*Amount[^:]*[:\s]+"),
        "market_value": _money(text, r"Market\s*Value[:\s]+"),
        "land_value_actweb": _money(text, r"Land\s*Value[:\s]+"),
        "improvement_value_actweb": _money(text, r"Improvement\s*Value[:\s]+"),
        "capped_value": _money(text, r"Capped\s*Value[:\s]+"),
    }
    return {k: v for k, v in out.items() if v is not None}


async def lookup_balance_for_property(prop: dict) -> dict:
    """High-level wrapper used by the server endpoint."""
    county = prop.get("county")
    update: dict = {
        "tax_office_search_url": actweb_search_url(county),
        "balance_checked_at": datetime.now(timezone.utc),
    }
    result = await lookup_balance(county, prop.get("address"), prop.get("owner"))
    if result:
        # Map to property schema
        if "total_amount_due" in result:
            update["current_balance"] = result["total_amount_due"]
            # If there's any current-year levy that's still due, mark status
            if result.get("current_amount_due", 0) > 0:
                update["tax_status"] = "current_due" if result.get("prior_year_amount_due", 0) == 0 else "delinquent"
        if "current_tax_levy" in result:
            update["current_year_levy"] = result["current_tax_levy"]
        if "current_amount_due" in result:
            update["current_year_due"] = result["current_amount_due"]
        if "prior_year_amount_due" in result:
            update["prior_year_due"] = result["prior_year_amount_due"]
        if "market_value" in result:
            update["appraised_value"] = result["market_value"]
        if "land_value_actweb" in result and "land_value" not in prop:
            update["land_value"] = result["land_value_actweb"]
        if "improvement_value_actweb" in result and "improvement_value" not in prop:
            update["improvement_value"] = result["improvement_value_actweb"]
        update["tax_office_property_url"] = result.get("tax_office_url")
        update["tax_office_account_number"] = result.get("account_number")
    return update
