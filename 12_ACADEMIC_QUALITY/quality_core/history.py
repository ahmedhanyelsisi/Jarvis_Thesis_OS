import json
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

from .models import QualityReport, QualityScore, Metric, RevisionTask
from .exceptions import QualityHistoryError

class QualityHistoryManager:
    """Stores and tracks history of quality reports to monitor score evolution."""

    def __init__(self, workspace_root: str):
        self._db_path = Path(workspace_root) / ".jarvis" / "quality_reports"
        self._db_path.mkdir(parents=True, exist_ok=True)

    def _validate_id(self, identifier: str) -> None:
        if not identifier or "\x00" in identifier:
            raise QualityHistoryError("Invalid identifier: null bytes not allowed.")
        if not re.match(r'^[\w\-]+$', identifier):
            raise QualityHistoryError(f"Invalid identifier: {identifier}. Only alphanumeric, hyphen, and underscore allowed.")

    def _get_safe_path(self, workflow_id: str) -> Path:
        self._validate_id(workflow_id)
        filename = f"history_{workflow_id}.json"
        file_path = self._db_path / filename
        
        try:
            if not file_path.resolve().is_relative_to(self._db_path.resolve()):
                raise QualityHistoryError("Path traversal attempt blocked.")
        except Exception as e:
            raise QualityHistoryError(f"Path resolution error: {e}")
            
        return file_path

    def save_report(self, report: QualityReport) -> None:
        file_path = self._get_safe_path(report.workflow_id)
        temp_path = file_path.with_suffix(".json.tmp")
        
        # Load existing history to append
        history = self.get_workflow_history(report.workflow_id)
        
        # Append new report
        report_dict = self._report_to_dict(report)
        history.append(report_dict)
        
        try:
            with temp_path.open("w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            temp_path.replace(file_path)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise QualityHistoryError(f"Failed to save quality report for {report.workflow_id}: {e}")

    def get_workflow_history(self, workflow_id: str) -> List[Dict[str, Any]]:
        file_path = self._get_safe_path(workflow_id)
        if not file_path.exists():
            return []
            
        try:
            with file_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            raise QualityHistoryError(f"Corrupted quality history JSON for {workflow_id}.")
        except Exception as e:
            raise QualityHistoryError(f"Failed to load quality history for {workflow_id}: {e}")
            
    def _report_to_dict(self, obj: Any) -> Any:
        import dataclasses
        if dataclasses.is_dataclass(obj):
            return {f.name: self._report_to_dict(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
        elif isinstance(obj, dict):
            return {k: self._report_to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._report_to_dict(x) for x in obj]
        else:
            return obj
