import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import logging
import os

# =====================================================
# LOGGING CONFIGURATION
# =====================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('etl_process_pandas.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =====================================================
# CONFIGURATION
# =====================================================
CSV_PATH = "F:/HK251/data_warehouse/WA_Fn-UseC_-HR-Employee-Attrition.csv"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "hr_data_warehouse"
DB_USER = "postgres"
DB_PASSWORD = "250904"

# ETL Batch ID để tracking
ETL_BATCH_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

def get_db_connection():
    """Create database connection"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def load_dimension_table(df, table_name, columns, key_column=None):
    """Load dimension table with deduplication"""
    logger.info(f"Loading {table_name}...")

    # Get distinct values
    if key_column:
        dim_df = df[columns].drop_duplicates(subset=[key_column])
    else:
        dim_df = df[columns].drop_duplicates()

    # Reset index and add surrogate key
    dim_df = dim_df.reset_index(drop=True)
    # Use table name without 'dim_' prefix for key name
    table_short = table_name.replace('dim_', '')
    key_name = f"{table_short}_key"
    dim_df[key_name] = range(1, len(dim_df) + 1)

    # Add timestamps
    dim_df['created_at'] = datetime.now()
    
    # Check if table has updated_at column
    conn = get_db_connection()
    has_updated_at = False
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = '{table_name}' AND column_name = 'updated_at'
            """)
            has_updated_at = cur.fetchone() is not None
    finally:
        conn.close()
    
    if has_updated_at:
        dim_df['updated_at'] = datetime.now()
        cols = [key_name] + columns + ['created_at', 'updated_at']
    else:
        cols = [key_name] + columns + ['created_at']
    
    dim_df = dim_df[cols]

    # Load to database
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Clear existing data
            cur.execute(f"TRUNCATE TABLE {table_name} CASCADE")

            # Insert data
            columns_list = dim_df.columns.tolist()
            # Convert numpy types to Python types
            values = [tuple(row) for row in dim_df.astype(object).values]

            query = f"""
                INSERT INTO {table_name} ({', '.join(columns_list)})
                VALUES %s
            """
            execute_values(cur, query, values)

        conn.commit()
        logger.info(f"Loaded {len(dim_df)} records into {table_name}")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error loading {table_name}: {e}")
        raise
    finally:
        conn.close()

    return dim_df

def load_fact_table(df, dim_dfs):
    """Load fact table with foreign keys"""
    logger.info("Loading fact_hr_attrition...")

    # Create mappings for foreign keys
    employee_map = dict(zip(dim_dfs['dim_employee']['employee_number'],
                           dim_dfs['dim_employee']['employee_key']))
    job_role_map = dict(zip(dim_dfs['dim_job_role']['job_role'],
                           dim_dfs['dim_job_role']['job_role_key']))
    department_map = dict(zip(dim_dfs['dim_department']['department'],
                             dim_dfs['dim_department']['department_key']))
    time_key = dim_dfs['dim_time']['time_key'].iloc[0]

    # Create fact records
    fact_records = []
    for _, row in df.iterrows():
        fact_record = (
            int(employee_map.get(row['employee_number'])),
            int(job_role_map.get(row['job_role'])),
            int(department_map.get(row['department'])),
            int(time_key),
            str(row['attrition']),
            int(row['attrition_label']),
            float(row['monthly_income']),
            float(row['hourly_rate']),
            float(row['daily_rate']),
            float(row['monthly_rate']),
            int(row['percent_salary_hike']),
            int(row['performance_rating']),
            int(row['environment_satisfaction']),
            int(row['job_satisfaction']),
            int(row['relationship_satisfaction']),
            int(row['work_life_balance']),
            int(row['years_at_company']),
            int(row['years_in_current_role']),
            int(row['years_since_last_promotion']),
            int(row['years_with_curr_manager']),
            str(row['business_travel']),
            str(row['over_time']),
            int(row['stock_option_level']),
            int(row['training_times_last_year']),
            datetime.now(),
            ETL_BATCH_ID
        )
        fact_records.append(fact_record)

    # Load to database
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Clear existing data
            cur.execute("TRUNCATE TABLE fact_hr_attrition CASCADE")

            # Insert data
            query = """
                INSERT INTO fact_hr_attrition (
                    employee_key, job_role_key, department_key, time_key,
                    attrition, attrition_label, monthly_income, hourly_rate,
                    daily_rate, monthly_rate, percent_salary_hike,
                    performance_rating, environment_satisfaction, job_satisfaction,
                    relationship_satisfaction, work_life_balance,
                    years_at_company, years_in_current_role, years_since_last_promotion,
                    years_with_curr_manager, business_travel, over_time,
                    stock_option_level, training_times_last_year,
                    load_timestamp, etl_batch_id
                ) VALUES %s
            """
            execute_values(cur, query, fact_records)

        conn.commit()
        logger.info(f"Loaded {len(fact_records)} records into fact_hr_attrition")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error loading fact_hr_attrition: {e}")
        raise
    finally:
        conn.close()

def main():
    try:
        logger.info(f"Starting ETL Process - Batch ID: {ETL_BATCH_ID}")

        # =====================================================
        # 1. EXTRACT - Đọc dữ liệu từ CSV
        # =====================================================
        logger.info(f"Reading CSV file from: {CSV_PATH}")

        if not os.path.exists(CSV_PATH):
            raise FileNotFoundError(f"CSV file not found: {CSV_PATH}")

        df = pd.read_csv(CSV_PATH)
        total_records = len(df)
        logger.info(f"Total records extracted: {total_records}")

        # =====================================================
        # 2. TRANSFORM - Data Quality & Cleaning
        # =====================================================
        logger.info("Starting data transformation...")

        # 2.1. Xóa các cột không có ý nghĩa phân tích
        df_clean = df.drop(["EmployeeCount", "Over18", "StandardHours"], axis=1)
        logger.info("Dropped redundant columns: EmployeeCount, Over18, StandardHours")

        # 2.2. Xử lý missing values (nếu có)
        null_counts = df_clean.isnull().sum()
        logger.info(f"Null value check completed. Total nulls: {null_counts.sum()}")

        # 2.3. Data type validation & conversion
        df_clean = df_clean.copy()
        df_clean['Age'] = df_clean['Age'].astype(int)
        df_clean['MonthlyIncome'] = df_clean['MonthlyIncome'].astype(float)
        df_clean['EmployeeNumber'] = df_clean['EmployeeNumber'].astype(int)

        # 2.4. Tạo Attrition Label và chuẩn hóa tên cột
        df_clean['Attrition_Label'] = (df_clean['Attrition'] == 'Yes').astype(int)

        # Chuẩn hóa tên cột theo snake_case để match với database schema
        column_mapping = {
            'EmployeeNumber': 'employee_number',
            'Age': 'age',
            'Gender': 'gender',
            'MaritalStatus': 'marital_status',
            'Education': 'education',
            'EducationField': 'education_field',
            'DistanceFromHome': 'distance_from_home',
            'NumCompaniesWorked': 'num_companies_worked',
            'TotalWorkingYears': 'total_working_years',
            'JobRole': 'job_role',
            'JobLevel': 'job_level',
            'JobInvolvement': 'job_involvement',
            'Department': 'department',
            'Attrition': 'attrition',
            'Attrition_Label': 'attrition_label',
            'MonthlyIncome': 'monthly_income',
            'HourlyRate': 'hourly_rate',
            'DailyRate': 'daily_rate',
            'MonthlyRate': 'monthly_rate',
            'PercentSalaryHike': 'percent_salary_hike',
            'PerformanceRating': 'performance_rating',
            'EnvironmentSatisfaction': 'environment_satisfaction',
            'JobSatisfaction': 'job_satisfaction',
            'RelationshipSatisfaction': 'relationship_satisfaction',
            'WorkLifeBalance': 'work_life_balance',
            'YearsAtCompany': 'years_at_company',
            'YearsInCurrentRole': 'years_in_current_role',
            'YearsSinceLastPromotion': 'years_since_last_promotion',
            'YearsWithCurrManager': 'years_with_curr_manager',
            'BusinessTravel': 'business_travel',
            'OverTime': 'over_time',
            'StockOptionLevel': 'stock_option_level',
            'TrainingTimesLastYear': 'training_times_last_year'
        }

        df_clean = df_clean.rename(columns=column_mapping)

        logger.info("Data cleaning and transformation completed")

        # =====================================================
        # 3. DIMENSION TABLES CREATION
        # =====================================================
        logger.info("Creating dimension tables...")

        dim_dfs = {}

        # 3.1. DIM_EMPLOYEE
        employee_cols = ['employee_number', 'age', 'gender', 'marital_status', 'education',
                        'education_field', 'distance_from_home', 'num_companies_worked', 'total_working_years']
        dim_employee = load_dimension_table(df_clean, 'dim_employee', employee_cols, 'employee_number')
        dim_dfs['dim_employee'] = dim_employee

        # 3.2. DIM_JOB_ROLE
        job_role_cols = ['job_role', 'job_level', 'job_involvement']
        dim_job_role = load_dimension_table(df_clean, 'dim_job_role', job_role_cols, 'job_role')
        dim_dfs['dim_job_role'] = dim_job_role

        # 3.3. DIM_DEPARTMENT
        department_cols = ['department']
        dim_department = load_dimension_table(df_clean, 'dim_department', department_cols, 'department')
        dim_dfs['dim_department'] = dim_department

        # 3.4. DIM_TIME
        time_df = pd.DataFrame({
            'time_key': [1],
            'load_date': [datetime.now().date()],
            'year': [datetime.now().year],
            'quarter': [((datetime.now().month - 1) // 3) + 1],
            'month': [datetime.now().month],
            'week': [datetime.now().isocalendar()[1]],
            'day': [datetime.now().day],
            'created_at': [datetime.now()]
        })

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE dim_time CASCADE")
                execute_values(cur, """
                    INSERT INTO dim_time (time_key, load_date, year, quarter, month, week, day, created_at)
                    VALUES %s
                """, [tuple(time_df.astype(object).iloc[0])])
            conn.commit()
        finally:
            conn.close()

        dim_dfs['dim_time'] = time_df
        logger.info("dim_time created with 1 record")

        # =====================================================
        # 4. FACT TABLE CREATION
        # =====================================================
        load_fact_table(df_clean, dim_dfs)

        # =====================================================
        # 5. DATA QUALITY SUMMARY
        # =====================================================
        logger.info("=" * 60)
        logger.info("ETL PROCESS COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info(f"Batch ID: {ETL_BATCH_ID}")
        logger.info(f"Total records processed: {total_records}")
        logger.info(f"dim_employee records: {len(dim_employee)}")
        logger.info(f"dim_job_role records: {len(dim_job_role)}")
        logger.info(f"dim_department records: {len(dim_department)}")
        logger.info(f"dim_time records: 1")
        logger.info(f"fact_hr_attrition records: {total_records}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"ETL Process failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()