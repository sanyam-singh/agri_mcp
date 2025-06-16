from fastapi import HTTPException
from typing import List, Dict, Any
# Import model functions. The API_KEYS definition in models.external_apis is temporary.
# Ideally, API_KEYS would be passed to model functions from presenter, or models import from a central config.
from models import external_apis

# MCP_TOOLS and API_KEYS will be passed from main.py or a config module.
# For now, define them here as placeholders to make methods testable in isolation if needed.
# This will be removed/refactored once main.py passes the actual config.
TEMP_MCP_TOOLS = [
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
    # ... (other tools would be listed here if this wasn't temporary)
]
TEMP_API_KEYS = {
    "OPENWEATHER_API_KEY": "your_openweather_key_temp", # Placeholder
}


class ToolPresenter:
    def __init__(self, mcp_tools: List[Dict], api_keys: Dict):
        self.mcp_tools = mcp_tools
        self.api_keys = api_keys
        # Update the API_KEYS in the models module. This is one way to provide config.
        # A cleaner way might be dependency injection for model functions or a shared config module.
        external_apis.API_KEYS = api_keys

    def list_tools(self) -> List[Dict]:
        return self.mcp_tools

    def get_tool_details(self, tool_name: str) -> Dict:
        for tool in self.mcp_tools:
            if tool["name"].lower() == tool_name.lower():
                return tool
        raise HTTPException(status_code=404, detail="Tool not found")

    async def call_tool_function(self, tool_name: str, params: Dict) -> Any:
        # This method will map tool_name to the actual model function call.
        # It now uses the API_KEYS provided at initialization to the models module.

        if tool_name == "OpenWeatherMapAPI":
            return await external_apis.call_openweather_api(params)
        elif tool_name == "OpenMeteoAPI":
            return await external_apis.call_openmeteo_api(params)
        elif tool_name == "SoilGridsAPI":
            return await external_apis.call_soilgrids_api(params)
        elif tool_name == "NASA_Power_API":
            return await external_apis.call_nasa_power_api(params)
        elif tool_name == "USGS_Earthquake_API":
            return await external_apis.call_usgs_earthquake_api(params)
        elif tool_name == "World_Bank_Climate_API":
            return await external_apis.call_worldbank_climate_api(params)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown or not implemented tool: {tool_name}")

    def get_free_tools(self) -> Dict:
        free_tools_list = [tool for tool in self.mcp_tools if not tool.get("requires_api_key", False)]
        return {"free_tools": free_tools_list, "count": len(free_tools_list)}

    def get_premium_tools(self) -> Dict:
        premium_tools_list = [tool for tool in self.mcp_tools if tool.get("requires_api_key", False)]
        return {"premium_tools": premium_tools_list, "count": len(premium_tools_list)}

    async def test_tool_endpoint(self, tool_name: str) -> Any:
        # Define more robust test parameters, ensuring all required fields are met
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

        return await self.call_tool_function(tool_name, test_params_map[tool_name])
