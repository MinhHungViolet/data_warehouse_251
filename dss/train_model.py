"""
HR Attrition Prediction - Model Training
=========================================
Huấn luyện Logistic Regression & Random Forest
"""

import pandas as pd
import numpy as np
import joblib
import json
import os
from datetime import datetime
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import warnings
warnings.filterwarnings('ignore')

# =====================================================
# CONFIGURATION
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(os.path.dirname(BASE_DIR), "WA_Fn-UseC_-HR-Employee-Attrition.csv")
MODELS_DIR = os.path.join(BASE_DIR, "models")

os.makedirs(MODELS_DIR, exist_ok=True)

# Features cho model
NUMERICAL_FEATURES = [
    'Age', 'DailyRate', 'DistanceFromHome', 'Education', 'EnvironmentSatisfaction',
    'HourlyRate', 'JobInvolvement', 'JobLevel', 'JobSatisfaction', 'MonthlyIncome',
    'MonthlyRate', 'NumCompaniesWorked', 'PercentSalaryHike', 'PerformanceRating',
    'RelationshipSatisfaction', 'StockOptionLevel', 'TotalWorkingYears',
    'TrainingTimesLastYear', 'WorkLifeBalance', 'YearsAtCompany',
    'YearsInCurrentRole', 'YearsSinceLastPromotion', 'YearsWithCurrManager'
]

CATEGORICAL_FEATURES = [
    'BusinessTravel', 'Department', 'EducationField', 'Gender',
    'JobRole', 'MaritalStatus', 'OverTime'
]

def load_and_preprocess_data():
    """Load và tiền xử lý dữ liệu"""
    print("=" * 60)
    print("LOADING DATA")
    print("=" * 60)
    
    df = pd.read_csv(DATA_PATH)
    print(f"✓ Loaded {len(df)} records from CSV")
    
    # Loại bỏ các cột không cần thiết
    df = df.drop(['EmployeeCount', 'Over18', 'StandardHours', 'EmployeeNumber'], axis=1)
    
    # Encode target variable
    df['Attrition'] = (df['Attrition'] == 'Yes').astype(int)
    
    return df


def encode_features(df, label_encoders=None, fit=True):
    """Encode categorical features"""
    df_encoded = df.copy()
    
    if label_encoders is None:
        label_encoders = {}
    
    for col in CATEGORICAL_FEATURES:
        if fit:
            le = LabelEncoder()
            df_encoded[col] = le.fit_transform(df_encoded[col])
            label_encoders[col] = le
        else:
            df_encoded[col] = label_encoders[col].transform(df_encoded[col])
    
    return df_encoded, label_encoders


def train_models(df):
    """Huấn luyện Logistic Regression và Random Forest"""
    print("\n" + "=" * 60)
    print("TRAINING MODELS")
    print("=" * 60)
    
    # Encode features
    df_encoded, label_encoders = encode_features(df, fit=True)
    
    # Prepare features and target
    feature_cols = NUMERICAL_FEATURES + CATEGORICAL_FEATURES
    X = df_encoded[feature_cols]
    y = df_encoded['Attrition']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    results = {}
    
    # =====================================================
    # 1. LOGISTIC REGRESSION
    # =====================================================
    print("\n[1] Training Logistic Regression...")
    lr_model = LogisticRegression(
        max_iter=1000,
        random_state=42,
        class_weight='balanced'
    )
    lr_model.fit(X_train_scaled, y_train)
    
    # Evaluate
    lr_pred = lr_model.predict(X_test_scaled)
    lr_proba = lr_model.predict_proba(X_test_scaled)[:, 1]
    
    lr_metrics = {
        'accuracy': round(accuracy_score(y_test, lr_pred), 4),
        'precision': round(precision_score(y_test, lr_pred), 4),
        'recall': round(recall_score(y_test, lr_pred), 4),
        'f1': round(f1_score(y_test, lr_pred), 4),
        'roc_auc': round(roc_auc_score(y_test, lr_proba), 4)
    }
    
    print(f"   ✓ Accuracy:  {lr_metrics['accuracy']}")
    print(f"   ✓ Precision: {lr_metrics['precision']}")
    print(f"   ✓ Recall:    {lr_metrics['recall']}")
    print(f"   ✓ F1-Score:  {lr_metrics['f1']}")
    print(f"   ✓ ROC-AUC:   {lr_metrics['roc_auc']}")
    
    results['logistic_regression'] = lr_metrics
    
    # =====================================================
    # 2. RANDOM FOREST
    # =====================================================
    print("\n[2] Training Random Forest...")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        random_state=42,
        class_weight='balanced',
        n_jobs=-1
    )
    rf_model.fit(X_train_scaled, y_train)
    
    # Evaluate
    rf_pred = rf_model.predict(X_test_scaled)
    rf_proba = rf_model.predict_proba(X_test_scaled)[:, 1]
    
    rf_metrics = {
        'accuracy': round(accuracy_score(y_test, rf_pred), 4),
        'precision': round(precision_score(y_test, rf_pred), 4),
        'recall': round(recall_score(y_test, rf_pred), 4),
        'f1': round(f1_score(y_test, rf_pred), 4),
        'roc_auc': round(roc_auc_score(y_test, rf_proba), 4)
    }
    
    print(f"   ✓ Accuracy:  {rf_metrics['accuracy']}")
    print(f"   ✓ Precision: {rf_metrics['precision']}")
    print(f"   ✓ Recall:    {rf_metrics['recall']}")
    print(f"   ✓ F1-Score:  {rf_metrics['f1']}")
    print(f"   ✓ ROC-AUC:   {rf_metrics['roc_auc']}")
    
    results['random_forest'] = rf_metrics
    
    # =====================================================
    # FEATURE IMPORTANCE (Random Forest)
    # =====================================================
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': rf_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n[3] Top 10 Feature Importance (Random Forest):")
    for i, row in feature_importance.head(10).iterrows():
        print(f"   {row['feature']}: {row['importance']:.4f}")
    
    # =====================================================
    # SAVE MODELS
    # =====================================================
    print("\n" + "=" * 60)
    print("SAVING MODELS")
    print("=" * 60)
    
    # Save Logistic Regression
    joblib.dump(lr_model, os.path.join(MODELS_DIR, 'logistic_regression.pkl'))
    print("✓ Saved: logistic_regression.pkl")
    
    # Save Random Forest
    joblib.dump(rf_model, os.path.join(MODELS_DIR, 'random_forest.pkl'))
    print("✓ Saved: random_forest.pkl")
    
    # Save Scaler
    joblib.dump(scaler, os.path.join(MODELS_DIR, 'scaler.pkl'))
    print("✓ Saved: scaler.pkl")
    
    # Save Label Encoders
    joblib.dump(label_encoders, os.path.join(MODELS_DIR, 'label_encoders.pkl'))
    print("✓ Saved: label_encoders.pkl")
    
    # Save Feature columns
    joblib.dump(feature_cols, os.path.join(MODELS_DIR, 'feature_columns.pkl'))
    print("✓ Saved: feature_columns.pkl")
    
    # Save Feature Importance
    feature_importance.to_csv(os.path.join(MODELS_DIR, 'feature_importance.csv'), index=False)
    print("✓ Saved: feature_importance.csv")
    
    # Save Model Metrics
    model_info = {
        'trained_at': datetime.now().isoformat(),
        'total_samples': len(df),
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'features': feature_cols,
        'metrics': results
    }
    
    with open(os.path.join(MODELS_DIR, 'model_info.json'), 'w') as f:
        json.dump(model_info, f, indent=2)
    print("✓ Saved: model_info.json")
    
    print("\n" + "=" * 60)
    print("TRAINING COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    
    return lr_model, rf_model, scaler, label_encoders


if __name__ == "__main__":
    df = load_and_preprocess_data()
    train_models(df)
