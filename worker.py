import re
import random
from datastore import get_recent_prices, store_price, store_sparkline, add_log_entry, LogCategory
from requests import request
from types import SimpleNamespace
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from utils import get_stacktrace, randset
from sparkline import get_b64_linegraph

default_headers = {
    'User-Agent': f"Mozilla/5.0 ({randset('Windows NT 10.0; Win64;', 'PlayStation 4 3.11;', 'PlayStation; PlayStation 5/2.26;', 'Macintosh; Intel Mac OS X 10_11_2;')} x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{randset('101', '102', '103', '104', '105', '106', '107', '108')}.0.0.0 Safari/537.36 SomeBrowser/{random.randrange(100)}.0",
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'sec-ch-ua': '"Not=A?Brand";v="24"',
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

    ## Fetch the price
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
            cookies = {}
            if hasattr(rule, 'cookies'):
                cookies = rule.cookies.__dict__
            resp = request('GET', rule.url, headers=default_headers, cookies=cookies)

            if (resp.status_code >= 300):
                print(f"[{idx}] HTTP error: Status Code {resp.status_code}")
                add_log_entry(config, LogCategory.CAT_REQUESTS, f"Unsuccessful HTTP status {resp.status_code} for job [{rule.category}] {rule.name}.")
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
            add_log_entry(config, LogCategory.CAT_REQUESTS, f"Warning: No price found on page {rule.url} for [{rule.category}] {rule.name}.")
            return

        price = float(price) / 100.0 if hasattr(rule, 'divide') and rule.divide else float(price)

        print(f"[{idx}] Storing price: {price}")
        store_price(price, rule.name, rule.category, config)
        print(f"[{idx}] Done!")

    except Exception as ex:
        print(f"[{idx}] ERROR while processing: {ex}")
        add_log_entry(config, LogCategory.CAT_REQUESTS, f"Unhandled exception [{type(ex).__name__}] while processing request for [{rule.category}] {rule.name}.", get_stacktrace(ex))
        return

    ## Write Sparkline
    try:
        x, y = get_recent_prices(config, rule.name)
        if (len(y) > 1):
            if (y[0] < y[-1]):
                color = 'firebrick'
            elif (y[0] > y[-1]):
                color = 'limegreen'
            else: # equal
                color = 'gold'
            b64spark = get_b64_linegraph(x, y, color)
            store_sparkline(config, rule.name, b64spark)

    except Exception as ex:
        print(f"[{idx}] ERROR while sparklining: {ex}")
        add_log_entry(config, LogCategory.CAT_SPARKLINES, f"Unhandled exception [{type(ex).__name__}] while generating sparkline for [{rule.category}] {rule.name}.", get_stacktrace(ex))
        return

def sanitize_price(rawPrice: str) -> float:
    return float(re.sub(r"[^0-9.]", "", rawPrice))