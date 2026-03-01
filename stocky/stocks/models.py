from django.db import models

class Stock(models.Model):
    symbol = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    sector = models.CharField(max_length=100)
    portfolio = models.ForeignKey('portfolio.Portfolio', on_delete=models.CASCADE, related_name='stocks')
    current_price = models.FloatField(default=0)
    pe_ratio = models.FloatField(null=True)
    market_cap = models.FloatField(default=0)
    day_change = models.FloatField(default=0)
    day_change_percent = models.FloatField(default=0)
    volume = models.BigIntegerField(default=0)
    high_52w = models.FloatField(default=0)
    low_52w = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
