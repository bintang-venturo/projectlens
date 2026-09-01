from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    question = serializers.CharField(min_length=1)


class CitationSerializer(serializers.Serializer):
    source = serializers.CharField()
    page = serializers.IntegerField()


class ChatResponseSerializer(serializers.Serializer):
    answer = serializers.CharField()
    citations = CitationSerializer(many=True)
