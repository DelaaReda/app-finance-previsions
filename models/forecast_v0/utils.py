"""
Model Persistence Utilities
For saving and loading forecasting models
MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
import pickle
import os
from datetime import datetime
from typing import Any, Dict, Optional
import joblib


def save_model(model: Any, model_name: str, model_dir: str = "./saved_models") -> str:
    """
    Save a trained model to disk
    
    Args:
        model: Trained model object
        model_name: Name of the model
        model_dir: Directory to save the model
        
    Returns:
        Path to the saved model
    """
    # Create directory if it doesn't exist
    os.makedirs(model_dir, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{model_name}_{timestamp}.pkl"
    filepath = os.path.join(model_dir, filename)
    
    # Save the model
    with open(filepath, 'wb') as f:
        pickle.dump(model, f)
    
    print(f"Model saved to {filepath}")
    return filepath


def load_model(filepath: str) -> Any:
    """
    Load a trained model from disk
    
    Args:
        filepath: Path to the saved model
        
    Returns:
        Loaded model object
    """
    with open(filepath, 'rb') as f:
        model = pickle.load(f)
    
    print(f"Model loaded from {filepath}")
    return model


def save_forecast_results(results: Dict, filename: str = None) -> str:
    """
    Save forecast results to a JSON file
    
    Args:
        results: Forecast results dictionary
        filename: Name of the output file (optional)
        
    Returns:
        Path to the saved file
    """
    import json
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"forecast_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"Forecast results saved to {filename}")
    return filename


def get_latest_model(model_dir: str = "./saved_models", model_name: str = None) -> Optional[str]:
    """
    Get the path to the latest saved model
    
    Args:
        model_dir: Directory containing saved models
        model_name: Specific model name to look for (optional)
        
    Returns:
        Path to the latest model file
    """
    if not os.path.exists(model_dir):
        return None
    
    files = os.listdir(model_dir)
    
    if model_name:
        # Filter files by model name
        files = [f for f in files if model_name in f]
    
    if not files:
        return None
    
    # Sort by modification time (most recent first)
    files = sorted(files, key=lambda x: os.path.getmtime(os.path.join(model_dir, x)), reverse=True)
    
    return os.path.join(model_dir, files[0])


class ModelRegistry:
    """
    Registry to keep track of different model versions and their performance
    """
    def __init__(self, registry_file: str = "model_registry.json"):
        self.registry_file = registry_file
        self.registry = self.load_registry()
    
    def load_registry(self) -> Dict:
        """Load the model registry from file"""
        import json
        import os
        
        if os.path.exists(self.registry_file):
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_registry(self):
        """Save the model registry to file"""
        import json
        
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2, default=str)
    
    def register_model(self, model_name: str, model_path: str, performance_metrics: Dict, 
                      features_used: list, training_data_info: Dict):
        """Register a new model in the registry"""
        import json
        
        model_id = f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.registry[model_id] = {
            "model_name": model_name,
            "model_path": model_path,
            "registered_at": datetime.now().isoformat(),
            "performance_metrics": performance_metrics,
            "features_used": features_used,
            "training_data_info": training_data_info
        }
        
        self.save_registry()
        print(f"Model {model_id} registered in the model registry")
    
    def get_best_model(self, model_name: str, metric: str = "accuracy") -> Optional[str]:
        """Get the best performing model based on a specific metric"""
        best_model_id = None
        best_score = float('-inf')
        
        for model_id, model_info in self.registry.items():
            if model_info["model_name"] == model_name:
                score = model_info["performance_metrics"].get(metric, float('-inf'))
                if score > best_score:
                    best_score = score
                    best_model_id = model_id
        
        if best_model_id:
            return self.registry[best_model_id]["model_path"]
        return None