"""SQLite database for persistent research history storage."""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import uuid

class ResearchDatabase:
    """Manage persistent storage of research sessions and results."""
    
    def __init__(self, db_path: Path = Path("data/research_history.db")):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            # Research sessions table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS research_sessions (
                    session_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    duration_seconds REAL,
                    total_cost REAL,
                    num_researchers INTEGER,
                    total_searches INTEGER,
                    synthesis TEXT,
                    research_plan TEXT,
                    status TEXT DEFAULT 'in_progress',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Research findings table (one per sub-researcher)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS research_findings (
                    finding_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    research_angle TEXT,
                    findings TEXT,
                    searches_performed INTEGER,
                    cost REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES research_sessions(session_id)
                )
            ''')
            
            # Sources table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS research_sources (
                    source_id TEXT PRIMARY KEY,
                    finding_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT,
                    domain TEXT,
                    relevance_score REAL,
                    content_snippet TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (finding_id) REFERENCES research_findings(finding_id)
                )
            ''')
            
            # Search queries table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS search_queries (
                    query_id TEXT PRIMARY KEY,
                    finding_id TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    num_results INTEGER,
                    from_cache BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (finding_id) REFERENCES research_findings(finding_id)
                )
            ''')
            
            # Create indices for better performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_timestamp ON research_sessions(timestamp DESC)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_query ON research_sessions(query)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_findings_session ON research_findings(session_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sources_finding ON research_sources(finding_id)')
            
            conn.commit()
    
    def create_session(self, query: str, research_plan: Dict[str, Any]) -> str:
        """Create a new research session."""
        session_id = str(uuid.uuid4())[:8]
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO research_sessions 
                (session_id, query, timestamp, research_plan, num_researchers)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                session_id,
                query,
                datetime.now(),
                json.dumps(research_plan),
                research_plan.get('num_sub_researchers', 0)
            ))
            conn.commit()
        
        return session_id
    
    def save_finding(
        self,
        session_id: str,
        research_angle: str,
        findings: str,
        searches_performed: int,
        cost: float,
        sources: List[Dict[str, Any]],
        query_details: List[Dict[str, Any]]
    ) -> str:
        """Save a research finding with its sources."""
        finding_id = str(uuid.uuid4())[:8]
        
        with sqlite3.connect(self.db_path) as conn:
            # Save finding
            conn.execute('''
                INSERT INTO research_findings
                (finding_id, session_id, research_angle, findings, searches_performed, cost)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                finding_id,
                session_id,
                research_angle,
                findings,
                searches_performed,
                cost
            ))
            
            # Save sources
            for source in sources:
                source_id = str(uuid.uuid4())[:8]
                conn.execute('''
                    INSERT INTO research_sources
                    (source_id, finding_id, url, title, domain, relevance_score)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    source_id,
                    finding_id,
                    source.get('url', ''),
                    source.get('title', ''),
                    source.get('domain', ''),
                    source.get('score', 0)
                ))
            
            # Save search queries
            for detail in query_details:
                query_id = str(uuid.uuid4())[:8]
                conn.execute('''
                    INSERT INTO search_queries
                    (query_id, finding_id, query_text, num_results)
                    VALUES (?, ?, ?, ?)
                ''', (
                    query_id,
                    finding_id,
                    detail.get('query', ''),
                    detail.get('num_results', 0)
                ))
            
            conn.commit()
        
        return finding_id
    
    def complete_session(
        self,
        session_id: str,
        synthesis: str,
        duration_seconds: float,
        total_cost: float,
        total_searches: int
    ):
        """Mark a session as complete with final results."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE research_sessions
                SET synthesis = ?, duration_seconds = ?, total_cost = ?,
                    total_searches = ?, status = 'completed'
                WHERE session_id = ?
            ''', (
                synthesis,
                duration_seconds,
                total_cost,
                total_searches,
                session_id
            ))
            conn.commit()
    
    def get_recent_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent research sessions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT session_id, query, timestamp, duration_seconds, total_cost,
                       num_researchers, total_searches, status
                FROM research_sessions
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            sessions = []
            for row in cursor:
                sessions.append(dict(row))
            
            return sessions
    
    def get_session_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get complete details for a research session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get session info
            cursor = conn.execute('''
                SELECT * FROM research_sessions WHERE session_id = ?
            ''', (session_id,))
            session = cursor.fetchone()
            
            if not session:
                return None
            
            result = dict(session)
            
            # Get findings
            cursor = conn.execute('''
                SELECT * FROM research_findings WHERE session_id = ?
            ''', (session_id,))
            findings = [dict(row) for row in cursor]
            
            # Get sources for each finding
            for finding in findings:
                cursor = conn.execute('''
                    SELECT * FROM research_sources WHERE finding_id = ?
                    ORDER BY relevance_score DESC
                ''', (finding['finding_id'],))
                finding['sources'] = [dict(row) for row in cursor]
                
                # Get search queries
                cursor = conn.execute('''
                    SELECT * FROM search_queries WHERE finding_id = ?
                ''', (finding['finding_id'],))
                finding['search_queries'] = [dict(row) for row in cursor]
            
            result['findings'] = findings
            
            # Parse JSON fields
            if result.get('research_plan'):
                result['research_plan'] = json.loads(result['research_plan'])
            
            return result
    
    def search_sessions(self, query: str) -> List[Dict[str, Any]]:
        """Search for research sessions by query text."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT session_id, query, timestamp, duration_seconds, total_cost, status
                FROM research_sessions
                WHERE query LIKE ?
                ORDER BY timestamp DESC
                LIMIT 50
            ''', (f'%{query}%',))
            
            return [dict(row) for row in cursor]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics from the database."""
        with sqlite3.connect(self.db_path) as conn:
            # Total sessions
            cursor = conn.execute('SELECT COUNT(*) FROM research_sessions')
            total_sessions = cursor.fetchone()[0]
            
            # Total cost
            cursor = conn.execute('SELECT SUM(total_cost) FROM research_sessions')
            total_cost = cursor.fetchone()[0] or 0
            
            # Average cost per session
            cursor = conn.execute('SELECT AVG(total_cost) FROM research_sessions WHERE status = "completed"')
            avg_cost = cursor.fetchone()[0] or 0
            
            # Total searches
            cursor = conn.execute('SELECT SUM(total_searches) FROM research_sessions')
            total_searches = cursor.fetchone()[0] or 0
            
            # Unique sources used
            cursor = conn.execute('SELECT COUNT(DISTINCT domain) FROM research_sources')
            unique_domains = cursor.fetchone()[0]
            
            return {
                'total_sessions': total_sessions,
                'total_cost': total_cost,
                'average_cost_per_session': avg_cost,
                'total_searches': total_searches,
                'unique_domains': unique_domains
            }

# Global database instance
research_db = ResearchDatabase()