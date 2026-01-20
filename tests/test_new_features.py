import unittest
import os
import sys
import csv
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from product_loader import ProductLoader
from publisher import WordPressPublisher

class TestNewFeatures(unittest.TestCase):
    def setUp(self):
        # Create a dummy CSV for testing
        self.test_csv = "test_products.csv"
        with open(self.test_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Product Name", "Description", "Keywords"])
            writer.writerow(["Test Product", "Test Description", "k1, k2"])

    def tearDown(self):
        if os.path.exists(self.test_csv):
            os.remove(self.test_csv)

    def test_csv_loading(self):
        loader = ProductLoader()
        products = loader.load_products_from_csv(self.test_csv)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['name'], "Test Product")
        self.assertEqual(products[0]['content'], "Test Description")
        self.assertEqual(products[0]['keywords'], ["k1", "k2"])

    def test_missing_csv(self):
        loader = ProductLoader()
        products = loader.load_products_from_csv("non_existent.csv")
        self.assertEqual(products, [])

    @patch('publisher.requests.post')
    def test_scheduling_parameter(self, mock_post):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 123, "link": "http://example.com/p/123"}
        mock_post.return_value = mock_response

        publisher = WordPressPublisher("http://example.com", "user", "pass")
        
        future_date = (datetime.now() + timedelta(hours=1)).isoformat()
        
        publisher.create_post(
            title="Scheduled Post", 
            content="Content", 
            date=future_date
        )
        
        # Verify the date parameter was passed in the JSON payload
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['date'], future_date)
        self.assertEqual(kwargs['json']['status'], 'draft') # Default status check

if __name__ == '__main__':
    import sys
    with open("test_results.txt", "w") as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        unittest.main(testRunner=runner, exit=False)

