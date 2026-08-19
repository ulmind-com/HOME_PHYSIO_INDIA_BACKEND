import asyncio
from app.database.connection import connect_to_mongo, init_database
from app.models.settings import WebsiteSettings
import sys
import os

async def update_settings():
    await init_database()
    
    settings = await WebsiteSettings.find_one()
    if settings:
        tiles = [
            {
                "image": "/assets/categories/nursing.jpg",
                "count": "200+",
                "title": "Home Nursing Care",
                "description": "Round-the-clock bedside medical care",
                "cta_label": "Book Now",
                "cta_link": "/booking"
            },
            {
                "image": "/assets/categories/elder.jpg",
                "count": "150+",
                "title": "Elderly Care",
                "description": "Daily living support & elderly companionship",
                "cta_label": "Book Now",
                "cta_link": "/booking"
            },
            {
                "image": "/assets/categories/mother-baby.png",
                "count": "50+",
                "title": "Mother & Baby Care",
                "description": "Post-delivery care for mother & newborn",
                "cta_label": "Book Now",
                "cta_link": "/booking"
            },
            {
                "image": "/assets/categories/physio.jpg",
                "count": "45+",
                "title": "Physiotherapy & Recovery",
                "description": "In-home rehab & pain recovery",
                "cta_label": "Book Now",
                "cta_link": "/booking"
            },
            {
                "image": "/assets/categories/equipment.jpg",
                "count": "100+",
                "title": "Medical Equipment",
                "description": "Rental medical equipment at home",
                "cta_label": "Book Now",
                "cta_link": "/medical-equipment"
            },
            {
                "image": "/assets/categories/icu-setup.png",
                "count": "30+",
                "title": "ICU Setup",
                "description": "Hospital-grade ICU setup delivered",
                "cta_label": "Book Now",
                "cta_link": "/booking"
            },
            {
                "image": "/assets/categories/home-sample.png",
                "count": "500+",
                "title": "Home Sample Collection",
                "description": "Lab tests from the comfort of home",
                "cta_label": "Book Now",
                "cta_link": "/booking"
            }
        ]
        settings.home_about_tiles = tiles
        await settings.save()
        print("Updated 7 tiles successfully!")
    else:
        print("Settings not found.")

if __name__ == "__main__":
    # Ensure correct sys path if running from project root
    sys.path.append(os.getcwd())
    asyncio.run(update_settings())
