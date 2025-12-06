from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, current_timestamp, lit, monotonically_increasing_id
from pyspark.sql.types import IntegerType, StringType, DoubleType
from datetime import datetime
import logging

# =====================================================
# LOGGING CONFIGURATION
# =====================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('etl_process.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =====================================================
# CONFIGURATION
# =====================================================
CSV_PATH = "F:/HK251/data_warehouse/WA_Fn-UseC_-HR-Employee-Attrition.csv"
JDBC_DRIVER_PATH = "file:///F:/HK251/data_warehouse/jars/postgresql-42.7.8.jar"  # Windows path format
DB_URL = "jdbc:postgresql://localhost:5432/hr_data_warehouse"
DB_USER = "postgres"
DB_PASSWORD = "250904"

db_properties = {
    "user": DB_USER,
    "password": DB_PASSWORD,
    "driver": "org.postgresql.Driver"
}

# ETL Batch ID để tracking
ETL_BATCH_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

try:
    logger.info(f"Starting ETL Process - Batch ID: {ETL_BATCH_ID}")
    
    # Check Java installation
    import subprocess
    try:
        java_version = subprocess.check_output(['java', '-version'], stderr=subprocess.STDOUT, text=True)
        logger.info(f"Java version: {java_version.split('\\n')[0]}")
    except Exception as e:
        logger.error(f"Java not found or not accessible: {e}")
        logger.error("Please ensure Java 8+ is installed and JAVA_HOME is set")
        raise
    
    # =====================================================
    # 1. KHỞI TẠO SPARK SESSION
    # =====================================================
    logger.info("Initializing Spark Session...")
    spark = SparkSession.builder \
        .appName("HR_ETL_Job") \
        .config("spark.jars", JDBC_DRIVER_PATH) \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "2g") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.hadoop.fs.file.impl", "org.apache.hadoop.fs.LocalFileSystem") \
        .config("spark.driver.host", "localhost") \
        .config("spark.sql.warehouse.dir", "file:///tmp/spark-warehouse") \
        .getOrCreate()
    
    logger.info("Spark Session created successfully")
    
    # =====================================================
    # 2. EXTRACT - ĐỌC DỮ LIỆU TỪ CSV
    # =====================================================
    logger.info(f"Reading CSV file from: {CSV_PATH}")
    df = spark.read.csv(CSV_PATH, header=True, inferSchema=True)
    
    total_records = df.count()
    logger.info(f"Total records extracted: {total_records}")
    
    # =====================================================
    # 3. TRANSFORM - DATA QUALITY & CLEANING
    # =====================================================
    logger.info("Starting data transformation...")
    
    # 3.1. Xóa các cột không có ý nghĩa phân tích
    df_clean = df.drop("EmployeeCount", "Over18", "StandardHours")
    logger.info("Dropped redundant columns: EmployeeCount, Over18, StandardHours")
    
    # 3.2. Xử lý missing values (nếu có)
    null_counts = df_clean.select([col(c).isNull().cast("int").alias(c) for c in df_clean.columns])
    null_summary = null_counts.agg(*[sum(col(c)).alias(c) for c in null_counts.columns])
    logger.info(f"Null value check completed")
    
    # 3.3. Data type validation & conversion
    df_clean = df_clean.withColumn("Age", col("Age").cast(IntegerType())) \
                       .withColumn("MonthlyIncome", col("MonthlyIncome").cast(DoubleType())) \
                       .withColumn("EmployeeNumber", col("EmployeeNumber").cast(IntegerType()))
    
    # 3.4. Tạo Attrition Label
    df_clean = df_clean.withColumn("Attrition_Label", 
                                   when(col("Attrition") == "Yes", 1).otherwise(0))
    
    logger.info("Data cleaning and transformation completed")
    
    # =====================================================
    # 4. DIMENSION TABLES CREATION
    # =====================================================
    logger.info("Creating dimension tables...")
    
    # 4.1. DIM_EMPLOYEE
    dim_employee = df_clean.select(
        monotonically_increasing_id().alias("employee_key"),
        col("EmployeeNumber").alias("employee_number"),
        col("Age").alias("age"),
        col("Gender").alias("gender"),
        col("MaritalStatus").alias("marital_status"),
        col("Education").alias("education"),
        col("EducationField").alias("education_field"),
        col("DistanceFromHome").alias("distance_from_home"),
        col("NumCompaniesWorked").alias("num_companies_worked"),
        col("TotalWorkingYears").alias("total_working_years")
    ).distinct()
    
    dim_employee = dim_employee.withColumn("created_at", current_timestamp()) \
                               .withColumn("updated_at", current_timestamp())
    
    logger.info(f"dim_employee created with {dim_employee.count()} records")
    
    # 4.2. DIM_JOB_ROLE
    dim_job_role = df_clean.select(
        col("JobRole").alias("job_role"),
        col("JobLevel").alias("job_level"),
        col("JobInvolvement").alias("job_involvement")
    ).distinct()
    
    dim_job_role = dim_job_role.withColumn("job_role_key", monotonically_increasing_id()) \
                               .withColumn("created_at", current_timestamp()) \
                               .select("job_role_key", "job_role", "job_level", "job_involvement", "created_at")
    
    logger.info(f"dim_job_role created with {dim_job_role.count()} records")
    
    # 4.3. DIM_DEPARTMENT
    dim_department = df_clean.select(
        col("Department").alias("department")
    ).distinct()
    
    dim_department = dim_department.withColumn("department_key", monotonically_increasing_id()) \
                                   .withColumn("created_at", current_timestamp()) \
                                   .select("department_key", "department", "created_at")
    
    logger.info(f"dim_department created with {dim_department.count()} records")
    
    # 4.4. DIM_TIME
    from pyspark.sql.functions import year, quarter, month, weekofyear, dayofmonth
    
    dim_time = spark.createDataFrame([(datetime.now().date(),)], ["load_date"])
    dim_time = dim_time.withColumn("time_key", monotonically_increasing_id()) \
                       .withColumn("year", year(col("load_date"))) \
                       .withColumn("quarter", quarter(col("load_date"))) \
                       .withColumn("month", month(col("load_date"))) \
                       .withColumn("week", weekofyear(col("load_date"))) \
                       .withColumn("day", dayofmonth(col("load_date"))) \
                       .withColumn("created_at", current_timestamp()) \
                       .select("time_key", "load_date", "year", "quarter", "month", "week", "day", "created_at")
    
    logger.info(f"dim_time created with {dim_time.count()} records")
    
    # =====================================================
    # 5. FACT TABLE CREATION
    # =====================================================
    logger.info("Creating fact table...")
    
    # Join với dimensions để lấy keys
    fact_table = df_clean.join(dim_employee, 
                               df_clean.EmployeeNumber == dim_employee.employee_number, 
                               "left") \
                         .join(dim_job_role, 
                               df_clean.JobRole == dim_job_role.job_role, 
                               "left") \
                         .join(dim_department, 
                               df_clean.Department == dim_department.department, 
                               "left") \
                         .crossJoin(dim_time)
    
    # Chọn các cột cho fact table
    fact_hr_attrition = fact_table.select(
        col("employee_key"),
        col("job_role_key"),
        col("department_key"),
        col("time_key"),
        col("Attrition").alias("attrition"),
        col("Attrition_Label").alias("attrition_label"),
        col("MonthlyIncome").alias("monthly_income"),
        col("HourlyRate").alias("hourly_rate"),
        col("DailyRate").alias("daily_rate"),
        col("MonthlyRate").alias("monthly_rate"),
        col("PercentSalaryHike").alias("percent_salary_hike"),
        col("PerformanceRating").alias("performance_rating"),
        col("EnvironmentSatisfaction").alias("environment_satisfaction"),
        col("JobSatisfaction").alias("job_satisfaction"),
        col("RelationshipSatisfaction").alias("relationship_satisfaction"),
        col("WorkLifeBalance").alias("work_life_balance"),
        col("YearsAtCompany").alias("years_at_company"),
        col("YearsInCurrentRole").alias("years_in_current_role"),
        col("YearsSinceLastPromotion").alias("years_since_last_promotion"),
        col("YearsWithCurrManager").alias("years_with_curr_manager"),
        col("BusinessTravel").alias("business_travel"),
        col("OverTime").alias("over_time"),
        col("StockOptionLevel").alias("stock_option_level"),
        col("TrainingTimesLastYear").alias("training_times_last_year")
    ).withColumn("load_timestamp", current_timestamp()) \
     .withColumn("etl_batch_id", lit(ETL_BATCH_ID))
    
    logger.info(f"fact_hr_attrition created with {fact_hr_attrition.count()} records")
    
    # =====================================================
    # 6. LOAD - GHI DỮ LIỆU VÀO POSTGRESQL
    # =====================================================
    logger.info("Loading data into PostgreSQL...")
    
    # Load Dimension Tables
    logger.info("Loading dim_employee...")
    dim_employee.write.jdbc(
        url=DB_URL,
        table="dim_employee",
        mode="overwrite",
        properties=db_properties
    )
    
    logger.info("Loading dim_job_role...")
    dim_job_role.write.jdbc(
        url=DB_URL,
        table="dim_job_role",
        mode="overwrite",
        properties=db_properties
    )
    
    logger.info("Loading dim_department...")
    dim_department.write.jdbc(
        url=DB_URL,
        table="dim_department",
        mode="overwrite",
        properties=db_properties
    )
    
    logger.info("Loading dim_time...")
    dim_time.write.jdbc(
        url=DB_URL,
        table="dim_time",
        mode="overwrite",
        properties=db_properties
    )
    
    # Load Fact Table
    logger.info("Loading fact_hr_attrition...")
    fact_hr_attrition.write.jdbc(
        url=DB_URL,
        table="fact_hr_attrition",
        mode="overwrite",
        properties=db_properties
    )
    
    # =====================================================
    # 7. DATA QUALITY SUMMARY
    # =====================================================
    logger.info("=" * 60)
    logger.info("ETL PROCESS COMPLETED SUCCESSFULLY")
    logger.info("=" * 60)
    logger.info(f"Batch ID: {ETL_BATCH_ID}")
    logger.info(f"Total records processed: {total_records}")
    logger.info(f"dim_employee records: {dim_employee.count()}")
    logger.info(f"dim_job_role records: {dim_job_role.count()}")
    logger.info(f"dim_department records: {dim_department.count()}")
    logger.info(f"dim_time records: {dim_time.count()}")
    logger.info(f"fact_hr_attrition records: {fact_hr_attrition.count()}")
    logger.info("=" * 60)
    
    spark.stop()
    logger.info("Spark session stopped")
    
except Exception as e:
    logger.error(f"ETL Process failed: {str(e)}", exc_info=True)
    if 'spark' in locals():
        spark.stop()
    raise