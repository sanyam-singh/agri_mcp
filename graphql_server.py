from fastapi import FastAPI
from fastapi.responses import JSONResponse
from ariadne import QueryType, ScalarType, make_executable_schema, MutationType
from ariadne.asgi import GraphQL
import requests
import nest_asyncio
import uvicorn
import json
from graphql import Undefined # Import Undefined for literal_parser
from graphql.language import StringValueNode, BooleanValueNode, FloatValueNode, IntValueNode, ListValueNode, ObjectValueNode, EnumValueNode, NullValueNode


# Configuration
MCP_SERVER_URL = "http://localhost:8000"

def fetch_mcp_tools_definitions():
    try:
        response = requests.get(f"{MCP_SERVER_URL}/v1/tools")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching MCP tools definitions: {e}")
        return []

mcp_tools_definitions = fetch_mcp_tools_definitions()
if not mcp_tools_definitions:
    print("⚠️ Warning: MCP tools definitions could not be fetched. GraphQL API will be limited.")
else:
    print(f"✅ Fetched {len(mcp_tools_definitions)} MCP tool definitions.")

type_defs = """
    scalar JSON

    type Query {
        _empty: String
        listMACTools: [ToolDefinition]
        getMACTool(name: String!): ToolDefinition
    }

    type ToolDefinition {
        name: String
        description: String
        parameters: JSON
        requires_api_key: Boolean
    }
"""

query = QueryType()
json_scalar = ScalarType("JSON")

@json_scalar.serializer
def serialize_json(value):
    return value

@json_scalar.value_parser
def parse_json_value(value):
    # This is for variables. If a JSON variable is passed, it's already parsed.
    return value

@json_scalar.literal_parser
def parse_json_literal(ast, variables=None):
    # Handles inline JSON in the query string
    if isinstance(ast, StringValueNode):
        try:
            return json.loads(ast.value)
        except json.JSONDecodeError:
            # If it's a string but not valid JSON, return it as a plain string
            # or raise a GraphQL error if strict JSON is required.
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
    return Undefined # Should not happen for valid JSON parts


@query.field("listMACTools")
def resolve_list_mcp_tools(_, info):
    return mcp_tools_definitions

@query.field("getMACTool")
def resolve_get_mcp_tool(_, info, name: str):
    for tool in mcp_tools_definitions:
        if tool["name"].lower() == name.lower():
            return tool
    return None


if mcp_tools_definitions:
    for tool in mcp_tools_definitions:
        tool_name = tool['name']
        gql_field_name = tool_name.replace("-", "_").replace(" ", "_")

        # Add to type_defs dynamically
        type_defs += f"""
        extend type Query {{
            call_{gql_field_name}(params: JSON!): JSON
        }}
        """

        def make_resolver(current_tool_name):
            def resolver_function(_, info, params):
                try:
                    payload = {
                        "tool_name": current_tool_name,
                        "params": params
                    }
                    response = requests.post(f"{MCP_SERVER_URL}/v1/functions/call", json=payload)
                    response.raise_for_status()
                    return response.json()
                except requests.HTTPError as e:
                    error_detail = f"Failed calling {current_tool_name} on MCP server: {e.response.status_code}"
                    try:
                        mcp_error = e.response.json()
                        if "detail" in mcp_error:
                            error_detail = mcp_error["detail"]
                        return {"error": error_detail, "mcp_response": mcp_error}
                    except ValueError:
                        return {"error": error_detail, "mcp_response_text": e.response.text}
                except requests.RequestException as e:
                    return {"error": f"Request failed for {current_tool_name}: {str(e)}"}
                except Exception as e:
                    return {"error": f"Unexpected error processing {current_tool_name}: {str(e)}"}
            return resolver_function

        query.set_field(f"call_{gql_field_name}", make_resolver(tool_name))
else:
    print("Skipping dynamic GraphQL field creation as no tool definitions were loaded.")


schema = make_executable_schema(type_defs, query, json_scalar)

graphql_app = FastAPI(title="MCP GraphQL Server", version="1.0.0")
graphql_app.add_route("/graphql", GraphQL(schema, debug=True))

if __name__ == "__main__":
    nest_asyncio.apply()
    print("🚀 GraphQL server starting on http://localhost:9000/graphql")
    # Use string "graphql_server:graphql_app" for uvicorn reload to work
    uvicorn.run("graphql_server:graphql_app", host="0.0.0.0", port=9000, reload=True)
