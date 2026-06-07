"""
LIFEWAY tblRadResult export for migrate_lmc.

One row per RequestID, with report text aggregated from RTBNotes.
Uses FOR XML PATH for compatibility with older SQL Server versions.
"""

LIFEWAY_RAD_RESULT_SELECT_BODY = """
    CAST(r.RequestID AS int) AS RequestID,
    CAST(MAX(req.PatientID) AS int) AS PatientID,
    CAST(MAX(r.[Date]) AS datetime) AS [Date],
    CAST(
        REPLACE(
            REPLACE(
                REPLACE(ISNULL(MAX(LTRIM(RTRIM(ISNULL(r.reportby, N'')))), N''), N',', N';'),
                CHAR(10),
                N' '
            ),
            CHAR(13),
            N' '
        ) AS nvarchar(100)
    ) AS ReportBy,
    CAST(
        ISNULL(
            STUFF((
                SELECT CHAR(10) + LTRIM(RTRIM(ISNULL(CAST(rr.RTBNotes AS nvarchar(max)), N'')))
                FROM dbo.tblRadResult rr
                WHERE rr.RequestID = r.RequestID
                  AND LTRIM(RTRIM(ISNULL(CAST(rr.RTBNotes AS nvarchar(max)), N''))) <> N''
                ORDER BY rr.ResultID
                FOR XML PATH('')
            ), 1, 1, N''), N''
        ) AS nvarchar(max)
    ) AS ReportText
FROM dbo.tblRadResult r
LEFT JOIN dbo.tblRadRequest req ON req.RequestID = r.RequestID
WHERE r.RequestID IS NOT NULL AND r.RequestID <> 0
GROUP BY r.RequestID
ORDER BY r.RequestID ASC
""".strip()
