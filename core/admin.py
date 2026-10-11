from django.contrib import admin
from django.db.models import Count, Max, Q
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from .dashboard import RESPONDED
from .models import Application, MetricSnapshot, Proof, ResumeVariant, RevisionNote, Skill


def freshness_color(value):
    return 'green' if value >= 0.6 else 'orange' if value >= 0.3 else 'red'


class NoteInline(TabularInline):
    model = RevisionNote
    extra = 0


class ProofInline(TabularInline):
    model = Proof.skills.through
    extra = 0
    verbose_name = 'proof'
    verbose_name_plural = 'proofs'
    autocomplete_fields = ('proof',)


@admin.register(Skill)
class SkillAdmin(ModelAdmin):
    list_display = ('name', 'category', 'level', 'freshness_badge', 'proof_total',
                    'last_activity_on', 'half_life_days')
    list_filter = ('category', 'level')
    search_fields = ('name', 'github_topics')
    inlines = [ProofInline, NoteInline]
    actions = ['mark_revised']
    fieldsets = (
        (None, {'fields': ('name', 'category', 'level')}),
        ('Freshness', {'fields': ('half_life_days', 'last_revised_at')}),
        ('GitHub sync', {'fields': ('github_topics',),
                         'description': 'Extra repo topics that prove this skill, comma-separated. '
                                        'The skill name already matches its own topic.'}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            last_proof=Max('proofs__occurred_at'), proof_count=Count('proofs', distinct=True))

    @admin.display(description='Freshness')
    def freshness_badge(self, obj):
        value = obj.freshness()
        return format_html('<b style="color:{}">{}</b>', freshness_color(value), value)

    @admin.display(description='Proofs', ordering='proof_count')
    def proof_total(self, obj):
        if not obj.proof_count:
            return format_html('<b style="color:red">{}</b>', 'none')
        return obj.proof_count

    @admin.display(description='Last activity')
    def last_activity_on(self, obj):
        last = obj.last_activity()
        return last.date() if last else '-'

    @admin.action(description='Mark selected skills as revised today')
    def mark_revised(self, request, queryset):
        updated = queryset.update(last_revised_at=timezone.now())
        self.message_user(request, f'Marked {updated} skill(s) revised.')


@admin.register(Proof)
class ProofAdmin(ModelAdmin):
    list_display = ('title', 'kind', 'metric', 'skill_names', 'occurred_at', 'link_ok')
    list_filter = ('kind', 'link_ok', 'skills')
    search_fields = ('title', 'metric', 'url')
    filter_horizontal = ('skills',)
    date_hierarchy = 'occurred_at'

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('skills')

    @admin.display(description='Skills')
    def skill_names(self, obj):
        return ', '.join(s.name for s in obj.skills.all()) or '-'


@admin.register(Application)
class ApplicationAdmin(ModelAdmin):
    list_display = ('company', 'role', 'variant', 'status', 'referral', 'applied_on')
    list_editable = ('status',)
    list_filter = ('status', 'variant', 'referral')
    list_select_related = ('variant',)
    search_fields = ('company', 'role', 'notes')
    date_hierarchy = 'applied_on'


@admin.register(ResumeVariant)
class ResumeVariantAdmin(ModelAdmin):
    list_display = ('name', 'headline', 'sent', 'responded')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            sent_n=Count('applications', filter=~Q(applications__status=Application.Status.SAVED)),
            responded_n=Count('applications', filter=Q(applications__status__in=RESPONDED)),
        )

    @admin.display(description='Sent', ordering='sent_n')
    def sent(self, obj):
        return obj.sent_n

    @admin.display(description='Responded', ordering='responded_n')
    def responded(self, obj):
        return obj.responded_n


@admin.register(MetricSnapshot)
class MetricSnapshotAdmin(ModelAdmin):
    list_display = ('week_start', 'applications', 'replies', 'interviews', 'referral_asks')
