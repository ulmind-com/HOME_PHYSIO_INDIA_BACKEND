import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.models.service import Service, Category
from app.models.base import ImageAsset
from app.models.enums import ContentStatus

async def main():
    client = AsyncIOMotorClient("mongodb+srv://ulmindorg_db_user:nupun123@cluster0.phsnman.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    db = client["nupun_health"]
    await init_beanie(database=db, document_models=[Service, Category])

    await Service.find_all().delete()
    
    fallbacks = [
        {
            "title": "Home Nursing Care",
            "category_name": "Home Nursing Care",
            "short_description": "24/7 qualified nurses at your home — injections, wound care, monitoring.",
            "description": "24/7 qualified nurses at your home — injections, wound care, monitoring.",
            "image": "/assets/categories/nursing-v2.jpg?v=2"
        },
        {
            "title": "Elderly Care",
            "category_name": "Elderly Care",
            "short_description": "Compassionate daily companionship and assisted living support.",
            "description": "Compassionate daily companionship and assisted living support.",
            "image": "/assets/categories/elder.jpg?v=2"
        },
        {
            "title": "Mother & Baby Care",
            "category_name": "Mother & Baby Care",
            "short_description": "Expert postnatal care for new mothers & newborns — feeding support, baby care & recovery.",
            "description": "Expert postnatal care for new mothers & newborns — feeding support, baby care & recovery.",
            "image": "/assets/categories/mother-baby.png"
        },
        {
            "title": "Physiotherapy & Recovery",
            "category_name": "Physiotherapy & Recovery",
            "short_description": "In-home rehab, mobility & pain management by expert therapists.",
            "description": "In-home rehab, mobility & pain management by expert therapists.",
            "image": "/assets/categories/physio-v2.jpg?v=2"
        },
        {
            "title": "Medical Equipment Rental",
            "category_name": "Medical Equipment Rental",
            "short_description": "Hospital-grade beds, oxygen, monitors — delivered & installed.",
            "description": "Hospital-grade beds, oxygen, monitors — delivered & installed.",
            "image": "/assets/categories/equipment-v2.jpg?v=2"
        },
        {
            "title": "ICU Setup",
            "category_name": "ICU Setup",
            "short_description": "Complete home ICU setup with ventilators, monitors & trained ICU nurses round the clock.",
            "description": "Complete home ICU setup with ventilators, monitors & trained ICU nurses round the clock.",
            "image": "/assets/categories/icu-setup.png"
        },
        {
            "title": "Home Sample Collection",
            "category_name": "Home Sample Collection",
            "short_description": "Convenient at-home blood tests & lab sample collection by certified phlebotomists.",
            "description": "Convenient at-home blood tests & lab sample collection by certified phlebotomists.",
            "image": "/assets/categories/home-sample.png"
        }
    ]

    for i, data in enumerate(fallbacks):
        service = Service(
            title=data["title"],
            slug=data["title"].lower().replace(" ", "-").replace("&", "and"),
            short_description=data["short_description"],
            description=data["description"],
            category_name=data["category_name"],
            featured_image=ImageAsset(url=data["image"]),
            status=ContentStatus.PUBLISHED,
            is_featured=True,
            order=i
        )
        await service.insert()
        print(f"Inserted: {service.title}")

if __name__ == "__main__":
    asyncio.run(main())
