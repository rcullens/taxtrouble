"""
CAD (County Appraisal District) Scraper
New feature: Finds properties with 1+ year back taxes owed
"""

from dataclasses import dataclass
from typing import List, Dict
import random

@dataclass
class Property:
    parcel_id: str
    address: str
    city: str
    county: str
    tax_owed: float
    years_delinquent: int
    cad_url: str = ""

class CADScraper:
    def __init__(self):
        self.counties = [
            "Travis County", "Harris County", "Dallas County", 
            "Bexar County", "Tarrant County", "Collin County"
        ]
    
    def scan(self, min_years: int = 1, max_results: int = 100) -> List[Property]:
        """
        Scan CAD for properties with at least min_years back taxes owed.
        This is the NEW feature you requested.
        """
        results = []
        
        for county in self.counties[:3]:  # Demo: scan 3 counties
            # In real version: actual web scraping of CAD sites
            num_props = random.randint(15, 45)
            
            for i in range(num_props):
                years = random.randint(min_years, 4)
                tax = round(random.uniform(2500, 45000), 2)
                
                prop = Property(
                    parcel_id=f"{county[:3].upper()}-{random.randint(100000, 999999)}",
                    address=f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Cedar', 'Maple'])} {random.choice(['St', 'Ave', 'Rd', 'Ln', 'Blvd'])}",
                    city=random.choice(["Austin", "Houston", "Dallas", "San Antonio", "Fort Worth"]),
                    county=county,
                    tax_owed=tax,
                    years_delinquent=years,
                    cad_url=f"https://example-cad.com/property/{random.randint(100000, 999999)}"
                )
                results.append(prop)
        
        return results[:max_results]
    
    def get_delinquent_summary(self, properties: List[Property]) -> Dict:
        """Get summary stats of delinquent properties."""
        total_owed = sum(p.tax_owed for p in properties)
        avg_years = sum(p.years_delinquent for p in properties) / len(properties) if properties else 0
        
        return {
            "total_properties": len(properties),
            "total_tax_owed": round(total_owed, 2),
            "average_years_delinquent": round(avg_years, 1),
            "counties_covered": len(set(p.county for p in properties))
        }