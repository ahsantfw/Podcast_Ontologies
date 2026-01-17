"""
Job Database - Track background processing jobs
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = ROOT / "data" / "jobs.db"

class JobDB:
    """Job tracking database."""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                type TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                results TEXT,  -- JSON
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_workspace 
            ON jobs(workspace_id)
        """)
        
        conn.commit()
        conn.close()
    
    def create_job(self, job_id: str, workspace_id: str, job_type: str, status: str = "pending"):
        """Create a new job."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO jobs (job_id, workspace_id, type, status, progress)
            VALUES (?, ?, ?, ?, 0)
        """, (job_id, workspace_id, job_type, status))
        
        conn.commit()
        conn.close()
    
    def update_job(self, job_id: str, status: str = None, progress: int = None, 
                   results: dict = None, error: str = None):
        """Update job status/progress."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if status:
            updates.append("status = ?")
            params.append(status)
        
        if progress is not None:
            updates.append("progress = ?")
            params.append(progress)
        
        if results:
            updates.append("results = ?")
            params.append(json.dumps(results))
        
        if error:
            updates.append("error = ?")
            params.append(error)
        
        if status == "completed" or status == "failed":
            updates.append("completed_at = CURRENT_TIMESTAMP")
        
        if updates:
            params.append(job_id)
            query = f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?"
            cursor.execute(query, params)
            conn.commit()
        
        conn.close()
    
    def get_job(self, job_id: str) -> dict:
        """Get job by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT job_id, workspace_id, type, status, progress, results, error, 
                   created_at, completed_at
            FROM jobs
            WHERE job_id = ?
        """, (job_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        return {
            "job_id": result[0],
            "workspace_id": result[1],
            "type": result[2],
            "status": result[3],
            "progress": result[4],
            "results": json.loads(result[5]) if result[5] else None,
            "error": result[6],
            "created_at": result[7],
            "completed_at": result[8]
        }

