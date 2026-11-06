import yfinance as yf
import pandas as pd
import math

import pandas as pd
import math
from datetime import datetime, timedelta, timezone, date


def get_statement_value(statement, period, metric):
    if statement.empty:
        return None

    if period not in statement.columns:
        return None

    if metric not in statement.index:
        return None

    value = statement.loc[metric, period]

    if pd.isna(value):
        return None

    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None

def get_company_tickers(company_name):
    results = yf.Search(company_name, max_results=5)
    return [
        {
            "name": company.get("shortname"),
            "ticker": company.get("symbol"),
            "exchange": company.get("exchange"),
        }
        for company in results.quotes
    ]

def get_price_metrics(closing_prices, days):
    if  closing_prices.empty or not isinstance(days, int) or days <= 0:
        return None
    
    target_date = closing_prices.index[-1] - pd.Timedelta(days=days)
    previous_prices = closing_prices.loc[:target_date]
    
    if previous_prices.empty:
        return None
    
    historical_price = previous_prices.iloc[-1]

    if historical_price <= 0:
        return None
    
    return float(((closing_prices.iloc[-1] - historical_price) / historical_price) * 100)

def get_fundamentals(info):
    return  {
        "marketCap": info.get("marketCap"),
        "revenueGrowth": info.get("revenueGrowth"),
        "profitMargins": info.get("profitMargins"),
        "totalDebt": info.get("totalDebt"),
        "freeCashflow": info.get("freeCashflow"),
        "trailingPE": info.get("trailingPE")
    }

def get_financial_statements(stock):
    income_statement = stock.quarterly_income_stmt
    income_statement = income_statement.sort_index(axis=1, ascending=False).iloc[:, :3]
    debt_statement = stock.quarterly_balance_sheet
    debt_statement = debt_statement.sort_index(axis=1, ascending=False).iloc[:, :3]
    cash_flow_statement = stock.quarterly_cashflow
    cash_flow_statement = cash_flow_statement.sort_index(axis=1, ascending=False).iloc[:, :3]

    summary = []
    for period in list(income_statement.columns):
        total_revenue = get_statement_value(income_statement, period, 'Total Revenue')
        net_income = get_statement_value(income_statement, period,'Net Income')
        total_debt =  get_statement_value(debt_statement, period, 'Total Debt')
        operatingCashFlow = get_statement_value(cash_flow_statement, period, 'Operating Cash Flow')
        info = {
            "period": period.strftime("%Y-%m-%d"),
            "totalRevenue": total_revenue,
            "netIncome": net_income,
            "totalDebt": total_debt,
            "operatingCashFlow": operatingCashFlow
        }

        summary.append(info)

    return summary

def get_earnings_risk(stock):
    calendar = stock.calendar
    earnings_dates = calendar.get("Earnings Date", [])
    today = date.today()

    if not earnings_dates:
        return None
    
    closest_days = None
    closest_date = None

    for earnings_date in earnings_dates:
        days_until_earnings = (earnings_date - today).days
        if days_until_earnings >= 0 and (
    closest_days is None or days_until_earnings < closest_days):
            closest_date = earnings_date
            closest_days = days_until_earnings

    return {
    "nextEarningsDate": closest_date.isoformat(),
    "daysUntilEarnings": closest_days,
    "earningsWithin30Days": 0 <= closest_days <= 30,
    "dateStatus": "unverified"
}

from datetime import datetime, timedelta, timezone


def get_recent_news(stock, limit=5):
    try:
        news = stock.get_news(count=20)
    except Exception as error:
        return {"articles": [], "error": str(error)}

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    articles = []

    for item in news:
        content = item.get("content") or {}

        title = content.get("title")
        published = content.get("pubDate")

        if not title or not published:
            continue

        try:
            published_date = datetime.fromisoformat(
                published.replace("Z", "+00:00")
            )
            if published_date.tzinfo is None:
                published_date = published_date.replace(
                    tzinfo=timezone.utc
                )
        except (ValueError, AttributeError):
            continue

        if not cutoff <= published_date <= datetime.now(timezone.utc):
            continue

        provider = content.get("provider") or {}
        url_data = (
            content.get("canonicalUrl")
            or content.get("clickThroughUrl")
            or {}
        )

        articles.append({
            "title": title,
            "publisher": provider.get("displayName"),
            "publishedAt": published_date.isoformat(),
            "url": url_data.get("url"),
            "summary": (content.get("summary") or "")[:300],
        })

        if len(articles) >= limit:
            break

    return {"articles": articles, "error": None}

import yfinance as yf


def get_market_context():
    result = {
        "sp500Return30dPct": None,
        "sp500AsOf": None,
        "vixLevel": None,
        "vixAsOf": None,
        "errors": [],
    }

    try:
        sp500 = yf.Ticker("^GSPC").history(period="3mo")

        if not sp500.empty:
            closing_prices = sp500["Close"].dropna()

            result["sp500Return30dPct"] = get_price_metrics(
                closing_prices, 30
            )
            result["sp500AsOf"] = (
                closing_prices.index[-1].date().isoformat()
            )
        else:
            result["errors"].append("S&P 500 data unavailable")

    except Exception as error:
        result["errors"].append(f"S&P 500: {error}")

    try:
        vix = yf.Ticker("^VIX").history(period="5d")

        if not vix.empty:
            closing_prices = vix["Close"].dropna()

            result["vixLevel"] = float(closing_prices.iloc[-1])
            result["vixAsOf"] = (
                closing_prices.index[-1].date().isoformat()
            )
        else:
            result["errors"].append("VIX data unavailable")

    except Exception as error:
        result["errors"].append(f"VIX: {error}")

    return result

import yfinance as yf


def analyze_stock(symbol):
    symbol = symbol.strip().upper()
    stock = yf.Ticker(symbol)

    try:
        history = stock.history(period="3mo", auto_adjust=True)

        if history.empty or "Close" not in history:
            return {"symbol": symbol, "error": "No price data available"}

        closing_prices = history["Close"].dropna()

        if closing_prices.empty:
            return {"symbol": symbol, "error": "No valid closing prices"}

    except Exception as error:
        return {"symbol": symbol, "error": str(error)}

    analysis = {
        "symbol": symbol,
        "asOf": closing_prices.index[-1].date().isoformat(),
        "priceMetrics": {
            "latestClose": float(closing_prices.iloc[-1]),
            "return7dPct": get_price_metrics(closing_prices, 7),
            "return30dPct": get_price_metrics(closing_prices, 30),
        },
        "fundamentals": None,
        "financialStatements": None,
        "earningsRisk": None,
        "recentNews": None,
        "marketContext": None,
        "errors": {},
    }

    try:
        analysis["fundamentals"] = get_fundamentals(stock.info)
    except Exception as error:
        analysis["errors"]["fundamentals"] = str(error)

    try:
        analysis["financialStatements"] = get_financial_statements(stock)
    except Exception as error:
        analysis["errors"]["financialStatements"] = str(error)

    try:
        analysis["earningsRisk"] = get_earnings_risk(stock)
    except Exception as error:
        analysis["errors"]["earningsRisk"] = str(error)

    try:
        analysis["recentNews"] = get_recent_news(stock)
    except Exception as error:
        analysis["errors"]["recentNews"] = str(error)

    try:
        analysis["marketContext"] = get_market_context()
    except Exception as error:
        analysis["errors"]["marketContext"] = str(error)

    return analysis

if __name__ == "__main__":
    import json

    result = analyze_stock("AAPL")
    print(json.dumps(result, indent=2, allow_nan=False))