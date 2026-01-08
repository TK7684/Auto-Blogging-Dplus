import argparse
import sys
import os
import random
import time
from datetime import datetime
from dotenv import load_dotenv

from product_loader import ProductLoader
from generator import ContentGenerator
from publisher import WordPressPublisher

def main():
    parser = argparse.ArgumentParser(description="Auto-Blogging for Thai Cosmetic Products")
    parser.add_argument("--mode", choices=["daily", "manual", "test"], default="daily", help="Operation mode")
    parser.add_argument("--product_file", help="Specific product file to process (filename only)")
    parser.add_argument("--dry_run", action="store_true", help="Generate content but do not publish")
    
    args = parser.parse_args()
    
    load_dotenv()
    
    # 1. Setup
    print(f"Starting Auto-Blogging in {args.mode} mode...")
    loader = ProductLoader()
    try:
        generator = ContentGenerator()
    except ValueError as e:
        print(f"Setup Error: {e}")
        return

    wp_url = os.getenv("WP_URL")
    wp_user = os.getenv("WP_USER")
    wp_pwd = os.getenv("WP_APP_PASSWORD")
    
    publisher = None
    if not args.dry_run:
        if wp_url and wp_user and wp_pwd:
            publisher = WordPressPublisher(wp_url, wp_user, wp_pwd)
        else:
            print("Warning: WP credentials missing. Switching to dry_run.")
            args.dry_run = True

    # 2. Select Product
    files = loader.get_product_files()
    if not files:
        print("No product files found in 'Products Data'.")
        return

    target_file = None
    if args.product_file:
        for f in files:
            if args.product_file in f:
                target_file = f
                break
        if not target_file:
            print(f"Product file '{args.product_file}' not found.")
            return
    else:
        # Daily mode: Pick distinct product based on day of year? Or random?
        # Random for now to rotate.
        target_file = random.choice(files)

    print(f"Selected Product File: {os.path.basename(target_file)}")

    # 3. Read Data
    product_content = loader.read_product(target_file)
    if not product_content:
        print("Failed to read product content.")
        return
    
    product_name = loader.extract_product_name(product_content)
    print(f"Product Name: {product_name}")

    # 4. Generate Content
    print("Generating content...")
    article = generator.generate_article(product_name, product_content)
    
    if not article:
        print("Content generation failed.")
        return

    print(f"Generated Title: {article.get('title')}")
    
    # 5. Publish
    if args.dry_run:
        print("Dry Run: Skipping publish.")
        print("--- Content Preview ---")
        print(f"Title: {article.get('title')}")
        print(f"Excerpt: {article.get('excerpt')}")
        print(f"HTML Length: {len(article.get('content_html', ''))}")
        print("-----------------------")
        
        # Save to file for inspection
        with open("dry_run_output.json", "w", encoding="utf-8") as f:
            json.dump(article, f, ensure_ascii=False, indent=4)
        print("Saved dry_run_output.json")
    else:
        print("Publishing to WordPress...")
        # TODO: Handle image generation or selection if needed. 
        # For now, we post text.
        
        # Map category/tags to IDs if dynamic, or just pass names if WP setup allows (Publisher uses IDs usually)
        # Simplified: Just post without cats/tags for MVP or rely on default.
        
        post_id = publisher.create_post(
            title=article.get('title'),
            content=article.get('content_html'),
            status='publish', # Auto publish
            # category_ids=[1], # Example
        )
        
        if post_id:
            print(f"Successfully published Post ID: {post_id}")
        else:
            print("Publishing failed.")

if __name__ == "__main__":
    main()
