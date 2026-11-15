# Extraction report: openai_gpt-oss-20b

117 receipts scored (of 361 in the dataset).

## Accuracy

| Field | Exact string | Same value | Near match |
|---|---|---|---|
| company | 21.4% | 61.5% | 75.2% |
| date | 87.2% | 93.2% | 93.2% |
| address | 0.9% | 53.8% | 83.8% |
| total | 87.2% | 94.9% | 94.9% |
| **all four fields** | 0.0% | 35.9% | 63.2% |

Same value: equal amounts, equal dates, text equal ignoring case, spacing and punctuation.
Near match: text at least 90% similar; allows for typos in the dataset's own labels.

## Review routing

A receipt is auto-accepted when validation raises no flag, and sent to a person otherwise.
Validation never sees the labels.

**Judged on date and total**

| Queue | Receipts | Correct |
|---|---|---|
| Auto-accepted | 91 (77.8%) | 98.9% |
| Sent to review | 26 (22.2%) | 50.0% |

Of 14 receipts with a wrong value, review caught 13 (92.9%).

**Judged on all four fields**

| Queue | Receipts | Correct |
|---|---|---|
| Auto-accepted | 91 (77.8%) | 42.9% |
| Sent to review | 26 (22.2%) | 11.5% |

Of 75 receipts with a wrong value, review caught 23 (30.7%).

## Flags raised

| Flag | Receipts |
|---|---|
| total:no_total_label | 8 |
| total:not_in_receipt | 7 |
| date:unparseable | 7 |
| date:not_in_receipt | 4 |
| address:missing | 1 |

## Cost and speed

- Tokens per receipt: 621 in, 181 out
- Model time per receipt: median 630 ms, 90th percentile 881 ms

## Wrong values

### company: 45 wrong

| Receipt | Extracted | Label | Flags |
|---|---|---|---|
| X51005200931 | PERNIAGAAN ZHENG HU! | PERNIAGAAN ZHENG HUI |  |
| X51005230621 | SINLIANHAP SON BHD | SIN LIANHAP SDN BHD |  |
| X51005230657 | CROSS CHANNEL NEIWORKSDN.BHD | CROSS CHANNEL NETWORK SDN. BHD. |  |
| X51005268408 | 99 SPEED MART 5/B (519537-X) | 99 SPEED MART S/B | total:not_in_receipt |
| X51005337867 | OLDTOWN WHITE COFFEE | OLD TOWN KOPITAM SND BHD |  |
| X51005361906 | TEO HENG STATIONERY & BOOKS | TED HENG STATIONERY & BOOKS |  |
| X51005361908 | TEO HENG STATIUNERY BOOKS | TEO HENG STATIONERY & BOOKS |  |
| X51005361923 | SWO ENTERPRISE SDNHHD | SWC ENTERPRISE SDN BHD |  |
| X51005442322 | TONY ROMA'S AEON TEBRAU CITY | GRAND COMPANIONS SDN BHD |  |
| X51005442388 | CONTENTO (JN0761170-K) | CONTENTO | total:not_in_receipt |
| X51005444040 | B.I.G. | BENS INDEPENDENT GROCER SDN. BHD |  |
| X51005444041 | B.I.C. | BENS INDEPENDENT GROCER SDN. BHD |  |
| X51005444044 | 99SPEEDMARTS/B(519537-X) | 99 SPEED MART S/B |  |
| X51005444046 | STARGROCERSDNBHD(1171881-W) | STAR GROCER SDN BHD |  |
| X51005447844 | RESTAURANT JIAWEI | RESTAURANT JIAWEI JIAWEI HOUSE |  |
| ... and 30 more | | | |

### date: 8 wrong

| Receipt | Extracted | Label | Flags |
|---|---|---|---|
| X51005442322 | 03Mar18 | 03 MAR 19 |  |
| X51005568885 | 01-01 10/072017 | 10/07/2017 | date:unparseable |
| X51005568892 | 01-01 18082017 | 18/09/2017 | date:unparseable |
| X51005675914 | 10/1'/2017 | 10/11/2017 | date:unparseable |
| X51005719898 | 19-03-1813 | 19-03-18 | date:unparseable |
| X51005724623 | 0803/2018 | 08/03/2018 | date:unparseable |
| X51005746204 | 27M3172018 | 27/MAR/2018 | date:unparseable |
| X51005746206 | 6h:2E:01 8102-E0-12 | 21-03-2018 | date:unparseable |

### address: 54 wrong

| Receipt | Extracted | Label | Flags |
|---|---|---|---|
| X00016469670 | NO2&4,JALANBAYU4, BANDAR SERIALAM, 81750MASAIJOHOR | NO 2 & 4, JALAN BAYU 4, BANDAR SERI ALAM, B1750 MASAI, JOHOR |  |
| X51005200931 | NO.59 JALAN PERMAS 915, BANDARBARUPERMAS JAYA, 81750 JOHOR BAHRU | NO.59 JALAN PERMAS 9/5 BANDAR BARU PERMAS JAYA 81750 JOHOR BAHRU |  |
| X51005230616 | Leve16,BangunanTH,DamansaraUptown3 No.3,Jalanss21/39,47400PetalingJaya Selangor | LEVEL 6, BANGUNAN TH, DAMANSARA UPTOWN3 NO.3, JALAN SS21/39,47400 PETALING JAYA SELANGOR |  |
| X51005230621 | LOT13.JALAN, SIN LIANHAP SDN BHD, LOT13,JALANIPOH, KGBATU30ULUYAMLAMA, 44300BTGKALISELANGO | LOT 13, JALAN IPOH, KG BATU 30, ULU YAM LAMA 44300 BTG KALI, SELANGOR. |  |
| X51005268408 | LOT P.T2811,JALAN ANG5A, TAMAN BERKELEY 4115O KLANG,5ELANGOR 1413-5ET1IA ALAM1 G57 1D.NO:0 | LOT P.T. 2811, JALAN ANGSA, TAMAN BERKELEY 41150 KLANG, SELANGOR 1413-SETIA ALAM 2 | total:not_in_receipt |
| X51005288570 | Riverwalk Village, Batu 3, Jalan lpoh, 51200 KL | RIVERWALK VILLAGE BATU 3, JALAN IPOH 51200 KL. | total:no_total_label |
| X51005337867 | 0ld TownKopitiam Sdn Bhd (716269-X), Sri Rampai | SRI RAMPAI |  |
| X51005361906 | NO. 53, JALAN BESAR, 4E60O BATANG BERSUNTA: SELANGOR DARULEHSAM | NO. 53, JALAN BESAR, 45600 BATANG BERJUNTAI SELANGOR DARUL EHSAN |  |
| X51005361908 | NO.53,JALANBESAR 4560O BATANG BERJUNI, SELANGORARUL EHSAN | NO. 53, JALAN BESAR, 45600 BATANG BERJUNTAI SELANGOR DARUL EHSAN |  |
| X51005361912 | NO.53,JALAN BESAR,456O0BATANGBERJUNTAI SELANGORDARULEHSANV | NO. 53, JALAN BESAR, 45600 BATANG BERJUNTAI SELANGOR DARUL EHSAN |  |
| X51005361923 | B& 10,Jalan Ijnk Permai 1, Pusat Niaga Ijok Parmai, 48o0o Ljok Selangor. | 8 & 10, JALAN IJOK PERMAI 1, PUSAT NIAGA IJOK PERMAI, 48000 IJOK, SELANGOR. |  |
| X51005365187 | NO.20, GROUND FLOOR, JALAN BS 1O/6 TAMAN BUKIT SERDANG, SEKSYEN 10 433O0 SERIKEMBANGAN., S | NO.20. GROUND FLOOR, JALAN BS 10/6 TAMAN BUKIT SERDANG, SEKSYEN 10, 43300 SERI KEMBANGAN.  |  |
| X51005433518 | 12, Jalan Tampoi 7/4,Kawasan Perindustrian Tampoi,81200 Jahor Bahru,Johor | 12, JALAN TAMPOI 7/4,KAWASAN PERINDUSTRIAN TAMPOI,81200 JOHOR BAHRU,JOHOR |  |
| X51005433548 | 379, JALAN PERMAS SATU, BANDAR BARU PERMAS JAYA B1750 PLENTONG, JOHOR. | 379, JALAN PERMAS SATU, BANDAR BARU PERMAS JAYA 81750 PLENTONG, JOHOR. | total:not_in_receipt |
| X51005433556 | $117, Second Floor, Aeon Tebrau City, 1, Jalan Desa Tebrau, Taman Desa Tebrau, 81100 Johor | S117, SECOND FLOOR, AEON TEBRAU CITY, 1, JALAN DESA TEBRAU, TAMAN DESA TEBRAU, 81100 JOHOR |  |
| ... and 39 more | | | |

### total: 6 wrong

| Receipt | Extracted | Label | Flags |
|---|---|---|---|
| X51005433548 | 34.57 | 33.80 | total:not_in_receipt |
| X51005577191 | 1000 | 10.00 | total:not_in_receipt |
| X51005582745 | 15000 | 150.00 | total:not_in_receipt |
| X51005710963 | 740 | 7.40 | total:not_in_receipt |
| X51005715455 | 10.00 | RM 10.60 | total:not_in_receipt |
| X51005745213 | 6.60 | 7.00 | total:no_total_label |

