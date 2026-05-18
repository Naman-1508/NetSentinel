import sys, os
# Ensure ml_risk_engine subdir is importable for package-local imports
sys.path.insert(0, os.path.abspath('ml_risk_engine'))
sys.path.insert(0, os.path.abspath('.'))
from predictor.predictor import RiskPredictor

models_dir = os.path.abspath('Offline2/artifacts')
print('Models dir:', models_dir)
rp = RiskPredictor(models_dir=models_dir)
print('is_mock:', rp.is_mock)
print('binary_model_classes:', getattr(rp.binary_model, 'classes_', None))
print('multiclass_model_classes:', getattr(rp.multiclass_model, 'classes_', None))
print('feature_list_exists:', getattr(rp, 'feature_list', None) is not None)
print('label_map_exists:', getattr(rp, 'label_map', None) is not None)
