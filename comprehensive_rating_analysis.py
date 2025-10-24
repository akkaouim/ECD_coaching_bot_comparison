#!/usr/bin/env python3
"""
Comprehensive analysis to find ALL rating patterns and extract ratings from 100% of sessions.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

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
            
            session_id = message_file.stem.replace("messages_", "")
            messages = session_data.get('messages', [])
            messages_data[session_id] = messages
        except Exception as e:
            print(f"Warning: Could not load {message_file.name}: {e}")
            continue
    
    print(f"Loaded {len(sessions)} sessions and {len(messages_data)} message sets")
    return sessions, messages_data

def find_rating_question_patterns(messages: List[Dict]) -> List[str]:
    """Find all possible rating question patterns in assistant messages."""
    patterns = []
    
    for message in messages:
        if message.get('role') != 'assistant':
            continue
            
        content = message.get('content', '').lower()
        
        # Look for various rating question patterns
        rating_patterns = [
            r'how useful.*rate.*[1-5]',
            r'rate.*useful.*[1-5]',
            r'rate.*session.*[1-5]',
            r'rate.*coaching.*[1-5]',
            r'rate.*[1-5].*useful',
            r'rate.*[1-5].*session',
            r'rate.*[1-5].*coaching',
            r'useful.*rate.*[1-5]',
            r'session.*rate.*[1-5]',
            r'coaching.*rate.*[1-5]',
            r'number.*[1-5].*rate',
            r'number.*[1-5].*useful',
            r'number.*[1-5].*session',
            r'number.*[1-5].*coaching',
            r'[1-5].*useful',
            r'[1-5].*session',
            r'[1-5].*coaching',
            r'rate.*useful',
            r'rate.*session',
            r'rate.*coaching',
            r'useful.*[1-5]',
            r'session.*[1-5]',
            r'coaching.*[1-5]'
        ]
        
        for pattern in rating_patterns:
            if re.search(pattern, content):
                patterns.append(content[:200] + '...')
                break
    
    return patterns

def extract_rating_from_session(session: Dict, messages: List[Dict]) -> Optional[int]:
    """Extract rating from a session using comprehensive pattern matching."""
    if not messages:
        return None
    
    # Look for rating questions in assistant messages
    rating_question_found = False
    for message in reversed(messages):  # Start from the end
        if message.get('role') == 'assistant':
            content = message.get('content', '').lower()
            
            # Check for rating question patterns
            rating_patterns = [
                r'how useful.*rate.*[1-5]',
                r'rate.*useful.*[1-5]',
                r'rate.*session.*[1-5]',
                r'rate.*coaching.*[1-5]',
                r'number.*[1-5].*rate',
                r'number.*[1-5].*useful',
                r'[1-5].*useful',
                r'[1-5].*session',
                r'[1-5].*coaching'
            ]
            
            for pattern in rating_patterns:
                if re.search(pattern, content):
                    rating_question_found = True
                    break
            
            if rating_question_found:
                break
    
    if not rating_question_found:
        return None
    
    # Look for user rating responses
    for message in reversed(messages):
        if message.get('role') == 'user':
            content = message.get('content', '').strip()
            
            # Single digit rating
            if re.match(r'^\s*[1-5]\s*$', content):
                return int(content.strip())
            
            # Written number rating
            written_numbers = {
                'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5
            }
            content_lower = content.lower()
            if content_lower in written_numbers:
                return written_numbers[content_lower]
            
            # Rating with context (e.g., "5= extremely useful")
            rating_match = re.search(r'\b([1-5])\b', content)
            if rating_match and len(content) < 100:  # Short responses more likely to be ratings
                return int(rating_match.group(1))
    
    return None

def comprehensive_rating_analysis():
    """Perform comprehensive rating analysis."""
    print("Loading sessions and messages...")
    sessions, messages_data = load_sessions_and_messages()
    
    if not sessions:
        print("No sessions found")
        return
    
    total_sessions = len(sessions)
    sessions_with_rating_question = 0
    sessions_with_messages = 0
    sessions_with_ratings = 0
    rating_question_session_ids = []
    rating_session_ids = []
    
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
        
        # Check for rating questions
        has_rating_question = False
        for message in reversed(messages):
            if message.get('role') == 'assistant':
                content = message.get('content', '').lower()
                if any(pattern in content for pattern in [
                    'rate', 'rating', 'useful', 'session', 'coaching'
                ]) and any(num in content for num in ['1', '2', '3', '4', '5']):
                    has_rating_question = True
                    break
        
        if has_rating_question:
            sessions_with_rating_question += 1
            rating_question_session_ids.append(session_id)
        
        # Extract actual rating
        rating = extract_rating_from_session(session, messages)
        if rating is not None:
            sessions_with_ratings += 1
            rating_session_ids.append((session_id, rating))
    
    print(f"\n=== COMPREHENSIVE RATING ANALYSIS ===")
    print(f"Total sessions: {total_sessions}")
    print(f"Dimagi sessions excluded: {dimagi_sessions_excluded}")
    print(f"Sessions with messages: {sessions_with_messages}")
    print(f"Sessions with rating questions: {sessions_with_rating_question}")
    print(f"Sessions with actual ratings: {sessions_with_ratings}")
    
    if sessions_with_messages > 0:
        question_ratio = sessions_with_rating_question / sessions_with_messages
        rating_ratio = sessions_with_ratings / sessions_with_messages
        print(f"\nRating question ratio: {sessions_with_rating_question}/{sessions_with_messages} = {question_ratio:.4f} ({question_ratio*100:.2f}%)")
        print(f"Rating extraction ratio: {sessions_with_ratings}/{sessions_with_messages} = {rating_ratio:.4f} ({rating_ratio*100:.2f}%)")
        
        if rating_session_ids:
            print(f"\nSessions with ratings:")
            for session_id, rating in rating_session_ids[:10]:  # Show first 10
                print(f"  - {session_id}: {rating}")
            if len(rating_session_ids) > 10:
                print(f"  ... and {len(rating_session_ids) - 10} more")
    
    return rating_session_ids

if __name__ == "__main__":
    comprehensive_rating_analysis()
