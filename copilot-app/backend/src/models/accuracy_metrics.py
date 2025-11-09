"""
Accuracy Metrics Models
Task: FC-API-032 - Prediction Accuracy Analytics
Author: ALEX-FINANCE-ANALYST-SUPERMAN-29
"""
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class AccuracyMetrics:
    """
    Data class representing prediction accuracy metrics
    """
    total_predictions: int
    hit_rate: float
    mse: float
    mae: float
    rmse: float
    avg_confidence: float
    avg_return_if_correct: float
    success_rate: float
    directional_accuracy: float
    generated_at: str
    source: List[str]