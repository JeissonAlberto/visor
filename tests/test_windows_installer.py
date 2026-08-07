from pathlib import Path
import unittest


class WindowsInstallerTests(unittest.TestCase):
    def test_all_installer_pauses_honor_noninteractive_mode(self):
        installer = (Path(__file__).parents[1] / "instalar.bat").read_text(encoding="utf-8")
        pause_lines = [line.strip() for line in installer.splitlines() if "pause" in line.lower()]

        self.assertTrue(pause_lines)
        self.assertTrue(all(line.lower() == "if not defined visor_no_pause pause" for line in pause_lines))


if __name__ == "__main__":
    unittest.main()
