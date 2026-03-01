from rest_framework import serializers
from .models import Stock

class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = [
            'id', 'symbol', 'name', 'sector', 'portfolio',
            'current_price', 'pe_ratio', 'market_cap',
            'day_change', 'day_change_percent', 'volume',
            'high_52w', 'low_52w'
        ]
