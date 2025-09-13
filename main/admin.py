from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "incident_type", "officer_badge", "incident_date", "status", "created_at")
    list_filter = ("status", "incident_type", "incident_date", "created_at")
    search_fields = ("id", "officer_badge", "incident_type", "status_message", "notes")
    readonly_fields = ("created_at", "updated_at", "progress_percent")
    fieldsets = (
        ("Case Information", {
            "fields": ("incident_date", "officer_badge", "incident_type", "notes")
        }),
        ("Evidence Files", {
            "fields": ("original_video", "extracted_audio")
        }),
        ("Processing Status", {
            "fields": ("status", "status_message", "progress_percent")
        }),
        ("AI Analysis Results", {
            "fields": ("transcript_text", "image_findings_json", "summarized_report")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

# Register your models here.
