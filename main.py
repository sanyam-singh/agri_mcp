from fastapi import FastAPI
# Remove: from starlette.graphql import GraphQLApp
from graphene_starlette.fastapi import GraphQLApp # Add this line
from graphql_app.schema import schema

app = FastAPI()

app.add_route("/graphql", GraphQLApp(schema=schema))
