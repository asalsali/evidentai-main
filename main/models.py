from django.db import models


class Report(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Uploaded assets
    original_video = models.FileField(upload_to='videos/')
    extracted_audio = models.FileField(upload_to='audio/', blank=True, null=True)

    # Police-specific fields
    incident_date = models.DateField(blank=True, null=True, help_text="Date of the incident")
    officer_badge = models.CharField(max_length=20, blank=True, help_text="Officer badge number")
    incident_type = models.CharField(
        max_length=50,
        choices=[
            ('traffic-stop', 'Traffic Stop'),
            ('domestic', 'Domestic Dispute'),
            ('theft', 'Theft/Burglary'),
            ('assault', 'Assault'),
            ('drug', 'Drug Related'),
            ('other', 'Other'),
        ],
        blank=True,
        help_text="Type of incident"
    )
    notes = models.TextField(blank=True, help_text="Additional incident notes")

    # Processing state
    status = models.CharField(max_length=32, default='pending')
    status_message = models.TextField(blank=True, default='')

    # Outputs
    transcript_text = models.TextField(blank=True, default='')
    image_findings_json = models.JSONField(blank=True, null=True)
    summarized_report = models.TextField(blank=True, default='')

    def __str__(self) -> str:
        return f"Case #{self.id} - {self.get_incident_type_display() or 'Unknown'} - {self.status}"

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
