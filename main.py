from fastapi import FastAPI
from graphene import Schema
from starlette.graphql import GraphQLApp
from graphql_app.schema import schema

app = FastAPI()

app.add_route("/graphql", GraphQLApp(schema=schema))
