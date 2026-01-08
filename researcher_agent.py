import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

class ResearcherAgent:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def research_product_topics(self, product_name, product_description):
        """
        Gathers scientific references and trending topics for a specific product.
        """
        prompt = f"""
        You are a Beauty Science Researcher. 
        Product: {product_name}
        Description: {product_description}

        Task:
        1. Search for trending skincare topics related to this product's ingredients in Thailand.
        2. Find scientific facts and studies (e.g., PubMed, Journal of Cosmetic Science) that back up the benefits.
        3. Identify 3-5 core scientific references or facts to include in a blog post.
        
        Format the output as JSON:
        {{
            "trending_topics": ["topic1", "topic2"],
            "scientific_references": [
                {{"fact": "fact description", "source": "Citation info"}},
                ...
            ],
            "key_takeaways": "Summary of research"
        }}
        Do not use markdown formatting.
        """
        
        print(f"Researcher: Investigating {product_name}...")
        try:
            # Use search if available, otherwise rely on internal knowledge base (Gemini 3/2.5 is very capable)
            # Note: For real-time search, one would use tool='google_search' if the API supports it.
            # For now, we rely on Gemini's extensive training data for scientific facts.
            response = self.model.generate_content(prompt)
            content = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            print(f"Researcher Error: {e}")
            return None

if __name__ == "__main__":
    # Test run
    researcher = ResearcherAgent()
    res = researcher.research_product_topics("Collagen", "High quality marine collagen for skin hydration.")
    print(json.dumps(res, indent=4, ensure_ascii=False))
