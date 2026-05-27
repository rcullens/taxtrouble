#!/usr/bin/env python3
"""
TaxTrouble Termux Version
Lightweight FastAPI + HTML/JS - Perfect for Termux/Android
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from pathlib import Path

app = FastAPI(title="TaxTrouble Termux")

# Simple in-memory data for demo
PROPERTIES = [
    {"id": "1", "address": "123 Main St", "city": "Austin", "county": "Travis County", "tax_owed": 12450, "years_delinquent": 2, "parcel_id": "TRV-123456"},
    {"id": "2", "address": "456 Oak Ave", "city": "Houston", "county": "Harris County", "tax_owed": 8750, "years_delinquent": 1, "parcel_id": "HRS-789012"},
    {"id": "3", "address": "789 Pine Rd", "city": "Dallas", "county": "Dallas County", "tax_owed": 15200, "years_delinquent": 3, "parcel_id": "DAL-345678"},
]

@app.get("/", response_class=HTMLResponse)
def home():
    html_path = Path(__file__).parent / "simple_ui.html"
    if html_path.exists():
        return html_path.read_text()
    return "<h1>TaxTrouble Termux</h1><p>UI file missing</p>"

@app.get("/api/stats")
def get_stats():
    total = len(PROPERTIES)
    total_tax = sum(p["tax_owed"] for p in PROPERTIES)
    return {"total_properties": total, "total_tax_owed": total_tax}

@app.post("/api/search")
def search(query: dict):
    q = query.get("query", "").lower()
    results = [p for p in PROPERTIES if q in p["address"].lower() or q in p["city"].lower()]
    return {"results": results, "total": len(results)}

@app.post("/api/cad-scan")
def cad_scan():
    # Simulate new CAD 1-year delinquent scan
    new_props = [
        {"id": "4", "address": "321 Elm St", "city": "Austin", "county": "Travis County", "tax_owed": 18750, "years_delinquent": 2, "parcel_id": "TRV-987654"},
        {"id": "5", "address": "654 Cedar Ln", "city": "Houston", "county": "Harris County", "tax_owed": 9200, "years_delinquent": 1, "parcel_id": "HRS-456789"},
    ]
    PROPERTIES.extend(new_props)
    return {"found": len(new_props), "message": "CAD 1-year delinquent scan complete"}

if __name__ == "__main__":
    print("Starting TaxTrouble Termux on http://0.0.0.0:8000")
    print("Open in your phone browser: http://YOUR_PHONE_IP:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)