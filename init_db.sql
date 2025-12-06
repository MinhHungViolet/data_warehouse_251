-- =====================================================
-- Script khoi tao Data Warehouse cho HR Attrition
-- =====================================================

-- Tao database (chay lenh nay voi postgres user)
-- CREATE DATABASE hr_data_warehouse;

-- Ket noi vao database hr_data_warehouse truoc khi chay cac lenh sau

-- =====================================================
-- 1. DIMENSION TABLES
-- =====================================================

-- Dimension: Employee (thong tin nhan khau hoc)
DROP TABLE IF EXISTS dim_employee CASCADE;
CREATE TABLE dim_employee (
    employee_key SERIAL PRIMARY KEY,
    employee_number INT UNIQUE NOT NULL,
    age INT,
    gender VARCHAR(10),
    marital_status VARCHAR(20),
    education INT,
    education_field VARCHAR(50),
    distance_from_home INT,
    num_companies_worked INT,
    total_working_years INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dimension: Job Role (thong tin cong viec)
DROP TABLE IF EXISTS dim_job_role CASCADE;
CREATE TABLE dim_job_role (
    job_role_key SERIAL PRIMARY KEY,
    job_role VARCHAR(100) UNIQUE NOT NULL,
    job_level INT,
    job_involvement INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dimension: Department (phong ban)
DROP TABLE IF EXISTS dim_department CASCADE;
CREATE TABLE dim_department (
    department_key SERIAL PRIMARY KEY,
    department VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dimension: Time (thoi gian - cho phan tich xu huong)
DROP TABLE IF EXISTS dim_time CASCADE;
CREATE TABLE dim_time (
    time_key SERIAL PRIMARY KEY,
    load_date DATE UNIQUE NOT NULL,
    year INT,
    quarter INT,
    month INT,
    week INT,
    day INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 2. FACT TABLE
-- =====================================================

-- Fact Table: HR Attrition (du lieu chinh ve bien dong nhan su)
DROP TABLE IF EXISTS fact_hr_attrition CASCADE;
CREATE TABLE fact_hr_attrition (
    fact_key SERIAL PRIMARY KEY,

    -- Foreign Keys to Dimensions
    employee_key INT REFERENCES dim_employee(employee_key),
    job_role_key INT REFERENCES dim_job_role(job_role_key),
    department_key INT REFERENCES dim_department(department_key),
    time_key INT REFERENCES dim_time(time_key),

    -- Measures (cac chi so do luong)
    attrition VARCHAR(5),
    attrition_label INT,  -- 1: Yes, 0: No
    monthly_income DECIMAL(10,2),
    hourly_rate DECIMAL(8,2),
    daily_rate DECIMAL(8,2),
    monthly_rate DECIMAL(10,2),
    percent_salary_hike INT,

    -- Performance & Satisfaction
    performance_rating INT,
    environment_satisfaction INT,
    job_satisfaction INT,
    relationship_satisfaction INT,
    work_life_balance INT,

    -- Tenure & Experience
    years_at_company INT,
    years_in_current_role INT,
    years_since_last_promotion INT,
    years_with_curr_manager INT,

    -- Work Characteristics
    business_travel VARCHAR(50),
    over_time VARCHAR(5),
    stock_option_level INT,
    training_times_last_year INT,

    -- ETL Metadata
    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    etl_batch_id VARCHAR(50)
);

-- =====================================================
-- 3. INDEXES (de tang toc query)
-- =====================================================

-- Indexes cho Dimension Tables
CREATE INDEX idx_employee_number ON dim_employee(employee_number);
CREATE INDEX idx_job_role_name ON dim_job_role(job_role);
CREATE INDEX idx_department_name ON dim_department(department);
CREATE INDEX idx_time_load_date ON dim_time(load_date);

-- Indexes cho Fact Table
CREATE INDEX idx_fact_employee_key ON fact_hr_attrition(employee_key);
CREATE INDEX idx_fact_job_role_key ON fact_hr_attrition(job_role_key);
CREATE INDEX idx_fact_department_key ON fact_hr_attrition(department_key);
CREATE INDEX idx_fact_time_key ON fact_hr_attrition(time_key);
CREATE INDEX idx_fact_attrition_label ON fact_hr_attrition(attrition_label);
CREATE INDEX idx_fact_load_timestamp ON fact_hr_attrition(load_timestamp);

-- =====================================================
-- 4. VIEWS (de Power BI de query)
-- =====================================================

-- View tong hop toan bo thong tin
CREATE OR REPLACE VIEW vw_hr_attrition_full AS
SELECT
    f.fact_key,
    e.employee_number,
    e.age,
    e.gender,
    e.marital_status,
    e.education,
    e.education_field,
    e.distance_from_home,
    e.num_companies_worked,
    e.total_working_years,
    j.job_role,
    j.job_level,
    j.job_involvement,
    d.department,
    t.load_date,
    t.year,
    t.quarter,
    t.month,
    f.attrition,
    f.attrition_label,
    f.monthly_income,
    f.hourly_rate,
    f.daily_rate,
    f.monthly_rate,
    f.percent_salary_hike,
    f.performance_rating,
    f.environment_satisfaction,
    f.job_satisfaction,
    f.relationship_satisfaction,
    f.work_life_balance,
    f.years_at_company,
    f.years_in_current_role,
    f.years_since_last_promotion,
    f.years_with_curr_manager,
    f.business_travel,
    f.over_time,
    f.stock_option_level,
    f.training_times_last_year,
    f.load_timestamp
FROM fact_hr_attrition f
LEFT JOIN dim_employee e ON f.employee_key = e.employee_key
LEFT JOIN dim_job_role j ON f.job_role_key = j.job_role_key
LEFT JOIN dim_department d ON f.department_key = d.department_key
LEFT JOIN dim_time t ON f.time_key = t.time_key;

-- View phan tich attrition theo department
CREATE OR REPLACE VIEW vw_attrition_by_department AS
SELECT
    d.department,
    COUNT(*) as total_employees,
    SUM(f.attrition_label) as attrition_count,
    ROUND(AVG(f.attrition_label) * 100, 2) as attrition_rate_percent,
    ROUND(AVG(f.monthly_income), 2) as avg_monthly_income,
    ROUND(AVG(f.job_satisfaction), 2) as avg_job_satisfaction
FROM fact_hr_attrition f
LEFT JOIN dim_department d ON f.department_key = d.department_key
GROUP BY d.department;

-- View phan tich attrition theo job role
CREATE OR REPLACE VIEW vw_attrition_by_job_role AS
SELECT
    j.job_role,
    j.job_level,
    COUNT(*) as total_employees,
    SUM(f.attrition_label) as attrition_count,
    ROUND(AVG(f.attrition_label) * 100, 2) as attrition_rate_percent,
    ROUND(AVG(f.monthly_income), 2) as avg_monthly_income,
    ROUND(AVG(f.years_at_company), 2) as avg_years_at_company
FROM fact_hr_attrition f
LEFT JOIN dim_job_role j ON f.job_role_key = j.job_role_key
GROUP BY j.job_role, j.job_level;

-- View phan tich demographics
CREATE OR REPLACE VIEW vw_attrition_demographics AS
SELECT
    e.gender,
    e.marital_status,
    CASE
        WHEN e.age < 25 THEN '< 25'
        WHEN e.age BETWEEN 25 AND 34 THEN '25-34'
        WHEN e.age BETWEEN 35 AND 44 THEN '35-44'
        WHEN e.age BETWEEN 45 AND 54 THEN '45-54'
        ELSE '55+'
    END as age_group,
    COUNT(*) as total_employees,
    SUM(f.attrition_label) as attrition_count,
    ROUND(AVG(f.attrition_label) * 100, 2) as attrition_rate_percent
FROM fact_hr_attrition f
LEFT JOIN dim_employee e ON f.employee_key = e.employee_key
GROUP BY e.gender, e.marital_status, age_group;

-- =====================================================
-- 5. GRANT PERMISSIONS (tuy chon)
-- =====================================================

-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO powerbi_user;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_user;
