"""FastAPI server for the Texas Back Taxes & HOA Liens Property Scraper."""
from __future__ import annotations

import csv
import io
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from fastapi import FastAPI, APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from auth import (
    create_token,
    get_current_user_id,
    hash_password,
    verify_password,
)
from models import (
    DashboardStats,
    CountyStats,
    NLQuery,
    NLQueryResponse,
    Property,
    PropertySearchFilters,
    PropertySearchResponse,
    SavedSearch,
    SavedSearchCreate,
    ScrapeJob,
    ScrapeRequest,
    ScrapeResult,
    TokenResponse,
    UserLogin,
    UserPublic,
    UserRegister,
)
from ai_service import generate_property_insights, parse_natural_language_query
from scrapers import scrape_county
from seed_data import AVAILABLE_COUNTIES, COUNTY_SOURCES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("tx_liens")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Texas Back Taxes & HOA Liens Scraper", version="1.0.0")
api = APIRouter(prefix="/api")


def _serialize_property(doc: dict) -> dict:
    """Strip Mongo internals + serialize datetimes."""
    doc.pop("_id", None)
    for key in ("last_updated", "scraped_at", "ai_generated_at"):
        v = doc.get(key)
        if isinstance(v, datetime):
            doc[key] = v.isoformat()
    return doc


def _prop_doc_for_mongo(prop_dict: dict) -> dict:
    """Convert datetime fields to ISO strings for storage."""
    out = dict(prop_dict)
    for key in ("last_updated", "scraped_at", "ai_generated_at"):
        v = out.get(key)
        if isinstance(v, datetime):
            out[key] = v.isoformat()
    return out


# =============== Health ===============
@api.get("/")
async def root():
    return {"status": "ok", "service": "tx-liens-scraper"}


@api.get("/counties")
async def list_counties():
    """List Texas counties available for scraping (with metadata)."""
    pre = list(COUNTY_SOURCES.keys())
    extra = [c for c in AVAILABLE_COUNTIES if c not in pre]
    return {
        "presupported": [
            {
                "name": name,
                "source_url": meta.get("source_url"),
                "source_doc": meta.get("source_doc"),
                "sale_location": meta.get("sale_location"),
            }
            for name, meta in COUNTY_SOURCES.items()
        ],
        "available": pre + extra,
    }


# =============== Auth ===============
@api.post("/auth/register", response_model=TokenResponse)
async def register(payload: UserRegister):
    existing = await db.users.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = UserPublic(
        id=__import__("uuid").uuid4().hex,
        email=payload.email.lower(),
        name=payload.name,
        created_at=datetime.now(timezone.utc),
    )
    doc = user.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["password_hash"] = hash_password(payload.password)
    await db.users.insert_one(doc)
    token = create_token(user.id, user.email)
    return TokenResponse(token=token, user=user)


@api.post("/auth/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    doc = await db.users.find_one({"email": payload.email.lower()}, {"_id": 0})
    if not doc or not verify_password(payload.password, doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user = UserPublic(
        id=doc["id"],
        email=doc["email"],
        name=doc["name"],
        created_at=datetime.fromisoformat(doc["created_at"]) if isinstance(doc["created_at"], str) else doc["created_at"],
    )
    token = create_token(user.id, user.email)
    return TokenResponse(token=token, user=user)


@api.get("/auth/me", response_model=UserPublic)
async def me(user_id: str = Depends(get_current_user_id)):
    doc = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPublic(
        id=doc["id"],
        email=doc["email"],
        name=doc["name"],
        created_at=datetime.fromisoformat(doc["created_at"]) if isinstance(doc["created_at"], str) else doc["created_at"],
    )


# =============== Properties: Search ===============
def _build_query(filters: PropertySearchFilters) -> dict:
    q: dict = {}
    if filters.counties:
        q["county"] = {"$in": filters.counties}
    if filters.cities:
        q["city"] = {"$in": filters.cities}
    if filters.zip_code:
        q["zip_code"] = filters.zip_code
    if filters.property_type:
        q["property_type"] = filters.property_type
    if filters.has_hoa_lien is not None:
        q["has_hoa_lien"] = filters.has_hoa_lien
    if filters.tax_status:
        q["tax_status"] = filters.tax_status
    if filters.min_acres is not None:
        q["acres"] = {"$gte": filters.min_acres}
    if filters.min_amount is not None or filters.max_amount is not None:
        rng: dict = {}
        if filters.min_amount is not None:
            rng["$gte"] = filters.min_amount
        if filters.max_amount is not None:
            rng["$lte"] = filters.max_amount
        q["tax_owed"] = rng
    if filters.query:
        regex = {"$regex": re.escape(filters.query), "$options": "i"}
        q["$or"] = [
            {"address": regex},
            {"owner": regex},
            {"city": regex},
            {"legal_description": regex},
            {"parcel_id": regex},
        ]
    return q


@api.post("/properties/search", response_model=PropertySearchResponse)
async def search_properties(
    filters: PropertySearchFilters,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    sort: str = Query("tax_owed_desc"),
):
    query = _build_query(filters)
    total = await db.properties.count_documents(query)
    sort_field, sort_dir = "tax_owed", -1
    if sort == "tax_owed_asc":
        sort_dir = 1
    elif sort == "newest":
        sort_field, sort_dir = "scraped_at", -1
    elif sort == "ai_score":
        sort_field, sort_dir = "ai_score", -1

    cursor = (
        db.properties.find(query, {"_id": 0})
        .sort(sort_field, sort_dir)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    results = [_serialize_property(d) async for d in cursor]
    return PropertySearchResponse(total=total, page=page, page_size=page_size, results=results)


@api.get("/properties/{property_id}", response_model=Property)
async def get_property(property_id: str):
    doc = await db.properties.find_one({"id": property_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Property not found")
    return _serialize_property(doc)


@api.post("/properties/{property_id}/ai-insights")
async def get_or_generate_ai_insights(property_id: str):
    doc = await db.properties.find_one({"id": property_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Property not found")
    if doc.get("ai_score") is not None:
        return _serialize_property(doc)
    try:
        ai = await generate_property_insights(doc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("AI insight generation failed")
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")
    update = {
        "ai_score": ai["score"],
        "ai_grade": ai["grade"],
        "ai_summary": ai["summary"],
        "ai_pros": ai["pros"],
        "ai_cons": ai["cons"],
        "ai_generated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.properties.update_one({"id": property_id}, {"$set": update})
    doc.update(update)
    return _serialize_property(doc)


@api.post("/search/nl-parse", response_model=NLQueryResponse)
async def natural_language_search(payload: NLQuery):
    try:
        result = await parse_natural_language_query(payload.query)
    except Exception as exc:  # noqa: BLE001
        logger.exception("NL parse failed")
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")
    return NLQueryResponse(interpreted=result["interpreted"], filters=PropertySearchFilters(**result["filters"]))


# =============== Export ===============
@api.post("/properties/export")
async def export_properties(filters: PropertySearchFilters):
    query = _build_query(filters)
    cursor = db.properties.find(query, {"_id": 0}).limit(5000)
    rows = [d async for d in cursor]

    buf = io.StringIO()
    cols = [
        "parcel_id", "address", "city", "state", "zip_code", "county",
        "owner", "property_type", "tax_owed", "minimum_bid", "adjudged_value",
        "has_hoa_lien", "hoa_lien_amount", "tax_status", "acres", "year_built",
        "legal_description", "case_number", "sale_date", "sale_location",
        "ai_score", "ai_grade", "ai_summary", "source_url",
    ]
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tx_properties_{int(time.time())}.csv"},
    )


# =============== Saved Searches ===============
@api.get("/saved-searches")
async def list_saved_searches(user_id: str = Depends(get_current_user_id)):
    cursor = db.saved_searches.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1)
    items = []
    async for d in cursor:
        if isinstance(d.get("created_at"), str):
            try:
                d["created_at"] = datetime.fromisoformat(d["created_at"])
            except ValueError:
                pass
        items.append(d)
    return {"items": items}


@api.post("/saved-searches", response_model=SavedSearch)
async def create_saved_search(payload: SavedSearchCreate, user_id: str = Depends(get_current_user_id)):
    obj = SavedSearch(user_id=user_id, name=payload.name, filters=payload.filters)
    doc = obj.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.saved_searches.insert_one(doc)
    return obj


@api.delete("/saved-searches/{search_id}")
async def delete_saved_search(search_id: str, user_id: str = Depends(get_current_user_id)):
    res = await db.saved_searches.delete_one({"id": search_id, "user_id": user_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": True}


# =============== Scraping ===============
@api.post("/scrape", response_model=ScrapeJob)
async def trigger_scrape(payload: ScrapeRequest):
    """Scrape one or more counties immediately and upsert into the DB."""
    job = ScrapeJob(counties=payload.counties, status="running")
    job_doc = job.model_dump()
    job_doc["started_at"] = job_doc["started_at"].isoformat()
    await db.scrape_jobs.insert_one(job_doc)

    results: list[ScrapeResult] = []
    for county in payload.counties:
        started = datetime.now(timezone.utc)
        try:
            scraped = await scrape_county(county)
            inserted = updated = 0
            for prop in scraped:
                # Generate id from parcel_id + county for idempotent upserts
                key = {"county": county, "parcel_id": prop.get("parcel_id")}
                existing = await db.properties.find_one(key, {"_id": 0, "id": 1})
                if existing:
                    prop["id"] = existing["id"]
                    await db.properties.update_one(key, {"$set": _prop_doc_for_mongo(prop)})
                    updated += 1
                else:
                    if "id" not in prop:
                        prop["id"] = __import__("uuid").uuid4().hex
                    await db.properties.insert_one(_prop_doc_for_mongo(prop))
                    inserted += 1
            finished = datetime.now(timezone.utc)
            results.append(ScrapeResult(
                county=county,
                status="success" if scraped else "partial",
                properties_found=len(scraped),
                properties_inserted=inserted,
                properties_updated=updated,
                duration_seconds=(finished - started).total_seconds(),
                source_url=COUNTY_SOURCES.get(county, {}).get("source_url", ""),
                message=None if scraped else "No parseable records returned; live data sources may require manual verification.",
                started_at=started,
                finished_at=finished,
            ))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Scrape failed for %s", county)
            finished = datetime.now(timezone.utc)
            results.append(ScrapeResult(
                county=county,
                status="error",
                properties_found=0,
                properties_inserted=0,
                properties_updated=0,
                duration_seconds=(finished - started).total_seconds(),
                source_url=COUNTY_SOURCES.get(county, {}).get("source_url", ""),
                message=str(exc),
                started_at=started,
                finished_at=finished,
            ))

    job.results = results
    job.status = "completed"
    job.finished_at = datetime.now(timezone.utc)
    finished_doc = {
        "status": job.status,
        "finished_at": job.finished_at.isoformat(),
        "results": [
            {**r.model_dump(),
             "started_at": r.started_at.isoformat(),
             "finished_at": r.finished_at.isoformat()}
            for r in results
        ],
    }
    await db.scrape_jobs.update_one({"id": job.id}, {"$set": finished_doc})
    return job


@api.get("/scrape/jobs")
async def list_scrape_jobs(limit: int = 20):
    cursor = db.scrape_jobs.find({}, {"_id": 0}).sort("started_at", -1).limit(limit)
    return {"items": [d async for d in cursor]}


# =============== Dashboard stats ===============
@api.get("/stats/dashboard", response_model=DashboardStats)
async def dashboard_stats():
    total = await db.properties.count_documents({})

    pipeline_total = [
        {"$group": {"_id": None, "sum": {"$sum": "$tax_owed"}}},
    ]
    agg = await db.properties.aggregate(pipeline_total).to_list(1)
    total_value = float(agg[0]["sum"]) if agg else 0.0

    pipeline_county = [
        {"$group": {
            "_id": "$county",
            "total_properties": {"$sum": 1},
            "total_tax_owed": {"$sum": "$tax_owed"},
            "avg_minimum_bid": {"$avg": "$minimum_bid"},
            "last_scraped": {"$max": "$scraped_at"},
        }},
        {"$sort": {"total_properties": -1}},
    ]
    counties = []
    async for row in db.properties.aggregate(pipeline_county):
        last_scraped = row.get("last_scraped")
        if isinstance(last_scraped, str):
            try:
                last_scraped = datetime.fromisoformat(last_scraped)
            except ValueError:
                last_scraped = None
        counties.append(CountyStats(
            county=row["_id"] or "Unknown",
            total_properties=row["total_properties"],
            total_tax_owed=float(row["total_tax_owed"] or 0),
            avg_minimum_bid=float(row.get("avg_minimum_bid") or 0),
            last_scraped=last_scraped,
        ))

    return DashboardStats(
        total_properties=total,
        total_value_at_risk=total_value,
        counties_covered=len(counties),
        new_this_week=total,  # all pre-scraped counts as new on first run
        counties=counties,
    )


# =============== Startup: auto-seed pre-supported counties ===============
@app.on_event("startup")
async def seed_pre_supported():
    count = await db.properties.count_documents({})
    if count > 0:
        logger.info("Properties already in DB (%d). Skipping initial seed.", count)
        return
    logger.info("DB empty - seeding pre-supported counties (Hill, Bosque, McLennan)...")
    for county in ["Hill County", "Bosque County", "McLennan County"]:
        try:
            scraped = await scrape_county(county)
            for prop in scraped:
                prop["id"] = __import__("uuid").uuid4().hex
                await db.properties.insert_one(_prop_doc_for_mongo(prop))
            logger.info("Seeded %d properties for %s", len(scraped), county)
        except Exception:
            logger.exception("Seed failed for %s", county)


@app.on_event("shutdown")
async def shutdown():
    client.close()


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
