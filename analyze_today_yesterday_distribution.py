#!/usr/bin/env python3
"""
Analyze distribution of today/yesterday questions by version and method
"""

import json
import re
from pathlib import Path
from collections import defaultdict
import sys

sys.path.append('.')
from version_comparison_simple import SimpleVersionComparisonDashboard

def main():
    dashboard = SimpleVersionComparisonDashboard()
    
    # Load sessions
    sessions = dashboard.load_sessions_from_files()
    session_ids = [s.get('id') for s in sessions if s.get('id')]
    messages_data = dashboard.load_messages_from_files(session_ids)
    
    # Track distribution
    by_version = defaultdict(int)
    by_method = defaultdict(int)
    by_version_method = defaultdict(lambda: defaultdict(int))
    
    total_found = 0
    
    for session in sessions:
        session_id = session.get('id')
        if not session_id:
            continue
        
        messages = messages_data.get(session_id, [])
        
        # Skip split sessions and test sessions
        if dashboard.should_exclude_session(session, messages):
            continue
        
        # Check if question exists
        question_found = False
        for message in reversed(messages):
            if message.get('role') == 'assistant':
                content = message.get('content', '').lower()
                original_content = message.get('content', '')
                
                has_today = 'today' in content or "today's" in content
                has_yesterday = 'yesterday' in content or "yesterday's" in content
                
                if has_today and has_yesterday:
                    if len(original_content) > 1000 or 'guide a conversation' in content:
                        continue
                    
                    question_indicators = [
                        'which', 'what', 'do you', 'did you', 'would you', 
                        'prefer', 'find', 'useful', 'better', 'question'
                    ]
                    has_question_marker = any(indicator in content for indicator in question_indicators)
                    ends_with_question = original_content.strip().endswith('?')
                    
                    if has_question_marker or ends_with_question:
                        question_found = True
                        break
        
        if question_found:
            total_found += 1
            
            # Determine version
            version = None
            for version_name, version_config in dashboard.coaching_bot_versions.items():
                if dashboard.matches_version(session, version_config, messages):
                    if 'Control' in version_name:
                        version = 'Control bot'
                    elif 'V3' in version_name:
                        version = 'Coaching bot V3'
                    elif 'V4' in version_name:
                        version = 'Coaching bot V4'
                    elif 'V5' in version_name:
                        version = 'Coaching bot V5'
                    elif 'V6' in version_name:
                        version = 'Coaching bot V6'
                    break
            
            # Determine method
            method = dashboard.detect_coaching_method(session, messages)
            
            if version:
                by_version[version] += 1
            if method:
                by_method[method] += 1
            if version and method:
                by_version_method[version][method] += 1
    
    print(f"\nTotal sessions with today/yesterday questions: {total_found}")
    print(f"\nBy Version:")
    for version, count in sorted(by_version.items()):
        print(f"  {version}: {count}")
    
    print(f"\nBy Method:")
    for method, count in sorted(by_method.items()):
        print(f"  {method}: {count}")
    
    print(f"\nBy Version and Method:")
    for version in sorted(by_version_method.keys()):
        print(f"  {version}:")
        for method in sorted(by_version_method[version].keys()):
            print(f"    {method}: {by_version_method[version][method]}")

if __name__ == "__main__":
    main()




