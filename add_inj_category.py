import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb+srv://ulmindorg_db_user:homephysio123@cluster0.phsnman.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    db = client["home_physio_india"]
    
    cat = await db["categories"].find_one({"name": "Injection Administration"})
    if not cat:
        await db["categories"].insert_one({
            "name": "Injection Administration",
            "slug": "injection-administration",
            "description": "Prescribed injections safely administered at home by trained and verified nursing staff.",
            "image": {"url": "/assets/categories/injection.png"},
            "status": "published",
            "is_featured": True,
            "order": 8
        })
        print("Inserted Injection Administration category")
    else:
        print("Already exists")

if __name__ == "__main__":
    asyncio.run(main())
