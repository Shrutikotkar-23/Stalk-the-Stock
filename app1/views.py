from django.shortcuts import render,HttpResponse,redirect
from .models import users
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
import requests as req
from .mdate import today
from django.http import JsonResponse 
from django.contrib.auth.decorators import login_required
import yfinance as yf
import json

# Create your views here.
def home(request):
    return HttpResponse("Hello World!!")


def signup(request):
    data={"isusername":"hidden","isemail":"hidden"}
    return render(request,"login/signup.html",data)


def user_login(request):
    def checkusername(text):
        try:
            uname=users.objects.get(username=text)
            checkpword=uname.password
            return checkpword
        except:
            return 0
        
    if request.method == "POST":
        uname=request.POST.get("username")
        pword=request.POST.get("password")

        iscorrectpword=checkusername(uname)
    
        if(iscorrectpword==0):
            data={"isusername":"visible","ispasswordcorrect":"hidden"}
            return render(request,"login/login.html",data)
        else:
            if(iscorrectpword==pword):
                auth_login(request,users.objects.get(username=uname))
                return redirect("dashboard")
            else:
                data={"isusername":"hidden","ispasswordcorrect":"visible"}
                return render(request,"login/login.html",data)
    
    data={"isusername":"hidden","ispasswordcorrect":"hidden"}
    return render(request,"login/login.html",data)


def createuser(request):
    if request.method=="POST":
        uname=request.POST.get("username")
        fname=request.POST.get("first_name")
        lname=request.POST.get("last_name")
        mail=request.POST.get("email")
        pword=request.POST.get("password")

        # print(uname,fname,lname,mail,pword)

        def checkusername(text):
            user_count=users.objects.filter(username=text).count()
            return user_count
        
        def checkemail(text):
            email_count=users.objects.filter(email=text).count()
            return email_count
        
        ucount=checkusername(uname)
        ecount=checkemail(mail)
        
        if(ucount==1 and ecount==1):
            data={"isusername":"visible","isemail":"visible"}
            return render(request,"login/signup.html",data)

        if(ucount==1):
            data={"isusername":"visible","isemail":"hidden"}
            return render(request,"login/signup.html",data)
        elif(ecount==1):
            data={"isusername":"hidden","isemail":"visible"}
            return render(request,"login/signup.html",data)
        
        if(ucount==0 and ecount==0):
            adduser=users(username=uname,firstname=fname,lastname=lname,email=mail,password=pword,watchlist={"symbol":["SONY","MSFT","META","GOOG","AAPL"]})
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

        watchlistsymbols = ",".join(user.watchlist.get("symbol", []))

        data = {
            "username": user.username,
            "name": user.firstname,
            "email": user.email,
            "totalbalance": round(user.balance, 2),
            "watchlist": json.dumps(watchlistsymbols), 
            "stocklist": user.watchlist["symbol"],
            "stock": list(stockname),
            "price": price,
            "start": today() - 52000,
            "end": today(),
            "currentlyholding": "hidden",
        }


        return data
        print("Dashboard symbols:", user.watchlist["symbol"])




def dashboard(request):
    if request.user.is_authenticated:
        data = user_a(request)
        data["title"]="Dashboard"
        return render(request,"main/dashboard.html",data)
    else:
        return redirect("login")


def stockdetails(request,query):
    if request.user.is_authenticated:
        todayepoch=int(today())
        start=str(todayepoch-457199)
        end=str(todayepoch)
        url="https://query2.finance.yahoo.com/v8/finance/chart/"+query+"?period1="+str(todayepoch-457199)+"&period2="+str(todayepoch)+"&interval=5m&includePrePost=true&events=div%7Csplit%7Cearn&&lang=en-US&region=US"
        headers={"User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"}
        response = req.get(url,headers=headers)
        data = response.json()

        store={}
        data=data["chart"]["result"][0]["meta"]
        previousclose=data["previousClose"]

        for i in data.keys():
            if i == ("firstTradeDate") or i == ("regularMarketTime") or i == ("hasPrePostMarketData") or i == ("gmtoffset") or i == ("timezone") or i == ("instrumentType") or i == ("fullExchangeName") or i == ("regularMarketVolume") or i == ("previousClose") or i == ("regularMarketPrice"):
                continue
            if i == "scale":
                break
            store[i.capitalize()]=data[i]
            
        
        print("Yes")
        user=request.user        
        watchlistsymbols = ",".join(user.watchlist.get("symbol", []))


        data={
            "username":user.username,
            "name":user.firstname,
            "email":user.email,
            "totalbalance":round(user.balance,2),
            "watchlist": json.dumps(watchlistsymbols), 
            "data":store,
            "query":query,
            "previousclose":previousclose,
            "start":start,
            "end":end,
            "title":query,
        }
        return render(request,"main/details.html",data)
    else:
        return redirect("login")


def removewatchlist(request,symbol):

    user = request.user

    user.watchlist["symbol"].remove(symbol)

    user.save()
    return redirect("dashboard")


def updatestocks(request):
    if request.method == "POST":
        quantity=int(request.POST.get("quantity-input"))
        print(quantity)
        name=request.POST.get("symbolname")
        print(name)
        currentprice=float(request.POST.get("currentprice"))
        print(currentprice)
        if "buy" in request.POST:
            user = request.user

            if(quantity==0):
                return render(request,"main/error.html")
                # return redirect("Quantity Can not be 0")
            if(currentprice*quantity)>user.balance:
                return render(request,"main/error.html")
                # return HttpResponse("Not Sufficient Balance")
            if (name in user.stockbuy.keys()):
                previousprice=user.stockbuy[name]["quantity"]*user.stockbuy[name]["boughtat"]
                currentshareprice=quantity*currentprice
                totalquantity=int(user.stockbuy[name]["quantity"])+int(quantity)
                averageprice=(previousprice+currentshareprice)/totalquantity
                user.stockbuy[name]={"quantity":totalquantity, "boughtat":currentprice, "averageprice":averageprice,"purchaseat":"date" }
                user.balance=user.balance-float(quantity*currentprice)
            else:
            # user.stockbuy={}
                user.stockbuy[name]={"quantity": quantity ,"boughtat": currentprice, "averageprice": currentprice,"purchaseat":"date" }
                user.balance=user.balance-float(quantity*currentprice)
            user.save()
            print("Buy")
        if "sell" in request.POST:
            user=request.user

            if (name in user.stockbuy.keys()):
                if quantity > user.stockbuy[name]["quantity"]:
                    return render(request,"main/error.html")
                    # print("Not Enough Shares Holding")
                if user.stockbuy[name]["quantity"] == quantity:
                    print("Here")
                    user.stockbuy.pop(name)
                    user.balance=user.balance+(currentprice*quantity)
                    user.save()
                else:
                    user.stockbuy[name].update({"quantity":user.stockbuy[name]["quantity"]-quantity})
                    user.balance=user.balance+(currentprice*quantity)
                    user.save()
                    print("Sell")
            else:
                print("Quantity is 0")
            print("Sell")
    
        return(redirect('dashboard'))
    else:
        return render(request,"login/login.html")



def user_portfolio(request):

    if request.user.is_authenticated:
        user = request.user

        stockname=user.stockbuy.keys()
        stock=[]
        price=[]
        for i in stockname:
            stock.append(i)
            price.append(user.stockbuy[i]["boughtat"]*user.stockbuy[i]["quantity"])
        print("Yes")
        user=request.user
        print(user)
        print(user.watchlist)
        watchlistsymbols = ",".join(user.watchlist.get("symbol", []))

        # print(watchlistsymbols)
        data={
            "username":user.username,
            "name":user.firstname,
            "email":user.email,
            "totalbalance":round(user.balance,2),
            "watchlist": json.dumps(watchlistsymbols), 
            "stock":stock,
            "price":price,
            "start":today()-70000,
            "end":today(),
            "currentlyholding":"hidden",
        }
        return render(request,"main/portfolio.html",data)
    else:
        return redirect("login")

def errorpage(request):
    if request.user.is_authenticated:
        user = request.user

        stockname=user.stockbuy.keys()
        stock=[]
        price=[]
        for i in stockname:
            stock.append(i)
            price.append(user.stockbuy[i]["boughtat"]*user.stockbuy[i]["quantity"])
        print("Yes")
        user=request.user
        print(user)
        print(user.watchlist)
        watchlistsymbols = ",".join(user.watchlist.get("symbol", []))
        data={
            "username":user.username,
            "name":user.firstname,
            "email":user.email,
            "totalbalance":round(user.balance,2),
            "watchlist": json.dumps(watchlistsymbols), 
            "stock":stock,
            "price":price,
        }
        return render(request,"main/error.html",data)
    else:
        return redirect("login")


def settings(request):
    if request.user.is_authenticated:
        data = user_a(request)
        data["currentcheck"]="hidden"
        data["matchcheck"]="hidden"
        data["title"]="Settings"
        if request.method == "POST":
            currentPass=request.POST.get("currentpassword")
            newpass=request.POST.get("newpassword")
            repeatpass=request.POST.get("repeat-password")
            user = request.user

            print("---------------------------------------")
            print(user.password)
            if (user.password == currentPass):
                data["currentcheck"]="hidden"
                if(newpass == repeatpass):
                    data["matchcheck"]="hidden"
                    user.password = newpass
                    user.save()
                else:
                    print("Password Doesn't Match")
                    data["matchcheck"]="visible"
            else:
                data["currentcheck"]="visible"
                print("Password is Not Correct")
            print(currentPass)
            print(newpass)
            print(repeatpass)
    return render(request,"main/settings.html",data)


from datetime import datetime, timedelta

def portfolio_data(request):
    if request.user.is_authenticated:
        user = request.user
        portfolio = []

        print(f"Stock symbols for income calculation: {','.join(user.stockbuy.keys())}")

        for symbol, info in user.stockbuy.items():
            quantity = info.get("quantity", 0)
            average_price = round(info.get("averageprice", 0), 2)

            try:
                ticker = yf.Ticker(symbol)

                # Get the most recent data (use 1m if markets open, else 1d)
                hist = ticker.history(period="1d", interval="1m")  # Minute-level

                if hist.empty:
                    raise ValueError("No historical data")

                # Get last row's close value
                current_price = round(hist['Close'].iloc[-1], 2)
                change = round(current_price - average_price, 2)

                portfolio.append({
                    "symbol": [symbol],
                    "quantity": [quantity],
                    "averageprice": average_price,
                    "currentprice": current_price,
                    "change": change
                })

                print(f"✅ FINAL: {symbol} | Qty: {quantity} | Avg: {average_price} | Live: {current_price} | Δ: {change}")

            except Exception as e:
                print(f"❌ Error loading {symbol}: {e}")
                continue

        return JsonResponse(portfolio, safe=False)

    return JsonResponse({"error": "Unauthorized"}, status=401)


