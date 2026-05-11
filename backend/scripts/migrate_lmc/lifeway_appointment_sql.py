"""
LIFEWAY tblOPDAppointment export: logical columns for migrate_lmc CSV + ODBC.

DoctorID is derived from ToSee (typically \"SURNAME, OTHER NAMES\") by matching
tblStaff (SurName + comma + OtherNames, case-insensitive, normalized commas)
then MIN(tblUsers.UserID) for that StaffID. Falls back to tblUsers.FullName
normalized the same way. Sender is clerical (e.g. \"Medical Records\") and is
not used for DoctorID.
"""

# Normalizes \"SURNAME, FIRST\" style strings for comparison.
_TOSEE_NORM = (
    "LOWER(LTRIM(RTRIM(REPLACE(REPLACE(ISNULL(a.ToSee, N''), N', ', N','), N' ,', N','))))"
)

LIFEWAY_OPD_APPOINTMENT_SELECT_BODY = f"""
    CAST(a.AppID AS int) AS AppointmentID,
    CAST(a.OutPatientID AS int) AS PatientID,
    CAST(ISNULL(a.Clinic, N'') AS nvarchar(50)) AS Clinic,
    CAST(
        COALESCE(
            (
                SELECT MIN(u.UserID)
                FROM dbo.tblStaff s
                INNER JOIN dbo.tblUsers u ON u.StaffID = s.StaffID
                WHERE LTRIM(RTRIM(ISNULL(a.ToSee, N''))) <> N''
                  AND LOWER(LTRIM(RTRIM(s.SurName))) + N',' + LOWER(LTRIM(RTRIM(ISNULL(s.OtherNames, N''))))
                      = {_TOSEE_NORM}
            ),
            (
                SELECT MIN(u.UserID)
                FROM dbo.tblUsers u
                WHERE LTRIM(RTRIM(ISNULL(a.ToSee, N''))) <> N''
                  AND LOWER(LTRIM(RTRIM(REPLACE(REPLACE(ISNULL(u.FullName, N''), N', ', N','), N' ,', N','))))
                      = {_TOSEE_NORM}
            )
        ) AS int
    ) AS DoctorID,
    CAST(a.[Date] AS datetime) AS AppointmentDate,
    CAST(a.[Status] AS nvarchar(50)) AS [Status],
    CAST(NULL AS int) AS VisitID,
    CAST(NULL AS nvarchar(max)) AS [Reason],
    CAST(NULL AS nvarchar(max)) AS [Notes],
    CAST(30 AS int) AS [Duration]
FROM dbo.tblOPDAppointment a
WHERE a.AppID IS NOT NULL
ORDER BY a.AppID ASC
""".strip()
