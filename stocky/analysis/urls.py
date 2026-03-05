from django.urls import path
from .views import (
    PriceGraphView,
    PERatioView,
    VolumePortfolioView,
    VolumeChartView,
    DiscountedValueView,
)

urlpatterns = [
    path('price-chart/', PriceGraphView.as_view()),
    path('pe-ratio/', PERatioView.as_view()),
    path('volume-portfolio/', VolumePortfolioView.as_view()),
    path('volume-chart/', VolumeChartView.as_view()),
    path('discounted-value/', DiscountedValueView.as_view()),
]