from fastapi import FastAPI
# Remove: from starlette.graphql import GraphQLApp# Add this line

from starlette_graphene import GraphQLApp
from graphql_app.schema import schema

app = FastAPI()

app.add_route("/graphql", GraphQLApp(schema=schema))
