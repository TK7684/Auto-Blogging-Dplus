import google.generativeai as genai
import os
import json
import requests
from dotenv import load_dotenv
from publisher import WordPressPublisher

class MaintenanceAgent:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
        
        wp_url = os.getenv("WP_URL")
        wp_user = os.getenv("WP_USER")
        wp_pwd = os.getenv("WP_APP_PASSWORD")
        
        if not wp_url or not wp_user or not wp_pwd:
             raise ValueError("WP Credentials missing in .env")
             
        self.publisher = WordPressPublisher(wp_url, wp_user, wp_pwd)
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def audit_and_fix_posts(self):
        """
        Fetches recent posts and checks for errors or outdated info.
        """
        print("Maintenance: Auditing previous posts...")
        posts = self.publisher.get_posts(per_page=10) # Review last 10 posts
        
        for post in posts:
            post_id = post.get('id')
            title = post.get('title', {}).get('rendered', '')
            content = post.get('content', {}).get('rendered', '')
            
            prompt = f"""
            You are a Maintenance Auditor for a Skincare Blog.
            Post Title: {title}
            Post Content: {content}

            Task:
            1. Identify any misleading information or outdated scientific claims.
            2. Check for broken CTAs or incorrect product info.
            3. If fixes are needed, provide the FULL CORRECTED HTML CONTENT.

            Format the output as JSON:
            {{
                "needs_update": true/false,
                "reason": "Why it needs update",
                "corrected_content_html": "Full HTML if needs_update is true, else null"
            }}
            Do not use markdown formatting.
            """
            
            try:
                response = self.model.generate_content(prompt)
                res = json.loads(response.text.replace("```json", "").replace("```", "").strip())
                
                if res.get('needs_update'):
                    print(f"Maintenance: Updating Post {post_id} - {title}...")
                    self.publisher.update_post(post_id, {"content": res.get('corrected_content_html')})
                    print(f"Maintenance: Fixed Post {post_id}")
                else:
                    print(f"Maintenance: Post {post_id} is OK.")
                    
            except Exception as e:
                print(f"Maintenance Error on Post {post_id}: {e}")

if __name__ == "__main__":
    # Test requires real WP connection
    try:
        maint = MaintenanceAgent()
        # maint.audit_and_fix_posts()
        print("Maintenance Agent initialized.")
    except Exception as e:
        print(f"Init failed: {e}")
