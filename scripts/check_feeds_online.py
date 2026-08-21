"""One-off: verify every online feed/endpoint used by Cripple is reachable."""
import json
import urllib.request
import ssl
import concurrent.futures
from pathlib import Path

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'}
ctx = ssl.create_default_context()

SOURCES = json.load(open('netstrip/data/updater_sources.json', encoding='utf-8'))['sources']
EXTRA = [
    ('GeoLite2 City DB', 'https://raw.githubusercontent.com/P3TERX/GeoLite.mmdb/download/GeoLite2-City.mmdb', 2000000),
    ('Update check API', 'https://api.github.com/repos/neohiro/Cripple-NetStrip/releases/latest', 10),
    ('dnscrypt resolvers', 'https://raw.githubusercontent.com/DNSCrypt/dnscrypt-resolvers/master/v3/public-resolvers.md', 100),
    ('ipwho.is', 'https://ipwho.is/', 10),
    ('ipinfo.io', 'https://ipinfo.io/json', 10),
    ('ipapi.co', 'https://ipapi.co/json/', 10),
    ('api.ipify.org', 'https://api.ipify.org', 10),
]

def check(name, url, min_bytes=50):
    try:
        req = urllib.request.Request(url, headers=UA, method='GET')
        with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
            code = r.getcode()
            data = r.read(min_bytes + 1)
            ok = code == 200 and len(data) >= min_bytes
            return name, url, code, len(data), ok
    except Exception as e:
        return name, url, getattr(e, 'code', None), 0, False

jobs = [(s['name'], s['url'], 50) for s in SOURCES] + EXTRA
results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
    futs = [ex.submit(check, *j) for j in jobs]
    for f in concurrent.futures.as_completed(futs):
        results.append(f.result())

results.sort(key=lambda r: (r[4], r[0]))
dead = [r for r in results if not r[4]]
print(f"TOTAL {len(results)} | ALIVE {len(results)-len(dead)} | DEAD {len(dead)}")
for name, url, code, size, ok in results:
    if not ok:
        print(f"DEAD [{code}] {name} :: {url}")
print("--- all alive:" if not dead else "---")
