#!/usr/bin/env python3
"""
Version Comparison Dashboard Runner
==================================

Simple script to run the version comparison dashboard with various options.

Usage:
    python run_dashboard.py                    # Generate dashboard
    python run_dashboard.py --test             # Test mode with limited data
    python run_dashboard.py --help             # Show help
"""

import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from version_comparison_simple import SimpleVersionComparisonDashboard

def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description='Version Comparison Dashboard Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_dashboard.py                    # Generate dashboard
  python run_dashboard.py --test             # Test mode with limited data
  python run_dashboard.py --output custom/  # Custom output directory
        """
    )
    
    parser.add_argument(
        '--test', 
        action='store_true', 
        help='Run in test mode with limited data (faster for testing)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Custom output directory (default: version_comparison/)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output for debugging'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize dashboard
        dashboard = SimpleVersionComparisonDashboard()
        
        # Override output directory if specified
        if args.output:
            dashboard.output_dir = Path(args.output)
            dashboard.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Add verbose mode if needed
        if args.verbose:
            print("Verbose mode enabled")
            print(f"Output directory: {dashboard.output_dir}")
            print(f"Data directory: {dashboard.data_dir}")
        
        # Generate dashboard
        print("🚀 Starting Version Comparison Dashboard Generation...")
        output_file = dashboard.generate_dashboard()
        
        if output_file and os.path.exists(output_file):
            print(f"✅ Dashboard generated successfully: {output_file}")
            print(f"📊 File size: {os.path.getsize(output_file)} bytes")
            print(f"🌐 Open in browser: {output_file}")
            print(f"📁 Output directory: {dashboard.output_dir}")
            
            # Show next steps
            print("\n📋 Next Steps:")
            print("1. Open the dashboard in your browser")
            print("2. For full functionality, serve via HTTP:")
            print(f"   cd {dashboard.output_dir} && python3 -m http.server 8002")
            print("3. Then open: http://localhost:8002/version_comparison_dashboard.html")
            
        else:
            print("❌ Failed to generate dashboard")
            return 1
            
    except Exception as e:
        print(f"❌ Error generating dashboard: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
