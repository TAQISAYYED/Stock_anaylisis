from rest_framework import serializers
from .models import Portfolio

class PortfolioSerializer(serializers.ModelSerializer):
    stock_count = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = ['id', 'name', 'description', 'icon', 'stock_count']

    def get_stock_count(self, obj):
        return obj.stocks.count()
