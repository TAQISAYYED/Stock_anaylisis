from rest_framework import serializers
from .models import Portfolio
from stocks.models import Stock
from stocks.serializers import StockSerializer


class PortfolioSerializer(serializers.ModelSerializer):
    stocks = StockSerializer(many=True, read_only=True)

    class Meta:
        model = Portfolio
        fields = ["id", "name", "created_at", "stocks"]
        read_only_fields = ["user", "created_at"]