import re
from typing import Tuple
from .models import LatexDiagnostic

class LogParser:
    """Deterministic, regex-based LaTeX log parser."""
    
    @staticmethod
    def parse(log_content: str) -> Tuple[LatexDiagnostic, ...]:
        diagnostics = []
        
        # 1. Parse errors matching "! <Error Message>." optionally followed by "l.<line number>"
        error_pattern = re.compile(r"!\s+(.*?)\.\s*\n(?:l\.(\d+))?", re.DOTALL)
        for match in error_pattern.finditer(log_content):
            msg = match.group(1).strip()
            line_str = match.group(2)
            line_num = int(line_str) if line_str else None
            
            diagnostics.append(LatexDiagnostic(
                type="error",
                line=line_num,
                message=msg,
                raw_context=match.group(0).strip()
            ))
            
        # 2. Parse warnings matching "LaTeX Warning: <Warning Message>"
        warning_pattern = re.compile(r"(?:LaTeX|Package).*?Warning.*?:(.*?(?:on input line\s+(\d+))?[^\n]*)", re.DOTALL | re.IGNORECASE)
        # We need a simpler warning regex to capture standard LaTeX warnings
        std_warning_pattern = re.compile(r"(?:LaTeX|Package)[\w\s]*Warning:\s+(.*?)(?:on input line\s+(\d+))?\.", re.DOTALL)
        
        for match in std_warning_pattern.finditer(log_content):
            raw_msg = match.group(1).strip()
            # Clean up newlines in the message
            msg = " ".join(raw_msg.split())
            line_str = match.group(2)
            line_num = int(line_str) if line_str else None
            
            diagnostics.append(LatexDiagnostic(
                type="warning",
                line=line_num,
                message=msg,
                raw_context=match.group(0).strip()
            ))
            
        # 3. Parse layout warnings (Overfull \hbox, Underfull \vbox)
        layout_pattern = re.compile(r"((?:Overfull|Underfull)\s+\\[hv]box[^\n]*)", re.IGNORECASE)
        for match in layout_pattern.finditer(log_content):
            msg = match.group(1).strip()
            # Extract line number if present
            line_match = re.search(r"lines?\s+(\d+)", msg, re.IGNORECASE)
            line_num = int(line_match.group(1)) if line_match else None
            
            diagnostics.append(LatexDiagnostic(
                type="warning",
                line=line_num,
                message=msg,
                raw_context=msg
            ))
            
        return tuple(diagnostics)
