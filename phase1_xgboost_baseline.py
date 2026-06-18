import os
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

in_csv = os.path.join(os.getcwd(), 'data', 'processed', 'station_matched_features.csv')

if not os.path.exists(in_csv):
    print(f"Matched data not found at {in_csv}. Run phase1_cpcb_match.py first.")
    exit(1)

print("Loading tabular matched dataset...")
df = pd.read_csv(in_csv)

# Drop any rows with NaN values in our features or target
df = df.dropna()

if len(df) < 3:
    print("Warning: Very small dataset (mock data). Metrics won't be statistically significant, but the pipeline works.")

# Features and target
# Our target is the ground observed PM2.5 (from CPCB mocks)
# Features are Satellite HCHO (as a proxy/correlate) and Meteorology
X = df[['s5p_hcho', 'era5_temp_2m', 'era5_u_wind', 'era5_v_wind']]
y = df['pm25_obs']

print("Splitting into Train/Test...")
# With real data we would do a temporal or spatial split, but for this mock we do random split
if len(df) > 1:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
else:
    # If dataset is too small, just train and test on the same for pipeline validation
    X_train, X_test, y_train, y_test = X, X, y, y

print("Training XGBoost Regressor Baseline...")
model = xgb.XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42)
model.fit(X_train, y_train)

print("Evaluating...")
preds = model.predict(X_test)

mse = mean_squared_error(y_test, preds)
rmse = np.sqrt(mse)
mae = mean_absolute_error(y_test, preds)

# R2 score might throw a warning if variance is zero, wrap in try/except or just print
try:
    r2 = r2_score(y_test, preds)
except:
    r2 = float('nan')

print("-" * 30)
print("Phase 1 - XGBoost Baseline Metrics")
print("-" * 30)
print(f"RMSE: {rmse:.2f} µg/m³")
print(f"MAE:  {mae:.2f} µg/m³")
print(f"R²:   {r2:.2f}")

out_dir = os.path.join(os.getcwd(), 'models')
os.makedirs(out_dir, exist_ok=True)
out_model = os.path.join(out_dir, 'xgboost_baseline.json')
model.save_model(out_model)
print(f"Saved model to {out_model}")
print("Phase 1 complete! Baseline established.")
