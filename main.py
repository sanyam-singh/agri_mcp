from fastapi import FastAPI, Body, HTTPException
from typing import List, Dict, Any
import uvicorn
import nest_asyncio
import os
from datetime import datetime
from pydantic import BaseModel # Keep for APIRequest if used by POST /v1/functions/call directly

# Ariadne imports
from ariadne import QueryType, ScalarType, make_executable_schema, MutationType
from ariadne.asgi import GraphQL
from graphql import Undefined as GraphQLUndefined # For JSON scalar literal parser
from graphql.language import StringValueNode, BooleanValueNode, FloatValueNode, IntValueNode, ListValueNode, ObjectValueNode, NullValueNode
import json # For JSON scalar literal parser

# MVP components
from presenters.tool_presenter import ToolPresenter
# Models are used by the presenter, so direct import here might not be needed unless for specific cases
# from models import external_apis

# --- Configuration ---
API_KEYS = {
    "OPENWEATHER_API_KEY": os.getenv("OPENWEATHER_API_KEY", "your_openweather_key"),
    "NASA_API_KEY": os.getenv("NASA_API_KEY", "DEMO_KEY"),
}

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
            "current": {"type": "string", "description": "Current weather variables (comma-separated)"},
            "hourly": {"type": "string", "description": "Hourly weather variables (comma-separated)"}
        },
        "requires_api_key": False
    },
    {
        "name": "SoilGridsAPI",
        "description": "Global soil information from ISRIC",
        "parameters": {
            "lat": {"type": "float", "description": "Latitude"},
            "lon": {"type": "float", "description": "Longitude"},
            "property": {"type": "string", "description": "Soil properties (comma-separated: phh2o,soc,sand,clay,silt)"},
            "depth": {"type": "string", "description": "Depth intervals (comma-separated: 0-5cm,5-15cm,15-30cm)"}
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
            "parameters": {"type": "string", "description": "Weather parameters (comma-separated e.g. T2M,PRECTOTCORR)"}
        },
        "requires_api_key": False # DEMO_KEY is often sufficient or no key needed
    },
    {
        "name": "USGS_Earthquake_API",
        "description": "USGS earthquake data",
        "parameters": {
            "starttime": {"type": "string", "description": "Start time (YYYY-MM-DDTHH:MM:SS)"},
            "endtime": {"type": "string", "description": "End time (YYYY-MM-DDTHH:MM:SS)"},
            "latitude": {"type": "float", "description": "Latitude for search center"},
            "longitude": {"type": "float", "description": "Longitude for search center"},
            "maxradiuskm": {"type": "integer", "description": "Search radius in km"}
        },
        "requires_api_key": False
    },
    {
        "name": "World_Bank_Climate_API",
        "description": "World Bank climate data",
        "parameters": {
            "country": {"type": "string", "description": "Country ISO3 code (e.g., USA, IND)"},
            "type": {"type": "string", "description": "Data type (e.g., mavg, annualavg)"},
            "var": {"type": "string", "description": "Variable (e.g., tas, pr for temperature, precipitation)"},
            "start_year": {"type": "string", "description": "Start year (YYYY)"},
            "end_year": {"type": "string", "description": "End year (YYYY)"}
        },
        "requires_api_key": False
    },
    {
        "name": "CHIRPSPrecipitation",
        "description": "Get CHIRPS precipitation data (mocked).",
        "parameters": {
            "lat": {"type": "float", "description": "Latitude"},
            "lon": {"type": "float", "description": "Longitude"},
            "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
            "temporal_resolution": {"type": "string", "description": "'daily', 'monthly', or 'seasonal' (default: daily)"}
        },
        "requires_api_key": False # Mocked, actual might vary
    },
    {
        "name": "SMAPSoilMoisture",
        "description": "Get SMAP soil moisture data (mocked).",
        "parameters": {
            "lat": {"type": "float", "description": "Latitude"},
            "lon": {"type": "float", "description": "Longitude"},
            "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
            "product": {"type": "string", "description": "SMAP product level (default: SPL3SMP)"}
        },
        "requires_api_key": False # Mocked
    },
    {
        "name": "GRACEGroundwater",
        "description": "Get GRACE groundwater storage data (mocked).",
        "parameters": {
            "lat": {"type": "float", "description": "Latitude"},
            "lon": {"type": "float", "description": "Longitude"},
            "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"}
        },
        "requires_api_key": False # Mocked
    },
    {
        "name": "Sentinel2Data",
        "description": "Get Sentinel-2 satellite data summary (mocked).",
        "parameters": {
            "lat": {"type": "float", "description": "Latitude"},
            "lon": {"type": "float", "description": "Longitude"},
            "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
            "cloud_cover_max": {"type": "integer", "description": "Max cloud coverage % (default: 20)"},
            "bands": {"type": "list_string", "description": "List of spectral bands (e.g., ['B04', 'B08']) (default: ['B04', 'B08', 'B11'])"}
        },
        "requires_api_key": False # Mocked, real Sentinel Hub access often needs auth
    },
    {
        "name": "FAOPriceData",
        "description": "Get FAO agricultural commodity price data (mocked).",
        "parameters": {
            "country": {"type": "string", "description": "Country name"},
            "commodity": {"type": "string", "description": "Commodity name"}
        },
        "requires_api_key": False # Mocked, actual API might have key option
    },
    {
        "name": "USDACropScape",
        "description": "Get USDA CropScape crop type identification (mocked).",
        "parameters": {
            "lat": {"type": "float", "description": "Latitude"},
            "lon": {"type": "float", "description": "Longitude"},
            "year": {"type": "integer", "description": "Year (default: current year)"}
        },
        "requires_api_key": False # Mocked
    },
    {
        "name": "ComprehensiveFarmData",
        "description": "Get comprehensive agricultural data for a location (mocked).",
        "parameters": {
            "lat": {"type": "float", "description": "Latitude"},
            "lon": {"type": "float", "description": "Longitude"},
            "country": {"type": "string", "description": "Country name for FAO price data (default: India)"},
            "commodity": {"type": "string", "description": "Commodity name for FAO price data (default: wheat)"}
        },
        "requires_api_key": False # Mocked
    }
]

# --- Pydantic Models for Request Bodies ---
class APIRequest(BaseModel):
    tool_name: str
    params: Dict

# --- FastAPI App Initialization ---
app = FastAPI(title="AgMCP Consolidated API Server (REST & GraphQL)", version="3.0.0")

# --- Presenter Initialization ---
# The presenter now gets the config from this central place
tool_presenter = ToolPresenter(mcp_tools=MCP_TOOLS, api_keys=API_KEYS)

# --- REST API Endpoints (Views) ---
@app.get("/v1/tools", response_model=List[Dict])
async def list_tools_route():
    return tool_presenter.list_tools()

@app.get("/v1/tool/{tool_name}", response_model=Dict)
async def get_tool_route(tool_name: str):
    return tool_presenter.get_tool_details(tool_name)

@app.get("/v1/health")
async def health_check_route():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.post("/v1/functions/call")
async def call_function_route(request: APIRequest):
    # FastAPI will handle HTTPException raised by the presenter
    return await tool_presenter.call_tool_function(request.tool_name, request.params)

@app.get("/v1/tools/free") # Matches old server
async def get_free_tools_route():
    return tool_presenter.get_free_tools()

@app.get("/v1/tools/premium") # Matches old server
async def get_premium_tools_route():
    return tool_presenter.get_premium_tools()

@app.post("/v1/test/{tool_name}") # Matches old server
async def test_api_endpoint_route(tool_name: str):
    return await tool_presenter.test_tool_endpoint(tool_name)


# --- GraphQL Setup (Ariadne) ---

# Base GraphQL type definitions
type_defs = """
    scalar JSON

    type Query {
        _empty: String # Placeholder
        listMACTools: [ToolDefinition]
        getMACTool(name: String!): ToolDefinition
        # Dynamic tool call fields will be added here
    }

    type ToolDefinition {
        name: String
        description: String
        parameters: JSON
        requires_api_key: Boolean
    }
"""

query_type = QueryType()
json_scalar = ScalarType("JSON")

@json_scalar.serializer
def serialize_json(value):
    return value

@json_scalar.value_parser
def parse_json_value(value):
    return value

@json_scalar.literal_parser
def parse_json_literal(ast, variables=None):
    if isinstance(ast, StringValueNode):
        try:
            return json.loads(ast.value)
        except json.JSONDecodeError:
            return ast.value
    elif isinstance(ast, ObjectValueNode):
        obj = {}
        for field in ast.fields:
            obj[field.name.value] = parse_json_literal(field.value, variables)
        return obj
    elif isinstance(ast, ListValueNode):
        return [parse_json_literal(value, variables) for value in ast.values]
    elif isinstance(ast, IntValueNode):
        return int(ast.value)
    elif isinstance(ast, FloatValueNode):
        return float(ast.value)
    elif isinstance(ast, BooleanValueNode):
        return ast.value
    elif isinstance(ast, NullValueNode):
        return None
    return GraphQLUndefined


# GraphQL Resolvers for static queries
@query_type.field("listMACTools")
async def resolve_list_mcp_tools_gql(_, info):
    # The presenter's list_tools is synchronous, but resolvers can be async
    return tool_presenter.list_tools()

@query_type.field("getMACTool")
async def resolve_get_mcp_tool_gql(_, info, name: str):
    try:
        return tool_presenter.get_tool_details(name)
    except HTTPException as e: # Catch presenter's not found error
        # Return None or a specific GraphQL error type
        # For simplicity, returning None if not found by presenter
        if e.status_code == 404:
            return None
        # Re-raise if it's another type of HTTPException, Ariadne will handle it
        raise

# Dynamically add query fields for each MCP tool
if MCP_TOOLS:
    for tool in MCP_TOOLS:
        tool_name_orig = tool['name']
        # Sanitize tool_name to be a valid GraphQL field name
        gql_field_name = tool_name_orig.replace("-", "_").replace(" ", "_")

        type_defs += f"""
        extend type Query {{
            call_{gql_field_name}(params: JSON!): JSON
        }}
        """

        # Define resolver function for this specific tool
        # This uses a closure to capture the correct tool_name_orig for each resolver
        def make_graphql_resolver(current_tool_name_for_resolver: str):
            async def dynamic_resolver(_, info, params: Dict[str, Any]):
                try:
                    # Use the tool_presenter to call the function
                    return await tool_presenter.call_tool_function(current_tool_name_for_resolver, params)
                except HTTPException as e:
                    # Convert HTTPException to a GraphQL-friendly error response
                    # Ariadne by default will turn exceptions into GraphQL errors.
                    # We can customize this if needed by returning a dict with an 'error' key.
                    # For now, let Ariadne handle it or raise it directly.
                    # Example: return {"error": {"message": e.detail, "status_code": e.status_code}}
                    raise # Let Ariadne format the error
                except Exception as e:
                    # Catch any other unexpected errors
                    # Log this error on the server for debugging
                    print(f"Unexpected GraphQL error calling tool {current_tool_name_for_resolver}: {e}")
                    # Return a generic error or raise for Ariadne to handle
                    raise Exception(f"An internal error occurred while calling {current_tool_name_for_resolver}.")
            return dynamic_resolver

        query_type.set_field(f"call_{gql_field_name}", make_graphql_resolver(tool_name_orig))
else:
    print("Warning: MCP_TOOLS is empty. No dynamic GraphQL tool call fields will be created.")


# Create executable schema
schema = make_executable_schema(type_defs, query_type, json_scalar)

# Mount Ariadne GraphQL app on the main FastAPI app
app.add_route("/graphql", GraphQL(schema, debug=True))


# --- Main Execution ---
if __name__ == "__main__":
    print("🌾 Starting AgMCP Consolidated Server (REST & GraphQL)...")
    print(f"📋 {len(MCP_TOOLS)} Tools configured.")
    print("🚀 Server starting on http://localhost:8000")
    print("📖 REST API docs available at http://localhost:8000/docs")
    print("☸️ GraphQL interface available at http://localhost:8000/graphql")
    print("🩺 Health check at http://localhost:8000/v1/health")

    nest_asyncio.apply()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
