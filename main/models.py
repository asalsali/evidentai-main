from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from cryptography.fernet import Fernet
import hashlib
import json


class OfficerWallet(models.Model):
    """XRPL wallet with XLS-70 credentials for law enforcement officers"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='officer_wallet'
    )
    
    # Wallet identification
    wallet_address = models.CharField(max_length=50, unique=True)
    encrypted_secret = models.TextField()  # Encrypted private key
    
    # XLS-70 Credential fields
    credential_id = models.CharField(max_length=100, blank=True, help_text="XLS-70 Credential ID")
    credential_data = models.JSONField(blank=True, null=True, help_text="Credential data from XRPL")
    credential_created_at = models.DateTimeField(null=True, blank=True, help_text="When credential was created")
    credential_accepted_at = models.DateTimeField(null=True, blank=True, help_text="When credential was accepted")
    
    # Status tracking
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.wallet_address}"
    
    def get_decrypted_secret(self):
        """Safely decrypt the wallet secret"""
        from django.conf import settings
        fernet = Fernet(settings.XRPL_ENCRYPTION_KEY)
        return fernet.decrypt(self.encrypted_secret.encode()).decode()
    
    @property
    def has_valid_credential(self):
        """Check if the officer has a valid XLS-70 credential"""
        if not self.credential_id or not self.credential_data:
            return False
        
        # Check if credential is expired
        expires_at = self.credential_data.get('expires_at')
        if expires_at:
            from datetime import datetime
            try:
                expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                return timezone.now() < expiry_date
            except:
                return False
        
        return True
    
    @property
    def credential_status(self):
        """Get human-readable credential status"""
        if not self.credential_id:
            return "No Credential"
        elif not self.credential_accepted_at:
            return "Pending Acceptance"
        elif self.has_valid_credential:
            return "Valid"
        else:
            return "Expired"


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

    # XRPL Digital Signature fields
    document_hash = models.CharField(max_length=64, blank=True, help_text="SHA-256 hash of the document content")
    signed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='signed_reports',
        help_text="Officer who digitally signed this report"
    )
    signed_at = models.DateTimeField(null=True, blank=True, help_text="When the document was digitally signed")
    signature_tx_hash = models.CharField(max_length=64, blank=True, help_text="XRPL transaction hash of the signature")
    signature_type = models.CharField(
        max_length=20,
        choices=[
            ('MOCK', 'Mock Signature (Testing)'),
            ('XLS70_CREDENTIAL', 'XLS-70 Credential Signature'),
            ('LEGACY', 'Legacy Transaction Memo'),
        ],
        default='MOCK',
        help_text="Type of digital signature used"
    )
    credential_id = models.CharField(max_length=100, blank=True, help_text="XLS-70 Credential ID used for signing")

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

    def generate_hash(self):
        """Generate hash of report content for signing"""
        content = {
            'id': self.id,
            'incident_type': self.incident_type,
            'officer_badge': self.officer_badge,
            'transcript': self.transcript_text,
            'summary': self.summarized_report,
            'created': self.created_at.isoformat(),
        }
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()


# Create your models here.
