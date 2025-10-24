#!/usr/bin/env python3
"""
Analyze the ratio of sessions that have the rating question in assistant messages.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

def load_sessions_and_messages() -> Tuple[List[Dict], Dict[str, List[Dict]]]:
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
            
            # Get session ID from filename
            session_id = message_file.stem.replace("messages_", "")
            messages = session_data.get('messages', [])
            messages_data[session_id] = messages
        except Exception as e:
            print(f"Warning: Could not load {message_file.name}: {e}")
            continue
    
    print(f"Loaded {len(sessions)} sessions and {len(messages_data)} message sets")
    return sessions, messages_data

def has_rating_question_in_last_assistant_message(session: Dict, messages: List[Dict]) -> bool:
    """Check if the last assistant message contains the rating question."""
    if not messages:
        return False
    
    # Find the last assistant message
    last_assistant_message = None
    for message in reversed(messages):
        if message.get('role') == 'assistant':
            last_assistant_message = message
            break
    
    if not last_assistant_message:
        return False
    
    content = last_assistant_message.get('content', '').lower()
    rating_question = "how useful did you find this coaching session? please rate it from 1 to 5"
    
    return rating_question in content

def analyze_rating_question_ratio():
    """Analyze the ratio of sessions with rating questions."""
    print("Loading sessions and messages...")
    sessions, messages_data = load_sessions_and_messages()
    
    if not sessions:
        print("No sessions found")
        return
    
    total_sessions = len(sessions)
    sessions_with_rating_question = 0
    sessions_with_messages = 0
    rating_question_session_ids = []
    
    # Filter out Dimagi staff sessions
    dimagi_sessions_excluded = 0
    
    for session in sessions:
        # Check if participant is Dimagi staff
        participant_id = session.get('participant', {}).get('identifier', '')
        if participant_id.endswith('@dimagi.com'):
            dimagi_sessions_excluded += 1
            continue
        
        session_id = session.get('id')
        if not session_id:
            continue
            
        messages = messages_data.get(session_id, [])
        if not messages:
            continue
            
        sessions_with_messages += 1
        
        if has_rating_question_in_last_assistant_message(session, messages):
            sessions_with_rating_question += 1
            rating_question_session_ids.append(session_id)
    
    print(f"\n=== RATING QUESTION ANALYSIS ===")
    print(f"Total sessions: {total_sessions}")
    print(f"Dimagi sessions excluded: {dimagi_sessions_excluded}")
    print(f"Sessions with messages: {sessions_with_messages}")
    print(f"Sessions with rating question: {sessions_with_rating_question}")
    
    if sessions_with_messages > 0:
        ratio = sessions_with_rating_question / sessions_with_messages
        percentage = ratio * 100
        print(f"\nRatio: {sessions_with_rating_question}/{sessions_with_messages} = {ratio:.4f}")
        print(f"Percentage: {percentage:.2f}%")
        
        if rating_question_session_ids:
            print(f"\nSession IDs with rating question:")
            for session_id in rating_question_session_ids:
                print(f"  - {session_id}")
    else:
        print("No sessions with messages found")

if __name__ == "__main__":
    analyze_rating_question_ratio()
