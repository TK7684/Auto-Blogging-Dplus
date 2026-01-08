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
    def generate_article(self, product_name, product_description, research_data=None):
        """
        Generates a blog post using the soft-sell strategy.
        """
        research_context = ""
        if research_data:
            research_context = f"""
            Scientific Context:
            {json.dumps(research_data.get('scientific_references', []), ensure_ascii=False)}
            Key Takeaways: {research_data.get('key_takeaways', '')}
            """

        prompt = f"""
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
