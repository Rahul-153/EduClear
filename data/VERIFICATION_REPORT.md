# EduClear — Dataset Verification Report

Generated 2026-11-06 by `scripts/make_report.py`. Sources: NIRF India Rankings 2025 (Engineering), JoSAA 2025 Round 6 archive, institute fee circulars, placement reports and annual reports saved under `data/sources/<id>/` with SHA-256 in each record.

## Summary

| College | NIRF rank | 4-yr cost (₹) | Median base (LPA) | Headline (LPA) | Placed / Eligible | Rate | Cutoff exam | 2nd-pass |
|---|---|---|---|---|---|---|---|---|
| BITS Pilani | 11 | 2,866,800 | 18.0 | 65 | 2,458 / 2,476 | 99.27% | BITSAT | VERIFIED |
| DTU Delhi | 30 | 1,673,000 | 13.25 | 85.03 | 1,759 / 1,759 | 100.0% | JEE Main (All India Over All Rank) via JAC Delhi | VERIFIED |
| IIT BHU | 10 | 1,140,552 | 20.0 | 165.0 | 996 / 998 | 99.8% | JEE Advanced | VERIFIED |
| IIT Guwahati | 8 | 1,300,400 | 19.48 | 205.0 | 658 / 677 | 97.19% | JEE Advanced | VERIFIED |
| IIT Hyderabad | 7 | 1,455,392 | 21.0 | 90 | 306 / 362 | 84.53% | JEE Advanced | VERIFIED |
| MNIT Jaipur | 42 | 1,110,348 | 11.0 | 64 | 603 / 715 | 84.34% | JEE Main | VERIFIED |
| NIT Calicut | 21 | 1,163,500 | 12.5 | 47 | 799 / 826 | 96.73% | JEE Main | VERIFIED after correction (see notes) |

## Gate results

Run `npm run validate:data`: all 6 manual gates + extra audit checks (snapshots hashed, provenance for key fields, D-09 eligibility).

## Birla Institute of Technology & Science, Pilani (`bits-pilani`)

- NIRF year 2025, retrieved 2026-11-06, fee circular: April 2026
- Cutoff: BITSAT 2026 (Academic Year 2026-2027 admission session) 'final BITSAT cut-off scores' (page does not label a round): B.E. Computer Science: 308 (BITSAT maximum marks 390). Score, not rank. Prior sessions on same page (Pilani B.E. CS): 2025-26 = 304/390. (Pilani campus)
- Accreditation: BITS, Pilani has been accredited by the National Assessment & Accreditation Council (NAAC) with 'A++' grade with a CGPA of 3.68 on a four point scale in the fourth cycle for five years, from 29th November 2024 to 28th November 2029. NBA status: not found.
- Audit note: NIRF 2025 UG 4-year batch graduating 2023-24: 2,759 graduated, 283 to higher studies, 2,458 placed of 2,476 eligible. Median Rs 1,800,000. Headline CTC: Pilani Campus, 2023-24, Maximum Salary (Domestic) printed as 6500000 INR (=65 LPA). Sheet does not say whether CTC or base, and gives no international maximum (not found in this sheet). Prior years in same sheet: 90 LPA (2021-22), 70 LPA (2022-23).

| Field | Source URL | Locator | Snapshot (SHA-256 prefix) |
|---|---|---|---|
| placement.batchSize | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0391.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: students graduating in minimum stipulated time | nirf-2025-dcs.pdf (a02f3395ad) |
| placement.eligibleStudents | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0391.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: graduating minus students selected for higher studies (D-09) | nirf-2025-dcs.pdf (a02f3395ad) |
| placement.actuallyPlaced | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0391.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: no. of students placed | nirf-2025-dcs.pdf (a02f3395ad) |
| placement.medianBaseSalary | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0391.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: median salary of placed graduates per annum | nirf-2025-dcs.pdf (a02f3395ad) |
| placement.headlineCTC | https://www.bits-pilani.ac.in/wp-content/uploads/Pilani-Placement-Statistics-03-06-2025.pdf | Page 1, row 'Maximum Salary ( Domestic)', column 2023-24 = 6500000 | pilani-placement-statistics.pdf (441fd19b23) |
| fees.tuitionAnnual | https://www.bitsadmission.com/FD/FD_fee.html | Page 'Schedule of Fees for the academic year 2026-27', Pilani Campus column, First Degree programmes (B.E., M.Sc., B.Pharm.) | fd-fee.html (009996fb57) |
| fees.hostelAndMessAnnual | https://www.bitsadmission.com/FD/FD_fee.html | Page 'Schedule of Fees for the academic year 2026-27', Pilani Campus column, First Degree programmes (B.E., M.Sc., B.Pharm.) | fd-fee.html (009996fb57) |
| fees.mandatoryInstituteFeesAnnual | https://www.bitsadmission.com/FD/FD_fee.html | Page 'Schedule of Fees for the academic year 2026-27', Pilani Campus column, First Degree programmes (B.E., M.Sc., B.Pharm.) | fd-fee.html (009996fb57) |
| fees.estimatedLivingAnnual | https://doe.gov.in/files/circulars_document/7th_July_2017.pdf | HRA class Z for Pilani (Jhunjhunu district, Rajasthan); band midpoint per D-19 | hra-doe-om-2017-07-07.pdf (ce31b4b4c5) |
| cutoffs.minPercentileOrRank | https://www.bitsadmission.com/FD/BITSAT_cutOffs.html | Section 'BITSAT Cut-off Scores for Academic Year 2026-2027', Pilani, B.E. Computer Science | bitsat-cutoffs.html (88a35a2e10) |
| nirfRank | https://www.nirfindia.org/Rankings/2025/EngineeringRanking.html | NIRF 2025 Engineering ranking table | nirf-2025-engineering-ranking.html (a7e29ec5af) |
| accreditation | https://www.bits-pilani.ac.in/awardsandaccreditations | NAAC Accreditation section | awards-and-accreditations.html (dc2095f932) |

Second-pass: 21 checks, 0 mismatch(es) recorded in `verification.json`.

## Delhi Technological University (`dtu-delhi`)

- NIRF year 2025, retrieved 2026-11-06, fee circular: May 2026
- Cutoff: JEE Main (All India Over All Rank) via JAC Delhi 2026 Round 4 (14/07/2026) - last regular round in JAC Delhi 2026 schedule; spot rounds followed: Delhi Region GNGND 14806 (GNGLD 20396); Outside Delhi Region GNGNO 7060 (GNGLO 8100). For reference 2025 Round 5 (15/07/2025): Delhi GNGND 11352 (GNGLD 15118); Outside Delhi GNGNO 6200 (GNGLO 6391). (Delhi Region and Outside Delhi Region)
- Accreditation: NAAC: Accredited with 'A+' Grade (CGPA 3.47 out of 4.0 by NAAC) per DTU B.Tech Continuing Education brochure 2026-27; DTU International Admission Brochure 2026-27 prints 'A+' Grade (CGPA 3.22 out of 4.0) - CGPA differs between DTU documents. NBA: 'At present 6 UG programs and 9 PG programs are accredited by NBA at DTU' (programme-level NBA status for Computer Engineering not stated).
- Audit note: NIRF 2025 UG 4-year batch graduating 2023-24: 2,412 graduated, 653 to higher studies, 1,759 placed of 1,759 eligible. Median Rs 1,325,000. Headline CTC: Institute-wide highest package for session 2023-24 as printed: 'Highest Package Rs. 85.03 LPA (offered by Atlassian)'; 360 companies, 2053 offers, average Rs. 15 LPA. CTC vs base and domestic/international not stated. Other official DTU docs print 85.3 LPA (tnp.dtu.ac.in 2023-24 highlights PDF, B.Tech COE/MCE/ECE max CTC 85.3; CSE dept page: 85.3 LPA Atlassian, window 1 Aug 2023-31 Jul 2024); 85.03 vs 85.3 discrepancy is in DTU's own documents.

| Field | Source URL | Locator | Snapshot (SHA-256 prefix) |
|---|---|---|---|
| placement.batchSize | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0098.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: students graduating in minimum stipulated time | nirf-2025-dcs.pdf (76d7480b8b) |
| placement.eligibleStudents | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0098.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: graduating minus students selected for higher studies (D-09) | nirf-2025-dcs.pdf (76d7480b8b) |
| placement.actuallyPlaced | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0098.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: no. of students placed | nirf-2025-dcs.pdf (76d7480b8b) |
| placement.medianBaseSalary | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0098.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: median salary of placed graduates per annum | nirf-2025-dcs.pdf (76d7480b8b) |
| placement.headlineCTC | https://www.dtu.ac.in/Web/publications/pdf/convo_24.pdf | 11th Convocation booklet (Dec 2024), 'PLACEMENTS 2023-24' table (PDF page 50) and Vice-Chancellor message | dtu-convocation-2024-booklet.pdf (d79df5c5a1) |
| fees.tuitionAnnual | https://cdnbbsr.s3waas.gov.in/s3e45823afe1e5120cec11fc4c379a0c67/uploads/2026/05/202605261990309362.pdf | JAC Delhi 2026 brochure Ch.6 Fee Structures (p.73-74); DTU Lateral Entry 2026 brochure p.18 table; hostel allotment policy 2026-27 sec 4.2; hostels.dtu.ac.in/fee.html | jac-delhi-2026-admission-brochure.pdf (8af2e346f7) |
| fees.hostelAndMessAnnual | https://cdnbbsr.s3waas.gov.in/s3e45823afe1e5120cec11fc4c379a0c67/uploads/2026/05/202605261990309362.pdf | JAC Delhi 2026 brochure Ch.6 Fee Structures (p.73-74); DTU Lateral Entry 2026 brochure p.18 table; hostel allotment policy 2026-27 sec 4.2; hostels.dtu.ac.in/fee.html | jac-delhi-2026-admission-brochure.pdf (8af2e346f7) |
| fees.mandatoryInstituteFeesAnnual | https://cdnbbsr.s3waas.gov.in/s3e45823afe1e5120cec11fc4c379a0c67/uploads/2026/05/202605261990309362.pdf | JAC Delhi 2026 brochure Ch.6 Fee Structures (p.73-74); DTU Lateral Entry 2026 brochure p.18 table; hostel allotment policy 2026-27 sec 4.2; hostels.dtu.ac.in/fee.html | jac-delhi-2026-admission-brochure.pdf (8af2e346f7) |
| fees.estimatedLivingAnnual | https://doe.gov.in/files/circulars_document/7th_July_2017.pdf | HRA class X for Delhi; band midpoint per D-19 | hra-doe-om-2017-07-07.pdf (ce31b4b4c5) |
| cutoffs.minPercentileOrRank | https://cdnbbsr.s3waas.gov.in/s3e45823afe1e5120cec11fc4c379a0c67/uploads/2026/07/20260715952726882.pdf | DTU 'Category Cutoff Round 4 (14/07/2026)', row 1 Computer Science and Engineering, Delhi Region table and Outside Delhi Region table | jac-delhi-2026-dtu-round4-cutoff.pdf (f1ee213182) |
| nirfRank | https://www.nirfindia.org/Rankings/2025/EngineeringRanking.html | NIRF 2025 Engineering ranking table | nirf-2025-engineering-ranking.html (a7e29ec5af) |
| accreditation | https://dtu.ac.in/Web/upload/admissions/2026/Admission_Brochue_btechce_2026.pdf | Cover and Section 4 'Accreditations'; international brochure cover | dtu-btech-continuing-ed-brochure-2026-27.pdf (97c73404d1) |

Second-pass: 20 checks, 0 mismatch(es) recorded in `verification.json`.

## Indian Institute of Technology (BHU) Varanasi (`iit-bhu`)

- NIRF year 2025, retrieved 2026-11-06, fee circular: 2 July 2025 (publication date on IIT (BHU) fresher news page; PDF itself prints no date, PDF metadata created 2 Jul 2025)
- Cutoff: JoSAA 2025 Round 6, CSE (4-yr B.Tech), OPEN, Gender-Neutral, All-India quota: opening AIR 747, closing AIR 1489 (JEE Advanced rank)
- Accreditation: Not stated in official sources reviewed
- Audit note: NIRF 2025 UG 4-year batch graduating 2023-24: 1,073 graduated, 75 to higher studies, 996 placed of 998 eligible. Median Rs 2,000,000. Headline CTC: AMBIGUITY: two official own-domain newsletters. Jan 2024 newsletter (alumni-newsletter-2024-jan.pdf, p.1 'Internship/Placement Updates') explicitly states for session 2023-24, as of 1 Feb 2024: 1044 offers incl. 11 international, 'highest offered CTC Rs. 1.68 crores' (168 LPA). Dec 2024 newsletter says 1.65 crore as of 30 Dec 2024 but does NOT tie it to a season (Dec 2024 is within the 2024-25 season, so likely different season). Lower official figure used per D-23 (165 LPA) although season attribution of the Dec figure is unclear; the only explicitly 2023-24-labelled figure is 168 LPA. CTC, not stated domestic/international, partial-season snapshot. Caller may prefer 168 LPA.

| Field | Source URL | Locator | Snapshot (SHA-256 prefix) |
|---|---|---|---|
| placement.batchSize | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0701.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: students graduating in minimum stipulated time | nirf-2025-dcs.pdf (0d486ec19d) |
| placement.eligibleStudents | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0701.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: graduating minus students selected for higher studies (D-09) | nirf-2025-dcs.pdf (0d486ec19d) |
| placement.actuallyPlaced | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0701.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: no. of students placed | nirf-2025-dcs.pdf (0d486ec19d) |
| placement.medianBaseSalary | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0701.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: median salary of placed graduates per annum | nirf-2025-dcs.pdf (0d486ec19d) |
| placement.headlineCTC | https://iitbhu.ac.in/contents/institute/dean/dora/doc/alumni_newsletter_2024_dec.pdf | Alma Communique Dec 2024, Internship/Placement Updates: 'maximum placement package offered was Rs. 1.65 crore per annum' (as of 30 Dec 2024) | alumni-newsletter-2024-dec.pdf (64a318efd1) |
| fees.tuitionAnnual | https://iitbhu.ac.in/sites/default/files/institute/academics/fresher/doc/fee_structure_2025-26.pdf | Fee structure PDF p.1 table sections A, C, D and footnote Note on Mess Advance | fee-structure-2025-26.pdf (f1cfa2581f) |
| fees.hostelAndMessAnnual | https://iitbhu.ac.in/sites/default/files/institute/academics/fresher/doc/fee_structure_2025-26.pdf | Fee structure PDF p.1 table sections A, C, D and footnote Note on Mess Advance | fee-structure-2025-26.pdf (f1cfa2581f) |
| fees.mandatoryInstituteFeesAnnual | https://iitbhu.ac.in/sites/default/files/institute/academics/fresher/doc/fee_structure_2025-26.pdf | Fee structure PDF p.1 table sections A, C, D and footnote Note on Mess Advance | fee-structure-2025-26.pdf (f1cfa2581f) |
| fees.estimatedLivingAnnual | https://doe.gov.in/files/circulars_document/21_07_2015.pdf | HRA class Y for Varanasi; band midpoint per D-19 | doe-hra-cities-classification-om-2015-07-21.pdf (38b935a849) |
| cutoffs.minPercentileOrRank | https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx | JoSAA Opening & Closing Rank Archive 2025, Round 6, filtered to CSE 4-yr B.Tech, OPEN, Gender-Neutral | josaa-2025-round6.html (10412b2e54) |
| nirfRank | https://www.nirfindia.org/Rankings/2025/EngineeringRanking.html | NIRF 2025 Engineering ranking table | nirf-2025-engineering-ranking.html (a7e29ec5af) |
| accreditation | https://www.nirfindia.org/ | No NAAC grade or NBA status found in official IIT documents reached (placement/fee/NIRF DCS) or via search of institute domain; not asserted | nirf-2025-dcs.pdf (0d486ec19d) |

Second-pass: 20 checks, 0 mismatch(es) recorded in `verification.json`.

## Indian Institute of Technology Guwahati (`iit-guwahati`)

- NIRF year 2025, retrieved 2026-11-06, fee circular: not printed (IIT Guwahati admission fee page, retrieved 2026-11-06; page shows COAP 2026 / PhD Dec 2026 links, so it appears current)
- Cutoff: JoSAA 2025 Round 6, CSE (4-yr B.Tech), OPEN, Gender-Neutral, All-India quota: opening AIR 504, closing AIR 792 (JEE Advanced rank)
- Accreditation: Not stated in official sources reviewed
- Audit note: NIRF 2025 UG 4-year batch graduating 2023-24: 856 graduated, 179 to higher studies, 658 placed of 677 eligible. Median Rs 1,948,000. Headline CTC: Placement Report AY 2023-24 (Centre for Career Development, July 2024). CTC as printed; report does not state domestic vs international or whether the figure is total or base, so ambiguity unresolved. No other official 2023-24 figure checked.

| Field | Source URL | Locator | Snapshot (SHA-256 prefix) |
|---|---|---|---|
| placement.batchSize | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0053.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: students graduating in minimum stipulated time | nirf-2025-dcs.pdf (4eec514360) |
| placement.eligibleStudents | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0053.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: graduating minus students selected for higher studies (D-09) | nirf-2025-dcs.pdf (4eec514360) |
| placement.actuallyPlaced | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0053.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: no. of students placed | nirf-2025-dcs.pdf (4eec514360) |
| placement.medianBaseSalary | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0053.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: median salary of placed graduates per annum | nirf-2025-dcs.pdf (4eec514360) |
| placement.headlineCTC | https://iitg.ac.in/ccd/assets/docs/reports/Placement_reports_2023_24.pdf | p.2 'Highlights of Placement Season 2023-24', row 'Highest Salary Offered (CTC): Rs. 2.05 Crore' | placement-report-2023-24.pdf (d163661b5d) |
| fees.tuitionAnnual | https://iitg.ac.in/acad/admission/imp_info/fee.php | Page sections 'Fee Structure' A, B, C and 'Tuition Fees (per semester)' table | fee-structure-page.html (59becb57f8) |
| fees.hostelAndMessAnnual | https://iitg.ac.in/acad/admission/imp_info/fee.php | Page sections 'Fee Structure' A, B, C and 'Tuition Fees (per semester)' table | fee-structure-page.html (59becb57f8) |
| fees.mandatoryInstituteFeesAnnual | https://iitg.ac.in/acad/admission/imp_info/fee.php | Page sections 'Fee Structure' A, B, C and 'Tuition Fees (per semester)' table | fee-structure-page.html (59becb57f8) |
| fees.estimatedLivingAnnual | https://doe.gov.in/files/circulars_document/21_07_2015.pdf | HRA class Y for Guwahati; band midpoint per D-19 | doe-hra-cities-classification-om-2015-07-21.pdf (38b935a849) |
| cutoffs.minPercentileOrRank | https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx | JoSAA Opening & Closing Rank Archive 2025, Round 6, filtered to CSE 4-yr B.Tech, OPEN, Gender-Neutral | josaa-2025-round6.html (06310cfb80) |
| nirfRank | https://www.nirfindia.org/Rankings/2025/EngineeringRanking.html | NIRF 2025 Engineering ranking table | nirf-2025-engineering-ranking.html (a7e29ec5af) |
| accreditation | https://www.nirfindia.org/ | No NAAC grade or NBA status found in official IIT documents reached (placement/fee/NIRF DCS) or via search of institute domain; not asserted | nirf-2025-dcs.pdf (4eec514360) |

Second-pass: 16 checks, 0 mismatch(es) recorded in `verification.json`.

## Indian Institute of Technology Hyderabad (`iit-hyderabad`)

- NIRF year 2025, retrieved 2026-11-06, fee circular: not printed (file name of the circular carries '15.05'; inferred 15 May 2026, not printed in the document)
- Cutoff: JoSAA 2025 Round 6, CSE (4-yr B.Tech), OPEN, Gender-Neutral, All-India quota: opening AIR 339, closing AIR 673 (JEE Advanced rank)
- Accreditation: NAAC: institute states it has no valid NAAC accreditation (NIRF 2025 data submitted by institute: 'valid NAAC Accreditation? NO'). NBA: no official statement found.
- Audit note: NIRF 2025 UG 4-year batch graduating 2023-24: 399 graduated, 37 to higher studies, 306 placed of 362 eligible. Median Rs 2,100,000. Headline CTC: Institute-wide highest annual package 2023-24 as printed by Office of Career Services; not labelled CTC vs base, not labelled domestic vs international (43 international offers made in total). Both official documents agree on 90. Other doc saved: annual-report-2023-24.pdf.

| Field | Source URL | Locator | Snapshot (SHA-256 prefix) |
|---|---|---|---|
| placement.batchSize | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0013.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: students graduating in minimum stipulated time | nirf-2025-dcs.pdf (afd57ead57) |
| placement.eligibleStudents | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0013.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: graduating minus students selected for higher studies (D-09) | nirf-2025-dcs.pdf (afd57ead57) |
| placement.actuallyPlaced | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0013.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: no. of students placed | nirf-2025-dcs.pdf (afd57ead57) |
| placement.medianBaseSalary | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0013.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: median salary of placed graduates per annum | nirf-2025-dcs.pdf (afd57ead57) |
| placement.headlineCTC | https://ocs.iith.ac.in/static/media/Placement-Stats-23-24.2b81e8ea.pdf | Placement Statistics 2023-24 p.1 'Highest Annual Package (in Lakhs) 90'; B.Tech highest 90 LPA (p.2). Agrees with Annual Report 2023-24: 'Highest Package: Rs 90.00 Lakhs' (pr.iith.ac.in/reports/annual/IITH-AR-2023-24.pdf, Placement section) | placement-stats-2023-24.pdf (83fc62dc8a) |
| fees.tuitionAnnual | https://iith.ac.in/academics/assets/files/fee/2026/jan-jun-2026/Fee_Structure_Jul-Dec2026Semester_15.05-1.pdf | IIT Hyderabad Fee Structure for the Semester July-December 2026, 'UG Newly Enrolled Students in July 2026', GEN/OBC column (p.2); items 1.1-1.3, 2.1-2.5, 3.1; mess note 1 | fee-structure-jul-dec-2026.pdf (d08372cc5a) |
| fees.hostelAndMessAnnual | https://iith.ac.in/academics/assets/files/fee/2026/jan-jun-2026/Fee_Structure_Jul-Dec2026Semester_15.05-1.pdf | IIT Hyderabad Fee Structure for the Semester July-December 2026, 'UG Newly Enrolled Students in July 2026', GEN/OBC column (p.2); items 1.1-1.3, 2.1-2.5, 3.1; mess note 1 | fee-structure-jul-dec-2026.pdf (d08372cc5a) |
| fees.mandatoryInstituteFeesAnnual | https://iith.ac.in/academics/assets/files/fee/2026/jan-jun-2026/Fee_Structure_Jul-Dec2026Semester_15.05-1.pdf | IIT Hyderabad Fee Structure for the Semester July-December 2026, 'UG Newly Enrolled Students in July 2026', GEN/OBC column (p.2); items 1.1-1.3, 2.1-2.5, 3.1; mess note 1 | fee-structure-jul-dec-2026.pdf (d08372cc5a) |
| fees.estimatedLivingAnnual | https://doe.gov.in/files/circulars_document/21_07_2015.pdf | HRA class X for Hyderabad (UA); band midpoint per D-19 | doe-hra-om-2015-07-21.pdf (38b935a849) |
| cutoffs.minPercentileOrRank | https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx | JoSAA Opening & Closing Rank Archive 2025, Round 6, filtered to CSE 4-yr B.Tech, OPEN, Gender-Neutral | josaa-2025-round6.html (f82024bd95) |
| nirfRank | https://www.nirfindia.org/Rankings/2025/EngineeringRanking.html | NIRF 2025 Engineering ranking table | nirf-2025-engineering-ranking.html (a7e29ec5af) |
| accreditation | https://iith.ac.in/assets/files/NIRF-Reports/2025/Indian_Institute_of_Technology_Hyderabad_Overall_2025.pdf | NIRF 2025 Overall report, Accreditation > NAAC Accreditation, question 1: NO | nirf-2025-overall.pdf (53c30cd02a) |

Second-pass: 20 checks, 0 mismatch(es) recorded in `verification.json`.

## Malaviya National Institute of Technology Jaipur (`mnit-jaipur`)

- NIRF year 2025, retrieved 2026-11-06, fee circular: not printed (fee structure PDF carries no date; inferred from the institute upload path /cms/uploads/2026/05/ i.e. May 2026; hostel circular is dated 25/03/2026)
- Cutoff: JoSAA 2025 Round 6, CSE (4-yr B.Tech), OPEN, Gender-Neutral: Other State closing AIR 5601 (opening 3027); Home State closing AIR 6013 (opening 2937) (JEE Main rank)
- Accreditation: NAAC: not found in any official document retrieved (null). NBA: official MNIT list 'List of UG Programmes NBA Accredited or Applied for Accreditation as on 02.08.22' shows B.Tech Computer Science & Engineering: '3 YEARS W.E.F.19-07-2008', remark 'Currently Not Accredited', action 'Department need to submit SAR for first cycle of Accreditation'. This list is dated Aug 2022 and may be outdated.
- Audit note: NIRF 2025 UG 4-year batch graduating 2023-24: 733 graduated, 18 to higher studies, 603 placed of 715 eligible. Median Rs 1,100,000. Headline CTC: Institute-wide UG highest, 2023-24 placement report, as printed in LPA (CTC/domestic-vs-international not specified in the document). Corroborated by Annual Report 2023-24 (saved as mnit-annual-report-2023-24.pdf, https://www.mnit.ac.in/uploads/Annual_Report/2023-24_Eng.pdf): 'highest package for UG being INR 64 lakh and PG INR 48 lakh'. Ambiguity: PG highest differs (placement report chart 33.06 LPA vs annual report 48 lakh); the lower PG figure is not relevant to the B.Tech headline. The report's 'Salient Features' heading reads 'Session 2022-23' (apparent typo in a report titled 2023-24).

| Field | Source URL | Locator | Snapshot (SHA-256 prefix) |
|---|---|---|---|
| placement.batchSize | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0410.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: students graduating in minimum stipulated time | nirf-2025-dcs.pdf (a9e9fe4001) |
| placement.eligibleStudents | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0410.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: graduating minus students selected for higher studies (D-09) | nirf-2025-dcs.pdf (a9e9fe4001) |
| placement.actuallyPlaced | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0410.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: no. of students placed | nirf-2025-dcs.pdf (a9e9fe4001) |
| placement.medianBaseSalary | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0410.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: median salary of placed graduates per annum | nirf-2025-dcs.pdf (a9e9fe4001) |
| placement.headlineCTC | https://placements.mnit.ac.in/public/assets/docs/PlacementReport2023-24.pdf | UG Placement Statistics table, TOTAL row, Highest (LPA) = 64 (also CSE row 64); chart 'Package Details (UG)' Maximum 64 | mnit-placement-report-2023-24.pdf (6ce499315d) |
| fees.tuitionAnnual | https://www.mnit.ac.in/cms/uploads/2026/05/Fee_UG_2026-27.pdf | mnit-fee-ug-2026-27.pdf page 1 'Fee Structure for B. Tech. students admitted in the session 2026-27' (Tuition, Institute Fee A-D, Notes); hostel: mnit-hostel-fee-mess-advance-2026-27.pdf page 1 table | mnit-fee-ug-2026-27.pdf (f9fd24aaff) |
| fees.hostelAndMessAnnual | https://www.mnit.ac.in/cms/uploads/2026/05/Fee_UG_2026-27.pdf | mnit-fee-ug-2026-27.pdf page 1 'Fee Structure for B. Tech. students admitted in the session 2026-27' (Tuition, Institute Fee A-D, Notes); hostel: mnit-hostel-fee-mess-advance-2026-27.pdf page 1 table | mnit-fee-ug-2026-27.pdf (f9fd24aaff) |
| fees.mandatoryInstituteFeesAnnual | https://www.mnit.ac.in/cms/uploads/2026/05/Fee_UG_2026-27.pdf | mnit-fee-ug-2026-27.pdf page 1 'Fee Structure for B. Tech. students admitted in the session 2026-27' (Tuition, Institute Fee A-D, Notes); hostel: mnit-hostel-fee-mess-advance-2026-27.pdf page 1 table | mnit-fee-ug-2026-27.pdf (f9fd24aaff) |
| fees.estimatedLivingAnnual | Department of Expenditure OM dated 07.07.2017 on HRA city classification (saved copy hra-doe-om-2017-07-07.pdf; original URL not re-verified) | HRA class Y for Jaipur; band midpoint per D-19 | hra-doe-om-2017-07-07.pdf (ce31b4b4c5) |
| cutoffs.minPercentileOrRank | https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx | JoSAA Opening & Closing Rank Archive 2025, Round 6, filtered to CSE 4-yr B.Tech, OPEN, Gender-Neutral | josaa-2025-round6.html (6e3efcaf23) |
| nirfRank | https://www.nirfindia.org/Rankings/2025/EngineeringRanking.html | NIRF 2025 Engineering ranking table | nirf-2025-engineering-ranking.html (a7e29ec5af) |
| accreditation | https://www.mnit.ac.in/cms/uploads/2022/08/AccrditationStatus.pdf | UG list, row 3 B.Tech - Computer Science & Engineering | mnit-nba-accreditation-status-2022-08.pdf (fd855059fb) |

Second-pass: 16 checks, 0 mismatch(es) recorded in `verification.json`.

## National Institute of Technology Calicut (`nit-calicut`)

- NIRF year 2025, retrieved 2026-11-06, fee circular: not printed
- Cutoff: JoSAA 2025 Round 6, CSE (4-yr B.Tech), OPEN, Gender-Neutral: Other State closing AIR 5222 (opening 3651); Home State closing AIR 8428 (opening 2998) (JEE Main rank)
- Accreditation: NBA: B.Tech Computer Science & Engineering accredited for 6 years (2022-2028), the maximum NBA status (press release 13-12-2022). NAAC grade not found in official sources reviewed.
- Audit note: NIRF 2025 UG 4-year batch graduating 2023-24: 902 graduated, 76 to higher studies, 799 placed of 826 eligible. Median Rs 1,250,000. Headline CTC: Internal discrepancy in the same report, so the lowest institute-wide highest figure is used (D-23). Printed p.60: UG highest Rs 47 LPA, PG highest Rs 50 LPA, PhD 10.5 LPA, infographic 'Highest Package 51 Lakhs'. Printed p.38 table 'UG and PG Placements 2024 Graduating Batch': UG max 50.64 lakh, PG max 39.27 lakh; Director's message: UG 50.6, PG 39.3 lakh. Institute-wide max of the p.60 per-programme figures = 50 (PG). Figures are offers in lakh INR, domestic/international and CTC-vs-base not specified. Placement brochure 2024-25 (nitc-placement-brochure-2024-25.pdf, PDF p.21 'Last year's Placement Records') shows UG max 47, PG max 50 lakhs, matching p.60 but with no year stated. | CORRECTED after verification: UG B.Tech record uses the lowest UG institute-wide figure (47 LPA, Annual Report 2023-24 p.60); the 50 LPA figure is PG.

| Field | Source URL | Locator | Snapshot (SHA-256 prefix) |
|---|---|---|---|
| placement.batchSize | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0263.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: students graduating in minimum stipulated time | nirf-2025-dcs.pdf (d2eaf003a8) |
| placement.eligibleStudents | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0263.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: graduating minus students selected for higher studies (D-09) | nirf-2025-dcs.pdf (d2eaf003a8) |
| placement.actuallyPlaced | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0263.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: no. of students placed | nirf-2025-dcs.pdf (d2eaf003a8) |
| placement.medianBaseSalary | https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/IR-E-U-0263.pdf | Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24: median salary of placed graduates per annum | nirf-2025-dcs.pdf (d2eaf003a8) |
| placement.headlineCTC | https://nitc.ac.in/imgserver/uploads/attachments/annual-report-2023---2024-english_b056945b-44e5-4565-a15f-8bcb11d8882e_0.pdf | NITC Annual Report 2023-24 (scanned), PDF p.62 / printed p.60 'Centre for Career Development' achievements; also printed p.38 table and Director's message (PDF p.4) | nitc-annual-report-2023-24.pdf (4ee62a2e6d) |
| fees.tuitionAnnual | https://nitc.ac.in/imgserver/uploads/attachments/nit-calicut-fee-structure-for-ug-for-the-ay-2026-27-b-stylecolorrednewb_2337_0.pdf | Fee circular: B.Tech, Category 1 table ('Open/EWS/OBC (NCL) ... above Rs.5,00,000'); hostel circular: 'Hostel Fee Structure for UG (2026-27)' tables A and B | nitc-fee-structure-ug-ay-2026-27.pdf (8e212df332) |
| fees.hostelAndMessAnnual | https://nitc.ac.in/imgserver/uploads/attachments/nit-calicut-fee-structure-for-ug-for-the-ay-2026-27-b-stylecolorrednewb_2337_0.pdf | Fee circular: B.Tech, Category 1 table ('Open/EWS/OBC (NCL) ... above Rs.5,00,000'); hostel circular: 'Hostel Fee Structure for UG (2026-27)' tables A and B | nitc-fee-structure-ug-ay-2026-27.pdf (8e212df332) |
| fees.mandatoryInstituteFeesAnnual | https://nitc.ac.in/imgserver/uploads/attachments/nit-calicut-fee-structure-for-ug-for-the-ay-2026-27-b-stylecolorrednewb_2337_0.pdf | Fee circular: B.Tech, Category 1 table ('Open/EWS/OBC (NCL) ... above Rs.5,00,000'); hostel circular: 'Hostel Fee Structure for UG (2026-27)' tables A and B | nitc-fee-structure-ug-ay-2026-27.pdf (8e212df332) |
| fees.estimatedLivingAnnual | https://doe.gov.in/files/circulars_document/7th_July_2017.pdf | HRA class Y for Kozhikode; band midpoint per D-19 | doe-7th_July_2017.pdf (ce31b4b4c5) |
| cutoffs.minPercentileOrRank | https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx | JoSAA Opening & Closing Rank Archive 2025, Round 6, filtered to CSE 4-yr B.Tech, OPEN, Gender-Neutral | josaa-2025-round6.html (424cca41b0) |
| nirfRank | https://www.nirfindia.org/Rankings/2025/EngineeringRanking.html | NIRF 2025 Engineering ranking table | nirf-2025-engineering-ranking.html (a7e29ec5af) |
| accreditation | https://nitc.ac.in/imgserver/uploads/attachments/press-release_b0c923c0-6c71-4a9b-9d91-af736cd33943_0.pdf | Press Release dated 13-12-2022, first paragraph | nitc-nba-press-release-2022-12-13.pdf (702911765a) |

Second-pass: 16 checks, 1 mismatch(es) recorded in `verification.json`.
  - fees.hostelAndMessAnnual: record 90000 vs independent 92625 — Record = 50,000 + 40,000 and omits the non-refundable 10,500 one-time hostel charges, whereas the MNIT record includes its one-time hostel fee /4 and IITG includes its one-time fees /4. Applying the same convention gives 92,625 (mess 20,000/sem) or 97,625 if mess is 25,000/sem as in table B3. Source itself is internally inconsistent on mess advance (25,000 vs 20,000). Record 90,000 is reproducible only by excluding the one-time hostel fees.

## Corrections made after second pass

- NIT Calicut: hostelAndMessAnnual 90,000 → 92,625 (one-time hostel fees ₹10,500 / 4 added; mess table inconsistent, lower value used); headline CTC 50 → 47 LPA (50 was a PG figure).

## Known caveats (flagged for your spot-check)

- Mess charges are published advances, not actual tariffs (BITS, IIT BHU, IIT Guwahati, IIT Hyderabad, NIT Calicut, MNIT Jaipur).
- Several fee circulars carry no printed date (circular date shown is inferred from the upload path or filename): BITS, DTU, IIT Hyderabad, IIT BHU (2025-26 sheet), IIT Guwahati, MNIT Jaipur, NIT Calicut.
- Headline CTC: official documents do not always say domestic vs international or CTC vs base. Lower official figure used (D-23). IIT BHU: 165 LPA used; the Jan 2024 newsletter says 168 for 2023-24.
- IIT cutoffs are JEE Advanced ranks; `safeCutoffScore` is null (D-21).
- Accreditation 'not stated' means not found in the official documents reviewed.
- HRA classes: IIT Hyderabad campus (Kandi, Sangareddy) and others mapped to the city's urban agglomeration; unlisted places default to Z per the OM note. Living cost uses the band midpoint (D-19).

## Five-item spot-check list for you

1. Open DTU `jac-delhi-2026-admission-brochure.pdf` and confirm the ₹2,69,700 first-year total.
2. Open BITS `nirf-2025-dcs.pdf` and confirm 2,759 graduated / 2,458 placed / median 18,00,000.
3. Open IIT Guwahati placement report and confirm 205 LPA highest.
4. Open `josaa-2025-round6.html` for MNIT Jaipur and confirm the CSE OPEN OS/HS closing ranks.
5. Open NIT Calicut fee circular and confirm tuition 62,500 per semester and hostel one-time fees ₹10,500.
