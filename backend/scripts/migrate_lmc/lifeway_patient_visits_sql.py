"""
LIFEWAY tblPatientVisits export: ClinicID + charge item name + OP narrative fields.

ClinicName comes from dbo.tblChargeItem.Name (same as vwChargeItems.itemName for a join on ClinicID).
Narrative columns are normalized for CSV (comma / newline stripping) and cast from ntext where needed.
"""

# Reusable: legacy free-text -> CSV-safe nvarchar(max)
_LIFEWAY_TX = (
    "CAST(REPLACE(REPLACE(REPLACE(ISNULL({expr}, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ') AS nvarchar(max))"
)


def _nv(expr: str) -> str:
    return _LIFEWAY_TX.format(expr=expr)


LIFEWAY_PATIENT_VISITS_SELECT_BODY = f"""
    CAST(v.visitID AS int) AS VisitID,
    CAST(v.OutPatientID AS int) AS PatientID,
    CAST(v.ClinicID AS int) AS ClinicID,
    CAST(ISNULL(ci.Name, N'') AS nvarchar(255)) AS ClinicName,
    CAST(v.[Date] AS datetime) AS [Date],
    CAST(N'CONSULTATION' AS nvarchar(50)) AS VisitType,
    CAST(N'OPEN' AS nvarchar(50)) AS [Status],
    CAST(N'UNPAID' AS nvarchar(50)) AS PaymentStatus,
    {_nv("v.Complaint")} AS ChiefComplaint,
    CAST(NULL AS nvarchar(max)) AS [Reason],
    {_nv("v.Notes")} AS VisitNotes,
    {_nv("v.HPC")} AS HPC,
    {_nv("v.PMH")} AS PMH,
    {_nv("v.FHx")} AS FHx,
    {_nv("v.Exam")} AS Exam,
    {_nv("v.Assesment")} AS Assessment,
    {_nv("v.TreatPlan")} AS TreatPlan,
    {_nv("v.[results]")} AS ResultsText,
    {_nv("v.Treatment")} AS Treatment,
    {_nv("v.Summary")} AS Summary,
    CAST(
        REPLACE(
            REPLACE(
                REPLACE(ISNULL(CAST(v.FollowUp AS nvarchar(max)), N''), N',', N';'),
                CHAR(10),
                N' '
            ),
            CHAR(13),
            N' '
        ) AS nvarchar(max)
    ) AS FollowUp,
    {_nv("v.IMH")} AS IMH,
    {_nv("v.DH")} AS DH,
    {_nv("v.Weight")} AS Weight,
    {_nv("v.Temperature")} AS Temperature,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(v.Doctor, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(100)
    ) AS LegacyDoctor
FROM dbo.tblPatientVisits v
LEFT JOIN dbo.tblChargeItem ci ON ci.ChargeItemID = v.ClinicID
WHERE v.visitID IS NOT NULL
ORDER BY v.visitID ASC
""".strip()
