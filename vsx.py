import os

import sqlite3
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, tableSetup, lookupPrice

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure sqlite3 Library to use SQLite database
conn = sqlite3.connect("finance.db", check_same_thread=False)
db = conn.cursor()
tableSetup(db)

# Make sure API key is set
if not os.environ.get("IEX_API_KEY"):
    raise RuntimeError("API KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    return apology("TODO")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == 'POST':
        shares = request.form.get("shares")
        stock = request.form.get("symbol")
        if not shares or not shares.isnumeric() or int(shares) <= 0:
            flash("Please input valid number of shares")
            return render_template("buy.html")
        if not stock:
            flash("Please input stock to purchase")
            return render_template("buy.html")
    
        price = lookupPrice(stock)
        if not price:
            flash("Please input valid stock to purchase")
            return render_template("buy.html")

        # Make change to Capital
        db.execute("SELECT cash FROM users WHERE id=?", (session["user_id"],))
        row = db.fetchone()
        cash = row[0]
        if cash < (int(shares)*float(price)):
            flash("You're broke fam")
            return render_template("buy.html")
            
        db.execute("UPDATE users SET cash =? WHERE id=?", (cash - int(shares)*float(price) ,session["user_id"]))
        # Record transaction
        db.execute("INSERT INTO transactions (stock_price, stock_symbol, transaction_time,shares,transaction_type,id) VALUES (?, ?, datetime('now'), ?, ?, ?)",
                    (price, stock.upper(), int(shares), "buy", session["user_id"]))      
        # Record change in Assets
        db.execute("SELECT * FROM assets WHERE stock_symbol=?", (stock.upper(),))
        row = db.fetchone()
        if not row:
            db.execute("INSERT INTO assets (stock_symbol, shares, id) VALUES (?, ?, ?)", (stock.upper(), int(shares), session["user_id"]))
        else:
            db.execute("UPDATE assets SET shares=? WHERE id=? AND stock_symbol=?", (row[1] + int(shares), session["user_id"], stock.upper()))
        conn.commit()

        flash(shares + " shares of " + stock.upper() + " purchased!")
        return render_template("buy.html")
    else:
        return render_template("buy.html")
    

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    db.execute("SELECT * FROM transactions WHERE id=?", (session["user_id"],))
    rows = db.fetchall()
    return render_template("history.html", transactions=rows)


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
        db.execute("SELECT * FROM users WHERE username = ?",(request.form.get("username"),))
        row = db.fetchone()

        # Ensure username exists and password is correct
        if row == None or row[1] != request.form.get("username") or not check_password_hash(row[2], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = row[0]

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
    if request.method == 'GET':
        return render_template("quote.html")
    else:
        quote = lookup(request.form.get("symbol"))
        if quote:
            return render_template("quoted.html", quote=quote)
        else:
            flash("Invalid Symbol")
            return render_template("quote.html")
        


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            flash("Must Provide Username")
            return render_template("register.html")
            # return apology("must provide username", 403)
        else:
            db.execute("SELECT * FROM users WHERE username = ?", (username,))
            rows = db.fetchone()
            if(rows != None):
                flash("Username Exists")
                return render_template("register.html")

        if not password:
            flash("Must Provide Password")
            return render_template("register.html")
        elif not request.form.get("confirm-password"):
            flash("Must Confirm Password")
            return render_template("register.html")
        elif(password != request.form.get('confirm-password')):
            flash("Passwords Do Not Match")
            return render_template("register.html")
        else:
            args = (request.form.get("username"), generate_password_hash(password))
            db.execute("INSERT INTO users (username,hash) VALUES (?,?);", args)
            session["user_id"] = db.lastrowid
            conn.commit()
            return redirect("/")    
    else:
        return render_template('register.html')



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        db.execute("SELECT stock_symbol FROM assets WHERE id=?", (session["user_id"],))
        stocks = db.fetchall()

        symbol = request.form.get("stock")
        shares = request.form.get("shares")
        db.execute("SELECT shares FROM assets WHERE id=? AND stock_symbol =?", (session["user_id"], symbol))
        userShares = db.fetchone()
        if userShares[0] < int(shares):
            flash("Not enough shares to sell")
            return render_template("sell.html", stocks=stocks)
        
        price = lookupPrice(symbol)
        # Make change to Capital
        db.execute("SELECT cash FROM users WHERE id=?", (session["user_id"],))
        row = db.fetchone()
        cash = row[0]            
        db.execute("UPDATE users SET cash =? WHERE id=?", (cash + int(shares)*float(price) ,session["user_id"]))
        # Record transaction
        db.execute("INSERT INTO transactions (stock_price, stock_symbol, transaction_time,shares,transaction_type,id) VALUES (?, ?, datetime('now'), ?, ?, ?)",
                    (price, symbol.upper(), int(shares), "sell", session["user_id"]))      
        # Record change in Assets
        db.execute("UPDATE assets SET shares=? WHERE id=? AND stock_symbol=?", (int(userShares[0]) - int(shares), session["user_id"], symbol.upper()))
        conn.commit()
        flash(shares + " shares of " + symbol + " sold!")
        return render_template("sell.html", stocks=stocks)
    else:
        db.execute("SELECT stock_symbol FROM assets WHERE id=?", (session["user_id"],))
        stocks = db.fetchall()
        return render_template("sell.html", stocks=stocks)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)