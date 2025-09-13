from django import forms
from .models import Report


class VideoUploadForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["original_video"]


