# 병원 데이터셋

`hospital.csv` (272행 × 32열) 와 `images/` (PNG 272장) 로 구성됩니다.

원본 파일은 저장소에 포함하지 않습니다. 도커 이미지 빌드에만 쓰이고,
`ghcr.io/hy2219/medical-sdlc-db` 안에 이미 적재되어 있기 때문입니다.
실습에서는 `docker compose up -d` 로 그 이미지를 받으면 됩니다.

SHA256: `37240fee2abf0f71754f63a9e0231e7bee2fee2b02ef4f8c4906669206c3fad1`

## 무엇인가

NIH ChestX-ray14 공개 영상에 **병원 운영 데이터를 합성해 붙인** 것입니다. 실존 환자는 없습니다 — 이름, 등록번호, 전화번호, 판독문은 전부 고정 시드로 생성했습니다.

그렇게 만든 이유는 병원 데이터의 **모양**이 필요해서입니다. 공개 데이터셋에는 이름도 등록번호도 없어서, 그것만으로는 가릴 것이 없고 마스킹이 성립하지 않습니다.

`hospital.csv` 는 **마스킹 전** 상태입니다. 이것이 컨테이너 안에 있고, 나갈 때 가려집니다.

## 32열

`image_file` 이 PNG 파일명이라 기록과 영상이 이어집니다.

**원본 (NIH 공개)** — 11열

```
image_file  findings_label  followup_no  _orig_patient_id  age  sex
view_position  img_width  img_height  pixel_spacing_x  pixel_spacing_y
```

**합성 (병원 운영 데이터 재현)** — 21열

```
patient_key  patient_name  mrn  birth_date  phone  insurance_type
accession_no  institution_code  device_id  visit_type  ward  department
ordering_physician  radiologist  report_status  study_datetime
read_datetime  report_text  clinical_info  is_synthetic  seed_id
```

## 반출 규칙

| 나감 (8) | 이유 |
|---|---|
| `patient_key` | 원본 ID 와 무관하게 재매핑됨 |
| `sex` `view_position` `followup_no` | 개인을 특정하지 않음 |
| `findings_label` | 공개 분류 체계 |
| `institution_code` `visit_type` `department` | 익명 코드, 작은 기관은 병합 |

| 나가지 않음 (24) | 이유 |
|---|---|
| `patient_name` `mrn` `birth_date` `phone` `accession_no` `ordering_physician` `radiologist` `_orig_patient_id` | 직접 식별자 |
| `report_text` `clinical_info` | 자유 텍스트. 마스킹이 확률적 |
| `age` | `age_bin` 구간으로만 |
| `study_datetime` `read_datetime` | 환자별 오프셋 적용 후 날짜만 |
| `image_file` 등 나머지 | 집계 응답에 필요 없음 |

## 규모

272행 / 153명 / PNG 272장.

k=5 를 만족하지 못해 **k=2** 로 만들었습니다. 데모 크기라 그렇습니다. 실제 병원 규모에서는 k=5 가 통과합니다.

나이 구간도 그래서 40년(`0-39`, `40-79`, `80+`)입니다. 10년 구간에서는 어린 환자군이 k 를 못 채웁니다.

## 다시 만들려면

```bash
docker compose --profile load run --rm data-loader \
    --raw Data_Entry_demo.csv --images images --bbox BBox_List_2017.csv --k 2
```

시드가 고정이라 같은 값이 나옵니다.
