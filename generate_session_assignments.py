#!/usr/bin/env python3
"""
Generate session assignments for 4 team members to tag 60 V6 sessions.
Each member gets 15 sessions, with equal representation of coaching methods
and unique participant IDs.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
from collections import defaultdict
import random

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
            if message.get('role') == 'assistant':
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

def get_session_end_date(session: Dict, messages: List[Dict]) -> datetime:
    """Get the session end date - use updated_at or last message timestamp"""
    from datetime import timezone
    
    # Try updated_at first
    updated_at_str = session.get('updated_at', '')
    if updated_at_str:
        try:
            dt = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
            # Make timezone-aware if not already
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, AttributeError):
            pass
    
    # Fall back to last message timestamp
    if messages:
        last_message = messages[-1]
        created_at_str = last_message.get('created_at', '')
        if created_at_str:
            try:
                dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                # Make timezone-aware if not already
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except (ValueError, AttributeError):
                pass
    
    # Fall back to session created_at
    created_at_str = session.get('created_at', '')
    if created_at_str:
        try:
            dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            # Make timezone-aware if not already
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, AttributeError):
            pass
    
    return None

def count_participant_messages(messages: List[Dict]) -> int:
    """Count the number of participant messages in a session"""
    if not messages:
        return 0
    
    count = 0
    for message in messages:
        if message.get('role') == 'user':
            count += 1
    
    return count

def count_session_tags(session: Dict, messages: List[Dict] = None) -> int:
    """Count the total number of tags in a session (session tags only)"""
    session_tags = session.get('tags', [])
    return len(session_tags)

def generate_session_assignments():
    """Generate session assignments for 4 team members."""
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
    
    # Date range: Oct 20, 2025 to Nov 7, 2025
    from datetime import timezone
    start_date = datetime(2025, 10, 20, tzinfo=timezone.utc)
    end_date = datetime(2025, 11, 7, 23, 59, 59, tzinfo=timezone.utc)
    
    # Filter sessions
    eligible_sessions = []
    
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
        
        # Check date range (session ended between Oct 20 and Nov 7, 2025)
        session_end = get_session_end_date(session, messages)
        if not session_end:
            continue
        
        if session_end < start_date or session_end > end_date:
            continue
        
        # Check at least 3 participant messages
        participant_message_count = count_participant_messages(messages)
        if participant_message_count < 3:
            continue
        
        # Check session has no more than 2 tags
        tag_count = count_session_tags(session, messages)
        if tag_count > 2:
            continue
        
        # Detect coaching method
        method = detect_coaching_method(session, messages)
        if method == 'Unknown':
            continue
        
        eligible_sessions.append({
            'session_id': session_id,
            'participant_id': participant_id,
            'method': method,
            'participant_message_count': participant_message_count,
            'session_end': session_end
        })
    
    print(f"\nFound {len(eligible_sessions)} eligible sessions")
    
    # Group by method
    sessions_by_method = defaultdict(list)
    for session in eligible_sessions:
        sessions_by_method[session['method']].append(session)
    
    print(f"\nSessions by coaching method:")
    for method, method_sessions in sessions_by_method.items():
        print(f"  {method}: {len(method_sessions)} sessions")
    
    # Ensure we have enough sessions
    if len(eligible_sessions) < 60:
        print(f"\nWarning: Only {len(eligible_sessions)} eligible sessions found, but 60 are needed.")
        print("Proceeding with available sessions...")
    
    # Group by participant to ensure unique participants
    sessions_by_participant = defaultdict(list)
    for session in eligible_sessions:
        sessions_by_participant[session['participant_id']].append(session)
    
    # Strategy: Select sessions ensuring:
    # 1. Each session from different participant
    # 2. Equal representation of coaching methods
    # 3. 15 sessions per team member
    
    # Count methods
    method_counts = {method: len(sessions) for method, sessions in sessions_by_method.items()}
    methods = list(method_counts.keys())
    
    # Calculate how many sessions per method (60 total, 4 members, 15 each)
    # Distribute methods as evenly as possible
    total_needed = 60
    sessions_per_method = total_needed // len(methods)
    remainder = total_needed % len(methods)
    
    method_targets = {}
    for i, method in enumerate(methods):
        method_targets[method] = sessions_per_method + (1 if i < remainder else 0)
    
    print(f"\nTarget distribution per method:")
    for method, target in method_targets.items():
        print(f"  {method}: {target} sessions")
    
    # Select sessions ensuring unique participants
    selected_sessions = []
    used_participants = set()
    
    # For each method, select sessions with unique participants
    for method, target_count in method_targets.items():
        method_sessions = sessions_by_method[method]
        # Shuffle for randomness
        random.shuffle(method_sessions)
        
        selected_for_method = []
        for session in method_sessions:
            if len(selected_for_method) >= target_count:
                break
            
            # Only add if participant not already used
            if session['participant_id'] not in used_participants:
                selected_for_method.append(session)
                used_participants.add(session['participant_id'])
        
        # If we don't have enough unique participants, fill with any available
        if len(selected_for_method) < target_count:
            for session in method_sessions:
                if len(selected_for_method) >= target_count:
                    break
                if session not in selected_for_method:
                    selected_for_method.append(session)
        
        selected_sessions.extend(selected_for_method)
        print(f"\nSelected {len(selected_for_method)} sessions for {method} (target: {target_count})")
    
    # If we still don't have 60, add more sessions (may have duplicate participants)
    if len(selected_sessions) < 60:
        remaining_needed = 60 - len(selected_sessions)
        print(f"\nNeed {remaining_needed} more sessions. Adding from available pool...")
        
        for session in eligible_sessions:
            if len(selected_sessions) >= 60:
                break
            if session not in selected_sessions:
                selected_sessions.append(session)
    
    # Distribute among 4 team members (15 each) with balanced method distribution
    team_members = ['Team Member 1', 'Team Member 2', 'Team Member 3', 'Team Member 4']
    assignments = {member: [] for member in team_members}
    
    # Group selected sessions by method
    selected_by_method = defaultdict(list)
    for session in selected_sessions[:60]:  # Take exactly 60
        selected_by_method[session['method']].append(session)
    
    # Distribute methods evenly across members
    # Each method should have 12 sessions, so 3 per member ideally
    member_idx = 0
    for method, method_sessions in selected_by_method.items():
        # Shuffle for randomness
        random.shuffle(method_sessions)
        # Distribute sessions of this method round-robin
        for session in method_sessions:
            assignments[team_members[member_idx % 4]].append(session)
            member_idx += 1
    
    # Print results
    print(f"\n{'='*80}")
    print("SESSION ASSIGNMENTS FOR 4 TEAM MEMBERS")
    print(f"{'='*80}\n")
    
    # Create table
    print(f"{'Team Member':<20} {'Session ID':<40} {'Method':<25} {'Participant ID':<30}")
    print("-" * 115)
    
    for member, member_sessions in assignments.items():
        print(f"\n{member}:")
        for session in sorted(member_sessions, key=lambda x: x['method']):
            print(f"  {session['session_id']:<40} {session['method']:<25} {session['participant_id']:<30}")
    
    # Summary statistics
    print(f"\n{'='*80}")
    print("SUMMARY STATISTICS")
    print(f"{'='*80}\n")
    
    for member, member_sessions in assignments.items():
        method_counts = defaultdict(int)
        participant_ids = set()
        for session in member_sessions:
            method_counts[session['method']] += 1
            participant_ids.add(session['participant_id'])
        
        print(f"{member}:")
        print(f"  Total sessions: {len(member_sessions)}")
        print(f"  Unique participants: {len(participant_ids)}")
        print(f"  Methods distribution:")
        for method, count in sorted(method_counts.items()):
            print(f"    {method}: {count}")
        print()
    
    # Overall statistics
    all_methods = defaultdict(int)
    all_participants = set()
    for member_sessions in assignments.values():
        for session in member_sessions:
            all_methods[session['method']] += 1
            all_participants.add(session['participant_id'])
    
    print(f"Overall:")
    print(f"  Total sessions assigned: {sum(len(s) for s in assignments.values())}")
    print(f"  Total unique participants: {len(all_participants)}")
    print(f"  Overall methods distribution:")
    for method, count in sorted(all_methods.items()):
        print(f"    {method}: {count}")
    
    # Export to CSV
    csv_path = Path("session_assignments.csv")
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write("Team Member,Session ID,Method,Participant ID,Participant Messages,Session End Date\n")
        for member, member_sessions in assignments.items():
            for session in sorted(member_sessions, key=lambda x: x['method']):
                f.write(f"{member},{session['session_id']},{session['method']},{session['participant_id']},{session['participant_message_count']},{session['session_end'].isoformat()}\n")
    
    print(f"\n{'='*80}")
    print(f"Results exported to: {csv_path}")
    print(f"{'='*80}")

if __name__ == "__main__":
    # Set random seed for reproducibility (change seed for different distributions)
    import time
    random.seed(int(time.time()))
    generate_session_assignments()

