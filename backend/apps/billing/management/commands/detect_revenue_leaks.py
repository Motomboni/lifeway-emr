"""
Django management command to detect revenue leaks.

Usage:
    python manage.py detect_revenue_leaks
"""
from django.core.management.base import BaseCommand
from apps.billing.leak_detection_service import LeakDetectionService


class Command(BaseCommand):
    help = 'Detect revenue leaks in the system'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("Revenue Leak Detection"))
        self.stdout.write("=" * 80)
        
        self.stdout.write("\nRunning leak detection...")
        
        results = LeakDetectionService.detect_all_leaks()
        
        self.stdout.write("\nDetection Results:")
        self.stdout.write(f"  - Lab Results: {results['lab_results']} leaks")
        self.stdout.write(f"  - Radiology Reports: {results['radiology_reports']} leaks")
        self.stdout.write(f"  - Drug Dispenses: {results['drug_dispenses']} leaks")
        self.stdout.write(f"  - Procedures: {results['procedures']} leaks")
        self.stdout.write(f"  - Total Leaks: {results['total_leaks']}")
        self.stdout.write(f"  - Total Estimated Loss: {results['total_estimated_loss']} NGN")
        
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("Leak detection completed!"))
        self.stdout.write("=" * 80)

