# Cloud reference scaffolds — not executed

Snowflake SQL/Snowpark can replace the local processing/store; Azure hosts a steward portal/API. Snowflake Streams/Tasks process changes already loaded to Snowflake and do not extract SAP ERP. The local demo does not connect these services.

Placeholders: YOUR_SNOWFLAKE_ACCOUNT, YOUR_DATABASE, YOUR_SCHEMA, YOUR_WAREHOUSE, YOUR_ROLE, private-key path, Azure subscription/resource group, Entra tenant/client IDs and Key Vault URI. See .env.example and solution-labs/master/cloud/. No credentials are present.

DDL and DML scaffolds illustrate staged normalized/candidate/decision/master/crosswalk/version contracts. Driver logic must validate a complete staged batch, check the publication pointer affected-row count, and rollback on conflicts. Canonical attribute survivorship, deletion/merge/split policy and regional authorization must be specified before live use.

References: https://docs.snowflake.com/en/sql-reference/transactions and https://docs.snowflake.com/en/user-guide/data-pipelines-intro
