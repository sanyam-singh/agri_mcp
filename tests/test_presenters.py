import unittest
from presenters.hello_presenter import HelloPresenter

class TestHelloPresenter(unittest.TestCase):

    def test_get_greeting_default_name(self):
        presenter = HelloPresenter()
        greeting = presenter.get_greeting(name="TestUser")
        self.assertEqual(greeting, "Hello TestUser")

    def test_get_greeting_custom_name(self):
        presenter = HelloPresenter()
        greeting = presenter.get_greeting(name="Jules")
        self.assertEqual(greeting, "Hello Jules")

if __name__ == '__main__':
    unittest.main()
