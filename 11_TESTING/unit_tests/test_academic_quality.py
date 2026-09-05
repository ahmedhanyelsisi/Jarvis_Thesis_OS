import pytest
from unittest.mock import MagicMock
from pathlib import Path
import json
import dataclasses

from quality_core.models import QualityScore, Metric, QualityReport, RevisionTask
from quality_core.metrics import MetricDefinitions, validate_metric_score
from quality_core.scoring import QualityScorer
from quality_core.feedback import FeedbackGenerator
from quality_core.history import QualityHistoryManager
from quality_core.evaluator import QualityEvaluator
from quality_core.exceptions import QualityEvaluationError, QualityHistoryError, MetricValidationError

def test_metric_validation():
    validate_metric_score(10.0)
    validate_metric_score(0.0)
    validate_metric_score(7.5)
    with pytest.raises(MetricValidationError):
        validate_metric_score(11.0)
    with pytest.raises(MetricValidationError):
        validate_metric_score(-1.0)

def test_adaptive_weighting():
    science_context = {"domain": "computer science"}
    weights = MetricDefinitions.get_adaptive_weights(science_context)
    
    assert weights["methodology"] > weights["structure"]
    assert weights["citation"] > weights["structure"]
    
    humanities_context = {"domain": "humanities - history"}
    weights = MetricDefinitions.get_adaptive_weights(humanities_context)
    assert weights["argument"] > weights["structure"]

def test_scoring_algorithm():
    raw = {"structure": 8.0, "argument": 6.0}
    reasonings = {"structure": "Good", "argument": "Weak"}
    
    # We pass empty domain so it uses baseline weights exactly
    score = QualityScorer.calculate_score(raw, reasonings, {})
    # Since only 2 metrics provided and 6 expected by baseline, the others will be 0.0
    # Wait, the scoring loops over all baseline metrics.
    # 8 + 6 = 14. 14 / 6 metrics = 2.33 overall
    assert score.overall_score == pytest.approx(2.33, 0.1)

def test_immutable_models():
    m = Metric("test", 10.0, 1.0, "reason")
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.score = 5.0

def test_history_path_traversal(tmp_path):
    manager = QualityHistoryManager(str(tmp_path))
    with pytest.raises(QualityHistoryError):
        manager.get_workflow_history("../secrets")
    with pytest.raises(QualityHistoryError):
        manager.get_workflow_history("null\x00byte")

def test_evaluator_integration(tmp_path):
    mock_runtime = MagicMock()
    manager = QualityHistoryManager(str(tmp_path))
    evaluator = QualityEvaluator(mock_runtime, manager)
    
    report = evaluator.evaluate("wf_123", "node_1", "Draft text...", {"domain": "science"})
    assert report.workflow_id == "wf_123"
    assert report.recommendation in ["APPROVE", "REVISE", "REJECT"]
    
    # Check persistence
    history = manager.get_workflow_history("wf_123")
    assert len(history) == 1
    assert history[0]["node_id"] == "node_1"

def test_feedback_generator():
    metrics = [
        Metric("structure", 8.0, 1.0, "Good"),
        Metric("argument", 3.0, 1.0, "Very bad"),
        Metric("methodology", 5.0, 1.0, "Okay")
    ]
    score = QualityScore(overall_score=5.0, metrics=tuple(metrics))
    
    tasks = FeedbackGenerator.generate_tasks(score, threshold=7.0)
    assert len(tasks) == 2
    assert tasks[0].target_metric == "argument"
    assert tasks[0].severity == "CRITICAL"
    assert tasks[1].target_metric == "methodology"
    assert tasks[1].severity == "HIGH"

def test_corrupted_history_recovery(tmp_path):
    manager = QualityHistoryManager(str(tmp_path))
    bad_file = tmp_path / ".jarvis" / "quality_reports" / "history_corrupt.json"
    bad_file.parent.mkdir(parents=True, exist_ok=True)
    bad_file.write_text("invalid json")
    
    with pytest.raises(QualityHistoryError):
        manager.get_workflow_history("corrupt")
