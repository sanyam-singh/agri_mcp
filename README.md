# AgMCP Consolidated API Server

## Overview

The AgMCP (Agricultural Multi-source Data Collection Platform) Consolidated API Server provides a unified interface (both RESTful and GraphQL) to access a variety of agricultural, environmental, and climate-related data tools. It is built using FastAPI and Ariadne, following an MVP (Model-View-Presenter) architecture.

The server integrates several external data sources, providing mocked responses for some of the newer, more complex tools, while others connect to live APIs.

## Features

*   **Single Server Instance**: Serves both RESTful API and GraphQL API on the same port (default: 8000).
*   **FastAPI Backend**: High-performance asynchronous web framework.
*   **Ariadne GraphQL**: Pythonic way to build GraphQL servers.
*   **MVP Architecture**: Organized into Models (data fetching), Views (API endpoints), and Presenters (business logic).
*   **Tool-Based Data Access**: Provides access to various data sources, each treated as a "tool."
*   **Dynamic GraphQL Schema**: GraphQL queries for tools are dynamically generated based on the available tool list.
*   **Environment Variable Configuration**: For API keys like OpenWeatherMap.
*   **Interactive API Docs**:
    *   REST API (Swagger UI): Access at `/docs` (e.g., `http://localhost:8000/docs`).
    *   GraphQL Playground: Access at `/graphql` (e.g., `http://localhost:8000/graphql`).

### Available Tools

The server provides access to the following tools (status of external connection noted):

1.  **OpenWeatherMapAPI**: Current weather data and forecasts (Requires API key; connects to live API).
2.  **OpenMeteoAPI**: Free weather API (Connects to live API).
3.  **SoilGridsAPI**: Global soil information from ISRIC (Connects to live API).
4.  **NASA_Power_API**: NASA POWER agroclimatology data (Connects to live API).
5.  **USGS_Earthquake_API**: USGS earthquake data (Connects to live API).
6.  **World_Bank_Climate_API**: World Bank climate data (Connects to live API).
7.  **CHIRPSPrecipitation**: CHIRPS precipitation data (Currently Mocked).
8.  **SMAPSoilMoisture**: SMAP soil moisture data (Currently Mocked).
9.  **GRACEGroundwater**: GRACE groundwater storage data (Currently Mocked).
10. **Sentinel2Data**: Sentinel-2 satellite data summary (Currently Mocked).
11. **FAOPriceData**: FAO agricultural commodity price data (Currently Mocked).
12. **USDACropScape**: USDA CropScape crop type identification (Currently Mocked).
13. **ComprehensiveFarmData**: Aggregates data from several of the above (mocked) tools for a location (Currently Mocked).

## Tech Stack

*   **Backend Framework**: FastAPI
*   **GraphQL Library**: Ariadne
*   **HTTP Client**: HTTPX (for asynchronous external API calls)
*   **ASGI Server**: Uvicorn
*   **Data Handling (future use)**: Pandas (dependency included)

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    # git clone <repository_url>
    # cd <repository_directory>
    ```
    (Assuming you have already cloned the project)

2.  **Create a Virtual Environment:**
    It's highly recommended to use a Python virtual environment.
    ```bash
    python -m venv venv
    ```
    Activate it:
    *   On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        .\venv\Scripts\activate
        ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

### API Keys

Some tools require API keys to function correctly when their real implementations are active. Currently, `OpenWeatherMapAPI` requires a key for live data.

*   **OpenWeatherMap API Key**:
    Set the `OPENWEATHER_API_KEY` environment variable to your OpenWeatherMap API key.
    *   On macOS/Linux:
        ```bash
        export OPENWEATHER_API_KEY="your_actual_openweathermap_api_key"
        ```
    *   On Windows (PowerShell):
        ```bash
        $env:OPENWEATHER_API_KEY="your_actual_openweathermap_api_key"
        ```
    If this key is not set, calls to `OpenWeatherMapAPI` will fail or use a very limited default if the API allows.

## Running the Server

Once the setup is complete and configurations are set:

1.  **Start the Uvicorn Server:**
    From the project root directory, run:
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ```
    *   `--host 0.0.0.0`: Makes the server accessible from your local network.
    *   `--port 8000`: Runs the server on port 8000 by default.
    *   `--reload`: Enables auto-reload when code changes are detected (useful for development).

2.  **Accessing the Server:**
    *   **REST API Docs (Swagger UI)**: `http://localhost:8000/docs`
    *   **GraphQL Interface (Playground)**: `http://localhost:8000/graphql`
    *   **Health Check**: `http://localhost:8000/v1/health`

## API Usage Examples

### REST API

*   **List all tools:**
    ```bash
    curl http://localhost:8000/v1/tools
    ```

*   **Call a tool (e.g., OpenMeteoAPI):**
    ```bash
    curl -X POST -H "Content-Type: application/json" \
         -d '{"tool_name": "OpenMeteoAPI", "params": {"latitude": 52.52, "longitude": 13.41, "current": "temperature_2m"}}' \
         http://localhost:8000/v1/functions/call
    ```

### GraphQL API

Access the GraphQL interface at `http://localhost:8000/graphql` in your browser to use the interactive playground.

*   **List all tools:**
    ```graphql
    query ListTools {
      listMACTools {
        name
        description
        requires_api_key
      }
    }
    ```

*   **Call a tool (e.g., FAOPriceData - mocked):**
    ```graphql
    query CallFAO {
      call_FAOPriceData(params: {country: "Kenya", commodity: "maize"})
    }
    ```
    The `params` argument takes a JSON object. The result for `call_` queries is raw JSON from the tool.

## Adding New Tools (Brief Overview)

The server is structured to make adding new tools relatively straightforward:

1.  **Model (`models/external_apis.py`):**
    *   Add a new `async def your_new_tool_function(params: Dict) -> Dict:` function. This function should handle the logic for fetching and processing data for the new tool. If it calls external services, use `httpx.AsyncClient`. For now, you can add mocked responses similar to the newer tools.
2.  **Configuration (`main.py`):**
    *   Add a dictionary defining your new tool's `name`, `description`, `parameters`, and `requires_api_key` to the `MCP_TOOLS` list.
3.  **Presenter (`presenters/tool_presenter.py`):**
    *   In the `ToolPresenter.call_tool_function` method, add an `elif tool_name == "YourNewToolName":` block that calls `await external_apis.your_new_tool_function(params)`.

The REST endpoints for listing/getting tool details and the GraphQL schema for calling tools will update automatically based on the `MCP_TOOLS` list.
