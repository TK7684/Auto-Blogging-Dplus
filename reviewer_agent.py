import os
import json
from dotenv import load_dotenv
from vertex_utils import create_vertex_model, get_model_name_from_env, call_vertex_with_retry

class ReviewerAgent:
    def __init__(self):
        load_dotenv()
        self.model_name = get_model_name_from_env("gemini-2.0-flash-exp")

        # Validate Vertex AI configuration
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise ValueError("GOOGLE_CLOUD_PROJECT not found in .env. "
                           "Please set your Google Cloud Project ID.")

        self.model = create_vertex_model(self.model_name)

        # Load compliance rules
        self.compliance_rules = {}
        if os.path.exists("compliance_rules.json"):
            with open("compliance_rules.json", "r", encoding="utf-8") as f:
                self.compliance_rules = json.load(f)
        
    def update_model(self, model_name):
        """Updates the underlying Vertex AI model."""
        self.model_name = model_name
        self.model = create_vertex_model(model_name)
        print(f"Reviewer: Model updated to {model_name}")

    def review_article(self, article):
        """
        Audits the article for compliance, scientific accuracy, and style.
        """
        prompt = f"""
        You are a Professional Editor and Thai FDA Compliance Officer specializing in skincare education content.

        Article Title: {article.get('title')}
        Article Content: {article.get('content_html')}

        Compliance Rules:
        Allowed Words: {self.compliance_rules.get('allowed_words', [])}
        Forbidden Words: {self.compliance_rules.get('forbidden_words', [])}

        CRITICAL REVIEW CHECKLIST - Check ALL of the following:

        1. **PLACEHOLDER CHECK** - IMMEDIATE REJECTION if found:
           - [IMAGE_PLACEHOLDER_X] patterns
           - [INSERT_INTERNAL_LINK:X] patterns
           - Any other bracketed placeholders
           Status: {"HAS PLACEHOLDERS - MUST FIX" if "[" in str(article.get('content_html', '')) and "PLACEHOLDER" in str(article.get('content_html', '')).upper() else "OK"}

        2. **SOFT SELL CHECK (80% Education, 20% Promotion)**:
           - Is the content primarily educational (teaching about ingredients, science, skincare)?
           - Is product mentioned only 1-2 times naturally in context?
           - NO aggressive CTAs like "buy now", "order today", "limited offer", "special price"
           - Positioning: Product as ONE option, not THE ONLY solution

        3. **INGREDIENT OVERLOAD CHECK**:
           - Are there more than 3-4 main ingredients discussed?
           - Is there a long ingredient list dump?
           - Should focus on 2-3 KEY ingredients related to the main topic

        4. **FDA COMPLIANCE**:
           - No forbidden words from compliance list
           - No medical treatment claims (รักษา, หายขาด, รักษาได้หายดี)
           - No absolute claims (ที่สุด, ดีที่สุด, อันดับ 1)

        5. **CONTENT FLOW**:
           - Educational introduction
           - Scientific explanation of ingredients/mechanism
           - Lifestyle tips (diet, sleep, stress)
           - Subtle product mention (optional, in context)
           - ONE subtle CTA at very end only

        Task:
        1. Check for ALL issues above
        2. If ANY placeholder found -> status = "needs_fix" with specific location
        3. If hard sell detected -> status = "needs_fix" with examples
        4. If ingredient overload -> status = "needs_fix" with guidance
        5. Provide specific, actionable feedback

        Format the output as JSON:
        {{
            "status": "approved" or "needs_fix",
            "compliance_warnings": ["specific_warning_1", "specific_warning_2"],
            "editor_feedback": "Detailed feedback with specific examples of what to fix",
            "suggested_title": "Alternative title if current one is too salesy",
            "suggested_improvements": ["specific_improvement_1", "specific_improvement_2"],
            "has_placeholders": true/false,
            "is_hard_sell": true/false,
            "ingredient_overload": true/false
        }}
        Do not use markdown formatting.
        """

        print("Reviewer: Auditing article...")
        try:
            print("Reviewer: Calling Vertex AI...")
            response = call_vertex_with_retry(self.model, prompt)
            if not response: return None
            print("Reviewer: API Call successful.")
            content = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            print(f"Reviewer Error: {e}")
            return None
