from typing import List, Dict, Optional
import json
from pathlib import Path
from .models import Property

class Database:
    def __init__(self, db_path: str = "data/properties.json"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.properties: List[Property] = []
        self.load()
    
    def load(self):
        if self.db_path.exists():
            with open(self.db_path) as f:
                data = json.load(f)
                self.properties = [Property(**p) for p in data]
    
    def save(self):
        with open(self.db_path, "w") as f:
            json.dump([p.__dict__ for p in self.properties], f, indent=2)
    
    def add_properties(self, props: List[Property]):
        self.properties.extend(props)
        self.save()
    
    def search(self, query: str = "", county: str = "", min_tax: float = 0) -> List[Property]:
        results = self.properties
        
        if query:
            q = query.lower()
            results = [p for p in results if q in p.address.lower() or q in p.city.lower() or q in p.owner.lower()]
        
        if county:
            results = [p for p in results if county.lower() in p.county.lower()]
        
        if min_tax > 0:
            results = [p for p in results if p.tax_owed >= min_tax]
        
        return results
    
    def get_stats(self) -> Dict:
        if not self.properties:
            return {"total": 0, "total_tax": 0, "counties": 0}
        
        return {
            "total": len(self.properties),
            "total_tax": sum(p.tax_owed for p in self.properties),
            "counties": len(set(p.county for p in self.properties)),
            "avg_tax": sum(p.tax_owed for p in self.properties) / len(self.properties)
        }