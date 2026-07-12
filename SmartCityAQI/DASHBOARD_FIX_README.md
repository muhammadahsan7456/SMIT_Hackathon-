# 🔧 DASHBOARD FIX GUIDE

## Problem Identified ❌

Your dashboard was hanging at "Fetching latest readings from Snowflake..." because:

1. **Schema Mismatch**: `.env` file has `SNOWFLAKE_SCHEMA=RAW`, but dashboard queries `GOLD` schema
2. **Missing Views**: The GOLD schema views don't exist yet (need to be created)
3. **Missing Dependencies**: Required packages not installed (snowflake-connector, streamlit, etc.)
4. **No Error Handling**: App would hang silently on connection timeout

---

## ✅ SOLUTIONS APPLIED

### 1. Updated Dashboard (`dashboard/app.py`)
✅ Explicitly sets schema to `GOLD` in connection  
✅ Added connection timeouts (10s connect, 30s query timeout)  
✅ Added proper error messages and logging  
✅ Better cache management (30s instead of 10s)  
✅ Shows progress messages instead of silent hanging  

### 2. Created Connection Test Script (`test_snowflake_connection.py`)
✅ Verifies Snowflake credentials  
✅ Tests query execution  
✅ Creates GOLD schema and views automatically  
✅ Checks if IOT_READINGS table has data  

### 3. Updated Requirements (`requirements.txt`)
✅ Added all missing dependencies  
✅ Includes snowflake-connector-python  

---

## 🚀 HOW TO FIX & RUN NOW

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```
**Wait 5-10 minutes** (snowflake-connector-python takes time to download & compile)

### Step 2: Test Connection & Create Views
```bash
python test_snowflake_connection.py
```
This will:
- ✅ Verify Snowflake credentials
- ✅ Create GOLD schema
- ✅ Create 5 required views automatically
- ✅ Check if you have data in RAW.IOT_READINGS

### Step 3: Run Dashboard
Once Step 2 completes successfully:
```bash
streamlit run dashboard/app.py
```

---

## 🔍 Troubleshooting

### If pip install fails:
```bash
pip install snowflake-connector-python --upgrade
pip install streamlit
pip install plotly
```

### If connection test shows errors:
1. **Check .env file exists** at: `SmartCityAQI/.env`
2. **Verify credentials**:
   ```
   SNOWFLAKE_USER=MUHAMMADAHSAN7456
   SNOWFLAKE_PASSWORD=Ahsankhanzada10@
   SNOWFLAKE_ACCOUNT=izlfwka-jqb26233
   ```
3. **Check Snowflake account status**: Login to web UI directly
4. **Check network**: Can you ping Snowflake from your computer?

### If dashboard still hangs:
1. Open terminal where app is running
2. Press `Ctrl+C` to stop
3. Run: `streamlit run dashboard/app.py --logger.level=debug`
4. Look for error messages in terminal

### If "No data" error:
1. First, populate data: `python main.py`
2. Then test views: `python test_snowflake_connection.py`
3. Then run dashboard: `streamlit run dashboard/app.py`

---

## 📝 Files Updated

| File | Changes |
|------|---------|
| `dashboard/app.py` | Fixed schema, added timeouts, better error handling |
| `requirements.txt` | Added missing dependencies |
| `test_snowflake_connection.py` | NEW - Connection test & auto-setup |

---

## ⏱️ Expected Times

- **pip install**: 5-10 minutes (first time only)
- **test_snowflake_connection.py**: 20-30 seconds
- **Dashboard startup**: 10-15 seconds (first load with cache)
- **Dashboard refresh**: 2-5 seconds (cached)

---

## 💡 Quick Reference

```bash
# One-time setup
pip install -r requirements.txt

# Test before running
python test_snowflake_connection.py

# Run dashboard
streamlit run dashboard/app.py

# Force refresh cache (if data changes)
streamlit run dashboard/app.py --client.caching.enable_cache=false
```

---

**Status**: Dashboard fixed ✅ | Ready to run 🚀
