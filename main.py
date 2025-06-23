"""Main entry point for the research system."""
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ui.gradio_app import ResearchUI
from src.config import config
import warnings
warnings.filterwarnings("ignore")

def check_config():
    """Check if required configuration is present."""
    from src.exceptions import ConfigurationError
    
    try:
        config.validate_configuration()
        return True
    except ConfigurationError as e:
        print(f"⚠️  Configuration Error: {e}")
        print("\nPlease update your .env file with the required values.")
        print("See .env.example for reference.")
        return False

def main():
    """Run the research system."""
    print("🚀 Starting Multi-Agent Research System...")
    
    # Check configuration
    if not check_config():
        print("\n❌ Configuration check failed. Please update your .env file.")
        return
    
    print("✅ Configuration loaded successfully")
    print(f"   - Lead Researcher Model: {config.settings.lead_researcher_model}")
    print(f"   - Sub-Researcher Model: {config.settings.sub_researcher_model}")
    print(f"   - Search Depth: {config.settings.tavily_search_depth}")
    print(f"   - Monthly Budget: ${config.settings.monthly_budget_usd}")
    
    # Create and launch UI
    print("\n🌐 Launching Gradio interface...")
    ui = ResearchUI()
    interface = ui.create_interface()
    
    # Launch the interface
    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        inbrowser=True
    )

if __name__ == "__main__":
    main()