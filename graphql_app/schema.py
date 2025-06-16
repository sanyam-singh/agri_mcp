import graphene
from presenters.hello_presenter import HelloPresenter

class Query(graphene.ObjectType):
    hello = graphene.String(name=graphene.String(default_value="stranger"))

    def resolve_hello(self, info, name):
        presenter = HelloPresenter()
        return presenter.get_greeting(name=name)

schema = graphene.Schema(query=Query)
