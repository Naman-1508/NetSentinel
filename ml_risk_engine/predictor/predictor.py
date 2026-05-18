import os
import joblib
import numpy as np
import logging
import pickle
import sys
from feature_extractor.extractor import extract_features

logger = logging.getLogger("RiskPredictor")
# Configure both console and file logging for diagnostics
logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'logs'))
os.makedirs(logs_dir, exist_ok=True)
logfile = os.path.join(logs_dir, 'ml_predictor.log')
handler_stream = logging.StreamHandler()
handler_file = logging.FileHandler(logfile, mode='a')
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
handler_stream.setFormatter(formatter)
handler_file.setFormatter(formatter)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    logger.addHandler(handler_stream)
    logger.addHandler(handler_file)


def _append_main_log(msg: str) -> None:
    """Best-effort append to the host netsentinel log locations so the
    frozen EXE writes a deterministic message we can inspect.
    """
    import sys
    from datetime import datetime as _dt
    candidates = []
    # repo-level log
    try:
        repo_log = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'netsentinel.log'))
        candidates.append(repo_log)
    except Exception:
        pass
    # exe-level logs when frozen
    try:
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            candidates.append(os.path.join(exe_dir, 'logs', 'netsentinel.log'))
            candidates.append(os.path.join(exe_dir, '..', 'logs', 'netsentinel.log'))
    except Exception:
        pass

    for p in candidates:
        try:
            d = os.path.dirname(p)
            if d and not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
            with open(p, 'a', encoding='utf-8') as f:
                f.write(f"{_dt.utcnow().isoformat()}Z [RiskPredictor] {msg}\n")
        except Exception:
            pass

# Custom unpickler to handle missing modules like unittest
class SafeUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        # Allow unittest to be a no-op stub if it's missing
        if module == 'unittest' or module.startswith('unittest.'):
            logger.warning(f"Skipping missing module {module}.{name}")
            return lambda *args, **kwargs: None
        return super().find_class(module, name)

class RiskPredictor:
    def __init__(self, models_dir="models/saved"):
        self.models_dir = models_dir
        self.binary_model = None
        self.multiclass_model = None
        self.binary_scaler = None
        self.multiclass_scaler = None
        self.is_mock = True
        self.reload()

    def reload(self):
        """Try to load the trained model and scaler. If missing, fallback to mock mode."""
        import sys

        # Build a list of candidate directories to search for models/saved
        candidates = []

        def add_candidate(path: str) -> None:
            if path and path not in candidates:
                candidates.append(path)

        if getattr(sys, 'frozen', False):
            # PyInstaller frozen exe — sys.executable is the .exe itself
            exe_dir = os.path.dirname(sys.executable)
            
            # _MEIPASS is the extraction folder for ONEFILE bundles
            meipass = getattr(sys, '_MEIPASS', None)

            # When PyInstaller bundles with datas like (artifacts, 'Offline2/artifacts'),
            # it puts them in _internal/ subdirectory by default in ONEDIR mode
            if meipass:
                # ONEFILE mode: files are extracted to _MEIPASS at runtime
                add_candidate(os.path.join(meipass, 'Offline2', 'artifacts'))
            
            # ONEDIR mode: files are in _internal/ next to exe
            add_candidate(os.path.join(exe_dir, '_internal', 'Offline2', 'artifacts'))
            add_candidate(os.path.join(exe_dir, 'Offline2', 'artifacts'))
            
            # Also check for models/saved directly (legacy structure)
            if meipass:
                add_candidate(os.path.join(meipass, 'models', 'saved'))
            add_candidate(os.path.join(exe_dir, '_internal', 'models', 'saved'))
            add_candidate(os.path.join(exe_dir, 'models', 'saved'))
            
            # Installer paths
            add_candidate(os.path.join(os.path.dirname(exe_dir), 'Offline2', 'artifacts'))
            add_candidate(os.path.join(os.path.dirname(exe_dir), 'ml_risk_engine', 'models', 'saved'))
        else:
            # Normal python execution — models are relative to the ml_risk_engine root
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            add_candidate(os.path.join(base_path, 'models', 'saved'))
            
            # Also check for Offline2 from project root
            try:
                repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                add_candidate(os.path.join(repo_root, 'Offline2', 'artifacts'))
            except Exception:
                pass

        models_path = None
        
        for c in candidates:
            logger.info(f"Checking {c}")
            # Prefer multiclass artifacts when available, then fall back to binary model.pkl
            if os.path.exists(os.path.join(c, "model_multiclass.pkl")):
                models_path = c
                logger.info(f"Found multiclass model at {c}")
                break
            if os.path.exists(os.path.join(c, "model.pkl")):
                models_path = c
                logger.info(f"Found binary model at {c}")
                break
            if os.path.exists(os.path.join(c, "best_model.pkl")):
                models_path = c
                logger.info(f"Found best_model at {c}")
                break

        if models_path is None:
            logger.error("No trained model found in any candidate path. Using heuristic mock predictor.")
            _append_main_log("No trained model found in any candidate path. Using heuristic mock predictor.")
            self.is_mock = True
            return

        binary_model_file = os.path.join(models_path, "model.pkl")
        if not os.path.exists(binary_model_file):
            binary_model_file = os.path.join(models_path, "best_model.pkl")

        multiclass_model_file = os.path.join(models_path, "model_multiclass.pkl")
        if not os.path.exists(multiclass_model_file):
            multiclass_model_file = binary_model_file

        binary_scaler_file = os.path.join(models_path, "scaler.pkl")
        multiclass_scaler_file = os.path.join(models_path, "scaler_multiclass.pkl")
        feature_list_file = os.path.join(models_path, "feature_list.pkl")
        label_map_file = os.path.join(models_path, "label_map.pkl")

        print(f"RiskPredictor: Loading models from {models_path}")

        try:
            # Use custom unpickler to handle missing unittest module
            def safe_joblib_load(filepath):
                try:
                    return joblib.load(filepath)
                except (ImportError, ModuleNotFoundError) as e:
                    if 'unittest' in str(e):
                        logger.warning(f"Standard unpickler failed ({e}), trying SafeUnpickler for {filepath}")
                        with open(filepath, 'rb') as f:
                            return SafeUnpickler(f).load()
                    raise
            
            self.binary_model = safe_joblib_load(binary_model_file)
            # Binary scaler may be absent for some models; load if present
            try:
                self.binary_scaler = safe_joblib_load(binary_scaler_file)
            except Exception:
                self.binary_scaler = None

            # Multiclass model/scaler are optional but preferred for attack labeling
            try:
                self.multiclass_model = safe_joblib_load(multiclass_model_file)
            except Exception:
                self.multiclass_model = None
            try:
                self.multiclass_scaler = safe_joblib_load(multiclass_scaler_file)
            except Exception:
                self.multiclass_scaler = None

            # Try to load saved feature list (column order expected by model/scaler)
            try:
                if os.path.exists(feature_list_file):
                    self.feature_list = safe_joblib_load(feature_list_file)
                else:
                    self.feature_list = None
            except Exception:
                self.feature_list = None
            try:
                if os.path.exists(label_map_file):
                    self.label_map = safe_joblib_load(label_map_file)
                else:
                    self.label_map = None
            except Exception:
                self.label_map = None
            self.is_mock = False
            # Log model type and classes for diagnostics
            try:
                binary_cls_info = getattr(self.binary_model, 'classes_', None)
                multiclass_cls_info = getattr(self.multiclass_model, 'classes_', None)
                logger.info(f"Successfully loaded trained ML models. binary classes_={binary_cls_info} multiclass classes_={multiclass_cls_info}")
                _append_main_log(f"Successfully loaded trained ML models from {models_path}")
                try:
                    if getattr(self, 'feature_list', None) is not None:
                        logger.info(f"feature_list length={len(self.feature_list)} sample={self.feature_list[:10]}")
                    else:
                        logger.info("no feature_list.pkl found")
                    if getattr(self, 'label_map', None) is not None:
                        logger.info(f"label_map keys={list(self.label_map.keys())[:10]}")
                except Exception:
                    pass
            except Exception:
                logger.info("Successfully loaded trained ML model.")
        except Exception as e:
            logger.error(f"Error loading model: {e}. Falling back to mock mode.")
            _append_main_log(f"Error loading model: {e}")
            self.is_mock = True


    def predict(self, session: dict) -> dict:
        """
        Takes a raw NetSentinel session dictionary and returns the risk prediction.
        """
        if self.is_mock:
            # Simple heuristic: flag high packet rates or unusual patterns as malicious
            try:
                X_raw = extract_features(session)
                pkt_rate = X_raw.get('Flow Pkts/s', None)
                if pkt_rate is not None:
                    pkt_rate = pkt_rate.iloc[0] if hasattr(pkt_rate, 'iloc') else pkt_rate
                    if pkt_rate > 1000:
                        return {
                            "src_ip": session.get("src_ip"),
                            "dst_ip": session.get("dst_ip"),
                            "prediction": "HighRate",
                            "binary_prediction": "Malicious",
                            "risk_score": 0.85,
                            "explanation": f"High packet rate ({int(pkt_rate)} pkts/s) detected",
                            "is_mock": True
                        }
            except Exception:
                pass
            
            # Default: benign
            return {
                "src_ip": session.get("src_ip"),
                "dst_ip": session.get("dst_ip"),
                "prediction": "Benign",
                "binary_prediction": "Benign",
                "risk_score": 0.1,
                "explanation": "Default mock prediction (model unavailable)",
                "is_mock": True
            }
            
        try:
            def _prepare_features(scaler_obj):
                x_df = extract_features(session)
                x_df.replace([np.inf, -np.inf], np.nan, inplace=True)
                x_df.fillna(0, inplace=True)

                preferred_features = None
                if getattr(self, 'feature_list', None):
                    preferred_features = list(self.feature_list)
                if preferred_features is None and scaler_obj is not None and hasattr(scaler_obj, 'feature_names_in_'):
                    preferred_features = list(getattr(scaler_obj, 'feature_names_in_', None))
                if preferred_features is None and hasattr(self.binary_model, 'feature_names_in_'):
                    preferred_features = list(getattr(self.binary_model, 'feature_names_in_', None))

                if preferred_features is not None:
                    x_df = x_df.reindex(columns=preferred_features, fill_value=0)

                if scaler_obj is not None:
                    x_scaled = scaler_obj.transform(x_df)
                    try:
                        import pandas as _pd
                        x_scaled = _pd.DataFrame(x_scaled, columns=preferred_features if preferred_features is not None else list(x_df.columns))
                    except Exception:
                        pass
                    return x_scaled, preferred_features

                return x_df, preferred_features

            # 1) Binary gate first
            binary_input, binary_features = _prepare_features(self.binary_scaler)
            print(f"Predictor: Binary gate input shape {binary_input.shape if hasattr(binary_input, 'shape') else 'N/A'}")
            binary_probs = None
            try:
                binary_probs = self.binary_model.predict_proba(binary_input)[0]
            except Exception:
                binary_probs = None
            binary_pred = self.binary_model.predict(binary_input)[0]

            binary_classes = list(getattr(self.binary_model, 'classes_', [0, 1]))
            if binary_pred in binary_classes:
                binary_label = str(binary_pred)
                binary_index = binary_classes.index(binary_pred)
            else:
                try:
                    binary_index = int(binary_pred)
                    binary_label = str(binary_classes[binary_index]) if binary_index < len(binary_classes) else str(binary_pred)
                except Exception:
                    binary_index = None
                    binary_label = str(binary_pred)

            if binary_probs is not None and len(binary_probs) > 1:
                # Calculate risk as the probability of the malicious class (index 1)
                # If index 0 is benign, index 1 is malicious
                malicious_idx = 1
                for idx, c in enumerate(binary_classes):
                    if str(c).lower() not in {"benign", "0"}:
                        malicious_idx = idx
                        break
                if malicious_idx < len(binary_probs):
                    binary_risk = float(binary_probs[malicious_idx])
                else:
                    # fallback
                    binary_risk = float(binary_probs[1]) if len(binary_probs) > 1 else 0.1
                    
                # Robustness Threshold: Machine Learning models on raw packet data
                # often produce false positives (0.5 - 0.8) on normal home Wi-Fi background traffic.
                # We enforce an 85% confidence threshold to be classified as an attack.
                if binary_risk < 0.85:
                    binary_label = "Benign"
            else:
                binary_risk = 0.9 if str(binary_label).lower() not in {"benign", "0"} else 0.1

            if str(binary_label).lower() in {"benign", "0"}:
                explanation = "Traffic classified as benign by binary ML gate."
                return {
                    "src_ip": session.get("src_ip"),
                    "dst_ip": session.get("dst_ip"),
                    "prediction": "Benign",
                    "binary_prediction": "Benign",
                    "risk_score": round(float(binary_risk), 3),
                    "explanation": explanation,
                    "is_mock": False
                }
            # 2) Malicious path: refine with multiclass model when available
            multiclass_prediction = "Malicious"
            multiclass_risk = binary_risk
            if self.multiclass_model is not None:
                multiclass_input, _ = _prepare_features(self.multiclass_scaler or self.binary_scaler)
                print(f"Predictor: Multiclass refinement input shape {multiclass_input.shape if hasattr(multiclass_input, 'shape') else 'N/A'}")
                try:
                    multiclass_probs = self.multiclass_model.predict_proba(multiclass_input)[0]
                except Exception:
                    multiclass_probs = None

                multiclass_pred = self.multiclass_model.predict(multiclass_input)[0]
                multiclass_classes = list(getattr(self.multiclass_model, 'classes_', []))

                if multiclass_pred in multiclass_classes:
                    multiclass_prediction = str(multiclass_pred)
                    multiclass_index = multiclass_classes.index(multiclass_pred)
                else:
                    try:
                        multiclass_index = int(multiclass_pred)
                        if getattr(self, 'label_map', None):
                            multiclass_prediction = str(self.label_map.get(multiclass_index, multiclass_pred))
                        elif multiclass_index < len(multiclass_classes):
                            multiclass_prediction = str(multiclass_classes[multiclass_index])
                        else:
                            multiclass_prediction = str(multiclass_pred)
                    except Exception:
                        multiclass_index = None
                        multiclass_prediction = str(multiclass_pred)

                if multiclass_probs is not None and multiclass_index is not None and multiclass_index < len(multiclass_probs):
                    multiclass_risk = float(multiclass_probs[multiclass_index])
                else:
                    multiclass_risk = max(binary_risk, 0.9)

            explanation = f"Binary ML gate flagged malicious; multiclass refinement identified {multiclass_prediction}."
            try:
                X_raw = extract_features(session)
                reasons = []
                pkt_rate = X_raw.get('Flow Pkts/s', None).iloc[0] if 'Flow Pkts/s' in X_raw else None
                if pkt_rate is not None and pkt_rate > 1000:
                    reasons.append(f"High packet rate ({int(pkt_rate)} pkts/s)")
                fwd_seg_avg = X_raw.get('Fwd Seg Size Avg', None).iloc[0] if 'Fwd Seg Size Avg' in X_raw else None
                if fwd_seg_avg is not None and fwd_seg_avg < 100:
                    reasons.append("Small forward segment size")
                syn_cnt = X_raw.get('SYN Flag Cnt', None).iloc[0] if 'SYN Flag Cnt' in X_raw else None
                if syn_cnt is not None and syn_cnt > 50:
                    reasons.append("High SYN flag count")
                if reasons:
                    explanation += " Contributing factors: " + ", ".join(reasons) + "."
            except Exception:
                pass

            return {
                "src_ip": session.get("src_ip"),
                "dst_ip": session.get("dst_ip"),
                "prediction": str(multiclass_prediction),
                "binary_prediction": "Malicious",
                "risk_score": round(float(multiclass_risk), 3),
                "binary_risk_score": round(float(binary_risk), 3),
                "explanation": explanation,
                "is_mock": False
            }
            
        except Exception as e:
            # Critical error — log and return error response
            import traceback
            print(f"Prediction ERROR: {e}")
            traceback.print_exc()
            return {
                "src_ip": session.get("src_ip"),
                "dst_ip": session.get("dst_ip"),
                "prediction": "Error",
                "risk_score": 0.0,
                "explanation": f"Prediction failed: {str(e)}",
                "is_mock": False
            }
