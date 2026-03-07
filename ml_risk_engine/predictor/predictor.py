import os
import joblib
import random
from feature_extractor.extractor import extract_features

class RiskPredictor:
    def __init__(self, models_dir="models/saved"):
        self.models_dir = models_dir
        self.model = None
        self.scaler = None
        self.is_mock = True
        self.reload()

    def reload(self):
        """Try to load the trained model and scaler. If missing, fallback to mock mode."""
        import sys
        
        # Determine base directory depending on if we are bundled or not
        if getattr(sys, 'frozen', False):
             # When running as a PyInstaller executable, find models next to the .exe
             base_path = os.path.dirname(sys.executable)
             # NSIS deposits the models directory directly in the same parent dir usually or inside ml_risk_engine depending on structure
             models_path = os.path.join(base_path, "ml_risk_engine", "models", "saved")
             if not os.path.exists(models_path):
                 models_path = os.path.join(base_path, "models", "saved")
        else:
             # Normal python execution
             base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
             models_path = os.path.join(base_path, "models", "saved")
             
        model_file = os.path.join(models_path, "best_model.pkl")
        scaler_file = os.path.join(models_path, "scaler.pkl")
        
        print(f"RiskPredictor: Looking for models in {models_path}")
        
        if os.path.exists(model_file) and os.path.exists(scaler_file):
            try:
                self.model = joblib.load(model_file)
                self.scaler = joblib.load(scaler_file)
                self.is_mock = False
                print("RiskPredictor: Successfully loaded trained ML model.")
            except Exception as e:
                print(f"RiskPredictor ERROR loading model: {e}. Falling back to mock mode.")
                self.is_mock = True
        else:
            print("RiskPredictor: No trained model found. Using heuristic mock predictor.")
            self.is_mock = True

    def predict(self, session: dict) -> dict:
        """
        Takes a raw DeepShark session dictionary and returns the risk prediction.
        """
        if self.is_mock:
            return self._mock_predict(session)
            
        try:
            # 1. Extract features into DataFrame shape
            X_df = extract_features(session)
            
            # 2. Scale numeric features
            numeric_cols = ["flow_duration", "total_packets", "total_bytes", "avg_packet_size", "packet_rate", "byte_rate", "syn_count", "ack_count", "fin_count", "rst_count"]
            X_df[numeric_cols] = self.scaler.transform(X_df[numeric_cols])
            
            # 3. Predict probability and class
            probs = self.model.predict_proba(X_df)[0]  # [prob_benign, prob_malicious]
            pred = self.model.predict(X_df)[0]         # 0 = benign, 1 = malicious
            
            if hasattr(self.model, "classes_") and len(self.model.classes_) == 2:
                # Assuming index 1 is Malicious based on our training setup 
                # (where 0=Benign, 1=Malicious)
                risk_score = float(probs[1]) 
            else:
                risk_score = 0.9 if pred == 1 else 0.1
                
            return {
                "src_ip": session.get("src_ip"),
                "dst_ip": session.get("dst_ip"),
                "prediction": "Malicious" if pred == 1 else "Benign",
                "risk_score": round(risk_score, 3),
                "is_mock": False
            }
            
        except Exception as e:
            # Fallback if something fails during live inference
            print(f"Prediction error: {e}")
            return self._mock_predict(session)

    def _mock_predict(self, session: dict) -> dict:
        """Heuristic rules to act as a fallback when no model is trained."""
        packet_rate = session.get("packet_rate", 0)
        byte_rate = session.get("byte_rate", 0)
        
        # Simple heuristic: huge packet rates or tiny byte rate / packet rate combos simulate attacks
        if packet_rate > 5000:
            risk = min(0.99, random.uniform(0.85, 0.98))
            pred = "Malicious"
        elif packet_rate > 1000 and byte_rate < 50000: # High count, low size (SYN Flood vibe)
            risk = min(0.95, random.uniform(0.75, 0.90))
            pred = "Malicious"
        else:
            risk = random.uniform(0.01, 0.25)
            pred = "Benign"
            
        return {
            "src_ip": session.get("src_ip"),
            "dst_ip": session.get("dst_ip"),
            "prediction": pred,
            "risk_score": round(risk, 3),
            "is_mock": True
        }
