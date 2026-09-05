from typing import List
from .models import ResearchGap, ResearchPaper

class GapDetector:
    """Basic heuristic logic to identify literature gaps."""
    
    @staticmethod
    def analyze_gaps(papers: List[ResearchPaper]) -> List[ResearchGap]:
        gaps = []
        
        # In a real environment, this would use LLM reasoning over the extracted limitatons sections
        # For now, we perform basic string matching heuristics to find explicit "future work"
        for paper in papers:
            text = " ".join(paper.sections.values()).lower()
            if "future work" in text or "limitations" in text:
                gaps.append(ResearchGap(
                    description=f"Identified potential limitation/future work in {paper.title}",
                    supporting_papers=(paper.paper_id,),
                    confidence=0.75
                ))
                
        return gaps
