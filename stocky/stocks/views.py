from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Stock
from .serializers import StockSerializer
import yfinance as yf


class StockListCreateView(APIView):

    def get(self, request):
        portfolio_id = request.query_params.get('portfolio')

        if portfolio_id:
            stocks = Stock.objects.filter(portfolio_id=portfolio_id)
        else:
            stocks = Stock.objects.all()

        serializer = StockSerializer(stocks, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = StockSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StockDetailView(APIView):

    def get(self, request, pk):
        stock = get_object_or_404(Stock, pk=pk)
        serializer = StockSerializer(stock)
        return Response(serializer.data)

    def put(self, request, pk):
        stock = get_object_or_404(Stock, pk=pk)
        serializer = StockSerializer(stock, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        stock = get_object_or_404(Stock, pk=pk)
        stock.delete()
        return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)