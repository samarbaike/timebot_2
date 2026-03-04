import os
import asyncio
import datetime
import pandas as pd
from database.db import DatabaseManager
from dotenv import load_dotenv
load_dotenv()
db_url = os.getenv("DB_URL")

async def main():
    db = DatabaseManager()
    await db.connect(db_url)
    
    #1. Fetch the data
    records = await db.migration.get()
    data = [dict(record) for record in records]
    if not data:
        print("Database is empty")

    #2. Ingest into Pandas
    df = pd.DataFrame(data)

    #3. Pivot the Table
    pivot_df = df.pivot_table(
        index='full_name',
        columns='log_date',
        values='pages_read',
        aggfunc='sum',
        fill_value=0
    )

    #4. Formate the date columns to strings
    pivot_df.columns = [col.strftime('%Y-%m-%d') if isinstance (col, datetime.date) else col for col in pivot_df.columns]


    #5. Flatten the index and rename the main column
    final_df = pivot_df.reset_index()
    final_df = final_df.rename(columns={'full_name':'Name Surname'})

    print(final_df.to_string())

if __name__=="__main__":
    asyncio.run(main())
