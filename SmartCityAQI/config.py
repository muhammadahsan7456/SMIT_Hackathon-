import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAQ API Configuration
OPENAQ_API_URL = "https://api.openaq.org/v3"

# Snowflake Configuration
SNOWFLAKE_CONFIG = {
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "database": os.getenv("SNOWFLAKE_DATABASE"),
    "schema": os.getenv("SNOWFLAKE_SCHEMA"),
    "role": os.getenv("SNOWFLAKE_ROLE"),
}