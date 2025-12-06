"""
HR Attrition Prediction - Decision Support System
==================================================
Streamlit Web App cho HR Manager dự đoán nhân viên nghỉ việc
"""

import streamlit as st
import pandas as pd
import numpy as np
import joblib
import os
import json
import plotly.express as px
import plotly.graph_objects as go

# =====================================================
# PAGE CONFIGURATION
# =====================================================
st.set_page_config(
    page_title="HR Attrition Prediction DSS",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# CUSTOM CSS
# =====================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .prediction-box {
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin: 1rem 0;
    }
    .high-risk {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a5a 100%);
        color: white;
    }
    .medium-risk {
        background: linear-gradient(135deg, #ffa726 0%, #fb8c00 100%);
        color: white;
    }
    .low-risk {
        background: linear-gradient(135deg, #66bb6a 0%, #43a047 100%);
        color: white;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        border-left: 4px solid #1f77b4;
    }
    .stSelectbox > div > div {
        background-color: #f0f2f6;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================
# LOAD MODELS
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

@st.cache_resource
def load_models():
    """Load trained models và các artifacts"""
    try:
        lr_model = joblib.load(os.path.join(MODELS_DIR, 'logistic_regression.pkl'))
        rf_model = joblib.load(os.path.join(MODELS_DIR, 'random_forest.pkl'))
        scaler = joblib.load(os.path.join(MODELS_DIR, 'scaler.pkl'))
        label_encoders = joblib.load(os.path.join(MODELS_DIR, 'label_encoders.pkl'))
        feature_cols = joblib.load(os.path.join(MODELS_DIR, 'feature_columns.pkl'))
        
        with open(os.path.join(MODELS_DIR, 'model_info.json'), 'r') as f:
            model_info = json.load(f)
        
        feature_importance = pd.read_csv(os.path.join(MODELS_DIR, 'feature_importance.csv'))
        
        return {
            'lr_model': lr_model,
            'rf_model': rf_model,
            'scaler': scaler,
            'label_encoders': label_encoders,
            'feature_cols': feature_cols,
            'model_info': model_info,
            'feature_importance': feature_importance
        }
    except Exception as e:
        st.error(f"⚠️ Chưa có model! Vui lòng chạy `python train_model.py` trước.")
        return None


# =====================================================
# PREDICTION FUNCTIONS
# =====================================================
def prepare_input(user_input, models):
    """Chuẩn bị input cho model"""
    label_encoders = models['label_encoders']
    feature_cols = models['feature_cols']
    scaler = models['scaler']
    
    # Create DataFrame
    input_df = pd.DataFrame([user_input])
    
    # Encode categorical features
    categorical_features = ['BusinessTravel', 'Department', 'EducationField', 
                           'Gender', 'JobRole', 'MaritalStatus', 'OverTime']
    
    for col in categorical_features:
        if col in input_df.columns:
            input_df[col] = label_encoders[col].transform(input_df[col])
    
    # Reorder columns
    input_df = input_df[feature_cols]
    
    # Scale
    input_scaled = scaler.transform(input_df)
    
    return input_scaled


def get_risk_level(probability):
    """Xác định mức độ rủi ro"""
    if probability >= 0.7:
        return "CAO", "high-risk", "🔴"
    elif probability >= 0.4:
        return "TRUNG BÌNH", "medium-risk", "🟠"
    else:
        return "THẤP", "low-risk", "🟢"


# =====================================================
# MAIN APP
# =====================================================
def main():
    # Header
    st.markdown('<h1 class="main-header">👥 HR Attrition Prediction System</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Hệ thống Hỗ trợ Quyết định - Dự đoán Nhân viên Nghỉ việc</p>', unsafe_allow_html=True)
    
    # Load models
    models = load_models()
    
    if models is None:
        st.stop()
    
    # Sidebar - Model Info
    with st.sidebar:
        st.header("📊 Model Information")
        model_info = models['model_info']
        
        st.metric("Total Samples", f"{model_info['total_samples']:,}")
        st.metric("Training Samples", f"{model_info['train_samples']:,}")
        st.metric("Test Samples", f"{model_info['test_samples']:,}")
        
        st.divider()
        
        st.subheader("🎯 Model Performance")
        metrics = model_info['metrics']
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Logistic Regression**")
            st.write(f"Accuracy: {metrics['logistic_regression']['accuracy']:.2%}")
            st.write(f"ROC-AUC: {metrics['logistic_regression']['roc_auc']:.2%}")
        
        with col2:
            st.write("**Random Forest**")
            st.write(f"Accuracy: {metrics['random_forest']['accuracy']:.2%}")
            st.write(f"ROC-AUC: {metrics['random_forest']['roc_auc']:.2%}")
        
        st.divider()
        
        # Model Selection
        st.subheader("⚙️ Chọn Model")
        selected_model = st.radio(
            "Model để dự đoán:",
            ["Random Forest", "Logistic Regression"],
            index=0
        )
    
    # Main content - Input Form
    st.header("📝 Nhập Thông tin Nhân viên")
    
    # Tabs for different input categories
    tab1, tab2, tab3, tab4 = st.tabs(["👤 Thông tin cá nhân", "💼 Công việc", "💰 Lương & Phúc lợi", "⏱️ Kinh nghiệm"])
    
    with tab1:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            age = st.number_input("Tuổi", min_value=18, max_value=65, value=35)
            gender = st.selectbox("Giới tính", ["Male", "Female"])
            marital_status = st.selectbox("Tình trạng hôn nhân", ["Single", "Married", "Divorced"])
        
        with col2:
            education = st.selectbox(
                "Trình độ học vấn",
                options=[1, 2, 3, 4, 5],
                format_func=lambda x: {1: "Below College", 2: "College", 3: "Bachelor", 4: "Master", 5: "Doctor"}[x],
                index=2
            )
            education_field = st.selectbox(
                "Lĩnh vực học",
                ["Life Sciences", "Medical", "Marketing", "Technical Degree", "Human Resources", "Other"]
            )
        
        with col3:
            distance_from_home = st.slider("Khoảng cách từ nhà (km)", 1, 30, 10)
            num_companies_worked = st.number_input("Số công ty đã làm", min_value=0, max_value=10, value=2)
    
    with tab2:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            department = st.selectbox("Phòng ban", ["Sales", "Research & Development", "Human Resources"])
            job_role = st.selectbox(
                "Vị trí công việc",
                ["Sales Executive", "Research Scientist", "Laboratory Technician", 
                 "Manufacturing Director", "Healthcare Representative", "Manager",
                 "Sales Representative", "Research Director", "Human Resources"]
            )
            job_level = st.selectbox("Cấp bậc công việc", [1, 2, 3, 4, 5], index=1)
        
        with col2:
            job_involvement = st.selectbox(
                "Mức độ tham gia công việc",
                options=[1, 2, 3, 4],
                format_func=lambda x: {1: "Low", 2: "Medium", 3: "High", 4: "Very High"}[x],
                index=2
            )
            job_satisfaction = st.selectbox(
                "Hài lòng với công việc",
                options=[1, 2, 3, 4],
                format_func=lambda x: {1: "Low", 2: "Medium", 3: "High", 4: "Very High"}[x],
                index=2
            )
            environment_satisfaction = st.selectbox(
                "Hài lòng môi trường",
                options=[1, 2, 3, 4],
                format_func=lambda x: {1: "Low", 2: "Medium", 3: "High", 4: "Very High"}[x],
                index=2
            )
        
        with col3:
            business_travel = st.selectbox("Đi công tác", ["Non-Travel", "Travel_Rarely", "Travel_Frequently"])
            over_time = st.selectbox("Làm thêm giờ", ["No", "Yes"])
            work_life_balance = st.selectbox(
                "Cân bằng công việc-cuộc sống",
                options=[1, 2, 3, 4],
                format_func=lambda x: {1: "Bad", 2: "Good", 3: "Better", 4: "Best"}[x],
                index=2
            )
    
    with tab3:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            monthly_income = st.number_input("Lương tháng ($)", min_value=1000, max_value=20000, value=5000, step=100)
            hourly_rate = st.number_input("Lương giờ ($)", min_value=30, max_value=100, value=60)
            daily_rate = st.number_input("Lương ngày ($)", min_value=100, max_value=1500, value=800)
        
        with col2:
            monthly_rate = st.number_input("Monthly Rate ($)", min_value=2000, max_value=27000, value=14000)
            percent_salary_hike = st.slider("% Tăng lương gần nhất", 11, 25, 15)
            stock_option_level = st.selectbox("Cổ phiếu công ty", [0, 1, 2, 3])
        
        with col3:
            performance_rating = st.selectbox(
                "Đánh giá hiệu suất",
                options=[1, 2, 3, 4],
                format_func=lambda x: {1: "Low", 2: "Good", 3: "Excellent", 4: "Outstanding"}[x],
                index=2
            )
            relationship_satisfaction = st.selectbox(
                "Hài lòng quan hệ đồng nghiệp",
                options=[1, 2, 3, 4],
                format_func=lambda x: {1: "Low", 2: "Medium", 3: "High", 4: "Very High"}[x],
                index=2
            )
            training_times_last_year = st.number_input("Số lần đào tạo năm qua", min_value=0, max_value=6, value=3)
    
    with tab4:
        col1, col2 = st.columns(2)
        
        with col1:
            total_working_years = st.number_input("Tổng số năm làm việc", min_value=0, max_value=40, value=10)
            years_at_company = st.number_input("Số năm tại công ty", min_value=0, max_value=40, value=5)
            years_in_current_role = st.number_input("Số năm ở vị trí hiện tại", min_value=0, max_value=20, value=3)
        
        with col2:
            years_since_last_promotion = st.number_input("Số năm kể từ lần thăng chức cuối", min_value=0, max_value=15, value=1)
            years_with_curr_manager = st.number_input("Số năm với quản lý hiện tại", min_value=0, max_value=17, value=3)
    
    # Prediction Button
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        predict_button = st.button("🔮 DỰ ĐOÁN NGUY CƠ NGHỈ VIỆC", type="primary", use_container_width=True)
    
    if predict_button:
        # Prepare input
        user_input = {
            'Age': age,
            'BusinessTravel': business_travel,
            'DailyRate': daily_rate,
            'Department': department,
            'DistanceFromHome': distance_from_home,
            'Education': education,
            'EducationField': education_field,
            'EnvironmentSatisfaction': environment_satisfaction,
            'Gender': gender,
            'HourlyRate': hourly_rate,
            'JobInvolvement': job_involvement,
            'JobLevel': job_level,
            'JobRole': job_role,
            'JobSatisfaction': job_satisfaction,
            'MaritalStatus': marital_status,
            'MonthlyIncome': monthly_income,
            'MonthlyRate': monthly_rate,
            'NumCompaniesWorked': num_companies_worked,
            'OverTime': over_time,
            'PercentSalaryHike': percent_salary_hike,
            'PerformanceRating': performance_rating,
            'RelationshipSatisfaction': relationship_satisfaction,
            'StockOptionLevel': stock_option_level,
            'TotalWorkingYears': total_working_years,
            'TrainingTimesLastYear': training_times_last_year,
            'WorkLifeBalance': work_life_balance,
            'YearsAtCompany': years_at_company,
            'YearsInCurrentRole': years_in_current_role,
            'YearsSinceLastPromotion': years_since_last_promotion,
            'YearsWithCurrManager': years_with_curr_manager
        }
        
        # Prepare and predict
        input_scaled = prepare_input(user_input, models)
        
        if selected_model == "Random Forest":
            model = models['rf_model']
        else:
            model = models['lr_model']
        
        probability = model.predict_proba(input_scaled)[0][1]
        prediction = model.predict(input_scaled)[0]
        
        risk_level, risk_class, emoji = get_risk_level(probability)
        
        # Display Results
        st.header("📊 Kết quả Dự đoán")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown(f"""
            <div class="prediction-box {risk_class}">
                <h1 style="font-size: 3rem; margin: 0;">{emoji}</h1>
                <h2 style="margin: 0.5rem 0;">NGUY CƠ NGHỈ VIỆC: {risk_level}</h2>
                <h1 style="font-size: 4rem; margin: 0.5rem 0;">{probability:.1%}</h1>
                <p style="margin: 0;">Xác suất nghỉ việc theo model {selected_model}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Additional Analysis
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 So sánh 2 Models")
            
            lr_prob = models['lr_model'].predict_proba(input_scaled)[0][1]
            rf_prob = models['rf_model'].predict_proba(input_scaled)[0][1]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=['Logistic Regression', 'Random Forest'],
                y=[lr_prob * 100, rf_prob * 100],
                marker_color=['#1f77b4', '#2ca02c'],
                text=[f"{lr_prob:.1%}", f"{rf_prob:.1%}"],
                textposition='outside'
            ))
            fig.update_layout(
                title="Xác suất nghỉ việc theo từng model",
                yaxis_title="Xác suất (%)",
                yaxis_range=[0, 100],
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🎯 Top 10 Yếu tố Quan trọng")
            
            feature_importance = models['feature_importance'].head(10)
            
            fig = px.bar(
                feature_importance,
                x='importance',
                y='feature',
                orientation='h',
                color='importance',
                color_continuous_scale='Blues'
            )
            fig.update_layout(
                title="Feature Importance (Random Forest)",
                xaxis_title="Importance",
                yaxis_title="",
                height=350,
                yaxis={'categoryorder': 'total ascending'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Recommendations
        st.subheader("💡 Khuyến nghị")
        
        if probability >= 0.7:
            st.error("""
            **Nhân viên có NGUY CƠ CAO nghỉ việc!** Đề xuất:
            - 🔄 Xem xét điều chỉnh lương hoặc phúc lợi
            - 💬 Tổ chức buổi trao đổi 1-1 để hiểu nguyện vọng
            - 🎯 Xem xét cơ hội thăng tiến hoặc đổi vị trí
            - ⏰ Đánh giá lại khối lượng công việc và overtime
            """)
        elif probability >= 0.4:
            st.warning("""
            **Nhân viên có NGUY CƠ TRUNG BÌNH nghỉ việc.** Đề xuất:
            - 📊 Theo dõi sát các chỉ số hài lòng
            - 🎓 Cung cấp thêm cơ hội đào tạo/phát triển
            - 🤝 Cải thiện môi trường làm việc
            """)
        else:
            st.success("""
            **Nhân viên có NGUY CƠ THẤP nghỉ việc.** Đề xuất:
            - ✅ Duy trì các chính sách hiện tại
            - 🌟 Ghi nhận và khen thưởng kịp thời
            - 📈 Tiếp tục phát triển career path
            """)


if __name__ == "__main__":
    main()
