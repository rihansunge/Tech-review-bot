"""Daily job: ask Gemini (with Google Search) for one trending tech product,
write a short summary, and add it to posts.json. Uses only the Python standard library."""
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()
TAG = os.environ.get("AFFILIATE_TAG", "").strip()
DOMAIN = os.environ.get("AMAZON_DOMAIN", "amazon.ae").strip()
POSTS_FILE = "posts.json"
MAX_POSTS = 60

if not API_KEY:
    sys.exit("GEMINI_API_KEY is missing. Add it under Settings > Secrets and variables > Actions.")

try:
    with open(POSTS_FILE, encoding="utf-8") as f:
        posts = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    posts = []

already = [p.get("product", "") for p in posts[:30]]

prompt = f"""Use Google Search to find ONE consumer electronics product (laptop, desk accessory,
audio gear, monitor, keyboard, etc.) that is getting attention this week.
Do NOT pick any of these products already covered: {json.dumps(already)}.

Write a short, honest summary based only on what published reviews and spec sheets say.
Never claim you tested the product yourself. Do not invent specs, prices, or quotes.

Reply with ONLY a JSON object, no other text, in this shape:
{{"product": "exact product name",
  "title": "short post title",
  "summary": "2-3 sentences on what it is and who it suits",
  "pros": ["3 short points"],
  "cons": ["2-3 short points"],
  "verdict": "one sentence",
  "search_query": "words to search for this product on Amazon"}}"""

body = json.dumps({
    "contents": [{"parts": [{"text": prompt}]}],
    "tools": [{"google_search": {}}],
}).encode("utf-8")

url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
req = urllib.request.Request(
    url, data=body, method="POST",
    headers={"Content-Type": "application/json", "x-goog-api-key": API_KEY},
)

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
except urllib.error.HTTPError as e:
    sys.exit(f"Gemini API error {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")

try:
    cand = data["candidates"][0]
    text = "".join(part.get("text", "") for part in cand["content"]["parts"])
except (KeyError, IndexError):
    sys.exit(f"Unexpected Gemini reply: {json.dumps(data)[:500]}")

match = re.search(r"\{.*\}", text, re.DOTALL)
if not match:
    sys.exit(f"No JSON found in reply: {text[:500]}")
item = json.loads(match.group(0))

for key in ("product", "title", "summary", "pros", "cons", "verdict", "search_query"):
    if not item.get(key):
        sys.exit(f"Reply is missing '{key}'. Nothing was saved.")

if item["product"].strip().lower() in [a.strip().lower() for a in already]:
    sys.exit("Gemini picked a product that is already on the site. Nothing was saved.")

query = urllib.parse.quote_plus(item["search_query"])
link = f"https://www.{DOMAIN}/s?k={query}"
if TAG:
    link += f"&tag={urllib.parse.quote_plus(TAG)}"

sources = []
for chunk in cand.get("groundingMetadata", {}).get("groundingChunks", [])[:3]:
    web = chunk.get("web", {})
    if web.get("uri"):
        sources.append({"title": web.get("title", "source"), "url": web["uri"]})

posts.insert(0, {
    "date": datetime.date.today().isoformat(),
    "product": item["product"],
    "title": item["title"],
    "summary": item["summary"],
    "pros": item["pros"][:4],
    "cons": item["cons"][:4],
    "verdict": item["verdict"],
    "link": link,
    "sources": sources,
})

with open(POSTS_FILE, "w", encoding="utf-8") as f:
    json.dump(posts[:MAX_POSTS], f, ensure_ascii=False, indent=2)

print(f"Added: {item['product']}")
