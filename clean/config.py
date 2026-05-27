from dataclasses import dataclass

@dataclass
class Config:
    app_name: str = "TaxTrouble 2.0"
    version: str = "2.0.0"
    mongo_url: str = "mongodb://localhost:27017"
    db_name: str = "taxtrouble_clean"
    
    # CAD Scraper settings
    cad_min_years_delinquent: int = 1
    cad_max_properties_per_county: int = 500
    
    # UI settings
    ui_port: int = 8080
    ui_dark_mode: bool = True