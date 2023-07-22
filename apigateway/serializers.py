from rest_framework import serializers
from .models import Upstream


class UpstreamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Upstream
        fields = ("scheme", "host", "port", "alias", "full_path")
