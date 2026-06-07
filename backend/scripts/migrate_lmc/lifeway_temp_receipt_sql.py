"""
LIFEWAY receipt detail lines: tblTempReceipt joined to tblReceiptGrid.

tblReceipt / tblReceiptLog are often empty in OPD backups; POS lines live in tblTempReceipt.
"""

_LIFEWAY_TX = (
    "CAST(REPLACE(REPLACE(REPLACE(ISNULL({expr}, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ') AS nvarchar(max))"
)


def _nv(expr: str) -> str:
    return _LIFEWAY_TX.format(expr=expr)


LIFEWAY_TEMP_RECEIPT_SELECT_BODY = f"""
    CAST(tr.ID AS int) AS TempReceiptID,
    CAST(tr.ReceiptID AS int) AS GridReceiptID,
    CAST(ISNULL(rg.ReceiptNo, 0) AS int) AS ReceiptNo,
    CAST(rg.PatientID AS int) AS PatientID,
    CAST(rg.[Date] AS datetime) AS LineDate,
    {_nv("CAST(tr.Service AS nvarchar(max))")} AS ServiceLine,
    {_nv("tr.FieldName")} AS FieldName,
    CAST(
        COALESCE(TRY_CAST(tr.Total AS decimal(18, 2)), CAST(0 AS decimal(18, 2)))
        AS decimal(18, 2)
    ) AS LineAmount
FROM dbo.tblTempReceipt tr
INNER JOIN dbo.tblReceiptGrid rg ON rg.ReceiptID = tr.ReceiptID
WHERE tr.ID IS NOT NULL
  AND tr.ReceiptID IS NOT NULL
  AND ISNULL(rg.Deleted, 0) = 0
  AND COALESCE(TRY_CAST(tr.Total AS decimal(18, 2)), CAST(0 AS decimal(18, 2))) > 0
ORDER BY tr.ID ASC
""".strip()
