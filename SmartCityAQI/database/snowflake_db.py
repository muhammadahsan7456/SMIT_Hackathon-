import snowflake.connector
from config import SNOWFLAKE_CONFIG


def get_connection():
    """
    Create and return a Snowflake connection.
    """
    conn = snowflake.connector.connect(
        user=SNOWFLAKE_CONFIG["user"],
        password=SNOWFLAKE_CONFIG["password"],
        account=SNOWFLAKE_CONFIG["account"],
        warehouse=SNOWFLAKE_CONFIG["warehouse"],
        database=SNOWFLAKE_CONFIG["database"],
        schema=SNOWFLAKE_CONFIG["schema"],
        role=SNOWFLAKE_CONFIG["role"],
    )
    return conn


def insert_sensor_data(reading):
    """
    Insert one sensor reading into Snowflake.
    """

    conn = get_connection()
    cursor = conn.cursor()

    try:
        sql = """
        INSERT INTO RAW.IOT_READINGS
        (
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
        )
        VALUES
        (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        """

        cursor.execute(
            sql,
            (
                reading["sensor_id"],
                reading["city"],
                reading["latitude"],
                reading["longitude"],
                reading["pm25"],
                reading["pm10"],
                reading["co"],
                reading["no2"],
                reading["so2"],
                reading["o3"],
                reading["temperature"],
                reading["humidity"],
                reading["wind_speed"],
                reading["aqi"],
                reading["aqi_category"],
                reading["health_risk"],
                reading["reading_time"],
            ),
        )

        conn.commit()

        print(f"✅ {reading['sensor_id']} inserted successfully.")

    except Exception as e:
        print("❌ Error:", e)

    finally:
        cursor.close()
        conn.close()



        