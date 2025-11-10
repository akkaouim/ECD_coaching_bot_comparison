#!/usr/bin/env python3
"""
Analyze participants with high refrigerator example rates but low GS scores.
Identify where they're failing and extract session IDs.
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

def load_gs_scores(csv_path: str) -> Dict[str, int]:
    """Load GS scores from CSV file."""
    scores = {}
    with open(csv_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
        reader = csv.DictReader(f)
        print(f"CSV columns: {reader.fieldnames}")
        for i, row in enumerate(reader):
            # Handle BOM in column name - try both with and without BOM
            participant_id = (row.get('participant ID', '') or 
                             row.get('\ufeffparticipant ID', '') or
                             row.get('participant_id', '') or 
                             row.get('Participant ID', '') or
                             row.get('Participant_ID', '')).strip()
            score_str = (row.get('Score', '') or 
                        row.get('score', '') or
                        row.get('GS Score', '') or
                        row.get('gs_score', '')).strip()
            
            if i < 5:  # Debug first few rows
                print(f"Row {i}: participant_id='{participant_id}', score_str='{score_str}'")
            
            if participant_id and score_str:
                try:
                    score = int(score_str)
                    scores[participant_id] = score
                except ValueError:
                    if i < 5:
                        print(f"  Could not parse score: '{score_str}'")
                    continue
    print(f"Loaded {len(scores)} valid scores")
    return scores

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

def is_refrigerator_example(session: Dict, messages: List[Dict] = None) -> bool:
    """Check if session is marked as a refrigerator example."""
    # Check session tags
    tags = session.get('tags', [])
    if 'refrigerator_example' in tags:
        return True
    
    # Check message tags
    if messages:
        for message in messages:
            msg_tags = message.get('tags', [])
            if 'refrigerator_example' in msg_tags:
                return True
    
    return False

def is_split_session(session: Dict, messages: List[Dict] = None) -> bool:
    """Check if session has less than 3 participant messages."""
    if not messages:
        return True
    
    user_message_count = sum(1 for msg in messages if msg.get('role') == 'user')
    return user_message_count < 3

def calculate_participant_refrigerator_rates(sessions: List[Dict], messages_data: Dict[str, List[Dict]], include_split_sessions: bool = False) -> Dict[str, Dict]:
    """Calculate refrigerator example rates per participant."""
    participant_stats = defaultdict(lambda: {
        'total_sessions': 0,
        'refrigerator_sessions': 0,
        'non_refrigerator_sessions': 0,
        'split_sessions': 0,
        'refrigerator_split_sessions': 0,
        'session_ids': [],
        'refrigerator_session_ids': [],
        'non_refrigerator_session_ids': [],
        'split_session_ids': []
    })
    
    for session in sessions:
        participant_id = session.get('participant', {}).get('identifier', '')
        if not participant_id or participant_id.endswith('@dimagi.com'):
            continue
        
        session_id = session.get('id', '')
        if not session_id:
            continue
        
        messages = messages_data.get(session_id, [])
        is_split = is_split_session(session, messages)
        
        # Track split sessions separately
        if is_split:
            participant_stats[participant_id]['split_sessions'] += 1
            participant_stats[participant_id]['split_session_ids'].append(session_id)
            if is_refrigerator_example(session, messages):
                participant_stats[participant_id]['refrigerator_split_sessions'] += 1
        
        # Only count non-split sessions in main stats (unless include_split_sessions is True)
        if is_split and not include_split_sessions:
            continue
        
        participant_stats[participant_id]['total_sessions'] += 1
        participant_stats[participant_id]['session_ids'].append(session_id)
        
        if is_refrigerator_example(session, messages):
            participant_stats[participant_id]['refrigerator_sessions'] += 1
            participant_stats[participant_id]['refrigerator_session_ids'].append(session_id)
        else:
            participant_stats[participant_id]['non_refrigerator_sessions'] += 1
            participant_stats[participant_id]['non_refrigerator_session_ids'].append(session_id)
    
    # Calculate rates
    for participant_id, stats in participant_stats.items():
        total = stats['total_sessions']
        if total > 0:
            stats['refrigerator_rate'] = (stats['refrigerator_sessions'] / total) * 100
        else:
            stats['refrigerator_rate'] = 0.0
        
        # Also calculate rate including split sessions
        total_with_split = total + stats['split_sessions']
        if total_with_split > 0:
            stats['refrigerator_rate_with_split'] = ((stats['refrigerator_sessions'] + stats['refrigerator_split_sessions']) / total_with_split) * 100
        else:
            stats['refrigerator_rate_with_split'] = 0.0
    
    return dict(participant_stats)

def find_high_refrigerator_low_gs_participants(
    participant_stats: Dict[str, Dict],
    gs_scores: Dict[str, int],
    min_refrigerator_rate: float = 30.0,
    max_gs_score: int = 80
) -> List[Tuple[str, Dict, int]]:
    """Find participants with high refrigerator rates but low GS scores."""
    results = []
    
    for participant_id, stats in participant_stats.items():
        gs_score = gs_scores.get(participant_id)
        if gs_score is None:
            continue
        
        refrigerator_rate = stats.get('refrigerator_rate', 0.0)
        
        if refrigerator_rate >= min_refrigerator_rate and gs_score <= max_gs_score:
            results.append((participant_id, stats, gs_score))
    
    # Sort by refrigerator rate (descending) then by GS score (ascending)
    results.sort(key=lambda x: (-x[1]['refrigerator_rate'], x[2]))
    
    return results

def main():
    """Main analysis function."""
    print("=" * 80)
    print("Analyzing participants with high refrigerator rates but low GS scores")
    print("=" * 80)
    
    # Load GS scores
    csv_path = "/Users/akkaouim/Downloads/GS scores.csv"
    print(f"\nLoading GS scores from {csv_path}...")
    gs_scores = load_gs_scores(csv_path)
    print(f"Loaded GS scores for {len(gs_scores)} participants")
    
    # Load sessions and messages
    print("\nLoading sessions and messages...")
    sessions, messages_data = load_sessions_and_messages()
    
    # Calculate participant refrigerator rates
    print("\nCalculating refrigerator example rates per participant...")
    participant_stats = calculate_participant_refrigerator_rates(sessions, messages_data, include_split_sessions=False)
    print(f"Analyzed {len(participant_stats)} participants")
    
    # Check for participants with GS scores and their refrigerator sessions (including split)
    print("\nChecking participants with GS scores for refrigerator sessions (including split)...")
    gs_participant_ids_lower = {pid.lower() for pid in gs_scores.keys()}
    for participant_id, stats in participant_stats.items():
        if participant_id.lower() in gs_participant_ids_lower:
            total_ref = stats['refrigerator_sessions'] + stats['refrigerator_split_sessions']
            if total_ref > 0:
                print(f"  {participant_id}: {total_ref} refrigerator sessions ({stats['refrigerator_sessions']} non-split, {stats['refrigerator_split_sessions']} split)")
                print(f"    Total sessions: {stats['total_sessions']} non-split, {stats['split_sessions']} split")
                print(f"    Refrigerator rate (non-split): {stats['refrigerator_rate']:.1f}%")
                print(f"    Refrigerator rate (with split): {stats['refrigerator_rate_with_split']:.1f}%")
    
    # Show distribution of participants with GS scores
    print("\nAnalyzing participants with GS scores...")
    participants_with_gs = []
    
    # Try case-insensitive matching
    gs_scores_lower = {k.lower(): v for k, v in gs_scores.items()}
    participant_stats_lower = {k.lower(): (k, v) for k, v in participant_stats.items()}
    
    for participant_id, stats in participant_stats.items():
        # Try exact match first
        gs_score = gs_scores.get(participant_id)
        if gs_score is None:
            # Try case-insensitive match
            gs_score = gs_scores_lower.get(participant_id.lower())
        
        if gs_score is not None:
            participants_with_gs.append((participant_id, stats, gs_score))
    
    print(f"Found {len(participants_with_gs)} participants with both GS scores and session data")
    
    # Debug: show sample participant IDs
    if len(participants_with_gs) == 0:
        print("\nDebugging participant ID matching...")
        print(f"Sample participant IDs from sessions (first 10):")
        for i, (pid, _, _) in enumerate(list(participant_stats.items())[:10]):
            print(f"  {i+1}. '{pid}'")
        print(f"\nSample participant IDs from CSV (first 10):")
        for i, (pid, score) in enumerate(list(gs_scores.items())[:10]):
            print(f"  {i+1}. '{pid}' (GS={score})")
        
        # Check for partial matches
        print("\nChecking for partial matches...")
        session_pids_lower = {pid.lower() for pid in participant_stats.keys()}
        csv_pids_lower = {pid.lower() for pid in gs_scores.keys()}
        matches = session_pids_lower.intersection(csv_pids_lower)
        print(f"Found {len(matches)} case-insensitive matches")
        if matches:
            print("Sample matches:")
            for match in list(matches)[:5]:
                print(f"  '{match}'")
    
    if participants_with_gs:
        # Show statistics
        print("\nStatistics for participants with GS scores:")
        print(f"  Average GS Score: {sum(gs for _, _, gs in participants_with_gs) / len(participants_with_gs):.1f}")
        print(f"  Min GS Score: {min(gs for _, _, gs in participants_with_gs)}")
        print(f"  Max GS Score: {max(gs for _, _, gs in participants_with_gs)}")
        
        avg_ref_rate = sum(stats['refrigerator_rate'] for _, stats, _ in participants_with_gs) / len(participants_with_gs)
        print(f"  Average Refrigerator Rate: {avg_ref_rate:.1f}%")
        print(f"  Max Refrigerator Rate: {max(stats['refrigerator_rate'] for _, stats, _ in participants_with_gs):.1f}%")
        
        # Show participants sorted by refrigerator rate
        participants_with_gs_sorted = sorted(participants_with_gs, key=lambda x: -x[1]['refrigerator_rate'])
        print(f"\nTop 10 participants by refrigerator rate:")
        for i, (pid, stats, gs) in enumerate(participants_with_gs_sorted[:10]):
            print(f"  {i+1}. {pid}: {stats['refrigerator_rate']:.1f}% refrigerator rate, GS={gs}")
    
    # Try different thresholds
    print("\n" + "=" * 80)
    print("Trying different thresholds...")
    
    thresholds = [
        (30.0, 80),  # Original
        (25.0, 85),  # Slightly relaxed
        (20.0, 80),  # Lower refrigerator rate
        (30.0, 90),  # Higher GS score
        (15.0, 85),  # More relaxed
    ]
    
    for min_rate, max_gs in thresholds:
        high_ref_low_gs = find_high_refrigerator_low_gs_participants(
            participant_stats, 
            gs_scores,
            min_refrigerator_rate=min_rate,
            max_gs_score=max_gs
        )
        print(f"\nThreshold: >= {min_rate}% refrigerator rate, <= {max_gs} GS score")
        print(f"  Found {len(high_ref_low_gs)} participants")
        if high_ref_low_gs:
            for pid, stats, gs in high_ref_low_gs[:5]:
                print(f"    - {pid}: {stats['refrigerator_rate']:.1f}% refrigerator, GS={gs}")
    
    # Alternative approach: Find participants with high refrigerator rates first, then check GS scores
    print("\n" + "=" * 80)
    print("Alternative approach: Finding participants with high refrigerator rates, then checking GS scores...")
    
    # Find all participants with high refrigerator rates (using rate with split sessions)
    high_ref_participants = []
    for participant_id, stats in participant_stats.items():
        # Use rate including split sessions for more comprehensive view
        ref_rate = stats.get('refrigerator_rate_with_split', stats.get('refrigerator_rate', 0.0))
        if ref_rate >= 15.0:  # At least 15% refrigerator rate
            gs_score = gs_scores.get(participant_id)
            if gs_score is None:
                # Try case-insensitive
                gs_score = gs_scores_lower.get(participant_id.lower())
            
            high_ref_participants.append((participant_id, stats, gs_score, ref_rate))
    
    # Sort by refrigerator rate
    high_ref_participants.sort(key=lambda x: -x[3])
    
    print(f"\nFound {len(high_ref_participants)} participants with >=15% refrigerator rate")
    print(f"  {sum(1 for _, _, gs, _ in high_ref_participants if gs is not None)} have GS scores")
    print(f"  {sum(1 for _, _, gs, _ in high_ref_participants if gs is not None and gs <= 85)} have GS scores <= 85")
    
    # Filter to those with GS scores and low scores
    high_ref_low_gs = [(pid, stats, gs, rate) for pid, stats, gs, rate in high_ref_participants 
                       if gs is not None and gs <= 85]
    
    print(f"\nFound {len(high_ref_low_gs)} participants with high refrigerator rates (>=15%) and low GS scores (<=85):")
    print("=" * 80)
    
    if not high_ref_low_gs:
        print("No participants found with high refrigerator rates and low GS scores.")
        print("\n" + "=" * 80)
        print("ANALYSIS: Participants with LOW GS scores (<=85) and their sessions")
        print("=" * 80)
        
        # Focus on participants with low GS scores
        low_gs_participants = [(pid, stats, gs) for pid, stats, gs in participants_with_gs if gs <= 85]
        low_gs_participants.sort(key=lambda x: x[2])  # Sort by GS score (ascending)
        
        print(f"\nFound {len(low_gs_participants)} participants with GS scores <= 85:")
        print("These participants have LOW refrigerator rates, so we'll extract ALL their session IDs")
        print("to analyze what types of sessions they're having (non-refrigerator sessions).\n")
        
        # Update high_ref_low_gs_formatted to include low GS participants for analysis
        high_ref_low_gs_formatted = low_gs_participants
        
        if not low_gs_participants:
            print("No participants with low GS scores found.")
            return
    else:
        # Convert to format expected by display code
        high_ref_low_gs_formatted = [(pid, stats, gs) for pid, stats, gs, _ in high_ref_low_gs]
    
    # Display results
    for participant_id, stats, gs_score in high_ref_low_gs_formatted:
        print(f"\nParticipant ID: {participant_id}")
        print(f"  GS Score: {gs_score}")
        print(f"  Total Sessions: {stats['total_sessions']}")
        print(f"  Refrigerator Sessions: {stats['refrigerator_sessions']} ({stats['refrigerator_rate']:.1f}%)")
        print(f"  Non-Refrigerator Sessions: {stats['non_refrigerator_sessions']}")
        print(f"  Refrigerator Session IDs ({len(stats['refrigerator_session_ids'])}):")
        for sid in stats['refrigerator_session_ids']:
            print(f"    - {sid}")
        print(f"  Non-Refrigerator Session IDs ({len(stats['non_refrigerator_session_ids'])}):")
        for sid in stats['non_refrigerator_session_ids']:
            print(f"    - {sid}")
    
    # Save results to file
    output_file = Path("output/high_refrigerator_low_gs_analysis.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    results_data = {
        'analysis_date': str(datetime.now()),
        'criteria': {
            'min_refrigerator_rate': 30.0,
            'max_gs_score': 80
        },
        'participants': []
    }
    
    for participant_id, stats, gs_score in high_ref_low_gs_formatted:
        results_data['participants'].append({
            'participant_id': participant_id,
            'gs_score': gs_score,
            'total_sessions': stats['total_sessions'],
            'refrigerator_sessions': stats['refrigerator_sessions'],
            'refrigerator_rate': stats['refrigerator_rate'],
            'non_refrigerator_sessions': stats['non_refrigerator_sessions'],
            'refrigerator_session_ids': stats['refrigerator_session_ids'],
            'non_refrigerator_session_ids': stats['non_refrigerator_session_ids'],
            'all_session_ids': stats['session_ids']
        })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"\n\nResults saved to: {output_file}")
    
    # Create a summary CSV
    csv_output = Path("output/high_refrigerator_low_gs_summary.csv")
    with open(csv_output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Participant ID',
            'GS Score',
            'Total Sessions',
            'Refrigerator Sessions',
            'Refrigerator Rate (%)',
            'Non-Refrigerator Sessions',
            'Refrigerator Session IDs',
            'Non-Refrigerator Session IDs',
            'All Session IDs'
        ])
        
        for participant_id, stats, gs_score in high_ref_low_gs_formatted:
            writer.writerow([
                participant_id,
                gs_score,
                stats['total_sessions'],
                stats['refrigerator_sessions'],
                f"{stats['refrigerator_rate']:.1f}",
                stats['non_refrigerator_sessions'],
                '; '.join(stats['refrigerator_session_ids']),
                '; '.join(stats['non_refrigerator_session_ids']),
                '; '.join(stats['session_ids'])
            ])
    
    print(f"Summary CSV saved to: {csv_output}")

if __name__ == "__main__":
    from datetime import datetime
    main()

