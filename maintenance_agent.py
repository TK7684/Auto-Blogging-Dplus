import os
import sys
import json
import requests
import time
from datetime import datetime
from dotenv import load_dotenv
from publisher import WordPressPublisher
from vertex_utils import create_vertex_model, get_model_name_from_env, call_vertex_with_retry, get_rate_limiter

# Fix Windows console encoding for Thai characters
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class MaintenanceAgent:
    def __init__(self):
        load_dotenv()
        self.model_name = get_model_name_from_env("gemini-2.0-flash-exp")

        # Validate Vertex AI configuration
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise ValueError("GOOGLE_CLOUD_PROJECT not found in .env. "
                           "Please set your Google Cloud Project ID.")

        wp_url = os.getenv("WP_URL")
        wp_user = os.getenv("WP_USER")
        wp_pwd = os.getenv("WP_APP_PASSWORD")

        if not wp_url or not wp_user or not wp_pwd:
             raise ValueError("WP Credentials missing in .env")

        self.publisher = WordPressPublisher(wp_url, wp_user, wp_pwd)
        self.model = create_vertex_model(self.model_name)

        # Load compliance rules
        self.compliance_rules = {}
        if os.path.exists("compliance_rules.json"):
            with open("compliance_rules.json", "r", encoding="utf-8") as f:
                self.compliance_rules = json.load(f)

    def _analyze_post_issues(self, post):
        """Analyze a post for common issues that need fixing."""
        content = post.get('content', {}).get('rendered', '')
        title = post.get('title', {}).get('rendered', '')
        post_id = post.get('id')

        issues = {
            'post_id': post_id,
            'title': title,
            'has_placeholders': False,
            'placeholder_details': [],
            'hard_sell_indicators': [],
            'ingredient_overload': False,
            'needs_optimization': False,
            'priority': 'low'  # low, medium, high
        }

        # Check for placeholders
        placeholder_patterns = [
            '[IMAGE_PLACEHOLDER',
            '[INSERT_INTERNAL_LINK',
            '[INTERNAL_LINK',
            '[LINK:',
        ]

        for pattern in placeholder_patterns:
            if pattern in content:
                issues['has_placeholders'] = True
                count = content.count(pattern)
                issues['placeholder_details'].append(f"{pattern}: {count} times")

        # Check for hard sell indicators
        hard_sell_patterns = [
            'shopee.co.th',
            'shopee',
            'ซื้อ',
            'สั่ง',
            'โปรโมชั่น',
            'ลดราคา',
            'พิเศษ',
            'limited',
            'order now',
            'buy now',
        ]

        for pattern in hard_sell_patterns:
            if pattern.lower() in content.lower():
                issues['hard_sell_indicators'].append(pattern)

        # Check for ingredient overload (too many ingredients mentioned)
        if content.lower().count('วิตามิน') > 5 or content.lower().count('สารสกัด') > 5:
            issues['ingredient_overload'] = True

        # Determine priority and if post needs optimization
        if issues['has_placeholders']:
            issues['priority'] = 'high'
            issues['needs_optimization'] = True
        elif len(issues['hard_sell_indicators']) > 3:
            issues['priority'] = 'high'
            issues['needs_optimization'] = True
        elif len(issues['hard_sell_indicators']) > 1:
            issues['priority'] = 'medium'
            issues['needs_optimization'] = True
        elif issues['ingredient_overload']:
            issues['priority'] = 'medium'
            issues['needs_optimization'] = True

        return issues

    def _regenerate_post_content(self, post, hot_topic_keywords=None):
        """Regenerate post content with new soft-sell approach."""
        from generator import ContentGenerator
        from reviewer_agent import ReviewerAgent

        title = post.get('title', {}).get('rendered', '')
        content = post.get('content', {}).get('rendered', '')
        post_id = post.get('id')

        print(f"  Regenerating Post {post_id}: {title[:50]}...")

        # Extract product info from title
        product_name = title.split('!')[0].split('?')[0].strip()
        product_description = f'Existing post about {product_name}'

        # Initialize agents
        generator = ContentGenerator()
        reviewer = ReviewerAgent()

        # Get research data
        from researcher_agent import ResearcherAgent
        researcher = ResearcherAgent()
        research_results = researcher.research_product_topics(product_name, product_description)

        # Generate new article
        article = generator.generate_article(
            product_name,
            product_description,
            research_data=research_results,
            hot_topic_keywords=hot_topic_keywords
        )

        if not article:
            print(f"  Failed to generate article for Post {post_id}")
            return None

        # Review the new article
        review_results = reviewer.review_article(article)

        if review_results and review_results.get('status') != 'approved':
            # Try once more with feedback
            article = generator.generate_article(
                product_name,
                product_description + f"\n\nRefinement: {review_results.get('editor_feedback')}",
                research_data=research_results,
                hot_topic_keywords=hot_topic_keywords
            )

        return article

    def _update_post(self, post_id, new_article):
        """Update a post with new content."""
        update_data = {
            "title": new_article.get('title'),
            "content": new_article.get('content_html', ''),
            "meta": {
                '_yoast_wpseo_focuskw': new_article.get('seo_keyphrase', ''),
                '_yoast_wpseo_metadesc': new_article.get('seo_meta_description', '')
            }
        }

        # Add FAQ schema if available
        if new_article.get('faq_schema_html'):
            update_data['content'] += f"\n\n{new_article['faq_schema_html']}"

        return self.publisher.update_post(post_id, update_data)

    def audit_and_fix_posts(self, dry_run=False, limit=None, mode='seo'):
        """
        Fetches and checks/updates posts.

        Args:
            dry_run: If True, don't actually update posts
            limit: Maximum number of posts to process (None for all)
            mode: 'seo' for SEO optimization, 'fix' for placeholder/hard sell fixing, 'both' for both
        """
        # Smart Skip: Check quota before starting
        rate_limiter = get_rate_limiter()
        usage = rate_limiter.get_daily_usage()
        limit_val = rate_limiter.requests_per_day

        if usage > (limit_val * 0.85):
            print(f"Maintenance: Skipping to save quota (Usage: {usage}/{limit_val}).")
            return

        mode_str = mode.upper()
        print(f"Maintenance: Starting audit (mode={mode_str}, limit={limit}, dry_run={dry_run})...")

        page = 1
        processed_count = 0
        fixed_count = 0
        skipped_count = 0

        # Hot topic keywords for content generation
        hot_topic_keywords = ['คอลลาเจน', 'ผิวใส', 'ไร้สิว', 'วิตามินซี', 'แอสตาแซนทิน']

        while True:
            print(f"Maintenance: Fetching page {page}...")
            posts = self.publisher.get_posts(per_page=10, page=page)

            if not posts:
                print("Maintenance: No more posts found. Audit complete.")
                break

            for post in posts:
                if limit and processed_count >= limit:
                    print(f"Maintenance: Limit of {limit} reached. Stopping.")
                    return self._print_summary(processed_count, fixed_count, skipped_count)

                post_id = post.get('id')
                title = post.get('title', {}).get('rendered', '')
                content = post.get('content', {}).get('rendered', '')

                # Analyze post for issues
                issues = self._analyze_post_issues(post)

                # Determine what needs to be done based on mode
                needs_fix = False
                fix_type = None

                if mode in ['fix', 'both']:
                    if issues['needs_optimization']:
                        needs_fix = True
                        fix_type = 'regenerate'
                        print(f"Maintenance: Post {post_id} needs {issues['priority']} priority fix")

                if mode in ['seo', 'both'] and not needs_fix:
                    # For SEO mode, process all posts (or could add SEO-specific checks)
                    if mode == 'seo':
                        needs_fix = True
                        fix_type = 'seo'

                if not needs_fix:
                    skipped_count += 1
                    continue

                try:
                    if fix_type == 'regenerate':
                        # Regenerate content with soft-sell approach
                        new_article = self._regenerate_post_content(post, hot_topic_keywords)

                        if new_article:
                            if not dry_run:
                                success = self._update_post(post_id, new_article)
                                if success:
                                    print(f"  [OK] Post {post_id} fixed successfully")
                                    fixed_count += 1
                                else:
                                    print(f"  [FAIL] Post {post_id} update failed")
                            else:
                                print(f"  [OK] Post {post_id} would be fixed (dry run)")
                                fixed_count += 1
                        else:
                            print(f"  [FAIL] Post {post_id} generation failed")

                    elif fix_type == 'seo':
                        # Enhanced Audit Logic (from Auto-Blogger-WP)
                        prompt = f"""
                        You are a senior SEO editor and fact-checker. Audit the following WordPress post:
                        
                        TITLE: {title}
                        CONTENT: {content[:5000]}  # Increased token limit
                        
                        TASKS:
                        1. **Fact Check & Debug**: Search for any outdated information, broken logic, or old statistics. Update them to be current for 2026. This is CRITICAL.
                        2. **Title Optimization**: Review the title. If it does not grab attention in 3 seconds (boring, too long), rewrite it to be a high-CTR, "click-bait" style professional title (max 60 chars).
                        3. **SEO Optimization**: Improve heading hierarchy (H2, H3), ensure keywords are used naturally, and add alt text placeholders if missing.
                        4. **Readability**: Break up long paragraphs and ensure the tone is professional yet engaging.
                        5. **Internal Linking**: If you see opportunities to link to generic topics, use the search-style link: <a href="/?s=topic">topic</a>.
                        
                        Return the optimized content, new title, and notes in JSON format:
                        {{
                            "needs_update": true,
                            "corrected_title": "New Title",
                            "corrected_content_html": "Full optimized HTML",
                            "seo_keyphrase": "Keyphrase",
                            "seo_meta_description": "Meta description",
                            "fact_check_notes": "What was fixed"
                        }}
                        """

                        response = call_vertex_with_retry(self.model, prompt)
                        if response:
                            try:
                                res = json.loads(response.text.replace("```json", "").replace("```", "").strip())

                                if res.get('needs_update'):
                                    update_data = {
                                        "title": res.get('corrected_title', title),
                                        "content": res.get('corrected_content_html', ""),
                                        "meta": {
                                            '_yoast_wpseo_focuskw': res.get('seo_keyphrase', ''),
                                            '_yoast_wpseo_metadesc': res.get('seo_meta_description', '')
                                        }
                                    }

                                    if not dry_run:
                                        success = self.publisher.update_post(post_id, update_data)
                                        if success:
                                            print(f"  [OK] Post {post_id} optimized (Facts & SEO)")
                                            print(f"       Notes: {res.get('fact_check_notes')}")
                                            fixed_count += 1
                                    else:
                                        print(f"  [OK] Post {post_id} would be optimized (dry run)")
                                        fixed_count += 1
                            except json.JSONDecodeError as e:
                                print(f"  [ERROR] Failed to parse JSON for Post {post_id}: {e}")

                    processed_count += 1
                    time.sleep(5)  # Delay to match rate limits

                except Exception as e:
                    print(f"  [ERROR] Maintenance Error on Post {post_id}: {e}")

            page += 1

        return self._print_summary(processed_count, fixed_count, skipped_count)

    def _print_summary(self, processed, fixed, skipped):
        """Print maintenance summary."""
        print(f"\n{'='*50}")
        print(f"Maintenance Summary")
        print(f"{'='*50}")
        print(f"Processed: {processed}")
        print(f"Fixed: {fixed}")
        print(f"Skipped: {skipped}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        return {'processed': processed, 'fixed': fixed, 'skipped': skipped}

    def optimize_old_posts(self, dry_run=False, limit=5):
        """
        Optimizes old posts by fixing placeholders, hard sell, and ingredient overload.
        This is called automatically in the maintenance cycle.
        """
        return self.audit_and_fix_posts(dry_run=dry_run, limit=limit, mode='fix')

    def seo_optimize_posts(self, dry_run=False, limit=5):
        """
        SEO optimization for posts.
        """
        return self.audit_and_fix_posts(dry_run=dry_run, limit=limit, mode='seo')


if __name__ == "__main__":
    # Test requires real WP connection
    try:
        maint = MaintenanceAgent()
        # Example usage:
        # maint.optimize_old_posts(dry_run=True, limit=3)
        # maint.seo_optimize_posts(dry_run=True, limit=3)
        print("Maintenance Agent initialized.")
    except Exception as e:
        print(f"Init failed: {e}")
