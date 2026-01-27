import os
import json
from dotenv import load_dotenv
from vertex_utils import create_vertex_model, get_model_name_from_env, call_vertex_with_retry
from vertexai.generative_models import GenerationConfig

class ContentGenerator:
    def __init__(self):
        load_dotenv()
        self.model_name = get_model_name_from_env("gemini-2.0-flash-exp")

        # Validate Vertex AI configuration
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise ValueError("GOOGLE_CLOUD_PROJECT not found in .env. "
                           "Please set your Google Cloud Project ID.")

        self.model = create_vertex_model(self.model_name)

        # Load brand guidelines
        self.brand_guidelines = {}
        if os.path.exists("brand_guidelines.json"):
            with open("brand_guidelines.json", "r", encoding="utf-8") as f:
                self.brand_guidelines = json.load(f)

        # Load compliance rules
        self.compliance_rules = {}
        if os.path.exists("compliance_rules.json"):
            with open("compliance_rules.json", "r", encoding="utf-8") as f:
                self.compliance_rules = json.load(f)

    def update_model(self, model_name):
        """Updates the underlying Vertex AI model."""
        self.model_name = model_name
        self.model = create_vertex_model(model_name)
        print(f"Generator: Model updated to {model_name}")

    def generate_article(self, product_name, product_description, research_data=None, hot_topic_keywords=None, related_articles=None):
        """
        Generates a blog post using the advanced SEO journalist strategy.

        Args:
            product_name: Name of the product
            product_description: Description of the product
            research_data: Research data from researcher agent
            hot_topic_keywords: Keywords from hot topic to focus on (optional)
            related_articles: List of dicts with 'title' and 'url' (optional)
        """
        brand_context = f"""
        Brand Identity: {self.brand_guidelines.get('brand_name')}
        Tagline: {self.brand_guidelines.get('tagline')}
        Messaging Style: {self.brand_guidelines.get('tone_of_voice')}
        Must Say: {json.dumps(self.brand_guidelines.get('brand_must_say', []), ensure_ascii=False)}
        Do Not Say: {json.dumps(self.brand_guidelines.get('brand_do_not_say', []), ensure_ascii=False)}
        CTA Recommendation: {self.brand_guidelines.get('social_links', {}).get('shopee')}
        """

        # Build research context with focus on hot topic
        research_context = ""
        focus_ingredients = []
        if research_data:
            scientific_refs = research_data.get('scientific_references', [])
            key_takeaways = research_data.get('key_takeaways', '')

            # If hot topic keywords provided, filter content to focus on those
            if hot_topic_keywords:
                research_context = f"""
                Hot Topic Focus: {', '.join(hot_topic_keywords)}
                Scientific Context (focus on topics related to hot keywords):
                {json.dumps([ref for ref in scientific_refs if any(kw.lower() in str(ref).lower() for kw in hot_topic_keywords)], ensure_ascii=False)}
                Key Takeaways: {key_takeaways}
                """
                focus_ingredients = hot_topic_keywords
            else:
                research_context = f"""
                Scientific Context:
                {json.dumps(scientific_refs, ensure_ascii=False)}
                Key Takeaways: {key_takeaways}
                """

        # Build related articles context
        related_context = ""
        if related_articles:
            links_html = "\n".join([f'<li><a href="{a["url"]}">{a["title"]}</a></li>' for a in related_articles])
            related_context = f"""
            =====================================================================
            INTERNAL LINKS: RELATED ARTICLES (MANDATORY)
            =====================================================================
            Add a section at the end (before FAQ) titled "บทความที่เกี่ยวข้อง" with these links:
            <ul>
            {links_html}
            </ul>
            """

        prompt = f"""
        You are an expert SEO content writer and senior investigative journalist specializing in skincare education.
        Write a comprehensive EDUCATIONAL article about: {product_name}.

        Brand Context: {brand_context}
        Product Info: {product_description}
        {research_context}
        {related_context}

        =====================================================================
        CRITICAL SEO REQUIREMENTS - MUST FOLLOW EXACTLY:
        =====================================================================

        1. **KEYPHRASE SELECTION (MANDATORY)**
           - Choose ONE main Thai keyword phrase (3-5 words) related to the topic
           - This keyphrase MUST be the focus of the entire article
           - Examples: "คอลลาเจนบำรุงผิว", "วิตามินซีให้ผิวใส", "โสมดำบำรุงผิว"
           - Place this exact keyphrase in the "seo_keyphrase" field

        2. **TITLE FORMAT (MANDATORY)**
           - MUST start with the keyphrase (exact match)
           - Keep under 60 characters total
           - Format: "[Keyphrase] - Brief benefit phrase"
           - Example: "คอลลาเจนบำรุงผิว - 5 วิธีเสริมสร้างผิวอ่อนเยาว์"

        3. **META DESCRIPTION (MANDATORY)**
           - MUST include the keyphrase naturally
           - Exactly 150-160 characters (no more, no less)
           - Must be compelling and educational

        4. **SLUG (MANDATORY)**
           - Must include English translation of the keyphrase
           - Use lowercase, hyphens between words
           - Example: "collagen-skin-nourishment-tips"

        5. **INTRODUCTION (MANDATORY)**
           - FIRST paragraph MUST include the keyphrase within the first 2 sentences
           - Hook the reader immediately

        6. **SUBHEADINGS (MANDATORY)**
           - At least ONE H2 or H3 MUST contain the keyphrase
           - Use descriptive, educational subheadings

        7. **CONTENT LENGTH (MANDATORY)**
           - Minimum 800 words (comprehensive but fits within output limits)
           - Detailed explanations for each point

        8. **IMAGES WITH ALT TEXT (MANDATORY)**
           - Include 2-3 images using this EXACT format:
             <img src="placeholder.jpg" alt="[รูปภาพ] [keyphrase] คำอธิบายเพิ่มเติม">
           - Alt text MUST include the keyphrase
           - Images must be relevant to the content

        9. **INTERNAL LINKS (MANDATORY)**
           - Add 2-3 internal links using this EXACT format:
             <a href="https://dplusskin.co.th/skincare-tips">ดูเพิ่มเติมเกี่ยวกับการดูแลผิว</a>
             <a href="https://dplusskin.co.th/collagen-boost">คอลลาเจนเสริมสร้างผิว</a>
           - Links must point to dplusskin.co.th

        10. **OUTBOUND LINKS (MANDATORY)**
            - Add 1-2 authoritative outbound links:
              <a href="https://example.com/scientific-source" target="_blank" rel="nofollow">แหล่งอ้างอิงวิจัย</a>

        11. **KEYPHRASE DENSITY (MANDATORY)**
            - Keyphrase must appear 3-5 times naturally throughout the content
            - In: title, introduction, 1+ subheading, body paragraphs, conclusion

        =====================================================================
        CONTENT GUIDELINES:
        =====================================================================

        - **STRICT SOFT SELL**: Focus on education, NOT sales. Mention the product {product_name} naturally as a solution or example within the educational context.
        - **NO CTA / NO HARD SELL**: Do NOT use phrases like "Buy now", "Order today", "Discount", or "Don't miss out". Strictly NO sales-oriented language.
        - **Thai Language**: Professional but friendly.
        - **HASHTAGS**: End the post with 3-5 relevant Thai hashtags (e.g., #สกินแคร์ #ผิวใส).
        - **Structure**: Quick Review → Introduction → Body → Conclusion → บทความที่เกี่ยวข้อง (Related Articles) → FAQ
        - **Word Count**: Aim for 1000+ words for maximum depth.

        Output Format: Raw JSON matching this structure:
        {{
            "title": "[Keyphrase] - Brief title under 60 chars",
            "content_html": "Full HTML with H tags, images with alt text containing keyphrase, internal links to dplusskin.co.th, outbound links, 1200+ words, FAQ section at end",
            "excerpt": "Educational summary (2-3 sentences)",
            "seo_keyphrase": "Thai keyphrase phrase (3-5 words, MUST appear in title, intro, subheading, content)",
            "seo_meta_description": "Educational meta description with keyphrase (exactly 150-160 characters)",
            "slug": "english-url-slug-with-keyphrase-translation",
            "suggested_categories": ["Skincare Education", "Health Tips", "Trends"],
            "faq_schema_html": "<script type='application/ld+json'>FAQ schema markup</script>"
        }}

        Remember: You are writing as a TRUSTED EDUCATIONAL SOURCE.
        """
        return self._call_gemini(prompt)

    def rewrite_competitor_content(self, competitor_data, product_name, product_description="", related_articles=None):
        """
        Rewrites competitor content with added scientific depth and investigative journalist tone,
        linking it to a specific brand product.
        """
        prompt = f"""
        You are an Investigative Journalist and SEO Expert focusing on skincare science.

        Competitor Article Summary (The GAP we are filling):
        {json.dumps(competitor_data, ensure_ascii=False)}

        Product to Link: {product_name}
        Product Info: {product_description}

        Brand Identity: {self.brand_guidelines.get('brand_name')}
        Brand tone: {self.brand_guidelines.get('tone_of_voice')}

        {f"Related Articles: {json.dumps(related_articles, ensure_ascii=False)}" if related_articles else ""}

        =====================================================================
        CRITICAL SEO REQUIREMENTS - MUST FOLLOW EXACTLY:
        =====================================================================

        1. **KEYPHRASE SELECTION (MANDATORY)**
           - Choose ONE main Thai keyword phrase (3-5 words) related to the topic
           - This keyphrase MUST be the focus of the entire article

        2. **TITLE FORMAT (MANDATORY)**
           - MUST start with the keyphrase
           - Keep under 60 characters total

        3. **META DESCRIPTION (MANDATORY)**
           - MUST include the keyphrase naturally
           - Exactly 150-160 characters

        4. **INTRODUCTION (MANDATORY)**
           - FIRST paragraph MUST include the keyphrase within first 2 sentences

        5. **SUBHEADINGS (MANDATORY)**
           - At least ONE H2 or H3 MUST contain the keyphrase

        6. **IMAGES WITH ALT TEXT (MANDATORY)**
           - Include 2-3 images with alt text containing keyphrase

        7. **INTERNAL LINKS (MANDATORY)**
           - Add 2-3 internal links to dplusskin.co.th

        8. **CONTENT LENGTH (MANDATORY)**
           - Minimum 800 words

        Task:
        1. Rewrite this content to be BETTER, MORE SCIENTIFIC, and MORE AUTHENTIC.
        2. Tone: Investigative and authoritative (Friend to Friend).
        3. **STRICT THAI LANGUAGE**.
        4. **Length: 800+ words**.
        5. **Structure**: Quick Review -> Intro -> Body -> Conclusion -> บทความที่เกี่ยวข้อง -> FAQ.
        6. **NO HARD SELL / NO CTA**. Focus purely on education. Mention {product_name} as an expert recommendation.
        7. **HASHTAGS**: End with 3-5 relevant Thai hashtags.
        8. Include images with alt text, internal links, outbound links.
        9. Include FAQ section with Schema.org markup.

        Output Format: Raw JSON (same keys as generate_article).
        Do not use markdown formatting.
        """
        return self._call_gemini(prompt)

    def _call_gemini(self, prompt):
        """Call Vertex AI with the prompt."""
        try:
            print("Generator: Calling Vertex AI...")
            # Use maximum token limit for comprehensive articles
            generation_config = GenerationConfig(
                max_output_tokens=8192,
                temperature=0.7,
                top_p=0.95,
                top_k=40
            )
            response = call_vertex_with_retry(self.model, prompt, generation_config=generation_config)
            if not response:
                print("Generator: API returned no response.")
                return None
            print("Generator: API Call successful.")
            content = response.text

            # Clean up common formatting issues
            # Remove markdown code blocks if present
            content = content.replace("```json", "").replace("```", "")
            # Remove any leading/trailing whitespace
            content = content.strip()

            try:
                return json.loads(content)
            except json.JSONDecodeError as je:
                print(f"Generator Error: Failed to parse JSON: {je}")
                print(f"Content preview (first 500 chars): {content[:500]}...")

                # Try to extract and fix partial JSON if response was truncated
                if '{' in content:
                    # Find first { and try to find matching }
                    start = content.find('{')
                    # Try different strategies to find valid JSON
                    for end in range(len(content) - 1, start, -1):
                        if content[end] == '}':
                            try:
                                partial_json = json.loads(content[start:end + 1])
                                print(f"Generator: Recovered partial JSON (length: {end - start + 1} chars).")
                                return partial_json
                            except:
                                continue

                print("Generator Error: Could not recover partial JSON.")
                return None
        except Exception as e:
            print(f"Generator Error: {e}")
            return None
