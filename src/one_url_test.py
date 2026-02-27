# %%
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
import json
import time
import random
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed



INPUT_FILE = "../data/urls.jsonl"
OUTPUT_FILE = "../data/raw_rows.jsonl"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-GB,en;q=0.9",
}


# get text from one url 
def load_urls():
    items = []
    with open(INPUT_FILE, "r", encoding="utf-8") as urls:
        for line in urls:
            if line.strip():
                items.append(json.loads(line))
    return items

urls = load_urls()
print(f'Loaded {len(urls)} URLs')
print(urls[0]['url'])
#%%
req = requests.get(urls[0]['url'],headers=HEADERS)
soup=BeautifulSoup(req.text,'lxml')
text = soup.get_text(" ", strip=True)

h4=soup.find_all('h4', class_=None)

data = {}
for h4 in soup.find_all("h4"):
    label = h4.get_text(strip=True)
    value_tag = h4.find_next()
    if value_tag:
        value = value_tag.get_text(strip=True)
        data[label] = value
        
# price
price = None
m = re.search(r"(\d[\d\s.,\u202F\u00A0]*)\s*€", text)
if m:
    raw = (m.group(1)
           .replace(" ", "")
           .replace("\u202F", "")  # thin space
           .replace("\u00A0", "")  # NBSP
           .replace(",", "")
           .replace(".", ""))
    if raw.isdigit():
        price = int(raw)
        
path = urlparse(urls[0]['url']).path.rstrip("/")
immovlan_id = path.split("/")[-1].upper()
print(immovlan_id)

print(price)
        
#print(data)
# %%
