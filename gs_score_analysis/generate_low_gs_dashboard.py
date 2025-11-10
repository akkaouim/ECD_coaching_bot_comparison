#!/usr/bin/env python3
"""
Generate a version comparison dashboard filtered to participants with low GS scores (<=85).
"""

import json
import sys
from pathlib import Path

# Import the dashboard class
sys.path.insert(0, str(Path(__file__).parent))
from version_comparison_simple import SimpleVersionComparisonDashboard

class LowGSDashboard(SimpleVersionComparisonDashboard):
    """Dashboard generator filtered to low GS score participants"""
    
    def __init__(self, participant_ids: list, gs_scores: dict = None):
        super().__init__()
        self.filter_participant_ids = {pid.lower() for pid in participant_ids}  # Case-insensitive matching
        self.gs_scores = gs_scores or {}
        self.output_dir = Path("output/low_gs_participants_dashboard")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Filtering dashboard to {len(participant_ids)} participants with low GS scores")
        print(f"Participant IDs: {', '.join(sorted(participant_ids))}")
    
    def load_sessions_from_files(self):
        """Load sessions filtered to specific participant IDs"""
        sessions = super().load_sessions_from_files()
        
        # Filter to only include sessions from our target participants
        filtered_sessions = []
        for session in sessions:
            participant_id = session.get('participant', {}).get('identifier', '')
            if participant_id.lower() in self.filter_participant_ids:
                filtered_sessions.append(session)
        
        print(f"Filtered to {len(filtered_sessions)} sessions from target participants (from {len(sessions)} total)")
        return filtered_sessions
    
    def generate_dashboard_html(self, *args, **kwargs):
        """Override to add custom title and description"""
        html = super().generate_dashboard_html(*args, **kwargs)
        
        # Add note to title
        html = html.replace(
            'Version Comparison Dashboard',
            'Version Comparison Dashboard - Low GS Score Participants (≤85)'
        )
        
        # Add note to overview section
        gs_range = f"{min(self.gs_scores.values())}-{max(self.gs_scores.values())}" if self.gs_scores else "≤85"
        note = f'''
        <div class="alert alert-warning mt-3">
            <h5 class="alert-heading">
                <i class="fas fa-filter me-2"></i>
                Filtered Dashboard
            </h5>
            <p class="mb-0">
                This dashboard shows data for <strong>{len(self.filter_participant_ids)} participants with GS scores ≤85</strong> (GS range: {gs_range}).
                <br>
                All sessions from these participants are included, regardless of refrigerator example status.
            </p>
        </div>
        '''
        
        # Insert after the overview alert
        html = html.replace(
            '</div>\n        </div>\n\n        <!-- Global Filters Section -->',
            f'</div>\n        </div>\n{note}\n        <!-- Global Filters Section -->'
        )
        
        return html

def main():
    """Main function to generate the filtered dashboard"""
    # Load participant IDs from the analysis file
    analysis_file = Path("output/high_refrigerator_low_gs_analysis.json")
    if not analysis_file.exists():
        print(f"Error: Analysis file not found: {analysis_file}")
        print("Please run analyze_gs_scores_refrigerator.py first")
        return
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        analysis_data = json.load(f)
    
    participant_ids = [p['participant_id'] for p in analysis_data['participants']]
    gs_scores = {p['participant_id']: p['gs_score'] for p in analysis_data['participants']}
    
    if not participant_ids:
        print("No participant IDs found in analysis file")
        return
    
    print("=" * 80)
    print("Generating Version Comparison Dashboard for Low GS Score Participants")
    print("=" * 80)
    print(f"Number of participants: {len(participant_ids)}")
    print(f"GS Score range: {min(gs_scores.values())} - {max(gs_scores.values())}")
    print()
    
    # Create dashboard generator
    dashboard = LowGSDashboard(participant_ids, gs_scores)
    
    # Generate dashboard
    output_file = dashboard.generate_dashboard()
    
    print()
    print("=" * 80)
    print(f"Dashboard generated successfully!")
    print(f"Output file: {output_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()

