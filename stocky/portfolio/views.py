from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Portfolio
from .serializers import PortfolioSerializer
from django.shortcuts import get_object_or_404


# GET (list) + POST (create)
class PortfolioListCreateView(APIView):

    def get(self, request):
        portfolios = Portfolio.objects.all()
        serializer = PortfolioSerializer(portfolios, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PortfolioSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# GET (single) + PUT + DELETE
class PortfolioDetailView(APIView):

    def get(self, request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk)
        serializer = PortfolioSerializer(portfolio)
        return Response(serializer.data)

    def put(self, request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk)
        serializer = PortfolioSerializer(portfolio, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk)
        portfolio.delete()
        return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)