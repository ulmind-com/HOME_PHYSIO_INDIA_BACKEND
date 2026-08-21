import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO = "mongodb+srv://ulmindorg_db_user:nupun123@cluster0.phsnman.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

async def main():
    client = AsyncIOMotorClient(MONGO)
    db = client["nupun_health"]

    # 1. Update Categories
    cats = db["categories"].find({})
    async for c in cats:
        updated = False
        fi = c.get("featured_image")
        if fi and isinstance(fi, dict) and fi.get("url"):
            if "infection_control" in fi["url"]:
                fi["url"] = fi["url"].replace("infection_control", "ic_nurse")
                updated = True
        
        if updated:
            await db["categories"].update_one({"_id": c["_id"]}, {"$set": {"featured_image": fi}})
            print(f"Updated category: {c.get('slug')}")

    # 2. Update Blogs
    blogs = db["blogs"].find({})
    async for b in blogs:
        updated = False
        fi = b.get("featured_image")
        if fi and isinstance(fi, dict) and fi.get("url"):
            if "infection_control" in fi["url"]:
                fi["url"] = fi["url"].replace("infection_control", "ic_nurse")
                updated = True
        
        if updated:
            await db["blogs"].update_one({"_id": b["_id"]}, {"$set": {"featured_image": fi}})
            print(f"Updated blog: {b.get('slug')}")

    # 3. Update Settings (Comprehensive Services & Hero Slides)
    settings = db["website_settings"].find({})
    async for s in settings:
        updated = False
        
        comp = s.get("comprehensive_services", [])
        for cs in comp:
            img = cs.get("image")
            if isinstance(img, dict) and img.get("url") and "infection_control" in img["url"]:
                cs["image"]["url"] = img["url"].replace("infection_control", "ic_nurse")
                updated = True
            elif isinstance(img, str) and "infection_control" in img:
                cs["image"] = img.replace("infection_control", "ic_nurse")
                updated = True
                
        slides = s.get("hero_slides", [])
        for slide in slides:
            desktop = slide.get("image_desktop")
            if isinstance(desktop, dict) and desktop.get("url") and "infection_control" in desktop["url"]:
                slide["image_desktop"]["url"] = desktop["url"].replace("infection_control", "ic_nurse")
                updated = True
            elif isinstance(desktop, str) and "infection_control" in desktop:
                slide["image_desktop"] = desktop.replace("infection_control", "ic_nurse")
                updated = True
                
            mobile = slide.get("image_mobile")
            if isinstance(mobile, dict) and mobile.get("url") and "infection_control" in mobile["url"]:
                slide["image_mobile"]["url"] = mobile["url"].replace("infection_control", "ic_nurse")
                updated = True
            elif isinstance(mobile, str) and "infection_control" in mobile:
                slide["image_mobile"] = mobile.replace("infection_control", "ic_nurse")
                updated = True

        if updated:
            await db["website_settings"].update_one(
                {"_id": s["_id"]}, 
                {"$set": {
                    "comprehensive_services": comp,
                    "hero_slides": slides
                }}
            )
            print(f"Updated settings")

    print("Done")

if __name__ == "__main__":
    asyncio.run(main())
