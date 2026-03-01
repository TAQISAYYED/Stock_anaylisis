from django.shortcuts import render

# Create your views here.
# analysis/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from stocks.models import Stock


class OpportunityAPIView(APIView):
    def get(self, request, stock_id):

        stock = Stock.objects.get(id=stock_id)

        score = 0

        if stock.pe_ratio and stock.pe_ratio < 25:
            score += 1

        if stock.revenue_growth and stock.revenue_growth > 0.1:
            score += 1

        if score >= 2:
            opportunity = "Good Opportunity"
        else:
            opportunity = "Risky / Average"

        return Response({
            "ticker": stock.ticker,
            "pe_ratio": stock.pe_ratio,
            "revenue_growth": stock.revenue_growth,
            "opportunity": opportunity
        })