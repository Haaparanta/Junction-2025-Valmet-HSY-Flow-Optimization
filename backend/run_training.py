#!/usr/bin/env python3
"""
Simple training script for the RL model.

This script loads data, trains the model, and saves the trained weights.
"""

import os
from pathlib import Path
import torch

from simulation.train import train, data_into_dataset
from simulation.csv_reader import read_csv_with_european_format


def main():
    # Configuration
    EPOCHS = 50  # Reduced from 100
    BATCH_SIZE = 32
    LEARNING_RATE = 5e-4  # Lower learning rate for more stable training
    
    # Path to CSV data
    csv_path = os.getenv(
        "CSV_DATA_PATH",
        str(
            Path(__file__).parent.parent
            / "Valmet-HSY-Docs"
            / "Hackathon_HSY_data.csv"
        ),
    )
    
    print("=== Training Configuration ===")
    print(f"CSV data path: {csv_path}")
    print(f"Epochs: {EPOCHS}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")
    print()
    
    # Check if CSV exists
    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found at {csv_path}")
        print("Please set CSV_DATA_PATH environment variable to the correct path.")
        return
    
    # Load data
    print("Loading CSV data...")
    df = read_csv_with_european_format(csv_path)
    print(f"Loaded {len(df)} rows from CSV")
    
    # Convert to training dataset
    print("Creating training dataset...")
    dataset = data_into_dataset(df)
    
    # Train model
    print(f"\nStarting training for {EPOCHS} epochs...")
    print("=" * 50)
    trained_policy = train(
        dataset, 
        batch_size=BATCH_SIZE, 
        epochs=EPOCHS,
        csv_path=csv_path,
    )
    
    # Save model weights
    output_path = Path(__file__).parent / "simulation" / "model_weights.pth"
    torch.save(trained_policy.state_dict(), output_path)
    print("\n=== Training Complete ===")
    print(f"Model weights saved to: {output_path}")


if __name__ == "__main__":
    main()
