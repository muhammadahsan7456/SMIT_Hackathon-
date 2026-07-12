"""
Test Snowflake Connection & Create Gold Views
==============================================
This script validates your Snowflake connection and creates
the necessary GOLD schema views for the dashboard.

Run this FIRST before running the dashboard!
"""

import sys
import os
from dotenv import load_dotenv
import snowflake.connector

# Load environment variables
load_dotenv()

SNOWFLAKE_CONFIG = {
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "database": os.getenv("SNOWFLAKE_DATABASE"),
    "schema": "GOLD",
    "role": os.getenv("SNOWFLAKE_ROLE"),
}

print("=" * 70)
print("🔍 SNOWFLAKE CONNECTION TEST")
print("=" * 70)

# Check environment variables
print("\n1️⃣  Checking Environment Variables...")
missing_vars = [k for k, v in SNOWFLAKE_CONFIG.items() if not v]
if missing_vars:
    print(f"   ❌ Missing variables: {', '.join(missing_vars)}")
    print("   Please check your .env file")
    sys.exit(1)
else:
    print("   ✅ All environment variables found")

# Test connection
print("\n2️⃣  Testing Snowflake Connection...")
try:
    conn = snowflake.connector.connect(
        user=SNOWFLAKE_CONFIG["user"],
        password=SNOWFLAKE_CONFIG["password"],
        account=SNOWFLAKE_CONFIG["account"],
        warehouse=SNOWFLAKE_CONFIG["warehouse"],
        database=SNOWFLAKE_CONFIG["database"],
        schema=SNOWFLAKE_CONFIG["schema"],
        role=SNOWFLAKE_CONFIG["role"],
        connect_timeout=10,
    )
    print("   ✅ Connected successfully!")
    
    # Test basic query
    print("\n3️⃣  Testing Query Execution...")
    cursor = conn.cursor()
    cursor.execute("SELECT CURRENT_USER(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA()")
    result = cursor.fetchone()
    print(f"   ✅ User: {result[0]}")
    print(f"   ✅ Warehouse: {result[1]}")
    print(f"   ✅ Database: {result[2]}")
    print(f"   ✅ Schema: {result[3]}")
    
    # Create GOLD schema if it doesn't exist
    print("\n4️⃣  Checking/Creating GOLD Schema...")
    try:
        cursor.execute("CREATE SCHEMA IF NOT EXISTS SMART_CITY_AQI.GOLD")
        print("   ✅ GOLD schema ready")
    except Exception as e:
        print(f"   ⚠️  {e}")
    
    # Create Gold views
    print("\n5️⃣  Creating GOLD Schema Views...")
    
    views = {
        "VW_CITY_AQI_SUMMARY": """
            CREATE OR REPLACE VIEW SMART_CITY_AQI.GOLD.VW_CITY_AQI_SUMMARY AS
            SELECT 
                CITY,
                COUNT(DISTINCT SENSOR_ID) as SENSOR_COUNT,
                ROUND(AVG(AQI), 2) as AVG_AQI,
                ROUND(AVG(PM25), 2) as AVG_PM25,
                ROUND(AVG(PM10), 2) as AVG_PM10,
                COUNT(*) as TOTAL_READINGS,
                MAX(READING_TIME) as LAST_UPDATE
            FROM SMART_CITY_AQI.RAW.IOT_READINGS
            WHERE READING_TIME >= DATEADD(hour, -24, CURRENT_TIMESTAMP())
            GROUP BY CITY
        """,
        
        "VW_LATEST_SENSOR": """
            CREATE OR REPLACE VIEW SMART_CITY_AQI.GOLD.VW_LATEST_SENSOR AS
            SELECT 
                SENSOR_ID,
                CITY,
                LATITUDE,
                LONGITUDE,
                PM25,
                PM10,
                CO,
                NO2,
                SO2,
                O3,
                TEMPERATURE,
                HUMIDITY,
                WIND_SPEED,
                AQI,
                AQI_CATEGORY,
                HEALTH_RISK,
                READING_TIME
            FROM SMART_CITY_AQI.RAW.IOT_READINGS
            WHERE READING_TIME = (SELECT MAX(READING_TIME) FROM SMART_CITY_AQI.RAW.IOT_READINGS)
            QUALIFY ROW_NUMBER() OVER (PARTITION BY SENSOR_ID ORDER BY READING_TIME DESC) = 1
        """,
        
        "VW_SENSOR_HISTORY": """
            CREATE OR REPLACE VIEW SMART_CITY_AQI.GOLD.VW_SENSOR_HISTORY AS
            SELECT 
                SENSOR_ID,
                CITY,
                AQI,
                AQI_CATEGORY,
                PM25,
                PM10,
                READING_TIME
            FROM SMART_CITY_AQI.RAW.IOT_READINGS
            WHERE READING_TIME >= DATEADD(day, -7, CURRENT_DATE())
            ORDER BY READING_TIME DESC
        """,
        
        "VW_AQI_STATUS": """
            CREATE OR REPLACE VIEW SMART_CITY_AQI.GOLD.VW_AQI_STATUS AS
            SELECT 
                AQI_CATEGORY,
                COUNT(*) as SENSOR_COUNT,
                ROUND(AVG(AQI), 2) as AVG_AQI
            FROM SMART_CITY_AQI.RAW.IOT_READINGS
            WHERE READING_TIME >= DATEADD(hour, -24, CURRENT_TIMESTAMP())
            GROUP BY AQI_CATEGORY
            ORDER BY AVG_AQI DESC
        """,
        
        "VW_POLLUTANT_SUMMARY": """
            CREATE OR REPLACE VIEW SMART_CITY_AQI.GOLD.VW_POLLUTANT_SUMMARY AS
            SELECT 
                ROUND(AVG(PM25), 2) as AVG_PM25,
                ROUND(AVG(PM10), 2) as AVG_PM10,
                ROUND(AVG(CO), 2) as AVG_CO,
                ROUND(AVG(NO2), 2) as AVG_NO2,
                ROUND(AVG(SO2), 2) as AVG_SO2,
                ROUND(AVG(O3), 2) as AVG_O3
            FROM SMART_CITY_AQI.RAW.IOT_READINGS
            WHERE READING_TIME >= DATEADD(hour, -24, CURRENT_TIMESTAMP())
        """
    }
    
    for view_name, view_sql in views.items():
        try:
            cursor.execute(view_sql)
            print(f"   ✅ {view_name} created/updated")
        except Exception as e:
            print(f"   ❌ {view_name}: {str(e)}")
    
    # Verify views were created
    print("\n6️⃣  Verifying Views...")
    cursor.execute("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.VIEWS 
        WHERE TABLE_SCHEMA = 'GOLD'
    """)
    views = cursor.fetchall()
    if views:
        print(f"   ✅ Found {len(views)} views in GOLD schema:")
        for v in views:
            print(f"      • {v[0]}")
    else:
        print("   ⚠️  No views found in GOLD schema")
    
    # Check if IOT_READINGS table has data
    print("\n7️⃣  Checking Data in RAW.IOT_READINGS...")
    cursor.execute("SELECT COUNT(*) FROM SMART_CITY_AQI.RAW.IOT_READINGS")
    count = cursor.fetchone()[0]
    print(f"   📊 Total readings: {count}")
    if count == 0:
        print("   ⚠️  No data found! Please run the ETL pipeline first:")
        print("      python main.py")
    else:
        print(f"   ✅ Data available for dashboard")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ SETUP COMPLETE! You can now run the dashboard:")
    print("   streamlit run dashboard/app.py")
    print("=" * 70)

except Exception as e:
    print(f"   ❌ Connection failed: {str(e)}")
    print("\n   Troubleshooting steps:")
    print("   1. Verify .env file has correct credentials")
    print("   2. Check Snowflake account name format (e.g., abc123-xy12345)")
    print("   3. Ensure your Snowflake account/user/password are active")
    print("   4. Check firewall/network connectivity to Snowflake")
    sys.exit(1)
