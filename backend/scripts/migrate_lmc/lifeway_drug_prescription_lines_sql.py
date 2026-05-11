"""
LIFEWAY prescription lines: tblDrugPresItems + tblDrugPrescription + drug name from tblPhamDrugItem.

One export row per PresItemID (suitable for migrate_lmc → apps.pharmacy.Prescription).
"""

_LIFEWAY_TX = (
    "CAST(REPLACE(REPLACE(REPLACE(ISNULL({expr}, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ') AS nvarchar(max))"
)


def _nv(expr: str) -> str:
    return _LIFEWAY_TX.format(expr=expr)


LIFEWAY_DRUG_PRESCRIPTION_LINES_SELECT_BODY = f"""
    CAST(i.PresItemID AS int) AS PresItemID,
    CAST(i.PrescriptionID AS int) AS PrescriptionID,
    CAST(p.PatientID AS int) AS PatientID,
    CAST(p.[Date] AS datetime) AS PrescriptionDate,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(p.Sender, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(100)
    ) AS Sender,
    CAST(i.DrugItemID AS int) AS DrugItemID,
    {_nv("d.Name")} AS DrugName,
    CAST(i.QtyIssued AS int) AS QtyIssued,
    {_nv("i.Notes")} AS ItemNotes
FROM dbo.tblDrugPresItems i
INNER JOIN dbo.tblDrugPrescription p ON p.PrescriptionID = i.PrescriptionID
LEFT JOIN dbo.tblPhamDrugItem d ON d.DrugItemID = i.DrugItemID
WHERE i.PresItemID IS NOT NULL
ORDER BY i.PresItemID ASC
""".strip()
