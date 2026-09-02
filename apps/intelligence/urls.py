from django.urls import path

from apps.intelligence.views import AnalysisDetailView, LatestAnalysisView, TriggerAnalysisView

app_name = "intelligence"

urlpatterns = [
    path("analyze/", TriggerAnalysisView.as_view(), name="trigger"),
    path("analysis/latest/", LatestAnalysisView.as_view(), name="latest"),
    path("analysis/<uuid:pk>/", AnalysisDetailView.as_view(), name="detail"),
]
