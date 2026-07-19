import io
import logging
from datetime import datetime
from pathlib import Path

from django.conf import settings
from .models import Patient
from apps.visits.models import Visit

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False


class MedicalHistoryPDFService:
    @staticmethod
    def _get_logo_path() -> str:
        base_dir = getattr(settings, "BASE_DIR", None)
        if base_dir:
            return str(Path(base_dir).parent / "frontend" / "public" / "logo.png")
        return ""

    @staticmethod
    def _format_date(date_val) -> str:
        if not date_val:
            return ""
        return date_val.strftime("%d %B %Y, %I:%M %p")

    @classmethod
    def generate_pdf(cls, patient: Patient) -> bytes:
        if not WEASYPRINT_AVAILABLE:
            raise ImportError("WeasyPrint is not installed or missing dependencies.")

        # Gather data
        visits = Visit.objects.filter(patient=patient).order_by("-created_at").prefetch_related(
            "consultation_set",
            "prescriptions",
            "lab_orders__results",
            "radiology_requests__results"
        )

        clinic_name = getattr(settings, "CLINIC_NAME", "Lifeway Medical Centre Ltd")
        clinic_address = getattr(settings, "CLINIC_ADDRESS", "Plot 1593, ZONE E, APO RESETTLEMENT, ABUJA")
        clinic_phone = getattr(settings, "CLINIC_PHONE", "07058893439, 08033145080")
        
        logo_path = cls._get_logo_path()
        base_url = Path(logo_path).parent.as_uri() + "/" if Path(logo_path).exists() else None
        
        logo_html = '<div class="logo-container"><img src="logo.png" alt="Logo" style="max-height: 80px;"/></div>' if base_url else ""

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Medical History - {patient.get_full_name()}</title>
            <style>
                @page {{ size: A4; margin: 20mm; }}
                body {{ font-family: 'Helvetica', 'Arial', sans-serif; font-size: 12px; line-height: 1.5; color: #333; }}
                .header {{ text-align: center; border-bottom: 2px solid #2563eb; padding-bottom: 10px; margin-bottom: 20px; }}
                .clinic-name {{ font-size: 20px; font-weight: bold; color: #2563eb; }}
                .title {{ font-size: 18px; font-weight: bold; margin: 20px 0; text-align: center; text-transform: uppercase; }}
                .patient-info {{ margin-bottom: 20px; padding: 15px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; }}
                .patient-info p {{ margin: 5px 0; }}
                h3 {{ color: #1e40af; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; margin-top: 30px; }}
                .visit-card {{ margin-bottom: 20px; padding: 15px; border: 1px solid #cbd5e1; border-radius: 8px; page-break-inside: avoid; }}
                .visit-header {{ font-weight: bold; font-size: 14px; margin-bottom: 10px; color: #0f172a; }}
                .section {{ margin-top: 10px; margin-bottom: 15px; }}
                .section-title {{ font-weight: bold; color: #475569; margin-bottom: 5px; text-transform: uppercase; font-size: 11px; }}
                .data-row {{ display: flex; margin-bottom: 3px; }}
                .label {{ font-weight: bold; width: 120px; flex-shrink: 0; color: #64748b; }}
                .value {{ flex-grow: 1; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 5px; font-size: 11px; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
                th {{ background-color: #f1f5f9; font-weight: bold; color: #334155; }}
            </style>
        </head>
        <body>
            <div class="header">
                {logo_html}
                <div class="clinic-name">{clinic_name}</div>
                <div>{clinic_address}</div>
                <div>{clinic_phone}</div>
            </div>
            
            <div class="title">Comprehensive Medical History</div>
            
            <div class="patient-info">
                <p><strong>Patient Name:</strong> {patient.get_full_name()}</p>
                <p><strong>Patient ID:</strong> {patient.patient_id}</p>
                <p><strong>Gender:</strong> {patient.gender or 'N/A'}</p>
                <p><strong>Date of Birth:</strong> {patient.date_of_birth or 'N/A'} {f" ({patient.age} years)" if patient.age else ""}</p>
                <p><strong>Phone:</strong> {patient.phone or 'N/A'}</p>
                <p><strong>Generated On:</strong> {cls._format_date(datetime.now())}</p>
            </div>
        """

        if not visits:
            html_content += "<p>No visit history found for this patient.</p>"

        for visit in visits:
            html_content += f"""
            <div class="visit-card">
                <div class="visit-header">
                    Visit #{visit.id} &bull; {cls._format_date(visit.created_at)}
                </div>
            """
            
            # Consultations
            consultations = visit.consultation_set.all()
            for cons in consultations:
                html_content += f'<div class="section"><div class="section-title">Consultation</div>'
                if cons.history:
                    html_content += f'<div class="data-row"><div class="label">History:</div><div class="value">{cons.history}</div></div>'
                if cons.examination:
                    html_content += f'<div class="data-row"><div class="label">Examination:</div><div class="value">{cons.examination}</div></div>'
                if cons.diagnosis:
                    html_content += f'<div class="data-row"><div class="label">Diagnosis:</div><div class="value" style="color:#dc2626;font-weight:bold;">{cons.diagnosis}</div></div>'
                if cons.clinical_notes:
                    html_content += f'<div class="data-row"><div class="label">Notes:</div><div class="value">{cons.clinical_notes}</div></div>'
                if cons.created_by:
                    html_content += f'<div class="data-row"><div class="label">Seen By:</div><div class="value">{cons.created_by.get_full_name()}</div></div>'
                html_content += '</div>'
            
            # Prescriptions
            prescriptions = visit.prescriptions.all()
            if prescriptions:
                html_content += '<div class="section"><div class="section-title">Prescriptions</div><table>'
                html_content += '<tr><th>Drug</th><th>Dosage</th><th>Frequency</th><th>Status</th></tr>'
                for rx in prescriptions:
                    html_content += f'<tr><td>{rx.drug}</td><td>{rx.dosage}</td><td>{rx.frequency or "-"}</td><td>{rx.status}</td></tr>'
                html_content += '</table></div>'
                
            # Labs
            lab_orders = visit.lab_orders.all()
            if lab_orders:
                has_results = any(o.results.exists() for o in lab_orders)
                html_content += '<div class="section"><div class="section-title">Laboratory</div>'
                for order in lab_orders:
                    for res in order.results.all():
                        html_content += f"""
                        <div style="margin-bottom:8px; padding:8px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:4px;">
                            <strong>Order #{order.id}</strong> {f'<span style="color:#dc2626;margin-left:8px;">Flag: {res.abnormal_flag}</span>' if res.abnormal_flag and res.abnormal_flag != 'NORMAL' else ''}
                            <pre style="margin:5px 0 0 0; font-family: monospace; font-size:10px; white-space: pre-wrap;">{res.result_data}</pre>
                        </div>
                        """
                html_content += '</div>'

            # Radiology
            rad_requests = visit.radiology_requests.all()
            if rad_requests:
                html_content += '<div class="section"><div class="section-title">Radiology</div>'
                for req in rad_requests:
                    for res in req.results.all():
                        html_content += f"""
                        <div style="margin-bottom:8px; padding:8px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:4px;">
                            <strong>Request #{req.id}</strong> {f'<span style="color:#d97706;margin-left:8px;">Flag: {res.finding_flag}</span>' if res.finding_flag and res.finding_flag != 'NORMAL' else ''}
                            <p style="margin:5px 0 0 0; font-size:11px;">{res.report}</p>
                        </div>
                        """
                html_content += '</div>'

            html_content += "</div>" # end visit-card

        html_content += "</body></html>"
        
        pdf = HTML(string=html_content, base_url=base_url).write_pdf()
        return pdf
