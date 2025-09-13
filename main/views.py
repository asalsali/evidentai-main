from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse, Http404
from .forms import VideoUploadForm
from .models import Report
import threading


def dashboard(request):
    reports = Report.objects.order_by('-created_at')[:10]
    form = VideoUploadForm()
    return render(request, 'dashboard.html', {"form": form, "reports": reports})


def _process_report_background(report_id: int):
    from agents_sdk.evidence_processing_agents.manager import EvidenceProcessingManager
    manager = EvidenceProcessingManager()
    manager.process_report_sync(report_id)


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


def reports_all(request):
    reports = Report.objects.order_by('-created_at')
    return render(request, 'reports/list.html', {"title": "All Reports", "reports": reports})


def reports_in_progress(request):
    reports = Report.objects.exclude(status__in=['completed', 'failed']).order_by('-created_at')
    return render(request, 'reports/list.html', {"title": "In Progress", "reports": reports})


def reports_completed(request):
    reports = Report.objects.filter(status='completed').order_by('-created_at')
    return render(request, 'reports/list.html', {"title": "Completed", "reports": reports})


def report_detail(request, pk: int):
    try:
        report = Report.objects.get(pk=pk)
    except Report.DoesNotExist as e:
        raise Http404 from e
    return render(request, 'reports/detail.html', {"report": report})


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

# Create your views here.
