import argparse
import sys
import os
import json
import random
import time
from datetime import datetime
from dotenv import load_dotenv

# Fix Windows console encoding for Thai characters
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from product_loader import ProductLoader
from generator import ContentGenerator
from publisher import WordPressPublisher

def main():
    parser = argparse.ArgumentParser(description="Auto-Blogging for Thai Cosmetic Products")
    parser.add_argument("--mode", choices=["daily", "weekly", "manual", "test"], default="daily", help="Operation mode")
    parser.add_argument("--product_file", help="Specific product file to process (filename only)")
    parser.add_argument("--dry_run", action="store_true", help="Generate content but do not publish")
    parser.add_argument("--skip_maintenance", action="store_true", help="Skip the maintenance cycle")
    
    args = parser.parse_args()
    
    load_dotenv()
    
    # 1. Setup
    print(f"Starting Auto-Blogging v2.2.0 in {args.mode} mode...")
    
    from maintenance_agent import MaintenanceAgent
    from researcher_agent import ResearcherAgent
    from reviewer_agent import ReviewerAgent
    
    loader = ProductLoader()
    try:
        generator = ContentGenerator()
        researcher = ResearcherAgent()
        reviewer = ReviewerAgent()
        maintenance = MaintenanceAgent()
        
        wp_url = os.getenv("WP_URL")
        wp_user = os.getenv("WP_USER")
        wp_pwd = os.getenv("WP_APP_PASSWORD")
        publisher = WordPressPublisher(wp_url, wp_user, wp_pwd)
    except Exception as e:
        print(f"Setup Error: {e}")
        return

    # Guard: 1 Post Per Day (Only for daily and weekly modes)
    history_file = "post_history.json"
    history = {}
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except Exception:
            history = {}

    if args.mode in ["daily", "weekly"] and not args.dry_run:
        today_str = datetime.now().strftime("%Y-%m-%d")
        last_global_post = history.get("__last_post_date__")
        if last_global_post == today_str:
            print(f"Post already created for today ({today_str}). Skipping to avoid over-posting.")
            if not args.skip_maintenance:
                print("\nStep 6: Maintenance (Running only because main post skipped)...")
                maintenance.audit_and_fix_posts(dry_run=args.dry_run, limit=5)
            return

    # 2. Process based on Mode
    article = None
    target_file = None
    product_name = None
    product_content = None
    target_product_data = None # Dictionary from CSV if applicable
    
    # Model Strategy for Vertex AI
    primary_model_flash = os.getenv("VERTEX_MODEL_NAME", "gemini-2.0-flash-exp")
    secondary_model = "gemini-1.5-flash-002"
    
    def execute_with_fallback(agent, method_name, *method_args, **method_kwargs):
        """Executes an agent method with model fallback."""
        # Determine initial model based on mode
        initial_model = primary_model_flash
        if args.mode == "weekly" and "researcher" in str(agent.__class__).lower():
            # Weekly mode might prefer a different model for research
            initial_model = "gemini-1.5-flash-002"

        fallback_model = secondary_model if initial_model != secondary_model else "gemini-2.0-flash-exp"
        
        models_to_try = [initial_model, fallback_model]
        # Remove duplicates
        models_to_try = list(dict.fromkeys(models_to_try))

        last_error = None
        for model_name in models_to_try:
            try:
                agent.update_model(model_name)
                res = getattr(agent, method_name)(*method_args, **method_kwargs)
                if res: return res
            except Exception as e:
                last_error = e
                print(f"Model ({model_name}) failed for {method_name}: {e}.")
                if "429" in str(e):
                    print("Quota exceeded, cooling down for 10 seconds...")
                    time.sleep(10)
        
        print(f"All models failed for {method_name}. Last error: {last_error}")
        return None

    if args.mode == "weekly":
        print("Step 2: Performing Content Gap Research (Weekly)...")
        # 1. Fetch own topics from WP
        own_posts = publisher.get_posts(per_page=50)
        own_titles = [p['title']['rendered'] for p in own_posts] if own_posts else []
        
        # 2. Fetch competitor RSS
        rss_urls = [
            "https://feeds.feedburner.com/ThaiSkincareNews", 
            "https://www.cosmeticsdesign-asia.com/rss/feed/645163",
            "https://www.vogue.co.th/beauty/rss"
        ]
        competitor_articles = researcher.fetch_competitor_rss(rss_urls)
        
        # 3. Analyze Gap (With Fallback)
        gap_results = execute_with_fallback(researcher, "analyze_content_gap", own_titles, competitor_articles)
        
        if gap_results and gap_results.get('content_gaps'):
            best_gap = gap_results['content_gaps'][0]
            print(f"Identified Content Gap: {best_gap['proposed_title']}")
            article = execute_with_fallback(generator, "rewrite_competitor_content", best_gap, "Thailand Beauty Trends")
        else:
            print("Gap analysis failed. Falling back to hot topic.")
            args.mode = "daily"

    if args.mode == "daily" or args.mode == "manual":
        # Check if we should find a hot topic first
        hot_topic_data = None
        # ALWAYS research hot topics if not provided, even if product_file is specified
        # This allows us to link the specific product to a GENERAL trend
        print("Step 2: Researching Hot Topics in Thailand...")
        hot_topic_data = execute_with_fallback(researcher, "research_hot_topics")
        
        # --- PRODUCT SELECTION LOGIC (CSV Priority) ---
        products_from_csv = loader.load_products_from_csv("product_data.csv")
        
        if products_from_csv and not args.product_file:
            print(f"Loaded {len(products_from_csv)} products from CSV.")
            # Random selection or Smart Match from CSV
            if hot_topic_data and hot_topic_data.get('hot_topics'):
                top_topic = hot_topic_data['hot_topics'][0]
                print(f"Top Hot Topic: {top_topic['headline_th']}")
                # Simple keyword matching
                best_product = None
                best_score = -1
                for p in products_from_csv:
                    score = sum(1 for kw in top_topic.get('keywords', []) if kw.lower() in p['name'].lower())
                    if score > best_score:
                        best_score = score
                        best_product = p
                
                if best_score > 0:
                     target_product_data = best_product
                     print(f"matched product to trend: {target_product_data['name']}")
                else:
                     # Random rotation
                     target_product_data = random.choice(products_from_csv)
                     print(f"No direct match, rotating random product: {target_product_data['name']}")
            else:
                 target_product_data = random.choice(products_from_csv)
                 print(f"Randomly selected product: {target_product_data['name']}")
            
            product_name = target_product_data['name']
            product_content = target_product_data['content']

        else:
            # Fallback to Text Files
            files = loader.get_product_files()
            if not files:
                print("No product files found in 'Products Data' and CSV empty.")
                return

            if args.product_file:
                for f in files:
                    if args.product_file in f:
                        target_file = f
                        break
                if not target_file:
                    print(f"Product file '{args.product_file}' not found.")
                    return
            else:
                # Smart Selection based on Hot Topic if available
                if hot_topic_data and hot_topic_data.get('hot_topics'):
                    top_topic = hot_topic_data['hot_topics'][0]
                    print(f"Top Hot Topic: {top_topic['headline_th']}")
                    # Simple keyword matching for selection
                    best_file = None
                    best_score = -1
                    for f in files:
                        fname = os.path.basename(f).lower()
                        score = sum(1 for kw in top_topic.get('keywords', []) if kw.lower() in fname)
                        if score > best_score:
                            best_score = score
                            best_file = f
                    
                    # If we found a good match, use it.
                    # If match score is 0, we might want to just rotate to keep variety
                    # but STILL use the hot topic for the "Connection" in the article
                    if best_score > 0:
                         target_file = best_file
                         print(f"matched product to trend: {target_file}")
                    else:
                         # Fallback to Smart Randomization (least recently used)
                         sorted_files = sorted(files, key=lambda x: history.get(os.path.basename(x), "2000-01-01"))
                         target_file = sorted_files[0]
                         print(f"No direct match, rotating to: {target_file} (Will connect to trend)")
    
                else:
                    # Fallback to Smart Randomization (least recently used)
                    sorted_files = sorted(files, key=lambda x: history.get(os.path.basename(x), "2000-01-01"))
                    target_file = sorted_files[0]

            if target_file:
                print(f"Selected Product File: {os.path.basename(target_file)}")
                product_content = loader.read_product(target_file)
                product_name = loader.extract_product_name(product_content)

        # 3. Research & Data
        print(f"Step 3: Deep Researching {product_name}...")
        research_results = execute_with_fallback(researcher, "research_product_topics", product_name, product_content)

        # 4. Generate Content
        print("Step 4: Generating pillar content with investigative persona...")
        # Extract keywords from hot topic for focused content
        hot_topic_keywords = None
        if hot_topic_data and hot_topic_data.get('hot_topics'):
            hot_topic_keywords = hot_topic_data['hot_topics'][0].get('keywords', [])

        article = execute_with_fallback(generator, "generate_article", product_name, product_content, research_data=research_results, hot_topic_keywords=hot_topic_keywords)

    if not article:
        print("Content generation failed.")
        return

    # 5. Review & Schema Check
    print("Step 5: Reviewing content for compliance and structured data...")
    review_results = execute_with_fallback(reviewer, "review_article", article)
    
    if review_results and review_results.get('status') != 'approved':
        print(f"Review Feedback: {review_results.get('editor_feedback')}")
        article = execute_with_fallback(
            generator,
            "generate_article",
            product_name, 
            product_content + f"\n\nRefinement: {review_results.get('editor_feedback')}", 
            research_data=research_results if 'research_results' in locals() else None
        )
    else:
        print("Reviewer: Article Approved!")

    # 6. Publish
    wp_url = os.getenv("WP_URL")
    wp_user = os.getenv("WP_USER")
    wp_pwd = os.getenv("WP_APP_PASSWORD")
    
    if args.dry_run:
        print("Dry Run: Saving to dry_run_output_v2.json")
        with open("dry_run_output_v2.json", "w", encoding="utf-8") as f:
            json.dump(article, f, ensure_ascii=False, indent=4)
    else:
        print("Step 5: Publishing to WordPress...")
        publisher = WordPressPublisher(wp_url, wp_user, wp_pwd)
        
        # Enhanced Metadata for WP
        seo_data = {
            'seo_keyphrase': article.get('seo_keyphrase'),
            'seo_meta_description': article.get('seo_meta_description')
        }
        
        # Combine content with FAQ schema if available
        final_content = article.get('content_html', '')
        if article.get('faq_schema_html'):
            final_content += f"\n\n{article['faq_schema_html']}"

        # --- RANDOM SCHEDULING ---
        from datetime import timedelta
        scheduled_date = None
        if args.mode in ['daily', 'weekly']:
            offset_minutes = random.randint(10, 120)
            scheduled_date = (datetime.now() + timedelta(minutes=offset_minutes)).isoformat()
            print(f"📅 Scheduling post for: {scheduled_date} (Offset: {offset_minutes} mins)")

        post_id = publisher.create_post(
            title=article.get('title'),
            content=final_content,
            status='publish' if not scheduled_date else 'future', # WP handles 'future' automatically if date is set
            slug=article.get('slug'),
            seo_data=seo_data,
            date=scheduled_date
        )
        if post_id:
            print(f"Successfully published/scheduled Post ID: {post_id}")
            history["__last_post_date__"] = datetime.now().strftime("%Y-%m-%d")
            # Log usage for non-file products too (using name as key)
            key = os.path.basename(target_file) if target_file else f"CSV:{product_name}"
            history[key] = datetime.now().isoformat()
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=4)
        else:
            print("Publishing failed.")

    # Maintenance
    if not args.skip_maintenance:
        print("\nStep 6: Maintenance - Reviewing and optimizing old posts...")
        # Run optimization mode first (fix placeholders, hard sell, ingredient overload)
        maintenance.optimize_old_posts(dry_run=args.dry_run, limit=3)
        # Then run SEO optimization
        maintenance.seo_optimize_posts(dry_run=args.dry_run, limit=2)

if __name__ == "__main__":
    main()
