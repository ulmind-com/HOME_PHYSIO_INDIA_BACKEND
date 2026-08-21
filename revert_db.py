import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb+srv://ulmindorg_db_user:nupun123@cluster0.phsnman.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    db = client["nupun_health"]
    
    settings_coll = db["website_settings"]
    doc = await settings_coll.find_one({})
    if doc:
        update = {}
        
        # 1. Unset comprehensive_services to force fallback
        if "comprehensive_services" in doc:
            update["$unset"] = {"comprehensive_services": ""}
            
        # 2. Remove the 2 slides we added from services_hero.slides
        if "services_hero" in doc:
            slides = doc["services_hero"].get("slides", [])
            original_slides = [s for s in slides if s.get("title") not in ["Infection Control Nurse Services", "Injection Administration"]]
            
            if "$set" not in update:
                update["$set"] = {}
            update["$set"]["services_hero.slides"] = original_slides
            
        if update:
            await settings_coll.update_one({"_id": doc["_id"]}, update)
            print("Reverted backend settings.")
        else:
            print("Nothing to revert in settings.")
            
if __name__ == "__main__":
    asyncio.run(main())
