import re
from datastore import store_price
from requests import request
from types import SimpleNamespace
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

default_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'sec-ch-ua': '"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'script',
    'sec-fetch-mode': 'no-cors',
    'sec-fetch-site': 'same-origin'
}

cache = {}


def fetch_price(rule: SimpleNamespace, config: SimpleNamespace, idx: int):
    print(f"[{idx}] Fetching: {rule.url}")
    price = None

    try:
        content = None
        if hasattr(config, 'cache') and rule.url in config.cache.__dict__ and f"{rule.url}__time" in cache:
            cacheMins = config.cache.__dict__[rule.url]
            cacheTime = cache[f"{rule.url}__time"]
            cacheContent = cache[f"{rule.url}__content"]
            if (cacheTime + timedelta(minutes=cacheMins) >= datetime.utcnow()):
                print(f"[{idx}] Using cached content for: {rule.url}")
                content = cacheContent
            else:
                cache.pop(f"{rule.url}__time", None)
                cache.pop(f"{rule.url}__content", None)

        if content is None:
            hds = default_headers
            if hasattr(rule, 'referer'):
                if type(rule.referer) is bool:
                    hds['Referer'] = rule.url
                elif type(rule.referer) is str:
                    hds['Referer'] = rule.referer
            resp = request('GET', rule.url, headers=default_headers)

            if (resp.status_code >= 300):
                print(f"[{idx}] HTTP error: Status Code {resp.status_code}")
                return
            
            content = resp.content.decode('utf8')

            cache[f"{rule.url}__content"] = content
            cache[f"{rule.url}__time"] = datetime.utcnow()

        bs = BeautifulSoup(content, features="html.parser")

        if hasattr(rule, 'selector'):
            if type(rule.selector) is str:
                match = bs.select_one(rule.selector)
                if match is not None:
                    price = sanitize_price(match.get_text())
            elif type(rule.selector) is list:
                for expr in rule.selector:
                    match = bs.select_one(expr)
                    if match is not None:
                        price = sanitize_price(match.get_text())
        elif hasattr(rule, 'regex'):
            if type(rule.regex) is str:
                match = re.search(rule.regex, content)
                if match is not None:
                    price = sanitize_price(match.group(1))
            elif type(rule.regex) is list:
                for r in rule.regex:
                    match = re.search(r, content)
                    if match is not None:
                        price = sanitize_price(match.group(1))

        if price is None:
            print(f"[{idx}] No price found.")
            return

        price = float(price) / 100.0 if hasattr(rule, 'divide') and rule.divide else float(price)

        # TODO: Record price
        print(f"[{idx}] Storing price: {price}")
        store_price(price, rule.name, config)
        print(f"[{idx}] Done!")

    except Exception as ex:
        print(f"[{idx}] ERROR while processing: {ex}")

def sanitize_price(rawPrice: str) -> float:
    return float(re.sub(r"[^0-9.]", "", rawPrice))