# Extraction report: openai_gpt-oss-120b

117 receipts scored (of 361 in the dataset).

## Accuracy

| Field | Exact string | Same value | Near match |
|---|---|---|---|
| company | 21.4% | 63.2% | 75.2% |
| date | 84.6% | 91.5% | 91.5% |
| address | 0.9% | 52.1% | 82.9% |
| total | 87.2% | 94.0% | 94.0% |
| **all four fields** | 0.0% | 36.8% | 59.8% |

Same value: equal amounts, equal dates, text equal ignoring case, spacing and punctuation.
Near match: text at least 90% similar; allows for typos in the dataset's own labels.

## Review routing

A receipt is auto-accepted when validation raises no flag, and sent to a person otherwise.
Validation never sees the labels.

**Judged on date and total**

| Queue | Receipts | Correct |
|---|---|---|
| Auto-accepted | 93 (79.5%) | 97.8% |
| Sent to review | 24 (20.5%) | 37.5% |

Of 17 receipts with a wrong value, review caught 15 (88.2%).

**Judged on all four fields**

| Queue | Receipts | Correct |
|---|---|---|
| Auto-accepted | 93 (79.5%) | 44.1% |
| Sent to review | 24 (20.5%) | 8.3% |

Of 74 receipts with a wrong value, review caught 22 (29.7%).

## Flags raised

| Flag | Receipts |
|---|---|
| total:no_total_label | 8 |
| date:unparseable | 8 |
| total:not_in_receipt | 4 |
| total:missing | 2 |
| date:not_in_receipt | 2 |
| company:missing | 1 |
| date:missing | 1 |

## Cost and speed

- Tokens per receipt: 621 in, 208 out
- Model time per receipt: median 909 ms, 90th percentile 1754 ms

## Wrong values

### company: 43 wrong

| Receipt | Extracted | Label | Flags |
|---|---|---|---|
| X51005200931 | GOGIANT ENGINEERING (M) SDN BHD | PERNIAGAAN ZHENG HUI |  |
| X51005230621 | SINLIANHAP SON BHD | SIN LIANHAP SDN BHD |  |
| X51005230657 | CROSS CHANNEL NEIWORKSDN.BHD | CROSS CHANNEL NETWORK SDN. BHD. |  |
| X51005268408 | 99 SPEED MART | 99 SPEED MART S/B |  |
| X51005337867 | OLDTOWN WHITE COFFEE | OLD TOWN KOPITAM SND BHD |  |
| X51005361906 | TEO HENG STATIONERY & BOOKS | TED HENG STATIONERY & BOOKS |  |
| X51005361908 | TEO HENG STATIUNERY BOOKS | TEO HENG STATIONERY & BOOKS |  |
| X51005361923 | SWO ENTERPRISE SDNHHD | SWC ENTERPRISE SDN BHD |  |
| X51005442322 | TONY ROMA'S AEON TEBRAU CITY | GRAND COMPANIONS SDN BHD |  |
| X51005442388 | CONTENTO (JN0761170-K) | CONTENTO | total:not_in_receipt |
| X51005444044 | 99SPEEDMARTS/B(519537-X) | 99 SPEED MART S/B |  |
| X51005444046 | STARGROCERSDNBHD(1171881-W) | STAR GROCER SDN BHD |  |
| X51005447844 | RESTAURANT JIAWEI | RESTAURANT JIAWEI JIAWEI HOUSE |  |
| X51005568885 | EVERCREENLICHTSOMBHD | EVERGREEN LIGHT SDN BHD | date:unparseable |
| X51005568887 | HONHWA HARDMARETRADING | HON HWA HARDWARE TRADING | date:not_in_receipt |
| ... and 28 more | | | |

### date: 10 wrong

| Receipt | Extracted | Label | Flags |
|---|---|---|---|
| X51005442322 | 03Mar18 | 03 MAR 19 |  |
| X51005568885 | 10/072017 | 10/07/2017 | date:unparseable |
| X51005568889 | 11/022017 | 11/02/2017 | date:unparseable |
| X51005568892 | 18082017 | 18/09/2017 | date:unparseable |
| X51005675914 | Late10/1'/2017 | 10/11/2017 | date:unparseable |
| X51005719857 | 19--02-2018 | 19-02-2018 | date:unparseable |
| X51005719863 | 12-01-20182153 | 12-01-2018 | date:unparseable, total:no_total_label |
| X51005724623 | 0803/2018 | 08/03/2018 | date:unparseable |
| X51005746204 |  | 27/MAR/2018 | date:missing |
| X51005746206 | 6h:2E:01 8102-E0-12 | 21-03-2018 | date:unparseable |

### address: 56 wrong

| Receipt | Extracted | Label | Flags |
|---|---|---|---|
| X00016469670 | NO2&4,JALANBAYU4, BANDAR SERIALAM, 81750MASAIJOHOR | NO 2 & 4, JALAN BAYU 4, BANDAR SERI ALAM, B1750 MASAI, JOHOR |  |
| X51005200931 | NO.59 JALAN PERMAS 915, BANDARBARUPERMAS JAYA, 81750 JOHOR BAHRU | NO.59 JALAN PERMAS 9/5 BANDAR BARU PERMAS JAYA 81750 JOHOR BAHRU |  |
| X51005230616 | Leve16,BangunanTH,DamansaraUptown3, No.3,Jalanss21/39,47400PetalingJaya, Selangor | LEVEL 6, BANGUNAN TH, DAMANSARA UPTOWN3 NO.3, JALAN SS21/39,47400 PETALING JAYA SELANGOR |  |
| X51005230621 | LOT13.JALAN, SIN LIANHAP SDN BHD, LOT13,JALANIPOH, KGBATU30ULUYAMLAMA, 44300BTGKALISELANGO | LOT 13, JALAN IPOH, KG BATU 30, ULU YAM LAMA 44300 BTG KALI, SELANGOR. |  |
| X51005268408 | LOT P.T2811,JALAN ANG5A, TAMAN BERKELEY 4115O KLANG,5ELANGOR 1413-5ET1IA ALAM1 | LOT P.T. 2811, JALAN ANGSA, TAMAN BERKELEY 41150 KLANG, SELANGOR 1413-SETIA ALAM 2 |  |
| X51005288570 | Riverwalk Village, Batu 3, Jalan lpoh, 51200 KL | RIVERWALK VILLAGE BATU 3, JALAN IPOH 51200 KL. | total:no_total_label |
| X51005361906 | NO. 53, JALAN BESAR, 4E60O BATANG BERSUNTA: SELANGOR DARULEHSAM | NO. 53, JALAN BESAR, 45600 BATANG BERJUNTAI SELANGOR DARUL EHSAN |  |
| X51005361908 | NO.53,JALANBESAR 4560O BATANG BERJUNI, SELANGORARUL EHSAN | NO. 53, JALAN BESAR, 45600 BATANG BERJUNTAI SELANGOR DARUL EHSAN |  |
| X51005361912 | NO.53,JALAN BESAR,456O0BATANGBERJUNTAI, SELANGORDARULEHSANV | NO. 53, JALAN BESAR, 45600 BATANG BERJUNTAI SELANGOR DARUL EHSAN |  |
| X51005361923 | B& 10,Jalan Ijnk Permai 1, Pusat Niaga Ijok Parmai, 48o0o Ljok Selangor. | 8 & 10, JALAN IJOK PERMAI 1, PUSAT NIAGA IJOK PERMAI, 48000 IJOK, SELANGOR. |  |
| X51005365187 | NO.20, GROUND FLOOR, JALAN BS 1O/6 TAMAN BUKIT SERDANG, SEKSYEN 10 433O0 SERIKEMBANGAN., S | NO.20. GROUND FLOOR, JALAN BS 10/6 TAMAN BUKIT SERDANG, SEKSYEN 10, 43300 SERI KEMBANGAN.  |  |
| X51005433518 | 12, Jalan Tampoi 7/4,Kawasan Perindustrian Tampoi,81200 Jahor Bahru,Johor | 12, JALAN TAMPOI 7/4,KAWASAN PERINDUSTRIAN TAMPOI,81200 JOHOR BAHRU,JOHOR |  |
| X51005433548 | 379, JALAN PERMAS SATU, BANDAR BARU PERMAS JAYA, B1750 PLENTONG, JOHOR. | 379, JALAN PERMAS SATU, BANDAR BARU PERMAS JAYA 81750 PLENTONG, JOHOR. | total:missing |
| X51005433556 | $117, Second Floor, Aeon Tebrau City, 1, Jalan Desa Tebrau, Taman Desa Tebrau, 81100 Johor | S117, SECOND FLOOR, AEON TEBRAU CITY, 1, JALAN DESA TEBRAU, TAMAN DESA TEBRAU, 81100 JOHOR |  |
| X51005442334 | 12, JalanTampoi 7/4,Kawasan Perindustrian Tampoi,81200 Johor Bahru,Johor | 12, JALAN TAMPOI 7/4,KAWASAN PARINDUSTRIAN TAMPOI,81200 JOHOR BAHRU,JOHOR |  |
| ... and 41 more | | | |

### total: 7 wrong

| Receipt | Extracted | Label | Flags |
|---|---|---|---|
| X51005268408 | 69.78 | 169.80 |  |
| X51005433548 |  | 33.80 | total:missing |
| X51005577191 | 1000 | 10.00 | total:not_in_receipt |
| X51005582745 |  | 150.00 | total:missing |
| X51005684949 | 7.40 | 7.42 | total:no_total_label |
| X51005710963 | 740 | 7.40 | total:not_in_receipt |
| X51005715455 | 10.00 | RM 10.60 | company:missing, total:not_in_receipt |

