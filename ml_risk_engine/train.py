import os
import joblib
import json
from data_pipeline.preprocessor import load_and_preprocess
from models.trainer import train_and_select_best

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    datasets_dir = os.path.join(base_dir, "datasets")
    save_dir = os.path.join(base_dir, "models", "saved")
    
    print(f"--- NetSentinel ML Risk Engine Training ---")
    print(f"Looking for dataset files in: {datasets_dir}")
    
    try:
        X, y, scaler = load_and_preprocess(datasets_dir)
        
        # Save the scaler so the predictor can use it
        os.makedirs(save_dir, exist_ok=True)
        scaler_path = os.path.join(save_dir, "scaler.pkl")
        joblib.dump(scaler, scaler_path)
        print(f"Saved scaler to {scaler_path}")
        
        print("\n--- Model Training ---")
        results, best_name = train_and_select_best(X, y, save_dir=save_dir)
        
        # Save metrics for API endpoint
        metrics_path = os.path.join(save_dir, "training_metrics.json")
        with open(metrics_path, "w") as f:
            json.dump({
                "best_model": best_name,
                "metrics": results
            }, f, indent=2)
            
        print("\nTraining Complete! You can now start the FastAPI server.")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
