"""
LIFEWAY tblLabRequest export for migrate_lmc.

TestsRequested is aggregated from tblLabRequestDetails + tblLabTest (pipe-delimited for CSV).
Uses FOR XML PATH for compatibility with older SQL Server versions (no STRING_AGG).
VisitID uses NULL when legacy stored 0 (no visit link).
"""

LIFEWAY_LAB_REQUEST_SELECT_BODY = """
    CAST(r.RequestID AS int) AS RequestID,
    CAST(r.PatientID AS int) AS PatientID,
    CAST(NULLIF(NULLIF(r.VisitID, 0), -1) AS int) AS VisitID,
    CAST(COALESCE(r.DateRequested, r.TimeRequested, r.[Date]) AS datetime) AS DateRequested,
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
                    REPLACE(REPLACE(REPLACE(ISNULL(t.TestName, N''), N'|', N'/'), CHAR(10), N' '), CHAR(13), N' ')
                ))
                FROM dbo.tblLabRequestDetails d
                LEFT JOIN dbo.tblLabTest t ON t.TestID = d.TestID
                WHERE d.RequestID = r.RequestID
                  AND LTRIM(RTRIM(ISNULL(t.TestName, N''))) <> N''
                ORDER BY d.LabRequestDetailsID
                FOR XML PATH('')
            ), 1, 1, N''), N''
        ) AS nvarchar(max)
    ) AS TestsRequested
FROM dbo.tblLabRequest r
WHERE r.RequestID IS NOT NULL
ORDER BY r.RequestID ASC
""".strip()
