import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import json

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from product_loader import ProductLoader
from generator import ContentGenerator
from publisher import WordPressPublisher

class TestAutoBlogging(unittest.TestCase):

    def setUp(self):
        # Create a dummy product file for testing
        self.test_dir = "Products Data"
        os.makedirs(self.test_dir, exist_ok=True)
        self.test_file = os.path.join(self.test_dir, "Test Product.txt")
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("Test Product\nFeatures: Good for skin.\nIngredients: Collagen.")
        
        # Set essential environment variables for tests
        os.environ["GOOGLE_CLOUD_PROJECT"] = "claudecode-480704"
        os.environ["VERTEX_MODEL_NAME"] = "gemini-2.0-flash-exp"

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_product_loader(self):
        loader = ProductLoader(data_dir=self.test_dir)
        files = loader.get_product_files()
        self.assertTrue(len(files) > 0)
        self.assertIn(self.test_file, files)
        
        content = loader.read_product(self.test_file)
        self.assertIn("Test Product", content)
        
        name = loader.extract_product_name(content)
        self.assertEqual(name, "Test Product")

    @patch('generator.call_vertex_with_retry')
    @patch('generator.create_vertex_model')
    def test_generator_mock(self, mock_create_model, mock_call_vertex):
        # Mock the API response
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "title": "Mock Title",
            "content_html": "<p>Mock Content</p>",
            "excerpt": "Mock Excerpt"
        })
        
        # Bottom-most decorator (@patch('generator.create_vertex_model')) -> mock_create_model
        # Top-most decorator (@patch('generator.call_vertex_with_retry')) -> mock_call_vertex
        mock_call_vertex.return_value = mock_response

        gen = ContentGenerator()
        article = gen.generate_article("Test Product", "Info")
        
        self.assertIsNotNone(article)
        self.assertEqual(article['title'], "Mock Title")
        self.assertEqual(article['content_html'], "<p>Mock Content</p>")

    @patch('requests.post')
    def test_publisher_mock(self, mock_post):
        # Mock WP response
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {"id": 123, "link": "http://example.com/p/123", "source_url": "http://img.url"}
        
        publisher = WordPressPublisher("http://mock.com", "user", "pass")
        
        # Test Post
        post_id = publisher.create_post("Title", "Content")
        self.assertEqual(post_id, 123)
        
        # Test Media Upload (mock file open)
        with patch("builtins.open", unittest.mock.mock_open(read_data=b"img_data")):
            media_id = publisher.upload_media("test.jpg")
            self.assertEqual(media_id, 123)

if __name__ == '__main__':
    unittest.main()
