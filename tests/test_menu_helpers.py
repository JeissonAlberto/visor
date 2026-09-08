import unittest

from ui.menu import _es_privada


class MenuHelperTests(unittest.TestCase):
    def test_es_privada_classifies_private_and_public_addresses(self):
        self.assertTrue(_es_privada("192.168.1.20"))
        self.assertFalse(_es_privada("8.8.8.8"))

    def test_es_privada_treats_invalid_input_as_private(self):
        self.assertTrue(_es_privada("not-an-ip"))
        self.assertTrue(_es_privada(None))


if __name__ == "__main__":
    unittest.main()
