import google.generativeai as genai
import os
import json
import random
from dotenv import load_dotenv

class ContentGenerator:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found.")
        
        genai.configure(api_key=api_key)
        # Use model from env or default to flexible one
        model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")
        print(f"Generator using model: {model_name}")
        self.model = genai.GenerativeModel(model_name) 
        
        self.compliance_rules = self._load_compliance_rules()

    def _load_compliance_rules(self):
        try:
            with open("compliance_rules.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print("Warning: compliance_rules.json not found. Compliance checks will be skipped.")
            return {"allowed_words": [], "forbidden_words": []}

    def generate_article(self, product_name, product_info, product_topic=None):
        """Generates a soft-sell article for the product."""
        
        allowed_claims = ", ".join(self.compliance_rules.get("allowed_words", [])[:50]) # Limit to first 50 hints
        forbidden_claims = ", ".join(self.compliance_rules.get("forbidden_words", [])[:50])

        topic_prompt = ""
        if product_topic:
            topic_prompt = f"Topic Focus: {product_topic}"
        else:
            topic_prompt = "Topic Focus: Choose a trending skincare/health topic relevant to the product benefits."

        prompt = f"""
        act as a Thai Cosmetic SEO Expert and Copywriter.
        
        Task: Write an engaging, education-first article in Thai about a health/beauty topic that naturally leads to the product: "{product_name}".
        
        Product Info:
        {product_info}
        
        {topic_prompt}
        
        Strategy (Soft Sell):
        1. Start with a hook about a common problem or trend (80% of content).
        2. Educate the reader on ingredients or solutions.
        3. Gently introduce "{product_name}" as a solution that contains these ingredients (20% of content).
        4. End with a specific Call to Action (CTA).
        
        Compliance Rules (Thai FDA):
        - STRICTLY use ONLY allowed claims.
        - DO NOT use forbidden words or over-claim (e.g., "cure", "instant", "miracle").
        - Forbidden examples: {forbidden_claims}...
        - Allowed examples: {allowed_claims}...
        
        Required Output Structure (JSON):
        {{
            "title": "Catchy SEO Title in Thai",
            "content_html": "<p>...</p>",
            "excerpt": "Short summary",
            "tags": ["tag1", "tag2"],
            "category": "Health/Beauty"
        }}
        
        CTA to include at the end is EXACTLY:
        "สนใจสั่งซื้อสินค้าได้ที่ Shopee: https://s.shopee.co.th/BNONxdisb"
        """

        try:
            response = self.model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            return json.loads(response.text)
        except Exception as e:
            print(f"Error generating content: {e}")
            return None

if __name__ == "__main__":
    gen = ContentGenerator()
    # Mock data for testing
    print(gen.generate_article("Test Product", "Good for skin, contains collagen."))
