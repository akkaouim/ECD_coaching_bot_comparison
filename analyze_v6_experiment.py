#!/usr/bin/env python3
"""
Analyze sessions from "ECD Coach - (Nigeria Experiments) V6" experiment
to find version numbers and tags
"""

import os
import sys
import json
from pathlib import Path
from collections import defaultdict, Counter

# Add parent directory to path to access constants.py
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import constants

def analyze_v6_experiment():
    """Analyze sessions from V6 experiment to find version numbers and tags"""
    
    # Load sessions from files
    sessions_dir = Path("../data/consolidated/sessions")
    if not sessions_dir.exists():
        print(f"Error: {sessions_dir} not found")
        return
    
    print(f"Analyzing sessions from: {sessions_dir}")
    print(f"Looking for experiment: 'ECD Coach - (Nigeria Experiments) V6'")
    
    # Track version numbers and tags
    version_numbers = []
    all_tags = []
    experiment_sessions = []
    
    session_files = list(sessions_dir.glob("session_*.json"))
    print(f"Found {len(session_files)} session files")
    
    for session_file in session_files:
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session = json.load(f)
            
            experiment_name = session.get('experiment', {}).get('name', '')
            version_number = session.get('experiment', {}).get('version_number', 0)
            
            # Check if this is the V6 experiment
            if 'ECD Coach - (Nigeria Experiments) V6' in experiment_name:
                experiment_sessions.append(session)
                version_numbers.append(version_number)
                
                # Collect session tags
                session_tags = session.get('tags', [])
                all_tags.extend(session_tags)
                
                print(f"Found V6 session: version {version_number}, tags: {session_tags}")
        
        except Exception as e:
            print(f"Warning: Could not load {session_file.name}: {e}")
            continue
    
    print(f"\n=== ANALYSIS RESULTS ===")
    print(f"Total V6 sessions found: {len(experiment_sessions)}")
    
    if version_numbers:
        print(f"\nVersion numbers found:")
        version_counter = Counter(version_numbers)
        for version, count in sorted(version_counter.items()):
            print(f"  Version {version}: {count} sessions")
        
        print(f"\nVersion number range: {min(version_numbers)} to {max(version_numbers)}")
    else:
        print("No version numbers found!")
    
    if all_tags:
        print(f"\nAll tags found ({len(all_tags)} total):")
        tag_counter = Counter(all_tags)
        for tag, count in sorted(tag_counter.items()):
            print(f"  '{tag}': {count} occurrences")
    else:
        print("No tags found!")
    
    # Show some example sessions
    print(f"\n=== SAMPLE SESSIONS ===")
    for i, session in enumerate(experiment_sessions[:5]):  # Show first 5
        print(f"\nSession {i+1}:")
        print(f"  ID: {session.get('id', 'N/A')}")
        print(f"  Experiment: {session.get('experiment', {}).get('name', 'N/A')}")
        print(f"  Version: {session.get('experiment', {}).get('version_number', 'N/A')}")
        print(f"  Tags: {session.get('tags', [])}")
        print(f"  Message count: {session.get('message_count', 'N/A')}")
        print(f"  First message role: {session.get('first_message_role', 'N/A')}")

if __name__ == "__main__":
    analyze_v6_experiment()
