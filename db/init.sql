CREATE TABLE hospital (
    image_file text NOT NULL,
    findings_label text NOT NULL,
    followup_no integer NOT NULL,
    _orig_patient_id bigint NOT NULL,
    age smallint NOT NULL,
    sex text NOT NULL,
    view_position text NOT NULL,
    img_width integer NOT NULL,
    img_height integer NOT NULL,
    pixel_spacing_x numeric NOT NULL,
    pixel_spacing_y numeric NOT NULL,
    patient_key bigint NOT NULL,
    patient_name text NOT NULL,
    mrn text NOT NULL,
    birth_date text NOT NULL,
    phone text NOT NULL,
    insurance_type text NOT NULL,
    accession_no text NOT NULL,
    institution_code text NOT NULL,
    device_id text NOT NULL,
    visit_type text NOT NULL,
    ward text NOT NULL,
    department text NOT NULL,
    ordering_physician text NOT NULL,
    radiologist text NOT NULL,
    report_status text NOT NULL,
    study_datetime timestamp NOT NULL,
    read_datetime timestamp NOT NULL,
    report_text text NOT NULL,
    clinical_info text NOT NULL,
    is_synthetic boolean NOT NULL,
    seed_id text PRIMARY KEY,
    image_data bytea
);

COPY hospital (
    image_file, findings_label, followup_no, _orig_patient_id, age, sex,
    view_position, img_width, img_height, pixel_spacing_x, pixel_spacing_y,
    patient_key, patient_name, mrn, birth_date, phone, insurance_type,
    accession_no, institution_code, device_id, visit_type, ward, department,
    ordering_physician, radiologist, report_status, study_datetime,
    read_datetime, report_text, clinical_info, is_synthetic, seed_id
)
FROM '/data/hospital.csv'
WITH (FORMAT csv, HEADER, ENCODING 'UTF8');

UPDATE hospital
SET image_data = pg_read_binary_file('/data/images/' || image_file);

ALTER TABLE hospital ALTER COLUMN image_data SET NOT NULL;

CREATE EXTENSION pgcrypto;

CREATE SCHEMA private;
REVOKE ALL ON SCHEMA private FROM PUBLIC;

CREATE TABLE private.masking_secret (
    id boolean PRIMARY KEY DEFAULT true CHECK (id),
    secret text NOT NULL
);

INSERT INTO private.masking_secret (secret)
VALUES (encode(gen_random_bytes(32), 'hex'));

CREATE FUNCTION private.mask_value(kind text, value text)
RETURNS text
LANGUAGE sql
STABLE
STRICT
SECURITY DEFINER
SET search_path = pg_catalog, private, public
AS $$
    SELECT kind || '_' || left(encode(hmac(value, secret, 'sha256'), 'hex'), 24)
    FROM private.masking_secret
    WHERE id
$$;

REVOKE ALL ON FUNCTION private.mask_value(text, text) FROM PUBLIC;

CREATE FUNCTION private.mask_hospital_text(
    value text,
    patient_name text,
    mrn text,
    birth_date text,
    phone text,
    accession_no text,
    ordering_physician text,
    radiologist text
)
RETURNS text
LANGUAGE sql
STABLE
STRICT
SECURITY DEFINER
SET search_path = pg_catalog, private, public
AS $$
    SELECT replace(
        replace(
            replace(
                replace(
                    replace(
                        replace(
                            replace(value,
                                patient_name, private.mask_value('NAME', patient_name)),
                            mrn, private.mask_value('MRN', mrn)),
                        birth_date, private.mask_value('BIRTH_DATE', birth_date)),
                    phone, private.mask_value('PHONE', phone)),
                accession_no, private.mask_value('ACCESSION', accession_no)),
            ordering_physician, private.mask_value('CLINICIAN', ordering_physician)),
        radiologist, private.mask_value('CLINICIAN', radiologist))
$$;

REVOKE ALL ON FUNCTION private.mask_hospital_text(
    text, text, text, text, text, text, text, text
) FROM PUBLIC;

CREATE SCHEMA llm;
REVOKE ALL ON SCHEMA llm FROM PUBLIC;

CREATE VIEW llm.hospital
WITH (security_barrier = true) AS
SELECT
    private.mask_value('IMAGE', image_file) AS image_file,
    findings_label,
    followup_no,
    private.mask_value('PATIENT', _orig_patient_id::text) AS _orig_patient_id,
    age,
    sex,
    view_position,
    img_width,
    img_height,
    pixel_spacing_x,
    pixel_spacing_y,
    private.mask_value('PATIENT', patient_key::text) AS patient_key,
    private.mask_value('NAME', patient_name) AS patient_name,
    private.mask_value('MRN', mrn) AS mrn,
    private.mask_value('BIRTH_DATE', birth_date) AS birth_date,
    private.mask_value('PHONE', phone) AS phone,
    insurance_type,
    private.mask_value('ACCESSION', accession_no) AS accession_no,
    institution_code,
    device_id,
    visit_type,
    ward,
    department,
    private.mask_value('CLINICIAN', ordering_physician) AS ordering_physician,
    private.mask_value('CLINICIAN', radiologist) AS radiologist,
    report_status,
    study_datetime,
    read_datetime,
    private.mask_hospital_text(
        report_text, patient_name, mrn, birth_date, phone, accession_no,
        ordering_physician, radiologist
    ) AS report_text,
    private.mask_hospital_text(
        clinical_info, patient_name, mrn, birth_date, phone, accession_no,
        ordering_physician, radiologist
    ) AS clinical_info,
    is_synthetic,
    private.mask_value('SEED', seed_id) AS seed_id,
    image_data
FROM public.hospital;

REVOKE ALL ON ALL TABLES IN SCHEMA llm FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
