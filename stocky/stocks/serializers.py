from rest_framework import serializers
from .models import Stock
import yfinance as yf


class StockSerializer(serializers.ModelSerializer):
    current_price   = serializers.SerializerMethodField()
    pe_ratio        = serializers.SerializerMethodField()
    day_high        = serializers.SerializerMethodField()
    day_low         = serializers.SerializerMethodField()
    week_52_high    = serializers.SerializerMethodField()
    week_52_low     = serializers.SerializerMethodField()
    day_change_pct  = serializers.SerializerMethodField()
    market_cap      = serializers.SerializerMethodField()
    volume          = serializers.SerializerMethodField()
    dividend_yield  = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = [
            "id",
            "portfolio",
            "ticker",
            "company_name",
            "added_at",
            "current_price",
            "pe_ratio",
            "day_high",
            "day_low",
            "week_52_high",
            "week_52_low",
            "day_change_pct",
            "market_cap",
            "volume",
            "dividend_yield",
        ]

    def get_stock_info(self, obj):
        """Single yfinance call per stock, cached on the instance."""
        if not hasattr(obj, "_yf_cache"):
            try:
                obj._yf_cache = yf.Ticker(f"{obj.ticker.upper()}.NS").info
            except Exception:
                obj._yf_cache = {}
        return obj._yf_cache

    def get_current_price(self, obj):
        info = self.get_stock_info(obj)
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        return round(price, 2) if price else None

    def get_pe_ratio(self, obj):
        info = self.get_stock_info(obj)
        pe = info.get("trailingPE")
        return round(pe, 2) if pe else None

    def get_day_high(self, obj):
        info = self.get_stock_info(obj)
        val = info.get("dayHigh") or info.get("regularMarketDayHigh")
        return round(val, 2) if val else None

    def get_day_low(self, obj):
        info = self.get_stock_info(obj)
        val = info.get("dayLow") or info.get("regularMarketDayLow")
        return round(val, 2) if val else None

    def get_week_52_high(self, obj):
        info = self.get_stock_info(obj)
        val = info.get("fiftyTwoWeekHigh")
        return round(val, 2) if val else None

    def get_week_52_low(self, obj):
        info = self.get_stock_info(obj)
        val = info.get("fiftyTwoWeekLow")
        return round(val, 2) if val else None

    def get_day_change_pct(self, obj):
        info = self.get_stock_info(obj)
        val = info.get("regularMarketChangePercent")
        return round(val, 2) if val else None

    def get_market_cap(self, obj):
        info = self.get_stock_info(obj)
        return info.get("marketCap")

    def get_volume(self, obj):
        info = self.get_stock_info(obj)
        return info.get("regularMarketVolume") or info.get("volume")

    def get_dividend_yield(self, obj):
        info = self.get_stock_info(obj)
        val = info.get("dividendYield")
        return round(val * 100, 2) if val else None