import math

from django.db import models
from django.utils import timezone


class Skill(models.Model):
    class Level(models.IntegerChoices):
        LEARNING = 1, 'Learning'
        WORKING = 2, 'Working'
        STRONG = 3, 'Strong'
        EXPERT = 4, 'Expert'

    name = models.CharField(max_length=80, unique=True)
    category = models.CharField(max_length=40)  # backend, ai, data, frontend, devops
    level = models.IntegerField(choices=Level.choices, default=Level.WORKING)
    half_life_days = models.PositiveIntegerField(default=90)
    last_revised_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def latest_proof_date(self):
        proof = self.proofs.order_by('-occurred_at').first()
        return proof.occurred_at if proof else None

    def last_activity(self):
        # Querysets annotate last_proof to avoid one query per row (no N+1).
        proof = self.last_proof if hasattr(self, 'last_proof') else self.latest_proof_date()
        dates = [d for d in (self.last_revised_at, proof) if d]
        return max(dates) if dates else None

    def freshness(self):
        # 1.0 right after a revision or proof, halving every half_life_days.
        last = self.last_activity()
        if last is None:
            return 0.0
        days = (timezone.now() - last).days
        return round(math.exp(-math.log(2) * days / self.half_life_days), 2)


class Proof(models.Model):
    class Kind(models.TextChoices):
        REPO = 'repo', 'Repository'
        CASE = 'case', 'Case study'
        METRIC = 'metric', 'Metric'

    title = models.CharField(max_length=160)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    url = models.URLField(blank=True)
    metric = models.CharField(max_length=120, blank=True)  # e.g. 83% latency drop, 12s to 2s
    star_answer = models.TextField(blank=True)  # private interview answer draft
    occurred_at = models.DateTimeField(default=timezone.now)
    skills = models.ManyToManyField(Skill, related_name='proofs', blank=True)
    link_ok = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class RevisionNote(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='notes')
    body = models.TextField()
    mistake = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Note on {self.skill}'


class ResumeVariant(models.Model):
    name = models.CharField(max_length=60, unique=True)
    headline = models.CharField(max_length=160)

    def __str__(self):
        return self.name


class Application(models.Model):
    class Status(models.TextChoices):
        SAVED = 'saved', 'Saved'
        APPLIED = 'applied', 'Applied'
        REPLIED = 'replied', 'Replied'
        INTERVIEW = 'interview', 'Interview'
        OFFER = 'offer', 'Offer'
        REJECTED = 'rejected', 'Rejected'

    company = models.CharField(max_length=120)
    role = models.CharField(max_length=120)
    variant = models.ForeignKey(ResumeVariant, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SAVED)
    referral = models.BooleanField(default=False)
    applied_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'{self.company} - {self.role}'


class MetricSnapshot(models.Model):
    week_start = models.DateField(unique=True)
    applications = models.PositiveIntegerField(default=0)
    replies = models.PositiveIntegerField(default=0)
    interviews = models.PositiveIntegerField(default=0)
    referral_asks = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-week_start']

    def __str__(self):
        return f'Week of {self.week_start}'
