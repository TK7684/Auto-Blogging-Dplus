import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY") 
if not api_key:
    print("Error: GEMINI_API_KEY not found in environment variables.")
    exit(1)

print(f"Debug: Using API Key: {api_key[:5]}...{api_key[-5:]}")
genai.configure(api_key=api_key)

def process_compliance():
    if not os.path.exists("compliance_text.txt"):
        print("Error: compliance_text.txt not found. Run extract_pdf.py first.")
        return

    with open("compliance_text.txt", "r", encoding="utf-8") as f:
        text = f.read()

    # The text is long, but 1.5 Flash has a large context window.
    prompt = f"""
    You are an expert in Thai FDA Cosmetic Regulations.
    I have extracted the text from the "Cosmetic Advertising Manual 2024" (คู่มือการโฆษณาเครื่องสำอางค์ 2567).
    
    Your task is to analyze this text and extract two lists:
    1. "allowed_words": Words or phrases that are explicitly mentioned as Acceptable Claims (Do).
    2. "forbidden_words": Words or phrases that are explicitly mentioned as Unacceptable Claims (Don't) or prohibited/over-claiming.
    
    Return the result as a raw JSON object with keys "allowed_words" and "forbidden_words".
    Do not wrap in markdown.
    
    Text content:
    {text}
    """

    print("Sending request to Gemini...")
    
    candidates = [
        'gemini-1.5-flash',
        'models/gemini-1.5-flash',
        'gemini-1.5-pro',
        'models/gemini-1.5-pro', 
        'gemini-pro',
        'models/gemini-2.0-flash-exp'
    ]
    
    response = None
    for model_name in candidates:
        print(f"Trying model: {model_name}...")
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            print(f"Success with {model_name}!")
            break
        except Exception as e:
            print(f"Failed with {model_name}: {e}")
    
    if not response:
        print("All models failed.")
        return
    
    try:
        # Clean up if markdown is present
        content = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        
        with open("compliance_rules.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("Successfully saved compliance_rules.json")
        
    except Exception as e:
        print(f"Error parsing response: {e}")
        try:
            print("Raw response:", response.text)
        except:
            pass

if __name__ == "__main__":
    process_compliance()
