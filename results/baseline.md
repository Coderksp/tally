# Extraction report: baseline

361 receipts scored (of 361 in the dataset).

## Accuracy

| Field | Exact string | Same value | Near match |
|---|---|---|---|
| company | 23.3% | 40.2% | 48.8% |
| date | 77.8% | 91.1% | 91.1% |
| address | 1.1% | 11.4% | 29.6% |
| total | 67.9% | 81.4% | 81.4% |
| **all four fields** | 0.3% | 5.3% | 19.1% |

Same value: equal amounts, equal dates, text equal ignoring case, spacing and punctuation.
Near match: text at least 90% similar; allows for typos in the dataset's own labels.

## Review routing

A receipt is auto-accepted when validation raises no flag, and sent to a person otherwise.
Validation never sees the labels.

**Judged on date and total**

| Queue | Receipts | Correct |
|---|---|---|
| Auto-accepted | 318 (88.1%) | 82.7% |
| Sent to review | 43 (11.9%) | 23.3% |

Of 88 receipts with a wrong value, review caught 33 (37.5%).

**Judged on all four fields**

| Queue | Receipts | Correct |
|---|---|---|
| Auto-accepted | 318 (88.1%) | 5.0% |
| Sent to review | 43 (11.9%) | 7.0% |

Of 342 receipts with a wrong value, review caught 40 (11.7%).

## Flags raised

| Flag | Receipts |
|---|---|
| date:missing | 25 |
| total:no_total_label | 23 |
| total:missing | 1 |

## Wrong values

### company: 216 wrong

| Receipt | Extracted | Label | Flags |
|---|---|---|---|
| X00016469670 | tan chay yee | OJC MARKETING SDN BHD |  |
| X00016469671 | tan chay yee | OJC MARKETING SDN BHD |  |
| X51005200931 | PERNIAGAAN ZHENG HU! | PERNIAGAAN ZHENG HUI |  |
| X51005230616 | formerly known as | GERBANG ALAF RESTAURANTS SDN BHD |  |
| X51005230621 | SINLIANHAP SON BHD | SIN LIANHAP SDN BHD |  |
| X51005230657 | CROSS CHANNEL NEIWORKSDN.BHD | CROSS CHANNEL NETWORK SDN. BHD. |  |
| X51005230659 | No.5-7,Jalan Mahagoni 7/1, | SWC ENTERPRISE SDN BHD |  |
| X51005268408 | LOT P.T2811,JALAN ANG5A, | 99 SPEED MART S/B |  |
| X51005288570 | CORPORATION S/B | SECURE PARKING CORPORATION S/B | total:no_total_label |
| X51005337867 | OLDTOWN WHITE COFFEE | OLD TOWN KOPITAM SND BHD |  |
| X51005361906 | TEO HENG STATIONERY & BOOKS | TED HENG STATIONERY & BOOKS |  |
| X51005361908 | TEO HENG STATIUNERY BOOKS | TEO HENG STATIONERY & BOOKS |  |
| X51005361923 | SWO ENTERPRISE SDNHHD | SWC ENTERPRISE SDN BHD |  |
| X51005442322 | RESTAURANT | GRAND COMPANIONS SDN BHD |  |
| X51005442334 | 12, JalanTampoi 7/4,Kawasan Perindustrian | UNIHAKKA INTERNATIONAL SDN BHD |  |
| ... and 201 more | | | |

### date: 32 wrong

| Receipt | Extracted | Label | Flags |
|---|---|---|---|
| X51005442322 | 03Mar18 | 03 MAR 19 |  |
| X51005568866 | 3 Sept 2017 | 20/08/17 |  |
| X51005568885 |  | 10/07/2017 | date:missing |
| X51005568887 |  | 26/04/2017 | date:missing |
| X51005568889 |  | 11/02/2017 | date:missing |
| X51005568890 |  | 05/01/2017 | date:missing |
| X51005568892 |  | 18/09/2017 | date:missing |
| X51005675914 |  | 10/11/2017 | date:missing |
| X51005719863 |  | 12-01-2018 | date:missing |
| X51005724623 |  | 08/03/2018 | date:missing |
| X51005746204 |  | 27/MAR/2018 | date:missing |
| X51005746206 |  | 21-03-2018 | date:missing |
| X51005806719 |  | 13/01/2018 | date:missing |
| X51005806720 |  | 13/01/2018 | date:missing |
| X51006332641 |  | 11/02/2017 | date:missing |
| ... and 17 more | | | |

### address: 320 wrong

| Receipt | Extracted | Label | Flags |
|---|---|---|---|
| X00016469670 | *** COPY***, OJCMARKETINGSDNBHD | NO 2 & 4, JALAN BAYU 4, BANDAR SERI ALAM, B1750 MASAI, JOHOR |  |
| X00016469671 | OJCMARKETINGSDNBHD | NO 2 & 4, JALAN BAYU 4, BANDAR SERI ALAM, 81750 MASAI, JOHOR |  |
| X51005200931 | JM0325955-V, NO.59 JALAN PERMAS 915, BANDARBARUPERMAS JAYA, 81750 JOHOR BAHRU | NO.59 JALAN PERMAS 9/5 BANDAR BARU PERMAS JAYA 81750 JOHOR BAHRU |  |
| X51005230605 | ALSERKAM ENTERPRTSE | KM 458.4 BKT LANJAN UTARA, L/RAYA UTARA SELATAN,SG BULOH 47000 SUNGAI BUL |  |
| X51005230616 | GoldenArchesRestaurantsSdnBhd, Licensee of McDonald's, Leve16,BangunanTH,DamansaraUptown3, | LEVEL 6, BANGUNAN TH, DAMANSARA UPTOWN3 NO.3, JALAN SS21/39,47400 PETALING JAYA SELANGOR |  |
| X51005230621 | LOT13.JALAN, SIN LIANHAP SDN BHD, LOT13,JALANIPOH, KGBATU30ULUYAMLAMA | LOT 13, JALAN IPOH, KG BATU 30, ULU YAM LAMA 44300 BTG KALI, SELANGOR. |  |
| X51005230659 | Sekysen 4, Bandar Utama, 44300, Batang Kali, Selangor. | NO. 5-7, JALAN MAHAGONI 7/1, SEKYSEN 4, BANDAR UTAMA, 44300 BATANG KALI, SELANGOR. |  |
| X51005268408 | TAMAN BERKELEY, 4115O KLANG,5ELANGOR, 1413-5ET1IA ALAM1, G57 1D.NO:000181747712 | LOT P.T. 2811, JALAN ANGSA, TAMAN BERKELEY 41150 KLANG, SELANGOR 1413-SETIA ALAM 2 |  |
| X51005288570 | Riverwalk Village, Batu 3, Jalan lpoh, 51200 KL | RIVERWALK VILLAGE BATU 3, JALAN IPOH 51200 KL. | total:no_total_label |
| X51005361906 | (00 7451$37-M), NO. 53, JALAN BESAR, 4E60O BATANG BERSUNTA:, SELANGOR DARULEHSAM | NO. 53, JALAN BESAR, 45600 BATANG BERJUNTAI SELANGOR DARUL EHSAN |  |
| X51005361908 | NO.53,JALANBESAR 4560O BATANG BERJUNI, SELANGORARUL EHSAN | NO. 53, JALAN BESAR, 45600 BATANG BERJUNTAI SELANGOR DARUL EHSAN |  |
| X51005361912 | NO.53,JALAN BESAR,456O0BATANGBERJUNTAI, SELANGORDARULEHSANV | NO. 53, JALAN BESAR, 45600 BATANG BERJUNTAI SELANGOR DARUL EHSAN |  |
| X51005361923 | B& 10,Jalan Ijnk Permai 1, Pusat Niaga Ijok Parmai, 48o0o Ljok Selangor. | 8 & 10, JALAN IJOK PERMAI 1, PUSAT NIAGA IJOK PERMAI, 48000 IJOK, SELANGOR. |  |
| X51005365187 | NO.20, GROUND FLOOR, JALAN BS 1O/6 TAMAN BUKIT SERDANG, SEKSYEN 10 433O0 SERIKEMBANGAN., S | NO.20. GROUND FLOOR, JALAN BS 10/6 TAMAN BUKIT SERDANG, SEKSYEN 10, 43300 SERI KEMBANGAN.  |  |
| X51005433518 | 07Mar201818:22 | 12, JALAN TAMPOI 7/4,KAWASAN PERINDUSTRIAN TAMPOI,81200 JOHOR BAHRU,JOHOR |  |
| ... and 305 more | | | |

### total: 67 wrong

| Receipt | Extracted | Label | Flags |
|---|---|---|---|
| X51005230648 | 6.36 | 6.35 |  |
| X51005268408 | 69.78 | 169.80 |  |
| X51005288570 | 23.03 | 1.00 | total:no_total_label |
| X51005337867 | 30.24 | 30.25 |  |
| X51005442388 | 11.80 | 21.60 | total:no_total_label |
| X51005444046 | 66.17 | 66.15 |  |
| X51005577191 | 0.57 | 10.00 |  |
| X51005582745 | 8.49 | 150.00 |  |
| X51005675103 | 94.50 | 100.17 |  |
| X51005675914 | 67.94 | 67.85 | date:missing |
| X51005710963 | 7.00 | 7.40 |  |
| X51005715455 |  | RM 10.60 | total:missing |
| X51005719863 | 73.00 | 77.40 | date:missing |
| X51005745298 | 3.99 | 4.00 |  |
| X51005757220 | 79.09 | 81.20 |  |
| ... and 52 more | | | |

