import os
import sys
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import torch
from torch.utils.data import DataLoader

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.dataset import AQITimeSeriesDataset

def extract_tabular_data(dataset):
    """
    Extracts tabular (flattened) data from the spatio-temporal dataset,
    filtering only for grid cells that have valid CPCB target data.
    """
    X_list = []
    y_list = []
    
    loader = DataLoader(dataset, batch_size=1, shuffle=False)
    
    for x_seq, y_grid, mask_grid in loader:
        # x_seq: (1, seq_len, channels, H, W)
        # We take the features from the LAST day of the sequence for the baseline
        # shape becomes (channels, H, W)
        x_last = x_seq[0, -1, :, :, :].numpy()
        y_val = y_grid[0].numpy()
        mask_val = mask_grid[0].numpy()
        
        # Find spatial indices where we have a ground truth sensor
        valid_y, valid_x = np.where(mask_val == 1.0)
        
        if len(valid_y) == 0:
            continue
            
        # For each valid sensor location, extract the features
        for r, c in zip(valid_y, valid_x):
            features = x_last[:, r, c]
            target = y_val[r, c]
            
            X_list.append(features)
            y_list.append(target)
            
    if len(X_list) == 0:
        return np.array([]), np.array([])
        
    return np.stack(X_list), np.array(y_list)

def train_xgboost_baseline(zarr_path, cpcb_dir):
    print("Preparing XGBoost Baseline datasets...")
    
    # Normally we'd use split='train' and 'val', but for the baseline
    # we'll just extract all available data or mock datasets depending on what's available
    try:
        train_ds = AQITimeSeriesDataset(zarr_path, cpcb_dir, split='train')
        val_ds = AQITimeSeriesDataset(zarr_path, cpcb_dir, split='val')
    except Exception as e:
        print(f"Error loading datasets: {e}")
        return
        
    if len(train_ds) == 0:
        print("No training data available. Cannot train XGBoost baseline.")
        return
        
    X_train, y_train = extract_tabular_data(train_ds)
    X_val, y_val = extract_tabular_data(val_ds)
    
    if len(X_train) == 0:
        print("No valid CPCB targets found in training set. Exiting.")
        return
        
    print(f"Training XGBoost on {len(X_train)} samples...")
    model = xgb.XGBRegressor(
        n_estimators=100, 
        max_depth=6, 
        learning_rate=0.1, 
        objective='reg:squarederror'
    )
    
    model.fit(X_train, y_train)
    
    if len(X_val) > 0:
        preds = model.predict(X_val)
        rmse = np.sqrt(mean_squared_error(y_val, preds))
        mae = mean_absolute_error(y_val, preds)
        r2 = r2_score(y_val, preds)
        print(f"XGBoost Baseline Results on Validation Set:")
        print(f"RMSE: {rmse:.2f} µg/m³")
        print(f"MAE:  {mae:.2f} µg/m³")
        print(f"R²:   {r2:.3f}")
    else:
        print("No validation data available to evaluate.")

if __name__ == "__main__":
    zarr_path = os.path.join(os.getcwd(), 'data', 'processed', 'datacube.zarr')
    cpcb_dir = os.path.join(os.getcwd(), 'data', 'raw', 'cpcb')
    train_xgboost_baseline(zarr_path, cpcb_dir)
