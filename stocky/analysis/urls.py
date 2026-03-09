from django.urls import path
from .views import PortfolioListView, Stage1ClusterView, Stage2SubClusterView

urlpatterns = [
    path("portfolios/",  PortfolioListView.as_view(),    name="analysis-portfolios"),
    path("stage1/",      Stage1ClusterView.as_view(),    name="analysis-stage1"),
    path("stage2/",      Stage2SubClusterView.as_view(), name="analysis-stage2"),
]
