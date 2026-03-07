import time
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.model_selection import train_test_split
import xgboost as xgb
import os

def evaluate_model(name, model, X_test, y_test):
    print(f"\nEvaluating {name}...")
    start = time.time()
    y_pred = model.predict(X_test)
    pred_time = time.time() - start
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred).tolist()
    
    print(f"  Accuracy:  {acc:.4f}")
    print(f"  Precision: {prec:.4f}")
    print(f"  Recall:    {rec:.4f}")
    print(f"  F1 Score:  {f1:.4f}")
    print(f"  Pred Time: {pred_time*1000:.2f} ms")
    
    return {
        "name": name,
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "confusion_matrix": cm,
        "prediction_time_ms": pred_time * 1000
    }

def train_and_select_best(X, y, save_dir="models/saved"):
    print("Splitting dataset...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, n_jobs=-1),
        "Random Forest": RandomForestClassifier(n_estimators=50, max_depth=10, n_jobs=-1, random_state=42),
        "XGBoost": xgb.XGBClassifier(n_estimators=50, max_depth=6, use_label_encoder=False, eval_metric='logloss', n_jobs=-1)
    }
    
    results = []
    best_model = None
    best_f1 = -1
    best_name = ""
    
    for name, model in models.items():
        print(f"\nTraining {name}...")
        start = time.time()
        model.fit(X_train, y_train)
        print(f"  Trained in {time.time() - start:.2f}s")
        
        metrics = evaluate_model(name, model, X_test, y_test)
        results.append(metrics)
        
        if metrics["f1"] > best_f1:
            best_f1 = metrics["f1"]
            best_model = model
            best_name = name
            
    print(f"\nBest Model: {best_name} (F1: {best_f1:.4f})")
    
    os.makedirs(save_dir, exist_ok=True)
    model_path = os.path.join(save_dir, "best_model.pkl")
    joblib.dump(best_model, model_path)
    print(f"Saved best model to {model_path}")
    
    return results, best_name
