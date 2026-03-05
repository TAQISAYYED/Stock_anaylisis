from django.db import models
from portfolio.models import Portfolio


class Stock(models.Model):
    portfolio        = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="stocks")

    # Identity
    ticker           = models.CharField(max_length=20)
    company_name     = models.CharField(max_length=255, blank=True)

    # Price data
    current_price    = models.FloatField(null=True, blank=True)
    day_high         = models.FloatField(null=True, blank=True)
    day_low          = models.FloatField(null=True, blank=True)
    day_change_pct   = models.FloatField(null=True, blank=True)

    # 52 week
    week_52_high     = models.FloatField(null=True, blank=True)
    week_52_low      = models.FloatField(null=True, blank=True)

    # Fundamentals
    pe_ratio         = models.FloatField(null=True, blank=True)
    market_cap       = models.BigIntegerField(null=True, blank=True)
    volume           = models.BigIntegerField(null=True, blank=True)
    dividend_yield   = models.FloatField(null=True, blank=True)

    # Metadata
    last_updated     = models.DateTimeField(auto_now=True)
    added_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("portfolio", "ticker")

    def __str__(self):
        return self.ticker