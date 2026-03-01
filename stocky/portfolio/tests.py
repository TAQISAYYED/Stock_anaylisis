from django.test import TestCase

# Create your tests here.
from rest_framework.routers import DefaultRouter
from .views import PortfolioViewSet

router = DefaultRouter()
router.register('', PortfolioViewSet, basename='portfolio')

urlpatterns = router.urls
