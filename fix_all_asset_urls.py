import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO = "mongodb+srv://ulmindorg_db_user:homephysio123@cluster0.phsnman.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
PREFIX = "https://home-physio-india-frontend.vercel.app"

async def main():
    client = AsyncIOMotorClient(MONGO)
    db = client["home_physio_india"]

    # 3. Update Settings (Comprehensive Services & Hero Slides)
    settings = db["website_settings"].find({})
    async for s in settings:
        updated = False
        
        comp = s.get("comprehensive_services", [])
        for cs in comp:
            img = cs.get("image")
            if isinstance(img, dict) and img.get("url") and img["url"].startswith("/assets/"):
                cs["image"]["url"] = PREFIX + img["url"]
                updated = True
            elif isinstance(img, str) and img.startswith("/assets/"):
                cs["image"] = PREFIX + img
                updated = True
                
        if updated:
            await db["website_settings"].update_one(
                {"_id": s["_id"]}, 
                {"$set": {
                    "comprehensive_services": comp
                }}
            )
            print(f"Updated settings with PREFIX")

    print("Done")

if __name__ == "__main__":
    asyncio.run(main())
