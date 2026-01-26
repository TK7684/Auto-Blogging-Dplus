import requests
import base64
import os
import json
from datetime import datetime

class WordPressPublisher:
    def __init__(self, wp_url, wp_user, wp_password):
        self.wp_url = wp_url.rstrip('/')
        self.auth = (wp_user, wp_password)
        self.api_url = f"{self.wp_url}/wp-json/wp/v2"

    def upload_media(self, image_path, title=None):
        """Uploads an image to WordPress."""
        media_url = f"{self.api_url}/media"
        
        try:
            with open(image_path, 'rb') as img:
                headers = {
                    'Content-Disposition': f'attachment; filename="{os.path.basename(image_path)}"',
                    'Content-Type': 'image/jpeg' # Adjust based on file type if needed
                }
                
                response = requests.post(
                    media_url, 
                    auth=self.auth, 
                    headers=headers, 
                    data=img
                )
                
                if response.status_code == 201:
                    data = response.json()
                    print(f"Image uploaded successfully: {data['source_url']}")
                    return data['id']
                else:
                    print(f"Failed to upload image: {response.text}")
                    return None
        except Exception as e:
            print(f"Error uploading media: {e}")
            return None

    def create_post(self, title, content, status='draft', category_ids=None, tag_ids=None, featured_media_id=None, slug=None, seo_data=None, date=None):
        """Creates a new WordPress post with SEO data."""
        post_url = f"{self.api_url}/posts"
        
        data = {
            'title': title,
            'content': content,
            'status': status,
            'date': date if date else datetime.now().isoformat()
        }
        
        if slug:
            data['slug'] = slug
            
        if category_ids:
            data['categories'] = category_ids
        if tag_ids:
            data['tags'] = tag_ids
        if featured_media_id:
            data['featured_media'] = featured_media_id

        # Yoast SEO & Meta Data
        if seo_data:
            data['meta'] = {
                '_yoast_wpseo_focuskw': seo_data.get('seo_keyphrase', ''),
                '_yoast_wpseo_metadesc': seo_data.get('seo_meta_description', '')
            }

        try:
            print(f"Creating post with data: {json.dumps({k: v for k, v in data.items() if k != 'content'}, indent=2)}")
            print(f"Content length: {len(content)} characters")
            response = requests.post(post_url, auth=self.auth, json=data)
            
            if response.status_code == 201:
                post_data = response.json()
                print(f"Post created successfully: {post_data['link']}")
                print(f"Post ID: {post_data['id']}")
                print(f"Post status: {post_data.get('status', 'unknown')}")
                print(f"Post date: {post_data.get('date', 'unknown')}")
                return post_data['id']
            else:
                print(f"Failed to create post: {response.status_code}")
                print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"Error creating post: {e}")
            return None

    def get_posts(self, per_page=10, page=1):
        url = f"{self.api_url}/posts?per_page={per_page}&page={page}"
        try:
            response = requests.get(url, auth=self.auth)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error fetching posts: {response.status_code}")
                return []
        except Exception as e:
            print(f"Fetcher Exception: {e}")
            return []

    def update_post(self, post_id, data):
        url = f"{self.api_url}/posts/{post_id}"
        try:
            # WordPress REST API expects POST for updates with ID in URL
            response = requests.post(url, json=data, auth=self.auth)
            if response.status_code == 200:
                return True
            else:
                print(f"Error updating post {post_id}: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                return False
        except Exception as e:
            print(f"Update Exception: {e}")
            return False

if __name__ == "__main__":
    # Test block
    from dotenv import load_dotenv
    load_dotenv()
    
    wp_url = os.getenv("WP_URL")
    wp_user = os.getenv("WP_USER")
    wp_pwd = os.getenv("WP_APP_PASSWORD")
    
    if wp_url and wp_user and wp_pwd:
        publisher = WordPressPublisher(wp_url, wp_user, wp_pwd)
        # publisher.create_post("Test Post", "This is a test content.", status="draft")
    else:
        print("WP credentials not set in .env")
