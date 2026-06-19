import os
import sys
import numpy as np
import pandas as pd
import xarray as xr
import torch
from torch.utils.data import Dataset

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.grid import LON, LAT, RESOLUTION
from data_pipeline.regrid import get_canonical_grid

class AQITimeSeriesDataset(Dataset):
    def __init__(self, zarr_path, cpcb_dir, seq_len=7, split='train', features=None):
        """
        Args:
            zarr_path (str): Path to the merged Zarr datacube.
            cpcb_dir (str): Path to the directory containing CPCB CSVs (data/raw/cpcb)
            seq_len (int): Number of previous days to use as input sequence.
            split (str): 'train', 'val', or 'test'.
            features (list): List of feature names to extract from Zarr.
        """
        self.zarr_path = zarr_path
        self.cpcb_dir = cpcb_dir
        self.seq_len = seq_len
        self.split = split
        
        if features is None:
            self.features = ['hcho_col', 't2m', 'u10', 'v10', 'blh', 'fire_count', 'aod']
        else:
            self.features = features
            
        self.ds = xr.open_zarr(zarr_path)
        
        # Determine temporal split (strict separation to prevent data leakage)
        # Train: <= 2022
        # Val: 2023
        # Test: 2024
        times = pd.to_datetime(self.ds.time.values)
        if split == 'train':
            valid_idx = np.where(times.year <= 2022)[0]
        elif split == 'val':
            valid_idx = np.where(times.year == 2023)[0]
        elif split == 'test':
            valid_idx = np.where(times.year >= 2024)[0]
        else:
            raise ValueError(f"Unknown split: {split}")
            
        # We need at least seq_len days before the target date
        # Filter indices such that idx - seq_len + 1 >= 0
        self.valid_idx = [i for i in valid_idx if i >= seq_len - 1]
        
        self.target_grid = get_canonical_grid()
        self.lat_bins = np.append(LAT - RESOLUTION/2, [LAT[-1] + RESOLUTION/2])
        self.lon_bins = np.append(LON - RESOLUTION/2, [LON[-1] + RESOLUTION/2])

    def __len__(self):
        return len(self.valid_idx)
        
    def _rasterize_cpcb(self, date_str):
        """
        Reads CPCB CSV for the given date and rasterizes it to match the canonical grid.
        Returns a target array and a mask array.
        """
        csv_path = os.path.join(self.cpcb_dir, date_str, 'ground_truth.csv')
        target = np.zeros((len(LAT), len(LON)), dtype=np.float32)
        mask = np.zeros((len(LAT), len(LON)), dtype=np.float32)
        
        if not os.path.exists(csv_path):
            return target, mask
            
        df = pd.read_csv(csv_path)
        if len(df) == 0:
            return target, mask
            
        # Use simple 2D histogram for PM2.5 to map point to grid
        # We take the mean PM2.5 if multiple sensors fall in the same cell
        sum_pm25, _, _ = np.histogram2d(
            df['lat'].values, df['lon'].values,
            bins=[self.lat_bins, self.lon_bins],
            weights=df['pm25'].values
        )
        count, _, _ = np.histogram2d(
            df['lat'].values, df['lon'].values,
            bins=[self.lat_bins, self.lon_bins]
        )
        
        with np.errstate(divide='ignore', invalid='ignore'):
            avg_pm25 = np.true_divide(sum_pm25, count)
            avg_pm25[~np.isfinite(avg_pm25)] = 0
            
        mask[count > 0] = 1.0
        return avg_pm25.astype(np.float32), mask.astype(np.float32)

    def __getitem__(self, idx):
        target_idx = self.valid_idx[idx]
        seq_indices = range(target_idx - self.seq_len + 1, target_idx + 1)
        
        # Extract features (seq_len, channels, H, W)
        x_seq = []
        for feat in self.features:
            if feat in self.ds.variables:
                # fillna with 0 for simplicity; in reality use interpolation
                val = self.ds[feat].isel(time=list(seq_indices)).fillna(0).values
            else:
                # Missing feature fallback
                val = np.zeros((self.seq_len, len(LAT), len(LON)), dtype=np.float32)
            x_seq.append(val)
            
        # Stack over channels: shape becomes (channels, seq_len, H, W)
        # We need (seq_len, channels, H, W) for PyTorch ConvLSTM
        x_arr = np.stack(x_seq, axis=1).astype(np.float32)
        
        # Get target for the LAST day of the sequence
        target_time = self.ds.time.values[target_idx]
        target_date_str = str(target_time)[:10]
        y_arr, mask_arr = self._rasterize_cpcb(target_date_str)
        
        return torch.tensor(x_arr), torch.tensor(y_arr), torch.tensor(mask_arr)
