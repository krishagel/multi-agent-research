"""Gradio UI for the research system."""
import gradio as gr
from typing import Dict, Any, Tuple, List, Optional
import json
from datetime import datetime
from pathlib import Path
from agents.research_crew import ResearchCrew
from src.config import config
from src.bedrock_client import bedrock
from src.thought_logger import thought_logger, ThoughtType
from src.research_database import research_db
import pandas as pd
import threading
import time

class ResearchUI:
    """Gradio-based UI for the research system."""
    
    def __init__(self):
        self.crew = None
        self.current_progress = 0
        self.current_status = "Ready"
        self.thought_stream = []
        self.thought_update_thread = None
        self.monitoring_thoughts = False
        self.current_search_results = []
        self.current_session_id = None
        
    def create_interface(self) -> gr.Blocks:
        """Create the Gradio interface."""
        css = """
        .thought-container {
            max-height: 600px;
            overflow-y: auto;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            background-color: #f9f9f9;
        }
        .thought-container h3 {
            margin-top: 15px;
            font-size: 0.9em;
        }
        .thought-container details {
            margin: 10px 0;
            padding: 10px;
            background-color: #f0f0f0;
            border-radius: 5px;
        }
        """
        
        with gr.Blocks(title="AI Research Assistant", theme=gr.themes.Soft(), css=css) as interface:
            gr.Markdown("# 🔍 Multi-Agent Research System")
            gr.Markdown("Powered by CrewAI, AWS Bedrock, and Tavily Search")
            
            with gr.Tabs():
                # Research Tab
                with gr.TabItem("Research"):
                    with gr.Row():
                        with gr.Column(scale=3):
                            query_input = gr.Textbox(
                                label="Research Query",
                                placeholder="Enter your research question... (Add [DEBUG] to enable debug mode)",
                                lines=3
                            )
                            
                            with gr.Row():
                                agent_config = config.get_agent_config()
                                num_researchers = gr.Slider(
                                    minimum=agent_config.min_sub_researchers,
                                    maximum=agent_config.max_sub_researchers,
                                    value=agent_config.default_sub_researchers,
                                    step=1,
                                    label="Number of Sub-Researchers"
                                )
                                
                                search_depth = gr.Radio(
                                    choices=["basic", "advanced"],
                                    value=config.settings.tavily_search_depth,
                                    label="Search Depth"
                                )
                            
                            with gr.Row():
                                submit_btn = gr.Button("Start Research", variant="primary")
                                clear_btn = gr.Button("Clear")
                        
                        with gr.Column(scale=1):
                            status_text = gr.Textbox(
                                label="Status",
                                value="Ready",
                                interactive=False
                            )
                            progress_bar = gr.Progress()
                            cost_estimate = gr.Textbox(
                                label="Estimated Cost",
                                value="$0.00",
                                interactive=False
                            )
                    
                    with gr.Row():
                        output_text = gr.Markdown(label="Research Results")
                    
                    with gr.Row():
                        download_json = gr.File(label="Download JSON")
                        download_md = gr.File(label="Download Markdown")
                
                # Settings Tab
                with gr.TabItem("Settings"):
                    gr.Markdown("## Model Configuration")
                    
                    lead_model = gr.Dropdown(
                        choices=[
                            "anthropic.claude-3-opus-20240229-v1:0",
                            "anthropic.claude-3-sonnet-20240229-v1:0",
                            "anthropic.claude-3-haiku-20240307-v1:0"
                        ],
                        value=config.settings.lead_researcher_model,
                        label="Lead Researcher Model"
                    )
                    
                    sub_model = gr.Dropdown(
                        choices=[
                            "anthropic.claude-3-opus-20240229-v1:0",
                            "anthropic.claude-3-sonnet-20240229-v1:0",
                            "anthropic.claude-3-haiku-20240307-v1:0"
                        ],
                        value=config.settings.sub_researcher_model,
                        label="Sub-Researcher Model"
                    )
                    
                    with gr.Row():
                        monthly_budget = gr.Number(
                            value=config.settings.monthly_budget_usd,
                            label="Monthly Budget (USD)"
                        )
                        alert_threshold = gr.Slider(
                            minimum=50,
                            maximum=100,
                            value=config.settings.alert_at_percent,
                            label="Alert at % of Budget"
                        )
                
                # Usage Stats Tab
                with gr.TabItem("Usage Statistics"):
                    stats_display = gr.Markdown()
                    refresh_stats_btn = gr.Button("Refresh Statistics")
                    
                    usage_graph = gr.Plot(label="Cost Trends")
                    
                    history_table = gr.Dataframe(
                        label="Recent Research History",
                        headers=["Timestamp", "Query", "Cost", "Duration"]
                    )
                
                # Research Process Tab
                with gr.TabItem("Research Process"):
                    gr.Markdown("## 🧠 AI Thought Stream")
                    gr.Markdown("Real-time view of the AI agents' thinking process during research")
                    
                    with gr.Row():
                        thought_filter = gr.Dropdown(
                            choices=["All"] + [t.value for t in ThoughtType],
                            value="All",
                            label="Filter by Thought Type",
                            interactive=True
                        )
                        agent_filter = gr.Dropdown(
                            choices=["All Agents"],
                            value="All Agents",
                            label="Filter by Agent",
                            interactive=True
                        )
                        auto_scroll = gr.Checkbox(
                            value=True,
                            label="Auto-scroll to latest",
                            interactive=True
                        )
                    
                    thought_display = gr.Markdown(
                        value="*No thoughts yet. Start a research query to see the AI's thinking process.*",
                        elem_id="thought-stream",
                        elem_classes=["thought-container"]
                    )
                    
                    with gr.Row():
                        export_thoughts_btn = gr.Button("Export Thought Log", variant="secondary")
                        clear_thoughts_btn = gr.Button("Clear Display", variant="secondary")
                    
                    thought_stats = gr.Markdown("**Thought Statistics:** No thoughts recorded yet.")
                
                # Search Results Tab
                with gr.TabItem("Search Results"):
                    gr.Markdown("## 🔍 Search Results from Current Research")
                    gr.Markdown("View all search results and sources discovered during the research process")
                    
                    with gr.Row():
                        results_filter = gr.Dropdown(
                            choices=["All Results", "By Researcher", "By Relevance"],
                            value="All Results",
                            label="View Mode",
                            interactive=True
                        )
                        refresh_results_btn = gr.Button("Refresh", variant="secondary")
                    
                    search_results_display = gr.Markdown(
                        value="*No search results yet. Start a research query to see results.*",
                        elem_classes=["search-results-container"]
                    )
                    
                    results_stats = gr.Markdown("**Search Statistics:** No searches performed yet.")
                
                # Research History Tab
                with gr.TabItem("Research History"):
                    gr.Markdown("## 📚 Past Research Sessions")
                    gr.Markdown("Browse and search through your previous research sessions")
                    
                    with gr.Row():
                        history_search = gr.Textbox(
                            label="Search Past Research",
                            placeholder="Search by query text...",
                            scale=3
                        )
                        search_history_btn = gr.Button("Search", scale=1)
                        refresh_history_btn = gr.Button("Refresh", scale=1)
                    
                    history_table = gr.Dataframe(
                        label="Research Sessions",
                        headers=["Session ID", "Query", "Date", "Duration (s)", "Cost ($)", "Status"],
                        interactive=True,
                        wrap=True
                    )
                    
                    with gr.Row():
                        session_details = gr.Markdown(
                            label="Session Details",
                            value="*Select a session from the table to view details*"
                        )
                    
                    with gr.Row():
                        selected_session_id = gr.Textbox(
                            label="Selected Session ID",
                            interactive=False,
                            visible=False
                        )
                        view_session_btn = gr.Button("View Full Session", variant="primary")
                        export_session_btn = gr.Button("Export Session", variant="secondary")
                    
                    # Database statistics
                    db_stats = gr.Markdown(label="Database Statistics")
            
            # Connect events
            submit_btn.click(
                fn=self.run_research,
                inputs=[query_input, num_researchers, search_depth],
                outputs=[output_text, status_text, download_json, download_md]
            )
            
            clear_btn.click(
                fn=lambda: ("", "", "Ready", None, None, "$0.00"),
                outputs=[query_input, output_text, status_text, download_json, download_md, cost_estimate]
            )
            
            # Update cost estimate when query or num_researchers changes
            query_input.change(
                fn=self.estimate_cost,
                inputs=[query_input, num_researchers],
                outputs=cost_estimate
            )
            
            num_researchers.change(
                fn=self.estimate_cost,
                inputs=[query_input, num_researchers],
                outputs=cost_estimate
            )
            
            refresh_stats_btn.click(
                fn=self.get_usage_statistics,
                outputs=[stats_display, usage_graph, history_table]
            )
            
            # Update model settings
            lead_model.change(
                fn=lambda x: self.update_model_setting("lead_researcher", x),
                inputs=[lead_model]
            )
            
            sub_model.change(
                fn=lambda x: self.update_model_setting("sub_researcher", x),
                inputs=[sub_model]
            )
            
            # Thought stream events
            export_thoughts_btn.click(
                fn=self.export_thoughts,
                outputs=gr.File()
            )
            
            clear_thoughts_btn.click(
                fn=self.clear_thought_display,
                outputs=[thought_display, thought_stats]
            )
            
            # Set up periodic thought stream updates
            interface.load(
                fn=self.start_thought_monitoring,
                outputs=[thought_display, thought_stats, agent_filter]
            )
            
            # Auto-refresh thought stream every 2 seconds during research
            thought_timer = gr.Timer(2.0)
            thought_timer.tick(
                fn=lambda tf, af: self.update_thought_display(tf, af) if self.monitoring_thoughts else (None, None),
                inputs=[thought_filter, agent_filter],
                outputs=[thought_display, thought_stats]
            )
            
            # Filter changes
            thought_filter.change(
                fn=self.update_thought_display,
                inputs=[thought_filter, agent_filter],
                outputs=[thought_display, thought_stats]
            )
            
            agent_filter.change(
                fn=self.update_thought_display,
                inputs=[thought_filter, agent_filter],
                outputs=[thought_display, thought_stats]
            )
            
            # Search Results events
            refresh_results_btn.click(
                fn=self.update_search_results,
                inputs=[results_filter],
                outputs=[search_results_display, results_stats]
            )
            
            results_filter.change(
                fn=self.update_search_results,
                inputs=[results_filter],
                outputs=[search_results_display, results_stats]
            )
            
            # Initial stats load
            interface.load(
                fn=self.get_usage_statistics,
                outputs=[stats_display, usage_graph, history_table]
            )
            
            # Initial cost estimate with default values
            interface.load(
                fn=lambda: self.estimate_cost("Sample research query", agent_config.default_sub_researchers),
                outputs=cost_estimate
            )
            
            # Research History events
            interface.load(
                fn=self.load_research_history,
                outputs=[history_table, db_stats]
            )
            
            refresh_history_btn.click(
                fn=self.load_research_history,
                outputs=[history_table, db_stats]
            )
            
            search_history_btn.click(
                fn=self.search_research_history,
                inputs=[history_search],
                outputs=[history_table]
            )
            
            history_table.select(
                fn=self.on_session_select,
                outputs=[session_details, selected_session_id]
            )
            
            view_session_btn.click(
                fn=self.view_full_session,
                inputs=[selected_session_id],
                outputs=[session_details]
            )
            
            export_session_btn.click(
                fn=self.export_session,
                inputs=[selected_session_id],
                outputs=gr.File()
            )
        
        return interface
    
    def run_research(
        self,
        query: str,
        num_researchers: int,
        search_depth: str
    ) -> Tuple[str, str, str, str]:
        """Run the research process."""
        if not query.strip():
            return "Please enter a research query.", "Error", None, None
        
        try:
            # Start new research session - clears thought stream and search results
            thought_logger.start_new_session()
            self.thought_stream.clear()  # Clear UI thought stream as well
            self.current_search_results.clear()  # Clear search results
            self.current_session_id = None
            
            # Update settings
            config.settings.tavily_search_depth = search_depth
            
            # Create crew with specified number of researchers
            # Enable debug mode if query contains [DEBUG]
            debug_mode = "[DEBUG]" in query
            if debug_mode:
                query = query.replace("[DEBUG]", "").strip()
                
            self.crew = ResearchCrew(num_sub_researchers=int(num_researchers), debug=debug_mode)
            
            # Progress callback
            def update_progress(status: str, progress: float):
                self.current_status = status
                self.current_progress = progress
            
            # Run research
            results = self.crew.conduct_research(query, update_progress)
            
            # Store session ID
            self.current_session_id = results.get('session_id')
            
            # Format output
            markdown_output = self._format_results_markdown(results)
            
            # Get file paths
            json_path = None
            md_path = None
            
            if self.crew.research_history:
                latest = self.crew.research_history[-1]
                json_path = latest.get('filepath')
                md_path = latest.get('markdown_filepath')
            
            return markdown_output, "Research Complete", json_path, md_path
            
        except Exception as e:
            return f"Error: {str(e)}", "Error", None, None
    
    def _format_results_markdown(self, results: Dict[str, Any]) -> str:
        """Format results for display."""
        md = f"""## Research Results

**Query:** {results['query']}  
**Duration:** {results['duration_seconds']:.1f} seconds  
**Total Cost:** ${results['statistics']['total_cost']:.4f}

### Synthesis

{results['synthesis']}

### Research Details

**Researchers Used:** {results['statistics']['num_researchers']}  
**Total Searches:** {results['statistics']['total_searches']}  
**Research Angles Explored:** {len(results['research_angles'])}
"""
        return md
    
    def get_usage_statistics(self) -> Tuple[str, Any, pd.DataFrame]:
        """Get and format usage statistics."""
        stats = bedrock.get_usage_stats()
        
        # Format stats markdown
        stats_md = f"""## Usage Statistics

### API Usage
- **Total Requests:** {stats['total_requests']}
- **Total Tokens:** {stats['total_tokens']:,}
- **Total Cost:** ${stats['total_cost']:.4f}
- **Average Cost per Request:** ${stats['average_cost_per_request']:.4f}

### Token Breakdown
- **Input Tokens:** {stats['total_input_tokens']:,}
- **Output Tokens:** {stats['total_output_tokens']:,}
"""
        
        # Create cost trend plot (placeholder for now)
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'Cost trends will appear here', 
                horizontalalignment='center', verticalalignment='center')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title('Research Cost Trends')
        
        # Create history dataframe
        history_data = []
        if hasattr(self, 'crew') and self.crew and self.crew.research_history:
            for entry in self.crew.research_history[-10:]:
                history_data.append({
                    'Timestamp': entry['timestamp'],
                    'Query': entry['query'][:50] + '...' if len(entry['query']) > 50 else entry['query'],
                    'Cost': f"${entry['cost']:.4f}",
                    'Duration': 'N/A'
                })
        
        df = pd.DataFrame(history_data) if history_data else pd.DataFrame(
            columns=['Timestamp', 'Query', 'Cost', 'Duration']
        )
        
        return stats_md, fig, df
    
    def update_model_setting(self, agent_type: str, model_id: str):
        """Update model settings."""
        if agent_type == "lead_researcher":
            config.settings.lead_researcher_model = model_id
        elif agent_type == "sub_researcher":
            config.settings.sub_researcher_model = model_id
        return f"Updated {agent_type} model to {model_id}"
    
    def estimate_cost(self, query: str, num_researchers: int) -> str:
        """Estimate the cost of a research query."""
        if not query or not query.strip():
            return "$0.00"
            
        try:
            # Rough estimation based on typical usage
            avg_tokens_per_request = 2000
            requests_per_researcher = 3
            
            # Account for query length impact
            query_length_factor = min(len(query) / 100, 2.0)  # Cap at 2x for long queries
            
            lead_cost = config.estimate_cost(
                config.settings.lead_researcher_model,
                int(avg_tokens_per_request * query_length_factor),
                avg_tokens_per_request // 2
            ) * 2  # Planning + synthesis
            
            sub_cost = config.estimate_cost(
                config.settings.sub_researcher_model,
                int(avg_tokens_per_request * query_length_factor),
                avg_tokens_per_request // 2
            ) * requests_per_researcher * num_researchers
            
            # Add fact checking and quality control costs
            quality_cost = config.estimate_cost(
                config.settings.sub_researcher_model,  # Uses Haiku model
                avg_tokens_per_request // 2,
                avg_tokens_per_request // 4
            ) * 2  # Quality controller + fact checker
            
            total_estimate = lead_cost + sub_cost + quality_cost
            return f"${total_estimate:.2f} - ${total_estimate * 1.5:.2f}"
        except Exception:
            return "$0.00 - Error calculating estimate"
    
    def start_thought_monitoring(self) -> Tuple[str, str, gr.Dropdown]:
        """Start monitoring thoughts and subscribe to updates."""
        # Subscribe to thought updates
        thought_logger.subscribe(self._on_new_thought)
        self.monitoring_thoughts = True
        
        # Get unique agents
        agents = self._get_unique_agents()
        
        return (
            self._format_thoughts(),
            self._get_thought_statistics(),
            gr.Dropdown(choices=["All Agents"] + agents, value="All Agents")
        )
    
    def _on_new_thought(self, thought: Dict[str, Any]):
        """Handle new thought from the logger."""
        self.thought_stream.append(thought)
        # Keep only last 500 thoughts to prevent memory issues
        if len(self.thought_stream) > 500:
            self.thought_stream = self.thought_stream[-500:]
        
        # Capture search results from thought metadata
        if thought.get("thought_type") == "searching" and "results" in thought.get("metadata", {}):
            search_data = {
                "timestamp": thought["timestamp"],
                "agent_id": thought["agent_id"],
                "agent_type": thought["agent_type"],
                "query": thought["metadata"].get("query", ""),
                "results": thought["metadata"]["results"],
                "num_results": thought["metadata"].get("num_results", 0)
            }
            self.current_search_results.append(search_data)
    
    def update_thought_display(
        self,
        thought_filter: str,
        agent_filter: str
    ) -> Tuple[str, str]:
        """Update the thought display based on filters."""
        return self._format_thoughts(thought_filter, agent_filter), self._get_thought_statistics()
    
    def _format_thoughts(
        self,
        thought_type_filter: str = "All",
        agent_filter: str = "All Agents"
    ) -> str:
        """Format thoughts for display."""
        if not self.thought_stream:
            return "*No thoughts yet. Start a research query to see the AI's thinking process.*"
        
        filtered_thoughts = self.thought_stream
        
        # Apply filters
        if thought_type_filter != "All":
            filtered_thoughts = [t for t in filtered_thoughts if t["thought_type"] == thought_type_filter]
        
        if agent_filter != "All Agents":
            filtered_thoughts = [t for t in filtered_thoughts if t["agent_id"] == agent_filter]
        
        if not filtered_thoughts:
            return "*No thoughts match the current filters.*"
        
        # Format thoughts for display
        formatted = []
        for thought in filtered_thoughts[-50:]:  # Show last 50 thoughts
            timestamp = datetime.fromisoformat(thought["timestamp"]).strftime("%H:%M:%S")
            agent_type = thought["agent_type"]
            thought_type = thought["thought_type"]
            content = thought["content"]
            metadata = thought.get("metadata", {})
            confidence = thought.get("confidence")
            
            # Choose emoji based on thought type
            emoji_map = {
                "planning": "📋",
                "searching": "🔍",
                "analyzing": "🤔",
                "synthesizing": "🧩",
                "evaluating": "⚖️",
                "deciding": "🎯",
                "error": "❌",
                "info": "ℹ️"
            }
            emoji = emoji_map.get(thought_type, "💭")
            
            # Format the thought
            thought_html = f"""
### {emoji} [{timestamp}] {agent_type} - {thought_type.upper()}
**{content}**
"""
            
            # Add metadata if present
            if metadata:
                metadata_str = json.dumps(metadata, indent=2)
                if len(metadata_str) > 200:
                    metadata_str = metadata_str[:200] + "..."
                thought_html += f"\n<details><summary>Details</summary>\n\n```json\n{metadata_str}\n```\n</details>\n"
            
            # Add confidence if present
            if confidence:
                confidence_bar = "🟩" * int(confidence * 10) + "⬜" * (10 - int(confidence * 10))
                thought_html += f"\n*Confidence: {confidence_bar} {confidence:.0%}*\n"
            
            formatted.append(thought_html)
        
        return "\n---\n".join(formatted)
    
    def _get_thought_statistics(self) -> str:
        """Get statistics about the current thought stream."""
        if not self.thought_stream:
            return "**Thought Statistics:** No thoughts recorded yet."
        
        # Count by type
        type_counts = {}
        agent_counts = {}
        
        for thought in self.thought_stream:
            thought_type = thought["thought_type"]
            agent_type = thought["agent_type"]
            
            type_counts[thought_type] = type_counts.get(thought_type, 0) + 1
            agent_counts[agent_type] = agent_counts.get(agent_type, 0) + 1
        
        stats = f"**Thought Statistics:** {len(self.thought_stream)} total thoughts\n\n"
        stats += "**By Type:** " + ", ".join([f"{k}: {v}" for k, v in type_counts.items()]) + "\n"
        stats += "**By Agent:** " + ", ".join([f"{k}: {v}" for k, v in agent_counts.items()])
        
        return stats
    
    def _get_unique_agents(self) -> List[str]:
        """Get list of unique agent IDs from thought stream."""
        agents = set()
        for thought in self.thought_stream:
            agents.add(thought["agent_id"])
        return sorted(list(agents))
    
    def export_thoughts(self) -> str:
        """Export the current thought log."""
        if not self.thought_stream:
            return None
        
        # Create export file
        export_path = thought_logger.export_thoughts()
        return str(export_path)
    
    def clear_thought_display(self) -> Tuple[str, str]:
        """Clear the thought display."""
        self.thought_stream.clear()
        return (
            "*Thought display cleared. New thoughts will appear here.*",
            "**Thought Statistics:** No thoughts recorded yet."
        )
    
    def load_research_history(self) -> Tuple[pd.DataFrame, str]:
        """Load research history from database."""
        sessions = research_db.get_recent_sessions(limit=50)
        
        # Convert to dataframe format
        data = []
        for session in sessions:
            data.append({
                'Session ID': session['session_id'],
                'Query': session['query'][:100] + '...' if len(session['query']) > 100 else session['query'],
                'Date': datetime.fromisoformat(str(session['timestamp'])).strftime("%Y-%m-%d %H:%M"),
                'Duration (s)': f"{session.get('duration_seconds', 0):.1f}" if session.get('duration_seconds') else 'N/A',
                'Cost ($)': f"{session.get('total_cost', 0):.4f}" if session.get('total_cost') else 'N/A',
                'Status': session.get('status', 'unknown')
            })
        
        df = pd.DataFrame(data) if data else pd.DataFrame(
            columns=['Session ID', 'Query', 'Date', 'Duration (s)', 'Cost ($)', 'Status']
        )
        
        # Get database statistics
        stats = research_db.get_statistics()
        stats_md = f"""**Database Statistics:**
- Total Research Sessions: {stats['total_sessions']}
- Total Cost: ${stats['total_cost']:.4f}
- Average Cost per Session: ${stats['average_cost_per_session']:.4f}
- Total Searches Performed: {stats['total_searches']}
- Unique Domains Used: {stats['unique_domains']}"""
        
        return df, stats_md
    
    def search_research_history(self, query: str) -> pd.DataFrame:
        """Search research history by query."""
        if not query.strip():
            return self.load_research_history()[0]
        
        sessions = research_db.search_sessions(query)
        
        # Convert to dataframe format
        data = []
        for session in sessions:
            data.append({
                'Session ID': session['session_id'],
                'Query': session['query'][:100] + '...' if len(session['query']) > 100 else session['query'],
                'Date': datetime.fromisoformat(str(session['timestamp'])).strftime("%Y-%m-%d %H:%M"),
                'Duration (s)': f"{session.get('duration_seconds', 0):.1f}" if session.get('duration_seconds') else 'N/A',
                'Cost ($)': f"{session.get('total_cost', 0):.4f}" if session.get('total_cost') else 'N/A',
                'Status': session.get('status', 'unknown')
            })
        
        return pd.DataFrame(data) if data else pd.DataFrame(
            columns=['Session ID', 'Query', 'Date', 'Duration (s)', 'Cost ($)', 'Status']
        )
    
    def on_session_select(self, evt: gr.SelectData) -> Tuple[str, str]:
        """Handle session selection from table."""
        try:
            # Get session ID from the selected row
            if evt and hasattr(evt, 'row_value') and evt.row_value:
                # Use row_value to get the entire row data
                session_id = evt.row_value[0]  # First column is Session ID
            elif evt and hasattr(evt, 'value'):
                # Fallback to cell value if row_value not available
                session_id = evt.value
            else:
                return "*Select a session from the table to view details*", ""
            
            session = research_db.get_session_details(session_id)
            
            if session:
                        summary = f"""## Research Session: {session_id}

**Query:** {session['query']}
**Date:** {datetime.fromisoformat(str(session['timestamp'])).strftime("%Y-%m-%d %H:%M")}
**Duration:** {session.get('duration_seconds', 0):.1f} seconds
**Total Cost:** ${session.get('total_cost', 0):.4f}

### Research Plan
{session.get('research_plan', {}).get('plan', 'N/A')}

### Summary
Found {len(session.get('findings', []))} research angles with {session.get('total_searches', 0)} total searches.

Click "View Full Session" to see complete details including findings and sources."""
                        
                        return summary, session_id
        except Exception as e:
            return f"*Error loading session: {str(e)}*", ""
        
        return "*Select a session from the table to view details*", ""
    
    def view_full_session(self, session_id: str) -> str:
        """View full session details."""
        if not session_id:
            return "*No session selected*"
        
        session = research_db.get_session_details(session_id)
        if not session:
            return f"*Session {session_id} not found*"
        
        # Format full session details
        md = f"""## Full Research Report - Session {session_id}

**Query:** {session['query']}
**Date:** {datetime.fromisoformat(str(session['timestamp'])).strftime("%Y-%m-%d %H:%M")}
**Duration:** {session.get('duration_seconds', 0):.1f} seconds
**Total Cost:** ${session.get('total_cost', 0):.4f}

### Research Plan
{session.get('research_plan', {}).get('plan', 'N/A')}

### Synthesis
{session.get('synthesis', 'No synthesis available')}

### Research Findings by Angle
"""
        
        for finding in session.get('findings', []):
            md += f"\n#### {finding['research_angle']}\n\n"
            md += f"{finding['findings']}\n\n"
            
            if finding.get('sources'):
                md += "**Sources Used:**\n"
                for source in finding['sources'][:5]:
                    # Make sure we have valid URLs
                    url = source.get('url', '#')
                    title = source.get('title', 'Untitled')
                    domain = source.get('domain', 'Unknown')
                    score = source.get('relevance_score', source.get('score', 0))
                    md += f"- [{title}]({url}) - {domain} (Score: {score:.2f})\n"
                md += "\n"
        
        return md
    
    def export_session(self, session_id: str) -> Optional[str]:
        """Export session details to JSON file."""
        if not session_id:
            return None
        
        session = research_db.get_session_details(session_id)
        if not session:
            return None
        
        # Create export file
        export_path = Path("data/exports")
        export_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"research_export_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = export_path / filename
        
        with open(filepath, 'w') as f:
            json.dump(session, f, indent=2, default=str)
        
        return str(filepath)
    
    def update_search_results(self, filter_mode: str) -> Tuple[str, str]:
        """Update the search results display."""
        if not self.current_search_results:
            return "*No search results yet. Start a research query to see results.*", "**Search Statistics:** No searches performed yet."
        
        # Calculate statistics
        total_searches = len(self.current_search_results)
        total_results = sum(sr['num_results'] for sr in self.current_search_results)
        unique_queries = len(set(sr['query'] for sr in self.current_search_results))
        
        stats = f"""**Search Statistics:**
- Total Searches: {total_searches}
- Total Results Found: {total_results}
- Unique Queries: {unique_queries}
- Average Results per Search: {total_results / max(1, total_searches):.1f}"""
        
        # Format results based on filter mode
        if filter_mode == "By Researcher":
            return self._format_results_by_researcher(), stats
        elif filter_mode == "By Relevance":
            return self._format_results_by_relevance(), stats
        else:  # All Results
            return self._format_all_results(), stats
    
    def _format_all_results(self) -> str:
        """Format all search results chronologically."""
        md = "## All Search Results\n\n"
        
        for i, search in enumerate(self.current_search_results):
            timestamp = datetime.fromisoformat(search["timestamp"]).strftime("%H:%M:%S")
            md += f"### Search {i+1} - {timestamp}\n"
            md += f"**Query:** {search['query']}\n"
            md += f"**Agent:** {search['agent_type']} ({search['agent_id']})\n"
            md += f"**Results Found:** {search['num_results']}\n\n"
            
            if search['results']:
                md += "#### Top Results:\n"
                for result in search['results']:
                    md += f"{result['rank']}. **[{result['title']}]({result['url']})**\n"
                    md += f"   - Domain: {result['domain']}\n"
                    md += f"   - Relevance Score: {result['score']:.2f}\n"
                    md += f"   - Snippet: {result['snippet']}\n\n"
            
            md += "---\n\n"
        
        return md
    
    def _format_results_by_researcher(self) -> str:
        """Format search results grouped by researcher."""
        md = "## Search Results by Researcher\n\n"
        
        # Group by agent_id
        by_agent = {}
        for search in self.current_search_results:
            agent_key = f"{search['agent_type']} ({search['agent_id']})"
            if agent_key not in by_agent:
                by_agent[agent_key] = []
            by_agent[agent_key].append(search)
        
        for agent, searches in by_agent.items():
            md += f"### {agent}\n"
            md += f"**Total Searches:** {len(searches)}\n\n"
            
            for search in searches:
                md += f"**Query:** {search['query']}\n"
                if search['results']:
                    for result in search['results'][:3]:  # Top 3 per search
                        md += f"- [{result['title']}]({result['url']}) (Score: {result['score']:.2f})\n"
                md += "\n"
            
            md += "---\n\n"
        
        return md
    
    def _format_results_by_relevance(self) -> str:
        """Format search results sorted by relevance score."""
        md = "## Search Results by Relevance\n\n"
        
        # Collect all results with their search context
        all_results = []
        for search in self.current_search_results:
            for result in search['results']:
                all_results.append({
                    'query': search['query'],
                    'agent': f"{search['agent_type']} ({search['agent_id']})",
                    **result
                })
        
        # Sort by relevance score
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        md += "### Top 20 Most Relevant Results\n\n"
        for i, result in enumerate(all_results[:20]):
            md += f"{i+1}. **[{result['title']}]({result['url']})**\n"
            md += f"   - Relevance Score: {result['score']:.2f}\n"
            md += f"   - Domain: {result['domain']}\n"
            md += f"   - Query: {result['query']}\n"
            md += f"   - Found by: {result['agent']}\n"
            md += f"   - Snippet: {result['snippet']}\n\n"
        
        return md