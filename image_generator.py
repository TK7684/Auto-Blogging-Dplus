import os
import json
from datetime import datetime
from dotenv import load_dotenv
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

class ImageGenerator:
    def __init__(self):
        load_dotenv()
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        # Updated to Imagen 3 model (imagegeneration@005 is deprecated as of 2025)
        self.model_name = "imagen-3.0-generate-001"

        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT not found in .env")

        vertexai.init(project=self.project_id, location=self.location)
        self.model = ImageGenerationModel.from_pretrained(self.model_name)
        print(f"ImageGenerator initialized with {self.model_name}")

    def generate_image(self, prompt, output_filename="generated_post_image.png"):
        """
        Generates an image based on the prompt and saves it locally.
        """
        print(f"Generating image with prompt: {prompt}")
        try:
            # Clean prompt for Imagen (remove hard-sell or overly specific terms if needed)
            # For now, we trust the prompt passed by main.py
            
            images = self.model.generate_images(
                prompt=prompt,
                number_of_images=1,
                language="en",
                aspect_ratio="1:1"
            )

            if images:
                image_path = os.path.join(os.getcwd(), output_filename)
                images[0].save(location=image_path, include_generation_parameters=False)
                print(f"Image saved to {image_path}")
                return image_path
            else:
                print("No images were generated.")
                return None
        except Exception as e:
            print(f"Error during image generation: {e}")
            return None

    def create_prompt_from_article(self, article_title, article_topic):
        """
        Creates a high-quality Imagen prompt based on the article's title and topic.
        """
        # We want aesthetic, professional skincare photography style
        base_prompt = f"A professional, high-quality, aesthetic commercial photography of {article_topic}. "
        style_details = "Soft natural lighting, clean background, premium skincare brand vibe, 8k resolution, photorealistic."
        
        return base_prompt + style_details
