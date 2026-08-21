import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb+srv://ulmindorg_db_user:nupun123@cluster0.phsnman.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    dbs = await client.list_database_names()
    print("Databases:", dbs)
    db = client["nupun_health"]
    colls = await db.list_collection_names()
    print("Collections in nupun_health:", colls)
    
if __name__ == "__main__":
    asyncio.run(main())
