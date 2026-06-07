"""
LIFEWAY tblPatientPayment export for migrate_lmc (billing slice).

PatientID is the legacy out-patient id (same key as tblOutPatientRecord / tblPatientVisits).
"""

_LIFEWAY_TX = (
    "CAST(REPLACE(REPLACE(REPLACE(ISNULL({expr}, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ') AS nvarchar(max))"
)


def _nv(expr: str) -> str:
    return _LIFEWAY_TX.format(expr=expr)


LIFEWAY_PATIENT_PAYMENT_SELECT_BODY = f"""
    CAST(p.PatientPayID AS int) AS PatientPayID,
    CAST(p.PatientID AS int) AS PatientID,
    CAST(p.[Date] AS datetime) AS PaymentDate,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(p.Status, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(50)
    ) AS LegacyStatus,
    CAST(p.ReceiptNo AS int) AS ReceiptNo,
    CAST(
        COALESCE(
            NULLIF(TRY_CAST(p.AmountPaid AS decimal(18, 2)), CAST(0 AS decimal(18, 2))),
            NULLIF(TRY_CAST(p.Total AS decimal(18, 2)), CAST(0 AS decimal(18, 2))),
            CAST(0 AS decimal(18, 2))
        ) AS decimal(18, 2)
    ) AS PayAmount,
    {_nv("CAST(p.Service AS nvarchar(max))")} AS ServiceLine,
    {_nv("p.Diagnosis")} AS DiagnosisLine,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(p.HMOCode, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(80)
    ) AS HMOCode,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(p.Name, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(80)
    ) AS PayerName
FROM dbo.tblPatientPayment p
WHERE p.PatientPayID IS NOT NULL
ORDER BY p.PatientPayID ASC
""".strip()
