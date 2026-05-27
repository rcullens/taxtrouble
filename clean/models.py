from dataclasses import dataclass
from typing import Optional

@dataclass
class Property:
    parcel_id: str
    address: str
    city: str
    county: str
    tax_owed: float
    years_delinquent: int = 0
    owner: str = ""
    property_type: str = ""
    cad_url: str = ""
    last_updated: str = ""