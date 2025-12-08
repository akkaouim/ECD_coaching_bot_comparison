#!/usr/bin/env python3
"""
Verify V6 release date by checking sessions around October 6, 2025 and analyzing
version detection more carefully.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
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

def get_version_from_all_messages(messages: List[Dict]) -> List[int]:
    """Get all version numbers mentioned in messages"""
    versions = []
    if not messages:
        return versions
    
    for message in messages:
        tags = message.get('tags', [])
        for tag in tags:
            if tag.startswith('v') and tag[1:].isdigit():
                versions.append(int(tag[1:]))
    
    return versions

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

def verify_v6_release_date():
    """Verify V6 release date by checking around October 6, 2025."""
    print("="*80)
    print("VERIFYING COACH BOT V6 RELEASE DATE")
    print("="*80)
    
    # Load data
    print("\n1. Loading sessions and messages...")
    sessions, messages_data = load_sessions_and_messages()
    
    # Find V6 sessions
    print("\n2. Identifying V6 sessions...")
    v6_sessions = []
    september_sessions = []
    october_6_sessions = []
    
    # Date ranges
    oct_6_start = datetime(2025, 10, 6, 0, 0, 0, tzinfo=timezone.utc)
    oct_6_end = datetime(2025, 10, 6, 23, 59, 59, tzinfo=timezone.utc)
    sept_start = datetime(2025, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    sept_end = datetime(2025, 9, 30, 23, 59, 59, tzinfo=timezone.utc)
    
    for session in sessions:
        session_id = session.get('id')
        if not session_id:
            continue
        
        messages = messages_data.get(session_id, [])
        
        # Skip test sessions
        participant_id = session.get('participant', {}).get('identifier', '')
        if participant_id.endswith('@dimagi.com'):
            continue
        
        # Check experiment ID
        experiment_id = session.get('experiment', {}).get('id', '')
        if experiment_id != "5d8be75e-03ff-4e3a-ab6a-e0aff6580986":
            continue
        
        # Get version
        version = get_version_from_last_message(messages)
        all_versions = get_version_from_all_messages(messages)
        
        session_date = get_session_date(session, messages)
        if not session_date:
            continue
        
        # Check if it's V6 (version 5+)
        if version >= 5:
            v6_sessions.append({
                'session_id': session_id,
                'date': session_date,
                'version': version,
                'all_versions': all_versions,
                'participant_id': participant_id,
                'created_at': session.get('created_at', ''),
                'updated_at': session.get('updated_at', ''),
                'tags': session.get('tags', []),
                'message_tags': [m.get('tags', []) for m in messages if m.get('tags')]
            })
            
            # Check if in September
            if sept_start <= session_date <= sept_end:
                september_sessions.append({
                    'session_id': session_id,
                    'date': session_date,
                    'version': version,
                    'participant_id': participant_id
                })
            
            # Check if on October 6
            if oct_6_start <= session_date <= oct_6_end:
                october_6_sessions.append({
                    'session_id': session_id,
                    'date': session_date,
                    'version': version,
                    'participant_id': participant_id
                })
    
    # Sort by date
    v6_sessions.sort(key=lambda x: x['date'])
    september_sessions.sort(key=lambda x: x['date'])
    october_6_sessions.sort(key=lambda x: x['date'])
    
    print(f"\n3. Analysis Results:")
    print(f"   Total V6 sessions found: {len(v6_sessions)}")
    print(f"   V6 sessions in September 2025: {len(september_sessions)}")
    print(f"   V6 sessions on October 6, 2025: {len(october_6_sessions)}")
    
    # Analyze September sessions
    if september_sessions:
        print(f"\n   SEPTEMBER 2025 V6 SESSIONS (first 10):")
        print(f"   {'Date':<20} {'Version':<10} {'Session ID':<40} {'Participant ID':<40}")
        print(f"   {'-'*20} {'-'*10} {'-'*40} {'-'*40}")
        for sess in september_sessions[:10]:
            date_str = sess['date'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"   {date_str:<20} v{sess['version']:<9} {sess['session_id']:<40} {sess['participant_id']:<40}")
        
        # Check first September session details
        first_sept = september_sessions[0]
        print(f"\n   First September V6 session details:")
        for sess in v6_sessions:
            if sess['session_id'] == first_sept['session_id']:
                print(f"   Session ID: {sess['session_id']}")
                print(f"   Date: {sess['date']}")
                print(f"   Version: v{sess['version']}")
                print(f"   All versions in messages: {sess['all_versions']}")
                print(f"   Session tags: {sess['tags']}")
                print(f"   Participant: {sess['participant_id']}")
                break
    
    # Analyze October 6 sessions
    if october_6_sessions:
        print(f"\n   OCTOBER 6, 2025 V6 SESSIONS:")
        print(f"   {'Date':<20} {'Version':<10} {'Session ID':<40} {'Participant ID':<40}")
        print(f"   {'-'*20} {'-'*10} {'-'*40} {'-'*40}")
        for sess in october_6_sessions:
            date_str = sess['date'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"   {date_str:<20} v{sess['version']:<9} {sess['session_id']:<40} {sess['participant_id']:<40}")
    
    # Check session volume around October 6
    print(f"\n4. Session Volume Around October 6, 2025:")
    sessions_by_date = defaultdict(int)
    for sess in v6_sessions:
        date_key = sess['date'].date()
        sessions_by_date[date_key] += 1
    
    # Show 5 days before and after October 6
    oct_6_date = datetime(2025, 10, 6).date()
    print(f"   Sessions around October 6, 2025:")
    for i in range(-5, 6):
        check_date = oct_6_date + timedelta(days=i)
        count = sessions_by_date.get(check_date, 0)
        marker = " <-- OCT 6" if i == 0 else ""
        print(f"   {check_date}: {count} session(s){marker}")
    
    # Find earliest V6 session
    if v6_sessions:
        earliest = v6_sessions[0]
        print(f"\n5. Earliest V6 Session:")
        print(f"   Date: {earliest['date'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"   Session ID: {earliest['session_id']}")
        print(f"   Version: v{earliest['version']}")
        print(f"   All versions: {earliest['all_versions']}")
        print(f"   Participant: {earliest['participant_id']}")
        print(f"   Session tags: {earliest['tags']}")
    
    # Check if there's a spike on October 6
    oct_6_count = sessions_by_date.get(oct_6_date, 0)
    if oct_6_count > 0:
        # Compare with previous days
        prev_days = [sessions_by_date.get(oct_6_date + timedelta(days=-i), 0) for i in range(1, 6)]
        avg_prev = sum(prev_days) / len(prev_days) if prev_days else 0
        
        print(f"\n6. October 6 Analysis:")
        print(f"   Sessions on Oct 6: {oct_6_count}")
        print(f"   Average sessions in 5 days before: {avg_prev:.1f}")
        if oct_6_count > avg_prev * 2:
            print(f"   ⚠️  SIGNIFICANT SPIKE on October 6 - possible release date!")
        elif oct_6_count > 0:
            print(f"   Note: Sessions exist on October 6, but not a clear spike")
    
    # Conclusion
    print(f"\n" + "="*80)
    print(f"CONCLUSION")
    print(f"="*80)
    if oct_6_count > 0:
        print(f"October 6, 2025 has {oct_6_count} V6 session(s)")
        if oct_6_count > avg_prev * 2:
            print(f"This appears to be the actual release date based on session volume spike.")
        else:
            print(f"However, V6 sessions exist as early as {earliest['date'].strftime('%B %d, %Y')}")
            print(f"These early sessions may be test/pre-release sessions.")
    else:
        print(f"No V6 sessions found on October 6, 2025")
        print(f"Earliest V6 session: {earliest['date'].strftime('%B %d, %Y')}")

if __name__ == "__main__":
    verify_v6_release_date()

