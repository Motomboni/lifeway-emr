"""Searchable guide articles for Ask Guide (bounded NL retrieval)."""

from __future__ import annotations

from .guide_modules import article_module_allowed

GUIDE_ARTICLES: list[dict] = [
    {
        "id": "lab-order",
        "roles": ["DOCTOR", "NURSE", "ADMIN"],
        "module": "laboratory",
        "keywords": ["lab", "laboratory", "cbc", "blood test", "order lab"],
        "title": "Order a lab test",
        "summary": "Lab orders are in the Consultation workspace, in the Lab Orders section below clinical notes.",
        "guide_target": "lab-inline",
        "steps": [
            "Open the patient's visit from Visits or your dashboard.",
            "Scroll to Lab Orders in the consultation workspace.",
            "Click Add lab order and select tests or apply a template.",
        ],
    },
    {
        "id": "lab-fulfillment",
        "roles": ["LAB_TECH", "ADMIN"],
        "module": "laboratory",
        "keywords": ["lab result", "worklist", "process lab", "lab tech", "fulfillment"],
        "title": "Process lab orders",
        "summary": "Lab Techs open the Lab Orders worklist, select a visit, and record results.",
        "guide_target": "lab-worklist",
        "steps": [
            "Open Lab Orders from your dashboard.",
            "Select a visit from the worklist.",
            "Add results for each pending order and flag abnormal values.",
        ],
    },
    {
        "id": "service-catalog",
        "roles": ["DOCTOR", "ADMIN"],
        "module": "nhia",
        "keywords": ["service", "catalog", "bill", "charge", "nhia"],
        "title": "Order from Service Catalog",
        "summary": "Doctors add billable services from the Service Catalog section after clinical notes.",
        "guide_target": "service-catalog",
        "steps": [
            "In Consultation, scroll to Service Catalog after clinical notes.",
            "Search for the service and add it to the visit bill.",
        ],
    },
    {
        "id": "nhia-claims",
        "roles": ["DOCTOR", "RECEPTIONIST", "ADMIN"],
        "module": "nhia",
        "keywords": ["nhia", "claim", "tariff", "hmo", "insurance", "compliance"],
        "title": "NHIA billing & claims",
        "summary": "Add NHIA-validated services from the catalog, then export claim packs from billing.",
        "guide_target": "service-catalog",
        "steps": [
            "Add NHIA tariff items from Service Catalog during consultation.",
            "Clear payment on Visit Details → Billing.",
            "Export claim pack (CSV/PDF) from the NHIA compliance dashboard when ready.",
        ],
    },
    {
        "id": "billing-clear",
        "roles": ["RECEPTIONIST", "ADMIN"],
        "keywords": ["payment", "billing", "clear", "pay", "cash", "pos"],
        "title": "Clear patient payment",
        "summary": "Reception clears payment on Visit Details → Billing before clinical staff can complete some actions.",
        "guide_target": "billing-dashboard",
        "steps": [
            "Open the visit from Visits or Pending Payments.",
            "Go to the Billing section.",
            "Process payment (Cash, POS, Transfer, or Paystack).",
        ],
    },
    {
        "id": "register-patient",
        "roles": ["RECEPTIONIST", "ADMIN"],
        "keywords": ["register", "new patient", "create patient", "enroll"],
        "title": "Register a new patient",
        "summary": "Use Register Patient from your dashboard quick actions.",
        "guide_target": "register-patient",
        "steps": [
            "From the Receptionist dashboard, click Register Patient.",
            "Complete demographics and save.",
            "Create a visit for the patient.",
        ],
    },
    {
        "id": "close-visit",
        "roles": ["DOCTOR", "ADMIN"],
        "keywords": ["close", "discharge", "finish", "complete visit"],
        "title": "Close a visit",
        "summary": "Save consultation, ensure billing is cleared, then close from Consultation actions.",
        "guide_target": "consultation-actions",
        "steps": [
            "Save the consultation.",
            "Confirm payment is PAID or SETTLED.",
            "Use Close Visit in consultation actions.",
        ],
    },
    {
        "id": "vitals",
        "roles": ["NURSE", "DOCTOR", "ADMIN"],
        "keywords": ["vitals", "blood pressure", "temperature", "pulse", "bp"],
        "title": "Record vital signs",
        "summary": "Vital signs are at the top of the Consultation or Nursing visit page.",
        "guide_target": "vitals-inline",
        "steps": [
            "Open the visit.",
            "Find Vital Signs near the top of the page.",
            "Enter values and save.",
        ],
    },
    {
        "id": "appointments",
        "roles": ["DOCTOR", "RECEPTIONIST", "ADMIN"],
        "keywords": ["appointment", "schedule", "book"],
        "title": "Schedule an appointment",
        "summary": "Doctors can self-schedule; reception sees all clinic appointments.",
        "guide_target": "appointments",
        "steps": [
            "Open Appointments from the dashboard.",
            "Select patient, date, and time.",
            "Save — reception will see doctor-scheduled slots.",
        ],
    },
    {
        "id": "radiology-order",
        "roles": ["DOCTOR", "ADMIN"],
        "module": "radiology",
        "keywords": ["radiology", "xray", "x-ray", "ct", "mri", "ultrasound", "imaging"],
        "title": "Order radiology imaging",
        "summary": "Radiology orders live in the Consultation workspace below clinical notes.",
        "guide_target": "radiology-inline",
        "steps": [
            "Open the visit consultation workspace.",
            "Scroll to Radiology / Imaging.",
            "Select modality, body part, and clinical indication, then submit.",
        ],
    },
    {
        "id": "prescription-order",
        "roles": ["DOCTOR", "ADMIN"],
        "module": "pharmacy",
        "keywords": ["prescription", "prescribe", "rx", "medication", "drug"],
        "title": "Write a prescription",
        "summary": "Prescriptions are created inline during consultation after diagnosis.",
        "guide_target": "prescription-inline",
        "steps": [
            "Save consultation with diagnosis first.",
            "Scroll to Prescriptions in the consultation workspace.",
            "Add drug, dosage, frequency, and quantity.",
        ],
    },
    {
        "id": "dispense-prescription",
        "roles": ["PHARMACIST", "ADMIN"],
        "module": "pharmacy",
        "keywords": ["dispense", "pharmacy", "pharmacist", "medication", "fulfillment"],
        "title": "Dispense prescriptions",
        "summary": "Pharmacists process the prescription worklist after payment is cleared.",
        "guide_target": "pharmacy-worklist",
        "steps": [
            "Open Prescriptions from your dashboard.",
            "Select a visit with pending Rx.",
            "Verify payment, enter dispensed quantity, and dispense.",
        ],
    },
    {
        "id": "anc-visit",
        "roles": ["DOCTOR", "NURSE", "ADMIN"],
        "module": "anc",
        "keywords": ["anc", "antenatal", "pregnancy", "prenatal", "maternal"],
        "title": "Antenatal (ANC) visit",
        "summary": "ANC visits use dedicated schedules, vitals, and macro templates in consultation.",
        "guide_target": "consultation-form",
        "steps": [
            "Open the patient's ANC visit.",
            "Record vitals and gestational age.",
            "Use the .anc macro or ANC scribe template for structured notes.",
        ],
    },
    {
        "id": "telemedicine-consult",
        "roles": ["DOCTOR", "RECEPTIONIST", "ADMIN"],
        "module": "telemedicine",
        "keywords": ["telemedicine", "video", "remote", "virtual", "telehealth"],
        "title": "Telemedicine consultation",
        "summary": "Start a video visit from the telemedicine queue; chart in the same consultation workspace.",
        "guide_target": "consultation-form",
        "steps": [
            "Open Telemedicine from the dashboard or appointments.",
            "Join the scheduled video session.",
            "Document in Consultation — orders and billing stay visit-scoped.",
        ],
    },
]


def search_guide_articles(
    query: str,
    role: str,
    limit: int = 5,
    enabled_modules: dict[str, bool] | None = None,
) -> list[dict]:
    """Simple keyword retrieval for Ask Guide, filtered by role and org modules."""
    modules = enabled_modules or {}
    q = (query or "").strip().lower()

    def eligible(article: dict) -> bool:
        if role not in article["roles"] and role != "ADMIN":
            return False
        if enabled_modules is not None and not article_module_allowed(article, modules):
            return False
        return True

    if not q:
        role_articles = [a for a in GUIDE_ARTICLES if eligible(a)]
        return role_articles[:limit]

    scored: list[tuple[int, dict]] = []
    for article in GUIDE_ARTICLES:
        if not eligible(article):
            continue
        score = 0
        if q in article["title"].lower():
            score += 10
        if q in article["summary"].lower():
            score += 5
        for kw in article["keywords"]:
            if q in kw or kw in q:
                score += 3
        if score > 0:
            scored.append((score, article))
    scored.sort(key=lambda x: -x[0])
    return [a for _, a in scored[:limit]]
