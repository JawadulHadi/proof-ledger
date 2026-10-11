from django.db.models import Count, Max
from django.urls import include, path
from rest_framework import routers, serializers, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Application, Proof, Skill


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
        fields = ['id', 'title', 'kind', 'url', 'metric', 'occurred_at', 'skills']


class SkillViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SkillSerializer
    queryset = Skill.objects.annotate(
        last_proof=Max('proofs__occurred_at'),
        proof_count=Count('proofs', distinct=True),
    )


class ProofViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProofSerializer
    queryset = Proof.objects.prefetch_related('skills').order_by('-occurred_at')


class SummaryView(APIView):
    def get(self, request):
        return Response({
            'skills': Skill.objects.count(),
            'proofs': Proof.objects.count(),
            'applications': Application.objects.count(),
            'unproven_skills': Skill.objects.filter(proofs__isnull=True).count(),
        })


router = routers.DefaultRouter()
router.register('skills', SkillViewSet)
router.register('proofs', ProofViewSet)

urlpatterns = [path('summary/', SummaryView.as_view()), path('', include(router.urls))]
