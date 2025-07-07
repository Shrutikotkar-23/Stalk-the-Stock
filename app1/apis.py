import requests
from datetime import datetime
from django.http import JsonResponse,HttpResponse
from .models import users
from .mdate import getdate,today
from json import dumps


def search(request,query):
    query=query.replace(" ","%20")
    url="https://query2.finance.yahoo.com/v1/finance/search?q="+query
    headers={"User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"}

    response = requests.get(url,headers=headers)
    data = response.json()

    store={"stocks":[]}

    for i in data["quotes"]:
        store["stocks"].append(i)

    return JsonResponse(store)


def watchlist(request, query):

    response_step1 = requests.get("https://fc.yahoo.com")
    cookie = response_step1.headers.get('Set-Cookie')

    url_step2 = "https://query2.finance.yahoo.com/v1/test/getcrumb"
    headers_step2 = headers = {
            "User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
            "Cookie": cookie
        }  # Include obtained cookie in request headers

    response_step2 = requests.get(url_step2, headers=headers_step2)
    crumb = response_step2.text

    url = "https://query1.finance.yahoo.com/v7/finance/quote?&symbols=" + query + "&fields=currency,fromCurrency,toCurrency,exchangeTimezoneName,exchangeTimezoneShortName,gmtOffSetMilliseconds,regularMarketChange,regularMarketChangePercent,regularMarketPrice,regularMarketTime,preMarketTime,postMarketTime,extendedMarketTime&crumb="+crumb+"&formatted=false&region=US&lang=en-US"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "Cookie": cookie
    }

    response_step3 = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",'Cookie': cookie})

    cache = {'cookie': cookie, 'crumb': crumb}

    data=response_step3.json()
    store={"stocks":[]}
    
    for i in range(0,len(data["quoteResponse"]["result"])):
        symbol=data["quoteResponse"]["result"][i]["symbol"]
        link="/removewatchlist/"+symbol
        store["stocks"].append([symbol,round(data["quoteResponse"]["result"][i]["regularMarketPrice"],2),round(data["quoteResponse"]["result"][i]["regularMarketChangePercent"],5),link,data["quoteResponse"]["result"][i]["marketState"]])

    return JsonResponse(store)


def fetchdetails(request, query):
    url="https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/"+query+"?merge=false&padTimeSeries=true&period1=1698240600&period2=1714055399&type=quarterlyMarketCap%2CtrailingMarketCap%2CquarterlyEnterpriseValue%2CtrailingEnterpriseValue%2CquarterlyPeRatio%2CtrailingPeRatio%2CquarterlyForwardPeRatio%2CtrailingForwardPeRatio%2CquarterlyPegRatio%2CtrailingPegRatio%2CquarterlyPsRatio%2CtrailingPsRatio%2CquarterlyPbRatio%2CtrailingPbRatio%2CquarterlyEnterprisesValueRevenueRatio%2CtrailingEnterprisesValueRevenueRatio%2CquarterlyEnterprisesValueEBITDARatio%2CtrailingEnterprisesValueEBITDARatio&lang=en-US&region=US"
    headers={"User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"}
    response = requests.get(url,headers=headers)
    data = response.json()

    store={}

    for i in (data["timeseries"]["result"]):
        typ=i["meta"]["type"][0]
        store[typ]=i[typ][0]["reportedValue"]["fmt"]
    
    return JsonResponse(store)


def graphdata(request, query, start, end):
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{query}?period1={start}&period2={end}&interval=1d&includePrePost=true&events=div%7Csplit%7Cearn&&lang=en-US&region=US"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    }
    print(url)
    
    response = requests.get(url, headers=headers)
    data = response.json()

    store = {"date": [], "close": []}

    try:
        timestamps = data["chart"]["result"][0].get("timestamp", [])
        closes = data["chart"]["result"][0]["indicators"]["quote"][0].get("close", [])

        for i in range(len(timestamps)):
            store["date"].append(getdate(timestamps[i]))
            try:
                if closes[i] is not None:
                    store["close"].append(round(closes[i], 2))
            except:
                continue

        store["currency"] = data["chart"]["result"][0]["meta"].get("currency", "USD")
        return JsonResponse(store)

    except Exception as e:
        print("Error fetching chart data:", e)
        return JsonResponse({
            "date": [],
            "close": [],
            "currency": "USD",
            "error": f"Data not available for {query}"
        })


def portfoliochart(request):
    user = request.user

    stocks = user.stockbuy
    price = []
    name = []

    if isinstance(stocks, dict):
        for symbol, data in stocks.items():
            try:
                amount = data.get("boughtat", 0) * data.get("quantity", 0)
                if amount > 0:
                    name.append(symbol)
                    price.append(round(float(amount), 2))  # safely format to 2 decimals
            except Exception as e:
                print("Error for stock:", symbol, e)

    return JsonResponse({"name": name, "price": price})



def income(request):
    user = request.user

    stocks = user.stockbuy
    name = list(stocks.keys())

    if not name:
        return HttpResponse(0)

    # Build comma-separated symbol list (reversed order for visual matching)
    stocksname = ",".join(reversed(name))
    print("Stock symbols for income calculation:", stocksname)

    # Make internal API call
    url = f"http://127.0.0.1:8000/api/watchlist/{stocksname}"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print("Failed to fetch stock data:", response.status_code)
            return HttpResponse(0)
        data = response.json()
    except Exception as e:
        print("Error parsing JSON from watchlist API:", e)
        return HttpResponse(0)

    try:
        storepl = 0
        for i in range(len(name)):
            symbol = name[i]
            quantity = user.stockbuy[symbol]["quantity"]
            average_price = user.stockbuy[symbol]["averageprice"]
            current_price = data["stocks"][i][1]  # [symbol, current_price, change%, ...]

            invested = average_price * quantity
            current = current_price * quantity
            pl = current - invested
            storepl += round(pl, 2)

        return HttpResponse(round(storepl, 2))
    except Exception as e:
        print("Error calculating P/L:", e)
        return HttpResponse(0)


    return HttpResponse(0)

def holdings(request, query):
    logedInUser = request.user
    stocks = logedInUser.stockbuy

    quantity = stocks.get(query, {}).get("quantity", 0)

    return JsonResponse({
        "symbol": query,
        "quantity": quantity
    })
    

def addtoWatchlist(request, query):
    user = request.user
    watchlist = user.watchlist
    
    if query in watchlist["symbol"]:
        return JsonResponse({"response": "Already Exists", "watchlist": watchlist["symbol"]})
    else:
        watchlist["symbol"].append(query)
        user.save()
        # Return the full updated watchlist
        return JsonResponse({"response": "Added " + query, "watchlist": watchlist["symbol"]})


