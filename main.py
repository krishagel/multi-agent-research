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
    missing_config = []
    
    if not config.settings.tavily_api_key:
        missing_config.append("TAVILY_API_KEY")
    
    if not config.settings.aws_access_key_id:
        missing_config.append("AWS_ACCESS_KEY_ID")
        
    if not config.settings.aws_secret_access_key:
        missing_config.append("AWS_SECRET_ACCESS_KEY")
    
    if missing_config:
        print("⚠️  Missing required configuration:")
        for item in missing_config:
            print(f"   - {item}")
        print("\nPlease update your .env file with the required values.")
        print("Example .env file has been created with placeholder values.")
        return False
    
    return True

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