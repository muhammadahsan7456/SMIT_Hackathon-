from database.snowflake_db import insert_sensor_data
import random
from datetime import datetime


# ==========================
# Karachi Smart City Sensors
# ==========================

SENSORS = [
    {
        "sensor_id": "KHI001",
        "city": "Karachi",
        "area": "Saddar",
        "latitude": 24.8607,
        "longitude": 67.0011,
    },
    {
        "sensor_id": "KHI002",
        "city": "Karachi",
        "area": "Clifton",
        "latitude": 24.8138,
        "longitude": 67.0305,
    },
    {
        "sensor_id": "KHI003",
        "city": "Karachi",
        "area": "DHA",
        "latitude": 24.8051,
        "longitude": 67.0308,
    },
    {
        "sensor_id": "KHI004",
        "city": "Karachi",
        "area": "Gulshan-e-Iqbal",
        "latitude": 24.9219,
        "longitude": 67.0921,
    },
    {
        "sensor_id": "KHI005",
        "city": "Karachi",
        "area": "Nazimabad",
        "latitude": 24.9167,
        "longitude": 67.0333,
    },
    {
        "sensor_id": "KHI006",
        "city": "Karachi",
        "area": "Korangi",
        "latitude": 24.8325,
        "longitude": 67.1360,
    },
    {
        "sensor_id": "KHI007",
        "city": "Karachi",
        "area": "Landhi",
        "latitude": 24.8400,
        "longitude": 67.1900,
    },
    {
        "sensor_id": "KHI008",
        "city": "Karachi",
        "area": "North Karachi",
        "latitude": 24.9500,
        "longitude": 67.0600,
    },
    {
        "sensor_id": "KHI009",
        "city": "Karachi",
        "area": "Malir",
        "latitude": 24.9000,
        "longitude": 67.2000,
    },
    {
        "sensor_id": "KHI010",
        "city": "Karachi",
        "area": "Orangi",
        "latitude": 24.9500,
        "longitude": 66.9900,
    },
]


# ==========================
# AQI Calculator
# ==========================

def calculate_aqi(pm25):

    if pm25 <= 12:
        return 50, "Good", "Air quality is satisfactory."

    elif pm25 <= 35.4:
        return 100, "Moderate", "Sensitive people should reduce prolonged outdoor activities."

    elif pm25 <= 55.4:
        return 150, "Unhealthy for Sensitive Groups", "Children and elderly should avoid outdoor exercise."

    elif pm25 <= 150.4:
        return 200, "Unhealthy", "Everyone should reduce outdoor activities."

    elif pm25 <= 250.4:
        return 300, "Very Unhealthy", "Health alert! Avoid going outside."

    else:
        return 500, "Hazardous", "Emergency conditions! Stay indoors."


# ==========================
# Generate Fake Sensor Data
# ==========================

def generate_sensor_data(sensor):

    pm25 = round(random.uniform(10, 250), 2)

    aqi, category, advice = calculate_aqi(pm25)

    return {

        "sensor_id": sensor["sensor_id"],

        "city": sensor["city"],

        "area": sensor["area"],

        "latitude": sensor["latitude"],

        "longitude": sensor["longitude"],

        "pm25": pm25,

        "pm10": round(random.uniform(20, 350), 2),

        "co": round(random.uniform(0.2, 8.0), 2),

        "no2": round(random.uniform(5, 120), 2),

        "so2": round(random.uniform(2, 60), 2),

        "o3": round(random.uniform(10, 180), 2),

        "temperature": round(random.uniform(20, 42), 1),

        "humidity": round(random.uniform(30, 90), 1),

        "wind_speed": round(random.uniform(1, 20), 1),

        "aqi": aqi,

        "aqi_category": category,

        "health_risk": advice,

        "reading_time": datetime.now()

    }


# ==========================
# Main Program
# ==========================

if __name__ == "__main__":

    print("=" * 70)
    print("🚀 Smart City AQI Simulator Started")
    print("=" * 70)

    for sensor in SENSORS:

        reading = generate_sensor_data(sensor)

        print(reading)

        insert_sensor_data(reading)

    print("=" * 70)
    print("✅ All Sensor Data Inserted Successfully")
    print("=" * 70)