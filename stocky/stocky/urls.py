from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication
    path('api/accounts/', include('accounts.urls')),
    path('api/login/', TokenObtainPairView.as_view()),
    path('api/refresh/', TokenRefreshView.as_view()),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Apps
    path('api/portfolio/', include('portfolio.urls')),
    path('api/stocks/', include('stocks.urls')),
    path('api/analysis/', include('analysis.urls')),
    path('api/goldsilver/', include('goldsilver.urls')),
    path('api/Forecasting/',include('Forecasting.urls'))
]