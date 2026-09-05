from typing import List, Dict

class CitationManager:
    """Prepares citations for LaTeX compilation (bridges Stone 20 to Stone 13)."""
    
    def __init__(self, file_access):
        self._file_access = file_access
        
    def generate_bibliography(self, citations: List[Dict[str, str]], target_file: str = "refs.bib"):
        """Compiles standard citations into a bib file."""
        bib_content = ""
        for cit in citations:
            bib_id = cit.get("id", "unknown")
            title = cit.get("title", "Untitled")
            author = cit.get("author", "Unknown")
            year = cit.get("year", "2024")
            
            bib_content += f"@article{{{bib_id},\n  title={{{title}}},\n  author={{{author}}},\n  year={{{year}}}\n}}\n\n"
            
        if self._file_access:
            self._file_access.write_file(target_file, bib_content)
        return bib_content
