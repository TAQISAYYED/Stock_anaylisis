from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Stock
from .serializers import StockSerializer


class StockViewSet(viewsets.ModelViewSet):
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Stock.objects.filter(portfolio__user=self.request.user)
        portfolio_id = self.request.query_params.get("portfolio")
        if portfolio_id:
            queryset = queryset.filter(portfolio_id=portfolio_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        GET /api/stocks/summary/?portfolio=1
        Returns all stocks with live data + highest/lowest price in portfolio.
        """
        portfolio_id = request.query_params.get("portfolio")
        if not portfolio_id:
            return Response(
                {"error": "portfolio query param is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        stocks = Stock.objects.filter(
            portfolio__user=request.user,
            portfolio_id=portfolio_id
        )

        if not stocks.exists():
            return Response({
                "total_stocks":  0,
                "highest_price": None,
                "lowest_price":  None,
                "stocks":        [],
            })

        serialized = StockSerializer(stocks, many=True).data

        # portfolio-level highest / lowest
        priced = [
            (s["current_price"], s["ticker"])
            for s in serialized
            if s["current_price"] is not None
        ]

        highest = {"value": max(priced, key=lambda x: x[0])[0], "ticker": max(priced, key=lambda x: x[0])[1]} if priced else None
        lowest  = {"value": min(priced, key=lambda x: x[0])[0], "ticker": min(priced, key=lambda x: x[0])[1]} if priced else None

        return Response({
            "total_stocks":  stocks.count(),
            "highest_price": highest,
            "lowest_price":  lowest,
            "stocks":        serialized,
        })