import os
import json
from dotenv import load_dotenv
from vertex_utils import create_vertex_model, get_model_name_from_env, call_vertex_with_retry

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

    def generate_article(self, product_name, product_description, research_data=None, hot_topic_keywords=None):
        """
        Generates a blog post using the advanced SEO journalist strategy.

        Args:
            product_name: Name of the product
            product_description: Description of the product
            research_data: Research data from researcher agent
            hot_topic_keywords: Keywords from hot topic to focus on (optional)
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

        prompt = f"""
        You are an expert SEO content writer and senior investigative journalist specializing in skincare education.
        Write a comprehensive EDUCATIONAL article about: {product_name}.

        Brand Context: {brand_context}
        Product Info: {product_description}
        {research_context}

        CRITICAL CONTENT GUIDELINES - READ CAREFULLY:

        1. **STRICT SOFT SELL APPROACH (95% Education, 5% Context)**
           - This is an EDUCATIONAL article. Do NOT write it as a product review or sales pitch.
           - Focus entirely on the *problem* (e.g., acne, aging) and the *solution* (e.g., ingredients, habits).
           - **FORBIDDEN WORDS**: "buy", "order", "price", "promotion", "sale", "limited", "shop now", "deal".
           - Mention the product ONLY ONCE or TWICE in the entire body, and only as a "helpful example" of a product containing the ingredients discussed.
           - If the Hot Topic is about "Glass Skin", write about "How to get Glass Skin naturally", not "Buy this cream for Glass Skin".

        2. **TREND & INGREDIENT FOCUS**
           {'- CONNECT TO TREND: Explain why ' + ', '.join(hot_topic_keywords) + ' is trending right now.' if hot_topic_keywords else '- Focus on current skincare standards.'}
           - Explain the SCIENCE: How do the ingredients actually work at a cellular level?
           - Include 3+ lifestyle tips (diet for skin, sleep hygiene, stress) that have NOTHING to do with the product.

        3. **NO PLACEHOLDERS - REAL CONTENT ONLY**
           - DO NOT use [IMAGE_PLACEHOLDER_X] - instead, use relevant emoji icons or descriptive section breaks.
           - DO NOT use [INSERT_INTERNAL_LINK:topic] - instead, write natural contextual mentions.
           - If suggesting related topics, write them as normal text: "คุณอาจสนใจบทความเกี่ยวกับ [หัวข้อ] ได้"

        4. **Structure & Formatting**
           - H1: Main title (Must be catchy/educational, e.g., "5 Secrets to Glass Skin...", NOT "Product Name Review")
           - H2: Section headers (educational topics)
           - H3: Subsections if needed
           - Short paragraphs (2-3 sentences max for mobile)
           - Use bullet points for easy reading
           - Include 2-3 relevant emoji throughout to break up text

        5. **Thai Language & Tone**
           - Professional but friendly (Friend to Friend).
           - Use natural Thai expressions.
           - Avoid robotic or translated-sounding phrases.

        6. **CTA Placement (Crucial)**
           - **ZERO** hard-sell language in the body.
           - At the very end, include a clear but non-aggressive Call to Action (CTA).
           - Explicitly providing a link to buy the product discussed as the perfect solution to the educational topics covered.
           - Format as a separate section: "### สนใจดูแลผิวด้วย [Ingredient]? ..." 
           - Include the following link: {self.brand_guidelines.get('social_links', {}).get('shopee', 'https://shopee.co.th')}

        7. **FAQ Section**
           - 5-7 frequently asked questions
           - Questions should be 100% EDUCATIONAL (e.g., "Vitamin C helps with what?", "Can I use Niacinamide in the morning?").
           - NO questions specific to the product (e.g., "How much is this cream?").

        Output Format: Raw JSON matching this structure:
        {{
            "title": "Thai Educational Title (catchy, trend-focused)",
            "content_html": "Full HTML with H tags, short paragraphs, NO placeholders, FAQ section at end",
            "excerpt": "Educational summary (2-3 sentences)",
            "seo_keyphrase": "Main Thai keyword phrase (related to topic/ingredient, not product name)",
            "seo_meta_description": "Educational meta description (150-160 chars)",
            "slug": "english-url-slug-topic-focused",
            "suggested_categories": ["Skincare Education", "Health Tips", "Trends"],
            "faq_schema_html": "<script type='application/ld+json'>FAQ schema markup</script>"
        }}

        Remember: Your goal is to be a TRUSTED INFORMANT. If you sell too hard, the user leaves. Educate them so well they trust your advice naturally.
        """
        return self._call_gemini(prompt)

    def rewrite_competitor_content(self, competitor_data, product_name, product_description=""):
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
        
        Task:
        1. Rewrite this content to be BETTER, MORE SCIENTIFIC, and MORE AUTHENTIC than the competitor.
        2. Tone: Investigative and authoritative (Friend to Friend).
        3. **STRICT THAI LANGUAGE**.
        4. **Length: 1200+ words**.
        5. Integrate scientific findings (ingredients, cellular effects) that are hidden or missed by the competitor.
        6. **SOFT SELL**: Focus on the education/science. Mention the product {product_name} only at the end as the recommended solution.
        7. NO placeholders. Use real content.
        8. Include FAQ section with Schema.org markup.
        9. **CTA**: Clear link to {self.brand_guidelines.get('social_links', {}).get('shopee', 'https://shopee.co.th')}
        
        Output Format: Raw JSON (same keys as generate_article).
        Do not use markdown formatting.
        """
        return self._call_gemini(prompt)

    def _call_gemini(self, prompt):
        """Call Vertex AI with the prompt."""
        try:
            print("Generator: Calling Vertex AI...")
            response = call_vertex_with_retry(self.model, prompt)
            if not response:
                print("Generator: API returned no response.")
                return None
            print("Generator: API Call successful.")
            content = response.text.replace("```json", "").replace("```", "").strip()
            try:
                return json.loads(content)
            except json.JSONDecodeError as je:
                print(f"Generator Error: Failed to parse JSON. Content: {content[:200]}...")
                return None
        except Exception as e:
            print(f"Generator Error: {e}")
            return None
