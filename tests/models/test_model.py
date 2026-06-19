import os
import sys
import torch
import numpy as np
import pytest
import xarray as xr
import pandas as pd

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from models.convlstm import SpatioTemporalAQIModel, masked_mse_loss
from models.dataset import AQITimeSeriesDataset
from config.grid import LAT, LON

@pytest.fixture
def mock_dataset_files(tmp_path):
    zarr_path = tmp_path / "mock_datacube.zarr"
    cpcb_dir = tmp_path / "cpcb"
    
    # Create mock Zarr with 30 days of data across 2022, 2023, 2024
    dates = pd.date_range("2022-12-15", periods=20, freq="D").append(
        pd.date_range("2023-01-01", periods=10, freq="D")
    ).append(
        pd.date_range("2024-01-01", periods=10, freq="D")
    )
    
    ds = xr.Dataset(
        coords={
            "time": dates,
            "y": LAT,
            "x": LON,
        }
    )
    
    # Add dummy variables
    for var in ['hcho_col', 't2m', 'u10', 'v10', 'blh', 'fire_count', 'aod']:
        ds[var] = (('time', 'y', 'x'), np.random.rand(len(dates), len(LAT), len(LON)))
        
    ds.to_zarr(zarr_path, mode='w')
    
    # Create empty cpcb dirs so it doesn't crash
    for d in dates:
        d_dir = cpcb_dir / d.strftime("%Y-%m-%d")
        d_dir.mkdir(parents=True)
        
    return str(zarr_path), str(cpcb_dir)

def test_temporal_split(mock_dataset_files):
    """
    Tests that the Dataset splits data strictly by year to prevent data leakage.
    Train <= 2022
    Val == 2023
    Test >= 2024
    """
    zarr_path, cpcb_dir = mock_dataset_files
    
    train_ds = AQITimeSeriesDataset(zarr_path, cpcb_dir, seq_len=3, split='train')
    val_ds = AQITimeSeriesDataset(zarr_path, cpcb_dir, seq_len=3, split='val')
    test_ds = AQITimeSeriesDataset(zarr_path, cpcb_dir, seq_len=3, split='test')
    
    # Verify train dates are only 2022 and before
    for idx in train_ds.valid_idx:
        time_val = train_ds.ds.time.values[idx]
        year = pd.to_datetime(time_val).year
        assert year <= 2022, "Temporal leakage: Train set contains future data!"
        
    # Verify val dates are only 2023
    for idx in val_ds.valid_idx:
        time_val = val_ds.ds.time.values[idx]
        year = pd.to_datetime(time_val).year
        assert year == 2023, "Temporal leakage: Val set contains non-2023 data!"
        
    # Verify test dates are only 2024+
    for idx in test_ds.valid_idx:
        time_val = test_ds.ds.time.values[idx]
        year = pd.to_datetime(time_val).year
        assert year >= 2024, "Temporal leakage: Test set contains past data!"

def test_model_forward_and_loss():
    """
    Tests the SpatioTemporalAQIModel forward pass and the masked MSE loss.
    """
    batch_size = 2
    seq_len = 5
    channels = 7
    h, w = len(LAT), len(LON)
    
    # Mock input: (batch, seq_len, channels, H, W)
    x = torch.randn(batch_size, seq_len, channels, h, w)
    
    model = SpatioTemporalAQIModel(in_channels=channels, hidden_dim=16)
    
    # Forward pass
    out = model(x)
    
    assert out.shape == (batch_size, h, w), f"Expected shape {(batch_size, h, w)}, got {out.shape}"
    
    # Mock targets and masks
    targets = torch.randn(batch_size, h, w)
    mask = torch.zeros(batch_size, h, w)
    
    # Put a few "sensors" in the mask
    mask[0, 10, 10] = 1.0
    mask[0, 50, 50] = 1.0
    mask[1, 20, 20] = 1.0
    
    loss = masked_mse_loss(out, targets, mask)
    
    assert loss.requires_grad, "Loss must require gradients for backprop"
    assert not torch.isnan(loss), "Loss should not be NaN"
    
    # Test backward pass
    loss.backward()
    
    # Check that gradients flowed back to the encoder
    has_grad = any(p.grad is not None for p in model.encoder.parameters())
    assert has_grad, "Gradients did not flow back to the encoder"
