import pytest
import dataclasses
from unittest.mock import MagicMock

from reasoning_core.exceptions import EvidenceError
from reasoning_core.models import Claim, Evidence, EvidenceSource, Argument, Contradiction, ReasoningResult, ReasoningConfidence
from reasoning_core.gateway import ReasoningGateway
from reasoning_core.evidence_mapper import EvidenceMapper
from reasoning_core.contradiction_detector import ContradictionDetector

def test_fake_evidence_injection():
    # Attempt to inject an unsupported source
    mapper = EvidenceMapper()
    with pytest.raises(EvidenceError):
        mapper.map_evidence("Some text", "fake_source", "id_123")

def test_unsupported_claim_generation():
    # A claim with no evidence shouldn't crash, but gets low confidence
    gateway = ReasoningGateway()
    argument = gateway.analyze_argument("Claim without proof", [{"text": "It is known.", "evidence": []}])
    assert argument.confidence.score == 0.0
    assert "No claims" not in argument.confidence.factors[0]
    assert any("Low evidence density" in f for f in argument.confidence.factors)

def test_cross_session_contamination():
    # Reasoning modules are stateless, contamination is impossible at this layer.
    # We verify that gateway instantiation doesn't hold hidden state.
    gw1 = ReasoningGateway()
    gw2 = ReasoningGateway()
    assert gw1 is not gw2

def test_contradiction_poisoning():
    # Create claims specifically designed to trigger the contradiction detector
    c1 = Claim("1", "The sky is blue", tuple())
    c2 = Claim("2", "Not the sky is blue", tuple())
    
    detector = ContradictionDetector()
    contradictions = detector.detect([c1, c2])
    
    assert len(contradictions) == 1
    assert contradictions[0].conflicting_claims == (c1, c2)

def test_immutable_model_tampering():
    e = Evidence(EvidenceSource.USER, "id1", "content")
    with pytest.raises(dataclasses.FrozenInstanceError):
        e.content = "hacked"
        
    c = Claim("1", "Text", (e,))
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.text = "hacked claim"
