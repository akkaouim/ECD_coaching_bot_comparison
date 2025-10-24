#!/usr/bin/env python3
"""
Find session IDs for Coaching bot V6 with unidentified coaching methods.
"""

import json
from pathlib import Path
from typing import Dict, List

def load_sessions_and_messages() -> tuple[List[Dict], Dict[str, List[Dict]]]:
    """Load sessions and messages from the consolidated data directory."""
    sessions_dir = Path("../data/consolidated/sessions")
    messages_dir = Path("../data/consolidated/messages")
    
    if not sessions_dir.exists() or not messages_dir.exists():
        print("Error: Data directories not found")
        return [], {}
    
    # Load sessions
    sessions = []
    session_files = list(sessions_dir.glob("session_*.json"))
    print(f"Found {len(session_files)} session files")
    
    for session_file in session_files:
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session = json.load(f)
            sessions.append(session)
        except Exception as e:
            print(f"Warning: Could not load {session_file.name}: {e}")
            continue
    
    # Load messages
    messages_data = {}
    message_files = list(messages_dir.glob("messages_*.json"))
    print(f"Found {len(message_files)} message files")
    
    for message_file in message_files:
        try:
            with open(message_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            session_id = message_file.stem.replace("messages_", "")
            messages = session_data.get('messages', [])
            messages_data[session_id] = messages
        except Exception as e:
            print(f"Warning: Could not load {message_file.name}: {e}")
            continue
    
    print(f"Loaded {len(sessions)} sessions and {len(messages_data)} message sets")
    return sessions, messages_data

def is_coaching_method_tag(tag: str) -> bool:
    """Check if a tag is a coaching method tag"""
    return tag.startswith('coach_method_')

def detect_coaching_method(session: Dict, messages: List[Dict] = None) -> str:
    """Detect coaching method from tags or message content"""
    # First, check for method tags in session
    session_tags = session.get('tags', [])
    for tag in session_tags:
        if tag == 'coach_method_scenarios':
            return 'Scenario'
        elif tag == 'coach_method_microlearning':
            return 'Microlearning'
        elif tag == 'coach_method_microlearning_vaccine':
            return 'Microlearning vaccines'
        elif tag == 'coach_method_motivational_interviewing':
            return 'Motivational interviewing'
        elif tag == 'coach_method_visit_debrief':
            return 'Visit check in'
    
    # Check message tags if no session tags found
    if messages:
        for message in messages:
            message_tags = message.get('tags', [])
            for tag in message_tags:
                if tag == 'coach_method_scenarios':
                    return 'Scenario'
                elif tag == 'coach_method_microlearning':
                    return 'Microlearning'
                elif tag == 'coach_method_microlearning_vaccine':
                    return 'Microlearning vaccines'
                elif tag == 'coach_method_motivational_interviewing':
                    return 'Motivational interviewing'
                elif tag == 'coach_method_visit_debrief':
                    return 'Visit check in'
    
    # If no tags found, analyze message content
    if messages:
        for message in messages:
            if message.get('role') == 'assistant':  # Only check assistant messages
                content = message.get('content', '').lower()
                if any(keyword in content for keyword in ['roleplay', 'role-play', 'scenario 1:', 'scenario 2:']):
                    return 'Scenario'
                elif any(keyword in content for keyword in ['quiz', 'microlearning', 'short quiz questions']):
                    return 'Microlearning'
                elif any(keyword in content for keyword in ['motivational interview', 'motivational interviewing']):
                    return 'Motivational interviewing'
                elif any(keyword in content for keyword in ['visit debrief', 'home visits', 'most recent visit']):
                    return 'Visit check in'
    
    return 'Unknown'

def get_version_from_last_message(messages: List[Dict]) -> int:
    """Extract version number from the last message's tags"""
    if not messages:
        return 0
    
    # Get the last message
    last_message = messages[-1]
    tags = last_message.get('tags', [])
    
    for tag in tags:
        if tag.startswith('v') and tag[1:].isdigit():
            return int(tag[1:])
    
    return 0

def matches_version(session: Dict, version_config: Dict, messages: List[Dict] = None) -> bool:
    """Check if session matches version criteria based on last message version tag"""
    experiment_id = session.get('experiment', {}).get('id', '')
    
    # Check experiment ID match
    if experiment_id not in version_config['experiment_id']:
        return False
    
    # Get version from last message tags if available
    version_number = get_version_from_last_message(messages) if messages else 0
    
    # Check version constraints
    version_range = version_config.get('version_range')
    if version_range is None:
        return True  # All versions
    elif version_range[1] is None:
        return version_number >= version_range[0]  # min and above
    else:
        return version_range[0] <= version_number <= version_range[1]  # range

def find_v6_unknown_sessions():
    """Find session IDs for Coaching bot V6 with unidentified coaching methods."""
    print("Loading sessions and messages...")
    sessions, messages_data = load_sessions_and_messages()
    
    if not sessions:
        print("No sessions found")
        return
    
    # V6 configuration
    v6_config = {
        "experiment_id": ["5d8be75e-03ff-4e3a-ab6a-e0aff6580986"],
        "version_range": (5, None)  # 5 and above
    }
    
    v6_unknown_sessions = []
    
    for session in sessions:
        # Check if participant is Dimagi staff
        participant_id = session.get('participant', {}).get('identifier', '')
        if participant_id.endswith('@dimagi.com'):
            continue
        
        session_id = session.get('id')
        if not session_id:
            continue
            
        messages = messages_data.get(session_id, [])
        if not messages:
            continue
        
        # Check if it's V6
        if not matches_version(session, v6_config, messages):
            continue
        
        # Detect coaching method
        detected_method = detect_coaching_method(session, messages)
        
        if detected_method == 'Unknown':
            v6_unknown_sessions.append(session_id)
    
    print(f"\n=== V6 UNKNOWN COACHING METHOD SESSIONS ===")
    print(f"Found {len(v6_unknown_sessions)} V6 sessions with unidentified coaching methods")
    
    if v6_unknown_sessions:
        print(f"\nFirst 10 session IDs:")
        for i, session_id in enumerate(v6_unknown_sessions[:10]):
            print(f"{i+1}. {session_id}")
        
        if len(v6_unknown_sessions) > 10:
            print(f"... and {len(v6_unknown_sessions) - 10} more")
    else:
        print("No V6 sessions with unidentified coaching methods found")

if __name__ == "__main__":
    find_v6_unknown_sessions()
