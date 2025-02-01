import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

import string

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    stocks = db.execute("SELECT symbol ,SUM(shares) as total_shares FROM transactions WHERE user_id=? GROUP BY symbol HAVING shares > 0",session["user_id"])
    cash = db.execute("SELECT cash FROM users WHERE id=?",session["user_id"])

    #print(cash[0]["cash"])
    total_money=cash[0]["cash"]
    for stock in stocks:
       quote=lookup(stock["symbol"])
       stock["name"]=quote["name"]
       stock["price"]=quote["price"]
       stock["value"]=stock["price"]*stock["total_shares"]
       total_money+=stock["value"]


    return render_template("index.html",stocks=stocks,cash=cash[0]["cash"],total_money=total_money)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    """Buy shares of stock"""
    if request.method =="POST":
        symbol = request.form.get('symbol')
        number = request.form.get('shares')
        quote =lookup(symbol)
        if not number.isdigit():
            return apology("number of shares must be digit",400)
        elif int(number)<1:
            return apology("number of stocks must be equal to or greater than 1",400)
        if quote == None:
            return apology("invalid symbol",400)
        else:
            price = quote['price']
            total_price = price * int(number)
            savings=db.execute("SELECT cash FROM users where id=?",session["user_id"])[0]["cash"]
            if total_price>savings:
                return apology("insufficient money :(",400)
            else:
                db.execute("UPDATE users set cash=cash-? where id=?",total_price,session["user_id"])
                db.execute("INSERT INTO transactions (user_id,symbol,shares,price) VALUES(?,?,?,?)",session["user_id"],symbol,number,price)
                flash(f"bought{number} shares of {symbol} for{usd(total_price)}")
                return redirect("/")

    else:
        return render_template('buy.html')#return apology("TODO")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions=db.execute("SELECT * FROM transactions WHERE user_id=?",session["user_id"])
    if transactions==None:
        return apology("no past transactions oucred",400)

    return render_template('/history.html',transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol =request.form.get("symbol")
        quote =lookup(symbol)

        if quote==None:
            return apology("invalid symbol ya man ana ta3ban",400)
        else:
            return render_template('quote.html',quote=quote)
    else:
        return render_template('quote.html')#apology("TODO")


@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()
    """Register user"""
    if request.method == "POST":
                # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)
        # checks if the confirmation was inputed
        elif not request.form.get("confirmation"):
            return apology("must provide password confirmation", 400)

        name = request.form.get("username")
        password=generate_password_hash(request.form.get("password"))


        #checks if password and confirmation match
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("password and confirmation must match", 400)
        #checks if there is a dublicant
        rows = db.execute("SELECT * FROM users WHERE username = ?",name)
        if len(rows) != 0:
            return apology("username already exist", 400)

        db.execute("INSERT INTO users (username,hash) VALUES(?,?)",name,password)
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    else:
        return render_template('register.html')
    #return apology("TODO")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    stock_symbols=db.execute("SELECT symbol,SUM(shares) as total_shares FROM transactions WHERE user_id=? GROUP BY symbol HAVING shares > 0",session["user_id"])
    number_owend=0
    if request.method == "POST":
        if not request.form.get("shares"):
            return apology("must type in a digit number of shares ",400)
        elif not request.form.get("symbol") and not request.form.get("shares").isdigit():
            return apology("must chosse symbol and type an integer for number of shares",400)

        symbol = request.form.get("symbol")
        quote=lookup(symbol)
        if quote==None:
            return apology("symbol invalid",400)

        price=quote["price"]
        try:
            number_shares = int(request.form.get("shares"))
        except:
            return apology("number must be integer",400)


        for stock_symbol in stock_symbols:
            if stock_symbol["symbol"]==symbol:
                number_owend = stock_symbol["total_shares"]

            #print(number_owend)
            #print(stock_symbol["symbol"])

        if number_shares<1:
            return apology(" that not a valid number of shares to sell you must sell 1 or more",400)

        elif number_shares >number_owend:
            return apology("you dont have enough shares try with a smaller number ",400)
        sale=number_shares*price
        db.execute("UPDATE users SET cash=cash+? WHERE ID=?",sale,session["user_id"])

        db.execute("INSERT INTO transactions (user_id,symbol,shares,price) VALUES(?,?,?,?)",session["user_id"],symbol,-number_shares,price)

        return redirect("/")
    else:
        return render_template("sell.html",stock_symbols=stock_symbols)
