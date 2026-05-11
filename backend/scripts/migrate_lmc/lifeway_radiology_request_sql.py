"""
LIFEWAY tblRadRequest export for migrate_lmc.

Investigations is aggregated from tblRadRequestDetails + tblChargeItem.Name (pipe-delimited).
Uses FOR XML PATH for compatibility with older SQL Server versions.
"""

LIFEWAY_RAD_REQUEST_SELECT_BODY = """
    CAST(r.RequestID AS int) AS RequestID,
    CAST(r.PatientID AS int) AS PatientID,
    CAST(NULLIF(NULLIF(r.VisitID, 0), -1) AS int) AS VisitID,
    CAST(r.[Date] AS datetime) AS [Date],
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(r.Sender, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(100)
    ) AS Sender,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(r.Status, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(100)
    ) AS Status,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(r.Diagnosis, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS Diagnosis,
    CAST(
        ISNULL(
            STUFF((
                SELECT N'|' + LTRIM(RTRIM(
                    REPLACE(REPLACE(REPLACE(ISNULL(ci.Name, N''), N'|', N'/'), CHAR(10), N' '), CHAR(13), N' ')
                ))
                FROM dbo.tblRadRequestDetails d
                LEFT JOIN dbo.tblChargeItem ci ON ci.ChargeItemID = d.TestID
                WHERE d.RequestID = r.RequestID
                  AND LTRIM(RTRIM(ISNULL(ci.Name, N''))) <> N''
                ORDER BY d.RadRequestDetailsID
                FOR XML PATH('')
            ), 1, 1, N''), N''
        ) AS nvarchar(max)
    ) AS Investigations
FROM dbo.tblRadRequest r
WHERE r.RequestID IS NOT NULL
ORDER BY r.RequestID ASC
""".strip()
