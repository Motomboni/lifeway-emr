/*
LMC legacy export queries for CSV-mode migration pipeline.

Target CSV files expected by the pipeline:
  - tblUsers.csv (staff; load before patients/appointments for legacy UserID -> Django user)
  - tblOutPatientRecord.csv
  - tblPatientVisits.csv
  - tblPatientPayment.csv
  - tblTempReceipt.csv
  - tblLabRequest.csv
  - tblLabResult.csv
  - tblRadRequest.csv
  - tblRadResult.csv
  - tblVitalSign.csv
  - tblOPDAppointment.csv
  - tblPhamDrugItem.csv
  - tblDrugPresItems.csv

Run these in SQL Server Management Studio against the legacy LIFEWAY DB,
then export each result grid to CSV (include column headers).
*/

USE [LIFEWAY];
GO

/* 0) tblUsers.csv — join tblStaff for designation / category / CanConsult */
SELECT
    CAST(u.UserID AS int) AS UserID,
    LTRIM(RTRIM(u.UserName)) AS UserName,
    LTRIM(RTRIM(ISNULL(u.FullName, N''))) AS FullName,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(u.Description, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(200)
    ) AS Description,
    CAST(ISNULL(u.Active, 1) AS int) AS Active,
    LTRIM(RTRIM(ISNULL(s.Designation, N''))) AS Designation,
    LTRIM(RTRIM(ISNULL(s.StaffCategory, N''))) AS StaffCategory,
    CAST(ISNULL(s.CanConsult, 0) AS int) AS CanConsult
FROM dbo.tblUsers u
LEFT JOIN dbo.tblStaff s ON s.StaffID = u.StaffID
WHERE u.UserName IS NOT NULL AND LTRIM(RTRIM(u.UserName)) <> N''
ORDER BY u.UserID ASC;
GO

/* 1) tblOutPatientRecord.csv */
SELECT
    CAST(OutPatientID AS int) AS PatientID,
    CAST(SurName AS nvarchar(255)) AS Surname,
    CAST(OtherNames AS nvarchar(255)) AS Othernames,
    CAST(Sex AS nvarchar(20)) AS Sex,
    CAST(DateOfBirth AS datetime) AS DOB,
    CAST(COALESCE(HomeTel, OfficeTel, NextOfKinTel, N'') AS nvarchar(50)) AS PhoneNo,
    CAST(Email AS nvarchar(255)) AS Email,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(HomeAddress, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS Address
FROM dbo.tblOutPatientRecord
WHERE OutPatientID IS NOT NULL
ORDER BY OutPatientID ASC;
GO

/* 2) tblPatientVisits.csv — ClinicName + OP narrative; see migrate_lmc/lifeway_patient_visits_sql.py */
SELECT
    CAST(v.visitID AS int) AS VisitID,
    CAST(v.OutPatientID AS int) AS PatientID,
    CAST(v.ClinicID AS int) AS ClinicID,
    CAST(ISNULL(ci.Name, N'') AS nvarchar(255)) AS ClinicName,
    CAST(v.[Date] AS datetime) AS [Date],
    CAST(N'CONSULTATION' AS nvarchar(50)) AS VisitType,
    CAST(N'OPEN' AS nvarchar(50)) AS [Status],
    CAST(N'UNPAID' AS nvarchar(50)) AS PaymentStatus,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(v.Complaint, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS ChiefComplaint,
    CAST(NULL AS nvarchar(max)) AS [Reason],
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(v.Notes, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS VisitNotes,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(v.HPC, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS HPC,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(v.PMH, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS PMH,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(v.FHx, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS FHx,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(v.Exam, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS Exam,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(v.Assesment, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS Assessment,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(v.TreatPlan, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS TreatPlan,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(v.[results], N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS ResultsText,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(v.Treatment, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS Treatment,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(v.Summary, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS Summary,
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
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(v.IMH, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS IMH,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(v.DH, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS DH,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(v.Weight, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS Weight,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(v.Temperature, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS Temperature,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(v.Doctor, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(100)
    ) AS LegacyDoctor
FROM dbo.tblPatientVisits v
LEFT JOIN dbo.tblChargeItem ci ON ci.ChargeItemID = v.ClinicID
WHERE v.visitID IS NOT NULL
ORDER BY v.visitID ASC;
GO

/* 1b) tblPatientPayment.csv — legacy patient payments; see migrate_lmc/lifeway_patient_payment_sql.py */
SELECT
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
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(CAST(p.Service AS nvarchar(max)), N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS ServiceLine,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(p.Diagnosis, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS DiagnosisLine,
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
ORDER BY p.PatientPayID ASC;
GO

/* 1c) tblTempReceipt.csv — POS receipt lines (tblTempReceipt + tblReceiptGrid); see migrate_lmc/lifeway_temp_receipt_sql.py */
SELECT
    CAST(tr.ID AS int) AS TempReceiptID,
    CAST(tr.ReceiptID AS int) AS GridReceiptID,
    CAST(ISNULL(rg.ReceiptNo, 0) AS int) AS ReceiptNo,
    CAST(rg.PatientID AS int) AS PatientID,
    CAST(rg.[Date] AS datetime) AS LineDate,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(CAST(tr.Service AS nvarchar(max)), N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS ServiceLine,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(tr.FieldName, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS FieldName,
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
ORDER BY tr.ID ASC;
GO

/* 2a) tblLabRequest.csv — TestsRequested = STRING_AGG(TestName) from details + tblLabTest; see migrate_lmc/lifeway_lab_request_sql.py */
SELECT
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
    CAST(ISNULL((
        SELECT STRING_AGG(
            LTRIM(RTRIM(
                REPLACE(REPLACE(REPLACE(ISNULL(t.TestName, N''), N'|', N'/'), CHAR(10), N' '), CHAR(13), N' ')
            )),
            N'|'
        ) WITHIN GROUP (ORDER BY d.LabRequestDetailsID)
        FROM dbo.tblLabRequestDetails d
        LEFT JOIN dbo.tblLabTest t ON t.TestID = d.TestID
        WHERE d.RequestID = r.RequestID
          AND LTRIM(RTRIM(ISNULL(t.TestName, N''))) <> N''
    ), N'') AS nvarchar(max)) AS TestsRequested
FROM dbo.tblLabRequest r
WHERE r.RequestID IS NOT NULL
ORDER BY r.RequestID ASC;
GO

/* 2a2) tblLabResult.csv — one row per RequestID; detail lines STRING_AGG from tblLabResultDetails; see migrate_lmc/lifeway_lab_result_sql.py */
SELECT
    CAST(r.RequestID AS int) AS RequestID,
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
    CAST(ISNULL((
        SELECT STRING_AGG(x.line, N' | ') WITHIN GROUP (ORDER BY x.rid, x.lid)
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
    ), N'') AS nvarchar(max)) AS ResultData
FROM dbo.tblLabResult r
WHERE r.RequestID IS NOT NULL AND r.RequestID <> 0
GROUP BY r.RequestID
ORDER BY r.RequestID ASC;
GO

/* 2a3) tblRadRequest.csv — investigations aggregated from details + charge items; see migrate_lmc/lifeway_radiology_request_sql.py */
SELECT
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
ORDER BY r.RequestID ASC;
GO

/* 2a4) tblRadResult.csv — report text aggregated from tblRadResult.RTBNotes; see migrate_lmc/lifeway_radiology_result_sql.py */
SELECT
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
ORDER BY r.RequestID ASC;
GO

/* 2b) tblVitalSign.csv — VisitID resolved from same-day tblPatientVisits; see migrate_lmc/lifeway_vital_sign_sql.py */
SELECT
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
ORDER BY vs.VSID ASC;
GO

/* 3) tblOPDAppointment.csv — Clinic (OPD area); DoctorID from ToSee; see migrate_lmc/lifeway_appointment_sql.py */
SELECT
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
                      = LOWER(LTRIM(RTRIM(REPLACE(REPLACE(ISNULL(a.ToSee, N''), N', ', N','), N' ,', N','))))
            ),
            (
                SELECT MIN(u.UserID)
                FROM dbo.tblUsers u
                WHERE LTRIM(RTRIM(ISNULL(a.ToSee, N''))) <> N''
                  AND LOWER(LTRIM(RTRIM(REPLACE(REPLACE(ISNULL(u.FullName, N''), N', ', N','), N' ,', N','))))
                      = LOWER(LTRIM(RTRIM(REPLACE(REPLACE(ISNULL(a.ToSee, N''), N', ', N','), N' ,', N','))))
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
ORDER BY a.AppID ASC;
GO

/* 4) tblPhamDrugItem.csv (drug catalog; Sell/Cost aligned with migrate_lmc load.py) */
SELECT
    CAST(DrugItemID AS int) AS DrugItemID,
    CAST(REPLACE(REPLACE(REPLACE(ISNULL(Name, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ') AS nvarchar(255)) AS DrugName,
    CAST(ISNULL(Sell, Cost) AS decimal(18, 2)) AS UnitPrice,
    CAST(Cost AS decimal(18, 2)) AS Cost
FROM dbo.tblPhamDrugItem
WHERE DrugItemID IS NOT NULL AND LTRIM(RTRIM(ISNULL(Name, N''))) <> N''
ORDER BY DrugItemID ASC;
GO

/* 4b) tblDrugPresItems.csv — prescription lines; see migrate_lmc/lifeway_drug_prescription_lines_sql.py */
SELECT
    CAST(i.PresItemID AS int) AS PresItemID,
    CAST(i.PrescriptionID AS int) AS PrescriptionID,
    CAST(p.PatientID AS int) AS PatientID,
    CAST(p.[Date] AS datetime) AS PrescriptionDate,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(p.Sender, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(100)
    ) AS Sender,
    CAST(i.DrugItemID AS int) AS DrugItemID,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(d.Name, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS DrugName,
    CAST(i.QtyIssued AS int) AS QtyIssued,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(i.Notes, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS ItemNotes
FROM dbo.tblDrugPresItems i
INNER JOIN dbo.tblDrugPrescription p ON p.PrescriptionID = i.PrescriptionID
LEFT JOIN dbo.tblPhamDrugItem d ON d.DrugItemID = i.DrugItemID
WHERE i.PresItemID IS NOT NULL
ORDER BY i.PresItemID ASC;
GO

