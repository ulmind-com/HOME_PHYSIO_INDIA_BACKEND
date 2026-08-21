import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO = "mongodb+srv://ulmindorg_db_user:nupun123@cluster0.phsnman.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
PREFIX = "https://nupun-health-frontend.vercel.app"

async def update_image_url(image_obj):
    if not image_obj: return image_obj
    if isinstance(image_obj, dict) and "url" in image_obj:
        if image_obj["url"] and image_obj["url"].startswith("/assets/"):
            image_obj["url"] = PREFIX + image_obj["url"]
    elif isinstance(image_obj, str) and image_obj.startswith("/assets/"):
        return PREFIX + image_obj
    return image_obj

async def main():
    client = AsyncIOMotorClient(MONGO)
    db = client["nupun_health"]

    # 1. Update Categories
    cats = db["categories"].find({})
    async for c in cats:
        updated = False
        fi = c.get("featured_image")
        if fi and isinstance(fi, dict) and fi.get("url", "").startswith("/assets/"):
            fi["url"] = PREFIX + fi["url"]
            updated = True
        
        if updated:
            await db["categories"].update_one({"_id": c["_id"]}, {"$set": {"featured_image": fi}})
            print(f"Updated category: {c.get('slug')}")

    # 2. Update Blogs
    blogs = db["blogs"].find({})
    async for b in blogs:
        updated = False
        fi = b.get("featured_image")
        if fi and isinstance(fi, dict) and fi.get("url", "").startswith("/assets/"):
            fi["url"] = PREFIX + fi["url"]
            updated = True
        
        if updated:
            await db["blogs"].update_one({"_id": b["_id"]}, {"$set": {"featured_image": fi}})
            print(f"Updated blog: {b.get('slug')}")

    # 3. Update Settings (Comprehensive Services & Hero Slides)
    settings = db["website_settings"].find({})
    async for s in settings:
        updated = False
        
        # comprehensive_services
        comp = s.get("comprehensive_services", [])
        for cs in comp:
            img = cs.get("image")
            if isinstance(img, dict) and img.get("url", "").startswith("/assets/"):
                cs["image"]["url"] = PREFIX + img["url"]
                updated = True
            elif isinstance(img, str) and img.startswith("/assets/"):
                cs["image"] = PREFIX + img
                updated = True
                
        # hero_slides
        slides = s.get("hero_slides", [])
        for slide in slides:
            desktop = slide.get("image_desktop")
            if isinstance(desktop, dict) and desktop.get("url", "").startswith("/assets/"):
                slide["image_desktop"]["url"] = PREFIX + desktop["url"]
                updated = True
            elif isinstance(desktop, str) and desktop.startswith("/assets/"):
                slide["image_desktop"] = PREFIX + desktop
                updated = True
                
            mobile = slide.get("image_mobile")
            if isinstance(mobile, dict) and mobile.get("url", "").startswith("/assets/"):
                slide["image_mobile"]["url"] = PREFIX + mobile["url"]
                updated = True
            elif isinstance(mobile, str) and mobile.startswith("/assets/"):
                slide["image_mobile"] = PREFIX + mobile
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
