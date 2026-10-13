-- DML reference template for a connector-managed transaction; not standalone automation.
-- Validate all staged products/crosswalks and stable-ID policy BEFORE beginning.
-- Bind :version, :expected_version and :snapshot through the connector.
BEGIN;
INSERT INTO YOUR_DATABASE.YOUR_SCHEMA.GLOBAL_PRODUCT
SELECT GLOBAL_ID, PUBLISH_VERSION, RECORD_JSON
FROM YOUR_DATABASE.YOUR_SCHEMA.STAGED_GLOBAL_PRODUCT WHERE PUBLISH_VERSION=:version;
INSERT INTO YOUR_DATABASE.YOUR_SCHEMA.REGIONAL_CROSSWALK
SELECT SOURCE_KEY, GLOBAL_ID, PUBLISH_VERSION
FROM YOUR_DATABASE.YOUR_SCHEMA.STAGED_CROSSWALK WHERE PUBLISH_VERSION=:version;
UPDATE YOUR_DATABASE.YOUR_SCHEMA.PUBLICATION
SET ACTIVE_VERSION=:version,SNAPSHOT_HASH=:snapshot
WHERE PRODUCT_NAME='GLOBAL_MASTER' AND ACTIVE_VERSION=:expected_version;
-- REQUIRED: driver checks affected-row count == 1, otherwise ROLLBACK and abort.
-- Do not execute COMMIT unconditionally in a script runner.
-- On success the driver issues COMMIT. On any error it issues ROLLBACK.
