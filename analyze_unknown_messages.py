#!/usr/bin/env python3
"""
Analyze participant messages in Unknown sessions for V3 and V4
"""

import sys
import os
from pathlib import Path
from typing import Dict, List
import statistics

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from version_comparison_simple import SimpleVersionComparisonDashboard

def analyze_unknown_messages():
    """Analyze participant messages in Unknown sessions for V3 and V4"""
    dashboard = SimpleVersionComparisonDashboard()
    
    # Load sessions
    print("Loading sessions...")
    sessions = dashboard.load_sessions_from_files()
    if not sessions:
        print("No sessions found!")
        return
    
    # Load messages
    session_ids = [session.get('id') for session in sessions if session.get('id')]
    print("Loading messages...")
    messages_data = dashboard.load_messages_from_files(session_ids)
    
    # Analyze Unknown sessions for V3 and V4
    v3_unknown_sessions = []
    v4_unknown_sessions = []
    
    for session in sessions:
        session_id = session.get('id')
        session_messages = messages_data.get(session_id, [])
        
        # Skip split sessions and test sessions
        if dashboard.should_exclude_session(session, session_messages):
            continue
        
        # Detect coaching method
        detected_method = dashboard.detect_coaching_method(session, session_messages)
        
        if detected_method != 'Unknown':
            continue
        
        # Determine version
        version = None
        for version_name, version_config in dashboard.coaching_bot_versions.items():
            if dashboard.matches_version(session, version_config, session_messages):
                if 'V3' in version_name:
                    version = 'V3'
                elif 'V4' in version_name:
                    version = 'V4'
                break
        
        if version == 'V3':
            # Count participant messages
            participant_message_count = 0
            for message in session_messages:
                if message.get('role') == 'user':
                    participant_message_count += 1
            
            v3_unknown_sessions.append({
                'session_id': session_id,
                'participant_message_count': participant_message_count
            })
        elif version == 'V4':
            # Count participant messages
            participant_message_count = 0
            for message in session_messages:
                if message.get('role') == 'user':
                    participant_message_count += 1
            
            v4_unknown_sessions.append({
                'session_id': session_id,
                'participant_message_count': participant_message_count
            })
    
    # Calculate statistics
    print("\n" + "="*60)
    print("PARTICIPANT MESSAGES IN UNKNOWN SESSIONS - V3 AND V4")
    print("="*60)
    
    # V3 Statistics
    if v3_unknown_sessions:
        v3_message_counts = [s['participant_message_count'] for s in v3_unknown_sessions]
        v3_total_sessions = len(v3_unknown_sessions)
        v3_total_messages = sum(v3_message_counts)
        v3_avg_messages = statistics.mean(v3_message_counts) if v3_message_counts else 0
        v3_median_messages = statistics.median(v3_message_counts) if v3_message_counts else 0
        v3_sessions_with_messages = sum(1 for count in v3_message_counts if count > 0)
        v3_sessions_without_messages = v3_total_sessions - v3_sessions_with_messages
        
        print(f"\n📊 V3 - Unknown Sessions:")
        print(f"  Total Unknown Sessions: {v3_total_sessions}")
        print(f"  Total Participant Messages: {v3_total_messages}")
        print(f"  Average Messages per Session: {v3_avg_messages:.2f}")
        print(f"  Median Messages per Session: {v3_median_messages:.1f}")
        print(f"  Sessions with Messages (>0): {v3_sessions_with_messages}")
        print(f"  Sessions without Messages (0): {v3_sessions_without_messages}")
        print(f"  Percentage with Messages: {(v3_sessions_with_messages/v3_total_sessions*100):.1f}%")
        
        # Message count distribution
        if v3_message_counts:
            print(f"\n  Message Count Distribution:")
            print(f"    Min: {min(v3_message_counts)}")
            print(f"    Max: {max(v3_message_counts)}")
            print(f"    25th percentile: {statistics.quantiles(v3_message_counts, n=4)[0]:.1f}")
            print(f"    75th percentile: {statistics.quantiles(v3_message_counts, n=4)[2]:.1f}")
    else:
        print("\n📊 V3 - Unknown Sessions: 0")
    
    # V4 Statistics
    if v4_unknown_sessions:
        v4_message_counts = [s['participant_message_count'] for s in v4_unknown_sessions]
        v4_total_sessions = len(v4_unknown_sessions)
        v4_total_messages = sum(v4_message_counts)
        v4_avg_messages = statistics.mean(v4_message_counts) if v4_message_counts else 0
        v4_median_messages = statistics.median(v4_message_counts) if v4_message_counts else 0
        v4_sessions_with_messages = sum(1 for count in v4_message_counts if count > 0)
        v4_sessions_without_messages = v4_total_sessions - v4_sessions_with_messages
        
        print(f"\n📊 V4 - Unknown Sessions:")
        print(f"  Total Unknown Sessions: {v4_total_sessions}")
        print(f"  Total Participant Messages: {v4_total_messages}")
        print(f"  Average Messages per Session: {v4_avg_messages:.2f}")
        print(f"  Median Messages per Session: {v4_median_messages:.1f}")
        print(f"  Sessions with Messages (>0): {v4_sessions_with_messages}")
        print(f"  Sessions without Messages (0): {v4_sessions_without_messages}")
        print(f"  Percentage with Messages: {(v4_sessions_with_messages/v4_total_sessions*100):.1f}%")
        
        # Message count distribution
        if v4_message_counts:
            print(f"\n  Message Count Distribution:")
            print(f"    Min: {min(v4_message_counts)}")
            print(f"    Max: {max(v4_message_counts)}")
            print(f"    25th percentile: {statistics.quantiles(v4_message_counts, n=4)[0]:.1f}")
            print(f"    75th percentile: {statistics.quantiles(v4_message_counts, n=4)[2]:.1f}")
    else:
        print("\n📊 V4 - Unknown Sessions: 0")
    
    print("\n" + "="*60)
    print("Note: Split sessions (no participant messages) and test sessions")
    print("(@dimagi.com) are excluded from this analysis.")
    print("="*60)

if __name__ == "__main__":
    analyze_unknown_messages()

