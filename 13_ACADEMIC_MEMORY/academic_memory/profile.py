from typing import Optional, Dict, Any
from .models import ResearcherProfile
from .memory_store import MemoryStore
from .governance import MemoryGovernance

class ProfileManager:
    """Manages long-term researcher styles and constraints."""
    
    def __init__(self, store: MemoryStore):
        self._store = store

    def get_profile(self, researcher_id: str) -> ResearcherProfile:
        filename = f"profile_{researcher_id}.json"
        data = self._store.load_json(filename)
        if not data:
            return ResearcherProfile(
                researcher_id=researcher_id,
                preferred_tone="academic",
                formatting_rules=[],
                supervisor_constraints=[]
            )
        return ResearcherProfile(**data)

    def update_profile(self, profile: ResearcherProfile):
        clean_tone = MemoryGovernance.sanitize_text(profile.preferred_tone)
        clean_rules = [MemoryGovernance.sanitize_text(r) for r in profile.formatting_rules]
        clean_constraints = [MemoryGovernance.sanitize_text(c) for c in profile.supervisor_constraints]
        
        data = {
            "researcher_id": profile.researcher_id,
            "preferred_tone": clean_tone,
            "formatting_rules": clean_rules,
            "supervisor_constraints": clean_constraints
        }
        
        filename = f"profile_{profile.researcher_id}.json"
        self._store.save_json(filename, data)
