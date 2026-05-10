"""Pydantic models for the Texas property scraper."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List, Literal
import uuid

from pydantic import BaseModel, Field, ConfigDict, EmailStr


def _new_id() -> str:
    return str(uuid.uuid4())


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ------------------ User & Auth ------------------
class UserPublic(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: EmailStr
    name: str
    created_at: datetime


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1, max_length=120)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    token: str
    user: UserPublic


# ------------------ Property ------------------
PropertyType = Literal["residential", "commercial", "land", "manufactured_home", "mixed_use", "unknown"]
DataSource = Literal["McLennan County", "Hill County", "Bosque County"]


class Property(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_new_id)
    parcel_id: str
    case_number: Optional[str] = None
    owner: str
    address: str
    city: str
    state: str = "TX"
    zip_code: Optional[str] = None
    county: DataSource
    property_type: PropertyType = "unknown"
    legal_description: Optional[str] = None
    acres: Optional[float] = None
    year_built: Optional[int] = None

    # Tax & Lien
    tax_owed: float = 0.0
    minimum_bid: Optional[float] = None
    adjudged_value: Optional[float] = None
    market_value: Optional[float] = None
    has_back_taxes: bool = True
    has_hoa_lien: bool = False
    hoa_lien_amount: Optional[float] = None
    tax_status: Literal["delinquent", "in_foreclosure", "scheduled_for_sale", "struck_off", "paid"] = "delinquent"

    # Sale info
    sale_date: Optional[str] = None
    sale_location: Optional[str] = None
    source_url: Optional[str] = None
    source_doc: Optional[str] = None

    # AI fields
    ai_score: Optional[int] = None  # 0-100 investment score
    ai_grade: Optional[Literal["A", "B", "C", "D", "F"]] = None
    ai_summary: Optional[str] = None
    ai_pros: List[str] = Field(default_factory=list)
    ai_cons: List[str] = Field(default_factory=list)
    ai_generated_at: Optional[datetime] = None

    last_updated: datetime = Field(default_factory=_utc_now)
    scraped_at: datetime = Field(default_factory=_utc_now)


class PropertySearchFilters(BaseModel):
    counties: Optional[List[str]] = None
    cities: Optional[List[str]] = None
    zip_code: Optional[str] = None
    property_type: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    has_hoa_lien: Optional[bool] = None
    tax_status: Optional[str] = None
    min_acres: Optional[float] = None
    query: Optional[str] = None  # free-text


class PropertySearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: List[Property]


# ------------------ Saved Search ------------------
class SavedSearch(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_new_id)
    user_id: str
    name: str
    filters: PropertySearchFilters
    created_at: datetime = Field(default_factory=_utc_now)


class SavedSearchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    filters: PropertySearchFilters


# ------------------ Natural Language Search ------------------
class NLQuery(BaseModel):
    query: str = Field(min_length=1)


class NLQueryResponse(BaseModel):
    interpreted: str
    filters: PropertySearchFilters


# ------------------ Scrape Trigger ------------------
class ScrapeRequest(BaseModel):
    counties: List[str]  # e.g. ["McLennan", "Hill", "Bosque"]


class ScrapeResult(BaseModel):
    county: str
    status: Literal["success", "partial", "error"]
    properties_found: int
    properties_inserted: int
    properties_updated: int
    duration_seconds: float
    source_url: str
    message: Optional[str] = None
    started_at: datetime
    finished_at: datetime


class ScrapeJob(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_new_id)
    counties: List[str]
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    started_at: datetime = Field(default_factory=_utc_now)
    finished_at: Optional[datetime] = None
    results: List[ScrapeResult] = Field(default_factory=list)


# ------------------ Stats ------------------
class CountyStats(BaseModel):
    county: str
    total_properties: int
    total_tax_owed: float
    avg_minimum_bid: float
    last_scraped: Optional[datetime] = None


class DashboardStats(BaseModel):
    total_properties: int
    total_value_at_risk: float
    counties_covered: int
    new_this_week: int
    counties: List[CountyStats]
