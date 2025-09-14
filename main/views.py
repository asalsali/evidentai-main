from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse, Http404, HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import VideoUploadForm
from .models import Report, OfficerWallet
from .xrpl_service import xrpl_service
import threading
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from io import BytesIO


def home(request):
    """Home page - shows login prompt for unauthenticated users, dashboard link for authenticated users"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')


def custom_login(request):
    """Custom login view to handle authentication"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        print(f"Login attempt: username='{username}', password length={len(password) if password else 0}")
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            print(f"Login successful for user: {user.username}")
            # Redirect to next page or dashboard
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            print(f"Login failed for username: {username}")
            messages.error(request, 'Invalid username or password. Please try again.')
    
    return render(request, 'auth/login.html')


def custom_logout(request):
    """Custom logout view to handle logout"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home')


@login_required
def dashboard(request):
    reports = Report.objects.order_by('-created_at')[:10]
    form = VideoUploadForm()
    return render(request, 'dashboard.html', {"form": form, "reports": reports})


def _process_report_background(report_id: int):
    from agents_sdk.evidence_processing_agents.manager import EvidenceProcessingManager
    manager = EvidenceProcessingManager()
    manager.process_report_sync(report_id)


@login_required
def upload_video(request):
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=True)
            messages.success(request, 'Video uploaded. Processing has started.')

            t = threading.Thread(target=_process_report_background, args=(report.id,))
            t.daemon = True
            t.start()

            return redirect(reverse('dashboard'))
        else:
            messages.error(request, 'Invalid upload. Please try again.')
    else:
        form = VideoUploadForm()
    return render(request, 'dashboard.html', {"form": form})


@login_required
def reports_all(request):
    reports = Report.objects.order_by('-created_at')
    return render(request, 'reports/list.html', {"title": "All Reports", "reports": reports})


@login_required
def reports_in_progress(request):
    reports = Report.objects.exclude(status__in=['completed', 'failed']).order_by('-created_at')
    return render(request, 'reports/list.html', {"title": "In Progress", "reports": reports})


@login_required
def reports_completed(request):
    reports = Report.objects.filter(status='completed').order_by('-created_at')
    return render(request, 'reports/list.html', {"title": "Completed", "reports": reports})


@login_required
def report_detail(request, pk: int):
    try:
        report = Report.objects.get(pk=pk)
    except Report.DoesNotExist as e:
        raise Http404 from e
    return render(request, 'reports/detail.html', {"report": report})


@login_required
def report_status_json(request, pk: int):
    try:
        report = Report.objects.get(pk=pk)
    except Report.DoesNotExist as e:
        raise Http404 from e
    return JsonResponse({
        "id": report.id,
        "status": report.status,
        "progress": report.progress_percent,
        "status_message": report.status_message,
    })


@login_required
def professional_report(request, pk: int):
    """Display a professional, print-ready report for law enforcement use."""
    try:
        report = Report.objects.get(pk=pk)
    except Report.DoesNotExist as e:
        raise Http404 from e
    
    context = {
        'report': report,
    }
    return render(request, 'reports/professional_report.html', context)


@login_required
def update_report(request, pk: int):
    """Update report information via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        report = Report.objects.get(pk=pk)
    except Report.DoesNotExist:
        return JsonResponse({'error': 'Report not found'}, status=404)
    
    # Get the field to update and new value
    field = request.POST.get('field')
    value = request.POST.get('value', '').strip()
    
    # Validate field name
    allowed_fields = ['incident_date', 'officer_badge', 'incident_type', 'notes']
    if field not in allowed_fields:
        return JsonResponse({'error': 'Invalid field'}, status=400)
    
    # Update the field
    setattr(report, field, value)
    report.save()
    
    return JsonResponse({
        'success': True,
        'field': field,
        'value': value,
        'display_value': getattr(report, f'get_{field}_display', lambda: value)() if hasattr(report, f'get_{field}_display') else value
    })


@login_required
def report_pdf(request, pk: int):
    """Generate and download a PDF version of the professional report."""
    try:
        report = Report.objects.get(pk=pk)
    except Report.DoesNotExist as e:
        raise Http404 from e
    
    # Create a BytesIO buffer to hold the PDF
    buffer = BytesIO()
    
    # Create the PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Create custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.darkblue
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=12,
        spaceAfter=8,
        textColor=colors.black
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        alignment=TA_JUSTIFY
    )
    
    # Build the PDF content
    story = []
    
    # Title
    story.append(Paragraph("EVIDENCE PROCESSING REPORT", title_style))
    story.append(Paragraph("Automated AI Analysis & Documentation", styles['Normal']))
    story.append(Paragraph(f"Case #{report.id} | Generated: {report.created_at.strftime('%B %d, %Y - %I:%M %p')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Case Information Section
    story.append(Paragraph("CASE INFORMATION", heading_style))
    
    # Create case info table
    case_data = [
        ['Incident Type:', report.get_incident_type_display() if report.incident_type else 'Not specified'],
        ['Officer Badge #:', f"#{report.officer_badge}" if report.officer_badge else 'Not specified'],
        ['Incident Date:', report.incident_date.strftime('%B %d, %Y') if report.incident_date else 'Not specified'],
        ['Report Status:', report.status.upper()],
    ]
    
    if report.notes:
        case_data.append(['Additional Notes:', report.notes])
    
    case_table = Table(case_data, colWidths=[2*inch, 4*inch])
    case_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(case_table)
    story.append(Spacer(1, 20))
    
    # Evidence Files Section
    story.append(Paragraph("EVIDENCE FILES", heading_style))
    
    evidence_data = [
        ['Original Bodycam Video:', 'File uploaded: ' + report.created_at.strftime('%b %d, %Y %I:%M %p') if report.original_video else 'No video file available'],
        ['Extracted Audio:', 'Audio file available' if report.extracted_audio else 'Audio extraction pending'],
    ]
    
    evidence_table = Table(evidence_data, colWidths=[2*inch, 4*inch])
    evidence_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.lightcyan),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(evidence_table)
    story.append(Spacer(1, 20))
    
    # AI Analysis Results
    if report.transcript_text or report.summarized_report:
        story.append(Paragraph("AI ANALYSIS RESULTS", heading_style))
        
        # Transcript Section
        if report.transcript_text:
            story.append(Paragraph("Audio Transcript", subheading_style))
            story.append(Paragraph("⚠️ OFFICER REVIEW REQUIRED: Please review the transcript for accuracy and completeness. AI transcription may contain errors.", normal_style))
            story.append(Spacer(1, 6))
            
            # Truncate transcript if too long
            transcript_text = report.transcript_text
            if len(transcript_text) > 2000:
                transcript_text = transcript_text[:2000] + "... [Transcript truncated for PDF - full version available in web interface]"
            
            story.append(Paragraph(transcript_text, normal_style))
            story.append(Spacer(1, 12))
        
        # Summary Section
        if report.summarized_report:
            story.append(Paragraph("Comprehensive Summary", subheading_style))
            story.append(Paragraph("📋 OFFICER REVIEW REQUIRED: Please verify the AI-generated summary for accuracy and add any additional observations or corrections.", normal_style))
            story.append(Spacer(1, 6))
            
            # Truncate summary if too long
            summary_text = report.summarized_report
            if len(summary_text) > 3000:
                summary_text = summary_text[:3000] + "... [Summary truncated for PDF - full version available in web interface]"
            
            story.append(Paragraph(summary_text, normal_style))
            story.append(Spacer(1, 20))
    
    # Processing Timeline
    story.append(Paragraph("PROCESSING TIMELINE", heading_style))
    
    timeline_data = [
        ['Report Created:', report.created_at.strftime('%b %d, %Y %I:%M %p')],
    ]
    
    if report.updated_at != report.created_at:
        timeline_data.append(['Last Updated:', report.updated_at.strftime('%b %d, %Y %I:%M %p')])
    
    timeline_data.append(['Processing Status:', 
                         '✓ Analysis completed successfully' if report.status == 'completed' 
                         else f'✗ Processing failed: {report.status_message}' if report.status == 'failed'
                         else '⏳ Currently processing...'])
    
    timeline_table = Table(timeline_data, colWidths=[2*inch, 4*inch])
    timeline_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgreen),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(timeline_table)
    story.append(Spacer(1, 20))
    
    # Officer Review Section
    story.append(Paragraph("OFFICER REVIEW & VERIFICATION", heading_style))
    story.append(Paragraph("🚨 MANDATORY OFFICER REVIEW: This report requires officer verification before use in official proceedings.", normal_style))
    story.append(Spacer(1, 12))
    
    review_items = [
        "☐ Audio Transcript Verified - I have reviewed the audio transcript for accuracy and completeness",
        "☐ Summary Report Verified - I have verified the AI-generated summary and added any necessary corrections",
        "☐ Evidence Chain of Custody Verified - I have confirmed the evidence files are complete and unaltered",
        "☐ Case Information Accurate - I have verified all case details including incident type, date, and officer information"
    ]
    
    for item in review_items:
        story.append(Paragraph(item, normal_style))
        story.append(Spacer(1, 6))
    
    story.append(Spacer(1, 12))
    story.append(Paragraph("Additional Officer Notes/Corrections:", normal_style))
    story.append(Paragraph("_" * 80, normal_style))
    story.append(Paragraph("_" * 80, normal_style))
    story.append(Paragraph("_" * 80, normal_style))
    story.append(Spacer(1, 20))
    
    # Certification Section
    story.append(Paragraph("CERTIFICATION", heading_style))
    
    cert_data = [
        ['Prepared By:', 'EvidenAI-M Automated System'],
        ['Date:', report.created_at.strftime('%B %d, %Y')]
    ]
    
    cert_table = Table(cert_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
    cert_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ('LINEBELOW', (1, 0), (1, 0), 1, colors.black),
        ('LINEBELOW', (3, 0), (3, 0), 1, colors.black),
    ]))
    
    story.append(cert_table)
    story.append(Spacer(1, 20))
    
    # Disclaimer
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        textColor=colors.red,
        backColor=colors.lightgrey,
        borderColor=colors.red,
        borderWidth=1,
        borderPadding=10
    )
    
    story.append(Paragraph("IMPORTANT DISCLAIMER", subheading_style))
    story.append(Paragraph(
        "This report was generated using artificial intelligence and MUST be reviewed and verified by qualified law enforcement personnel before use in official proceedings. The accuracy of AI-generated content may vary and should be verified against original evidence. This report is a preliminary analysis tool and does not replace professional law enforcement investigation and documentation.",
        disclaimer_style
    ))
    
    # Build PDF
    doc.build(story)
    
    # Get the PDF content
    pdf_content = buffer.getvalue()
    buffer.close()
    
    # Create HTTP response with PDF
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="evidence_report_case_{report.id}.pdf"'
    
    return response


# XRPL Digital Signature Views

@login_required
def setup_wallet(request):
    """One-click XRPL wallet setup for officers"""
    try:
        # Check if user already has a wallet
        if hasattr(request.user, 'officer_wallet'):
            messages.info(request, "You already have an XRPL wallet set up.")
            return redirect('dashboard')
        
        # Create wallet
        officer_wallet = xrpl_service.create_wallet_for_user(request.user)
        messages.success(request, f"XRPL wallet created successfully! Address: {officer_wallet.wallet_address}")
        
    except Exception as e:
        messages.error(request, f"Failed to create wallet: {str(e)}")
    
    return redirect('dashboard')


@login_required
def wallet_dashboard(request):
    """Display user's XRPL wallet information"""
    try:
        officer_wallet = xrpl_service.get_wallet_for_user(request.user)
        
        if not officer_wallet:
            messages.info(request, "You need to set up an XRPL wallet first.")
            return redirect('setup_wallet')
        
        # Get wallet balance
        balance = xrpl_service.get_wallet_balance(officer_wallet)
        
        # Get signed reports
        signed_reports = Report.objects.filter(signed_by=request.user).order_by('-signed_at')
        
        context = {
            'officer_wallet': officer_wallet,
            'balance': balance,
            'signed_reports': signed_reports,
        }
        return render(request, 'wallet/dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading wallet dashboard: {str(e)}")
        return redirect('dashboard')


@login_required
def sign_report(request, pk):
    """Sign a report with XRPL digital signature"""
    report = get_object_or_404(Report, pk=pk)
    
    # Check if already signed
    if report.signed_by:
        messages.warning(request, "This report is already signed.")
        return redirect('report_detail', pk=pk)
    
    # Check if user has wallet
    if not hasattr(request.user, 'officer_wallet'):
        messages.error(request, "You need to set up an XRPL wallet first.")
        return redirect('setup_wallet')
    
    try:
        # Sign the report
        tx_hash = xrpl_service.sign_report(report, request.user)
        messages.success(request, f"Report signed successfully! Transaction: {tx_hash}")
        
    except Exception as e:
        messages.error(request, f"Signing failed: {str(e)}")
    
    return redirect('report_detail', pk=pk)


@login_required
def verify_signature(request, pk):
    """Verify a report's digital signature"""
    report = get_object_or_404(Report, pk=pk)
    
    if not report.signature_tx_hash:
        messages.error(request, "This report has not been digitally signed.")
        return redirect('report_detail', pk=pk)
    
    try:
        verification_result = xrpl_service.verify_signature(report)
        
        if verification_result.get('verified'):
            messages.success(request, "Digital signature verified successfully!")
        else:
            messages.error(request, f"Signature verification failed: {verification_result.get('error')}")
        
        context = {
            'report': report,
            'verification_result': verification_result,
        }
        return render(request, 'wallet/verify_signature.html', context)
        
    except Exception as e:
        messages.error(request, f"Error verifying signature: {str(e)}")
        return redirect('report_detail', pk=pk)


@login_required
def signature_status_api(request, pk):
    """API endpoint to get signature status"""
    report = get_object_or_404(Report, pk=pk)
    
    try:
        if report.signature_tx_hash:
            verification_result = xrpl_service.verify_signature(report)
            return JsonResponse({
                'signed': True,
                'verified': verification_result.get('verified', False),
                'tx_hash': report.signature_tx_hash,
                'signed_by': report.signed_by.username if report.signed_by else None,
                'signed_at': report.signed_at.isoformat() if report.signed_at else None,
                'verification_result': verification_result
            })
        else:
            return JsonResponse({
                'signed': False,
                'verified': False
            })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


# Create your views here.
