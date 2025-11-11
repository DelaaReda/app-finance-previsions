"""
Accuracy Metrics Models
Task: FC-API-032 - Prediction Accuracy Analytics
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime


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


@dataclass
class PredictionAccuracyReport:
    """
    Complete report structure for prediction accuracy analysis
    """
    accuracy_metrics: AccuracyMetrics
    summary: Dict
    by_horizon: Dict
    by_asset: Dict
    generated_at: str
    parameters: Dict
    source: List[str]