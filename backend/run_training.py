import os
from pathlib import Path
import torch
import torch.optim as optim
import pickle

from simulation.train import train, data_into_dataset
from simulation.rl_model import TransformerFlowPolicy
from simulation.csv_reader import read_csv_with_european_format

# Set device
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {DEVICE}")

# Load CSV data
csv_path = os.getenv(
    "CSV_DATA_PATH",
    str(Path.cwd().parent / "Valmet-HSY-Docs" / "Hackathon_HSY_data.csv")
)

# Check if path exists, otherwise use default
if not os.path.exists(csv_path):
    csv_path = str(Path.cwd() / "data" / "Hackathon_HSY_data.csv")
    if not os.path.exists(csv_path):
        print(f"Warning: CSV file not found at {csv_path}")
        print("Please set CSV_DATA_PATH environment variable or place the file in the correct location")
    
print(f"Reading CSV data from: {csv_path}")

# Read and prepare dataset - use pickle cache if available
pickle_path = "/tmp/dataset.pickle"
if os.path.exists(pickle_path):
    print(f"Loading dataset from pickle cache: {pickle_path}")
    with open(pickle_path, "rb") as f:
        dataset = pickle.load(f)
    print(f"Loaded {len(dataset)} samples from cache")
else:
    print("Processing CSV data (this may take a while)...")
    df = read_csv_with_european_format(csv_path)
    dataset = data_into_dataset(df)
    # Save to pickle for faster loading next time
    print(f"Saving dataset to pickle cache: {pickle_path}")
    with open(pickle_path, "wb") as f:
        pickle.dump(dataset, f)
    print(f"Cached {len(dataset)} samples for future use")

# Initialize model and optimizer
policy = TransformerFlowPolicy(input_shape=[96, 11]).to(DEVICE)
optimizer = optim.Adam(policy.parameters(), lr=1e-3)

# Train with 25 epochs and batch size 64
print("\nStarting training with 25 epochs and batch size 64...")
trained_policy, trained_optimizer = train(
    policy, 
    optimizer, 
    dataset, 
    batch_size=64, 
    epochs=25,
    csv_path=csv_path
)

# Save the trained model
model_save_path = Path(__file__).parent / "simulation" / "model_weights.pth"
torch.save(trained_policy.state_dict(), model_save_path)
print(f"\nModel saved to: {model_save_path}")