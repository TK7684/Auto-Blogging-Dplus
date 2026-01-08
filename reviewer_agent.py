import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

class ReviewerAgent:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        
        # Load compliance rules
        self.compliance_rules = {}
        if os.path.exists("compliance_rules.json"):
            with open("compliance_rules.json", "r", encoding="utf-8") as f:
                self.compliance_rules = json.load(f)

    def review_article(self, article):
        """
        Audits the article for compliance, scientific accuracy, and style.
        """
        prompt = f"""
        You are a Professional Editor and Thai FDA Compliance Officer.
        
        Article Title: {article.get('title')}
        Article Content: {article.get('content_html')}
        
        Compliance Rules:
        Allowed Words: {self.compliance_rules.get('allowed_words', [])}
        Forbidden Words: {self.compliance_rules.get('forbidden_words', [])}

        Task:
        1. Check if the article uses any FORBIDDEN words.
        2. Verify if the tone is "Soft Sell" (not hard selling).
        3. Check for structural flow (Introduction -> Scientific Education -> Product Tie-in -> CTA).
        4. Provide specific feedback for improvements or approve it.

        Format the output as JSON:
        {{
            "status": "approved" or "needs_fix",
            "compliance_warnings": ["issue1", ...],
            "editor_feedback": "Detailed feedback",
            "suggested_title": "Alternative if better",
            "suggested_improvements": ["fix1", ...]
        }}
        Do not use markdown formatting.
        """
        
        print("Reviewer: Auditing article...")
        try:
            response = self.model.generate_content(prompt)
            content = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            print(f"Reviewer Error: {e}")
            return None

if __name__ == "__main__":
    reviewer = ReviewerAgent()
    demo_article = {"title": "Test", "content_html": "This is a miracle cure."}
    res = reviewer.review_article(demo_article)
    print(json.dumps(res, indent=4, ensure_ascii=False))
