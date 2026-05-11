"""
LIFEWAY tblVitalSign export for migrate_lmc.

VisitID is not stored on tblVitalSign; it is resolved by matching tblPatientVisits
(OutPatientID = PatientID, same calendar day as vital Date, closest time to TimePosted/Date).
Legacy column BTemp is exported as Temperature; BP/BPUpper+BPLower as BloodPressure.
"""

LIFEWAY_VITAL_SIGN_SELECT_BODY = """
    CAST(vs.VSID AS int) AS VSID,
    CAST((
        SELECT TOP 1 v.visitID
        FROM dbo.tblPatientVisits v
        WHERE v.OutPatientID = vs.PatientID
          AND vs.PatientID IS NOT NULL
          AND v.[Date] IS NOT NULL
          AND vs.[Date] IS NOT NULL
          AND CAST(v.[Date] AS date) = CAST(vs.[Date] AS date)
        ORDER BY ABS(DATEDIFF(second, v.[Date], ISNULL(vs.TimePosted, vs.[Date]))), v.visitID
    ) AS int) AS VisitID,
    CAST(ISNULL(vs.TimePosted, vs.[Date]) AS datetime) AS RecordedAt,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(vs.BTemp, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(50)
    ) AS Temperature,
    CAST(
        CASE
            WHEN NULLIF(LTRIM(RTRIM(ISNULL(vs.BP, N''))), N'') IS NOT NULL
                THEN REPLACE(REPLACE(REPLACE(ISNULL(vs.BP, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
            WHEN vs.BPUpper IS NOT NULL AND vs.BPLower IS NOT NULL
                THEN CAST(vs.BPUpper AS nvarchar(10)) + N'/' + CAST(vs.BPLower AS nvarchar(10))
            ELSE N''
        END AS nvarchar(50)
    ) AS BloodPressure,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(vs.Pulse, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(50)
    ) AS Pulse,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(vs.Resp, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(50)
    ) AS Resp,
    CAST(ISNULL(CAST(vs.SPO2 AS nvarchar(50)), N'') AS nvarchar(50)) AS SPO2,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(vs.Wt, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(50)
    ) AS Wt,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(vs.Ht, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(50)
    ) AS Ht
FROM dbo.tblVitalSign vs
WHERE vs.VSID IS NOT NULL
ORDER BY vs.VSID ASC
""".strip()
