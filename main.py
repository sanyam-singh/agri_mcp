from fastapi import FastAPI, Body, HTTPException
from typing import List, Dict, Optional
import uvicorn
import nest_asyncio
import httpx
import asyncio
from datetime import datetime, timedelta
import os
from pydantic import BaseModel

app = FastAPI(title="AgMCP API Server - Real APIs", version="2.0.0")

# Configuration - Add your API keys here
API_KEYS = {
    "OPENWEATHER_API_KEY": os.getenv("OPENWEATHER_API_KEY", "your_openweather_key"),
    "NASA_API_KEY": os.getenv("NASA_API_KEY", "DEMO_KEY"),  # NASA APIs work with DEMO_KEY
}

class APIRequest(BaseModel):
    tool_name: str
    params: Dict

# MCP Tools List with real API endpoints
MCP_TOOLS = [
    {
        "name": "OpenWeatherMapAPI",
        "description": "Get current weather data and forecasts",
        "parameters": {
            "lat": {"type": "float", "description": "Latitude"},
            "lon": {"type": "float", "description": "Longitude"},
            "q": {"type": "string", "description": "City name (alternative to lat/lon)"}
        },
        "requires_api_key": True
    },
    {
        "name": "OpenMeteoAPI",
        "description": "Free weather API with no key required",
        "parameters": {
            "latitude": {"type": "float", "description": "Latitude"},
            "longitude": {"type": "float", "description": "Longitude"},
            "current": {"type": "string", "description": "Current weather variables"},
            "hourly": {"type": "string", "description": "Hourly weather variables"}
        },
        "requires_api_key": False
    },
    {
        "name": "SoilGridsAPI",
        "description": "Global soil information from ISRIC",
        "parameters": {
            "lat": {"type": "float", "description": "Latitude"},
            "lon": {"type": "float", "description": "Longitude"},
            "property": {"type": "string", "description": "Soil property (phh2o, soc, sand, clay)"},
            "depth": {"type": "string", "description": "Depth (0-5cm, 5-15cm, etc.)"}
        },
        "requires_api_key": False
    },
    {
        "name": "NASA_Power_API",
        "description": "NASA POWER agroclimatology data",
        "parameters": {
            "lat": {"type": "float", "description": "Latitude"},
            "lon": {"type": "float", "description": "Longitude"},
            "start": {"type": "string", "description": "Start date (YYYYMMDD)"},
            "end": {"type": "string", "description": "End date (YYYYMMDD)"},
            "parameters": {"type": "string", "description": "Weather parameters"}
        },
        "requires_api_key": False
    },
    {
        "name": "USGS_Earthquake_API",
        "description": "USGS earthquake data (affects agriculture)",
        "parameters": {
            "starttime": {"type": "string", "description": "Start time"},
            "endtime": {"type": "string", "description": "End time"},
            "latitude": {"type": "float", "description": "Latitude"},
            "longitude": {"type": "float", "description": "Longitude"},
            "maxradiuskm": {"type": "integer", "description": "Search radius in km"}
        },
        "requires_api_key": False
    },
    {
        "name": "World_Bank_Climate_API",
        "description": "World Bank climate data",
        "parameters": {
            "country": {"type": "string", "description": "Country ISO code"},
            "type": {"type": "string", "description": "Data type (mavg, annualavg)"},
            "var": {"type": "string", "description": "Variable (tas, pr)"}
        },
        "requires_api_key": False
    }
]

@app.get("/v1/tools", response_model=List[Dict])
async def list_tools():
    """List all available AgMCP tools"""
    return MCP_TOOLS

@app.get("/v1/tool/{tool_name}", response_model=Dict)
async def get_tool(tool_name: str):
    """Get specific tool information"""
    for tool in MCP_TOOLS:
        if tool["name"].lower() == tool_name.lower():
            return tool
    raise HTTPException(status_code=404, detail="Tool not found")

@app.get("/v1/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

async def call_openweather_api(params: Dict) -> Dict:
    """Call OpenWeatherMap API"""
    api_key = API_KEYS.get("OPENWEATHER_API_KEY")
    if not api_key or api_key == "your_openweather_key":
        raise HTTPException(status_code=400, detail="OpenWeatherMap API key not configured or missing.")

    base_url = "https://api.openweathermap.org/data/2.5/weather"
    query_params = {"appid": api_key, "units": "metric"}

    if "q" in params:
        query_params["q"] = params["q"]
    elif "lat" in params and "lon" in params:
        query_params["lat"] = params["lat"]
        query_params["lon"] = params["lon"]
    else:
        raise HTTPException(status_code=400, detail="Either city name ('q') or latitude ('lat') and longitude ('lon') must be provided for OpenWeatherMap.")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(base_url, params=query_params)
            response.raise_for_status()
            data = response.json()
            return {
                "location": {"lat": data["coord"]["lat"], "lon": data["coord"]["lon"]},
                "city": data.get("name"),
                "country": data.get("sys", {}).get("country"),
                "temperature_celsius": data["main"]["temp"],
                "humidity_percent": data["main"]["humidity"],
                "pressure_hpa": data["main"]["pressure"],
                "weather": data["weather"][0]["description"],
                "wind_speed_ms": data["wind"]["speed"],
                "visibility_m": data.get("visibility", "N/A"),
                "timestamp": datetime.now().isoformat()
            }
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"OpenWeather API error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"OpenWeather API request failed: {str(e)}")


async def call_openmeteo_api(params: Dict) -> Dict:
    """Call Open-Meteo API (Free, no API key required)"""
    lat = params.get("latitude")
    lon = params.get("longitude")
    if lat is None or lon is None:
        raise HTTPException(status_code=400, detail="Latitude and longitude are required for OpenMeteo.")

    current_params = params.get("current", "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,soil_moisture_0_to_1cm")
    hourly_params = params.get("hourly", "temperature_2m,relative_humidity_2m,precipitation,soil_moisture_0_to_1cm")

    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current={current_params}&hourly={hourly_params}&forecast_days=1"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            current_data = data.get("current", {})
            hourly_data = data.get("hourly", {})

            def get_hourly_data(key, default_val=None, count=24):
                return hourly_data.get(key, [default_val]*count)[:count]

            return {
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "timezone": data.get("timezone"),
                "current": {
                    "time": current_data.get("time"),
                    "temperature_2m": current_data.get("temperature_2m"),
                    "relative_humidity_2m": current_data.get("relative_humidity_2m"),
                    "precipitation": current_data.get("precipitation"),
                    "wind_speed_10m": current_data.get("wind_speed_10m"),
                    "soil_moisture_0_to_1cm": current_data.get("soil_moisture_0_to_1cm")
                },
                "hourly_forecast": {
                    "time": get_hourly_data("time"),
                    "temperature_2m": get_hourly_data("temperature_2m"),
                    "relative_humidity_2m": get_hourly_data("relative_humidity_2m"),
                    "precipitation": get_hourly_data("precipitation"),
                    "soil_moisture_0_to_1cm": get_hourly_data("soil_moisture_0_to_1cm")
                },
                "timestamp": datetime.now().isoformat()
            }
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Open-Meteo API error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Open-Meteo API request failed: {str(e)}")

async def call_soilgrids_api(params: Dict) -> Dict:
    """Call ISRIC SoilGrids API (Free)"""
    lat = params.get("lat")
    lon = params.get("lon")
    if lat is None or lon is None:
        raise HTTPException(status_code=400, detail="Latitude and longitude are required for SoilGrids.")

    properties_param = params.get("property", "phh2o,soc,sand,clay,silt")
    depths_param = params.get("depth", "0-5cm,5-15cm,15-30cm")

    url = f"https://rest.isric.org/soilgrids/v2.0/properties/query?lon={lon}&lat={lat}&property={properties_param}&depth={depths_param}&value=mean"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            properties = {}
            if "properties" in data and "layers" in data["properties"]:
                for prop_layer in data["properties"]["layers"]:
                    prop_name = prop_layer["name"]
                    unit_measure = prop_layer["unit_measure"]
                    properties[prop_name] = {"unit": unit_measure, "depths": {}}
                    if "depths" in prop_layer:
                        for depth_info in prop_layer["depths"]:
                            depth_label = depth_info["label"]
                            # Ensure 'values' and 'mean' exist
                            if "values" in depth_info and "mean" in depth_info["values"]:
                                value = depth_info["values"]["mean"]
                                properties[prop_name]["depths"][depth_label] = value

            return {
                "location": {"lat": lat, "lon": lon},
                "properties": properties,
                "timestamp": datetime.now().isoformat()
            }
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"SoilGrids API error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"SoilGrids API request failed: {str(e)}")

async def call_nasa_power_api(params: Dict) -> Dict:
    """Call NASA POWER API (Free)"""
    lat = params.get("lat")
    lon = params.get("lon")
    if lat is None or lon is None:
        raise HTTPException(status_code=400, detail="Latitude and longitude are required for NASA POWER.")

    start_date = params.get("start", (datetime.now() - timedelta(days=7)).strftime("%Y%m%d"))
    end_date = params.get("end", datetime.now().strftime("%Y%m%d"))
    parameters_str = params.get("parameters", "T2M,PRECTOTCORR,RH2M,WS10M")

    url = (f"https://power.larc.nasa.gov/api/temporal/daily/point"
           f"?parameters={parameters_str}&community=AG&longitude={lon}&latitude={lat}"
           f"&start={start_date}&end={end_date}&format=JSON")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return {
                "location": {"lat": lat, "lon": lon},
                "date_range": {"start": start_date, "end": end_date},
                "parameters_queried": parameters_str.split(','),
                "data": data.get("properties", {}).get("parameter", {}),
                "metadata": {
                    "source": "NASA POWER",
                    "version": data.get("header", {}).get("api_version"),
                    "title": data.get("header", {}).get("title")
                },
                "timestamp": datetime.now().isoformat()
            }
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"NASA POWER API error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"NASA POWER API request failed: {str(e)}")


async def call_usgs_earthquake_api(params: Dict) -> Dict:
    """Call USGS Earthquake API (Free)"""
    lat = params.get("latitude")
    lon = params.get("longitude")
    if lat is None or lon is None:
        raise HTTPException(status_code=400, detail="Latitude and longitude are required for USGS Earthquake API.")

    radius_km = params.get("maxradiuskm", 100)
    start_time_str = params.get("starttime", (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"))
    end_time_str = params.get("endtime", datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))

    url = (f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson"
           f"&starttime={start_time_str}&endtime={end_time_str}"
           f"&latitude={lat}&longitude={lon}&maxradiuskm={radius_km}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            earthquakes = []
            if "features" in data:
                for feature in data["features"]:
                    properties = feature.get("properties", {})
                    geometry = feature.get("geometry", {})
                    coords = geometry.get("coordinates") if geometry else [None, None, None]
                    if coords is None: coords = [None, None, None] # Ensure coords is a list

                    earthquakes.append({
                        "magnitude": properties.get("mag"),
                        "place": properties.get("place"),
                        "time": datetime.fromtimestamp(properties.get("time")/1000).isoformat() if properties.get("time") else None,
                        "coordinates": {"longitude": coords[0], "latitude": coords[1], "depth_km": coords[2] if len(coords) > 2 else None},
                        "url": properties.get("url")
                    })
            return {
                "location_queried": {"latitude": lat, "longitude": lon, "radius_km": radius_km},
                "date_range_queried": {"start": start_time_str, "end": end_time_str},
                "earthquake_count": len(earthquakes),
                "earthquakes": earthquakes[:20],
                "timestamp": datetime.now().isoformat()
            }
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"USGS API error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"USGS API request failed: {str(e)}")

async def call_worldbank_climate_api(params: Dict) -> Dict:
    """Call World Bank Climate API (Free)"""
    country_code = params.get("country")
    if not country_code:
        raise HTTPException(status_code=400, detail="Country ISO3 code is required for World Bank Climate API.")

    data_type = params.get("type", "mavg")
    variable = params.get("var", "tas")
    start_year, end_year = params.get("start_year", "1991"), params.get("end_year", "2020")

    base_url = f"https://climatedataapi.worldbank.org/climateweb/rest/v1/country/{data_type}/{variable}/{start_year}/{end_year}/{country_code}.json"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(base_url)
            response.raise_for_status()
            data = response.json()
            return {
                "country_code": country_code,
                "variable": variable,
                "data_type_queried": data_type,
                "period_queried": f"{start_year}-{end_year}",
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
        except httpx.HTTPStatusError as e:
            detail_msg = f"World Bank API error: {e.response.status_code} - {e.response.text}"
            try:
                error_json = e.response.json()
                if isinstance(error_json, list) and error_json and "message" in error_json[0]: # WB specific error format
                    detail_msg = f"World Bank API error: {error_json[0]['message']}"
                elif isinstance(error_json, dict) and "fault" in error_json: # Another possible error format
                     detail_msg = f"World Bank API error: {error_json['fault']['faultstring']}"
            except ValueError: # If response is not JSON
                pass
            raise HTTPException(status_code=e.response.status_code, detail=detail_msg)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"World Bank API request failed: {str(e)}")


@app.post("/v1/functions/call")
async def call_real_api(request: APIRequest):
    """Call real agricultural APIs based on tool_name"""
    tool_name = request.tool_name
    params = request.params

    try:
        if tool_name == "OpenWeatherMapAPI":
            return await call_openweather_api(params)
        elif tool_name == "OpenMeteoAPI":
            return await call_openmeteo_api(params)
        elif tool_name == "SoilGridsAPI":
            return await call_soilgrids_api(params)
        elif tool_name == "NASA_Power_API":
            return await call_nasa_power_api(params)
        elif tool_name == "USGS_Earthquake_API":
            return await call_usgs_earthquake_api(params)
        elif tool_name == "World_Bank_Climate_API":
            return await call_worldbank_climate_api(params)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown or not implemented tool: {tool_name}")

    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Service request error for {tool_name}: {str(e)}")
    except Exception as e:
        print(f"Unexpected error calling tool {tool_name}: {e}") # Log error
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while calling {tool_name}: {str(e)}")

@app.get("/v1/tools/free")
async def get_free_tools():
    """Get tools that don't require API keys"""
    free_tools = [tool for tool in MCP_TOOLS if not tool.get("requires_api_key", False)]
    return {"free_tools": free_tools, "count": len(free_tools)}

@app.get("/v1/tools/premium")
async def get_premium_tools():
    """Get tools that require API keys"""
    premium_tools = [tool for tool in MCP_TOOLS if tool.get("requires_api_key", False)]
    return {"premium_tools": premium_tools, "count": len(premium_tools)}

@app.post("/v1/test/{tool_name}")
async def test_api_endpoint(tool_name: str):
    """Test API endpoints with sample data. This helps in quickly checking an API's health."""
    test_params_map = {
        "OpenWeatherMapAPI": {"lat": 40.7128, "lon": -74.0060},
        "OpenMeteoAPI": {"latitude": 40.7128, "longitude": -74.0060, "current": "temperature_2m", "hourly": "temperature_2m"},
        "SoilGridsAPI": {"lat": 40.7128, "lon": -74.0060, "property": "phh2o", "depth": "0-5cm"},
        "NASA_Power_API": {"lat": 40.7128, "lon": -74.0060, "start": "20240101", "end": "20240107", "parameters": "T2M"},
        "USGS_Earthquake_API": {"latitude": 34.0522, "longitude": -118.2437, "maxradiuskm": 200, "starttime": "2024-01-01T00:00:00", "endtime": "2024-01-31T23:59:59"},
        "World_Bank_Climate_API": {"country": "USA", "type": "mavg", "var": "tas", "start_year": "2010", "end_year": "2019"}
    }

    if tool_name not in test_params_map:
        raise HTTPException(status_code=404, detail=f"No test parameters defined for tool: {tool_name}")

    request_payload = APIRequest(tool_name=tool_name, params=test_params_map[tool_name])
    return await call_real_api(request_payload)


if __name__ == "__main__":
    print("🌾 Starting AgMCP Server with Real APIs...")
    print("📋 Available APIs:")
    for tool in MCP_TOOLS:
        key_required = "🔑" if tool.get("requires_api_key") else "🆓"
        print(f"  {key_required} {tool['name']}")
    print("\n🚀 FastAPI server starting on http://localhost:8000")
    print("📖 API docs available at http://localhost:8000/docs")
    print("🩺 Health check at http://localhost:8000/v1/health")

    nest_asyncio.apply()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
