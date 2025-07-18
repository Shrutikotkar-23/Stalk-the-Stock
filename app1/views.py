from django.http import JsonResponse
from django.shortcuts import render, HttpResponse, redirect
from .models import users
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
import requests as req
from .mdate import today

# Create your views here.
def home(request):
    return HttpResponse("Hello World!!")

def signup(request):
    data = {"isusername": "hidden", "isemail": "hidden"}
    return render(request, "login/signup.html", data)

def user_login(request):
    def checkusername(text):
        try:
            uname = users.objects.get(username=text)
            checkpword = uname.password
            return checkpword
        except:
            return 0

    if request.method == "POST":
        uname = request.POST.get("username")
        pword = request.POST.get("password")
        iscorrectpword = checkusername(uname)

        if iscorrectpword == 0:
            data = {"isusername": "visible", "ispasswordcorrect": "hidden"}
            return render(request, "login/login.html", data)
        else:
            if iscorrectpword == pword:
                auth_login(request, users.objects.get(username=uname))
                return redirect("dashboard")
            else:
                data = {"isusername": "hidden", "ispasswordcorrect": "visible"}
                return render(request, "login/login.html", data)

    data = {"isusername": "hidden", "ispasswordcorrect": "hidden"}
    return render(request, "login/login.html", data)

def createuser(request):
    if request.method == "POST":
        uname = request.POST.get("username")
        fname = request.POST.get("first_name")
        lname = request.POST.get("last_name")
        mail = request.POST.get("email")
        pword = request.POST.get("password")

        def checkusername(text):
            return users.objects.filter(username=text).count()

        def checkemail(text):
            return users.objects.filter(email=text).count()

        ucount = checkusername(uname)
        ecount = checkemail(mail)

        if ucount == 1 and ecount == 1:
            data = {"isusername": "visible", "isemail": "visible"}
            return render(request, "login/signup.html", data)
        if ucount == 1:
            data = {"isusername": "visible", "isemail": "hidden"}
            return render(request, "login/signup.html", data)
        elif ecount == 1:
            data = {"isusername": "hidden", "isemail": "visible"}
            return render(request, "login/signup.html", data)

        if ucount == 0 and ecount == 0:
            adduser = users(
                username=uname,
                firstname=fname,
                lastname=lname,
                email=mail,
                password=pword,
                watchlist={"symbol": ["SONY", "MSFT", "META", "GOOG", "AAPL"]}
            )
            adduser.save()
            return redirect("login")
    else:
        return redirect("login")

def logout(request):
    auth_logout(request)
    return HttpResponse("Logout!!")

def user_a(request):
    if request.user.is_authenticated:
        user = request.user
        stockname = user.stockbuy.keys()
        stock = []
        price = []
        for i in stockname:
            stock.append(i)
            price.append(user.stockbuy[i]["boughtat"] * user.stockbuy[i]["quantity"])
        watchlistsymbols = ",".join(user.watchlist["symbol"])
        data = {
            "username": user.username,
            "name": user.firstname,
            "email": user.email,
            "totalbalance": round(user.balance, 2),
            "watchlist": watchlistsymbols,
            "stocklist": user.watchlist["symbol"],
            "stock": list(stockname),
            "price": price,
            "start": today() - 52000,
            "end": today(),
            "currentlyholding": "hidden",
            "marketstatusclass" : "hidden",
        }
        return data

def dashboard(request):
    if request.user.is_authenticated:
        data = user_a(request)
        data["title"] = "Dashboard"
        return render(request, "main/dashboard.html", data)
    else:
        return redirect("login")

def stockdetails(request, query):
    if request.user.is_authenticated:
        todayepoch = int(today())
        start = str(todayepoch - 457199)
        end = str(todayepoch)
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{query}?period1={start}&period2={end}&interval=5m&includePrePost=true&events=div%7Csplit%7Cearn&&lang=en-US&region=US"
        headers = {
            "User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
        }
        response = req.get(url, headers=headers)
        data = response.json()
        store = {}
        data = data["chart"]["result"][0]["meta"]
        previousclose = data["previousClose"]

        for i in data.keys():
            if i in ("firstTradeDate", "regularMarketTime", "hasPrePostMarketData", "gmtoffset", "timezone", "instrumentType", "fullExchangeName", "regularMarketVolume", "previousClose", "regularMarketPrice"):
                continue
            if i == "scale":
                break
            store[i.capitalize()] = data[i]

        user = request.user
        watchlistsymbols = ",".join(user.watchlist["symbol"])
        data = {
            "username": user.username,
            "name": user.firstname,
            "email": user.email,
            "totalbalance": round(user.balance, 2),
            "watchlist": watchlistsymbols,
            "data": store,
            "query": query,
            "previousclose": previousclose,
            "start": start,
            "end": end,
            "title": query,
        }
        return render(request, "main/details.html", data)
    else:
        return redirect("login")

def removewatchlist(request, symbol):
    user = request.user
    watchlist_symbols = user.watchlist.get("symbol", [])

    if len(watchlist_symbols) > 1 and symbol in watchlist_symbols:
        watchlist_symbols.remove(symbol)
        user.watchlist["symbol"] = watchlist_symbols
        user.save()

    return redirect("dashboard")

def updatestocks(request):
    if request.method == "POST":
        quantity = int(request.POST.get("quantity-input"))
        name = request.POST.get("symbolname")
        currentprice = float(request.POST.get("currentprice"))
        user = request.user

        if "buy" in request.POST:
            if quantity == 0 or currentprice * quantity > user.balance:
                return render(request, "main/error.html")

            if name in user.stockbuy:
                previousprice = user.stockbuy[name]["quantity"] * user.stockbuy[name]["boughtat"]
                currentshareprice = quantity * currentprice
                totalquantity = user.stockbuy[name]["quantity"] + quantity
                averageprice = (previousprice + currentshareprice) / totalquantity
                user.stockbuy[name] = {
                    "quantity": totalquantity,
                    "boughtat": currentprice,
                    "averageprice": averageprice,
                    "purchaseat": "date"
                }
            else:
                user.stockbuy[name] = {
                    "quantity": quantity,
                    "boughtat": currentprice,
                    "averageprice": currentprice,
                    "purchaseat": "date"
                }
            user.balance -= quantity * currentprice
            user.save()

        if "sell" in request.POST:
            if name in user.stockbuy:
                if quantity > user.stockbuy[name]["quantity"]:
                    return render(request, "main/error.html")
                if user.stockbuy[name]["quantity"] == quantity:
                    user.stockbuy.pop(name)
                else:
                    user.stockbuy[name]["quantity"] -= quantity
                user.balance += quantity * currentprice
                user.save()

        return redirect("dashboard")
    else:
        return render(request, "login/login.html")

def user_portfolio(request):
    if request.user.is_authenticated:
        user = request.user
        stockname = user.stockbuy.keys()
        stock = []
        price = []
        for i in stockname:
            stock.append(i)
            price.append(user.stockbuy[i]["boughtat"] * user.stockbuy[i]["quantity"])
        watchlistsymbols = ",".join(user.watchlist["symbol"])
        data = {
            "username": user.username,
            "name": user.firstname,
            "email": user.email,
            "totalbalance": round(user.balance, 2),
            "watchlist": watchlistsymbols,
            "stock": stock,
            "price": price,
            "start": today() - 70000,
            "end": today(),
            "currentlyholding": "hidden",
            "marketstatusclass" : "hidden",

        }
        return render(request, "main/portfolio.html", data)
    else:
        return redirect("login")

def errorpage(request):
    if request.user.is_authenticated:
        user = request.user
        stockname = user.stockbuy.keys()
        stock = []
        price = []
        for i in stockname:
            stock.append(i)
            price.append(user.stockbuy[i]["boughtat"] * user.stockbuy[i]["quantity"])
        watchlistsymbols = ",".join(user.watchlist["symbol"])
        data = {
            "username": user.username,
            "name": user.firstname,
            "email": user.email,
            "totalbalance": round(user.balance, 2),
            "watchlist": watchlistsymbols,
            "stock": stock,
            "price": price,
        }
        return render(request, "main/error.html", data)
    else:
        return redirect("login")

def settings(request):
    if request.user.is_authenticated:
        data = user_a(request)
        data["currentcheck"] = "hidden"
        data["matchcheck"] = "hidden"
        data["title"] = "Settings"
        if request.method == "POST":
            currentPass = request.POST.get("currentpassword")
            newpass = request.POST.get("newpassword")
            repeatpass = request.POST.get("repeat-password")
            user = request.user
            if user.password == currentPass:
                if newpass == repeatpass:
                    data["matchcheck"] = "hidden"
                    user.password = newpass
                    user.save()
                else:
                    data["matchcheck"] = "visible"
            else:
                data["currentcheck"] = "visible"
    return render(request, "main/settings.html", data)

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from django.http import JsonResponse

from django.http import JsonResponse

def user_data_api(request):
    try:
        user = request.user
        
        # 1. Get watchlist symbols (from JSON array)
        watchlist_symbols = user.watchlist.get("symbol", []) if isinstance(user.watchlist, dict) else []
        
        # 2. Get stockbuy symbols (extract keys from JSON dict)
        stockbuy_symbols = list(user.stockbuy.keys()) if isinstance(user.stockbuy, dict) else []
        
        # 3. Merge and deduplicate (using Python set)
        unique_symbols = sorted(set(watchlist_symbols + stockbuy_symbols))
        
        # 4. Return only the merged unique symbols
        return JsonResponse({
            "symbols": unique_symbols  # Clean response with no duplicates
        })

    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        return JsonResponse({"error": str(e)}, status=500)