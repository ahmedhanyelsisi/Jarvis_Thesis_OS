import uuid
from typing import List, Dict, Any, Optional

from .models import Claim, Evidence, Argument, Contradiction, ReasoningResult
from .evidence_mapper import EvidenceMapper
from .argument_analyzer import ArgumentAnalyzer
from .contradiction_detector import ContradictionDetector
from .synthesis_engine import SynthesisEngine

class ReasoningGateway:
    """Safe exposure of Stone 21 capabilities to AgentContext."""
    
    def __init__(self, research_gateway=None, context_gateway=None):
        self._mapper = EvidenceMapper(research_gateway, context_gateway)
        self._analyzer = ArgumentAnalyzer()
        self._detector = ContradictionDetector()
        
    def map_evidence(self, text: str, source: str, source_id: str) -> Evidence:
        """Exposed: Map raw evidence."""
        return self._mapper.map_evidence(text, source, source_id)
        
    def analyze_argument(self, text: str, claims_data: List[Dict[str, Any]]) -> Argument:
        """Exposed: Analyze a single argument."""
        # claims_data is a simplified dict structure passed by agent
        claims = []
        for c in claims_data:
            evidence_objs = []
            for e in c.get("evidence", []):
                evidence_objs.append(
                    self.map_evidence(e["text"], e["source"], e["source_id"])
                )
            
            claims.append(Claim(
                claim_id=str(uuid.uuid4()),
                text=c["text"],
                evidence=tuple(evidence_objs)
            ))
            
        return self._analyzer.analyze(text, claims)
        
    def detect_contradictions(self, claims: List[Claim]) -> List[Contradiction]:
        """Exposed: Detect contradictions between a list of claims."""
        return self._detector.detect(claims)
        
    def synthesize_reasoning(self, arguments: List[Argument], contradictions: List[Contradiction]) -> ReasoningResult:
        """Exposed: Synthesize a final reasoning result."""
        return SynthesisEngine.synthesize(arguments, contradictions)
