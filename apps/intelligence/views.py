from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.intelligence.models import ProjectAnalysis
from apps.intelligence.serializers import AnalysisDetailSerializer, AnalysisStatusSerializer
from apps.intelligence.tasks import run_project_analysis


class TriggerAnalysisView(APIView):

    def post(self, request):
        in_progress = ProjectAnalysis.objects.filter(
            status__in=[
                ProjectAnalysis.Status.PENDING,
                ProjectAnalysis.Status.PROCESSING,
            ]
        ).exists()
        if in_progress:
            return Response(
                {"error": "An analysis is already in progress."},
                status=status.HTTP_409_CONFLICT,
            )

        analysis = ProjectAnalysis.objects.create()
        run_project_analysis.delay(str(analysis.pk))

        serializer = AnalysisStatusSerializer(analysis)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


class AnalysisDetailView(APIView):

    def get(self, request, pk):
        try:
            analysis = ProjectAnalysis.objects.get(pk=pk)
        except ProjectAnalysis.DoesNotExist:
            return Response(
                {"error": "Analysis not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AnalysisDetailSerializer(analysis)
        return Response(serializer.data)


class LatestAnalysisView(APIView):

    def get(self, request):
        analysis = ProjectAnalysis.objects.first()
        if not analysis:
            return Response(
                {"error": "No analysis found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AnalysisDetailSerializer(analysis)
        return Response(serializer.data)
