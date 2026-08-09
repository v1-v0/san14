import re, csv, requests, os
from bs4 import BeautifulSoup

URL = "https://www.gamecity.com.tw/sangokushi14/officers-list.html"
html = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
html.encoding = html.apparent_encoding          # important for Big5/UTF-8
soup = BeautifulSoup(html.text, "html.parser")

text = soup.get_text("\n")
tokens = [t.strip() for t in text.split("\n") if t.strip()]

pairs = {}
for a, b in zip(tokens, tokens[1:]):
    if re.fullmatch(r"\d{1,4}", a) and not re.fullmatch(r"\d+", b):
        n = int(a)
        if 1 <= n <= 1000:
            pairs.setdefault(n, b)

rows = [(n, pairs[n]) for n in sorted(pairs)]
print("count =", len(rows))                      # expect 1000

# Save to CSV under local Downloads folder
downloads = os.path.expanduser("~/Downloads")
os.makedirs(downloads, exist_ok=True)
outfile = os.path.join(downloads, "sangokushi14_officers.csv")
with open(outfile, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["no", "name"])
    w.writerows(rows)