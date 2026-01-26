import re
import os
import sys
import json
import requests
import time
from datetime import datetime
from dotenv import load_dotenv
from publisher import WordPressPublisher
from vertex_utils import create_vertex_model, get_model_name_from_env, call_vertex_with_retry, get_rate_limiter
from image_generator import ImageGenerator
from yoast_integrator import YoastSEOIntegrator

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
        self.image_gen = ImageGenerator()
        self.yoast = YoastSEOIntegrator(wp_url, wp_user, wp_pwd)

        # Load compliance rules
        self.compliance_rules = {}
        if os.path.exists("compliance_rules.json"):
            with open("compliance_rules.json", "r", encoding="utf-8") as f:
                self.compliance_rules = json.load(f)

    def _cleanup_ai_leftovers(self, content):
        """Removes common AI tags like [image: ...], [link: ...], etc. using regex."""
        patterns = [
            r'\[image:.*?\]',
            r'\[link:.*?\]',
            r'\[internal link:.*?\]',
            r'\[IMAGE_PLACEHOLDER.*?\]',
            r'\[INSERT_INTERNAL_LINK.*?\]',
            r'\[\(.*?ภาพ.*?\).*?\]', # Catch Thai placeholders like [(ภาพ...)]
        ]
        cleaned_content = content
        for pattern in patterns:
            cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.IGNORECASE)
        return cleaned_content.strip()

    def _analyze_post_issues(self, post):
        """Analyze a post for common issues that need fixing."""
        content = post.get('content', {}).get('rendered', '')
        title = post.get('title', {}).get('rendered', '')
        post_id = post.get('id')
        featured_media = post.get('featured_media', 0)

        issues = {
            'post_id': post_id,
            'title': title,
            'has_placeholders': False,
            'placeholder_details': [],
            'hard_sell_indicators': [],
            'ingredient_overload': False,
            'missing_image': featured_media == 0,
            'needs_cleanup': False,
            'needs_optimization': False,
            'priority': 'low'
        }

        # Check for placeholders using regex patterns
        ai_leftover_patterns = [r'\[image:.*?\]', r'\[link:.*?\]', r'\[IMAGE_PLACEHOLDER']
        for pattern in ai_leftover_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                issues['has_placeholders'] = True
                issues['needs_cleanup'] = True
                issues['priority'] = 'medium'

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
        if issues['has_placeholders'] or issues['missing_image']:
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
                
                # --- NEW: CLEANUP & IMAGE FIX ---
                current_content = content
                cleaned_content = self._cleanup_ai_leftovers(current_content)
                content_updated = False
                
                if cleaned_content != current_content:
                    print(f"  [FIX] Cleaned AI leftovers from Post {post_id}")
                    current_content = cleaned_content
                    content_updated = True
                
                if issues['missing_image'] and not dry_run:
                    print(f"  [FIX] Generating missing image for Post {post_id}")
                    try:
                        # Extract a simple prompt from the title
                        img_prompt = f"Professional skincare product photography for {title}, high end, clean background, 4k"
                        img_path = self.image_gen.generate_image(img_prompt)
                        if img_path:
                            media_id = self.publisher.upload_media(img_path, title=title)
                            if media_id:
                                self.publisher.update_post(post_id, {"featured_media": media_id})
                                print(f"  [OK] Featured image set for Post {post_id}")
                    except Exception as e:
                        print(f"  [ERROR] Image generation failed for Post {post_id}: {e}")

                # Determine what needs to be done based on mode
                needs_fix = False
                fix_type = None

                if mode in ['fix', 'both']:
                    if issues['needs_optimization']:
                        needs_fix = True
                        fix_type = 'regenerate'
                        print(f"  [TODO] Post {post_id} needs regeneration (Priority: {issues['priority']})")
                
                if mode in ['seo', 'both'] and not needs_fix:
                    needs_fix = True
                    fix_type = 'seo'

                # If we just needed cleanup or image fix and not full regeneration/seo
                if not needs_fix and content_updated and not dry_run:
                     update_success = self.publisher.update_post(post_id, {"content": current_content})
                     if update_success:
                         print(f"  [OK] Cleaned content updated for Post {post_id}")
                         fixed_count += 1
                     else:
                         print(f"  [FAIL] Could not update content for Post {post_id}")
                     processed_count += 1
                     continue

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
                                    # Post-fix SEO update
                                    try:
                                        seo_score = self.yoast.calculate_seo_score(
                                            new_article.get('content_html', ''),
                                            new_article.get('seo_keyphrase', ''),
                                            new_article.get('title', ''),
                                            new_article.get('seo_meta_description', '')
                                        )
                                        read_score = self.yoast.calculate_readability_score(new_article.get('content_html', ''))
                                        self.yoast.update_yoast_meta_fields(post_id, {
                                            'focus_keyword': new_article.get('seo_keyphrase'),
                                            'seo_title': new_article.get('title'),
                                            'meta_description': new_article.get('seo_meta_description'),
                                            'seo_score': seo_score,
                                            'readability_score': read_score
                                        })
                                        print(f"  [OK] Post {post_id} fixed and SEO scores updated")
                                        fixed_count += 1
                                    except Exception as seo_e:
                                        print(f"  [WARN] SEO update failed for Post {post_id}: {seo_e}")
                                        print(f"  [OK] Post {post_id} content fixed (SEO update skipped)")
                                        fixed_count += 1
                                else:
                                    print(f"  [FAIL] Post {post_id} update failed")
                            else:
                                print(f"  [OK] Post {post_id} would be fixed (dry run)")
                                fixed_count += 1
                        else:
                            print(f"  [FAIL] Post {post_id} regeneration failed")

                    elif fix_type == 'seo':
                        # Enhanced Audit Logic
                        prompt = f"""
                        You are a senior SEO editor. Audit and Optimize this post for 2026.
                        TITLE: {title}
                        CONTENT: {current_content[:5000]}

                        Return optimized JSON with these exact fields:
                        {{
                            "needs_update": true/false,
                            "corrected_title": "optimized title",
                            "corrected_content_html": "optimized content",
                            "seo_keyphrase": "main keyword",
                            "seo_meta_description": "meta description 150-160 chars"
                        }}
                        Do not use markdown formatting.
                        """
                        response = call_vertex_with_retry(self.model, prompt)
                        if response:
                            try:
                                # Clean and parse JSON with better error handling
                                content = response.text
                                # Remove markdown code blocks if present
                                content = content.replace("```json", "").replace("```", "")
                                # Remove any leading/trailing whitespace
                                content = content.strip()

                                res = json.loads(content)

                                if res.get('needs_update'):
                                    update_data = {
                                        "title": res.get('corrected_title', title),
                                        "content": self._cleanup_ai_leftovers(res.get('corrected_content_html', "")),
                                        "meta": {
                                            '_yoast_wpseo_focuskw': res.get('seo_keyphrase', ''),
                                            '_yoast_wpseo_metadesc': res.get('seo_meta_description', '')
                                        }
                                    }

                                    if not dry_run:
                                        success = self.publisher.update_post(post_id, update_data)
                                        if success:
                                            # Update Yoast scores
                                            seo_score = self.yoast.calculate_seo_score(
                                                update_data['content'],
                                                res.get('seo_keyphrase', ''),
                                                update_data['title'],
                                                res.get('seo_meta_description', '')
                                            )
                                            read_score = self.yoast.calculate_readability_score(update_data['content'])
                                            self.yoast.update_yoast_meta_fields(post_id, {
                                                'focus_keyword': res.get('seo_keyphrase'),
                                                'seo_title': update_data['title'],
                                                'meta_description': res.get('seo_meta_description'),
                                                'seo_score': seo_score,
                                                'readability_score': read_score
                                            })
                                            print(f"  [OK] Post {post_id} optimized and SEO scores updated")
                                            fixed_count += 1
                                    else:
                                        print(f"  [OK] Post {post_id} would be optimized (dry run)")
                                        fixed_count += 1
                            except json.JSONDecodeError as je:
                                print(f"  [ERROR] JSON parsing failed for Post {post_id}: {je}")
                                print(f"  Content preview (first 200 chars): {content[:200]}...")
                                # Try to extract partial JSON if response was truncated
                                if '{' in content:
                                    # Find first { and try to find matching }
                                    start = content.find('{')
                                    # Try different strategies to find valid JSON
                                    for end in range(len(content) - 1, start, -1):
                                        if content[end] == '}':
                                            try:
                                                partial_json = json.loads(content[start:end + 1])
                                                print(f"  [RECOVER] Partial JSON recovered for Post {post_id}")
                                                res = partial_json
                                                # Continue with processing if we have needs_update
                                                if res.get('needs_update'):
                                                    # Same update logic as above
                                                    update_data = {
                                                        "title": res.get('corrected_title', title),
                                                        "content": self._cleanup_ai_leftovers(res.get('corrected_content_html', "")),
                                                        "meta": {
                                                            '_yoast_wpseo_focuskw': res.get('seo_keyphrase', ''),
                                                            '_yoast_wpseo_metadesc': res.get('seo_meta_description', '')
                                                        }
                                                    }
                                                    if not dry_run:
                                                        success = self.publisher.update_post(post_id, update_data)
                                                        if success:
                                                            print(f"  [OK] Post {post_id} optimized (from recovered JSON)")
                                                            fixed_count += 1
                                                    break
                                            except:
                                                continue
                                # If we couldn't recover, skip this post
                                print(f"  [SKIP] Could not recover JSON for Post {post_id}, skipping")
                            except Exception as e:
                                print(f"  [ERROR] Audit processing failed for Post {post_id}: {e}")

                    processed_count += 1
                    time.sleep(5) 

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
