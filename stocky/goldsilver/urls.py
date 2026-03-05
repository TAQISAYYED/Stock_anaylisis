from django.urls import path
from .views import GoldSilverAnalysisView

urlpatterns = [
    path('', GoldSilverAnalysisView.as_view()),
]