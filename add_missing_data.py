import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.models.service import Service, Category
from app.models.base import ImageAsset
from app.models.enums import ContentStatus

async def main():
    client = AsyncIOMotorClient("mongodb+srv://ulmindorg_db_user:homephysio123@cluster0.phsnman.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    db = client["home_physio_india"]
    await init_beanie(database=db, document_models=[Service, Category])

    # 1. Add Infection Control Service if not exists
    infection = await Service.find_one({"title": "Infection Control Nurse Services"})
    if not infection:
        s1 = Service(
            title="Infection Control Nurse Services",
            slug="infection-control-nurse-services",
            short_description="Professional infection prevention & control support, training and guidance for healthcare settings.",
            description="Professional infection prevention & control support, training and guidance for healthcare settings.",
            category_name="Infection Control Nurse Services",
            featured_image=ImageAsset(url="/assets/infection_control_desktop.jpg"),
            status=ContentStatus.PUBLISHED,
            is_featured=True,
            order=7
        )
        await s1.insert()
        print("Inserted Infection Control Service")
    
    # 2. Add Injection Administration Service if not exists
    injection = await Service.find_one({"title": "Injection Administration"})
    if not injection:
        s2 = Service(
            title="Injection Administration",
            slug="injection-administration",
            short_description="Prescribed injections safely administered at home by trained and verified nursing staff.",
            description="Prescribed injections safely administered at home by trained and verified nursing staff.",
            category_name="Injection Administration",
            featured_image=ImageAsset(url="/assets/categories/injection.png"),
            status=ContentStatus.PUBLISHED,
            is_featured=True,
            order=8
        )
        await s2.insert()
        print("Inserted Injection Administration Service")

    # 3. Update Settings for Hero Slider
    settings_coll = db["settings"]
    settings_doc = await settings_coll.find_one({})
    if settings_doc and "services_hero" in settings_doc:
        slides = settings_doc["services_hero"].get("slides", [])
        
        has_inf = any(s.get("title") == "Infection Control Nurse Services" for s in slides)
        has_inj = any(s.get("title") == "Injection Administration" for s in slides)
        
        if not has_inf:
            slides.append({
                "title": "Infection Control Nurse Services",
                "subtitle": "Professional infection prevention & control support, training and guidance for healthcare settings.",
                "button_text": "Learn More",
                "button_link": "/infection-control-nurse",
                "image_desktop": {"url": "/assets/infection_control_desktop.jpg"},
                "image_mobile": {"url": "/assets/infection_control_desktop.jpg"}
            })
        if not has_inj:
            slides.append({
                "title": "Injection Administration",
                "subtitle": "Prescribed injections safely administered at home by trained and verified nursing staff.",
                "button_text": "Book Injection",
                "button_link": "/nursing-care",
                "image_desktop": {"url": "/assets/categories/injection.png"},
                "image_mobile": {"url": "/assets/categories/injection.png"}
            })
            
        await settings_coll.update_one(
            {"_id": settings_doc["_id"]},
            {"$set": {"services_hero.slides": slides}}
        )
        print("Updated Hero Slider settings!")

if __name__ == "__main__":
    asyncio.run(main())
