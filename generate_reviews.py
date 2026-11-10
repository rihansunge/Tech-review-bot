import os
import json
import requests
import random

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "rihanqa-20")

API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

CATEGORIES = ["Laptops & PC Accessories", "Audio & Headphones", "Smart Home & Lighting", "Desk Setup & Ergonomics", "Mobile & Wearables"]

def fetch_daily_affiliate_review():
    selected_category = random.choice(CATEGORIES)
    
    prompt = f"""
    Select ONE popular, real tech product in the "{selected_category}" category available on Amazon.
    Generate a short review article. Respond ONLY with valid JSON in this exact structure:
    {{
      "title": "Catchy review title mentioning product name",
      "date": "Today's date YYYY-MM-DD",
      "category": "{selected_category}",
      "summary": "2-3 sentences explaining pros and why it's worth buying.",
      "searchKeywords": "Exact brand and model name",
      "badgeText": "Short tag like 'Best Overall' or 'Top Pick'"
    }}
    """

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    try:
        response = requests.post(API_URL, json=payload, headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            data = response.json()
            item = json.loads(data['candidates'][0]['content']['parts'][0]['text'])
            encoded_query = requests.utils.quote(item['searchKeywords'])
            item['affiliateLink'] = f"https://www.amazon.com/s?k={encoded_query}&tag={AFFILIATE_TAG}"
            return item
        else:
            print("API Error:", response.status_code, response.text)
            return None
    except Exception as e:
        print("Script Exception:", str(e))
        return None

if __name__ == "__main__":
    new_review = fetch_daily_affiliate_review()
    if new_review:
        data_file = "posts.json"
        posts = []
        if os.path.exists(data_file):
            try:
                with open(data_file, "r") as f:
                    posts = json.load(f)
            except Exception:
                posts = []

        posts.insert(0, new_review)
        posts = posts[:20]

        with open(data_file, "w") as f:
            json.dump(posts, f, indent=2)

        print(f"Successfully added: {new_review['title']}")
