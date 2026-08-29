import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb+srv://ulmindorg_db_user:homephysio123@cluster0.phsnman.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    db = client["home_physio_india"]
    cats = await db["categories"].find().to_list(100)
    print(f"Found {len(cats)} categories")
    for c in cats:
        print(c.get("name"), c.get("slug"))

if __name__ == "__main__":
    asyncio.run(main())
