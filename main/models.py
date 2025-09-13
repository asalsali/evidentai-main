from django.db import models


class Report(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Uploaded assets
    original_video = models.FileField(upload_to='videos/')
    extracted_audio = models.FileField(upload_to='audio/', blank=True, null=True)

    # Processing state
    status = models.CharField(max_length=32, default='pending')
    status_message = models.TextField(blank=True, default='')

    # Outputs
    transcript_text = models.TextField(blank=True, default='')
    image_findings_json = models.JSONField(blank=True, null=True)
    summarized_report = models.TextField(blank=True, default='')

    def __str__(self) -> str:
        return f"Report #{self.id} - {self.status}"

    @property
    def progress_percent(self) -> int:
        mapping = {
            'pending': 0,
            'extracting': 20,
            'transcribing': 40,
            'analyzing_images': 60,
            'summarizing': 80,
            'completed': 100,
            'failed': 0,
        }
        return mapping.get(self.status, 0)


# Create your models here.
