import os
import re

class ProductLoader:
    def __init__(self, data_dir="Products Data"):
        self.data_dir = data_dir

    def get_product_files(self):
        """Returns a list of .txt files in the data directory."""
        if not os.path.exists(self.data_dir):
            return []
        
        return [
            os.path.join(self.data_dir, f) 
            for f in os.listdir(self.data_dir) 
            if f.endswith(".txt")
        ]

    def read_product(self, file_path):
        """Reads the content of a product file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None

    def extract_product_name(self, content):
        """Extracts the first line as product name."""
        lines = content.strip().split("\n")
        if lines:
            return lines[0].strip()
        return "Unknown Product"

    def load_products_from_csv(self, csv_path="product_data.csv"):
        """Loads products from a CSV file."""
        import csv
        products = []
        if not os.path.exists(csv_path):
            print(f"CSV file not found: {csv_path}")
            return products
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Flexible column names
                    name = row.get('Product Name') or row.get('name') or row.get('title') or row.get('product_name')
                    content = row.get('Description') or row.get('description') or row.get('content') or row.get('product_description') or ""
                    keywords = row.get('Keywords') or row.get('keywords') or ""
                    
                    if name:
                        products.append({
                            'name': name.strip(),
                            'content': content.strip(),
                            'keywords': [k.strip() for k in keywords.split(',')] if keywords else []
                        })
        except Exception as e:
            print(f"Error reading CSV {csv_path}: {e}")
        
        return products

if __name__ == "__main__":
    loader = ProductLoader()
    files = loader.get_product_files()
    print(f"Found {len(files)} product files.")
    if files:
        print(f"Sample: {files[0]}")
        content = loader.read_product(files[0])
        print(f"Name: {loader.extract_product_name(content)}")
