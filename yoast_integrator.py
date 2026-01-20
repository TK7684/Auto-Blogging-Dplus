"""
Yoast SEO Integration Module.

Handles integration with Yoast SEO plugin for WordPress:
- Updates Yoast meta fields
- Calculates readability and SEO scores
- Optimizes content for Yoast's analysis
"""

import logging
import requests
import os
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class YoastSEOIntegrator:
    """Integrate with Yoast SEO plugin meta fields."""

    def __init__(self, wp_url: str, wp_user: str, wp_app_password: str):
        self.wp_url = wp_url.rstrip('/')
        self.wp_user = wp_user
        self.wp_app_password = wp_app_password
        self.api_base = f"{self.wp_url}/wp-json"

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for WordPress REST API."""
        import base64
        credentials = f"{self.wp_user}:{self.wp_app_password}"
        token = base64.b64encode(credentials.encode()).decode('utf-8')
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json"
        }

    def update_yoast_meta_fields(self, post_id: int, seo_data: Dict) -> bool:
        """
        Update Yoast SEO meta fields for a post via standard WP Meta API.
        """
        meta_fields = {
            "_yoast_wpseo_focuskw": seo_data.get('focus_keyword', ''),
            "_yoast_wpseo_title": seo_data.get('seo_title', ''),
            "_yoast_wpseo_metadesc": seo_data.get('meta_description', ''),
            "_yoast_wpseo_canonical": seo_data.get('canonical_url', ''),
            "_yoast_wpseo_opengraph-title": seo_data.get('og_title', ''),
            "_yoast_wpseo_opengraph-description": seo_data.get('og_description', ''),
            "_yoast_wpseo_opengraph-image": seo_data.get('og_image', ''),
            "_yoast_wpseo_linkdex": str(seo_data.get('seo_score', 0)),
            "_yoast_wpseo_content_score": str(seo_data.get('readability_score', 0)),
        }

        meta_payload = {k: v for k, v in meta_fields.items() if v}

        try:
            url = f"{self.api_base}/wp/v2/posts/{post_id}"
            headers = self.get_auth_headers()
            
            response = requests.post(url, headers=headers, json={"meta": meta_payload}, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"✅ Yoast SEO meta fields updated for post {post_id}")
                return True
            else:
                logger.warning(f"❌ Failed to update Yoast meta for post {post_id}: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error updating Yoast meta fields: {e}")
            return False

    def calculate_seo_score(self, content: str, focus_keyword: str,
                           title: str, meta_description: str) -> int:
        """Calculate an approximate SEO score based on Yoast's criteria."""
        score = 0
        content_lower = content.lower()
        keyword_lower = focus_keyword.lower() if focus_keyword else ""

        if not keyword_lower:
            return 0

        # Keyword in title
        if keyword_lower in title.lower():
            score += 10

        # Keyword in first paragraph
        first_paragraph = content_lower.split('\n')[0] if content_lower else ''
        if keyword_lower in first_paragraph:
            score += 10

        # Keyword density (2-3% ideal)
        word_count = len(content_lower.split())
        keyword_count = content_lower.count(keyword_lower)
        if word_count > 0:
            density = (keyword_count / word_count) * 100
            if 0.5 <= density <= 3:
                score += 20
            elif density > 0:
                score += 10

        # Content length
        if word_count >= 300:
            score += 20
        elif word_count >= 200:
            score += 10

        # Meta description length and keyword
        if 120 <= len(meta_description) <= 160:
            score += 10
        if keyword_lower in meta_description.lower():
            score += 5

        # Title length
        if 30 <= len(title) <= 60:
            score += 15
        elif len(title) < 60:
            score += 10

        # Subheadings
        if '<h2>' in content or '<h3>' in content:
            score += 10

        # Links
        if '<a href=' in content:
            score += 5

        return min(score, 100)

    def calculate_readability_score(self, content: str) -> int:
        """Calculate readability score based on Yoast's criteria."""
        text_content = re.sub(r'<[^>]+>', ' ', content)
        text_content = ' '.join(text_content.split())

        if not text_content:
            return 0

        score = 0
        sentences = text_content.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0

        if avg_sentence_length <= 20:
            score += 30
        elif avg_sentence_length <= 25:
            score += 20
        else:
            score += 10

        paragraphs = text_content.split('\n\n')
        short_paragraphs = sum(1 for p in paragraphs if len(p.split()) <= 150)
        if len(paragraphs) > 0:
            paragraph_ratio = short_paragraphs / len(paragraphs)
            if paragraph_ratio >= 0.7:
                score += 30
            elif paragraph_ratio >= 0.5:
                score += 20

        return min(score, 100)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    wp_url = os.environ.get("WP_URL")
    wp_user = os.environ.get("WP_USER")
    wp_password = os.environ.get("WP_APP_PASSWORD")
    if all([wp_url, wp_user, wp_password]):
        integrator = YoastSEOIntegrator(wp_url, wp_user, wp_password)
        print("Yoast Integrator Ready")
    else:
        print("Missing Credentials")
