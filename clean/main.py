#!/usr/bin/env python3
"""
TaxTrouble 2.0 - Clean Modular Version
No Emergent bullshit. Modern NiceGUI + clean architecture.
"""

import os
os.environ['QT_QPA_PLATFORM'] = 'xcb'

from nicegui import ui, app
from pathlib import Path

# Import our clean modules
try:
    from .config import Config
    from .scrapers.cad_scraper import CADScraper
except ImportError:
    # Fallback for direct run
    import sys
    sys.path.append(str(Path(__file__).parent))
    from config import Config
    from scrapers.cad_scraper import CADScraper

config = Config()

@ui.page('/')
def main_page():
    ui.label('TaxTrouble 2.0').classes('text-4xl font-bold')
    ui.label('Clean version - No Emergent garbage').classes('text-xl text-gray-500')
    
    with ui.card():
        ui.label('Quick Stats').classes('text-2xl')
        ui.label('Total Properties: 72 (demo)')
        ui.label('Total Tax Owed: $1,245,000')
    
    with ui.card():
        ui.label('New: CAD 1-Year Delinquent Scraper').classes('text-xl text-green-600')
        ui.button('Run CAD 1-Year Scan', on_click=run_cad_scan).classes('bg-green-600')
    
    ui.button('Search Properties', on_click=lambda: ui.notify('Search coming soon'))

def run_cad_scan():
    ui.notify('Starting CAD 1-Year Delinquent scan...')
    scraper = CADScraper()
    results = scraper.scan()
    ui.notify(f'Found {len(results)} properties with 1+ year back taxes')

if __name__ == "__main__":
    ui.run(title='TaxTrouble 2.0', port=8080)