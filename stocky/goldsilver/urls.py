from django.urls import path
from .views import GoldSilverAnalysisView

urlpatterns = [
    path('analysis/', GoldSilverAnalysisView.as_view()),
]