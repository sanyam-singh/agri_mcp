class HelloPresenter:
    def get_greeting(self, name: str) -> str:
        # In a more complex app, this might interact with a model
        # to fetch user data or persisted greeting templates.
        return f"Hello {name}"
