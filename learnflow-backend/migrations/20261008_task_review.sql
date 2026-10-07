-- Apply once only if these columns are absent. Development startup already
-- adds missing columns through _ensure_schema_extensions.
ALTER TABLE tasks ADD COLUMN reviewed_at TIMESTAMP NULL;
ALTER TABLE tasks ADD COLUMN reviewed_by VARCHAR(36) NULL;
ALTER TABLE tasks ADD COLUMN review_notes TEXT NULL;
