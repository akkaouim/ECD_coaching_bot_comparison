#!/usr/bin/env python3
"""
Select 10 participants from Cohort 8, Sabon Gari LGA for Focus Group Discussion.

Selection criteria:
- Good and bad performers (visit duration/count extremes vs median)
- All have gone through all Coach methods
- Some used AI tool to populate answers
- Some were blocked in loops
- Some have good ECD knowledge (low post test trial number)
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
import statistics

# List of Cohort 8 users from Sabon Gari LGA
SABON_GARI_C8_USER_IDS = {
    '41ca09f534bb72d42230', '8064eda250cb10b5e6d5', '1869e47d21ddd499da19',
    'e583b049c08d350ec8ff', '878d40b3b1e4c72e592d', '57c1eafc54f259741fd6',
    'aa87f3cf117715123f74', '10b284f022e853916844', '6161ca7dd52f0d30f4e4',
    '14f9ed2770785c5033bd', 'a82c8a80785cdbad746d', '98aff0d24d9586357d5f',
    'f34cb66ca0f1c46a4c35', '0cb4346a043632be69b3', '47efef75c548f597d90c',
    '598c2781ddd952473732', '9a8a412e5673d1f0c1ed', '0008d8064749e2465008',
    '5d427e96aefe122f15fd', 'a6607ee2a0b98a148f3a', '2fd49b5273d135b8e1d0',
    '9fb0925cef913a2a1421', '9dbcb45583925fc3c6f5', 'd1088eff5aa5287298f8',
    '35d77e18cb88f968c6de', '210e86b072f7fe0afb17', '6c9e447e6cfb9da3698d',
    '82694a87c2647d2917df', '95bea32e91c1a369d18f', '83a07691869834a47f50',
    '1991acdfc83d63079c1a', '3b27fb0b1143eab23ff4', '556920eddaf33a8f1885',
    '7683ded0c8623c48c4d0', 'f5f7201dc2a6ee3a41fd', '606706c16b9383535303',
    'e7ebafd1ba2c8b3e1e6e', 'd281835087457fac96c9', '268c804063f2424a9929',
    'd4a915f7f2cad13b73b2', 'd656dd9bdbb7b534400e', 'a98a9d69640df97e8343'
}

ALL_COACH_METHODS = {'Scenario', 'Microlearning', 'Microlearning vaccines', 
                     'Motivational interviewing', 'Visit check in'}

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

def detect_ai_tool_usage(messages: List[Dict]) -> bool:
    """Detect if user used AI tool to populate answers.
    More strict detection: requires multiple strong indicators."""
    if not messages:
        return False
    
    user_messages = [m for m in messages if m.get('role') == 'user']
    if len(user_messages) < 3:
        return False
    
    indicators = 0
    
    # Check for very long responses (AI might generate longer text) - STRICT
    long_responses = sum(1 for m in user_messages if len(m.get('content', '')) > 300)
    if long_responses >= 3:  # Need at least 3 very long responses
        indicators += 1
    
    # Check for repetitive patterns - STRICT
    contents = [m.get('content', '').strip() for m in user_messages if len(m.get('content', '').strip()) > 10]
    if len(contents) >= 5:
        # Check if many responses are identical or very similar
        exact_duplicates = len(contents) - len(set(contents))
        if exact_duplicates >= 3:  # At least 3 exact duplicates
            indicators += 1
    
    # Check for AI-related keywords in messages - STRICT
    ai_keywords = ['ai generated', 'artificial intelligence', 'auto-filled', 'auto-populated', 'chatgpt', 'gpt']
    ai_keyword_found = False
    for message in user_messages:
        content = message.get('content', '').lower()
        if any(keyword in content for keyword in ai_keywords):
            ai_keyword_found = True
            break
    if ai_keyword_found:
        indicators += 1
    
    # Check message tags for AI-related tags - STRICT
    ai_tag_found = False
    for message in messages:
        tags = message.get('tags', [])
        for tag in tags:
            tag_lower = tag.lower()
            if 'ai' in tag_lower and ('tool' in tag_lower or 'generated' in tag_lower or 'auto' in tag_lower):
                ai_tag_found = True
                break
        if ai_tag_found:
            break
    if ai_tag_found:
        indicators += 1
    
    # Require at least 2 strong indicators
    return indicators >= 2

def detect_loop_blocking(messages: List[Dict]) -> bool:
    """Detect if user was blocked in a loop during interaction.
    More strict detection: requires clear loop patterns."""
    if not messages:
        return False
    
    assistant_messages = [m for m in messages if m.get('role') == 'assistant']
    user_messages = [m for m in messages if m.get('role') == 'user']
    
    if len(assistant_messages) < 5 or len(user_messages) < 3:
        return False
    
    indicators = 0
    
    # Check for repetitive assistant messages (same content repeated) - STRICT
    assistant_contents = [m.get('content', '').strip() for m in assistant_messages if len(m.get('content', '').strip()) > 30]
    if len(assistant_contents) >= 5:
        # Check if same message appears multiple times
        content_counts = defaultdict(int)
        for content in assistant_contents:
            # Use first 150 chars as key for better matching
            key = content[:150].lower()
            content_counts[key] += 1
        
        # If same message appears 4+ times, likely a loop
        if any(count >= 4 for count in content_counts.values()):
            indicators += 1
    
    # Check for very short user responses pattern - STRICT
    # Need at least 5 very short responses in a row or throughout
    short_responses = sum(1 for m in user_messages if len(m.get('content', '').strip()) <= 3)
    if short_responses >= 5:  # At least 5 very short responses
        indicators += 1
    
    # Check for error messages or "I didn't understand" patterns - STRICT
    error_patterns = ["i didn't understand", "i don't understand", "could you repeat", 
                      "please try again", "i'm sorry, i didn't", "let me try again"]
    error_count = 0
    for message in assistant_messages:
        content = message.get('content', '').lower()
        if any(pattern in content for pattern in error_patterns):
            error_count += 1
    
    if error_count >= 3:  # At least 3 error messages
        indicators += 1
    
    # Check for circular pattern: same question-answer sequence repeating
    if len(assistant_messages) >= 6 and len(user_messages) >= 4:
        # Check if we see a pattern like: A1, U1, A2, U2, A1, U1 (repeating)
        if len(assistant_messages) >= 6:
            # Simple check: see if message pairs repeat
            pairs = []
            min_len = min(len(assistant_messages), len(user_messages))
            for i in range(min_len - 1):
                a_content = assistant_messages[i].get('content', '')[:100]
                u_content = user_messages[i].get('content', '')[:50]
                pairs.append((a_content.lower(), u_content.lower()))
            
            # Check for repeating pairs
            if len(pairs) >= 4:
                for i in range(len(pairs) - 3):
                    pair = pairs[i]
                    if pairs.count(pair) >= 2:  # Same pair appears at least twice
                        indicators += 1
                        break
    
    # Require at least 2 strong indicators
    return indicators >= 2

def calculate_session_duration(session: Dict, messages: List[Dict]) -> Optional[float]:
    """Calculate session duration in minutes."""
    if not messages:
        return None
    
    try:
        first_message = messages[0]
        last_message = messages[-1]
        
        first_time = datetime.fromisoformat(first_message.get('created_at', '').replace('Z', '+00:00'))
        last_time = datetime.fromisoformat(last_message.get('created_at', '').replace('Z', '+00:00'))
        
        duration = (last_time - first_time).total_seconds() / 60  # Convert to minutes
        return duration
    except Exception:
        return None

def load_gs_and_flw_data() -> Tuple[Dict[str, Dict], Dict[str, Dict]]:
    """Load GS scores and FLW activity data."""
    gs_data = {}
    flw_data = {}
    
    # Load GS scores list
    gs_file = Path("../data/GS scores list.csv")
    if gs_file.exists():
        with open(gs_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                participant_id = row.get('Participant ID', '').strip()
                if participant_id:
                    cohort = row.get('Cohort', '').strip()
                    gs_data[participant_id] = {
                        'cohort': cohort,
                        'score': None
                    }
                    score_str = row.get('Score', '').strip()
                    if score_str:
                        try:
                            gs_data[participant_id]['score'] = int(score_str)
                        except ValueError:
                            pass
    
    # Load ECD OCS Connect Data
    ecd_file = Path("../data/ECD OCS Connect Data.csv")
    if ecd_file.exists():
        with open(ecd_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                participant_id = row.get('connect_id', '').strip()
                if participant_id:
                    # Get post_test_tries
                    post_test_tries_str = row.get('post_test_tries', '').strip()
                    post_test_tries = None
                    if post_test_tries_str:
                        try:
                            post_test_tries = float(post_test_tries_str)
                        except ValueError:
                            pass
                    
                    flw_data[participant_id] = {
                        'post_test_tries': post_test_tries
                    }
    
    return gs_data, flw_data

def analyze_participants():
    """Main analysis function."""
    print("="*80)
    print("FOCUS GROUP PARTICIPANT SELECTION - COHORT 8, SABON GARI LGA")
    print("="*80)
    
    # Load data
    print("\n1. Loading data...")
    sessions, messages_data = load_sessions_and_messages()
    gs_data, flw_data = load_gs_and_flw_data()
    
    # Filter sessions for Cohort 8, Sabon Gari users
    print("\n2. Filtering for Cohort 8, Sabon Gari LGA users...")
    user_sessions = defaultdict(list)
    
    for session in sessions:
        participant_id = session.get('participant', {}).get('identifier', '')
        if participant_id in SABON_GARI_C8_USER_IDS:
            session_id = session.get('id')
            messages = messages_data.get(session_id, [])
            
            # Skip split sessions (less than 3 participant messages)
            participant_message_count = sum(1 for m in messages if m.get('role') == 'user')
            if participant_message_count < 3:
                continue
            
            # Skip test sessions
            if participant_id.endswith('@dimagi.com'):
                continue
            
            user_sessions[participant_id].append((session, messages))
    
    print(f"Found {len(user_sessions)} users with valid sessions")
    
    # Analyze each user
    print("\n3. Analyzing users...")
    user_analysis = {}
    
    for participant_id, session_list in user_sessions.items():
        methods_used = set()
        total_visits = len(session_list)
        visit_durations = []
        ai_tool_used = False
        loop_blocked = False
        
        for session, messages in session_list:
            # Detect coaching method
            method = detect_coaching_method(session, messages)
            if method != 'Unknown':
                methods_used.add(method)
            
            # Check for AI tool usage
            if detect_ai_tool_usage(messages):
                ai_tool_used = True
            
            # Check for loop blocking
            if detect_loop_blocking(messages):
                loop_blocked = True
            
            # Calculate session duration
            duration = calculate_session_duration(session, messages)
            if duration is not None:
                visit_durations.append(duration)
        
        # Get post test tries
        post_test_tries = flw_data.get(participant_id, {}).get('post_test_tries')
        
        user_analysis[participant_id] = {
            'methods_used': methods_used,
            'all_methods_covered': methods_used == ALL_COACH_METHODS,
            'total_visits': total_visits,
            'avg_visit_duration': statistics.mean(visit_durations) if visit_durations else None,
            'median_visit_duration': statistics.median(visit_durations) if visit_durations else None,
            'ai_tool_used': ai_tool_used,
            'loop_blocked': loop_blocked,
            'post_test_tries': post_test_tries
        }
    
    # Calculate medians for comparison
    visit_counts = [ua['total_visits'] for ua in user_analysis.values()]
    visit_durations = [ua['avg_visit_duration'] for ua in user_analysis.values() if ua['avg_visit_duration'] is not None]
    
    median_visit_count = statistics.median(visit_counts) if visit_counts else 0
    median_visit_duration = statistics.median(visit_durations) if visit_durations else 0
    
    print(f"\nMedian visit count: {median_visit_count:.1f}")
    print(f"Median visit duration: {median_visit_duration:.1f} minutes")
    
    # Categorize users
    print("\n4. Categorizing users...")
    for participant_id, analysis in user_analysis.items():
        # Performance extremes
        visit_count_extreme = False
        visit_duration_extreme = False
        performance_type = None  # 'good_performer' or 'bad_performer'
        
        if analysis['total_visits']:
            if analysis['total_visits'] >= median_visit_count * 1.5:
                visit_count_extreme = True
                performance_type = 'good_performer'  # High visit count = good
            elif analysis['total_visits'] <= median_visit_count * 0.5:
                visit_count_extreme = True
                performance_type = 'bad_performer'  # Low visit count = bad
        
        if analysis['avg_visit_duration']:
            if analysis['avg_visit_duration'] >= median_visit_duration * 1.5:
                visit_duration_extreme = True
                if performance_type is None:
                    performance_type = 'bad_performer'  # Very long sessions = bad
            elif analysis['avg_visit_duration'] <= median_visit_duration * 0.5:
                visit_duration_extreme = True
                if performance_type is None:
                    performance_type = 'good_performer'  # Fast sessions = good
        
        analysis['visit_count_extreme'] = visit_count_extreme
        analysis['visit_duration_extreme'] = visit_duration_extreme
        analysis['performance_extreme'] = visit_count_extreme or visit_duration_extreme
        analysis['performance_type'] = performance_type
    
    # Filter users who have all coach methods
    eligible_users = {pid: ua for pid, ua in user_analysis.items() 
                     if ua['all_methods_covered']}
    
    print(f"\nUsers with all coach methods: {len(eligible_users)}")
    
    # Select 10 participants with good mix
    print("\n5. Selecting 10 participants...")
    
    # Sort by criteria priority
    candidates = []
    for participant_id, analysis in eligible_users.items():
        score = 0
        
        # Must have all methods (already filtered)
        if not analysis['all_methods_covered']:
            continue
        
        # Performance extremes (good or bad)
        if analysis['performance_extreme']:
            score += 10
        
        # AI tool usage
        if analysis['ai_tool_used']:
            score += 5
        
        # Loop blocking
        if analysis['loop_blocked']:
            score += 5
        
        # Good ECD knowledge (low post test tries)
        if analysis['post_test_tries'] is not None:
            if analysis['post_test_tries'] <= 2:  # Low is good
                score += 8
            elif analysis['post_test_tries'] <= 3:
                score += 4
        
        candidates.append((participant_id, analysis, score))
    
    # Sort by score (descending)
    candidates.sort(key=lambda x: x[2], reverse=True)
    
    # Select diverse group with specific requirements
    selected = []
    selected_ai = 0
    selected_loop = 0
    selected_good_ecd = 0
    selected_perf_extreme = 0
    selected_good_performers = 0
    selected_bad_performers = 0
    
    # Separate candidates into categories
    ai_only_candidates = [(pid, a, s) for pid, a, s in candidates if a['ai_tool_used'] and not a['loop_blocked']]
    loop_only_candidates = [(pid, a, s) for pid, a, s in candidates if a['loop_blocked'] and not a['ai_tool_used']]
    both_candidates = [(pid, a, s) for pid, a, s in candidates if a['ai_tool_used'] and a['loop_blocked']]
    normal_candidates = [(pid, a, s) for pid, a, s in candidates if not a['ai_tool_used'] and not a['loop_blocked']]
    
    print(f"   Candidates breakdown:")
    print(f"   - AI only: {len(ai_only_candidates)}")
    print(f"   - Loop only: {len(loop_only_candidates)}")
    print(f"   - Both AI and Loop: {len(both_candidates)}")
    print(f"   - Normal interactions: {len(normal_candidates)}")
    
    # First, select 1-2 with AI tool usage only (prefer those with performance extremes)
    ai_only_candidates.sort(key=lambda x: (x[1]['performance_extreme'], x[2]), reverse=True)
    for participant_id, analysis, score in ai_only_candidates:
        if selected_ai >= 2 or len(selected) >= 10:
            break
        selected.append((participant_id, analysis))
        selected_ai += 1
        if analysis['performance_extreme']:
            selected_perf_extreme += 1
        if analysis['performance_type'] == 'good_performer':
            selected_good_performers += 1
        elif analysis['performance_type'] == 'bad_performer':
            selected_bad_performers += 1
        if analysis['post_test_tries'] is not None and analysis['post_test_tries'] <= 3:
            selected_good_ecd += 1
    
    # If we still need AI candidates and have none, take 1 from "both" category (max 2 total with AI)
    if selected_ai < 2 and len(selected) < 10:
        both_candidates.sort(key=lambda x: (x[1]['performance_extreme'], x[2]), reverse=True)
        for participant_id, analysis, score in both_candidates:
            if selected_ai >= 2 or len(selected) >= 10:
                break
            if any(pid == participant_id for pid, _ in selected):
                continue
            selected.append((participant_id, analysis))
            selected_ai += 1
            if analysis['performance_extreme']:
                selected_perf_extreme += 1
            if analysis['performance_type'] == 'good_performer':
                selected_good_performers += 1
            elif analysis['performance_type'] == 'bad_performer':
                selected_bad_performers += 1
            if analysis['post_test_tries'] is not None and analysis['post_test_tries'] <= 3:
                selected_good_ecd += 1
    
    # Count how many already have loop blocking (from AI+loop category)
    current_loop_total = sum(1 for _, a in selected if a['loop_blocked'])
    
    # Then, select 0-1 with loop blocking only
    # We want max 2 total with loop blocking (including those with AI+loop)
    max_loop_total = 2
    loop_only_candidates.sort(key=lambda x: (x[1]['performance_extreme'], x[2]), reverse=True)
    
    # Only select loop-only if we have fewer than 2 total with loop so far
    if current_loop_total < max_loop_total:
        for participant_id, analysis, score in loop_only_candidates:
            if current_loop_total >= max_loop_total or len(selected) >= 10:
                break
            if any(pid == participant_id for pid, _ in selected):
                continue
            selected.append((participant_id, analysis))
            selected_loop += 1
            current_loop_total += 1
            if analysis['performance_extreme']:
                selected_perf_extreme += 1
            if analysis['performance_type'] == 'good_performer':
                selected_good_performers += 1
            elif analysis['performance_type'] == 'bad_performer':
                selected_bad_performers += 1
            if analysis['post_test_tries'] is not None and analysis['post_test_tries'] <= 3:
                selected_good_ecd += 1
    
    # Fill remaining slots with normal interactions (no AI, no loops)
    # Prioritize performance extremes and good ECD knowledge
    normal_candidates.sort(key=lambda x: (x[1]['performance_extreme'], x[1]['post_test_tries'] is not None and x[1]['post_test_tries'] <= 3, x[2]), reverse=True)
    for participant_id, analysis, score in normal_candidates:
        if len(selected) >= 10:
            break
        if any(pid == participant_id for pid, _ in selected):
            continue
        
        selected.append((participant_id, analysis))
        if analysis['performance_extreme']:
            selected_perf_extreme += 1
        if analysis['performance_type'] == 'good_performer':
            selected_good_performers += 1
        elif analysis['performance_type'] == 'bad_performer':
            selected_bad_performers += 1
        if analysis['post_test_tries'] is not None and analysis['post_test_tries'] <= 3:
            selected_good_ecd += 1
    
    # If we still don't have 10, fill from any remaining candidates
    # Prioritize normal interactions, but allow a few more with loop if needed to reach 10
    if len(selected) < 10:
        current_loop_total = sum(1 for _, a in selected if a['loop_blocked'])
        current_ai_total = sum(1 for _, a in selected if a['ai_tool_used'])
        
        # First, try to add from "both" category but prefer those without loop if we already have 2 with loop
        # Sort to prefer those without loop if we're at limit
        both_sorted = sorted(both_candidates, key=lambda x: (
            x[1]['loop_blocked'] and current_loop_total >= 2,  # Put loop-blocked last if at limit
            not x[1]['performance_extreme'],
            -x[2]
        ))
        
        for participant_id, analysis, score in both_sorted:
            if len(selected) >= 10:
                break
            if any(pid == participant_id for pid, _ in selected):
                continue
            # Prefer not to add more with loop if we already have 2, but allow if needed
            if analysis['loop_blocked'] and current_loop_total >= 2 and len(selected) >= 8:
                # Only add if we're close to 10 and really need to fill
                pass  # Allow it to proceed
            selected.append((participant_id, analysis))
            if analysis['loop_blocked']:
                current_loop_total += 1
            if analysis['performance_extreme']:
                selected_perf_extreme += 1
            if analysis['performance_type'] == 'good_performer':
                selected_good_performers += 1
            elif analysis['performance_type'] == 'bad_performer':
                selected_bad_performers += 1
            if analysis['post_test_tries'] is not None and analysis['post_test_tries'] <= 3:
                selected_good_ecd += 1
        
        # Try loop-only if still needed (prefer to avoid, but allow if needed to reach 10)
        if len(selected) < 10:
            # Only add loop-only if we have fewer than 2 with loop, or if we're at 9 and need 1 more
            if current_loop_total < 2 or len(selected) >= 9:
                for participant_id, analysis, score in loop_only_candidates:
                    if len(selected) >= 10:
                        break
                    if any(pid == participant_id for pid, _ in selected):
                        continue
                    # Only add if we have < 2 with loop, or if we're at 9 and need 1 more
                    if current_loop_total >= 2 and len(selected) < 9:
                        continue
                    selected.append((participant_id, analysis))
                    current_loop_total += 1
                    if analysis['performance_extreme']:
                        selected_perf_extreme += 1
                    if analysis['performance_type'] == 'good_performer':
                        selected_good_performers += 1
                    elif analysis['performance_type'] == 'bad_performer':
                        selected_bad_performers += 1
                    if analysis['post_test_tries'] is not None and analysis['post_test_tries'] <= 3:
                        selected_good_ecd += 1
    
    # Print results
    print("\n" + "="*80)
    print("SELECTED 10 PARTICIPANTS FOR FOCUS GROUP DISCUSSION")
    print("="*80)
    
    for i, (participant_id, analysis) in enumerate(selected, 1):
        print(f"\n{i}. Participant ID: {participant_id}")
        print(f"   Methods used: {', '.join(sorted(analysis['methods_used']))}")
        print(f"   Total visits: {analysis['total_visits']}")
        print(f"   Avg visit duration: {analysis['avg_visit_duration']:.1f} min" if analysis['avg_visit_duration'] else "   Avg visit duration: N/A")
        print(f"   Post test tries: {analysis['post_test_tries']}" if analysis['post_test_tries'] is not None else "   Post test tries: N/A")
        
        # Performance type
        if analysis['performance_type']:
            perf_label = "GOOD PERFORMER" if analysis['performance_type'] == 'good_performer' else "BAD PERFORMER"
            print(f"   Performance type: {perf_label}")
            if analysis['visit_count_extreme']:
                if analysis['total_visits'] >= median_visit_count * 1.5:
                    print(f"      - High visit count: {analysis['total_visits']} (median: {median_visit_count:.1f})")
                else:
                    print(f"      - Low visit count: {analysis['total_visits']} (median: {median_visit_count:.1f})")
            if analysis['visit_duration_extreme']:
                if analysis['avg_visit_duration'] >= median_visit_duration * 1.5:
                    print(f"      - Long visit duration: {analysis['avg_visit_duration']:.1f} min (median: {median_visit_duration:.1f} min)")
                else:
                    print(f"      - Short visit duration: {analysis['avg_visit_duration']:.1f} min (median: {median_visit_duration:.1f} min)")
        else:
            print(f"   Performance type: NORMAL (within median range)")
        
        # Interaction type
        interaction_type = []
        if analysis['ai_tool_used']:
            interaction_type.append("AI tool usage")
        if analysis['loop_blocked']:
            interaction_type.append("Loop blocking")
        if not interaction_type:
            interaction_type.append("Normal interactions")
        print(f"   Interaction type: {', '.join(interaction_type)}")
        
        reasons = []
        if analysis['post_test_tries'] is not None and analysis['post_test_tries'] <= 3:
            reasons.append(f"Good ECD knowledge (post test tries: {analysis['post_test_tries']})")
        
        if reasons:
            print(f"   Additional notes: {', '.join(reasons)}")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total eligible users (all methods): {len(eligible_users)}")
    print(f"Users with AI tool usage: {sum(1 for ua in eligible_users.values() if ua['ai_tool_used'])}")
    print(f"Users with loop blocking: {sum(1 for ua in eligible_users.values() if ua['loop_blocked'])}")
    print(f"Users with good ECD knowledge (post test tries <= 3): {sum(1 for ua in eligible_users.values() if ua['post_test_tries'] is not None and ua['post_test_tries'] <= 3)}")
    print(f"Users with performance extremes: {sum(1 for ua in eligible_users.values() if ua['performance_extreme'])}")
    
    # Export to CSV
    output_file = Path("selected_focus_group_participants.csv")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Participant ID', 'Methods Used', 'Total Visits', 'Avg Visit Duration (min)', 
                        'Post Test Tries', 'Performance Type', 'Performance Details', 'AI Tool Used', 
                        'Loop Blocked', 'Interaction Type', 'Good ECD Knowledge'])
        for participant_id, analysis in selected:
            # Performance type and details
            perf_type = 'N/A'
            perf_details = ''
            if analysis['performance_type']:
                perf_type = 'Good Performer' if analysis['performance_type'] == 'good_performer' else 'Bad Performer'
                details = []
                if analysis['visit_count_extreme']:
                    if analysis['total_visits'] >= median_visit_count * 1.5:
                        details.append(f"High visits: {analysis['total_visits']} (median: {median_visit_count:.1f})")
                    else:
                        details.append(f"Low visits: {analysis['total_visits']} (median: {median_visit_count:.1f})")
                if analysis['visit_duration_extreme']:
                    if analysis['avg_visit_duration'] >= median_visit_duration * 1.5:
                        details.append(f"Long duration: {analysis['avg_visit_duration']:.1f}min (median: {median_visit_duration:.1f}min)")
                    else:
                        details.append(f"Short duration: {analysis['avg_visit_duration']:.1f}min (median: {median_visit_duration:.1f}min)")
                perf_details = '; '.join(details) if details else 'N/A'
            else:
                perf_type = 'Normal'
                perf_details = f"Visits: {analysis['total_visits']} (median: {median_visit_count:.1f}); Duration: {analysis['avg_visit_duration']:.1f}min (median: {median_visit_duration:.1f}min)" if analysis['avg_visit_duration'] else 'N/A'
            
            # Interaction type
            interaction_type = []
            if analysis['ai_tool_used']:
                interaction_type.append("AI tool")
            if analysis['loop_blocked']:
                interaction_type.append("Loop blocking")
            if not interaction_type:
                interaction_type.append("Normal")
            interaction_str = ', '.join(interaction_type)
            
            writer.writerow([
                participant_id,
                ', '.join(sorted(analysis['methods_used'])),
                analysis['total_visits'],
                f"{analysis['avg_visit_duration']:.1f}" if analysis['avg_visit_duration'] else 'N/A',
                analysis['post_test_tries'] if analysis['post_test_tries'] is not None else 'N/A',
                perf_type,
                perf_details,
                'Yes' if analysis['ai_tool_used'] else 'No',
                'Yes' if analysis['loop_blocked'] else 'No',
                interaction_str,
                'Yes' if (analysis['post_test_tries'] is not None and analysis['post_test_tries'] <= 3) else 'No'
            ])
    
    print(f"\nResults exported to: {output_file}")

if __name__ == "__main__":
    analyze_participants()

