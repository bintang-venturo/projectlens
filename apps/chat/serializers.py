from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    question = serializers.CharField(min_length=1)
    session_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class CitationSerializer(serializers.Serializer):
    source = serializers.CharField()
    page = serializers.IntegerField()


class ChatResponseSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    answer = serializers.CharField()
    citations = CitationSerializer(many=True)
