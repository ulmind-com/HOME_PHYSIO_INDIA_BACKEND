import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb+srv://ulmindorg_db_user:homephysio123@cluster0.phsnman.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    db = client["home_physio_india"]
    settings_doc = await db["website_settings"].find_one({})
    if settings_doc:
        print("Settings found")
        if "services_hero" in settings_doc:
            slides = settings_doc["services_hero"].get("slides", [])
            print(f"Number of slides: {len(slides)}")
            for s in slides:
                print(s.get("title"))
            
            # Let's update it here
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
            
            await db["website_settings"].update_one(
                {"_id": settings_doc["_id"]},
                {"$set": {"services_hero.slides": slides}}
            )
            print("Settings updated")
        else:
            print("No services_hero")
    else:
        print("No settings")

if __name__ == "__main__":
    asyncio.run(main())
