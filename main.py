import argparse
import sys
import os
import json
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
    print(f"Starting Auto-Blogging v2.0 in {args.mode} mode...")
    
    from maintenance_agent import MaintenanceAgent
    from researcher_agent import ResearcherAgent
    from reviewer_agent import ReviewerAgent
    
    loader = ProductLoader()
    try:
        generator = ContentGenerator()
        researcher = ResearcherAgent()
        reviewer = ReviewerAgent()
        maintenance = MaintenanceAgent()
    except Exception as e:
        print(f"Setup Error: {e}")
        return

    # 1.5 Maintenance Cycle
    print("Step 1: Maintenance - Reviewing old posts...")
    maintenance.audit_and_fix_posts()

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
        target_file = random.choice(files)

    print(f"Selected Product File: {os.path.basename(target_file)}")

    # 3. Research & Data
    product_content = loader.read_product(target_file)
    product_name = loader.extract_product_name(product_content)
    
    print(f"Step 2: Researching {product_name}...")
    research_results = researcher.research_product_topics(product_name, product_content)
    
    # 4. Generate Content
    print("Step 3: Generating content...")
    article = generator.generate_article(product_name, product_content, research_data=research_results)
    
    if not article:
        print("Content generation failed.")
        return

    # 5. Review
    print("Step 4: Reviewing content...")
    review_results = reviewer.review_article(article)
    
    if review_results.get('status') != 'approved':
        print(f"Review Feedback: {review_results.get('editor_feedback')}")
        print("Regenerating with feedback...")
        # Simple loop: Regenerate once with feedback as extra context
        article = generator.generate_article(
            product_name, 
            product_content + f"\n\nAdditional Editor Feedback: {review_results.get('editor_feedback')}", 
            research_data=research_results
        )
    else:
        print("Reviewer: Article Approved!")

    # 6. Publish
    wp_url = os.getenv("WP_URL")
    wp_user = os.getenv("WP_USER")
    wp_pwd = os.getenv("WP_APP_PASSWORD")
    
    publisher = None
    if not args.dry_run:
        if wp_url and wp_user and wp_pwd:
            from publisher import WordPressPublisher
            publisher = WordPressPublisher(wp_url, wp_user, wp_pwd)
        else:
            print("Warning: WP credentials missing. Switching to dry_run.")
            args.dry_run = True

    if args.dry_run:
        print("Dry Run: Skipping publish.")
        print("--- Content Preview ---")
        print(f"Title: {article.get('title')}")
        print("-----------------------")
        
        with open("dry_run_output_v2.json", "w", encoding="utf-8") as f:
            json.dump(article, f, ensure_ascii=False, indent=4)
        print("Saved dry_run_output_v2.json")
    else:
        print("Step 5: Publishing to WordPress...")
        post_id = publisher.create_post(
            title=article.get('title'),
            content=article.get('content_html'),
            status='publish',
        )
        if post_id:
            print(f"Successfully published Post ID: {post_id}")
        else:
            print("Publishing failed.")

if __name__ == "__main__":
    main()
