import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print(f"Testing key ending in ...{api_key[-5:]}")
model = genai.GenerativeModel("gemini-pro")

try:
    model = genai.GenerativeModel("gemini-1.5-flash") # Try 1.5 first
    print("Testing gemini-1.5-flash...")
    response = model.generate_content("Hello")
    print("Success 1.5-flash")
except Exception as e:
    print(f"Failed 1.5-flash: {e}")

try:
    model = genai.GenerativeModel("gemini-2.5-flash") # Try 2.5
    print("Testing gemini-2.5-flash...")
    response = model.generate_content("Hello")
    print("Success 2.5-flash")
except Exception as e:
    print(f"Failed 2.5-flash: {e}")
