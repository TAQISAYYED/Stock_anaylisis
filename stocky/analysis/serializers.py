from rest_framework import serializers


class Stage1ResultSerializer(serializers.Serializer):
    ticker       = serializers.CharField()
    company_name = serializers.CharField(allow_null=True)
    pca_1        = serializers.FloatField()
    pca_2        = serializers.FloatField()
    cluster      = serializers.IntegerField()
    current_price= serializers.FloatField(allow_null=True)
    pe_ratio     = serializers.FloatField(allow_null=True)


class Stage2ResultSerializer(serializers.Serializer):
    ticker        = serializers.CharField()
    company_name  = serializers.CharField(allow_null=True)
    current_price = serializers.FloatField(allow_null=True)
    week_52_high  = serializers.FloatField(allow_null=True)
    week_52_low   = serializers.FloatField(allow_null=True)
    discount_pct  = serializers.FloatField()
    pe_ratio      = serializers.FloatField(allow_null=True)
    sub_cluster   = serializers.IntegerField()
    sub_label     = serializers.CharField()


class CentroidSerializer(serializers.Serializer):
    sub_cluster  = serializers.IntegerField()
    discount_pct = serializers.FloatField()
    pe_ratio     = serializers.FloatField()
    label        = serializers.CharField()
