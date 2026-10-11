from django.contrib import admin
from django.db.models import Max
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from .models import Application, MetricSnapshot, Proof, ResumeVariant, RevisionNote, Skill


class NoteInline(TabularInline):
    model = RevisionNote
    extra = 0


@admin.register(Skill)
class SkillAdmin(ModelAdmin):
    list_display = ('name', 'category', 'level', 'freshness_badge')
    list_filter = ('category', 'level')
    search_fields = ('name',)
    inlines = [NoteInline]
    actions = ['mark_revised']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(last_proof=Max('proofs__occurred_at'))

    @admin.display(description='Freshness')
    def freshness_badge(self, obj):
        value = obj.freshness()
        color = 'green' if value >= 0.6 else 'orange' if value >= 0.3 else 'red'
        return format_html('<b style="color:{}">{}</b>', color, value)

    @admin.action(description='Mark selected skills as revised today')
    def mark_revised(self, request, queryset):
        queryset.update(last_revised_at=timezone.now())


@admin.register(Proof)
class ProofAdmin(ModelAdmin):
    list_display = ('title', 'kind', 'metric', 'occurred_at', 'link_ok')
    list_filter = ('kind', 'link_ok')
    search_fields = ('title', 'metric')
    filter_horizontal = ('skills',)


@admin.register(Application)
class ApplicationAdmin(ModelAdmin):
    list_display = ('company', 'role', 'variant', 'status', 'referral', 'applied_on')
    list_filter = ('status', 'variant', 'referral')
    search_fields = ('company', 'role')


admin.site.register(ResumeVariant, type('ResumeVariantAdmin', (ModelAdmin,), {}))
admin.site.register(MetricSnapshot, type('MetricSnapshotAdmin', (ModelAdmin,), {}))
