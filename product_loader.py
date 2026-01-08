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

if __name__ == "__main__":
    loader = ProductLoader()
    files = loader.get_product_files()
    print(f"Found {len(files)} product files.")
    if files:
        print(f"Sample: {files[0]}")
        content = loader.read_product(files[0])
        print(f"Name: {loader.extract_product_name(content)}")
