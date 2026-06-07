"""
LIFEWAY lab results for migrate_lmc: one row per RequestID with aggregated detail lines.

Uses FOR XML PATH for compatibility with older SQL Server versions (no STRING_AGG).
tblLabResult can have multiple rows per RequestID; detail lines come from tblLabResultDetails.
"""

LIFEWAY_LAB_RESULT_SELECT_BODY = """
    CAST(r.RequestID AS int) AS RequestID,
    CAST(MAX(req.PatientID) AS int) AS PatientID,
    CAST(MAX(r.[Date]) AS datetime) AS [Date],
    CAST(
        REPLACE(
            REPLACE(
                REPLACE(ISNULL(MAX(LTRIM(RTRIM(ISNULL(r.AuthorizedBy, N'')))), N''), N',', N';'),
                CHAR(10),
                N' '
            ),
            CHAR(13),
            N' '
        ) AS nvarchar(200)
    ) AS AuthorizedBy,
    CAST(
        REPLACE(
            REPLACE(
                REPLACE(ISNULL(MAX(CAST(r.notes AS nvarchar(max))), N''), N',', N';'),
                CHAR(10),
                N' '
            ),
            CHAR(13),
            N' '
        ) AS nvarchar(max)
    ) AS HeaderNotes,
    CAST(
        ISNULL(
            STUFF((
                SELECT N' | ' + x.line
                FROM (
                    SELECT
                        lr.ResultID AS rid,
                        d.LabResultDetailsID AS lid,
                        LTRIM(RTRIM(ISNULL(d.Test, N''))) + N': ' + LTRIM(RTRIM(ISNULL(d.Value, N''))) +
                        CASE
                            WHEN NULLIF(LTRIM(RTRIM(ISNULL(d.measure, N''))), N'') IS NOT NULL
                                THEN N' ' + LTRIM(RTRIM(d.measure))
                            ELSE N''
                        END +
                        CASE
                            WHEN NULLIF(LTRIM(RTRIM(ISNULL(d.rangeVal, N''))), N'') IS NOT NULL
                                THEN N' (ref ' + LTRIM(RTRIM(d.rangeVal)) + N')'
                            ELSE N''
                        END AS line
                    FROM dbo.tblLabResult lr
                    INNER JOIN dbo.tblLabResultDetails d ON d.ResultID = lr.ResultID
                    WHERE lr.RequestID = r.RequestID
                ) AS x
                ORDER BY x.rid, x.lid
                FOR XML PATH('')
            ), 1, 3, N''), N''
        ) AS nvarchar(max)
    ) AS ResultData
FROM dbo.tblLabResult r
LEFT JOIN dbo.tblLabRequest req ON req.RequestID = r.RequestID
WHERE r.RequestID IS NOT NULL AND r.RequestID <> 0
GROUP BY r.RequestID
ORDER BY r.RequestID ASC
""".strip()
