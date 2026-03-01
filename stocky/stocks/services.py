import yfinance as yf

def update_stock_data(stock):
    ticker = yf.Ticker(stock.symbol)
    info = ticker.info
    stock.current_price = info.get('currentPrice', 0)
    stock.pe_ratio = info.get('trailingPE')
    stock.market_cap = info.get('marketCap', 0) / 10000000  # Convert to Cr
    stock.day_change = info.get('regularMarketChange', 0)
    stock.day_change_percent = info.get('regularMarketChangePercent', 0)
    stock.volume = info.get('regularMarketVolume', 0)
    stock.high_52w = info.get('fiftyTwoWeekHigh', 0)
    stock.low_52w = info.get('fiftyTwoWeekLow', 0)
    stock.save()
    return stock

def get_stock_analysis(stocks):
    results = []
    for stock in stocks:
        ticker = yf.Ticker(stock.symbol)
        info = ticker.info
        industry_pe = info.get('industryPe', stock.pe_ratio or 20)
        pe = stock.pe_ratio or 0
        score = max(0, min(100, int(100 - (pe / max(industry_pe, 1)) * 50)))
        results.append({
            'symbol': stock.symbol,
            'name': stock.name,
            'pe_ratio': pe,
            'industry_avg_pe': industry_pe,
            'opportunity_score': score,
            'recommendation': 'Buy' if pe < industry_pe * 0.8 else 'Sell' if pe > industry_pe * 1.3 else 'Hold'
        })
    return results
