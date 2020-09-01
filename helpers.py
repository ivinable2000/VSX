import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""
    # urllib.parse.quote_plus(symbol)
    # Contact API
    try:
        api_key = os.environ.get("IEX_API_KEY")
        response = requests.get(f"https://sandbox.iexapis.com/stable/stock/{symbol}/batch?types=quote&token={api_key}")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        batch = response.json()
        quotes = batch["quote"]
        res =  {
            "name": quotes["companyName"],
            "symbol": quotes["symbol"],
            "price": float(quotes["latestPrice"]),
            "change": float(quotes["change"]),
            "changePercent": quotes["changePercent"],
            "latestSource": quotes["latestSource"],
            "latestTime": quotes["latestTime"],
            "isUSMarketOpen": "Open" if quotes["isUSMarketOpen"] else "Close",
            "askPrice": float(quotes["iexAskPrice"]),
            "askSize": quotes["iexAskSize"],
            "bidPrice": float(quotes["iexBidPrice"]),
            "bidSize": quotes["iexBidSize"],
            "open": quotes["open"],
            "close": quotes["close"],
            "high": quotes["high"],
            "low": quotes["low"],
            "week52High": quotes["week52High"],
            "week52Low": quotes["week52Low"],
            "extendedPrice": quotes["extendedPrice"],
            "extendedChange": quotes["extendedChange"],
            "extendedChangePercent": quotes["extendedChangePercent"]
        }
        return res
    except (KeyError, TypeError, ValueError):
        return None

def lookupPrice(symbol):
    """Look up price for stock from symbol."""
    # Contact API
    try:
        api_key = os.environ.get("IEX_API_KEY")
        response = requests.get(f"https://sandbox.iexapis.com/stable/stock/{symbol}/price?token={api_key}")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        price = response.json()
        return price
    except (KeyError, TypeError, ValueError):
        return None

def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"

def tableSetup(db):
    """ Create necessary tables for db if it does not exist already """
    db.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
	    stock_price REAL NOT NULL,
        stock_symbol TEXT NOT NULL,
	    transaction_time TEXT NOT NULL,
	    shares INTEGER NOT NULL,
    	transaction_type TEXT NOT NULL,
	    transaction_id INTEGER PRIMARY KEY NOT NULL,
	    id INTEGER NOT NULL,
	    FOREIGN KEY(id)
		    REFERENCES users(id)
			    ON UPDATE CASCADE
			    ON DELETE CASCADE,
	    CHECK (shares > 0 AND
		    	stock_price >= 0)
    );""")
    db.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        stock_symbol TEXT NOT NULL,
	    shares INTEGER NOT NULL,
	    id INTEGER NOT NULL,
	    PRIMARY KEY (id, stock_symbol),
	    FOREIGN KEY(id)
		    REFERENCES users(id)
			    ON UPDATE CASCADE
			    ON DELETE CASCADE,
	    CHECK (shares > 0)
    ) WITHOUT ROWID;
    """)
