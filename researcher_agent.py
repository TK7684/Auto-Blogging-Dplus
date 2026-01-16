import os
import json
from dotenv import load_dotenv
from vertex_utils import create_vertex_model, get_model_name_from_env, call_vertex_with_retry

class ResearcherAgent:
    def __init__(self):
        load_dotenv()
        self.model_name = get_model_name_from_env("gemini-2.0-flash-exp")

        # Validate Vertex AI configuration
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise ValueError("GOOGLE_CLOUD_PROJECT not found in .env. "
                           "Please set your Google Cloud Project ID.")

        # Enable Google Search Grounding for research
        self.use_search_tool = True
        self.model = create_vertex_model(self.model_name, use_search_tool=self.use_search_tool)

    def update_model(self, model_name):
        """Updates the underlying Vertex AI model."""
        self.model_name = model_name
        self.model = create_vertex_model(model_name, use_search_tool=self.use_search_tool)
        print(f"Researcher: Model updated to {model_name}")

    def research_product_topics(self, product_name, product_description):
        """
        Gathers scientific references, trending topics, and IMAGES for a specific product.
        Focuses on scientific validation.
        """
        prompt = f"""
        You are a Beauty Science Researcher with access to Google Search.
        Product: {product_name}
        Description: {product_description}

        Task:
        1. Search for trending skincare topics related to this product's ingredients in Thailand.
        2. Find scientific facts and studies (e.g., PubMed, Journal of Cosmetic Science, NCBI).
        3. **Provide at least 3 SPECIFIC CITATIONS** with titles and URLs.
        4. Find 3-5 high-quality IMAGE URLs (JPG/PNG/WEBP) related to ingredients or benefits.
        
        Format the output as JSON:
        {{
            "trending_topics": ["topic1", "topic2"],
            "scientific_references": [
                {{"fact": "fact description", "source_name": "Paper Title", "source_url": "URL"}}
            ],
            "image_urls": ["url1", "url2"],
            "key_takeaways": "Summary of research"
        }}
        Do not use markdown formatting.
        """
        return self._call_gemini(f"Investigating {product_name}", prompt)

    def research_hot_topics(self, niche="skincare and supplements"):
        """
        Finds the hottest trending topics in the Thai market for a given niche.
        """
        prompt = f"""
        You are a Trend Analyst for the Thai {niche} market.
        Access Google Search to find what people in Thailand are currently worried about or interested in regarding {niche}, health, and lifestyle.
        
        Task:
        1. Identify the TOP 3 "Hot Topics" right now in Thailand (can be broader than just skincare, e.g., PM2.5, Heatwave, Stress, New Year, Songkran).
        2. For each topic, provide:
           - A catchy Thai headline.
           - Why it's trending.
           - **How it relates to skincare/health** (e.g., "PM2.5 causes acne", "Heatwave dehydrates skin").
           - Key ingredients people are searching for related to this problem.

        Format the output as JSON:
        {{
            "hot_topics": [
                {{
                    "headline_th": "Thai Headline",
                    "reason": "Why it's hot",
                    "connection": "Connection to skincare/health",
                    "keywords": ["keyword1", "keyword2"]
                }}
            ]
        }}
        Do not use markdown formatting.
        """
        return self._call_gemini("Finding Hot Topics in Thailand", prompt)

    def fetch_competitor_rss(self, rss_urls):
        """
        Fetches latest articles from competitor RSS feeds.
        """
        import feedparser
        all_entries = []
        for url in rss_urls:
            print(f"Researcher: Fetching RSS from {url}...")
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]: # Get top 10 from each
                all_entries.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": entry.summary if 'summary' in entry else ""
                })
        return all_entries

    def analyze_content_gap(self, own_post_titles, competitor_articles):
        """
        Identifies topics competitors covered that we haven't.
        """
        prompt = f"""
        You are a Content Strategist. 
        Own Post Titles: {json.dumps(own_post_titles, ensure_ascii=False)}
        Competitor Articles: {json.dumps(competitor_articles, ensure_ascii=False)}

        Task:
        1. Analyze the competitor articles against our own posts.
        2. Identify 3 "Content Gaps" (topics they covered well but we haven't covered yet).
        3. For each gap, propose a specific high-traffic target title for us.

        Format output as JSON:
        {{
            "content_gaps": [
                {{
                    "competitor_topic": "Their topic",
                    "proposed_title": "Our better title",
                    "reason": "Why this gap matters"
                }}
            ]
        }}
        Do not use markdown.
        """
        return self._call_gemini("Analyzing Content Gaps", prompt)

    def research_competitors(self, niche="skincare and food supplements"):
        """
        Searches for high-traffic competitor articles in Thailand and summarizes them for rewriting.
        """
        # We can combine organic search with RSS if we have URLs
        prompt = f"""
        You are a Competitive Intelligence Agent.
        Search for top-ranking blog posts or articles in Thailand about {niche}.
        
        Task:
        1. Find 3 high-performing competitor articles.
        2. Summarize the main points they cover.
        3. Identify "missing pieces" or areas where we can add more scientific depth.

        Format the output as JSON:
        {{
            "competitors": [
                {{
                    "title": "Competitor Title",
                    "url": "URL",
                    "summary": "Thai summary of content",
                    "gap": "What they missed (scientific depth)"
                }}
            ]
        }}
        Do not use markdown formatting.
        """
        return self._call_gemini("Researching Competitors", prompt)

    def _call_gemini(self, log_message, prompt):
        """Call Vertex AI with the prompt."""
        print(f"Researcher: {log_message}...")
        try:
            print("Researcher: Calling Vertex AI...")
            response = call_vertex_with_retry(self.model, prompt)
            if not response:
                print("Researcher: API returned no response.")
                return None

            print("Researcher: API Call successful.")
            content = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            print(f"Researcher Error for {log_message}: {e}")
            return None
