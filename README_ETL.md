# HR Attrition Data Warehouse - ETL Process

## Tổng quan
Pipeline ETL hoàn chỉnh để xây dựng Data Warehouse phân tích biến động nhân sự (HR Attrition & Demographics), áp dụng Star Schema với Pandas và PostgreSQL.

## Kiến trúc

### 1. Star Schema Design
```
                    dim_employee
                         |
                         |
    dim_department -- fact_hr_attrition -- dim_job_role
                         |
                         |
                     dim_time
```

### 2. Dimension Tables

**dim_employee** - Thông tin nhân khẩu học
- employee_key (PK)
- employee_number
- age, gender, marital_status
- education, education_field
- distance_from_home
- num_companies_worked, total_working_years

**dim_job_role** - Thông tin công việc
- job_role_key (PK)
- job_role
- job_level, job_involvement

**dim_department** - Phòng ban
- department_key (PK)
- department

**dim_time** - Thời gian
- time_key (PK)
- load_date
- year, quarter, month, week, day

### 3. Fact Table

**fact_hr_attrition** - Dữ liệu biến động nhân sự
- fact_key (PK)
- employee_key, job_role_key, department_key, time_key (FKs)
- attrition, attrition_label
- Measures: monthly_income, performance_rating, satisfaction scores
- Tenure: years_at_company, years_in_current_role, etc.
- Work characteristics: business_travel, over_time, stock_option_level
- Metadata: load_timestamp, etl_batch_id

## Cách sử dụng

### Bước 1: Khởi tạo Database
```powershell
# Kết nối PostgreSQL
psql -U postgres

# Tạo database
CREATE DATABASE hr_data_warehouse;

# Chạy script khởi tạo schema
\c hr_data_warehouse
\i init_db.sql
```

### Bước 2: Chạy ETL Process
```powershell
# Đảm bảo các thư viện đã cài đặt
pip install pandas psycopg2-binary

# Chạy ETL
python etl_process_pandas.py
```

### Bước 3: Kiểm tra dữ liệu
```sql
-- Kiểm tra số lượng records
SELECT 'dim_employee' as table_name, COUNT(*) as record_count FROM dim_employee
UNION ALL
SELECT 'dim_job_role', COUNT(*) FROM dim_job_role
UNION ALL
SELECT 'dim_department', COUNT(*) FROM dim_department
UNION ALL
SELECT 'dim_time', COUNT(*) FROM dim_time
UNION ALL
SELECT 'fact_hr_attrition', COUNT(*) FROM fact_hr_attrition;

-- Xem dữ liệu tổng hợp
SELECT * FROM vw_hr_attrition_full LIMIT 10;

-- Phân tích attrition theo department
SELECT * FROM vw_attrition_by_department;
```

## ETL Process Details

### Extract
- Nguồn: CSV file `WA_Fn-UseC_-HR-Employee-Attrition.csv`
- Tool: Pandas với read_csv
- Validation: Kiểm tra số lượng records (1,470 records)

### Transform
1. **Data Cleaning**
   - Xóa cột không có ý nghĩa: EmployeeCount, Over18, StandardHours
   - Kiểm tra null values (0 nulls trong dataset)

2. **Data Type Conversion**
   - Age → Integer
   - MonthlyIncome → Float
   - EmployeeNumber → Integer

3. **Feature Engineering**
   - Tạo Attrition_Label (0/1)
   - Chuẩn hóa tên cột theo snake_case

4. **Dimensional Modeling**
   - Tách dimension tables với distinct values
   - Tạo surrogate keys tự động
   - Thêm timestamps cho auditing

5. **Fact Table Construction**
   - Join dimensions để lấy foreign keys
   - Chọn measures và attributes
   - Thêm ETL metadata (batch_id, timestamp)

### Load
- Target: PostgreSQL tables
- Mode: Overwrite (full refresh)
- Tool: psycopg2 với execute_values (bulk insert)
- Logging: Chi tiết từng bước với timestamps

## Views cho Power BI

### vw_hr_attrition_full
View tổng hợp toàn bộ thông tin từ fact và dimensions - dùng cho detailed analysis

### vw_attrition_by_department
Phân tích attrition rate, avg income, satisfaction theo department

### vw_attrition_by_job_role
Phân tích attrition rate, avg income, tenure theo job role

### vw_attrition_demographics
Phân tích attrition theo demographics (gender, marital status, age group)

## Monitoring & Logging

### Log File
- File: `etl_process_pandas.log`
- Format: timestamp - name - level - message
- Outputs: File + Console

### ETL Metrics
- Batch ID: YYYYMMDD_HHMMSS
- Record counts cho mỗi table
- Execution status cho từng phase
- Error tracking với full stack trace

## Kết nối với Power BI

### Connection String
```
Server: localhost
Database: hr_data_warehouse
Authentication: Database (postgres/250904)
```

### Recommended Views
- vw_hr_attrition_full (chi tiết)
- vw_attrition_by_department (tổng hợp)
- vw_attrition_by_job_role (tổng hợp)
- vw_attrition_demographics (tổng hợp)

### Direct Query vs Import
- Import mode: Khuyến nghị cho dataset nhỏ (<1M rows)
- DirectQuery: Nếu cần real-time data

## Troubleshooting

### Lỗi kết nối PostgreSQL
```
Error: connection to server failed
Solution:
- Kiểm tra PostgreSQL đang chạy
- Verify port 5432
- Check password (250904)
```

### Lỗi Import
```
Error: ModuleNotFoundError
Solution:
pip install pandas psycopg2-binary
```

### Lỗi Schema
```
Error: relation does not exist
Solution:
- Chạy init_db.sql trước
- Verify đã connect đúng database
```

## Trạng thái hiện tại

### ✅ Đã hoàn thành:
- Database schema với Star Schema
- ETL pipeline với pandas
- Data loading thành công (1,470 records)
- 4 analytical views
- Comprehensive logging

### 📊 Thống kê dữ liệu:
```
dim_employee      | 1,470 records
dim_job_role      | 9 records
dim_department    | 3 records
dim_time          | 1 record
fact_hr_attrition | 1,470 records
```

## Next Steps

1. **Visualization (Power BI)**
   - Kết nối đến PostgreSQL
   - Tạo dashboard attrition analysis
   - Interactive filters và drill-down

2. **DSS (Machine Learning + Web)**
   - Export data từ vw_hr_attrition_full
   - Train models dự đoán attrition (Random Forest, XGBoost)
   - Xây dựng web interface với Streamlit
   - ML prediction interface

3. **Incremental Load**
   - Thay overwrite bằng append
   - Implement SCD Type 2 cho dimensions
   - Add change tracking

4. **Data Quality Checks**
   - Validate data ranges
   - Check for duplicates
   - Monitor data freshness

## Files trong dự án

- `init_db.sql` - Database schema và views
- `etl_process_pandas.py` - ETL pipeline chính
- `etl_process.py` - ETL với PySpark (alternative)
- `README_ETL.md` - Documentation này
- `WA_Fn-UseC_-HR-Employee-Attrition.csv` - Raw data
- `etl_process_pandas.log` - Execution logs
- `jars/` - JDBC drivers (cho PySpark)
