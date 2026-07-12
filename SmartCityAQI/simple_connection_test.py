"""
Simple Snowflake Connection Test
Minimal dependencies - just needs snowflake-connector-python
"""

import os
from dotenv import load_dotenv

print("=" * 60)
print("🔌 SNOWFLAKE CONNECTION TEST (Simple)")
print("=" * 60)

# Load environment
load_dotenv()

config = {
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "database": os.getenv("SNOWFLAKE_DATABASE"),
    "role": os.getenv("SNOWFLAKE_ROLE"),
}

print("\n1. Checking .env file...")
missing = [k for k, v in config.items() if not v]
if missing:
    print(f"   ❌ Missing: {missing}")
    exit(1)
print("   ✅ All variables found\n")

print("2. Attempting connection...")
try:
    import snowflake.connector
    conn = snowflake.connector.connect(
        user=config["user"],
        password=config["password"],
        account=config["account"],
        warehouse=config["warehouse"],
        database=config["database"],
        role=config["role"],
        connect_timeout=10,
    )
    print("   ✅ Connected!\n")
    
    cursor = conn.cursor()
    cursor.execute("SELECT CURRENT_USER(), CURRENT_DATABASE()")
    user, db = cursor.fetchone()
    print(f"   User: {user}")
    print(f"   Database: {db}\n")
    
    # Check if tables exist
    print("3. Checking tables...")
    cursor.execute("SHOW TABLES IN SMART_CITY_AQI.RAW")
    tables = [row[1] for row in cursor.fetchall()]
    
    if "IOT_READINGS" in tables:
        cursor.execute("SELECT COUNT(*) FROM SMART_CITY_AQI.RAW.IOT_READINGS")
        count = cursor.fetchone()[0]
        print(f"   ✅ IOT_READINGS table exists with {count} rows\n")
    else:
        print(f"   ❌ IOT_READINGS not found. Tables: {tables}\n")
    
    # Check if GOLD schema exists
    print("4. Checking GOLD schema...")
    cursor.execute("SHOW SCHEMAS IN SMART_CITY_AQI")
    schemas = [row[1] for row in cursor.fetchall()]
    
    if "GOLD" in schemas:
        print("   ✅ GOLD schema exists")
        cursor.execute("SHOW VIEWS IN SMART_CITY_AQI.GOLD")
        views = [row[1] for row in cursor.fetchall()]
        print(f"   ✅ Views found: {len(views)}")
        for v in views[:5]:
            print(f"      • {v}")
    else:
        print(f"   ❌ GOLD schema missing. Schemas: {schemas}")
        print("   💡 Tip: Run test_snowflake_connection.py to auto-create it\n")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ CONNECTION SUCCESSFUL!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. python test_snowflake_connection.py  (auto-create views)")
    print("2. streamlit run dashboard/app.py       (run dashboard)")
    
except Exception as e:
    print(f"   ❌ Error: {e}\n")
    print("=" * 60)
    print("Troubleshooting:")
    print("• Check .env file has correct credentials")
    print("• Verify account name (not full URL)")
    print("• Ensure Snowflake account is active")
    print("=" * 60)
