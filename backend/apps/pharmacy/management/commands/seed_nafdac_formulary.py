"""
Seed NAFDAC formulary reference rows linked to NHIA drug tariff codes.

Run: python manage.py seed_nafdac_formulary
Optional CSV: python manage.py seed_nafdac_formulary --file formulary.csv
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.pharmacy.nafdac_models import NAFDACFormularyEntry

STARTER_FORMULARY = [
    {
        "nafdac_reg_no": "04-0001",
        "product_name": "Coartem (Artemether/Lumefantrine) 20/120mg",
        "active_ingredient": "Artemether/Lumefantrine",
        "dosage_form": "Tablet",
        "strength": "20/120mg",
        "manufacturer": "Novartis",
        "nhia_tariff_code": "3-01-01",
        "is_essential_medicine": True,
    },
    {
        "nafdac_reg_no": "04-0002",
        "product_name": "Coartem Dispersible (Artemether/Lumefantrine) 20/120mg",
        "active_ingredient": "Artemether/Lumefantrine",
        "dosage_form": "Dispersible tablet",
        "strength": "20/120mg",
        "manufacturer": "Novartis",
        "nhia_tariff_code": "3-02-01",
        "is_essential_medicine": True,
    },
    {
        "nafdac_reg_no": "04-0003",
        "product_name": "Paracetamol 500mg",
        "active_ingredient": "Paracetamol",
        "dosage_form": "Tablet",
        "strength": "500mg",
        "manufacturer": "Emzor Pharmaceuticals",
        "nhia_tariff_code": "",
        "is_essential_medicine": True,
    },
    {
        "nafdac_reg_no": "04-0004",
        "product_name": "Amoxicillin 500mg",
        "active_ingredient": "Amoxicillin",
        "dosage_form": "Capsule",
        "strength": "500mg",
        "manufacturer": "GlaxoSmithKline",
        "nhia_tariff_code": "",
        "is_essential_medicine": True,
    },
    {
        "nafdac_reg_no": "04-0005",
        "product_name": "Amoxicillin/Clavulanic acid 625mg",
        "active_ingredient": "Amoxicillin/Clavulanic acid",
        "dosage_form": "Tablet",
        "strength": "625mg",
        "manufacturer": "GlaxoSmithKline",
        "nhia_tariff_code": "3-20-01",
        "is_essential_medicine": True,
    },
    {
        "nafdac_reg_no": "04-0006",
        "product_name": "Metformin 500mg",
        "active_ingredient": "Metformin hydrochloride",
        "dosage_form": "Tablet",
        "strength": "500mg",
        "manufacturer": "Merck",
        "nhia_tariff_code": "4-01-01",
        "is_essential_medicine": True,
    },
    {
        "nafdac_reg_no": "04-0007",
        "product_name": "Glibenclamide 5mg",
        "active_ingredient": "Glibenclamide",
        "dosage_form": "Tablet",
        "strength": "5mg",
        "manufacturer": "Sanofi",
        "nhia_tariff_code": "4-01-01",
        "is_essential_medicine": True,
    },
    {
        "nafdac_reg_no": "04-0008",
        "product_name": "Oral Rehydration Salts (ORS)",
        "active_ingredient": "Glucose/Electrolytes",
        "dosage_form": "Powder for oral solution",
        "strength": "Standard WHO",
        "manufacturer": "Fidson Healthcare",
        "nhia_tariff_code": "",
        "is_essential_medicine": True,
    },
    {
        "nafdac_reg_no": "04-0009",
        "product_name": "Zinc Sulphate 20mg",
        "active_ingredient": "Zinc sulphate",
        "dosage_form": "Dispersible tablet",
        "strength": "20mg",
        "manufacturer": "Emzor Pharmaceuticals",
        "nhia_tariff_code": "",
        "is_essential_medicine": True,
    },
    {
        "nafdac_reg_no": "04-0010",
        "product_name": "Ferrous Sulphate + Folic Acid",
        "active_ingredient": "Ferrous sulphate/Folic acid",
        "dosage_form": "Tablet",
        "strength": "200mg + 0.4mg",
        "manufacturer": "Emzor Pharmaceuticals",
        "nhia_tariff_code": "4-02-01",
        "is_essential_medicine": True,
    },
    {
        "nafdac_reg_no": "04-0011",
        "product_name": "Oxytocin 10 IU/mL",
        "active_ingredient": "Oxytocin",
        "dosage_form": "Injection",
        "strength": "10 IU/mL",
        "manufacturer": "Pfizer",
        "nhia_tariff_code": "5-01-01",
        "is_essential_medicine": True,
    },
    {
        "nafdac_reg_no": "04-0012",
        "product_name": "Magnesium Sulphate 50%",
        "active_ingredient": "Magnesium sulphate",
        "dosage_form": "Injection",
        "strength": "50%",
        "manufacturer": "Fidson Healthcare",
        "nhia_tariff_code": "4-02-02",
        "is_essential_medicine": True,
    },
    {
        "nafdac_reg_no": "04-0013",
        "product_name": "Cotrimoxazole 480mg",
        "active_ingredient": "Sulfamethoxazole/Trimethoprim",
        "dosage_form": "Tablet",
        "strength": "480mg",
        "manufacturer": "Emzor Pharmaceuticals",
        "nhia_tariff_code": "",
        "is_essential_medicine": True,
    },
    {
        "nafdac_reg_no": "04-0014",
        "product_name": "Salbutamol Inhaler 100mcg",
        "active_ingredient": "Salbutamol",
        "dosage_form": "Metered-dose inhaler",
        "strength": "100mcg/dose",
        "manufacturer": "GlaxoSmithKline",
        "nhia_tariff_code": "",
        "is_essential_medicine": True,
    },
    {
        "nafdac_reg_no": "04-0015",
        "product_name": "Amlodipine 5mg",
        "active_ingredient": "Amlodipine besylate",
        "dosage_form": "Tablet",
        "strength": "5mg",
        "manufacturer": "Pfizer",
        "nhia_tariff_code": "",
        "is_essential_medicine": True,
    },
    {
        "nafdac_reg_no": "04-0016",
        "product_name": "Losartan 50mg",
        "active_ingredient": "Losartan potassium",
        "dosage_form": "Tablet",
        "strength": "50mg",
        "manufacturer": "Merck",
        "nhia_tariff_code": "",
        "is_essential_medicine": True,
    },
    {
        "nafdac_reg_no": "04-0017",
        "product_name": "Artesunate 60mg",
        "active_ingredient": "Artesunate",
        "dosage_form": "Injection",
        "strength": "60mg",
        "manufacturer": "Guilin Pharmaceutical",
        "nhia_tariff_code": "3-01-01",
        "is_essential_medicine": True,
    },
    {
        "nafdac_reg_no": "04-0018",
        "product_name": "Ceftriaxone 1g",
        "active_ingredient": "Ceftriaxone sodium",
        "dosage_form": "Injection",
        "strength": "1g",
        "manufacturer": "Roche",
        "nhia_tariff_code": "",
        "is_essential_medicine": True,
    },
]

CSV_COLUMNS = {
    "nafdac_reg_no": ["nafdac_reg_no", "reg_no", "registration_number", "nafdac"],
    "product_name": ["product_name", "product", "name"],
    "active_ingredient": ["active_ingredient", "ingredient", "generic"],
    "dosage_form": ["dosage_form", "form"],
    "strength": ["strength"],
    "manufacturer": ["manufacturer", "mfr"],
    "nhia_tariff_code": ["nhia_tariff_code", "nhia_code", "tariff_code"],
}


def _normalize_header(header: str) -> str:
    return header.strip().lower().replace(" ", "_")


def _map_csv_row(row: dict) -> dict:
    normalized = {_normalize_header(k): (v or "").strip() for k, v in row.items()}
    mapped = {}
    for field, aliases in CSV_COLUMNS.items():
        for alias in aliases:
            if alias in normalized and normalized[alias]:
                mapped[field] = normalized[alias]
                break
    if not mapped.get("nafdac_reg_no") or not mapped.get("product_name"):
        raise CommandError(f"Row missing nafdac_reg_no or product_name: {row}")
    mapped.setdefault("active_ingredient", "")
    mapped.setdefault("dosage_form", "")
    mapped.setdefault("strength", "")
    mapped.setdefault("manufacturer", "")
    mapped.setdefault("nhia_tariff_code", "")
    essential = normalized.get("is_essential_medicine", "")
    mapped["is_essential_medicine"] = essential.lower() in ("1", "true", "yes", "y")
    mapped["is_active"] = normalized.get("is_active", "true").lower() not in (
        "0",
        "false",
        "no",
        "n",
    )
    return mapped


class Command(BaseCommand):
    help = "Seed NAFDAC formulary reference rows (starter pack or CSV import)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            help="Optional CSV file with formulary rows.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing NAFDAC formulary rows before seeding.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = NAFDACFormularyEntry.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"Removed {deleted} existing formulary rows.")
            )

        rows = STARTER_FORMULARY
        if options["file"]:
            rows = self._load_csv(options["file"])

        created = 0
        updated = 0
        for row in rows:
            defaults = {
                "product_name": row["product_name"],
                "active_ingredient": row.get("active_ingredient", ""),
                "dosage_form": row.get("dosage_form", ""),
                "strength": row.get("strength", ""),
                "manufacturer": row.get("manufacturer", ""),
                "nhia_tariff_code": row.get("nhia_tariff_code", ""),
                "is_essential_medicine": row.get("is_essential_medicine", False),
                "is_active": row.get("is_active", True),
            }
            _, was_created = NAFDACFormularyEntry.objects.update_or_create(
                nafdac_reg_no=row["nafdac_reg_no"],
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"NAFDAC formulary seeded: {created} created, {updated} updated "
                f"({len(rows)} rows)."
            )
        )

    def _load_csv(self, file_path: str) -> list:
        path = Path(file_path)
        if not path.exists():
            raise CommandError(f"File not found: {file_path}")
        rows = []
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise CommandError("CSV file has no header row.")
            for row in reader:
                rows.append(_map_csv_row(row))
        if not rows:
            raise CommandError("CSV file contains no data rows.")
        return rows
