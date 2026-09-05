import uuid
import re
from typing import Dict, Tuple

from .models import ResearchPaper

class PaperParser:
    """Converts raw extracted PDF text into structured ResearchPaper objects."""

    @staticmethod
    def parse(raw_data: dict) -> ResearchPaper:
        text = raw_data.get("text", "")
        meta = raw_data.get("metadata", {})
        
        # Simple heuristic parsing (in reality, requires complex NLP or LLMs)
        sections = PaperParser._split_sections(text)
        
        abstract = sections.get("abstract", "")
        if not abstract and "Abstract" in text[:2000]:
            # Fallback regex for abstract
            match = re.search(r'(?i)abstract[\s\:]+(.*?)(?i)(introduction|1\.)', text[:3000], re.DOTALL)
            if match:
                abstract = match.group(1).strip()
        
        title = meta.get("title", "Unknown Title")
        authors = tuple(meta.get("author", "Unknown Author").split(","))
        
        # Try to parse year from meta or text
        year_str = meta.get("creationDate", "")
        year = 2024 # Default fallback
        if year_str and len(year_str) >= 6:
            try:
                year = int(year_str[2:6])
            except ValueError:
                pass

        return ResearchPaper(
            paper_id=str(uuid.uuid4()),
            title=title.strip(),
            authors=tuple(a.strip() for a in authors if a.strip()),
            abstract=abstract,
            publication_year=year,
            doi=meta.get("doi", ""),
            sections=sections,
            metadata=meta
        )

    @staticmethod
    def _split_sections(text: str) -> Dict[str, str]:
        """Heuristic section splitting."""
        sections = {}
        headers = ["abstract", "introduction", "related work", "methodology", "methods", "results", "discussion", "conclusion", "references"]
        
        # Very rudimentary section splitting for the proof-of-concept
        lower_text = text.lower()
        last_idx = 0
        last_header = "frontmatter"
        
        for header in headers:
            # find index of header as a line
            # regex for header at start of line
            pattern = re.compile(rf'^\s*(?:[0-9]+\.?\s*)?{header}\s*$', re.MULTILINE | re.IGNORECASE)
            match = pattern.search(text[last_idx:])
            if match:
                idx = match.start() + last_idx
                sections[last_header] = text[last_idx:idx].strip()
                last_header = header
                last_idx = match.end() + last_idx
                
        sections[last_header] = text[last_idx:].strip()
        
        # Consolidate alternative names
        if "methods" in sections and "methodology" not in sections:
            sections["methodology"] = sections.pop("methods")
            
        return sections
