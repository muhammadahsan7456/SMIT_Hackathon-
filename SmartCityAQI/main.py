import snowflake.connector
from config import SNOWFLAKE_CONFIG


def test_connection():
    try:
        conn = snowflake.connector.connect(
            user=SNOWFLAKE_CONFIG["user"],
            password=SNOWFLAKE_CONFIG["password"],
            account=SNOWFLAKE_CONFIG["account"],
            warehouse=SNOWFLAKE_CONFIG["warehouse"],
            database=SNOWFLAKE_CONFIG["database"],
            schema=SNOWFLAKE_CONFIG["schema"],
            role=SNOWFLAKE_CONFIG["role"],
        )

        print("✅ Connected to Snowflake Successfully!")

        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_VERSION();")

        version = cursor.fetchone()

        print(f"Snowflake Version: {version[0]}")

        cursor.close()
        conn.close()

    except Exception as e:
        print("❌ Connection Failed!")
        print(e)


if __name__ == "__main__":
    test_connection()