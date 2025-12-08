#!/usr/bin/env python3
"""
Find when Coach bot V6 was released by analyzing the earliest V6 sessions in the data.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone
from collections import defaultdict

def get_version_from_last_message(messages: List[Dict]) -> int:
    """Extract version number from the last message's tags"""
    if not messages:
        return 0
    
    # Get the last message (most recent)
    last_message = messages[-1]
    tags = last_message.get('tags', [])
    
    # Look for version tags (format: v5, v15, etc.)
    for tag in tags:
        if tag.startswith('v') and tag[1:].isdigit():
            return int(tag[1:])
    
    return 0

def matches_v6(session: Dict, messages: List[Dict] = None) -> bool:
    """Check if session is V6"""
    experiment_id = session.get('experiment', {}).get('id', '')
    
    # V6 uses experiment ID: 5d8be75e-03ff-4e3a-ab6a-e0aff6580986
    if experiment_id != "5d8be75e-03ff-4e3a-ab6a-e0aff6580986":
        return False
    
    # V6 is version 5 and above
    version_number = get_version_from_last_message(messages) if messages else 0
    return version_number >= 5

def get_session_date(session: Dict, messages: List[Dict] = None) -> Optional[datetime]:
    """Get the session date - prefer created_at, fall back to updated_at or first message"""
    # Try created_at first
    created_at_str = session.get('created_at', '')
    if created_at_str:
        try:
            dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, AttributeError):
            pass
    
    # Try updated_at
    updated_at_str = session.get('updated_at', '')
    if updated_at_str:
        try:
            dt = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, AttributeError):
            pass
    
    # Try first message timestamp
    if messages and len(messages) > 0:
        first_message = messages[0]
        created_at_str = first_message.get('created_at', '')
        if created_at_str:
            try:
                dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except (ValueError, AttributeError):
                pass
    
    return None

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

def find_v6_release_date():
    """Find the earliest V6 session to determine release date."""
    print("="*80)
    print("FINDING COACH BOT V6 RELEASE DATE")
    print("="*80)
    
    # Load data
    print("\n1. Loading sessions and messages...")
    sessions, messages_data = load_sessions_and_messages()
    
    # Find V6 sessions
    print("\n2. Identifying V6 sessions...")
    v6_sessions = []
    
    for session in sessions:
        session_id = session.get('id')
        if not session_id:
            continue
        
        messages = messages_data.get(session_id, [])
        
        # Skip test sessions
        participant_id = session.get('participant', {}).get('identifier', '')
        if participant_id.endswith('@dimagi.com'):
            continue
        
        # Check if it's V6
        if matches_v6(session, messages):
            session_date = get_session_date(session, messages)
            version = get_version_from_last_message(messages)
            
            if session_date:
                v6_sessions.append({
                    'session_id': session_id,
                    'date': session_date,
                    'version': version,
                    'participant_id': participant_id,
                    'created_at': session.get('created_at', ''),
                    'updated_at': session.get('updated_at', '')
                })
    
    if not v6_sessions:
        print("\nNo V6 sessions found in the data.")
        return
    
    # Sort by date
    v6_sessions.sort(key=lambda x: x['date'])
    
    # Find earliest session
    earliest_session = v6_sessions[0]
    earliest_date = earliest_session['date']
    
    print(f"\n3. Analysis Results:")
    print(f"   Total V6 sessions found: {len(v6_sessions)}")
    print(f"\n   EARLIEST V6 SESSION:")
    print(f"   Date: {earliest_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"   Session ID: {earliest_session['session_id']}")
    print(f"   Version: v{earliest_session['version']}")
    print(f"   Participant ID: {earliest_session['participant_id']}")
    print(f"   Created at: {earliest_session['created_at']}")
    print(f"   Updated at: {earliest_session['updated_at']}")
    
    # Show first 10 sessions
    print(f"\n   FIRST 10 V6 SESSIONS (chronologically):")
    print(f"   {'Date':<20} {'Version':<10} {'Session ID':<40} {'Participant ID':<40}")
    print(f"   {'-'*20} {'-'*10} {'-'*40} {'-'*40}")
    for i, sess in enumerate(v6_sessions[:10], 1):
        date_str = sess['date'].strftime('%Y-%m-%d %H:%M:%S')
        print(f"   {date_str:<20} v{sess['version']:<9} {sess['session_id']:<40} {sess['participant_id']:<40}")
    
    # Analyze by date
    print(f"\n4. V6 Sessions by Date:")
    sessions_by_date = defaultdict(list)
    for sess in v6_sessions:
        date_key = sess['date'].date()
        sessions_by_date[date_key].append(sess)
    
    sorted_dates = sorted(sessions_by_date.keys())
    print(f"   First date with V6 sessions: {sorted_dates[0]}")
    print(f"   Number of sessions on first day: {len(sessions_by_date[sorted_dates[0]])}")
    
    print(f"\n   First 5 days of V6:")
    for date in sorted_dates[:5]:
        count = len(sessions_by_date[date])
        print(f"   {date}: {count} session(s)")
    
    # Version distribution
    print(f"\n5. Version Distribution (first 100 sessions):")
    version_counts = defaultdict(int)
    for sess in v6_sessions[:100]:
        version_counts[sess['version']] += 1
    
    for version in sorted(version_counts.keys()):
        print(f"   v{version}: {version_counts[version]} sessions")
    
    # Conclusion
    print(f"\n" + "="*80)
    print(f"CONCLUSION")
    print(f"="*80)
    print(f"Coach bot V6 was released on: {earliest_date.strftime('%B %d, %Y')}")
    print(f"First session time: {earliest_date.strftime('%H:%M:%S UTC')}")
    print(f"First session date: {earliest_date.strftime('%Y-%m-%d')}")
    print(f"\nNote: This is based on the earliest V6 session found in the data.")
    print(f"      The actual release may have been slightly earlier if there were")
    print(f"      no sessions immediately after release.")

if __name__ == "__main__":
    find_v6_release_date()

