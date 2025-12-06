## Plan: HR Attrition Data Warehouse

Clarify how the Spark/PostgreSQL pipeline feeds a dimensional model used by Power BI visualization and the DSS (ML + web interface), ensuring ETL, schema targets, and reporting/decision-support requirements align.

### Steps
1. Define the dimensional schema (fact `fact_hr_attrition` plus candidate dims such as `dim_employee`, `dim_job_role`, `dim_time`) with tables and keys so downstream tools know what data to consume from `etl_process.py`.
2. Document preprocessing steps (cleansing, label creation, datatype enforcement, joins) needed before loading into PostgreSQL; include expected outputs (tables, sample stats) from the Spark job.
3. Specify how Power BI will connect (tables/views, refresh cadence) and which visuals (attrition trend, demographics, satisfaction vs. attrition) it will show, linking each visual to source columns.
4. Describe the DSS pipeline: the ML model (feature set, label, algorithm) trained on `fact_hr_attrition`, how predictions are stored, and how the web interface exposes input/output; note any ETL updates required for scoring data.
5. Identify governance steps (PostgreSQL schema/permissions, refresh schedule, logging) so the Spark ETL, Power BI reports, and DSS app stay in sync.

### Further Considerations
1. Confirm whether additional data sources (e.g., engagement surveys) need integration before dimensional modeling, or if the CSV is sufficient.
2. Decide how frequently the Spark job runs and whether incremental loads / CDC are required for the DSS and Power BI refresh windows.
3. Clarify the DSS web interface requirements (authentication, input validation, expected response time) to guide backend ETL/data provisioning.
