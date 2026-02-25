import unittest
from src.asset_manager import AssetManager
from src.converter import Converter
import os
import shutil

class TestComponents(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_output"
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_asset_manager_path(self):
        manager = AssetManager(self.test_dir)
        # We won't actually download, just check logic if possible, 
        # but download_image does network call. 
        # We can mock it or just test path generation logic if we extract it.
        # For now, let's just check directory creation.
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "assets")))

    def test_converter(self):
        converter = Converter()
        html = "<h1>Hello</h1><p>World</p>"
        md = converter.convert(html, "Test Title")
        self.assertIn("# Test Title", md)
        self.assertIn("World", md)

if __name__ == '__main__':
    unittest.main()
