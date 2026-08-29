import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb+srv://ulmindorg_db_user:homephysio123@cluster0.phsnman.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    dbs = await client.list_database_names()
    print("Databases:", dbs)
    db = client["home_physio_india"]
    colls = await db.list_collection_names()
    print("Collections in home_physio_india:", colls)
    
if __name__ == "__main__":
    asyncio.run(main())
