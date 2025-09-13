from django import forms
from .models import Report


class VideoUploadForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["original_video", "incident_date", "officer_badge", "incident_type", "notes"]
        widgets = {
            'incident_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-gray-200'}),
            'officer_badge': forms.TextInput(attrs={'placeholder': 'e.g., 1234', 'class': 'w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-gray-200'}),
            'incident_type': forms.Select(attrs={'class': 'w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-gray-200'}),
            'notes': forms.Textarea(attrs={'placeholder': 'Brief description of the incident...', 'class': 'w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-gray-200 h-20', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['incident_date'].required = False
        self.fields['officer_badge'].required = False
        self.fields['incident_type'].required = False
        self.fields['notes'].required = False
        
        # Add empty option for incident_type
        self.fields['incident_type'].choices = [('', 'Select incident type...')] + list(self.fields['incident_type'].choices)[1:]


