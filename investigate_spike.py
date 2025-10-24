#!/usr/bin/env python3
"""
Investigate the spike in Visit check in sessions at session number 10.
"""

import json
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

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

def is_split_session(session: Dict, messages: List[Dict] = None) -> bool:
    """Check if session is a split session - defined as session with no participant messages"""
    if messages is None:
        return False
    
    # Check if there are any user messages
    for message in messages:
        if message.get('role') == 'user':
            return False  # Has user messages, not a split session
    
    return True  # No user messages found, this is a split session

def is_test_session(session: Dict) -> bool:
    """Check if session is a test session - defined by participant ID being an email address like *@dimagi.com"""
    participant_id = session.get('participant', {}).get('identifier', '')
    return participant_id.endswith('@dimagi.com')

def should_exclude_session(session: Dict, messages: List[Dict] = None) -> bool:
    """Check if session should be excluded (split or test session)"""
    return is_split_session(session, messages) or is_test_session(session)

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

def get_session_number_for_participant(session: Dict, all_sessions: List[Dict]) -> int:
    """Get the session number for a participant based on chronological order"""
    participant_id = session.get('participant', {}).get('identifier', '')
    session_created = session.get('created_at', '')
    
    if not participant_id or not session_created:
        return 1
    
    # Get all sessions for this participant, sorted by creation time
    participant_sessions = []
    for s in all_sessions:
        if s.get('participant', {}).get('identifier', '') == participant_id:
            participant_sessions.append(s)
    
    # Sort by created_at to get chronological order
    participant_sessions.sort(key=lambda x: x.get('created_at', ''))
    
    # Find the position of current session
    for i, s in enumerate(participant_sessions):
        if s.get('id') == session.get('id'):
            return i + 1  # Session number is 1-based
    
    return 1  # Default to 1 if not found (shouldn't happen)

def investigate_visit_checkin_spike():
    """Investigate the spike in Visit check in sessions at session number 10"""
    print("Loading sessions and messages...")
    sessions, messages_data = load_sessions_and_messages()
    
    if not sessions:
        print("No sessions found")
        return
    
    # Filter out split and test sessions
    valid_sessions = []
    for session in sessions:
        session_id = session.get('id')
        messages = messages_data.get(session_id, [])
        if not should_exclude_session(session, messages):
            valid_sessions.append(session)
    
    print(f"Valid sessions (after filtering): {len(valid_sessions)}")
    
    # Group sessions by participant
    participant_sessions = defaultdict(list)
    for session in valid_sessions:
        participant_id = session.get('participant', {}).get('identifier', '')
        if participant_id:
            participant_sessions[participant_id].append(session)
    
    # Sort sessions by creation time for each participant
    for participant_id in participant_sessions:
        participant_sessions[participant_id].sort(key=lambda x: x.get('created_at', ''))
    
    # Find Visit check in sessions at session number 10
    visit_checkin_session_10 = []
    
    for participant_id, participant_session_list in participant_sessions.items():
        for session_index, session in enumerate(participant_session_list):
            session_number = session_index + 1
            if session_number == 10:  # Focus on session 10
                session_id = session.get('id')
                session_messages = messages_data.get(session_id, [])
                
                # Detect coaching method
                detected_method = detect_coaching_method(session, session_messages)
                
                if detected_method == 'Visit check in':
                    # Calculate user words for this session
                    user_words = 0
                    for message in session_messages:
                        if message.get('role') == 'user':
                            content = message.get('content', '')
                            if content:
                                user_words += len(content.split())
                    
                    visit_checkin_session_10.append({
                        'session_id': session_id,
                        'participant_id': participant_id,
                        'user_words': user_words,
                        'created_at': session.get('created_at', ''),
                        'session': session,
                        'messages': session_messages
                    })
    
    print(f"\n=== VISIT CHECK IN SESSIONS AT SESSION NUMBER 10 ===")
    print(f"Found {len(visit_checkin_session_10)} Visit check in sessions at session 10")
    
    if visit_checkin_session_10:
        # Sort by user words to find the highest
        visit_checkin_session_10.sort(key=lambda x: x['user_words'], reverse=True)
        
        print(f"\nTop 5 sessions by word count:")
        for i, session_data in enumerate(visit_checkin_session_10[:5]):
            print(f"{i+1}. Session {session_data['session_id']}")
            print(f"   Participant: {session_data['participant_id']}")
            print(f"   User words: {session_data['user_words']}")
            print(f"   Created: {session_data['created_at']}")
            print()
        
        # Analyze the highest word count session
        top_session = visit_checkin_session_10[0]
        print(f"=== ANALYSIS OF HIGHEST WORD COUNT SESSION ===")
        print(f"Session ID: {top_session['session_id']}")
        print(f"Participant: {top_session['participant_id']}")
        print(f"User words: {top_session['user_words']}")
        print(f"Created: {top_session['created_at']}")
        
        # Show some message content
        print(f"\nFirst few user messages:")
        user_message_count = 0
        for message in top_session['messages']:
            if message.get('role') == 'user':
                user_message_count += 1
                content = message.get('content', '')
                if content:
                    print(f"Message {user_message_count}: {content[:200]}{'...' if len(content) > 200 else ''}")
                    if user_message_count >= 3:  # Show first 3 user messages
                        break
        
        print(f"\nTotal user messages in session: {user_message_count}")
        
        # Check for any special tags or characteristics
        session_tags = top_session['session'].get('tags', [])
        print(f"\nSession tags: {session_tags}")
        
        # Check message tags
        message_tags = []
        for message in top_session['messages']:
            message_tags.extend(message.get('tags', []))
        print(f"Message tags: {list(set(message_tags))}")

if __name__ == "__main__":
    investigate_visit_checkin_spike()
