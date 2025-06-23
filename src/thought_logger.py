"""Centralized thought logging system for AI agents."""
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
import queue
import threading

class ThoughtType(Enum):
    """Types of thoughts that agents can have."""
    PLANNING = "planning"
    SEARCHING = "searching"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    EVALUATING = "evaluating"
    DECIDING = "deciding"
    ERROR = "error"
    INFO = "info"

class ThoughtLogger:
    """Centralized logger for agent thoughts and reasoning."""
    
    def __init__(self, log_to_file: bool = True):
        self.thoughts: List[Dict[str, Any]] = []
        self.thought_queue = queue.Queue()
        self.subscribers: List[Callable] = []
        self.log_to_file = log_to_file
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if self.log_to_file:
            self.log_dir = Path("data/thought_logs")
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.log_file = self.log_dir / f"thoughts_{self.session_id}.jsonl"
        
        # Start background thread for processing thoughts
        self.processing = True
        self.processor_thread = threading.Thread(target=self._process_thoughts, daemon=True)
        self.processor_thread.start()
    
    def log_thought(
        self,
        agent_id: str,
        agent_type: str,
        thought_type: ThoughtType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None
    ):
        """Log a thought from an agent."""
        thought = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "agent_type": agent_type,
            "thought_type": thought_type.value,
            "content": content,
            "metadata": metadata or {},
            "confidence": confidence
        }
        
        self.thought_queue.put(thought)
    
    def _process_thoughts(self):
        """Background thread to process thoughts."""
        while self.processing:
            try:
                thought = self.thought_queue.get(timeout=0.1)
                self.thoughts.append(thought)
                
                # Write to file if enabled
                if self.log_to_file:
                    with open(self.log_file, 'a') as f:
                        f.write(json.dumps(thought) + '\n')
                
                # Notify subscribers
                for subscriber in self.subscribers:
                    try:
                        subscriber(thought)
                    except Exception as e:
                        print(f"Error notifying subscriber: {e}")
                        
            except queue.Empty:
                continue
    
    def subscribe(self, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe to thought updates."""
        self.subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[Dict[str, Any]], None]):
        """Unsubscribe from thought updates."""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    def get_thoughts(
        self,
        agent_id: Optional[str] = None,
        thought_type: Optional[ThoughtType] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get thoughts with optional filtering."""
        filtered_thoughts = self.thoughts
        
        if agent_id:
            filtered_thoughts = [t for t in filtered_thoughts if t["agent_id"] == agent_id]
        
        if thought_type:
            filtered_thoughts = [t for t in filtered_thoughts if t["thought_type"] == thought_type.value]
        
        if limit:
            filtered_thoughts = filtered_thoughts[-limit:]
        
        return filtered_thoughts
    
    def get_thought_summary(self) -> Dict[str, Any]:
        """Get a summary of all thoughts."""
        summary = {
            "total_thoughts": len(self.thoughts),
            "by_type": {},
            "by_agent": {},
            "session_id": self.session_id
        }
        
        # Count by type
        for thought in self.thoughts:
            thought_type = thought["thought_type"]
            summary["by_type"][thought_type] = summary["by_type"].get(thought_type, 0) + 1
            
            agent_id = thought["agent_id"]
            summary["by_agent"][agent_id] = summary["by_agent"].get(agent_id, 0) + 1
        
        return summary
    
    def export_thoughts(self, filepath: Optional[Path] = None) -> Path:
        """Export all thoughts to a JSON file."""
        if not filepath:
            filepath = self.log_dir / f"thought_export_{self.session_id}.json"
        
        export_data = {
            "session_id": self.session_id,
            "export_time": datetime.now().isoformat(),
            "summary": self.get_thought_summary(),
            "thoughts": self.thoughts
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return filepath
    
    def clear(self):
        """Clear all thoughts."""
        self.thoughts.clear()
    
    def start_new_session(self):
        """Start a new research session with a fresh session ID and optionally clear thoughts."""
        # Clear in-memory thoughts for UI
        self.thoughts.clear()
        
        # Create new session ID
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create new log file if logging to file
        if self.log_to_file:
            self.log_file = self.log_dir / f"thoughts_{self.session_id}.jsonl"
        
        # Notify subscribers of session change
        session_change_thought = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": "system",
            "agent_type": "system",
            "thought_type": ThoughtType.INFO.value,
            "content": "New research session started",
            "metadata": {"session_id": self.session_id},
            "confidence": None
        }
        
        # Process this thought to notify subscribers
        self.thought_queue.put(session_change_thought)
    
    def stop(self):
        """Stop the thought logger."""
        self.processing = False
        self.processor_thread.join()

# Global thought logger instance
thought_logger = ThoughtLogger()