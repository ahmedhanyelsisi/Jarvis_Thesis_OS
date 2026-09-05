import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from .exceptions import MemoryStorageError
from .models import AgentPerformance, WorkflowOutcome

class MemoryStore:
    """Hybrid storage: SQLite for telemetry, JSON for profiles/feedback."""
    
    def __init__(self, workspace_root: str):
        self._root = Path(workspace_root) / ".jarvis" / "academic_memory"
        self._root.mkdir(parents=True, exist_ok=True)
        
        self._db_path = self._root / "telemetry.db"
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS agent_performance (
                        agent_role TEXT,
                        task_type TEXT,
                        success_rate REAL,
                        total_executions INTEGER,
                        average_duration_sec REAL,
                        PRIMARY KEY (agent_role, task_type)
                    )
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS workflow_outcomes (
                        workflow_id TEXT PRIMARY KEY,
                        status TEXT,
                        steps_completed INTEGER,
                        human_interventions INTEGER
                    )
                ''')
        except sqlite3.Error as e:
            raise MemoryStorageError(f"Failed to initialize SQLite: {e}")

    def save_json(self, filename: str, data: Dict[str, Any]):
        """Atomic JSON write to prevent corruption."""
        target_path = self._root / filename
        # Basic path traversal protection
        if not target_path.resolve().is_relative_to(self._root.resolve()):
            raise MemoryStorageError("Path traversal blocked.")
            
        tmp_path = target_path.with_suffix('.json.tmp')
        try:
            with tmp_path.open('w', encoding='utf-8') as f:
                json.dump(data, f)
            tmp_path.replace(target_path)
        except OSError as e:
            raise MemoryStorageError(f"Failed to save JSON {filename}: {e}")

    def load_json(self, filename: str) -> Optional[Dict[str, Any]]:
        target_path = self._root / filename
        if not target_path.resolve().is_relative_to(self._root.resolve()):
            raise MemoryStorageError("Path traversal blocked.")
            
        if not target_path.exists():
            return None
        try:
            with target_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            raise MemoryStorageError(f"Corrupted JSON in {filename}")

    def upsert_agent_performance(self, perf: AgentPerformance):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute('''
                INSERT INTO agent_performance (agent_role, task_type, success_rate, total_executions, average_duration_sec)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(agent_role, task_type) DO UPDATE SET
                    success_rate = excluded.success_rate,
                    total_executions = excluded.total_executions,
                    average_duration_sec = excluded.average_duration_sec
            ''', (perf.agent_role, perf.task_type, perf.success_rate, perf.total_executions, perf.average_duration_sec))

    def insert_workflow_outcome(self, outcome: WorkflowOutcome):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO workflow_outcomes (workflow_id, status, steps_completed, human_interventions)
                VALUES (?, ?, ?, ?)
            ''', (outcome.workflow_id, outcome.status, outcome.steps_completed, outcome.human_interventions))
