from django.db.models import Count, Max
from django.urls import include, path
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import routers, serializers, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .dashboard import funnel, summary, variant_funnel
from .models import Proof, Skill

# Public, read-only data that changes a few times a day: cache it briefly.
CACHE_SECONDS = 60


class SkillSerializer(serializers.ModelSerializer):
    freshness = serializers.SerializerMethodField()
    proof_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Skill
        fields = ['id', 'name', 'category', 'level', 'freshness', 'proof_count']

    def get_freshness(self, obj):
        return obj.freshness()


class ProofSerializer(serializers.ModelSerializer):
    skills = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    class Meta:
        model = Proof
        # star_answer is deliberately excluded: interview drafts stay private.
        fields = ['id', 'title', 'kind', 'url', 'metric', 'occurred_at', 'link_ok', 'skills']


class SkillViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SkillSerializer
    queryset = Skill.objects.annotate(
        last_proof=Max('proofs__occurred_at'),
        proof_count=Count('proofs', distinct=True),
    )


class ProofViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProofSerializer
    queryset = Proof.objects.prefetch_related('skills').order_by('-occurred_at')


@method_decorator(cache_page(CACHE_SECONDS), name='get')
class SummaryView(APIView):
    def get(self, request):
        return Response(summary())


@method_decorator(cache_page(CACHE_SECONDS), name='get')
class FunnelView(APIView):
    """Applications per stage, and reply rate per resume variant."""

    def get(self, request):
        return Response({'stages': funnel(), 'variants': variant_funnel()})


router = routers.DefaultRouter()
router.register('skills', SkillViewSet)
router.register('proofs', ProofViewSet)

urlpatterns = [
    path('summary/', SummaryView.as_view()),
    path('funnel/', FunnelView.as_view()),
    path('', include(router.urls)),
]
