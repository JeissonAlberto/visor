import unittest

from ui.menu_lan_vision import _ip_sort_key


class LanVisionMenuTests(unittest.TestCase):
    def test_ip_sort_key_orders_valid_ipv4_parts(self):
        self.assertLess(_ip_sort_key("192.168.1.2"), _ip_sort_key("192.168.1.10"))

    def test_ip_sort_key_handles_malformed_values(self):
        self.assertEqual(_ip_sort_key(None), (0, 0, 0, 0))
        self.assertEqual(_ip_sort_key("not-an-ip"), (0, 0, 0, 0))


if __name__ == "__main__":
    unittest.main()
