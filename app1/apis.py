#import matplotlib.pyplot as plt
#import numpy as np

import time
import traceback
import requests
from datetime import datetime
from django.http import JsonResponse, HttpResponse
from .models import users
from .mdate import getdate, today

from json import dumps

import requests
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@require_GET
def search(request, query):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query.replace(' ', '%20')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)  # ⏱ Short timeout
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return JsonResponse({"stocks": []})  # Fallback for failed request

    stocks = data.get("quotes", [])
    return JsonResponse({"stocks": stocks})

# Cache storage
_yahoo_cookie = None
_yahoo_crumb = None
_cache_timestamp = 0
CACHE_EXPIRY_SECONDS = 3600  # 1 hour


def get_yahoo_cookie_and_crumb():
    global _yahoo_cookie, _yahoo_crumb, _cache_timestamp

    current_time = time.time()
    if _yahoo_cookie and _yahoo_crumb and (current_time - _cache_timestamp) < CACHE_EXPIRY_SECONDS:
        return _yahoo_cookie, _yahoo_crumb

    # Step 1: Get cookie
    response_step1 = requests.get("https://fc.yahoo.com")
    cookie = response_step1.headers.get('Set-Cookie')

    # Step 2: Get crumb using that cookie
    headers_step2 = {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "Cookie": cookie
    }
    response_step2 = requests.get("https://query2.finance.yahoo.com/v1/test/getcrumb", headers=headers_step2)
    crumb = response_step2.text.strip()

    # Cache it
    _yahoo_cookie = cookie
    _yahoo_crumb = crumb
    _cache_timestamp = current_time

    return cookie, crumb


def fetch_yahoo_quotes(symbols):
    cookie, crumb = get_yahoo_cookie_and_crumb()
    url = (
        f"https://query1.finance.yahoo.com/v7/finance/quote"
        f"?symbols={symbols}&fields=currency,regularMarketPrice,"
        f"regularMarketChangePercent,marketState&crumb={crumb}&formatted=false"
    )

    headers = {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "Cookie": cookie
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        return []

    results = data.get("quoteResponse", {}).get("result", [])
    stocks = []
    for item in results:
        stocks.append({
            "symbol": item.get("symbol"),
            "price": round(item.get("regularMarketPrice", 0), 2),
            "change_percent": round(item.get("regularMarketChangePercent", 0), 5),
            "market_state": item.get("marketState"),
        })
    return stocks


def watchlist(request, query):
    stocks = fetch_yahoo_quotes(query)

    store = {"stocks": []}
    for stock in stocks:
        symbol = stock["symbol"]
        price = stock["price"]
        change_percent = stock["change_percent"]
        market_state = stock["market_state"]
        link = f"/removewatchlist/{symbol}"

        store["stocks"].append([symbol, price, change_percent, link, market_state])

    return JsonResponse(store)

def fetchdetails(request, query):
    url = f"https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{query}?merge=false&padTimeSeries=true&period1=1698240600&period2=1714055399&type=quarterlyMarketCap%2CtrailingMarketCap%2CquarterlyEnterpriseValue%2CtrailingEnterpriseValue%2CquarterlyPeRatio%2CtrailingPeRatio%2CquarterlyForwardPeRatio%2CtrailingForwardPeRatio%2CquarterlyPegRatio%2CtrailingPegRatio%2CquarterlyPsRatio%2CtrailingPsRatio%2CquarterlyPbRatio%2CtrailingPbRatio%2CquarterlyEnterprisesValueRevenueRatio%2CtrailingEnterprisesValueRevenueRatio%2CquarterlyEnterprisesValueEBITDARatio%2CtrailingEnterprisesValueEBITDARatio&lang=en-US&region=US"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    }
    response = requests.get(url, headers=headers)
    data = response.json()

    store = {}

    for i in data["timeseries"]["result"]:
        typ = i["meta"]["type"][0]
        store[typ] = i[typ][0]["reportedValue"]["fmt"]
    
    return JsonResponse(store)

def getdate(timestamp):
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")

def graphdata(request, query, start, end):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{query}?period1={start}&period2={end}&interval=5m&includePrePost=true&events=div%7Csplit%7Cearn&&lang=en-US&region=US"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    }

    try:
        response = requests.get(url, headers=headers)
        data = response.json()

        # Check for expected structure
        if (
            "chart" not in data
            or "result" not in data["chart"]
            or not data["chart"]["result"]
            or "timestamp" not in data["chart"]["result"][0]
            or "indicators" not in data["chart"]["result"][0]
            or "quote" not in data["chart"]["result"][0]["indicators"]
            or not data["chart"]["result"][0]["indicators"]["quote"]
            or "close" not in data["chart"]["result"][0]["indicators"]["quote"][0]
        ):
            return JsonResponse({"error": "Incomplete data received from Yahoo Finance API."}, status=500)

        timestamps = data["chart"]["result"][0]["timestamp"]
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]

        store = {"date": [], "close": []}

        for i in range(len(timestamps)):
            date_str = getdate(timestamps[i])
            try:
                close_value = round(closes[i], 2)
                store["date"].append(date_str)
                store["close"].append(close_value)
            except (TypeError, ValueError):
                continue

        store["currency"] = data["chart"]["result"][0]["meta"].get("currency", "USD")
        return JsonResponse(store)

    except Exception:
        return JsonResponse({"error": "Could not fetch or process data"}, status=500)

def portfolio(request):
    user = request.user
    stocks = user.stockbuy
    symbols = list(stocks.keys())

    stocksname = ",".join(symbols)

    import os

    # Use env variable if set, otherwise fallback to your deployed URL
    url = f"https://stalk-the-stock-django.onrender.com/api/watchlist/{stocksname}"

    headers = {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    }
    response = requests.get(url, headers=headers)
    data = response.json()

    market_data = {stock[0]: stock for stock in data.get("stocks", [])}

    store = []
    for symbol in symbols:
        user_stock = stocks[symbol]
        market = market_data.get(symbol, [symbol, 0, 0, "", ""])

        store.append({
            "symbol": symbol,
            "quantity": user_stock["quantity"],
            "boughtat": user_stock["boughtat"],
            "averageprice": user_stock["averageprice"],
            "currentprice": market[1],
            "percentchange": market[2]
        })

    return JsonResponse(store, safe=False)

def portfoliochart(request):
    user = request.user
    stocks = user.stockbuy
    price = []
    name = list(stocks.keys())
    for i in name:
        price.append(user.stockbuy[i]["boughtat"] * user.stockbuy[i]["quantity"])

    store = {"name": name, "price": price}
    return JsonResponse(store)

from django.http import HttpResponse
import requests

def income(request):
    user = request.user
    stocks = user.stockbuy  # Example: { 'AAPL': {'averageprice': 150, 'quantity': 5}, ... }
    symbols = list(stocks.keys())

    if not symbols:
        return HttpResponse(0)

    # Prepare the symbol string
    stocks_query = ",".join(reversed(symbols))
    print("Fetching data for symbols:", stocks_query)

    import os

    # Use environment variable or default to Render URL
    url = f"https://stalk-the-stock-django.onrender.com/api/watchlist/{stocks_query}"

    headers = {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print("❌ Failed to fetch or parse watchlist data:", e)
        return HttpResponse(0)

    try:
        # Map: symbol -> current price
        symbol_price_map = {item[0]: item[1] for item in data.get("stocks", [])}
        print("Current prices:", symbol_price_map)

        total_income = 0
        for symbol in symbols:
            if symbol not in symbol_price_map:
                print(f"⚠️ Missing data for symbol: {symbol}")
                continue

            avg_price = stocks[symbol]["averageprice"]
            quantity = stocks[symbol]["quantity"]
            current_price = symbol_price_map[symbol]

            income = (current_price - avg_price) * quantity  # Unrounded
            total_income += income

        return HttpResponse(round(total_income, 2))
    
    except Exception as e:
        print("❌ Error calculating income:", e)
        return HttpResponse(0)

def holdings(request, query):
    logedInUser = request.user
    stocks = logedInUser.stockbuy.keys()
    if query in list(stocks):
        quantity = logedInUser.stockbuy[query]["quantity"]
        return JsonResponse({"quantity": quantity})
    else:
        return JsonResponse({"quantity": 0})

def addtoWatchlist(request, query):
    logedInUser = request.user
    watchlist = logedInUser.watchlist

    if "symbol" not in watchlist:
        watchlist["symbol"] = []

    print("Watchlist before:", watchlist)
    print("Query:", query)

    if query in watchlist["symbol"]:
        print("Already Exists")
        return JsonResponse({"response": "Already Exists"})
    else:
        watchlist["symbol"].append(query)
        logedInUser.watchlist = watchlist
        logedInUser.save()
        return JsonResponse({"response": f"Added {query}"})
    
import requests
from django.http import JsonResponse

import finnhub
from django.http import JsonResponse

# Initialize Finnhub client once (put API key here)
finnhub_client = finnhub.Client(api_key="d1of599r01qjadrjodh0d1of599r01qjadrjodhg")

def fetch_market_status(request, symbol):
    try:
        # 1. Search symbols
        search_results = finnhub_client.symbol_lookup(symbol)
        print( "\n\n\n\n\n Search API response:", search_results , "\n\n\n" )  # Debug print
        results = search_results.get("result", [])
        if not results:
            raise ValueError("No data found for symbol")

        # Find best match
        matched = None
        for item in results:
            if item.get("symbol", "").upper() == symbol.upper() or item.get("displaySymbol", "").upper() == symbol.upper():
                matched = item
                break
        if not matched:
            matched = results[0]

        # 2. Get detailed profile for the matched symbol
        profile = finnhub_client.company_profile2(symbol=matched["symbol"])
        print("Company Profile API response:", profile)  # Debug print
        exchange_code = profile.get("exchange")
        if not exchange_code:
            raise ValueError("No exchange info found for symbol")

        # 3. Get market status for this exchange
        status = finnhub_client.market_status(exchange=exchange_code)
        print("Market Status API response:", status)  # Debug print

        return JsonResponse({
            "symbol": symbol,
            "exchange": exchange_code,
            "is_open": status.get("isOpen", False),
            "market_state": status.get("session", "CLOSED")
        })

    except Exception as e:
        print(f"Error fetching market status: {e}")
        return JsonResponse({
            "symbol": symbol,
            "exchange": None,
            "is_open": False,
            "market_state": "ERROR"
        })
    
def userbalance(request):
    user = request.user

    print ( "\n\n\n\n" , user.stockbuy , "\n\n\n\n" ) ; 

    return JsonResponse({'balance': user.balance  , 'stockbuy' : user.stockbuy }) ; 