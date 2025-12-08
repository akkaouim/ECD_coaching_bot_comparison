#!/usr/bin/env python3
"""
Simple Version Comparison Dashboard Generator
===========================================

A lightweight version that works directly with JSON files to avoid memory issues.
"""

import os
import sys
import json
import re
import webbrowser
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict
import statistics

# Add parent directory to path to access constants.py
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import constants

class SimpleVersionComparisonDashboard:
    """Lightweight version comparison dashboard generator"""
    
    def __init__(self):
        self.output_dir = Path("output/version_comparison")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Define coaching bot versions based on experiment IDs
        self.coaching_bot_versions = {
            "Control bot": {
                "experiment_id": ["1027993a-40c9-4484-a5fb-5c7e034dadcd"],
                "version_range": None  # All versions
            },
            "Coaching bot V3": {
                "experiment_id": ["e2b4855f-8550-47ff-87d2-d92018676ff3"],
                "version_range": None  # All versions
            },
            "Coaching bot V4": {
                "experiment_id": ["b7621271-da98-459f-9f9b-f68335d09ad4"],
                "version_range": (13, None)  # 13 and above
            },
            "Coaching bot V5": {
                "experiment_id": ["5d8be75e-03ff-4e3a-ab6a-e0aff6580986"],
                "version_range": (1, 4)  # 1 to 4
            },
            "Coaching bot V6": {
                "experiment_id": ["5d8be75e-03ff-4e3a-ab6a-e0aff6580986"],
                "version_range": (5, None)  # 5 and above
            }
        }
    
    def load_sessions_from_files(self) -> List[Dict]:
        """Load sessions from individual JSON files, filtered by relevant experiments and excluding Dimagi staff"""
        sessions_dir = Path("../data/consolidated/sessions")
        if not sessions_dir.exists():
            print(f"Error: {sessions_dir} not found")
            return []
        
        # Get relevant experiment IDs
        relevant_experiment_ids = set()
        for version_config in self.coaching_bot_versions.values():
            relevant_experiment_ids.update(version_config['experiment_id'])
        
        print(f"Loading sessions from {sessions_dir}")
        print(f"Looking for experiment IDs: {list(relevant_experiment_ids)}")
        
        filtered_sessions = []
        dimagi_sessions_excluded = 0
        session_files = list(sessions_dir.glob("session_*.json"))
        print(f"Found {len(session_files)} session files")
        
        for session_file in session_files:
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session = json.load(f)
                
                # Check if participant ID is a Dimagi email address
                participant_id = session.get('participant', {}).get('identifier', '')
                if participant_id.endswith('@dimagi.com'):
                    dimagi_sessions_excluded += 1
                    continue
                
                experiment_id = session.get('experiment', {}).get('id', '')
                if experiment_id in relevant_experiment_ids:
                        filtered_sessions.append(session)
            except Exception as e:
                print(f"Warning: Could not load {session_file.name}: {e}")
                continue
        
        print(f"Loaded {len(filtered_sessions)} sessions (filtered from {len(session_files)} total)")
        print(f"Excluded {dimagi_sessions_excluded} sessions from Dimagi staff (@dimagi.com)")
        return filtered_sessions
    
    def load_messages_from_files(self, session_ids: List[str]) -> Dict[str, List[Dict]]:
        """Load messages from individual JSON files, filtered by session IDs"""
        messages_dir = Path("../data/consolidated/messages")
        if not messages_dir.exists():
            print(f"Warning: {messages_dir} not found")
            return {}
        
        session_ids_set = set(session_ids)
        filtered_messages = {}
        
        print(f"Loading messages from {messages_dir}")
        message_files = list(messages_dir.glob("messages_*.json"))
        print(f"Found {len(message_files)} message files")
        
        for message_file in message_files:
            try:
                # Extract session ID from filename
                session_id = message_file.stem.replace('messages_', '')
                if session_id in session_ids_set:
                    with open(message_file, 'r', encoding='utf-8') as f:
                        message_data = json.load(f)
                        # The message file contains the session data with messages
                        if 'messages' in message_data:
                            filtered_messages[session_id] = message_data['messages']
            except Exception as e:
                print(f"Warning: Could not load {message_file.name}: {e}")
                continue
        
        print(f"Loaded messages for {len(filtered_messages)} sessions (filtered from {len(message_files)} total)")
        return filtered_messages
    
    def load_gs_visit_list(self) -> Dict[str, Dict]:
        """Load and merge GS visit data from both GS scores list.csv and ECD OCS Connect Data.csv
        ECD OCS Connect Data takes priority when there are conflicts (as it's a direct system export)
        """
        gs_data = {}
        
        # Step 1: Load data from GS scores list.csv (baseline)
        gs_file = Path("../data/GS scores list.csv")
        if gs_file.exists():
            print(f"Loading GS visit list from {gs_file}")
            try:
                with open(gs_file, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
                    reader = csv.DictReader(f)
                    for row in reader:
                        participant_id = row.get('Participant ID', '').strip()
                        if not participant_id:
                            continue
                        
                        gs_date_str = row.get('GS visit Date', '').strip()
                        gs_score_str = row.get('Score', '').strip()
                        # Handle BOM in Group column name
                        group = row.get('Group', row.get('\ufeffGroup', '')).strip()
                        cohort = row.get('Cohort', '').strip()
                        
                        gs_date = None
                        if gs_date_str:
                            # Try multiple date formats
                            date_formats = [
                                '%m/%d/%y',      # 6/26/25
                                '%m/%d/%Y',      # 6/26/2025
                                '%d-%m-%Y',      # 13-5-2025
                                '%d-%m-%y',      # 13-5-25
                                '%d/%m/%Y',      # 13/5/2025
                                '%d/%m/%y',      # 13/5/25
                                '%Y-%m-%d',      # 2025-06-26
                            ]
                            
                            for date_format in date_formats:
                                try:
                                    gs_date = datetime.strptime(gs_date_str, date_format)
                                    break
                                except ValueError:
                                    continue
                            
                            if gs_date is None:
                                print(f"Warning: Could not parse GS date '{gs_date_str}' for participant {participant_id}")
                        
                        gs_score = None
                        if gs_score_str:
                            try:
                                gs_score = int(gs_score_str)
                            except ValueError:
                                pass
                        
                        gs_data[participant_id] = {
                            'date': gs_date,
                            'date_str': gs_date_str,  # Keep original string format
                            'score': gs_score,
                            'group': group,
                            'cohort': cohort,
                            'source': 'gs_scores_list'  # Track data source
                        }
                
                print(f"Loaded GS visit data from GS scores list for {len(gs_data)} participants")
            except Exception as e:
                print(f"Error loading GS visit list: {e}")
        else:
            print(f"Warning: {gs_file} not found")
        
        # Step 2: Load and merge data from ECD OCS Connect Data.csv (takes priority)
        ecd_file = Path("../data/ECD OCS Connect Data.csv")
        if ecd_file.exists():
            print(f"Loading and merging GS data from {ecd_file}")
            ecd_updates = 0
            ecd_new = 0
            try:
                with open(ecd_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        participant_id = row.get('connect_id', '').strip()
                        if not participant_id:
                            continue
                        
                        # Get GS score from ECD (gs_total_score_percent)
                        gs_score_str = row.get('gs_total_score_percent', '').strip()
                        gs_score = None
                        if gs_score_str:
                            try:
                                # ECD has percentage, convert to integer score
                                gs_score_float = float(gs_score_str)
                                gs_score = int(round(gs_score_float))
                            except (ValueError, TypeError):
                                pass
                        
                        # Get GS date from ECD (gs1_date)
                        gs_date_str = row.get('gs1_date', '').strip()
                        gs_date = None
                        if gs_date_str:
                            # ECD dates are typically in YYYY-MM-DD format
                            date_formats = [
                                '%Y-%m-%d',      # 2025-10-07
                                '%m/%d/%y',      # 6/26/25
                                '%m/%d/%Y',      # 6/26/2025
                                '%d-%m-%Y',      # 13-5-2025
                                '%d-%m-%y',      # 13-5-25
                                '%d/%m/%Y',      # 13/5/2025
                                '%d/%m/%y',      # 13/5/25
                            ]
                            
                            for date_format in date_formats:
                                try:
                                    gs_date = datetime.strptime(gs_date_str, date_format)
                                    break
                                except ValueError:
                                    continue
                        
                        # Get group from coach_vs_control (coach -> B, control -> A)
                        coach_vs_control = row.get('coach_vs_control', '').strip().lower()
                        group = None
                        if coach_vs_control == 'coach':
                            group = 'B'
                        elif coach_vs_control == 'control':
                            group = 'A'
                        
                        # Check if this participant already exists
                        if participant_id in gs_data:
                            # Update existing entry (ECD takes priority)
                            existing = gs_data[participant_id]
                            
                            # Update score if ECD has it (even if GS scores list had it)
                            if gs_score is not None:
                                if existing['score'] != gs_score:
                                    print(f"  Updating score for {participant_id}: {existing['score']} -> {gs_score} (ECD priority)")
                                existing['score'] = gs_score
                            
                            # Update date if ECD has it
                            if gs_date is not None:
                                existing['date'] = gs_date
                                existing['date_str'] = gs_date_str
                            
                            # Update group if ECD has it
                            if group:
                                existing['group'] = group
                            
                            existing['source'] = 'merged'  # Mark as merged
                            ecd_updates += 1
                        else:
                            # New participant from ECD
                            gs_data[participant_id] = {
                                'date': gs_date,
                                'date_str': gs_date_str,
                                'score': gs_score,
                                'group': group,
                                'cohort': '',  # ECD doesn't have cohort
                                'source': 'ecd_ocs_connect'
                            }
                            ecd_new += 1
                
                print(f"  Updated {ecd_updates} existing participants from ECD OCS Connect Data")
                print(f"  Added {ecd_new} new participants from ECD OCS Connect Data")
            except Exception as e:
                print(f"Error loading ECD OCS Connect Data: {e}")
        else:
            print(f"Warning: {ecd_file} not found")
        
        print(f"Total GS visit data loaded: {len(gs_data)} participants")
        return gs_data
    
    def load_flw_activity_data(self) -> Dict[str, Dict]:
        """Load FLW activity data from ECD OCS Connect Data.csv
        Returns a dictionary mapping participant_id to activity metrics
        """
        flw_data = {}
        ecd_file = Path("../data/ECD OCS Connect Data.csv")
        
        if not ecd_file.exists():
            print(f"Warning: {ecd_file} not found. FLW activity data will not be available.")
            return flw_data
        
        print(f"Loading FLW activity data from {ecd_file}")
        try:
            with open(ecd_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                loaded_count = 0
                for row in reader:
                    participant_id = row.get('connect_id', '').strip()
                    if not participant_id:
                        continue
                    
                    # Load all FLW activity metrics
                    activity_metrics = {}
                    
                    # approved_visits_percentage
                    approved_visits_str = row.get('approved_visits_percentage', '').strip()
                    if approved_visits_str:
                        try:
                            activity_metrics['approved_visits_percentage'] = float(approved_visits_str)
                        except (ValueError, TypeError):
                            pass
                    
                    # ecd_completed_intervention_percentage
                    completed_intervention_str = row.get('ecd_completed_intervention_percentage', '').strip()
                    if completed_intervention_str:
                        try:
                            activity_metrics['ecd_completed_intervention_percentage'] = float(completed_intervention_str)
                        except (ValueError, TypeError):
                            pass
                    
                    # visits_before_gs1
                    visits_before_gs1_str = row.get('visits_before_gs1', '').strip()
                    if visits_before_gs1_str:
                        try:
                            activity_metrics['visits_before_gs1'] = float(visits_before_gs1_str)
                        except (ValueError, TypeError):
                            pass
                    
                    # time_spent_learn (in hours, will convert to days later)
                    time_spent_learn_str = row.get('time_spent_learn', '').strip()
                    if time_spent_learn_str:
                        try:
                            activity_metrics['time_spent_learn'] = float(time_spent_learn_str)
                        except (ValueError, TypeError):
                            pass
                    
                    # post_test_tries
                    post_test_tries_str = row.get('post_test_tries', '').strip()
                    if post_test_tries_str:
                        try:
                            activity_metrics['post_test_tries'] = float(post_test_tries_str)
                        except (ValueError, TypeError):
                            pass
                    
                    # avg_distance_km_between_visits
                    avg_distance_str = row.get('avg_distance_km_between_visits', '').strip()
                    if avg_distance_str:
                        try:
                            activity_metrics['avg_distance_km_between_visits'] = float(avg_distance_str)
                        except (ValueError, TypeError):
                            pass
                    
                    # avg_minutes_between_visits
                    avg_minutes_str = row.get('avg_minutes_between_visits', '').strip()
                    if avg_minutes_str:
                        try:
                            activity_metrics['avg_minutes_between_visits'] = float(avg_minutes_str)
                        except (ValueError, TypeError):
                            pass
                    
                    if activity_metrics:
                        flw_data[participant_id] = activity_metrics
                        loaded_count += 1
                
                print(f"Loaded FLW activity data for {loaded_count} participants")
        except Exception as e:
            print(f"Error loading FLW activity data: {e}")
        
        return flw_data
    
    def matches_version(self, session: Dict, version_config: Dict, messages: List[Dict] = None) -> bool:
        """Check if session matches version criteria based on last message version tag"""
        experiment_id = session.get('experiment', {}).get('id', '')

        # Check experiment ID match
        if experiment_id not in version_config['experiment_id']:
            return False
        
        # Get version from last message tags if available
        version_number = self.get_version_from_last_message(messages) if messages else 0
        
        # Check version constraints
        version_range = version_config.get('version_range')
        if version_range is None:
            return True  # All versions
        elif version_range[1] is None:
            return version_number >= version_range[0]  # min and above
        else:
            return version_range[0] <= version_number <= version_range[1]  # range
    
    def get_version_from_last_message(self, messages: List[Dict]) -> int:
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
    
    def is_split_session(self, session: Dict, messages: List[Dict] = None) -> bool:
        """Check if session is a split session - defined as session with less than 3 participant messages"""
        if messages is None:
            return False
        
        # Count user messages
        user_message_count = 0
        for message in messages:
            if message.get('role') == 'user':
                user_message_count += 1
        
        # A split session has less than 3 user messages
        return user_message_count < 3
    
    def is_test_session(self, session: Dict) -> bool:
        """Check if session is a test session - defined by participant ID being an email address like *@dimagi.com"""
        participant_id = session.get('participant', {}).get('identifier', '')
        return participant_id.endswith('@dimagi.com')
    
    def should_exclude_session(self, session: Dict, messages: List[Dict] = None) -> bool:
        """Check if session should be excluded (split or test session)"""
        return self.is_split_session(session, messages) or self.is_test_session(session)
    
    def is_annotated_session(self, session: Dict, messages: List[Dict] = None) -> bool:
        """Check if session is annotated - excludes sessions with only coaching method tags"""
        # Collect all non-version tags from session and messages
        all_non_version_tags = []
        
        # Check session tags
        for tag in session.get('tags', []):
            if not self.is_version_tag(tag):
                all_non_version_tags.append(tag)
        
        # Check message tags if messages provided
        if messages:
            for message in messages:
                for tag in message.get('tags', []):
                    if not self.is_version_tag(tag):
                        all_non_version_tags.append(tag)
        
        # If no non-version tags, not annotated
        if not all_non_version_tags:
            return False
        
        # Check if all non-version tags are coaching method tags
        non_coaching_method_tags = [tag for tag in all_non_version_tags if not self.is_coaching_method_tag(tag)]
        
        # Session is annotated if it has non-version tags that are NOT all coaching method tags
        return len(non_coaching_method_tags) > 0
    
    def is_version_tag(self, tag: str) -> bool:
        """Check if tag is a version tag"""
        tag_lower = tag.lower()
        return (tag_lower.startswith('v') and tag_lower[1:].isdigit()) or 'unreleased' in tag_lower
    
    def is_coaching_method_tag(self, tag: str) -> bool:
        """Check if tag is a coaching method tag"""
        tag_lower = tag.lower()
        return tag_lower.startswith('coach_method_')
    
    def has_refrigerator_example_tag(self, session: Dict, messages: List[Dict] = None) -> bool:
        """Check if session has refrigerator_example tag"""
        # Check session tags
        if 'refrigerator_example' in session.get('tags', []):
            return True
        
        # Check message tags if messages provided
        if messages:
            for message in messages:
                if 'refrigerator_example' in message.get('tags', []):
                    return True
        
        return False
    
    def has_refrigerator_annotation(self, session: Dict, messages: List[Dict] = None) -> bool:
        """Check if session has refrigerator_example OR not_refrigerator_example tag"""
        # Check session tags
        session_tags = session.get('tags', [])
        if 'refrigerator_example' in session_tags or 'not_refrigerator_example' in session_tags:
            return True
        
        # Check message tags if messages provided
        if messages:
            for message in messages:
                message_tags = message.get('tags', [])
                if 'refrigerator_example' in message_tags or 'not_refrigerator_example' in message_tags:
                    return True
        
        return False
    
    def has_not_refrigerator_example_tag(self, session: Dict, messages: List[Dict] = None) -> bool:
        """Check if session has not_refrigerator_example tag"""
        # Check session tags
        if 'not_refrigerator_example' in session.get('tags', []):
            return True
        
        # Check message tags if messages provided
        if messages:
            for message in messages:
                if 'not_refrigerator_example' in message.get('tags', []):
                    return True
        
        return False
    
    def detect_coaching_method(self, session: Dict, messages: List[Dict] = None) -> str:
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
    
    def calculate_refrigerator_rate_by_method(self, sessions: List[Dict], messages_data: Dict) -> Dict[str, Dict[str, float]]:
        """Calculate refrigerator example rate by coaching method
        
        Returns a dict with two calculation modes:
        - 'annotated': refrigerator_example / total annotated sessions (refrigerator_example OR not_refrigerator_example)
        - 'explicit': refrigerator_example / (refrigerator_example + not_refrigerator_example)
        """
        # Group sessions by method
        method_sessions = {}
        for session in sessions:
            session_id = session.get('id')
            messages = messages_data.get(session_id, [])
            
            # Skip split sessions and test sessions
            if self.should_exclude_session(session, messages):
                continue
            
            method = self.detect_coaching_method(session, messages)
            
            if method not in method_sessions:
                method_sessions[method] = []
            method_sessions[method].append((session, messages))
        
        # Calculate rates for each method
        method_rates = {}
        for method, session_list in method_sessions.items():
            # For "annotated" mode: use ALL annotated sessions (not just refrigerator-tagged ones)
            all_annotated_sessions = []
            # For "explicit" mode: only sessions with explicit refrigerator tags
            refrigerator_annotated_sessions = []
            
            for session, messages in session_list:
                # Check if session is annotated (has any non-version, non-coaching-method tags)
                if self.is_annotated_session(session, messages):
                    all_annotated_sessions.append((session, messages))
                
                # Check if session has refrigerator-related tags
                if self.has_refrigerator_annotation(session, messages):
                    refrigerator_annotated_sessions.append((session, messages))
            
            # Count refrigerator examples in all annotated sessions (for "annotated" mode)
            refrigerator_count_annotated = 0
            for session, messages in all_annotated_sessions:
                if self.has_refrigerator_example_tag(session, messages):
                    refrigerator_count_annotated += 1
            
            # Count refrigerator examples and not-refrigerator in explicitly tagged sessions (for "explicit" mode)
            refrigerator_count_explicit = 0
            not_refrigerator_count = 0
            for session, messages in refrigerator_annotated_sessions:
                if self.has_refrigerator_example_tag(session, messages):
                    refrigerator_count_explicit += 1
                elif self.has_not_refrigerator_example_tag(session, messages):
                    not_refrigerator_count += 1
            
            # Calculate rate 1: refrigerator_example / total annotated sessions (ALL annotated sessions)
            rate_annotated = (refrigerator_count_annotated / len(all_annotated_sessions)) * 100 if all_annotated_sessions else 0.0
            
            # Calculate rate 2: refrigerator_example / (refrigerator_example + not_refrigerator_example)
            explicit_total = refrigerator_count_explicit + not_refrigerator_count
            rate_explicit = (refrigerator_count_explicit / explicit_total) * 100 if explicit_total > 0 else 0.0
            
            method_rates[method] = {
                'annotated': rate_annotated,
                'explicit': rate_explicit
            }
        
        return method_rates

    def get_session_number_for_participant(self, session: Dict, all_sessions: List[Dict]) -> int:
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
        
        # Sort by creation time
        participant_sessions.sort(key=lambda x: x.get('created_at', ''))
        
        # Find the position of current session
        for i, s in enumerate(participant_sessions):
            if s.get('id') == session.get('id'):
                return i + 1
        
        return 1

    def calculate_median_words_by_method_and_version(self, sessions: List[Dict], messages: List[Dict], exclude_outliers: bool = False) -> Dict[str, Dict[str, float]]:
        """Calculate median user words per session grouped by coaching method and version"""
        method_version_words = {}
        
        # Initialize structure
        for method in ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']:
            method_version_words[method] = {}
            for version in ['V3', 'V4', 'V5', 'V6', 'Control']:
                method_version_words[method][version] = []
        
        # Collect word counts for each method-version combination
        for session in sessions:
            session_id = session.get('id')
            session_messages = messages.get(session_id, [])
            
            # Skip split sessions and test sessions
            if self.should_exclude_session(session, session_messages):
                continue
            
            # Determine version and method
            version = None
            detected_method = None
            
            # Check if this is a Control bot session first
            control_config = self.coaching_bot_versions.get('Control bot', {})
            if self.matches_version(session, control_config, session_messages):
                # Control bot sessions should all be categorized as "Unknown"
                detected_method = 'Unknown'
                version = 'Control'  # Use a special identifier for Control bot
            else:
                # For coaching bots, detect method and version normally
                detected_method = self.detect_coaching_method(session, session_messages)
                
                # Determine version
                for version_name, version_config in self.coaching_bot_versions.items():
                    if version_name != 'Control bot' and self.matches_version(session, version_config, session_messages):
                        if 'V3' in version_name:
                            version = 'V3'
                        elif 'V4' in version_name:
                            version = 'V4'
                        elif 'V5' in version_name:
                            version = 'V5'
                        elif 'V6' in version_name:
                            version = 'V6'
                        break
            
            if detected_method and version:
                # Calculate total user words and message count in this session
                user_words = 0
                user_message_count = 0
                for message in session_messages:
                    if message.get('role') == 'user':
                        user_message_count += 1
                        content = message.get('content', '')
                        if content:
                            user_words += len(content.split())
                
                # Apply outlier filtering if requested
                if exclude_outliers:
                    if self.is_outlier_session(session_messages, user_message_count, user_words):
                        continue
                
                # For Control bot, include all sessions (even with 0 words)
                # For coaching bots, only include sessions with words > 0
                if version == 'Control' or user_words > 0:
                    method_version_words[detected_method][version].append(user_words)
        
        # Calculate medians
        median_results = {}
        for method in method_version_words:
            median_results[method] = {}
            for version in method_version_words[method]:
                word_counts = method_version_words[method][version]
                if word_counts:
                    word_counts.sort()
                    n = len(word_counts)
                    if n % 2 == 0:
                        median = (word_counts[n//2 - 1] + word_counts[n//2]) / 2
                    else:
                        median = word_counts[n//2]
                    median_results[method][version] = median
                else:
                    median_results[method][version] = 0.0
        
        return median_results

    def calculate_median_messages_by_method_and_version(self, sessions: List[Dict], messages: Dict, exclude_outliers: bool = False) -> Dict[str, Dict[str, float]]:
        """Calculate median number of participant messages per session grouped by coaching method and version"""
        method_version_messages = {}
        
        # Initialize structure
        for method in ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']:
            method_version_messages[method] = {}
            for version in ['V3', 'V4', 'V5', 'V6', 'Control']:
                method_version_messages[method][version] = []
        
        # Collect message counts for each method-version combination
        for session in sessions:
            session_id = session.get('id')
            session_messages = messages.get(session_id, [])
            
            # Skip split sessions and test sessions
            if self.should_exclude_session(session, session_messages):
                continue
            
            # Determine version and method
            version = None
            detected_method = None
            
            # Check if this is a Control bot session first
            control_config = self.coaching_bot_versions.get('Control bot', {})
            if self.matches_version(session, control_config, session_messages):
                # Control bot sessions should all be categorized as "Unknown"
                detected_method = 'Unknown'
                version = 'Control'  # Use a special identifier for Control bot
            else:
                # For coaching bots, detect method and version normally
                detected_method = self.detect_coaching_method(session, session_messages)
                
                # Determine version
                for version_name, version_config in self.coaching_bot_versions.items():
                    if version_name != 'Control bot' and self.matches_version(session, version_config, session_messages):
                        if 'V3' in version_name:
                            version = 'V3'
                        elif 'V4' in version_name:
                            version = 'V4'
                        elif 'V5' in version_name:
                            version = 'V5'
                        elif 'V6' in version_name:
                            version = 'V6'
                        break
            
            if detected_method and version:
                # Count user messages and words for this session
                user_message_count = 0
                user_words = 0
                for message in session_messages:
                    if message.get('role') == 'user':
                        user_message_count += 1
                        content = message.get('content', '')
                        if content:
                            user_words += len(content.split())
                
                # Apply outlier filtering if requested
                if exclude_outliers:
                    if self.is_outlier_session(session_messages, user_message_count, user_words):
                        continue
                
                # For Control bot, include all sessions (even with 0 messages)
                # For coaching bots, only include sessions with messages > 0
                if version == 'Control' or user_message_count > 0:
                    method_version_messages[detected_method][version].append(user_message_count)
        
        # Calculate medians
        median_results = {}
        for method in method_version_messages:
            median_results[method] = {}
            for version in method_version_messages[method]:
                message_counts = method_version_messages[method][version]
                if message_counts:
                    message_counts.sort()
                    n = len(message_counts)
                    if n % 2 == 0:
                        median = (message_counts[n//2 - 1] + message_counts[n//2]) / 2
                    else:
                        median = message_counts[n//2]
                    median_results[method][version] = median
                else:
                    median_results[method][version] = 0.0
        
        return median_results

    def is_outlier_session(self, session_messages: List[Dict], user_message_count: int, user_words: int) -> bool:
        """Check if session is an outlier based on message count or word count (3 standard deviations from mean)"""
        if not session_messages or user_message_count == 0:
            return False
        
        # Calculate statistics for all sessions to determine outliers
        # This is a simplified approach - in practice, you'd want to calculate these once and cache them
        # For now, we'll use reasonable thresholds based on typical session patterns
        
        # Typical session patterns (these could be calculated dynamically from all sessions)
        # Message count thresholds (3 std dev from typical range)
        message_threshold = 50  # Most normal sessions have < 50 user messages
        
        # Word count thresholds (3 std dev from typical range)  
        word_threshold = 1000  # Most normal sessions have < 1000 user words
        
        return user_message_count > message_threshold or user_words > word_threshold

    def calculate_session_progression_data(self, sessions: List[Dict], messages: List[Dict], exclude_outliers: bool = False, return_session_data: bool = False) -> Dict:
        """Calculate session progression data for line graph"""
        # Group sessions by participant, excluding split and test sessions
        participant_sessions = {}
        session_level_data = []  # Store session-level data for filtering
        
        for session in sessions:
            session_id = session.get('id')
            session_messages = messages.get(session_id, [])
            
            # Skip split sessions and test sessions
            if self.should_exclude_session(session, session_messages):
                continue
                
            participant_id = session.get('participant', {}).get('identifier', '')
            if participant_id:
                if participant_id not in participant_sessions:
                    participant_sessions[participant_id] = []
                participant_sessions[participant_id].append(session)
        
        # Sort sessions by creation time for each participant
        for participant_id in participant_sessions:
            participant_sessions[participant_id].sort(key=lambda x: x.get('created_at', ''))
        
        # Calculate progression data
        progression_data = {
            'by_method': {},  # Option A: One line per coaching method
            'by_method_version': {},  # Option B: One line per coaching method per version
            'by_version': {}  # Option C: One line per version
        }
        
        # Initialize data structures
        for method in ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']:
            progression_data['by_method'][method] = {}
            for version in ['V3', 'V4', 'V5', 'V6', 'Control']:
                progression_data['by_method_version'][f"{method}_{version}"] = {}
        
        for version in ['V3', 'V4', 'V5', 'V6', 'Control']:
            progression_data['by_version'][version] = {}
        
        # Process each participant's sessions
        for participant_id, participant_session_list in participant_sessions.items():
            for session_index, session in enumerate(participant_session_list):
                session_number = session_index + 1
                if session_number > 22:  # Limit to 22 sessions as specified
                    break
                
                session_id = session.get('id')
                session_messages = messages.get(session_id, [])
                
                # Calculate user words and message count for this session
                user_words = 0
                user_message_count = 0
                for message in session_messages:
                    if message.get('role') == 'user':
                        user_message_count += 1
                        content = message.get('content', '')
                        if content:
                            user_words += len(content.split())
                
                # Apply outlier filtering if requested
                if exclude_outliers:
                    if self.is_outlier_session(session_messages, user_message_count, user_words):
                        continue
                
                if user_words == 0:
                    continue
                
                # Detect coaching method
                detected_method = self.detect_coaching_method(session, session_messages)
                
                # Determine version
                version = None
                for version_name, version_config in self.coaching_bot_versions.items():
                    if self.matches_version(session, version_config, session_messages):
                        if 'Control' in version_name:
                            version = 'Control'
                        elif 'V3' in version_name:
                            version = 'V3'
                        elif 'V4' in version_name:
                            version = 'V4'
                        elif 'V5' in version_name:
                            version = 'V5'
                        elif 'V6' in version_name:
                            version = 'V6'
                        break
                
                if not detected_method or not version:
                    continue
                
                # Add to progression data
                # Option A: By method
                if session_number not in progression_data['by_method'][detected_method]:
                    progression_data['by_method'][detected_method][session_number] = []
                progression_data['by_method'][detected_method][session_number].append(user_words)
                
                # Option B: By method and version
                method_version_key = f"{detected_method}_{version}"
                if session_number not in progression_data['by_method_version'][method_version_key]:
                    progression_data['by_method_version'][method_version_key][session_number] = []
                progression_data['by_method_version'][method_version_key][session_number].append(user_words)
                
                # Option C: By version
                if session_number not in progression_data['by_version'][version]:
                    progression_data['by_version'][version][session_number] = []
                progression_data['by_version'][version][session_number].append(user_words)
                
                # Store session-level data for filtering
                if return_session_data:
                    session_level_data.append({
                        'session_id': session_id,
                        'participant_id': participant_id,
                        'session_number': session_number,
                        'user_words': user_words,
                        'method': detected_method,
                        'version': version
                    })
        
        # Calculate averages for each session number
        for option in progression_data:
            for key in progression_data[option]:
                for session_num in progression_data[option][key]:
                    word_counts = progression_data[option][key][session_num]
                    if word_counts:
                        progression_data[option][key][session_num] = sum(word_counts) / len(word_counts)
                    else:
                        progression_data[option][key][session_num] = 0
        
        if return_session_data:
            return progression_data, session_level_data
        return progression_data

    def calculate_average_rating_by_method_and_version(self, sessions: List[Dict], messages_data: Dict) -> Dict:
        """Calculate average session rating by coaching method and version"""
        # Initialize structure
        method_version_ratings = {}
        for method in ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']:
            method_version_ratings[method] = {}
            for version in ['V3', 'V4', 'V5', 'V6', 'Control']:
                method_version_ratings[method][version] = []
        
        # Process each session
        for session in sessions:
            session_id = session.get('id')
            session_messages = messages_data.get(session_id, [])
            
            # Skip split sessions and test sessions
            if self.should_exclude_session(session, session_messages):
                continue
            
            # Get session rating
            session_rating = self.extract_session_rating(session, session_messages)
            if session_rating is None:
                continue
            
            # Detect coaching method
            detected_method = self.detect_coaching_method(session, session_messages)
            
            # Determine version
            version = None
            for version_name, version_config in self.coaching_bot_versions.items():
                if self.matches_version(session, version_config, session_messages):
                    if 'Control' in version_name:
                        version = 'Control'
                    elif 'V3' in version_name:
                        version = 'V3'
                    elif 'V4' in version_name:
                        version = 'V4'
                    elif 'V5' in version_name:
                        version = 'V5'
                    elif 'V6' in version_name:
                        version = 'V6'
                    break
            
            if not version:
                continue
            
            # For Control bot, use 'Unknown' method if no method detected
            if version == 'Control' and not detected_method:
                detected_method = 'Unknown'
            
            # Add rating to the appropriate method-version combination
            method_version_ratings[detected_method][version].append(session_rating)
        
        # Calculate averages
        average_ratings = {}
        for method in method_version_ratings:
            average_ratings[method] = {}
            for version in method_version_ratings[method]:
                ratings = method_version_ratings[method][version]
                if ratings:
                    average_ratings[method][version] = sum(ratings) / len(ratings)
                else:
                    average_ratings[method][version] = 0.0
        
        return average_ratings
    
    def calculate_flw_activity_metrics(self, sessions: List[Dict], messages_data: Dict, flw_activity_data: Dict[str, Dict], metric_type: str) -> Dict[str, Dict[str, float]]:
        """Calculate FLW activity metrics by method and version
        
        Args:
            sessions: List of session dictionaries
            messages_data: Dictionary mapping session_id to list of messages
            flw_activity_data: Dictionary mapping participant_id to activity metrics
            metric_type: One of 'approved_visits_percentage', 'ecd_completed_intervention_percentage', 
                        'visits_before_gs1', 'time_spent_learn', 'post_test_tries'
        
        Returns:
            Dictionary with structure: {method: {version: value}}
            - For approved_visits_percentage and ecd_completed_intervention_percentage: median
            - For visits_before_gs1, time_spent_learn, post_test_tries: average
        """
        method_version_values = {}
        
        # Initialize structure
        for method in ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']:
            method_version_values[method] = {}
            for version in ['V3', 'V4', 'V5', 'V6', 'Control']:
                method_version_values[method][version] = []
        
        # Track participants we've already processed (to avoid double counting)
        participant_processed = {}
        
        # Collect values for each method-version combination
        for session in sessions:
            session_id = session.get('id')
            session_messages = messages_data.get(session_id, [])
            
            # Skip split sessions and test sessions
            if self.should_exclude_session(session, session_messages):
                continue
            
            # Get participant ID
            participant_id = session.get('participant', {}).get('identifier', '').strip()
            if not participant_id:
                continue
            
            # Get activity data for this participant
            activity_metrics = flw_activity_data.get(participant_id)
            if not activity_metrics:
                continue
            
            # Get the specific metric value
            metric_value = activity_metrics.get(metric_type)
            if metric_value is None:
                continue
            
            # Determine version and method
            version = None
            detected_method = None
            
            # Check if this is a Control bot session first
            control_config = self.coaching_bot_versions.get('Control bot', {})
            if self.matches_version(session, control_config, session_messages):
                detected_method = 'Unknown'
                version = 'Control'
            else:
                # For coaching bots, detect method and version normally
                detected_method = self.detect_coaching_method(session, session_messages)
                
                # Determine version
                for version_name, version_config in self.coaching_bot_versions.items():
                    if version_name != 'Control bot' and self.matches_version(session, version_config, session_messages):
                        if 'V3' in version_name:
                            version = 'V3'
                        elif 'V4' in version_name:
                            version = 'V4'
                        elif 'V5' in version_name:
                            version = 'V5'
                        elif 'V6' in version_name:
                            version = 'V6'
                        break
            
            if version and detected_method:
                # Use participant_id + version + method as key to avoid double counting same participant
                participant_key = f"{participant_id}_{version}_{detected_method}"
                if participant_key not in participant_processed:
                    method_version_values[detected_method][version].append(metric_value)
                    participant_processed[participant_key] = True
        
        # Calculate medians or averages
        method_version_results = {}
        for method in method_version_values:
            method_version_results[method] = {}
            for version in method_version_values[method]:
                values = method_version_values[method][version]
                if not values:
                    method_version_results[method][version] = None
                else:
                    if metric_type in ['approved_visits_percentage', 'ecd_completed_intervention_percentage']:
                        # Use median for percentages
                        sorted_values = sorted(values)
                        n = len(sorted_values)
                        if n % 2 == 0:
                            median = (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
                        else:
                            median = sorted_values[n//2]
                        method_version_results[method][version] = median
                    else:
                        # Use average for counts and time
                        avg = sum(values) / len(values)
                        if metric_type == 'time_spent_learn':
                            # Convert hours to days
                            avg = avg / 24.0
                        method_version_results[method][version] = avg
        
        return method_version_results
    
    def calculate_rating_distribution(self, sessions: List[Dict], messages_data: Dict) -> Dict:
        """Calculate rating distribution (counts and percentages for ratings 1-5) by method and version
        
        Returns:
            Dictionary with structure: {
                'all': {rating: count},  # All sessions combined
                'by_method': {method: {rating: count}},
                'by_version': {version: {rating: count}},
                'by_method_version': {method: {version: {rating: count}}}
            }
        """
        from collections import defaultdict
        
        # Initialize data structures
        all_ratings = defaultdict(int)  # {rating: count}
        by_method = defaultdict(lambda: defaultdict(int))  # {method: {rating: count}}
        by_version = defaultdict(lambda: defaultdict(int))  # {version: {rating: count}}
        by_method_version = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))  # {method: {version: {rating: count}}}
        
        # Process each session
        for session in sessions:
            session_id = session.get('id')
            session_messages = messages_data.get(session_id, [])
            
            # Skip split sessions and test sessions
            if self.should_exclude_session(session, session_messages):
                continue
            
            # Get session rating
            session_rating = self.extract_session_rating(session, session_messages)
            if session_rating is None:
                continue
            
            # Convert to integer (ratings are 1-5)
            rating = int(session_rating)
            if rating < 1 or rating > 5:
                continue
            
            # Detect coaching method
            detected_method = self.detect_coaching_method(session, session_messages)
            
            # Determine version
            version = None
            for version_name, version_config in self.coaching_bot_versions.items():
                if self.matches_version(session, version_config, session_messages):
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
            
            if not version:
                continue
            
            # For Control bot, use 'Unknown' method if no method detected
            if version == 'Control bot' and not detected_method:
                detected_method = 'Unknown'
            
            # Count ratings
            all_ratings[rating] += 1
            by_method[detected_method][rating] += 1
            by_version[version][rating] += 1
            by_method_version[detected_method][version][rating] += 1
        
        # Calculate percentages
        total_all = sum(all_ratings.values())
        all_percentages = {rating: (count / total_all * 100) if total_all > 0 else 0 
                          for rating, count in all_ratings.items()}
        
        by_method_percentages = {}
        for method, ratings in by_method.items():
            total = sum(ratings.values())
            by_method_percentages[method] = {rating: (count / total * 100) if total > 0 else 0 
                                            for rating, count in ratings.items()}
        
        by_version_percentages = {}
        for version, ratings in by_version.items():
            total = sum(ratings.values())
            by_version_percentages[version] = {rating: (count / total * 100) if total > 0 else 0 
                                              for rating, count in ratings.items()}
        
        by_method_version_percentages = {}
        for method, version_data in by_method_version.items():
            by_method_version_percentages[method] = {}
            for version, ratings in version_data.items():
                total = sum(ratings.values())
                by_method_version_percentages[method][version] = {rating: (count / total * 100) if total > 0 else 0 
                                                                  for rating, count in ratings.items()}
        
        return {
            'all': {
                'counts': dict(all_ratings),
                'percentages': all_percentages,
                'total': total_all
            },
            'by_method': {
                'counts': {method: dict(ratings) for method, ratings in by_method.items()},
                'percentages': by_method_percentages
            },
            'by_version': {
                'counts': {version: dict(ratings) for version, ratings in by_version.items()},
                'percentages': by_version_percentages
            },
            'by_method_version': {
                'counts': {method: {version: dict(ratings) for version, ratings in version_data.items()} 
                          for method, version_data in by_method_version.items()},
                'percentages': by_method_version_percentages
            }
        }

    def calculate_session_volume_by_time(self, sessions: List[Dict], messages_data: Dict, aggregation: str = 'week', refrigerator_only: bool = False, return_session_mapping: bool = False) -> Dict:
        """
        Calculate session volume grouped by time period, version, and coaching method.
        
        Args:
            sessions: List of session dictionaries
            messages_data: Dictionary mapping session IDs to message lists
            aggregation: 'day', 'week', or 'month' (default: 'week')
        
        Returns:
            Dictionary with structure: {time_period: {version: {method: count}}}
        """
        from datetime import datetime, timedelta
        from collections import defaultdict
        
        # Initialize data structure
        volume_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        session_mapping = {}  # {time_key: {version: {method: [session_ids]}}}
        
        # Process each session
        for session in sessions:
            session_id = session.get('id')
            session_messages = messages_data.get(session_id, [])
            
            # Skip split sessions and test sessions
            if self.should_exclude_session(session, session_messages):
                continue
            
            # Skip non-refrigerator sessions if filter is enabled
            if refrigerator_only and not self.has_refrigerator_example_tag(session, session_messages):
                continue
            
            # Get session created_at date
            created_at_str = session.get('created_at', '')
            if not created_at_str:
                continue
            
            try:
                # Parse ISO format date
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                continue
            
            # Determine time period based on aggregation
            if aggregation == 'day':
                time_key = created_at.strftime('%Y-%m-%d')
            elif aggregation == 'week':
                # Get the Monday of the week (ISO week)
                monday = created_at - timedelta(days=created_at.weekday())
                time_key = monday.strftime('%Y-%m-%d')
            elif aggregation == 'month':
                time_key = created_at.strftime('%Y-%m')
            else:
                time_key = created_at.strftime('%Y-%m-%d')
            
            # Detect coaching method
            detected_method = self.detect_coaching_method(session, session_messages)
            
            # Determine version
            version = None
            for version_name, version_config in self.coaching_bot_versions.items():
                if self.matches_version(session, version_config, session_messages):
                    if 'Control' in version_name:
                        version = 'Control'
                    elif 'V3' in version_name:
                        version = 'V3'
                    elif 'V4' in version_name:
                        version = 'V4'
                    elif 'V5' in version_name:
                        version = 'V5'
                    elif 'V6' in version_name:
                        version = 'V6'
                    break
            
            if not version:
                continue
            
            # For Control bot, use 'Unknown' method if no method detected
            if version == 'Control' and not detected_method:
                detected_method = 'Unknown'
            
            # Increment count
            volume_data[time_key][version][detected_method] += 1
            
            # Track which session contributes to this count (for filtering)
            if return_session_mapping:
                if time_key not in session_mapping:
                    session_mapping[time_key] = {}
                if version not in session_mapping[time_key]:
                    session_mapping[time_key][version] = {}
                if detected_method not in session_mapping[time_key][version]:
                    session_mapping[time_key][version][detected_method] = []
                session_mapping[time_key][version][detected_method].append(session_id)
        
        # Convert to regular dict for JSON serialization
        result = {}
        for time_key in sorted(volume_data.keys()):
            result[time_key] = {}
            for version in ['Control', 'V3', 'V4', 'V5', 'V6']:
                result[time_key][version] = {}
                for method in ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']:
                    result[time_key][version][method] = volume_data[time_key][version][method]
        
        if return_session_mapping:
            # Convert session_mapping defaultdict to regular dict for JSON serialization
            session_mapping_dict = {}
            for time_key in sorted(session_mapping.keys()):
                session_mapping_dict[time_key] = {}
                for version in session_mapping[time_key]:
                    session_mapping_dict[time_key][version] = {}
                    for method in session_mapping[time_key][version]:
                        session_mapping_dict[time_key][version][method] = list(session_mapping[time_key][version][method])
            return result, session_mapping_dict
        return result
    
    def calculate_volume_summary(self, volume_data: Dict) -> Dict:
        """
        Calculate total session counts by method and version across all time periods.
        
        Args:
            volume_data: Dictionary with structure: {time_period: {version: {method: count}}}
        
        Returns:
            Dictionary with structure: {version: {method: total_count}}
        """
        summary = {}
        versions = ['Control', 'V3', 'V4', 'V5', 'V6']
        methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        
        # Initialize structure
        for version in versions:
            summary[version] = {}
            for method in methods:
                summary[version][method] = 0
        
        # Aggregate counts across all time periods
        for time_period, period_data in volume_data.items():
            for version in versions:
                if version in period_data:
                    for method in methods:
                        if method in period_data[version]:
                            summary[version][method] += period_data[version][method]
        
        return summary
    
    def generate_volume_summary_table_rows(self, volume_summary: Dict, metrics: List[Dict]) -> str:
        """Generate table rows for session volume summary by method and version"""
        methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        versions = ['Control', 'V3', 'V4', 'V5', 'V6']
        
        # Store values for global calculation
        global_values = [[] for _ in metrics]
        all_versions_values = []  # For "All Versions" column
        
        rows = ""
        for method in methods:
            row = f"<tr><td><strong>{method}</strong></td>"
            method_all_versions = []  # Collect values across all versions for this method
            
            # Map version names from metrics to version keys
            for idx, metric in enumerate(metrics):
                version_name = metric.get('version_name', '')
                version_key = None
                
                if version_name == 'Control bot':
                    version_key = 'Control'
                elif 'V3' in version_name:
                    version_key = 'V3'
                elif 'V4' in version_name:
                    version_key = 'V4'
                elif 'V5' in version_name:
                    version_key = 'V5'
                elif 'V6' in version_name:
                    version_key = 'V6'
                
                if version_key and version_key in volume_summary:
                    count = volume_summary[version_key].get(method, 0)
                    if count > 0:
                        row += f"<td>{count}</td>"
                        global_values[idx].append(count)
                        method_all_versions.append(count)
                    else:
                        row += f"<td>-</td>"
                else:
                    row += f"<td>-</td>"
            
            # Add "All Versions" column for this method
            if method_all_versions:
                all_versions_total = sum(method_all_versions)
                row += f"<td style='font-weight: bold;'>{all_versions_total}</td>"
                all_versions_values.append(all_versions_total)
            else:
                row += "<td>-</td>"
                all_versions_values.append(0)
            
            row += "</tr>"
            rows += row
        
        # Add Total row
        total_row = '<tr style="background-color: #f8f9fa;"><td><strong>Total (All Methods)</strong></td>'
        for idx, values in enumerate(global_values):
            if values:
                total_sum = sum(values)
                total_row += f"<td style='font-weight: bold;'>{total_sum}</td>"
            else:
                total_row += "<td>-</td>"
        
        # Add "All Versions" column for Total row
        if all_versions_values:
            total_all_versions = sum([v for v in all_versions_values if v > 0])
            if total_all_versions > 0:
                total_row += f"<td style='font-weight: bold;'>{total_all_versions}</td>"
            else:
                total_row += "<td>-</td>"
        else:
            total_row += "<td>-</td>"
        
        total_row += "</tr>"
        rows += total_row
        
        return rows

    def generate_median_words_table_rows(self, metrics: List[Dict]) -> str:
        """Generate table rows for median words by method and version"""
        # Get all unique methods across all versions
        all_methods = set()
        for metric in metrics:
            median_words = metric.get('median_words_by_method', {})
            all_methods.update(median_words.keys())
        
        # Sort methods for consistent display
        method_order = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        sorted_methods = [method for method in method_order if method in all_methods]
        sorted_methods.extend([method for method in all_methods if method not in method_order])
        
        # Store values for global calculation (per version and across all versions)
        global_values = [[] for _ in metrics]
        all_versions_values = []  # For "All Versions" column
        
        rows = ""
        for method in sorted_methods:
            row = f"<tr><td><strong>{method}</strong></td>"
            method_all_versions = []  # Collect values across all versions for this method
            
            for idx, metric in enumerate(metrics):
                version_name = metric.get('version_name', '')
                median_words = metric.get('median_words_by_method', {})
                method_data = median_words.get(method, {})
                
                # Special handling for Control bot
                if version_name == 'Control bot':
                    if method == 'Unknown':
                        # Show Control bot data only under Unknown
                        if isinstance(method_data, dict):
                            control_words = method_data.get('Control', 0.0)
                        else:
                            control_words = method_data if isinstance(method_data, (int, float)) else 0.0
                        if control_words > 0:
                            row += f"<td>{control_words:.1f}</td>"
                            global_values[idx].append(control_words)
                            method_all_versions.append(control_words)
                        else:
                            row += f"<td>0.0</td>"
                    else:
                        # Show hyphen for specific coaching methods
                        row += f"<td>-</td>"
                else:
                    # Regular handling for coaching bots
                    if isinstance(method_data, dict):
                        # Get the value for this version
                        version_key = version_name.replace('Coaching bot ', '')
                        words = method_data.get(version_key, 0.0)
                    else:
                        words = method_data if isinstance(method_data, (int, float)) else 0.0
                    
                    if words > 0:
                        row += f"<td>{words:.1f}</td>"
                        global_values[idx].append(words)
                        method_all_versions.append(words)
                    else:
                        row += f"<td>-</td>"
            
            # Add "All Versions" column for this method
            if method_all_versions:
                method_all_versions_sorted = sorted(method_all_versions)
                n = len(method_all_versions_sorted)
                if n % 2 == 0:
                    all_versions_median = (method_all_versions_sorted[n//2 - 1] + method_all_versions_sorted[n//2]) / 2
                else:
                    all_versions_median = method_all_versions_sorted[n//2]
                row += f"<td style='font-weight: bold;'>{all_versions_median:.1f}</td>"
                all_versions_values.append(all_versions_median)
            else:
                row += "<td>-</td>"
                all_versions_values.append(0)
            
            row += "</tr>"
            rows += row
        
        # Add Total row
        total_row = '<tr style="background-color: #f8f9fa;"><td><strong>Total (All Methods)</strong></td>'
        for idx, values in enumerate(global_values):
            if values:
                values_sorted = sorted(values)
                n = len(values_sorted)
                if n % 2 == 0:
                    global_median = (values_sorted[n//2 - 1] + values_sorted[n//2]) / 2
                else:
                    global_median = values_sorted[n//2]
                total_row += f"<td style='font-weight: bold;'>{global_median:.1f}</td>"
            else:
                total_row += "<td>-</td>"
        
        # Add "All Versions" column for Total row
        if all_versions_values:
            all_versions_sorted = sorted([v for v in all_versions_values if v > 0])
            if all_versions_sorted:
                n = len(all_versions_sorted)
                if n % 2 == 0:
                    total_all_versions = (all_versions_sorted[n//2 - 1] + all_versions_sorted[n//2]) / 2
                else:
                    total_all_versions = all_versions_sorted[n//2]
                total_row += f"<td style='font-weight: bold;'>{total_all_versions:.1f}</td>"
            else:
                total_row += "<td>-</td>"
        else:
            total_row += "<td>-</td>"
        
        total_row += "</tr>"
        rows += total_row
        
        return rows

    def generate_median_messages_table_rows(self, metrics: List[Dict]) -> str:
        """Generate table rows for median messages by method and version"""
        # Get all unique methods across all versions
        all_methods = set()
        for metric in metrics:
            median_messages_data = metric.get('median_messages_by_method', {})
            all_methods.update(median_messages_data.keys())

        # Sort methods for consistent display
        method_order = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        sorted_methods = [method for method in method_order if method in all_methods]
        sorted_methods.extend([method for method in all_methods if method not in method_order])

        # Store values for global calculation (per version and across all versions)
        global_values = [[] for _ in metrics]
        all_versions_values = []  # For "All Versions" column

        rows = ""
        for method in sorted_methods:
            row = f"<tr><td><strong>{method}</strong></td>"
            method_all_versions = []  # Collect values across all versions for this method
            
            for idx, metric in enumerate(metrics):
                version_name = metric.get('version_name', '')
                median_messages_data = metric.get('median_messages_by_method', {})
                method_messages = median_messages_data.get(method, 0.0)
                
                # Special handling for Control bot
                if version_name == 'Control bot':
                    if method == 'Unknown':
                        # Show Control bot data only under Unknown
                        if isinstance(method_messages, dict):
                            control_messages = method_messages.get('Control', 0.0)
                            if control_messages > 0:
                                row += f"<td>{control_messages:.1f}</td>"
                                global_values[idx].append(control_messages)
                                method_all_versions.append(control_messages)
                            else:
                                row += f"<td>0.0</td>"
                        else:
                            if method_messages > 0:
                                row += f"<td>{method_messages:.1f}</td>"
                                global_values[idx].append(method_messages)
                                method_all_versions.append(method_messages)
                            else:
                                row += f"<td>0.0</td>"
                    else:
                        # Show hyphen for specific coaching methods
                        row += f"<td>-</td>"
                else:
                    # Regular handling for coaching bots
                    if isinstance(method_messages, dict):
                        # Get the value for this version
                        version_key = version_name.replace('Coaching bot ', '')
                        messages = method_messages.get(version_key, 0.0)
                    else:
                        messages = method_messages if isinstance(method_messages, (int, float)) else 0.0
                    
                    if messages > 0:
                        row += f"<td>{messages:.1f}</td>"
                        global_values[idx].append(messages)
                        method_all_versions.append(messages)
                    else:
                        row += f"<td>-</td>"
            
            # Add "All Versions" column for this method
            if method_all_versions:
                method_all_versions_sorted = sorted(method_all_versions)
                n = len(method_all_versions_sorted)
                if n % 2 == 0:
                    all_versions_median = (method_all_versions_sorted[n//2 - 1] + method_all_versions_sorted[n//2]) / 2
                else:
                    all_versions_median = method_all_versions_sorted[n//2]
                row += f"<td style='font-weight: bold;'>{all_versions_median:.1f}</td>"
                all_versions_values.append(all_versions_median)
            else:
                row += "<td>-</td>"
                all_versions_values.append(0)
            
            row += "</tr>"
            rows += row

        # Add Total row
        total_row = '<tr style="background-color: #f8f9fa;"><td><strong>Total (All Methods)</strong></td>'
        for idx, values in enumerate(global_values):
            if values:
                values_sorted = sorted(values)
                n = len(values_sorted)
                if n % 2 == 0:
                    global_median = (values_sorted[n//2 - 1] + values_sorted[n//2]) / 2
                else:
                    global_median = values_sorted[n//2]
                total_row += f"<td style='font-weight: bold;'>{global_median:.1f}</td>"
            else:
                total_row += "<td>-</td>"
        
        # Add "All Versions" column for Total row
        if all_versions_values:
            all_versions_sorted = sorted([v for v in all_versions_values if v > 0])
            if all_versions_sorted:
                n = len(all_versions_sorted)
                if n % 2 == 0:
                    total_all_versions = (all_versions_sorted[n//2 - 1] + all_versions_sorted[n//2]) / 2
                else:
                    total_all_versions = all_versions_sorted[n//2]
                total_row += f"<td style='font-weight: bold;'>{total_all_versions:.1f}</td>"
            else:
                total_row += "<td>-</td>"
        else:
            total_row += "<td>-</td>"
        
        total_row += "</tr>"
        rows += total_row

        return rows

    def generate_rating_table_rows(self, metrics: List[Dict]) -> str:
        """Generate table rows for average ratings by method and version"""
        # Get all unique methods across all versions
        all_methods = set()
        for metric in metrics:
            rating_data = metric.get('average_rating_by_method', {})
            all_methods.update(rating_data.keys())
        
        # Sort methods for consistent display
        method_order = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        sorted_methods = [method for method in method_order if method in all_methods]
        sorted_methods.extend([method for method in all_methods if method not in method_order])
        
        # Store values for global calculation
        global_values = [[] for _ in metrics]
        all_versions_values = []  # For "All Versions" column
        
        rows = ""
        for method in sorted_methods:
            row = f"<tr><td><strong>{method}</strong></td>"
            method_all_versions = []  # Collect values across all versions for this method
            
            for idx, metric in enumerate(metrics):
                version_name = metric.get('version_name', '')
                rating_data = metric.get('average_rating_by_method', {})
                method_rating = rating_data.get(method, 0.0)
                
                # Special handling for Control bot
                if version_name == 'Control bot':
                    if method == 'Unknown':
                        # Show Control bot rating under Unknown method
                        if isinstance(method_rating, dict):
                            control_rating = method_rating.get('Control', 0.0)
                        else:
                            control_rating = method_rating if isinstance(method_rating, (int, float)) else 0.0
                        if control_rating > 0:
                            row += f"<td>{control_rating:.2f}</td>"
                            global_values[idx].append(control_rating)
                            method_all_versions.append(control_rating)
                        else:
                            row += f"<td>-</td>"
                    else:
                        # Show hyphen for specific coaching methods
                        row += f"<td>-</td>"
                else:
                    # Regular handling for coaching bots
                    if isinstance(method_rating, dict):
                        # Get the average across all versions for this method
                        version_ratings = [rating for rating in method_rating.values() if rating > 0]
                        if version_ratings:
                            method_rating = sum(version_ratings) / len(version_ratings)
                        else:
                            method_rating = 0.0
                    
                    if method_rating and method_rating > 0:
                        row += f"<td>{method_rating:.2f}</td>"
                        global_values[idx].append(method_rating)
                        method_all_versions.append(method_rating)
                    else:
                        row += f"<td>-</td>"
            
            # Add "All Versions" column for this method
            if method_all_versions:
                all_versions_avg = sum(method_all_versions) / len(method_all_versions)
                row += f"<td style='font-weight: bold;'>{all_versions_avg:.2f}</td>"
                all_versions_values.append(all_versions_avg)
            else:
                row += "<td>-</td>"
                all_versions_values.append(0)
            
            row += "</tr>"
            rows += row
        
        # Add Total row
        total_row = '<tr style="background-color: #f8f9fa;"><td><strong>Total (All Methods)</strong></td>'
        for idx, values in enumerate(global_values):
            if values:
                total_avg = sum(values) / len(values)
                total_row += f"<td style='font-weight: bold;'>{total_avg:.2f}</td>"
            else:
                total_row += "<td>-</td>"
        
        # Add "All Versions" column for Total row
        if all_versions_values:
            all_versions_filtered = [v for v in all_versions_values if v > 0]
            if all_versions_filtered:
                total_all_versions = sum(all_versions_filtered) / len(all_versions_filtered)
                total_row += f"<td style='font-weight: bold;'>{total_all_versions:.2f}</td>"
            else:
                total_row += "<td>-</td>"
        else:
            total_row += "<td>-</td>"
        
        total_row += "</tr>"
        rows += total_row
        
        return rows
    
    def generate_method_table_rows(self, metrics: List[Dict], calculation_mode: str = 'annotated') -> str:
        """Generate table rows for refrigerator rate by method with data attributes for both modes
        
        Args:
            metrics: List of metric dictionaries
            calculation_mode: 'annotated' or 'explicit' (default display mode)
        """
        # Get all unique methods across all versions
        all_methods = set()
        for metric in metrics:
            method_rates = metric.get('method_refrigerator_rates', {})
            all_methods.update(method_rates.keys())
        
        # Sort methods for consistent display
        method_order = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        sorted_methods = [method for method in method_order if method in all_methods]
        sorted_methods.extend([method for method in all_methods if method not in method_order])
        
        # Store values for global calculation for both modes
        global_values_annotated = [[] for _ in metrics]
        global_values_explicit = [[] for _ in metrics]
        all_versions_values_annotated = []
        all_versions_values_explicit = []
        
        rows = ""
        for method in sorted_methods:
            row = f"<tr><td><strong>{method}</strong></td>"
            method_all_versions_annotated = []
            method_all_versions_explicit = []
            
            for idx, metric in enumerate(metrics):
                method_rates = metric.get('method_refrigerator_rates', {})
                method_data = method_rates.get(method, {})
                
                # Extract both rates
                if isinstance(method_data, dict):
                    rate_annotated = method_data.get('annotated', 0.0)
                    rate_explicit = method_data.get('explicit', 0.0)
                else:
                    # Backward compatibility: if it's a float, use it for both
                    rate_annotated = method_data if isinstance(method_data, (int, float)) else 0.0
                    rate_explicit = rate_annotated
                
                # Display the selected mode
                display_rate = rate_annotated if calculation_mode == 'annotated' else rate_explicit
                
                if display_rate and display_rate > 0:
                    row += f"<td data-mode-annotated=\"{rate_annotated:.1f}\" data-mode-explicit=\"{rate_explicit:.1f}\">{display_rate:.1f}%</td>"
                    global_values_annotated[idx].append(rate_annotated)
                    global_values_explicit[idx].append(rate_explicit)
                    method_all_versions_annotated.append(rate_annotated)
                    method_all_versions_explicit.append(rate_explicit)
                else:
                    row += f"<td data-mode-annotated=\"-\" data-mode-explicit=\"-\">-</td>"
            
            # Add "All Versions" column for this method
            if method_all_versions_annotated:
                all_versions_avg_annotated = sum(method_all_versions_annotated) / len(method_all_versions_annotated)
                all_versions_avg_explicit = sum(method_all_versions_explicit) / len(method_all_versions_explicit) if method_all_versions_explicit else 0.0
                display_avg = all_versions_avg_annotated if calculation_mode == 'annotated' else all_versions_avg_explicit
                row += f"<td style='font-weight: bold;' data-mode-annotated=\"{all_versions_avg_annotated:.1f}\" data-mode-explicit=\"{all_versions_avg_explicit:.1f}\">{display_avg:.1f}%</td>"
                all_versions_values_annotated.append(all_versions_avg_annotated)
                all_versions_values_explicit.append(all_versions_avg_explicit)
            else:
                row += "<td data-mode-annotated=\"-\" data-mode-explicit=\"-\">-</td>"
                all_versions_values_annotated.append(0)
                all_versions_values_explicit.append(0)
            
            row += "</tr>"
            rows += row
        
        # Add Total row
        total_row = '<tr style="background-color: #f8f9fa;"><td><strong>Total (All Methods)</strong></td>'
        for idx in range(len(metrics)):
            values_annotated = global_values_annotated[idx]
            values_explicit = global_values_explicit[idx]
            
            if values_annotated:
                total_avg_annotated = sum(values_annotated) / len(values_annotated)
                total_avg_explicit = sum(values_explicit) / len(values_explicit) if values_explicit else 0.0
                display_total = total_avg_annotated if calculation_mode == 'annotated' else total_avg_explicit
                total_row += f"<td style='font-weight: bold;' data-mode-annotated=\"{total_avg_annotated:.1f}\" data-mode-explicit=\"{total_avg_explicit:.1f}\">{display_total:.1f}%</td>"
            else:
                total_row += "<td data-mode-annotated=\"-\" data-mode-explicit=\"-\">-</td>"
        
        # Add "All Versions" column for Total row
        if all_versions_values_annotated:
            all_versions_filtered_annotated = [v for v in all_versions_values_annotated if v > 0]
            all_versions_filtered_explicit = [v for v in all_versions_values_explicit if v > 0]
            
            if all_versions_filtered_annotated:
                total_all_versions_annotated = sum(all_versions_filtered_annotated) / len(all_versions_filtered_annotated)
                total_all_versions_explicit = sum(all_versions_filtered_explicit) / len(all_versions_filtered_explicit) if all_versions_filtered_explicit else 0.0
                display_total_all = total_all_versions_annotated if calculation_mode == 'annotated' else total_all_versions_explicit
                total_row += f"<td style='font-weight: bold;' data-mode-annotated=\"{total_all_versions_annotated:.1f}\" data-mode-explicit=\"{total_all_versions_explicit:.1f}\">{display_total_all:.1f}%</td>"
            else:
                total_row += "<td data-mode-annotated=\"-\" data-mode-explicit=\"-\">-</td>"
        else:
            total_row += "<td data-mode-annotated=\"-\" data-mode-explicit=\"-\">-</td>"
        
        total_row += "</tr>"
        rows += total_row
        
        return rows
    
    def calculate_median_human_words(self, sessions: List[Dict], messages_data: Dict) -> float:
        """Calculate median human words per session"""
        session_word_counts = []
        
        for session in sessions:
            session_id = session.get('id')
            if session_id in messages_data:
                messages = messages_data[session_id]
                total_user_words = 0
                for message in messages:
                    if message.get('role') == 'user':
                        content = message.get('content', '')
                        total_user_words += len(content.split())
                session_word_counts.append(total_user_words)
        
        if not session_word_counts:
            return 0.0
        
        return statistics.median(session_word_counts)
    
    def extract_session_rating(self, session: Dict, messages: List[Dict]) -> Optional[float]:
        """Extract session rating from messages using comprehensive pattern matching"""
        if not messages:
            return None
        
        # Look for rating questions in assistant messages (from end to start)
        rating_question_found = False
        for message in reversed(messages):
            if message.get('role') == 'assistant':
                content = message.get('content', '').lower()
                
                # Check for comprehensive rating question patterns
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
        
        # Look for user rating responses (from end to start)
        for message in reversed(messages):
            if message.get('role') == 'user':
                content = message.get('content', '').strip()
                
                # Single digit rating
                if re.match(r'^\s*[1-5]\s*$', content):
                    return float(content.strip())
                
                # Written number rating
                written_numbers = {
                    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5
                }
                content_lower = content.lower()
                if content_lower in written_numbers:
                    return float(written_numbers[content_lower])
                
                # Rating with context (e.g., "5= extremely useful")
                rating_match = re.search(r'\b([1-5])\b', content)
                if rating_match and len(content) < 100:  # Short responses more likely to be ratings
                    return float(rating_match.group(1))
        
        return None
    
    def extract_today_yesterday_preference(self, session: Dict, messages: List[Dict]) -> Optional[str]:
        """Extract today/yesterday preference from messages"""
        if not messages:
            return None
        
        # Look for today/yesterday question in assistant messages (from end to start)
        # Check all messages but prioritize the last ones (feedback questions typically at end)
        question_found = False
        question_message_index = -1
        
        # Check all messages, starting from the end
        messages_to_check = list(reversed(messages))
        
        for idx, message in enumerate(messages_to_check):
            if message.get('role') == 'assistant':
                content = message.get('content', '').lower()
                original_content = message.get('content', '')
                
                # Check for today/yesterday question patterns - more flexible
                # Look for "today" and ("yesterday" OR "last one"/"your last one") in the same message
                has_today = 'today' in content or "today's" in content
                has_yesterday = 'yesterday' in content or "yesterday's" in content
                has_last_one = 'last one' in content or 'your last one' in content or 'your last' in content
                
                if has_today and (has_yesterday or has_last_one):
                    # Exclude system prompts/instructions (usually very long or contain "Guide a conversation")
                    if len(original_content) > 1000 or 'guide a conversation' in content:
                        continue
                    
                    # Check if it's asking a question - be more lenient
                    # If it contains both today and yesterday, and has question indicators OR ends with ?
                    question_indicators = [
                        'which', 'what', 'do you', 'did you', 'would you', 
                        'prefer', 'find', 'useful', 'better', 'question'
                    ]
                    has_question_marker = any(indicator in content for indicator in question_indicators)
                    ends_with_question = original_content.strip().endswith('?')
                    
                    if has_question_marker or ends_with_question:
                        question_found = True
                        # Calculate actual index in full messages list
                        question_message_index = len(messages) - 1 - idx
                        break
        
        if not question_found:
            return None
        
        # Look for user responses (from end to start, after the question)
        # Check first 5 user messages after the question
        user_messages_checked = 0
        for message in messages[question_message_index + 1:]:
            if message.get('role') == 'user':
                user_messages_checked += 1
                if user_messages_checked > 5:  # Check first 5 user responses
                    break
                
                content = message.get('content', '').strip().lower()
                original_content = message.get('content', '').strip()
                
                # Skip very long responses (> 500 chars) - likely just explanations
                if len(original_content) > 500:
                    continue
                
                # Check for "both" response first - valid answer
                if re.search(r'^\s*both\s*$', content) or (re.search(r'\bboth\b', content) and len(original_content) < 15):
                    return 'both'
                
                # Simple detection: if response contains "today" (and not "yesterday"/"last"), it's "today"
                # If response contains "yesterday" or "last" (and not "today"), it's "yesterday"
                has_today = re.search(r'\btoday\'?s?\b', content)
                has_yesterday = re.search(r'\byesterday\'?s?\b', content)
                has_last = (re.search(r'\blast\s+(one|session)?\b', content) or 
                           'your last' in content or 
                           'the last' in content or
                           re.search(r'\bprevious\b', content))
                
                # "today" response (not yesterday or last)
                if has_today and not has_yesterday and not has_last:
                    return 'today'
                
                # "yesterday" or "last" response (not today)
                if (has_yesterday or has_last) and not has_today:
                    return 'yesterday'
        
        return None
    
    def calculate_today_yesterday_tendency_by_version_and_method(self, sessions: List[Dict], messages_data: Dict) -> Dict:
        """Calculate today/yesterday preference tendency by version and method"""
        methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        
        # Structure: {version: {method: {'today': count, 'yesterday': count, 'both': count, 'total': count}}}
        tendency_data = defaultdict(lambda: defaultdict(lambda: {'today': 0, 'yesterday': 0, 'both': 0, 'total': 0}))
        
        # Also track statistics
        stats = defaultdict(lambda: defaultdict(lambda: {
            'sessions_with_question': 0,
            'sessions_with_response': 0
        }))
        
        for session in sessions:
            session_id = session.get('id')
            if not session_id:
                continue
            
            messages = messages_data.get(session_id, [])
            
            # Skip split sessions and test sessions
            if self.should_exclude_session(session, messages):
                continue
            
            # Determine version
            version = None
            for version_name, version_config in self.coaching_bot_versions.items():
                if self.matches_version(session, version_config, messages):
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
            
            if not version:
                continue
            
            # Determine coaching method
            method = self.detect_coaching_method(session, messages)
            
            # Check if question was asked - look for today/yesterday or today/last one question
            question_found = False
            for message in reversed(messages):
                if message.get('role') == 'assistant':
                    content = message.get('content', '').lower()
                    original_content = message.get('content', '')
                    
                    # Exclude system prompts
                    if len(original_content) > 1000 or 'guide a conversation' in content:
                        continue
                    
                    # Look for today with yesterday or last one
                    has_today = 'today' in content or "today's" in content
                    has_yesterday = 'yesterday' in content or "yesterday's" in content
                    has_last_one = 'last one' in content or 'your last' in content
                    
                    if has_today and (has_yesterday or has_last_one):
                        question_indicators = [
                            'which', 'what', 'do you', 'did you', 'would you', 
                            'prefer', 'find', 'useful', 'better', 'question', 'most useful'
                        ]
                        has_question_marker = any(indicator in content for indicator in question_indicators)
                        ends_with_question = original_content.strip().endswith('?')
                        
                        if has_question_marker or ends_with_question:
                            question_found = True
                            break
            
            if question_found:
                stats[version][method]['sessions_with_question'] += 1
                
                # Extract preference
                preference = self.extract_today_yesterday_preference(session, messages)
                if preference:
                    tendency_data[version][method][preference] += 1
                    tendency_data[version][method]['total'] += 1
                    stats[version][method]['sessions_with_response'] += 1
        
        # Calculate tendency (more today = 'today', more yesterday = 'yesterday', tie = 'tie')
        # Note: 'both' responses are counted in total but don't affect tendency calculation
        result = {}
        for version, method_data in tendency_data.items():
            result[version] = {}
            for method, counts in method_data.items():
                today_count = counts['today']
                yesterday_count = counts['yesterday']
                both_count = counts.get('both', 0)
                total = counts['total']
                
                # Tendency is calculated only from today vs yesterday (both is excluded from tendency)
                preference_total = today_count + yesterday_count
                
                if preference_total == 0:
                    tendency = None
                elif today_count > yesterday_count:
                    tendency = 'today'
                elif yesterday_count > today_count:
                    tendency = 'yesterday'
                else:
                    tendency = 'tie'
                
                result[version][method] = {
                    'tendency': tendency,
                    'today_count': today_count,
                    'yesterday_count': yesterday_count,
                    'both_count': both_count,
                    'total': total
                }
        
        # Add statistics
        result['_stats'] = dict(stats)
        
        return dict(result)
    
    def generate_today_yesterday_table_rows(self, tendency_data: Dict, metrics: List[Dict]) -> str:
        """Generate HTML rows for today/yesterday tendency table"""
        if not tendency_data or '_stats' not in tendency_data:
            return "<tr><td colspan='6' class='text-center'>No data available</td></tr>"
        
        methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        stats = tendency_data.get('_stats', {})
        
        rows = ""
        
        for method in methods:
            row = f"<tr><td><strong>{method}</strong></td>"
            
            for metric in metrics:
                version_name = metric['version_name']
                method_data = tendency_data.get(version_name, {}).get(method, {})
                tendency = method_data.get('tendency')
                
                if tendency is None:
                    row += "<td>-</td>"
                elif tendency == 'today':
                    row += '<td style="text-align: center;"><span style="color: green; font-size: 1.5em;">→</span></td>'
                elif tendency == 'yesterday':
                    row += '<td style="text-align: center;"><span style="color: red; font-size: 1.5em;">←</span></td>'
                else:  # tie
                    row += '<td style="text-align: center;"><span style="color: orange; font-size: 1.5em;">↔</span></td>'
            
            # Calculate "All Versions" tendency
            all_versions_today = 0
            all_versions_yesterday = 0
            for metric in metrics:
                version_name = metric['version_name']
                method_data = tendency_data.get(version_name, {}).get(method, {})
                all_versions_today += method_data.get('today_count', 0)
                all_versions_yesterday += method_data.get('yesterday_count', 0)
            
            if all_versions_today + all_versions_yesterday == 0:
                row += "<td>-</td>"
            elif all_versions_today > all_versions_yesterday:
                row += '<td style="text-align: center; font-weight: bold;"><span style="color: green; font-size: 1.5em;">→</span></td>'
            elif all_versions_yesterday > all_versions_today:
                row += '<td style="text-align: center; font-weight: bold;"><span style="color: red; font-size: 1.5em;">←</span></td>'
            else:
                row += '<td style="text-align: center; font-weight: bold;"><span style="color: orange; font-size: 1.5em;">↔</span></td>'
            
            row += "</tr>"
            rows += row
        
        # Add Total row
        total_row = "<tr style='background-color: #f8f9fa;'><td><strong>Total (All Methods)</strong></td>"
        
        for metric in metrics:
            version_name = metric['version_name']
            total_today = 0
            total_yesterday = 0
            
            for method in methods:
                method_data = tendency_data.get(version_name, {}).get(method, {})
                total_today += method_data.get('today_count', 0)
                total_yesterday += method_data.get('yesterday_count', 0)
            
            if total_today + total_yesterday == 0:
                total_row += "<td>-</td>"
            elif total_today > total_yesterday:
                total_row += '<td style="text-align: center; font-weight: bold;"><span style="color: green; font-size: 1.5em;">→</span></td>'
            elif total_yesterday > total_today:
                total_row += '<td style="text-align: center; font-weight: bold;"><span style="color: red; font-size: 1.5em;">←</span></td>'
            else:
                total_row += '<td style="text-align: center; font-weight: bold;"><span style="color: orange; font-size: 1.5em;">↔</span></td>'
        
        # All Versions total
        all_versions_total_today = 0
        all_versions_total_yesterday = 0
        for metric in metrics:
            version_name = metric['version_name']
            for method in methods:
                method_data = tendency_data.get(version_name, {}).get(method, {})
                all_versions_total_today += method_data.get('today_count', 0)
                all_versions_total_yesterday += method_data.get('yesterday_count', 0)
        
        if all_versions_total_today + all_versions_total_yesterday == 0:
            total_row += "<td>-</td>"
        elif all_versions_total_today > all_versions_total_yesterday:
            total_row += '<td style="text-align: center; font-weight: bold;"><span style="color: green; font-size: 1.5em;">→</span></td>'
        elif all_versions_total_yesterday > all_versions_total_today:
            total_row += '<td style="text-align: center; font-weight: bold;"><span style="color: red; font-size: 1.5em;">←</span></td>'
        else:
            total_row += '<td style="text-align: center; font-weight: bold;"><span style="color: orange; font-size: 1.5em;">↔</span></td>'
        
        total_row += "</tr>"
        rows += total_row
        
        return rows
    
    def generate_today_yesterday_statistics(self, tendency_data: Dict, metrics: List[Dict]) -> str:
        """Generate statistics for today/yesterday preference collection"""
        if not tendency_data or '_stats' not in tendency_data:
            return ""
        
        stats = tendency_data.get('_stats', {})
        methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        
        # Calculate overall statistics
        total_sessions_with_question = 0
        total_sessions_with_response = 0
        
        for metric in metrics:
            version_name = metric['version_name']
            version_stats = stats.get(version_name, {})
            for method in methods:
                method_stats = version_stats.get(method, {})
                total_sessions_with_question += method_stats.get('sessions_with_question', 0)
                total_sessions_with_response += method_stats.get('sessions_with_response', 0)
        
        response_percentage = (total_sessions_with_response / total_sessions_with_question * 100) if total_sessions_with_question > 0 else 0
        
        # Calculate today, yesterday, and "both" responses counts
        total_today_responses = 0
        total_yesterday_responses = 0
        total_both_responses = 0
        for metric in metrics:
            version_name = metric['version_name']
            version_data = tendency_data.get(version_name, {})
            for method in methods:
                method_data = version_data.get(method, {})
                total_today_responses += method_data.get('today_count', 0)
                total_yesterday_responses += method_data.get('yesterday_count', 0)
                total_both_responses += method_data.get('both_count', 0)
        
        stats_text = f"""
        <div class="mt-3">
            <small class="text-muted">
                <strong>Today/Yesterday Preference Collection Statistics:</strong><br>
                • Today/Yesterday Questions: {total_sessions_with_question} sessions contain today/yesterday preference questions<br>
                • Valid Responses: {total_sessions_with_response} sessions ({response_percentage:.1f}% of sessions with question) have extractable preferences<br>
                &nbsp;&nbsp;&nbsp;&nbsp;- "Today" Responses: {total_today_responses} sessions<br>
                &nbsp;&nbsp;&nbsp;&nbsp;- "Yesterday/Last One" Responses: {total_yesterday_responses} sessions<br>
                • "Both" Responses: {total_both_responses} sessions indicated both sessions were equally useful (not included in tendency calculation)
            </small>
        </div>
        """
        
        return stats_text
    
    def calculate_average_rating_by_preference(self, sessions: List[Dict], messages_data: Dict, preference: str) -> Dict:
        """Calculate average session rating for sessions where user responded 'today' or 'yesterday'"""
        methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        
        # Structure: {version: {method: {'ratings': [list], 'count': count, 'average': float}}}
        rating_data = defaultdict(lambda: defaultdict(lambda: {'ratings': [], 'count': 0, 'average': None}))
        
        for session in sessions:
            session_id = session.get('id')
            if not session_id:
                continue
            
            messages = messages_data.get(session_id, [])
            
            # Skip split sessions and test sessions
            if self.should_exclude_session(session, messages):
                continue
            
            # Extract preference
            session_preference = self.extract_today_yesterday_preference(session, messages)
            if session_preference != preference:
                continue
            
            # Extract rating
            rating = self.extract_session_rating(session, messages)
            if rating is None:
                continue
            
            # Determine version
            version = None
            for version_name, version_config in self.coaching_bot_versions.items():
                if self.matches_version(session, version_config, messages):
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
            
            if not version:
                continue
            
            # Determine coaching method
            method = self.detect_coaching_method(session, messages)
            
            # Add rating
            rating_data[version][method]['ratings'].append(rating)
            rating_data[version][method]['count'] += 1
        
        # Calculate averages
        result = {}
        for version, method_data in rating_data.items():
            result[version] = {}
            for method, data in method_data.items():
                ratings = data['ratings']
                if ratings:
                    result[version][method] = {
                        'average': sum(ratings) / len(ratings),
                        'count': len(ratings)
                    }
                else:
                    result[version][method] = {
                        'average': None,
                        'count': 0
                    }
        
        return dict(result)
    
    def generate_average_rating_table_rows(self, rating_data: Dict, metrics: List[Dict], preference_label: str) -> str:
        """Generate HTML rows for average rating table by preference"""
        if not rating_data:
            return "<tr><td colspan='6' class='text-center'>No data available</td></tr>"
        
        methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        rows = ""
        
        for method in methods:
            row = f"<tr><td><strong>{method}</strong></td>"
            
            for metric in metrics:
                version_name = metric['version_name']
                method_data = rating_data.get(version_name, {}).get(method, {})
                average = method_data.get('average')
                count = method_data.get('count', 0)
                
                if average is None or count == 0:
                    row += "<td>-</td>"
                else:
                    row += f"<td style='text-align: center;'>{average:.2f} <small class='text-muted'>(n={count})</small></td>"
            
            # Calculate "All Versions" average
            all_versions_ratings = []
            all_versions_count = 0
            for metric in metrics:
                version_name = metric['version_name']
                method_data = rating_data.get(version_name, {}).get(method, {})
                count = method_data.get('count', 0)
                average = method_data.get('average')
                if average is not None and count > 0:
                    # Weight by count for overall average
                    all_versions_ratings.extend([average] * count)
                    all_versions_count += count
            
            if all_versions_count == 0:
                row += "<td>-</td>"
            else:
                overall_avg = sum(all_versions_ratings) / len(all_versions_ratings) if all_versions_ratings else None
                row += f"<td style='text-align: center; font-weight: bold;'>{overall_avg:.2f} <small class='text-muted'>(n={all_versions_count})</small></td>"
            
            row += "</tr>"
            rows += row
        
        # Add Total row
        total_row = "<tr style='background-color: #f8f9fa;'><td><strong>Total (All Methods)</strong></td>"
        
        for metric in metrics:
            version_name = metric['version_name']
            total_ratings = []
            total_count = 0
            
            for method in methods:
                method_data = rating_data.get(version_name, {}).get(method, {})
                count = method_data.get('count', 0)
                average = method_data.get('average')
                if average is not None and count > 0:
                    total_ratings.extend([average] * count)
                    total_count += count
            
            if total_count == 0:
                total_row += "<td>-</td>"
            else:
                overall_avg = sum(total_ratings) / len(total_ratings) if total_ratings else None
                total_row += f"<td style='text-align: center; font-weight: bold;'>{overall_avg:.2f} <small class='text-muted'>(n={total_count})</small></td>"
        
        # All Versions total
        all_versions_total_ratings = []
        all_versions_total_count = 0
        for metric in metrics:
            version_name = metric['version_name']
            for method in methods:
                method_data = rating_data.get(version_name, {}).get(method, {})
                count = method_data.get('count', 0)
                average = method_data.get('average')
                if average is not None and count > 0:
                    all_versions_total_ratings.extend([average] * count)
                    all_versions_total_count += count
        
        if all_versions_total_count == 0:
            total_row += "<td>-</td>"
        else:
            overall_avg = sum(all_versions_total_ratings) / len(all_versions_total_ratings) if all_versions_total_ratings else None
            total_row += f"<td style='text-align: center; font-weight: bold;'>{overall_avg:.2f} <small class='text-muted'>(n={all_versions_total_count})</small></td>"
        
        total_row += "</tr>"
        rows += total_row
        
        return rows
    
    def calculate_rating_statistics(self, sessions: List[Dict], messages_data: Dict) -> Dict:
        """Calculate comprehensive rating statistics"""
        # Filter out split sessions and test sessions
        valid_sessions = []
        for session in sessions:
            session_id = session.get('id')
            messages = messages_data.get(session_id, [])
            if not self.should_exclude_session(session, messages):
                valid_sessions.append(session)
        
        total_sessions = len(valid_sessions)
        sessions_with_rating_questions = 0
        sessions_with_ratings = 0
        
        for session in valid_sessions:
            session_id = session.get('id')
            messages = messages_data.get(session_id, [])
            
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
                sessions_with_rating_questions += 1
            
            # Check for actual rating
            rating = self.extract_session_rating(session, messages)
            if rating is not None:
                sessions_with_ratings += 1
        
        return {
            'total_sessions': total_sessions,
            'sessions_with_rating_questions': sessions_with_rating_questions,
            'sessions_with_ratings': sessions_with_ratings,
            'rating_question_percentage': (sessions_with_rating_questions / total_sessions * 100) if total_sessions > 0 else 0,
            'rating_extraction_percentage': (sessions_with_ratings / total_sessions * 100) if total_sessions > 0 else 0
        }
    
    def calculate_average_rating(self, sessions: List[Dict], messages_data: Dict) -> float:
        """Calculate average session rating"""
        ratings = []
        
        for session in sessions:
            session_id = session.get('id')
            if session_id in messages_data:
                rating = self.extract_session_rating(session, messages_data[session_id])
                if rating is not None:
                    ratings.append(rating)
        
        if not ratings:
            return 0.0
        
        return statistics.mean(ratings)
    
    def calculate_metrics_for_version(self, version_name: str, sessions: List[Dict], messages_data: Dict, refrigerator_only: bool = False) -> Dict:
        """Calculate metrics for a specific version"""
        # Filter out split sessions and test sessions
        valid_sessions = []
        for session in sessions:
            session_id = session.get('id')
            messages = messages_data.get(session_id, [])
            if not self.should_exclude_session(session, messages):
                # Apply refrigerator filter if enabled
                if refrigerator_only and not self.has_refrigerator_example_tag(session, messages):
                    continue
                valid_sessions.append(session)
        
        # Count annotated sessions
        annotated_sessions = []
        for session in valid_sessions:
            session_id = session.get('id')
            messages = messages_data.get(session_id, [])
            if self.is_annotated_session(session, messages):
                annotated_sessions.append(session)
        
        # Calculate refrigerator examples percentage
        refrigerator_sessions = []
        for session in annotated_sessions:
            session_id = session.get('id')
            messages = messages_data.get(session_id, [])
            if self.has_refrigerator_example_tag(session, messages):
                refrigerator_sessions.append(session)
        
        refrigerator_percent = (len(refrigerator_sessions) / len(annotated_sessions) * 100) if annotated_sessions else 0.0
        
        # Calculate refrigerator example rate by method
        method_refrigerator_rates = self.calculate_refrigerator_rate_by_method(valid_sessions, messages_data)
        
        # Calculate median human words per session
        median_words = self.calculate_median_human_words(valid_sessions, messages_data)
        
        # Calculate average session rating
        avg_rating = self.calculate_average_rating(valid_sessions, messages_data)
        
        # Note: median_words_by_method and median_messages_by_method are calculated globally
        # and added to each metric in the main generation loop
        
        # Calculate average rating by method and version
        average_rating_by_method = self.calculate_average_rating_by_method_and_version(valid_sessions, messages_data)
        
        return {
            'version_name': version_name,
            'total_sessions': len(valid_sessions),
            'annotated_sessions': len(annotated_sessions),
            'refrigerator_examples_percent': refrigerator_percent,
            'method_refrigerator_rates': method_refrigerator_rates,
            'median_human_words_per_session': median_words,
            'average_session_rating': avg_rating,
            'average_rating_by_method': average_rating_by_method
        }
    
    def calculate_flw_breakdown_by_gs_tiers(self, gs_data: Dict[str, Dict]) -> Dict:
        """Calculate FLW count breakdown by cohort, group, and GS score tiers"""
        # Structure: {cohort: {group: {tier: count}}}
        breakdown = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        
        for participant_id, gs_info in gs_data.items():
            cohort = gs_info.get('cohort', '').strip()
            group_raw = gs_info.get('group', '').strip()
            score = gs_info.get('score')
            
            # Skip if missing essential data
            if not cohort or not group_raw or score is None:
                continue
            
            # Map group: A = Control, B = Coached
            if group_raw.upper() == 'A':
                group = 'Control'
            elif group_raw.upper() == 'B':
                group = 'Coached'
            else:
                # Try to match other variations
                group_lower = group_raw.lower()
                if 'control' in group_lower or group_lower == 'a':
                    group = 'Control'
                elif 'coach' in group_lower or group_lower == 'b':
                    group = 'Coached'
                else:
                    continue  # Skip unknown groups
            
            # Determine GS score bracket
            if 0 <= score <= 19:
                bracket = '0-19'
            elif 20 <= score <= 39:
                bracket = '20-39'
            elif 40 <= score <= 59:
                bracket = '40-59'
            elif 60 <= score <= 79:
                bracket = '60-79'
            elif 80 <= score <= 100:
                bracket = '80-100'
            else:
                continue  # Skip invalid scores
            
            breakdown[cohort][group][bracket] += 1
        
        return dict(breakdown)
    
    def calculate_avg_gs_by_version_and_method(self, sessions: List[Dict], messages_data: Dict, gs_data: Dict[str, Dict]) -> Dict:
        """Calculate average GS score by bot version and coaching method"""
        # Structure: {version: {method: [list of GS scores]}}
        version_method_scores = defaultdict(lambda: defaultdict(list))
        
        # Create case-insensitive lookup for GS data
        gs_data_lower = {}
        for pid, info in gs_data.items():
            gs_data_lower[pid.lower()] = info
        
        # Group sessions by participant
        participant_sessions = defaultdict(list)
        for session in sessions:
            participant_id = session.get('participant', {}).get('identifier', '')
            if not participant_id:
                continue
            
            # Skip test sessions
            if participant_id.endswith('@dimagi.com'):
                continue
            
            session_id = session.get('id')
            if not session_id:
                continue
            
            messages = messages_data.get(session_id, [])
            
            # Skip split sessions and test sessions
            if self.should_exclude_session(session, messages):
                continue
            
            participant_sessions[participant_id].append((session, messages))
        
        # For each participant with GS score, determine their version/method usage
        for participant_id, session_list in participant_sessions.items():
            # Get GS score (try exact match first, then case-insensitive)
            gs_info = gs_data.get(participant_id) or gs_data_lower.get(participant_id.lower())
            if not gs_info or gs_info.get('score') is None:
                continue
            
            gs_score = gs_info['score']
            
            # Track which version/method combinations this participant used
            participant_combinations = set()
            
            for session, messages in session_list:
                # Determine version
                version = None
                for version_name, version_config in self.coaching_bot_versions.items():
                    if self.matches_version(session, version_config, messages):
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
                
                if not version:
                    continue
                
                # Determine coaching method
                method = self.detect_coaching_method(session, messages)
                
                # Add to combination set (to avoid double-counting same participant)
                combination = (version, method)
                if combination not in participant_combinations:
                    participant_combinations.add(combination)
                    version_method_scores[version][method].append(gs_score)
        
        # Calculate averages
        avg_scores = {}
        for version, method_scores in version_method_scores.items():
            avg_scores[version] = {}
            for method, scores in method_scores.items():
                if scores:
                    avg_scores[version][method] = statistics.mean(scores)
                else:
                    avg_scores[version][method] = 0.0
        
        return avg_scores
    
    def has_tag(self, session: Dict, messages: List[Dict], tag: str) -> bool:
        """Check if session or any message has the specified tag"""
        # Check session tags
        if tag in session.get('tags', []):
            return True
        
        # Check message tags
        if messages:
            for message in messages:
                if tag in message.get('tags', []):
                    return True
        
        return False
    
    def is_tagged_session(self, session: Dict, messages: List[Dict] = None) -> bool:
        """Check if session is a tagged session (has non-version and non-method tags)"""
        # Collect all tags from session and messages
        all_tags = set(session.get('tags', []))
        
        if messages:
            for message in messages:
                all_tags.update(message.get('tags', []))
        
        # Filter out version tags and method tags
        non_version_method_tags = [
            tag for tag in all_tags 
            if not self.is_version_tag(tag) and not self.is_coaching_method_tag(tag)
        ]
        
        return len(non_version_method_tags) > 0
    
    def calculate_tag_counts_by_version_and_method(self, sessions: List[Dict], messages_data: Dict) -> Dict:
        """Calculate tag counts by version and method"""
        # Define all tags to track
        tags_to_track = [
            'safe', 'unsafe', 'acceptable', 'unacceptable',
            'refrigerator_example', 'not_refrigerator_example',
            'bot_performance_good', 'bot_performance_bad',
            'coaching_good', 'coaching_undetermined', 'coaching_bad',
            'engagement_good', 'engagement_bad',
            'user_knowledge_good', 'user_knowledge_bad',
            'user_ai_response'
        ]
        
        methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        
        # Structure: {version: {tag: {method: count, 'total': count}}}
        tag_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        
        # Track unique tagged sessions by version and method
        # Structure: {version: {method: set of session_ids}}
        tagged_sessions_by_version_method = defaultdict(lambda: defaultdict(set))
        
        # Also track overall counts (all versions combined)
        overall_counts = defaultdict(lambda: defaultdict(int))  # {tag: {method: count}}
        overall_totals = defaultdict(int)  # {tag: total_count}
        
        for session in sessions:
            session_id = session.get('id')
            if not session_id:
                continue
            
            messages = messages_data.get(session_id, [])
            
            # Skip split sessions and test sessions
            if self.should_exclude_session(session, messages):
                continue
            
            # Only count tagged sessions
            if not self.is_tagged_session(session, messages):
                continue
            
            # Determine version
            version = None
            for version_name, version_config in self.coaching_bot_versions.items():
                if self.matches_version(session, version_config, messages):
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
            
            if not version:
                continue
            
            # Determine coaching method
            method = self.detect_coaching_method(session, messages)
            
            # Track this session as a tagged session
            tagged_sessions_by_version_method[version][method].add(session_id)
            
            # Check each tag
            for tag in tags_to_track:
                if self.has_tag(session, messages, tag):
                    # Count for this version/method combination
                    tag_counts[version][tag][method] += 1
                    tag_counts[version][tag]['total'] += 1
                    
                    # Count for overall (all versions)
                    overall_counts[tag][method] += 1
                    overall_totals[tag] += 1
        
        # Add overall counts to the structure
        tag_counts['All Versions'] = {}
        for tag in tags_to_track:
            tag_counts['All Versions'][tag] = dict(overall_counts[tag])
            tag_counts['All Versions'][tag]['total'] = overall_totals[tag]
        
        # Add tagged session counts to the structure
        for version in tagged_sessions_by_version_method:
            if version not in tag_counts:
                tag_counts[version] = {}
            tag_counts[version]['_tagged_sessions'] = {}
            for method in methods:
                tag_counts[version]['_tagged_sessions'][method] = len(tagged_sessions_by_version_method[version].get(method, set()))
            # Total tagged sessions for this version
            all_sessions_for_version = set()
            for method_sessions in tagged_sessions_by_version_method[version].values():
                all_sessions_for_version.update(method_sessions)
            tag_counts[version]['_tagged_sessions']['total'] = len(all_sessions_for_version)
        
        return dict(tag_counts)
    
    def calculate_tag_gs_scores_by_version_and_method(self, sessions: List[Dict], messages_data: Dict, gs_data: Dict) -> Dict:
        """Calculate median GS scores for sessions with each tag, grouped by version and method"""
        # Define all tags to track
        tags_to_track = [
            'safe', 'unsafe', 'acceptable', 'unacceptable',
            'refrigerator_example', 'not_refrigerator_example',
            'bot_performance_good', 'bot_performance_bad',
            'coaching_good', 'coaching_undetermined', 'coaching_bad',
            'engagement_good', 'engagement_bad',
            'user_knowledge_good', 'user_knowledge_bad',
            'user_ai_response'
        ]
        
        methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        
        # Structure: {version: {tag: {method: [list of GS scores]}}}
        tag_gs_scores = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        
        # Also track overall GS scores (all versions combined)
        overall_gs_scores = defaultdict(lambda: defaultdict(list))  # {tag: {method: [GS scores]}}
        overall_gs_scores_total = defaultdict(list)  # {tag: [all GS scores]}
        
        # Create lowercase mapping for case-insensitive lookup
        gs_data_lower = {}
        for pid, gs_info in gs_data.items():
            gs_data_lower[pid.lower()] = gs_info
        
        for session in sessions:
            session_id = session.get('id')
            if not session_id:
                continue
            
            messages = messages_data.get(session_id, [])
            
            # Skip split sessions and test sessions
            if self.should_exclude_session(session, messages):
                continue
            
            # Only count tagged sessions
            if not self.is_tagged_session(session, messages):
                continue
            
            # Get participant ID and GS score
            participant_id = session.get('participant', {}).get('identifier', '')
            if not participant_id:
                continue
            
            # Look up GS score (case-insensitive)
            gs_info = gs_data.get(participant_id) or gs_data_lower.get(participant_id.lower())
            if not gs_info or gs_info.get('score') is None:
                continue
            
            gs_score = gs_info['score']
            
            # Determine version
            version = None
            for version_name, version_config in self.coaching_bot_versions.items():
                if self.matches_version(session, version_config, messages):
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
            
            if not version:
                continue
            
            # Determine coaching method
            method = self.detect_coaching_method(session, messages)
            
            # Check each tag
            for tag in tags_to_track:
                if self.has_tag(session, messages, tag):
                    # Add GS score for this version/method combination
                    tag_gs_scores[version][tag][method].append(gs_score)
                    
                    # Add to overall (all versions)
                    overall_gs_scores[tag][method].append(gs_score)
                    overall_gs_scores_total[tag].append(gs_score)
        
        # Calculate medians
        # Structure: {version: {tag: {method: median_score, 'total': median_score}}}
        tag_gs_medians = defaultdict(lambda: defaultdict(dict))
        
        for version in tag_gs_scores:
            for tag in tags_to_track:
                if tag in tag_gs_scores[version]:
                    # Calculate median for each method
                    for method in methods:
                        scores = tag_gs_scores[version][tag].get(method, [])
                        if scores:
                            tag_gs_medians[version][tag][method] = statistics.median(scores)
                    
                    # Calculate total median (all methods combined)
                    all_scores = []
                    for method in methods:
                        all_scores.extend(tag_gs_scores[version][tag].get(method, []))
                    if all_scores:
                        tag_gs_medians[version][tag]['total'] = statistics.median(all_scores)
        
        # Add overall medians (all versions combined)
        tag_gs_medians['All Versions'] = {}
        for tag in tags_to_track:
            tag_gs_medians['All Versions'][tag] = {}
            # Calculate median for each method
            for method in methods:
                scores = overall_gs_scores[tag].get(method, [])
                if scores:
                    tag_gs_medians['All Versions'][tag][method] = statistics.median(scores)
            
            # Calculate total median (all methods combined)
            all_scores = overall_gs_scores_total[tag]
            if all_scores:
                tag_gs_medians['All Versions'][tag]['total'] = statistics.median(all_scores)
        
        return dict(tag_gs_medians)
    
    def prepare_tag_combination_data(self, sessions: List[Dict], messages_data: Dict) -> Dict:
        """Prepare data structure for tag combination calculations"""
        tags_to_track = [
            'safe', 'unsafe', 'acceptable', 'unacceptable',
            'refrigerator_example', 'not_refrigerator_example',
            'bot_performance_good', 'bot_performance_bad',
            'coaching_good', 'coaching_undetermined', 'coaching_bad',
            'engagement_good', 'engagement_bad',
            'user_knowledge_good', 'user_knowledge_bad',
            'user_ai_response'
        ]
        
        # Structure: {version: {method: {session_id: [list of tags]}}}
        session_tags_by_version_method = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        
        # Also track total tagged sessions per version/method
        tagged_sessions_by_version_method = defaultdict(lambda: defaultdict(int))
        
        for session in sessions:
            session_id = session.get('id')
            if not session_id:
                continue
            
            messages = messages_data.get(session_id, [])
            
            # Skip split sessions and test sessions
            if self.should_exclude_session(session, messages):
                continue
            
            # Only count tagged sessions
            if not self.is_tagged_session(session, messages):
                continue
            
            # Determine version
            version = None
            for version_name, version_config in self.coaching_bot_versions.items():
                if self.matches_version(session, version_config, messages):
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
            
            if not version:
                continue
            
            # Determine coaching method
            method = self.detect_coaching_method(session, messages)
            
            # Collect tags for this session
            session_tags = []
            for tag in tags_to_track:
                if self.has_tag(session, messages, tag):
                    session_tags.append(tag)
            
            if session_tags:
                session_tags_by_version_method[version][method][session_id] = session_tags
                tagged_sessions_by_version_method[version][method] += 1
        
        # Convert to a format suitable for JSON
        result = {}
        for version, method_data in session_tags_by_version_method.items():
            result[version] = {}
            for method, sessions_data in method_data.items():
                result[version][method] = {
                    'sessions': dict(sessions_data),
                    'total_tagged': tagged_sessions_by_version_method[version].get(method, 0)
                }
        
        return dict(result)
    
    def prepare_tag_combination_gs_data(self, sessions: List[Dict], messages_data: Dict, gs_data: Dict) -> Dict:
        """Prepare GS score data structure for tag combination calculations"""
        tags_to_track = [
            'safe', 'unsafe', 'acceptable', 'unacceptable',
            'refrigerator_example', 'not_refrigerator_example',
            'bot_performance_good', 'bot_performance_bad',
            'coaching_good', 'coaching_undetermined', 'coaching_bad',
            'engagement_good', 'engagement_bad',
            'user_knowledge_good', 'user_knowledge_bad',
            'user_ai_response'
        ]
        
        # Structure: {version: {method: {session_id: {tags: [list], participant_id: str, gs_score: int}}}}
        session_data_by_version_method = defaultdict(lambda: defaultdict(dict))
        
        # Create lowercase mapping for case-insensitive lookup
        gs_data_lower = {}
        for pid, gs_info in gs_data.items():
            gs_data_lower[pid.lower()] = gs_info
        
        for session in sessions:
            session_id = session.get('id')
            if not session_id:
                continue
            
            messages = messages_data.get(session_id, [])
            
            # Skip split sessions and test sessions
            if self.should_exclude_session(session, messages):
                continue
            
            # Only count tagged sessions
            if not self.is_tagged_session(session, messages):
                continue
            
            # Get participant ID and GS score
            participant_id = session.get('participant', {}).get('identifier', '')
            if not participant_id:
                continue
            
            # Look up GS score (case-insensitive)
            gs_info = gs_data.get(participant_id) or gs_data_lower.get(participant_id.lower())
            if not gs_info or gs_info.get('score') is None:
                continue
            
            gs_score = gs_info['score']
            
            # Determine version
            version = None
            for version_name, version_config in self.coaching_bot_versions.items():
                if self.matches_version(session, version_config, messages):
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
            
            if not version:
                continue
            
            # Determine coaching method
            method = self.detect_coaching_method(session, messages)
            
            # Collect tags for this session
            session_tags = []
            for tag in tags_to_track:
                if self.has_tag(session, messages, tag):
                    session_tags.append(tag)
            
            if session_tags:
                session_data_by_version_method[version][method][session_id] = {
                    'tags': session_tags,
                    'participant_id': participant_id,
                    'gs_score': gs_score
                }
        
        # Convert to a format suitable for JSON
        result = {}
        for version, method_data in session_data_by_version_method.items():
            result[version] = {}
            for method, sessions_data in method_data.items():
                result[version][method] = {
                    'sessions': {sid: data['tags'] for sid, data in sessions_data.items()},
                    'gs_scores': {sid: data['gs_score'] for sid, data in sessions_data.items()},
                    'total_tagged': len(sessions_data)
                }
        
        return dict(result)
    
    def generate_tag_table_rows(self, tag_counts: Dict, metrics: List[Dict], selected_versions: List[str] = None, selected_tags: List[str] = None, mode: str = 'count', tag_gs_scores: Dict = None) -> str:
        """Generate HTML rows for tag counts table with count and percentage columns, or GS score medians
        
        Args:
            tag_counts: Tag count data (for count mode)
            metrics: List of version metrics
            selected_versions: List of selected versions to filter
            selected_tags: List of selected tags to filter
            mode: 'count' or 'gs_score'
            tag_gs_scores: GS score median data (for gs_score mode)
        """
        tags_to_track = [
            'safe', 'unsafe', 'acceptable', 'unacceptable',
            'refrigerator_example', 'not_refrigerator_example',
            'bot_performance_good', 'bot_performance_bad',
            'coaching_good', 'coaching_undetermined', 'coaching_bad',
            'engagement_good', 'engagement_bad',
            'user_knowledge_good', 'user_knowledge_bad',
            'user_ai_response'
        ]
        
        # Filter tags if specified
        if selected_tags is None:
            tags_to_show = tags_to_track
        else:
            tags_to_show = [tag for tag in tags_to_track if tag in selected_tags]
        
        methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        
        # Filter versions if specified
        if selected_versions is None:
            # Default: all versions
            version_names = [m['version_name'] for m in metrics]
        else:
            if mode == 'count':
                version_names = [v for v in selected_versions if v in tag_counts]
            else:
                version_names = [v for v in selected_versions if v in (tag_gs_scores or {})]
        
        if mode == 'count':
            if not tag_counts:
                return "<tr><td colspan='14' class='text-center'>No tag data available</td></tr>"
            
            rows = ""
            
            # Calculate total tagged sessions per method across selected versions
            total_tagged_by_method = defaultdict(int)
            for version in version_names:
                if version in tag_counts and '_tagged_sessions' in tag_counts[version]:
                    for method in methods:
                        total_tagged_by_method[method] += tag_counts[version]['_tagged_sessions'].get(method, 0)
            
            # Calculate total tagged sessions across all selected versions
            total_tagged_sessions = sum(total_tagged_by_method.values())
            
            # Generate rows for each tag
            for tag in tags_to_show:
                row = f"<tr><td><strong>{tag}</strong></td>"
                
                # Total count across all selected versions
                total_count = 0
                for version in version_names:
                    if version in tag_counts and tag in tag_counts[version]:
                        total_count += tag_counts[version][tag].get('total', 0)
                
                # Total percentage
                total_percentage = (total_count / total_tagged_sessions * 100) if total_tagged_sessions > 0 else 0
                row += f"<td>{total_count}</td><td>{total_percentage:.1f}%</td>"
                
                # Count by method (aggregated across selected versions)
                method_totals = defaultdict(int)
                for version in version_names:
                    if version in tag_counts and tag in tag_counts[version]:
                        for method in methods:
                            method_totals[method] += tag_counts[version][tag].get(method, 0)
                
                for method in methods:
                    count = method_totals[method]
                    # Percentage: count for this method / total count for this tag
                    percentage = (count / total_count * 100) if total_count > 0 else 0
                    row += f"<td>{count}</td><td>{percentage:.1f}%</td>"
                
                row += "</tr>"
                rows += row
            
            # Add Total row
            total_row = "<tr><td><strong>Total</strong></td>"
            total_row += f"<td><strong>{total_tagged_sessions}</strong></td><td><strong>100.0%</strong></td>"
            
            # Total by method - sum across selected versions
            total_by_method = defaultdict(int)
            for version in version_names:
                if version in tag_counts and '_tagged_sessions' in tag_counts[version]:
                    for method in methods:
                        method_count = tag_counts[version]['_tagged_sessions'].get(method, 0)
                        total_by_method[method] += method_count
            
            for method in methods:
                count = total_by_method[method]
                percentage = (count / total_tagged_sessions * 100) if total_tagged_sessions > 0 else 0
                total_row += f"<td><strong>{count}</strong></td><td><strong>{percentage:.1f}%</strong></td>"
            
            total_row += "</tr>"
            rows += total_row
            
            return rows
        
        else:  # mode == 'gs_score'
            if not tag_gs_scores:
                return "<tr><td colspan='14' class='text-center'>No GS score data available</td></tr>"
            
            rows = ""
            
            # Generate rows for each tag
            for tag in tags_to_show:
                row = f"<tr><td><strong>{tag}</strong></td>"
                
                # Collect all GS scores for this tag across selected versions
                all_scores = []
                for version in version_names:
                    if version in tag_gs_scores and tag in tag_gs_scores[version]:
                        score = tag_gs_scores[version][tag].get('total')
                        if score is not None:
                            all_scores.append(score)
                
                # Calculate total median
                total_median = statistics.median(all_scores) if all_scores else None
                if total_median is not None:
                    row += f"<td>{total_median:.1f}</td><td>-</td>"
                else:
                    row += "<td>-</td><td>-</td>"
                
                # Median by method (aggregated across selected versions)
                method_scores = defaultdict(list)
                for version in version_names:
                    if version in tag_gs_scores and tag in tag_gs_scores[version]:
                        for method in methods:
                            score = tag_gs_scores[version][tag].get(method)
                            if score is not None:
                                method_scores[method].append(score)
                
                for method in methods:
                    scores = method_scores[method]
                    if scores:
                        median_score = statistics.median(scores)
                        row += f"<td>{median_score:.1f}</td><td>-</td>"
                    else:
                        row += "<td>-</td><td>-</td>"
                
                row += "</tr>"
                rows += row
            
            # Add Total row (not applicable for GS scores, but keep for consistency)
            total_row = "<tr><td><strong>Total</strong></td>"
            total_row += "<td><strong>-</strong></td><td><strong>-</strong></td>"
            
            for method in methods:
                total_row += "<td><strong>-</strong></td><td><strong>-</strong></td>"
            
            total_row += "</tr>"
            rows += total_row
            
            return rows
    
    def calculate_tag_combination_counts(self, sessions: List[Dict], messages_data: Dict, selected_tags: List[str]) -> Dict:
        """Calculate session counts for tag combinations by version and method"""
        if not selected_tags:
            return {}
        
        methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        
        # Structure: {version: {method: count}}
        combination_counts = defaultdict(lambda: defaultdict(int))
        tagged_sessions_by_version_method = defaultdict(lambda: defaultdict(int))
        
        for session in sessions:
            session_id = session.get('id')
            if not session_id:
                continue
            
            messages = messages_data.get(session_id, [])
            
            # Skip split sessions and test sessions
            if self.should_exclude_session(session, messages):
                continue
            
            # Only count tagged sessions
            if not self.is_tagged_session(session, messages):
                continue
            
            # Check if session has ALL selected tags
            has_all_tags = True
            for tag in selected_tags:
                if not self.has_tag(session, messages, tag):
                    has_all_tags = False
                    break
            
            if not has_all_tags:
                continue
            
            # Determine version
            version = None
            for version_name, version_config in self.coaching_bot_versions.items():
                if self.matches_version(session, version_config, messages):
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
            
            if not version:
                continue
            
            # Determine coaching method
            method = self.detect_coaching_method(session, messages)
            
            # Count this session
            combination_counts[version][method] += 1
            
            # Also track total tagged sessions for percentage calculation
            tagged_sessions_by_version_method[version][method] += 1
        
        # Calculate percentages
        result = {}
        for version, method_counts in combination_counts.items():
            result[version] = {}
            for method, count in method_counts.items():
                total_tagged = tagged_sessions_by_version_method[version].get(method, 0)
                percentage = (count / total_tagged * 100) if total_tagged > 0 else 0
                result[version][method] = {
                    'count': count,
                    'percentage': percentage
                }
        
        return dict(result)
    
    def generate_flw_breakdown_table_rows(self, flw_breakdown: Dict) -> str:
        """Generate HTML rows for FLW breakdown table with collapsible cohort rows"""
        if not flw_breakdown:
            return "<tr><td colspan='8' class='text-center'>No GS data available</td></tr>"
        
        rows = ""
        brackets = ['0-19', '20-39', '40-59', '60-79', '80-100']
        groups = ['Control', 'Coached']
        
        # Get all cohorts and sort them
        cohorts = sorted(flw_breakdown.keys())
        
        # Calculate totals
        total_by_group_bracket = defaultdict(lambda: defaultdict(int))
        total_by_cohort = defaultdict(int)
        total_by_group = defaultdict(int)
        grand_total = 0
        
        # Store cohort data for JavaScript
        cohort_data = {}
        
        for cohort, group_data in flw_breakdown.items():
            cohort_total = 0
            cohort_data[cohort] = {}
            for group in groups:
                group_total = 0
                cohort_data[cohort][group] = {}
                for bracket in brackets:
                    count = group_data.get(group, {}).get(bracket, 0)
                    total_by_group_bracket[group][bracket] += count
                    group_total += count
                    cohort_total += count
                    cohort_data[cohort][group][bracket] = count
                cohort_data[cohort][group]['total'] = group_total
                total_by_group[group] += group_total
            total_by_cohort[cohort] = cohort_total
            grand_total += cohort_total
        
        # Generate rows for each cohort with collapsible structure
        for cohort in cohorts:
            group_data = flw_breakdown[cohort]
            control_total = cohort_data[cohort]['Control']['total']
            coached_total = cohort_data[cohort]['Coached']['total']
            cohort_combined_total = control_total + coached_total
            
            # Cohort header row (always visible, clickable to toggle) - shows combined totals for each bracket when collapsed
            row = f'<tr class="cohort-header" data-cohort="{cohort}" style="cursor: pointer; background-color: #f8f9fa;" onclick="toggleCohort(\'{cohort}\')">'
            row += f'<td><strong>{cohort}</strong> <i class="fas fa-chevron-right cohort-icon" id="icon-{cohort}"></i></td>'
            row += '<td><strong>Total</strong></td>'
            # Show combined totals (control + coach) for each bracket in collapsed view
            for bracket in brackets:
                control_count = group_data.get('Control', {}).get(bracket, 0)
                coach_count = group_data.get('Coached', {}).get(bracket, 0)
                bracket_total = control_count + coach_count
                row += f'<td class="cohort-summary-bracket" data-cohort="{cohort}" data-bracket="{bracket}" data-count="{bracket_total}">{bracket_total}</td>'
            row += f'<td class="cohort-total-cell"><strong>{cohort_combined_total}</strong></td></tr>'
            rows += row
            
            # Expanded detail rows (hidden by default)
            # Control detail row
            row = f'<tr class="cohort-detail" data-cohort="{cohort}" style="display: none; color: #6c757d;">'
            row += f'<td></td><td><strong>control</strong></td>'
            for bracket in brackets:
                count = group_data.get('Control', {}).get(bracket, 0)
                row += f'<td data-count="{count}">{count}</td>'
            row += f'<td><strong>{control_total}</strong></td></tr>'
            rows += row
            
            # Coached detail row
            row = f'<tr class="cohort-detail" data-cohort="{cohort}" style="display: none; color: #6c757d;">'
            row += '<td></td><td><strong>coach</strong></td>'
            for bracket in brackets:
                count = group_data.get('Coached', {}).get(bracket, 0)
                row += f'<td data-count="{count}">{count}</td>'
            row += f'<td><strong>{coached_total}</strong></td></tr>'
            rows += row
        
        # Add totals row (always visible) - emphasized with darker background
        if cohorts:
            # Control total row
            control_grand_total = total_by_group['Control']
            rows += '<tr class="total-row" style="background-color: #e9ecef; font-weight: bold;"><td><strong>Total</strong></td><td><strong>control</strong></td>'
            for bracket in brackets:
                count = total_by_group_bracket['Control'].get(bracket, 0)
                rows += f'<td data-count="{count}"><strong>{count}</strong></td>'
            rows += f'<td><strong>{control_grand_total}</strong></td></tr>'
            
            # Coached total row
            coached_grand_total = total_by_group['Coached']
            rows += '<tr class="total-row" style="background-color: #e9ecef; font-weight: bold;"><td></td><td><strong>coach</strong></td>'
            for bracket in brackets:
                count = total_by_group_bracket['Coached'].get(bracket, 0)
                rows += f'<td data-count="{count}"><strong>{count}</strong></td>'
            rows += f'<td><strong>{coached_grand_total}</strong></td></tr>'
        
        return rows
    
    def generate_avg_gs_table_rows(self, avg_gs_scores: Dict, metrics: List[Dict]) -> str:
        """Generate HTML rows for average GS score table"""
        if not avg_gs_scores:
            return "<tr><td colspan='6' class='text-center'>No GS data available</td></tr>"
        
        methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        version_names = [m['version_name'] for m in metrics]
        
        rows = ""
        
        # Calculate totals
        method_totals = defaultdict(list)  # Store all scores for averaging
        version_totals = defaultdict(list)
        
        for version, method_scores in avg_gs_scores.items():
            for method, avg_score in method_scores.items():
                if avg_score > 0:
                    # We need to track individual scores, but we only have averages
                    # For now, we'll use a weighted approach or just show the average
                    method_totals[method].append(avg_score)
                    version_totals[version].append(avg_score)
        
        # Generate rows for each method
        for method in methods:
            row = f"<tr><td><strong>{method}</strong></td>"
            method_scores_list = []
            
            for version_name in version_names:
                avg_score = avg_gs_scores.get(version_name, {}).get(method, 0)
                if avg_score > 0:
                    row += f"<td>{avg_score:.1f}</td>"
                    method_scores_list.append(avg_score)
                else:
                    row += "<td>-</td>"
            
            # Calculate "All Versions" average for this method
            if method_scores_list:
                all_versions_avg = statistics.mean(method_scores_list)
                row += f"<td><strong>{all_versions_avg:.1f}</strong></td>"
            else:
                row += "<td>-</td>"
            
            row += "</tr>"
            rows += row
        
        # Add "Total (All Methods)" row
        rows += "<tr><td><strong>Total (All Methods)</strong></td>"
        for version_name in version_names:
            version_scores_list = version_totals.get(version_name, [])
            if version_scores_list:
                version_avg = statistics.mean(version_scores_list)
                rows += f"<td><strong>{version_avg:.1f}</strong></td>"
            else:
                rows += "<td>-</td>"
        
        # Calculate overall average for "All Versions" column
        all_scores = []
        for method_scores_list in method_totals.values():
            all_scores.extend(method_scores_list)
        if all_scores:
            overall_avg = statistics.mean(all_scores)
            rows += f"<td><strong>{overall_avg:.1f}</strong></td>"
        else:
            rows += "<td>-</td>"
        rows += "</tr>"
        
        return rows
    
    def generate_flw_activity_table_rows(self, flw_activity_metrics: Dict, metrics: List[Dict], metric_type: str) -> str:
        """Generate HTML rows for FLW activity table by method and version
        
        Args:
            flw_activity_metrics: Dictionary with all metric types
            metrics: List of version metrics
            metric_type: One of 'approved_visits_percentage', 'ecd_completed_intervention_percentage', 
                        'visits_before_gs1', 'time_spent_learn', 'post_test_tries'
        """
        if not flw_activity_metrics or metric_type not in flw_activity_metrics:
            return "<tr><td colspan='6' class='text-center'>No FLW activity data available</td></tr>"
        
        metric_data = flw_activity_metrics[metric_type]
        methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        versions = ['V3', 'V4', 'V5', 'V6', 'Control']
        
        rows = ""
        
        # Generate rows for each method
        for method in methods:
            row = f"<tr><td><strong>{method}</strong></td>"
            
            # Add version columns
            for version in versions:
                value = metric_data.get(method, {}).get(version)
                if value is not None:
                    if metric_type in ['approved_visits_percentage', 'ecd_completed_intervention_percentage']:
                        # Display as percentage with 1 decimal place
                        row += f"<td>{value:.1f}%</td>"
                    elif metric_type == 'time_spent_learn':
                        # Display as days with 2 decimal places
                        row += f"<td>{value:.2f}</td>"
                    else:
                        # Display as number with 2 decimal places
                        row += f"<td>{value:.2f}</td>"
                else:
                    row += "<td>-</td>"
            
            row += "</tr>"
            rows += row
        
        # Add "All Versions" column calculation
        # Calculate weighted average or median of medians for each method
        rows_with_all_versions = ""
        for method in methods:
            row = f"<tr><td><strong>{method}</strong></td>"
            
            # Version columns
            for version in versions:
                value = metric_data.get(method, {}).get(version)
                if value is not None:
                    if metric_type in ['approved_visits_percentage', 'ecd_completed_intervention_percentage']:
                        row += f"<td>{value:.1f}%</td>"
                    elif metric_type == 'time_spent_learn':
                        row += f"<td>{value:.2f}</td>"
                    else:
                        row += f"<td>{value:.2f}</td>"
                else:
                    row += "<td>-</td>"
            
            # "All Versions" column - median of medians for percentages, average of averages for others
            version_values = [metric_data.get(method, {}).get(v) for v in versions]
            version_values = [v for v in version_values if v is not None]
            
            if version_values:
                if metric_type in ['approved_visits_percentage', 'ecd_completed_intervention_percentage']:
                    # Median of medians
                    sorted_values = sorted(version_values)
                    n = len(sorted_values)
                    if n % 2 == 0:
                        all_versions_value = (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
                    else:
                        all_versions_value = sorted_values[n//2]
                    row += f"<td><strong>{all_versions_value:.1f}%</strong></td>"
                else:
                    # Average of averages
                    all_versions_value = sum(version_values) / len(version_values)
                    if metric_type == 'time_spent_learn':
                        row += f"<td><strong>{all_versions_value:.2f}</strong></td>"
                    else:
                        row += f"<td><strong>{all_versions_value:.2f}</strong></td>"
            else:
                row += "<td>-</td>"
            
            row += "</tr>"
            rows_with_all_versions += row
        
        # Add "Total (All Methods)" row
        total_row = "<tr><td><strong>Total (All Methods)</strong></td>"
        for version in versions:
            version_values = [metric_data.get(method, {}).get(version) for method in methods]
            version_values = [v for v in version_values if v is not None]
            
            if version_values:
                if metric_type in ['approved_visits_percentage', 'ecd_completed_intervention_percentage']:
                    # Median of medians
                    sorted_values = sorted(version_values)
                    n = len(sorted_values)
                    if n % 2 == 0:
                        total_value = (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
                    else:
                        total_value = sorted_values[n//2]
                    total_row += f"<td><strong>{total_value:.1f}%</strong></td>"
                else:
                    # Average of averages
                    total_value = sum(version_values) / len(version_values)
                    if metric_type == 'time_spent_learn':
                        total_row += f"<td><strong>{total_value:.2f}</strong></td>"
                    else:
                        total_row += f"<td><strong>{total_value:.2f}</strong></td>"
            else:
                total_row += "<td>-</td>"
        
        # "All Versions" column for total row
        all_method_version_values = []
        for method in methods:
            for version in versions:
                value = metric_data.get(method, {}).get(version)
                if value is not None:
                    all_method_version_values.append(value)
        
        if all_method_version_values:
            if metric_type in ['approved_visits_percentage', 'ecd_completed_intervention_percentage']:
                sorted_values = sorted(all_method_version_values)
                n = len(sorted_values)
                if n % 2 == 0:
                    grand_total = (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
                else:
                    grand_total = sorted_values[n//2]
                total_row += f"<td><strong>{grand_total:.1f}%</strong></td>"
            else:
                grand_total = sum(all_method_version_values) / len(all_method_version_values)
                if metric_type == 'time_spent_learn':
                    total_row += f"<td><strong>{grand_total:.2f}</strong></td>"
                else:
                    total_row += f"<td><strong>{grand_total:.2f}</strong></td>"
        else:
            total_row += "<td>-</td>"
        
        total_row += "</tr>"
        
        return rows_with_all_versions + total_row
    
    def generate_dashboard_html(self, metrics: List[Dict], progression_data: Dict = None, rating_stats: Dict = None, progression_data_filtered: Dict = None, volume_data: Dict = None, volume_data_refrigerator: Dict = None, session_participant_map: Dict = None, volume_session_maps: Dict = None, progression_session_data: List[Dict] = None, progression_session_data_filtered: List[Dict] = None, all_sessions: List[Dict] = None, all_messages_data: Dict = None, flw_breakdown: Dict = None, avg_gs_scores: Dict = None, tag_counts: Dict = None, tag_combination_data: Dict = None, today_yesterday_tendency: Dict = None, avg_rating_today: Dict = None, avg_rating_yesterday: Dict = None, tag_gs_scores: Dict = None, tag_combination_gs_data: Dict = None, rating_distribution: Dict = None, flw_activity_metrics: Dict = None) -> str:
        """Generate complete dashboard HTML"""
        # Generate summary table
        table_rows = ""
        total_sessions = 0
        total_annotated = 0
        total_refrigerator_count = 0
        median_words_list = []
        ratings_list = []
        
        for metric in metrics:
            table_rows += f"""
                            <tr>
                                <td><strong>{metric['version_name']}</strong></td>
                                <td>{metric['total_sessions']}</td>
                                <td>{metric['annotated_sessions']}</td>
                                <td>{metric['refrigerator_examples_percent']:.1f}%</td>
                                <td>{metric['median_human_words_per_session']:.1f}</td>
                                <td>{metric['average_session_rating']:.2f}</td>
                            </tr>
            """
            # Collect values for total row
            total_sessions += metric['total_sessions']
            total_annotated += metric['annotated_sessions']
            # Calculate refrigerator count from percentage
            if metric['annotated_sessions'] > 0:
                refrigerator_count = int(metric['annotated_sessions'] * metric['refrigerator_examples_percent'] / 100)
                total_refrigerator_count += refrigerator_count
            if metric['median_human_words_per_session'] > 0:
                median_words_list.append(metric['median_human_words_per_session'])
            if metric['average_session_rating'] > 0:
                ratings_list.append(metric['average_session_rating'])
        
        # Calculate totals for total row
        total_refrigerator_percent = (total_refrigerator_count / total_annotated * 100) if total_annotated > 0 else 0.0
        total_median_words = statistics.median(median_words_list) if median_words_list else 0.0
        total_avg_rating = statistics.mean(ratings_list) if ratings_list else 0.0
        
        # Add Total row
        table_rows += f"""
                            <tr style="background-color: #f8f9fa;">
                                <td><strong>Total (All Versions)</strong></td>
                                <td style="font-weight: bold;">{total_sessions}</td>
                                <td style="font-weight: bold;">{total_annotated}</td>
                                <td style="font-weight: bold;">{total_refrigerator_percent:.1f}%</td>
                                <td style="font-weight: bold;">{total_median_words:.1f}</td>
                                <td style="font-weight: bold;">{total_avg_rating:.2f}</td>
                            </tr>
            """
        
        # Generate refrigerator rate by method table (both versions)
        method_table_rows = self.generate_method_table_rows(metrics)
        # Generate filtered version
        metrics_refrigerator = [m.get('refrigerator_filtered', m) for m in metrics]
        method_table_rows_refrigerator = self.generate_method_table_rows(metrics_refrigerator)
        
        # Generate median words by method table
        median_words_table_rows = self.generate_median_words_table_rows(metrics)
        
        # Generate rating by method table (both versions)
        rating_table_rows = self.generate_rating_table_rows(metrics)
        rating_table_rows_refrigerator = self.generate_rating_table_rows(metrics_refrigerator)
        
        # Convert progression data to JSON for JavaScript
        progression_data_json = json.dumps(progression_data) if progression_data else "{}"
        progression_data_filtered_json = json.dumps(progression_data_filtered) if progression_data_filtered else "{}"
        
        # Convert volume data to JSON for JavaScript (all aggregation levels)
        volume_data_day_json = json.dumps(volume_data.get('day', {})) if volume_data else "{}"
        volume_data_week_json = json.dumps(volume_data.get('week', {})) if volume_data else "{}"
        volume_data_month_json = json.dumps(volume_data.get('month', {})) if volume_data else "{}"
        
        # Convert refrigerator-filtered volume data to JSON for JavaScript
        volume_data_refrigerator_day_json = json.dumps(volume_data_refrigerator.get('day', {})) if volume_data_refrigerator else "{}"
        volume_data_refrigerator_week_json = json.dumps(volume_data_refrigerator.get('week', {})) if volume_data_refrigerator else "{}"
        volume_data_refrigerator_month_json = json.dumps(volume_data_refrigerator.get('month', {})) if volume_data_refrigerator else "{}"
        
        # Calculate total session counts by method and version for the summary table (both versions)
        volume_summary = self.calculate_volume_summary(volume_data.get('week', {}) if volume_data else {})
        volume_summary_table_rows = self.generate_volume_summary_table_rows(volume_summary, metrics)
        volume_summary_refrigerator = self.calculate_volume_summary(volume_data_refrigerator.get('week', {}) if volume_data_refrigerator else {})
        volume_summary_table_rows_refrigerator = self.generate_volume_summary_table_rows(volume_summary_refrigerator, metrics_refrigerator)
        
        # Generate summary table rows for refrigerator-filtered version
        table_rows_refrigerator = ""
        total_sessions_r = 0
        total_annotated_r = 0
        total_refrigerator_count_r = 0
        median_words_list_r = []
        ratings_list_r = []
        
        for metric in metrics_refrigerator:
            table_rows_refrigerator += f"""
                            <tr>
                                <td><strong>{metric['version_name']}</strong></td>
                                <td>{metric['total_sessions']}</td>
                                <td>{metric['annotated_sessions']}</td>
                                <td>{metric['refrigerator_examples_percent']:.1f}%</td>
                                <td>{metric['median_human_words_per_session']:.1f}</td>
                                <td>{metric['average_session_rating']:.2f}</td>
                            </tr>
            """
            # Collect values for total row
            total_sessions_r += metric['total_sessions']
            total_annotated_r += metric['annotated_sessions']
            # Calculate refrigerator count from percentage
            if metric['annotated_sessions'] > 0:
                refrigerator_count = int(metric['annotated_sessions'] * metric['refrigerator_examples_percent'] / 100)
                total_refrigerator_count_r += refrigerator_count
            if metric['median_human_words_per_session'] > 0:
                median_words_list_r.append(metric['median_human_words_per_session'])
            if metric['average_session_rating'] > 0:
                ratings_list_r.append(metric['average_session_rating'])
        
        # Calculate totals for total row
        total_refrigerator_percent_r = (total_refrigerator_count_r / total_annotated_r * 100) if total_annotated_r > 0 else 0.0
        total_median_words_r = statistics.median(median_words_list_r) if median_words_list_r else 0.0
        total_avg_rating_r = statistics.mean(ratings_list_r) if ratings_list_r else 0.0
        
        # Add Total row
        table_rows_refrigerator += f"""
                            <tr style="background-color: #f8f9fa;">
                                <td><strong>Total (All Versions)</strong></td>
                                <td style="font-weight: bold;">{total_sessions_r}</td>
                                <td style="font-weight: bold;">{total_annotated_r}</td>
                                <td style="font-weight: bold;">{total_refrigerator_percent_r:.1f}%</td>
                                <td style="font-weight: bold;">{total_median_words_r:.1f}</td>
                                <td style="font-weight: bold;">{total_avg_rating_r:.2f}</td>
                            </tr>
            """
        
        # Calculate metrics for not_refrigerator_example sessions
        total_sessions_nr = 0
        total_annotated_nr = 0
        total_refrigerator_count_nr = 0
        median_words_list_nr = []
        ratings_list_nr = []
        
        if all_sessions and all_messages_data:
            # Filter sessions with not_refrigerator_example tag
            not_refrigerator_sessions = []
            for session in all_sessions:
                session_id = session.get('id')
                messages = all_messages_data.get(session_id, [])
                if not self.should_exclude_session(session, messages):
                    if self.has_not_refrigerator_example_tag(session, messages):
                        not_refrigerator_sessions.append(session)
            
            # Calculate metrics for not_refrigerator_example sessions
            for session in not_refrigerator_sessions:
                total_sessions_nr += 1
                session_id = session.get('id')
                messages = all_messages_data.get(session_id, [])
                
                # Check if annotated
                if self.is_annotated_session(session, messages):
                    total_annotated_nr += 1
                    if self.has_refrigerator_example_tag(session, messages):
                        total_refrigerator_count_nr += 1
                
                # Calculate median words
                total_user_words = 0
                for message in messages:
                    if message.get('role') == 'user':
                        content = message.get('content', '')
                        total_user_words += len(content.split())
                if total_user_words > 0:
                    median_words_list_nr.append(total_user_words)
                
                # Calculate rating
                rating = self.extract_session_rating(session, messages)
                if rating is not None:
                    ratings_list_nr.append(rating)
        
        # Calculate totals for not_refrigerator_example row
        total_refrigerator_percent_nr = (total_refrigerator_count_nr / total_annotated_nr * 100) if total_annotated_nr > 0 else 0.0
        total_median_words_nr = statistics.median(median_words_list_nr) if median_words_list_nr else 0.0
        total_avg_rating_nr = statistics.mean(ratings_list_nr) if ratings_list_nr else 0.0
        
        # Generate aggregated summary table (All Versions vs Refrigerator Only vs Not Refrigerator)
        aggregated_summary_rows = f"""
                            <tr>
                                <td><strong>All Versions</strong></td>
                                <td>{total_sessions}</td>
                                <td>{total_annotated}</td>
                                <td>{total_refrigerator_percent:.1f}%</td>
                                <td>{total_median_words:.1f}</td>
                                <td>{total_avg_rating:.2f}</td>
                            </tr>
                            <tr>
                                <td><strong>Refrigerator Example Sessions Only</strong></td>
                                <td>{total_sessions_r}</td>
                                <td>{total_annotated_r}</td>
                                <td>{total_refrigerator_percent_r:.1f}%</td>
                                <td>{total_median_words_r:.1f}</td>
                                <td>{total_avg_rating_r:.2f}</td>
                            </tr>
                            <tr>
                                <td><strong>Not Refrigerator Example Sessions Only</strong></td>
                                <td>{total_sessions_nr}</td>
                                <td>{total_annotated_nr}</td>
                                <td>{total_refrigerator_percent_nr:.1f}%</td>
                                <td>{total_median_words_nr:.1f}</td>
                                <td>{total_avg_rating_nr:.2f}</td>
                            </tr>
            """
        
        # Convert metrics data to JSON for JavaScript (for dynamic table updates)
        metrics_json = json.dumps(metrics) if metrics else "[]"
        
        # Convert session-participant mapping to JSON for JavaScript
        session_participant_map_json = json.dumps(session_participant_map) if session_participant_map else "{}"
        
        # Convert volume session maps to JSON for JavaScript
        volume_session_maps_json = json.dumps(volume_session_maps) if volume_session_maps else "{}"
        
        # Convert progression session data to JSON for JavaScript
        progression_session_data_json = json.dumps(progression_session_data) if progression_session_data else "[]"
        progression_session_data_filtered_json = json.dumps(progression_session_data_filtered) if progression_session_data_filtered else "[]"
        
        # Convert tag_counts and tag_gs_scores to JSON for JavaScript
        tag_counts_json = json.dumps(tag_counts) if tag_counts else "{}"
        tag_gs_scores_json = json.dumps(tag_gs_scores) if tag_gs_scores else "{}"
        
        # Convert tag_combination_data to JSON for JavaScript
        tag_combination_data_json = json.dumps(tag_combination_data) if tag_combination_data else "{}"
        tag_combination_gs_data_json = json.dumps(tag_combination_gs_data) if tag_combination_gs_data else "{}"
        
        # Convert rating_distribution to JSON for JavaScript
        rating_distribution_json = json.dumps(rating_distribution) if rating_distribution else "{}"
        
        # Generate FLW activity table rows (default to approved_visits_percentage)
        flw_activity_table_rows = ""
        if flw_activity_metrics:
            flw_activity_table_rows = self.generate_flw_activity_table_rows(flw_activity_metrics, metrics, 'approved_visits_percentage')
        else:
            flw_activity_table_rows = "<tr><td colspan='7' class='text-center'>No FLW activity data available</td></tr>"
        
        # Generate FLW visit spacing table rows (default to avg_distance_km_between_visits)
        flw_visit_spacing_table_rows = ""
        if flw_activity_metrics:
            flw_visit_spacing_table_rows = self.generate_flw_activity_table_rows(flw_activity_metrics, metrics, 'avg_distance_km_between_visits')
        else:
            flw_visit_spacing_table_rows = "<tr><td colspan='7' class='text-center'>No FLW activity data available</td></tr>"
        
        # Convert FLW activity metrics to JSON for JavaScript
        flw_activity_metrics_json = json.dumps(flw_activity_metrics) if flw_activity_metrics else "{}"
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Version Comparison Dashboard - OCS</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {{
            background-color: #f8f9fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        .card {{
            box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
            border: 1px solid rgba(0, 0, 0, 0.125);
            margin-bottom: 1.5rem;
        }}
        .card-header {{
            background-color: #007bff;
            color: white;
            border-bottom: 1px solid rgba(0, 0, 0, 0.125);
        }}
        .table th {{
            background-color: #f8f9fa;
            border-top: none;
        }}
        .table-dark th {{
            background-color: #343a40 !important;
            color: #ffffff !important;
            font-weight: bold;
        }}
        /* Style for control/coach detail rows - lighter font color */
        tr.cohort-detail {{
            color: #6c757d;
        }}
        tr.cohort-detail td {{
            color: #6c757d;
        }}
        /* Style for total rows - emphasized with background and bold */
        tr.total-row {{
            background-color: #e9ecef !important;
            font-weight: bold;
        }}
        tr.total-row td {{
            background-color: #e9ecef !important;
            font-weight: bold;
        }}
        /* Style for cohort header rows */
        tr.cohort-header {{
            background-color: #f8f9fa;
        }}
        .navbar {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="#">
                <i class="fas fa-chart-line me-2"></i>
                Version Comparison Dashboard
            </a>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row">
            <div class="col-12">
                <div class="alert alert-info">
                    <h4 class="alert-heading">
                        <i class="fas fa-info-circle me-2"></i>
                        Dashboard Overview
                    </h4>
                    <p>This dashboard compares coaching bot versions based on session metrics, annotations, and user engagement.</p>
                    <hr>
                    <p class="mb-0">
                        <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                </div>
            </div>
        </div>

        <!-- Global Filters Section -->
        <div class="row mt-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h4>
                            <i class="fas fa-filter me-2"></i>Dashboard Filters
                            <button class="btn btn-sm btn-light float-end" type="button" data-bs-toggle="collapse" data-bs-target="#filterCollapse" aria-expanded="false" aria-controls="filterCollapse" style="border: 2px solid #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                                <i class="fas fa-chevron-down text-dark"></i>
                            </button>
                        </h4>
                    </div>
                    <div class="collapse" id="filterCollapse">
                    <div class="card-body">
                        <div class="row">
                            <!-- Date Range Filter -->
                            <div class="col-md-4">
                                <label for="dateRange" class="form-label">Session Date Range:</label>
                                <div class="input-group">
                                    <input type="date" class="form-control" id="startDate" placeholder="Start Date">
                                    <span class="input-group-text">to</span>
                                    <input type="date" class="form-control" id="endDate" placeholder="End Date">
                                </div>
                            </div>
                            
                            <!-- Participant ID Filter -->
                            <div class="col-md-4">
                                <label for="participantFilter" class="form-label">Participant IDs:</label>
                                <textarea class="form-control" id="participantFilter" rows="4" placeholder="Enter participant IDs, one per line"></textarea>
                                <small class="form-text text-muted">Enter one participant ID per line. Leave empty to show all participants.</small>
                                <button class="btn btn-sm btn-primary mt-2" type="button" onclick="applyParticipantFilter()">
                                    <i class="fas fa-filter me-1"></i>Apply Participant Filter
                                </button>
                            </div>
                            
                            <!-- Outlier Filter -->
                            <div class="col-md-4">
                                <label class="form-label">Data Quality Filters:</label>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="excludeOutliersGlobal" onchange="applyGlobalFilters()">
                                    <label class="form-check-label" for="excludeOutliersGlobal">
                                        Exclude outlier sessions (sessions with >50 messages or >1000 words)
                                    </label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="excludeSplitSessions" onchange="applyGlobalFilters()" checked>
                                    <label class="form-check-label" for="excludeSplitSessions">
                                        Exclude split sessions (sessions with less than 3 participant messages)
                                    </label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="excludeTestSessions" onchange="applyGlobalFilters()" checked>
                                    <label class="form-check-label" for="excludeTestSessions">
                                        Exclude test sessions (participant IDs ending with @dimagi.com)
                                    </label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="refrigeratorOnly" onchange="applyGlobalFilters()">
                                    <label class="form-check-label" for="refrigeratorOnly">
                                        Show only refrigerator example sessions
                                    </label>
                                </div>
                            </div>
                        </div>
                        
                        <div class="row mt-3">
                            <div class="col-12">
                                <button class="btn btn-primary" onclick="applyGlobalFilters()">
                                    <i class="fas fa-sync me-2"></i>Apply Filters
                                </button>
                                <button class="btn btn-secondary ms-2" onclick="resetGlobalFilters()">
                                    <i class="fas fa-undo me-2"></i>Reset Filters
                                </button>
                                <small class="text-muted ms-3">
                                    <i class="fas fa-info-circle me-1"></i>
                                    Note: Date and participant filters work for the Session Volume chart. Refrigerator filter applies to all graphs and tables. Participant filter for tables requires dashboard regeneration. Outlier filtering affects the progression line graph and median words/messages tables.
                                </small>
                            </div>
                        </div>
                    </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tab Navigation -->
        <div class="row mt-4">
            <div class="col-12">
                <ul class="nav nav-tabs" id="dashboardTabs" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active" id="summary-tab" data-bs-toggle="tab" data-bs-target="#summary" type="button" role="tab" aria-controls="summary" aria-selected="true">Summary</button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="performance-tab" data-bs-toggle="tab" data-bs-target="#performance" type="button" role="tab" aria-controls="performance" aria-selected="false">Performance</button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="engagement-tab" data-bs-toggle="tab" data-bs-target="#engagement" type="button" role="tab" aria-controls="engagement" aria-selected="false">User Engagement</button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="volume-tab" data-bs-toggle="tab" data-bs-target="#volume" type="button" role="tab" aria-controls="volume" aria-selected="false">Session Volume</button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="gold-standard-tab" data-bs-toggle="tab" data-bs-target="#gold-standard" type="button" role="tab" aria-controls="gold-standard" aria-selected="false">Gold Standard</button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="flw-activity-tab" data-bs-toggle="tab" data-bs-target="#flw-activity" type="button" role="tab" aria-controls="flw-activity" aria-selected="false">FLW Activity</button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="tags-tab" data-bs-toggle="tab" data-bs-target="#tags" type="button" role="tab" aria-controls="tags" aria-selected="false">Tags</button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="definitions-tab" data-bs-toggle="tab" data-bs-target="#definitions" type="button" role="tab" aria-controls="definitions" aria-selected="false">Definitions</button>
                    </li>
                </ul>
                
                <div class="tab-content" id="dashboardTabContent">
                    <!-- Summary Tab -->
                    <div class="tab-pane fade show active" id="summary" role="tabpanel" aria-labelledby="summary-tab">
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h3>Summary Metrics by Version</h3>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead class="table-dark">
                                    <tr>
                                        <th>Coaching Bot Version</th>
                                        <th># Sessions</th>
                                        <th># Annotated Sessions</th>
                                        <th>Refrigeration Examples (%)</th>
                                        <th>Median Human Words per Session</th>
                                        <th>Average Session Rating</th>
                                    </tr>
                                </thead>
                                                <tbody id="summaryMetricsTableBody">
                                    {table_rows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

                        <!-- Aggregated Summary Table -->
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3>Summary Metrics - All Versions vs Refrigerator Examples</h3>
                                    </div>
                                    <div class="card-body">
                                        <div class="table-responsive">
                                            <table class="table table-striped table-hover">
                                                <thead class="table-dark">
                                                    <tr>
                                                        <th>Category</th>
                                                        <th># Sessions</th>
                                                        <th># Annotated Sessions</th>
                                                        <th>Refrigeration Examples (%)</th>
                                                        <th>Median Human Words per Session</th>
                                                        <th>Average Session Rating</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {aggregated_summary_rows}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <!-- Performance Tab -->
                    <div class="tab-pane fade" id="performance" role="tabpanel" aria-labelledby="performance-tab">
                        <!-- FLW Rating Distribution Chart -->
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3>FLW Rating Distribution</h3>
                                    </div>
                                    <div class="card-body">
                                        <div class="mb-3">
                                            <div class="row">
                                                <div class="col-md-6">
                                                    <label for="ratingChartMethodFilter" class="form-label">Filter by Coaching Method:</label>
                                                    <select class="form-select" id="ratingChartMethodFilter" onchange="updateRatingDistributionChart()">
                                                        <option value="all">All Methods</option>
                                                        <option value="Scenario">Scenario</option>
                                                        <option value="Microlearning">Microlearning</option>
                                                        <option value="Microlearning vaccines">Microlearning vaccines</option>
                                                        <option value="Motivational interviewing">Motivational interviewing</option>
                                                        <option value="Visit check in">Visit check in</option>
                                                        <option value="Unknown">Unknown</option>
                                                    </select>
                                                </div>
                                                <div class="col-md-6">
                                                    <label for="ratingChartVersionFilter" class="form-label">Filter by Bot Version:</label>
                                                    <select class="form-select" id="ratingChartVersionFilter" onchange="updateRatingDistributionChart()">
                                                        <option value="all">All Versions</option>
                                                        {''.join([f'<option value="{metric["version_name"]}">{metric["version_name"]}</option>' for metric in metrics])}
                                                    </select>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="chart-container" style="position: relative; height: 400px;">
                                            <canvas id="ratingDistributionChart"></canvas>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3>Refrigerator Example Rate by Method and Version</h3>
                                    </div>
                                    <div class="card-body">
                                        <div class="mb-3">
                                            <label class="form-label"><strong>Calculation Mode:</strong></label>
                                            <div class="btn-group" role="group" aria-label="Calculation mode toggle">
                                                <input type="radio" class="btn-check" name="refrigeratorCalcMode" id="calcModeAnnotated" value="annotated" checked onchange="updateRefrigeratorCalculationMode()">
                                                <label class="btn btn-outline-primary" for="calcModeAnnotated">
                                                    refrigerator_example / total annotated sessions
                                                </label>
                                                
                                                <input type="radio" class="btn-check" name="refrigeratorCalcMode" id="calcModeExplicit" value="explicit" onchange="updateRefrigeratorCalculationMode()">
                                                <label class="btn btn-outline-primary" for="calcModeExplicit">
                                                    refrigerator_example / (refrigerator_example + not_refrigerator_example)
                                                </label>
                                            </div>
                                        </div>
                                        <div class="table-responsive">
                                            <table class="table table-striped table-hover">
                                                <thead class="table-dark">
                                                    <tr>
                                                        <th>Method</th>
                                                        {''.join([f'<th>{metric["version_name"]}</th>' for metric in metrics])}
                                                        <th>All Versions</th>
                                                    </tr>
                                                </thead>
                                                <tbody id="refrigeratorRateTableBody">
                                                    {method_table_rows}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3>Average FLW Score by Method and Version</h3>
                                    </div>
                                    <div class="card-body">
                                        <div class="table-responsive">
                                            <table class="table table-striped table-hover">
                                                <thead class="table-dark">
                                                    <tr>
                                                        <th>Method</th>
                                                        {''.join([f'<th>{metric["version_name"]}</th>' for metric in metrics])}
                                                        <th>All Versions</th>
                                                    </tr>
                                                </thead>
                                                <tbody id="averageRatingTableBody">
                                                    {rating_table_rows}
                                                </tbody>
                                            </table>
                                        </div>
                                        {f'''
                                        <div class="mt-3">
                                            <small class="text-muted">
                                                <strong>Rating Collection Statistics:</strong><br>
                                                • Rating Questions: {rating_stats['rating_question_percentage']:.1f}% of sessions ({rating_stats['sessions_with_rating_questions']} out of {rating_stats['total_sessions']}) contain rating questions<br>
                                                • Actual Ratings: {rating_stats['rating_extraction_percentage']:.1f}% of sessions ({rating_stats['sessions_with_ratings']} out of {rating_stats['total_sessions']}) have extractable ratings
                                            </small>
                                        </div>
                                        ''' if rating_stats else ''}
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3>Today vs Yesterday Preference by Method and Version</h3>
                                    </div>
                                    <div class="card-body">
                                        <div class="table-responsive">
                                            <table class="table table-striped table-hover">
                                                <thead class="table-dark">
                                                    <tr>
                                                        <th>Method</th>
                                                        {''.join([f'<th>{metric["version_name"]}</th>' for metric in metrics])}
                                                        <th>All Versions</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {self.generate_today_yesterday_table_rows(today_yesterday_tendency, metrics) if today_yesterday_tendency else '<tr><td colspan="' + str(len(metrics) + 2) + '" class="text-center">No data available</td></tr>'}
                                                </tbody>
                                            </table>
                                        </div>
                                        <p class="text-muted mt-2">
                                            <small>
                                                <strong>Legend:</strong><br>
                                                <span style="color: green; font-size: 1.5em;">→</span> More users preferred "today"<br>
                                                <span style="color: red; font-size: 1.5em;">←</span> More users preferred "yesterday"<br>
                                                <span style="color: orange; font-size: 1.5em;">↔</span> Equal preference (tie)
                                            </small>
                                        </p>
                                        {self.generate_today_yesterday_statistics(today_yesterday_tendency, metrics) if today_yesterday_tendency else ''}
                                        
                                        <!-- Average Rating for "Yesterday" Responses -->
                                        <div class="mt-5">
                                            <h5>Average Session Rating for Users Who Preferred "Yesterday/Last One"</h5>
                                            <div class="table-responsive">
                                                <table class="table table-bordered table-sm">
                                                    <thead class="table-light">
                                                        <tr>
                                                            <th>Method</th>
                                                            {''.join([f'<th>{metric["version_name"]}</th>' for metric in metrics])}
                                                            <th>All Versions</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {self.generate_average_rating_table_rows(avg_rating_yesterday, metrics, 'yesterday') if avg_rating_yesterday else '<tr><td colspan="' + str(len(metrics) + 2) + '" class="text-center">No data available</td></tr>'}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                        
                                        <!-- Average Rating for "Today" Responses -->
                                        <div class="mt-5">
                                            <h5>Average Session Rating for Users Who Preferred "Today"</h5>
                                            <div class="table-responsive">
                                                <table class="table table-bordered table-sm">
                                                    <thead class="table-light">
                                                        <tr>
                                                            <th>Method</th>
                                                            {''.join([f'<th>{metric["version_name"]}</th>' for metric in metrics])}
                                                            <th>All Versions</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {self.generate_average_rating_table_rows(avg_rating_today, metrics, 'today') if avg_rating_today else '<tr><td colspan="' + str(len(metrics) + 2) + '" class="text-center">No data available</td></tr>'}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- User Engagement Tab -->
                    <div class="tab-pane fade" id="engagement" role="tabpanel" aria-labelledby="engagement-tab">
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3>Median Number of Participant Messages per Session by Method and Version</h3>
                                    </div>
                                    <div class="card-body">
                                        <div class="table-responsive">
                                            <table class="table table-striped table-hover" id="medianMessagesTable">
                                                <thead class="table-dark">
                                                    <tr>
                                                        <th>Method</th>
                                                        {''.join([f'<th>{metric["version_name"]}</th>' for metric in metrics])}
                                                        <th>All Versions</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {self.generate_median_messages_table_rows(metrics)}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3>Median User Words per Session by Method and Version</h3>
                                    </div>
                                    <div class="card-body">
                                        <div class="mb-3">
                                            <label class="form-label">Display Mode:</label>
                                            <div class="btn-group" role="group" aria-label="Words display mode">
                                                <input type="radio" class="btn-check" name="wordsDisplayMode" id="wordsModePerSession" value="per_session" checked onchange="updateMedianWordsTable()">
                                                <label class="btn btn-outline-primary" for="wordsModePerSession">Per Session</label>
                                                
                                                <input type="radio" class="btn-check" name="wordsDisplayMode" id="wordsModePerMessage" value="per_message" onchange="updateMedianWordsTable()">
                                                <label class="btn btn-outline-primary" for="wordsModePerMessage">Per Message</label>
                                            </div>
                                            <small class="form-text text-muted d-block mt-2">Per Session: Median words per session. Per Message: Median words per session divided by median messages per session.</small>
                                        </div>
                                        <div class="table-responsive">
                                            <table class="table table-striped table-hover" id="medianWordsTable">
                                                <thead class="table-dark">
                                                    <tr>
                                                        <th>Method</th>
                                                        {''.join([f'<th>{metric["version_name"]}</th>' for metric in metrics])}
                                                        <th>All Versions</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {median_words_table_rows}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3>Median User Words - Session Progression Analysis</h3>
                                    </div>
                                    <div class="card-body">
                                        <div class="mb-3">
                                            <div class="row">
                                                <div class="col-md-6">
                                                    <label for="progressionView" class="form-label">Select View:</label>
                                                    <select class="form-select" id="progressionView" onchange="updateProgressionChart()">
                                                        <option value="by_method">By Coaching Method</option>
                                                        <option value="by_method_version">By Coaching Method per Version</option>
                                                        <option value="by_version">By Version</option>
                                                    </select>
                                                </div>
                                                <div class="col-md-6">
                                                    <!-- Outlier filtering now handled by global filters above -->
                                                </div>
                                            </div>
                                        </div>
                                        <div class="chart-container" style="position: relative; height: 400px;">
                                            <canvas id="progressionChart"></canvas>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Session Volume Tab -->
                    <div class="tab-pane fade" id="volume" role="tabpanel" aria-labelledby="volume-tab">
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3>Volume of Session per Coach Version</h3>
                                    </div>
                                    <div class="card-body">
                                        <div class="mb-3">
                                            <div class="row">
                                                <div class="col-md-6">
                                                    <label for="volumeAggregation" class="form-label">Aggregation Level:</label>
                                                    <select class="form-select" id="volumeAggregation" onchange="updateVolumeChart()">
                                                        <option value="day">Day</option>
                                                        <option value="week" selected>Week</option>
                                                        <option value="month">Month</option>
                                                    </select>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="chart-container" style="position: relative; height: 500px;">
                                            <canvas id="volumeChart"></canvas>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3>Session Count by Method and Version</h3>
                                    </div>
                                    <div class="card-body">
                                        <div class="table-responsive">
                                            <table class="table table-striped table-hover">
                                                <thead class="table-dark">
                                                    <tr>
                                                        <th>Method</th>
                                                        {''.join([f'<th>{metric["version_name"]}</th>' for metric in metrics])}
                                                        <th>All Versions</th>
                                                    </tr>
                                                </thead>
                                                <tbody id="sessionCountTableBody">
                                                    {volume_summary_table_rows}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Gold Standard Tab -->
                    <div class="tab-pane fade" id="gold-standard" role="tabpanel" aria-labelledby="gold-standard-tab">
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3>GS Score Brackets</h3>
                                    </div>
                                    <div class="card-body">
                                        <div class="mb-3">
                                            <label class="form-label">Display Mode:</label>
                                            <div class="btn-group" role="group" aria-label="GS brackets display mode">
                                                <input type="radio" class="btn-check" name="gsBracketsDisplayMode" id="gsBracketsModeCount" value="count" checked onchange="updateGSBracketsTable()">
                                                <label class="btn btn-outline-primary" for="gsBracketsModeCount">Count</label>
                                                
                                                <input type="radio" class="btn-check" name="gsBracketsDisplayMode" id="gsBracketsModePercentage" value="percentage" onchange="updateGSBracketsTable()">
                                                <label class="btn btn-outline-primary" for="gsBracketsModePercentage">Percentage</label>
                                            </div>
                                            <small class="form-text text-muted d-block mt-2">Count: Number of FLWs. Percentage: Percentage based on the Total column for each row.</small>
                                        </div>
                                        <div class="table-responsive">
                                            <table class="table table-striped table-hover" id="gsBracketsTable">
                                                <thead class="table-dark">
                                                    <tr>
                                                        <th>Cohort</th>
                                                        <th>coach_vs_control</th>
                                                        <th>0-19%</th>
                                                        <th>20-39%</th>
                                                        <th>40-59%</th>
                                                        <th>60-79%</th>
                                                        <th>80-100%</th>
                                                        <th>Total</th>
                                                    </tr>
                                                </thead>
                                                <tbody id="gsBracketsTableBody">
                                                    {self.generate_flw_breakdown_table_rows(flw_breakdown) if flw_breakdown else '<tr><td colspan="8" class="text-center">No GS data available</td></tr>'}
                                                </tbody>
                                            </table>
                                        </div>
                                        <p class="text-muted mt-3">
                                            <small>Note: Group A = Control, Group B = Coached. GS score brackets: 0-19, 20-39, 40-59, 60-79, 80-100. Click on cohort rows to expand/collapse details.</small>
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3>Average GS Score by Bot Version and Coaching Method</h3>
                                    </div>
                                    <div class="card-body">
                                        <div class="table-responsive">
                                            <table class="table table-striped table-hover">
                                                <thead class="table-dark">
                                                    <tr>
                                                        <th>Method</th>
                                                        {''.join([f'<th>{metric["version_name"]}</th>' for metric in metrics])}
                                                        <th>All Versions</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {self.generate_avg_gs_table_rows(avg_gs_scores, metrics) if avg_gs_scores else f'<tr><td colspan="{len(metrics) + 2}" class="text-center">No GS data available</td></tr>'}
                                                </tbody>
                                            </table>
                                        </div>
                                        <p class="text-muted mt-3">
                                            <small>Note: Average GS scores are calculated for participants who have GS scores and have used the corresponding bot version and coaching method combination.</small>
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- FLW Activity Tab -->
                    <div class="tab-pane fade" id="flw-activity" role="tabpanel" aria-labelledby="flw-activity-tab">
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3>FLW Activity Metrics by Method and Version</h3>
                                    </div>
                                    <div class="card-body">
                                        <div class="mb-3">
                                            <label for="flwActivityMetric" class="form-label">Select Metric:</label>
                                            <select class="form-select" id="flwActivityMetric" onchange="updateFLWActivityTable()">
                                                <option value="approved_visits_percentage" selected>Median Approval Rate (%)</option>
                                                <option value="ecd_completed_intervention_percentage">Median Intervention Completion Rate (%)</option>
                                                <option value="visits_before_gs1">Average Number of Visits Before GS Score</option>
                                                <option value="time_spent_learn">Average Time in Learn Module (days)</option>
                                                <option value="post_test_tries">Average Number of Post Test Tries</option>
                                            </select>
                                        </div>
                                        <div class="table-responsive">
                                            <table class="table table-striped table-hover" id="flwActivityTable">
                                                <thead class="table-dark">
                                                    <tr>
                                                        <th>Coaching Method</th>
                                                        <th>V3</th>
                                                        <th>V4</th>
                                                        <th>V5</th>
                                                        <th>V6</th>
                                                        <th>Control</th>
                                                        <th>All Versions</th>
                                                    </tr>
                                                </thead>
                                                <tbody id="flwActivityTableBody">
                                                    {flw_activity_table_rows}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Second FLW Activity Table -->
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3>Visit Spacing Metrics by Method and Version</h3>
                                    </div>
                                    <div class="card-body">
                                        <div class="mb-3">
                                            <label for="flwVisitSpacingMetric" class="form-label">Select Metric:</label>
                                            <select class="form-select" id="flwVisitSpacingMetric" onchange="updateFLWVisitSpacingTable()">
                                                <option value="avg_distance_km_between_visits" selected>Average Distance Between Visits (km)</option>
                                                <option value="avg_minutes_between_visits">Average Time Between Visits (minutes)</option>
                                            </select>
                                        </div>
                                        <div class="table-responsive">
                                            <table class="table table-striped table-hover" id="flwVisitSpacingTable">
                                                <thead class="table-dark">
                                                    <tr>
                                                        <th>Coaching Method</th>
                                                        <th>V3</th>
                                                        <th>V4</th>
                                                        <th>V5</th>
                                                        <th>V6</th>
                                                        <th>Control</th>
                                                        <th>All Versions</th>
                                                    </tr>
                                                </thead>
                                                <tbody id="flwVisitSpacingTableBody">
                                                    {flw_visit_spacing_table_rows}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Tags Tab -->
                    <div class="tab-pane fade" id="tags" role="tabpanel" aria-labelledby="tags-tab">
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3>Tag Counts by Version and Method</h3>
                                    </div>
                                    <div class="card-body">
                                        <div class="mb-3">
                                            <div class="row mb-3">
                                                <div class="col-12">
                                                    <label class="form-label">Display Mode:</label>
                                                    <div class="btn-group" role="group" aria-label="Tag display mode">
                                                        <input type="radio" class="btn-check" name="tagDisplayMode" id="tagModeCount" value="count" checked onchange="updateTagTable()">
                                                        <label class="btn btn-outline-primary" for="tagModeCount">Count</label>
                                                        
                                                        <input type="radio" class="btn-check" name="tagDisplayMode" id="tagModeGS" value="gs_score" onchange="updateTagTable()">
                                                        <label class="btn btn-outline-primary" for="tagModeGS">GS Score</label>
                                                    </div>
                                                    <small class="form-text text-muted d-block mt-2">Count: Number of sessions with tags. GS Score: Median GS score for participants in tagged sessions.</small>
                                                </div>
                                            </div>
                                            <div class="row">
                                                <div class="col-md-6">
                                                    <label for="versionFilterTags" class="form-label">Filter by Bot Version (multi-select):</label>
                                                    <select class="form-select" id="versionFilterTags" multiple size="6" onchange="updateTagTable()">
                                                        {''.join([f'<option value="{metric["version_name"]}" selected>{metric["version_name"]}</option>' for metric in metrics])}
                                                    </select>
                                                    <small class="form-text text-muted">Hold Ctrl/Cmd to select multiple versions. All versions selected by default.</small>
                                                </div>
                                                <div class="col-md-6">
                                                    <label for="tagFilterTags" class="form-label">Filter by Tag (multi-select):</label>
                                                    <select class="form-select" id="tagFilterTags" multiple size="6" onchange="updateTagTable()">
                                                        <option value="safe" selected>safe</option>
                                                        <option value="unsafe" selected>unsafe</option>
                                                        <option value="acceptable" selected>acceptable</option>
                                                        <option value="unacceptable" selected>unacceptable</option>
                                                        <option value="refrigerator_example" selected>refrigerator_example</option>
                                                        <option value="not_refrigerator_example" selected>not_refrigerator_example</option>
                                                        <option value="bot_performance_good" selected>bot_performance_good</option>
                                                        <option value="bot_performance_bad" selected>bot_performance_bad</option>
                                                        <option value="coaching_good" selected>coaching_good</option>
                                                        <option value="coaching_undetermined" selected>coaching_undetermined</option>
                                                        <option value="coaching_bad" selected>coaching_bad</option>
                                                        <option value="engagement_good" selected>engagement_good</option>
                                                        <option value="engagement_bad" selected>engagement_bad</option>
                                                        <option value="user_knowledge_good" selected>user_knowledge_good</option>
                                                        <option value="user_knowledge_bad" selected>user_knowledge_bad</option>
                                                        <option value="user_ai_response" selected>user_ai_response</option>
                                                    </select>
                                                    <small class="form-text text-muted">Hold Ctrl/Cmd to select multiple tags. All tags selected by default.</small>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="table-responsive">
                                            <table class="table table-striped table-hover" id="tagTable">
                                                <thead class="table-dark" id="tagTableHeader">
                                                    <tr>
                                                        <th rowspan="2">Tag</th>
                                                        <th colspan="2">Total Sessions</th>
                                                        <th colspan="2">Scenario</th>
                                                        <th colspan="2">Microlearning</th>
                                                        <th colspan="2">Microlearning vaccines</th>
                                                        <th colspan="2">Motivational interviewing</th>
                                                        <th colspan="2">Visit check in</th>
                                                        <th colspan="2">Unknown</th>
                                                    </tr>
                                                    <tr>
                                                        <th>Count</th>
                                                        <th>%</th>
                                                        <th>Count</th>
                                                        <th>%</th>
                                                        <th>Count</th>
                                                        <th>%</th>
                                                        <th>Count</th>
                                                        <th>%</th>
                                                        <th>Count</th>
                                                        <th>%</th>
                                                        <th>Count</th>
                                                        <th>%</th>
                                                        <th>Count</th>
                                                        <th>%</th>
                                                    </tr>
                                                </thead>
                                                <tbody id="tagTableBody">
                                                    {self.generate_tag_table_rows(tag_counts, metrics) if tag_counts else '<tr><td colspan="15" class="text-center">No tag data available</td></tr>'}
                                                </tbody>
                                            </table>
                                        </div>
                                        <p class="text-muted mt-3">
                                            <small>Note: A tagged session is a session that carries non-version tags and non-method tags either at session level or message level.</small>
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3>Sessions with Tag Combinations</h3>
                                    </div>
                                    <div class="card-body">
                                        <div class="mb-3">
                                            <div class="row mb-3">
                                                <div class="col-12">
                                                    <label class="form-label">Display Mode:</label>
                                                    <div class="btn-group" role="group" aria-label="Tag combination display mode">
                                                        <input type="radio" class="btn-check" name="tagCombinationDisplayMode" id="tagCombinationModeCount" value="count" checked onchange="updateTagCombinationTable()">
                                                        <label class="btn btn-outline-primary" for="tagCombinationModeCount">Count</label>
                                                        
                                                        <input type="radio" class="btn-check" name="tagCombinationDisplayMode" id="tagCombinationModeGS" value="gs_score" onchange="updateTagCombinationTable()">
                                                        <label class="btn btn-outline-primary" for="tagCombinationModeGS">GS Score</label>
                                                    </div>
                                                    <small class="form-text text-muted d-block mt-2">Count: Number of sessions with tag combinations. GS Score: Median GS score for participants in sessions with tag combinations.</small>
                                                </div>
                                            </div>
                                            <label for="tagCombinationFilter" class="form-label">Select Tag(s) to Filter (multi-select):</label>
                                            <select class="form-select" id="tagCombinationFilter" multiple size="6" onchange="updateTagCombinationTable()">
                                                <option value="safe">safe</option>
                                                <option value="unsafe">unsafe</option>
                                                <option value="acceptable">acceptable</option>
                                                <option value="unacceptable">unacceptable</option>
                                                <option value="refrigerator_example">refrigerator_example</option>
                                                <option value="not_refrigerator_example">not_refrigerator_example</option>
                                                <option value="bot_performance_good">bot_performance_good</option>
                                                <option value="bot_performance_bad">bot_performance_bad</option>
                                                <option value="coaching_good">coaching_good</option>
                                                <option value="coaching_undetermined">coaching_undetermined</option>
                                                <option value="coaching_bad">coaching_bad</option>
                                                <option value="engagement_good">engagement_good</option>
                                                <option value="engagement_bad">engagement_bad</option>
                                                <option value="user_knowledge_good">user_knowledge_good</option>
                                                <option value="user_knowledge_bad">user_knowledge_bad</option>
                                                <option value="user_ai_response">user_ai_response</option>
                                            </select>
                                            <small class="form-text text-muted">Hold Ctrl/Cmd to select multiple tags. Sessions must have ALL selected tags (at session or message level).</small>
                                        </div>
                                        <div class="table-responsive">
                                            <table class="table table-striped table-hover" id="tagCombinationTable">
                                                <thead class="table-dark" id="tagCombinationTableHeader">
                                                    <tr>
                                                        <th>Method</th>
                                                        {''.join([f'<th colspan="2">{metric["version_name"]}</th>' for metric in metrics])}
                                                    </tr>
                                                    <tr>
                                                        <th></th>
                                                        {''.join([f'<th>Count</th><th>%</th>' for metric in metrics])}
                                                    </tr>
                                                </thead>
                                                <tbody id="tagCombinationTableBody">
                                                    <tr><td colspan="{len(metrics) * 2 + 1}" class="text-center">Select one or more tags to see results</td></tr>
                                                </tbody>
                                            </table>
                                        </div>
                                        <p class="text-muted mt-3">
                                            <small>Note: Shows sessions that have ALL selected tags. Percentage is based on total tagged sessions for that version/method combination.</small>
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Definitions Tab -->
                    <div class="tab-pane fade" id="definitions" role="tabpanel" aria-labelledby="definitions-tab">
        <div class="row mt-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h3>Definitions</h3>
                    </div>
                    <div class="card-body">
                                        <h5>Version Definitions</h5>
                                        <p>This dashboard compares five bot categories based on experiment IDs and version ranges:</p>
                                        <ul>
                                            <li><strong>Control bot:</strong> Experiment ID: 1027993a-40c9-4484-a5fb-5c7e034dadcd (All versions)</li>
                                            <li><strong>Coaching bot V3:</strong> Experiment ID: e2b4855f-8550-47ff-87d2-d92018676ff3 (All versions)</li>
                                            <li><strong>Coaching bot V4:</strong> Experiment ID: b7621271-da98-459f-9f9b-f68335d09ad4 (Version 13 and above)</li>
                                            <li><strong>Coaching bot V5:</strong> Experiment ID: 5d8be75e-03ff-4e3a-ab6a-e0aff6580986 (Version 1 to 4)</li>
                                            <li><strong>Coaching bot V6:</strong> Experiment ID: 5d8be75e-03ff-4e3a-ab6a-e0aff6580986 (Version 5 and above)</li>
                                        </ul>
                                        
                                        <h5>Coaching Methods</h5>
                                        <p>Coaching methods are detected through a 3-tier approach:</p>
                                        <ul>
                                            <li><strong>Scenario:</strong> Roleplay and scenario-based coaching</li>
                                            <li><strong>Microlearning:</strong> Quiz and microlearning sessions</li>
                                            <li><strong>Microlearning vaccines:</strong> Vaccine-specific quiz sessions</li>
                                            <li><strong>Motivational interviewing:</strong> Motivational interview techniques</li>
                                            <li><strong>Visit check in:</strong> Home visit debrief sessions</li>
                                        </ul>
                                        
                                        <h5 class="mt-4">Average FLW Score by Method and Version</h5>
                                        <p>This metric shows the average session rating (1-5 scale) grouped by coaching method and bot version.</p>
                                        <ul>
                                            <li><strong>Calculation:</strong> Average of user ratings for sessions ending with "How useful did you find this coaching session? Please rate it from 1 to 5"</li>
                                            <li><strong>Rating Scale:</strong> 1 (not useful) to 5 (very useful)</li>
                                            <li><strong>Method Detection:</strong> Based on session tags (coach_method_*) or message content analysis</li>
                                            <li><strong>Version Detection:</strong> Based on experiment ID and version tags from last message</li>
                                            <li><strong>Purpose:</strong> Identify whether coaching methods receive higher ratings with bot evolution</li>
                                        </ul>
                                        
                                        <h5 class="mt-4">Median Number of Participant Messages per Session by Method and Version</h5>
                                        <p>This metric shows the median number of messages participants send per session, grouped by coaching method and bot version.</p>
                                        <ul>
                                            <li><strong>Calculation:</strong> Median count of user messages within a session</li>
                                            <li><strong>Method Detection:</strong> Based on session tags (coach_method_*) or message content analysis</li>
                                            <li><strong>Version Detection:</strong> Based on experiment ID and version tags from last message</li>
                                            <li><strong>Message Count:</strong> Total number of user messages in a session</li>
                                        </ul>
                                        
                                        <h5 class="mt-4">Median User Words per Session by Method and Version</h5>
                                        <p>This metric shows the median number of words users type per session, grouped by coaching method and bot version.</p>
                                        <ul>
                                            <li><strong>Calculation:</strong> Median word count of all user messages within a session</li>
                                            <li><strong>Method Detection:</strong> Based on session tags (coach_method_*) or message content analysis</li>
                                            <li><strong>Version Detection:</strong> Based on experiment ID and version tags from last message</li>
                                            <li><strong>Word Count:</strong> Total words across all user messages in a session</li>
                                            <li><strong>Outlier Filtering:</strong> Optional checkbox to exclude sessions with >50 messages or >1000 words</li>
                                        </ul>
                                        
                                        <h6>Session Numbering:</h6>
                                        <p>For line graph analysis, sessions are numbered chronologically per participant:</p>
                                        <ul>
                                            <li><strong>Participant ID:</strong> Based on participant.identifier field</li>
                                            <li><strong>Chronological Order:</strong> Sorted by session created_at timestamp</li>
                                            <li><strong>Session Number:</strong> Position in participant's session sequence (1st, 2nd, 3rd, etc.)</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        // Progression data from server
        const progressionData = {progression_data_json};
        const progressionDataFiltered = {progression_data_filtered_json};
        
        // Volume data from server
        const volumeDataDay = {volume_data_day_json};
        const volumeDataWeek = {volume_data_week_json};
        const volumeDataMonth = {volume_data_month_json};
        
        // Refrigerator-filtered volume data from server
        const volumeDataRefrigeratorDay = {volume_data_refrigerator_day_json};
        const volumeDataRefrigeratorWeek = {volume_data_refrigerator_week_json};
        const volumeDataRefrigeratorMonth = {volume_data_refrigerator_month_json};
        
        // Metrics data from server (for dynamic table updates)
        const metricsData = {metrics_json};
        
        // Session to participant mapping for filtering
        const sessionParticipantMap = {session_participant_map_json};
        
        // Volume session mappings (which sessions contribute to each count)
        const volumeSessionMaps = {volume_session_maps_json};
        
        // Progression session-level data for filtering
        const progressionSessionData = {progression_session_data_json};
        const progressionSessionDataFiltered = {progression_session_data_filtered_json};
        
        // Tag counts data from server
        const tagCountsData = {tag_counts_json};
        
        // Tag GS scores data from server
        const tagGScoresData = {tag_gs_scores_json};
        
        // Tag combination data from server
        const tagCombinationData = {tag_combination_data_json};
        
        // Tag combination GS data from server
        const tagCombinationGSData = {tag_combination_gs_data_json};
        
        // Rating distribution data from server
        const ratingDistributionData = {rating_distribution_json};
        
        // FLW activity metrics data from server
        const flwActivityMetricsData = {flw_activity_metrics_json};
        
        // Function to update FLW activity table based on selected metric
        function updateFLWActivityTable() {{
            const metricSelect = document.getElementById('flwActivityMetric');
            const selectedMetric = metricSelect.value;
            const tbody = document.getElementById('flwActivityTableBody');
            
            if (!flwActivityMetricsData || !flwActivityMetricsData[selectedMetric]) {{
                tbody.innerHTML = '<tr><td colspan="7" class="text-center">No data available for selected metric</td></tr>';
                return;
            }}
            
            const metricData = flwActivityMetricsData[selectedMetric];
            const methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown'];
            const versions = ['V3', 'V4', 'V5', 'V6', 'Control'];
            
            let rows = '';
            
            // Generate rows for each method
            for (const method of methods) {{
                let row = `<tr><td><strong>${{method}}</strong></td>`;
                const versionValues = [];
                
                // Add version columns
                for (const version of versions) {{
                    const value = metricData[method]?.[version];
                    if (value !== null && value !== undefined) {{
                        if (selectedMetric === 'approved_visits_percentage' || selectedMetric === 'ecd_completed_intervention_percentage') {{
                            row += `<td>${{value.toFixed(1)}}%</td>`;
                        }} else if (selectedMetric === 'time_spent_learn') {{
                            row += `<td>${{value.toFixed(2)}}</td>`;
                        }} else {{
                            row += `<td>${{value.toFixed(2)}}</td>`;
                        }}
                        versionValues.push(value);
                    }} else {{
                        row += '<td>-</td>';
                    }}
                }}
                
                // "All Versions" column
                if (versionValues.length > 0) {{
                    let allVersionsValue;
                    if (selectedMetric === 'approved_visits_percentage' || selectedMetric === 'ecd_completed_intervention_percentage') {{
                        // Median of medians
                        const sorted = versionValues.slice().sort((a, b) => a - b);
                        const n = sorted.length;
                        allVersionsValue = n % 2 === 0 
                            ? (sorted[n/2 - 1] + sorted[n/2]) / 2 
                            : sorted[Math.floor(n/2)];
                        row += `<td><strong>${{allVersionsValue.toFixed(1)}}%</strong></td>`;
                    }} else {{
                        // Average of averages
                        allVersionsValue = versionValues.reduce((a, b) => a + b, 0) / versionValues.length;
                        if (selectedMetric === 'time_spent_learn') {{
                            row += `<td><strong>${{allVersionsValue.toFixed(2)}}</strong></td>`;
                        }} else {{
                            row += `<td><strong>${{allVersionsValue.toFixed(2)}}</strong></td>`;
                        }}
                    }}
                }} else {{
                    row += '<td>-</td>';
                }}
                
                row += '</tr>';
                rows += row;
            }}
            
            // Add "Total (All Methods)" row
            let totalRow = '<tr><td><strong>Total (All Methods)</strong></td>';
            for (const version of versions) {{
                const versionValues = methods
                    .map(method => metricData[method]?.[version])
                    .filter(v => v !== null && v !== undefined);
                
                if (versionValues.length > 0) {{
                    let totalValue;
                    if (selectedMetric === 'approved_visits_percentage' || selectedMetric === 'ecd_completed_intervention_percentage') {{
                        const sorted = versionValues.slice().sort((a, b) => a - b);
                        const n = sorted.length;
                        totalValue = n % 2 === 0 
                            ? (sorted[n/2 - 1] + sorted[n/2]) / 2 
                            : sorted[Math.floor(n/2)];
                        totalRow += `<td><strong>${{totalValue.toFixed(1)}}%</strong></td>`;
                    }} else {{
                        totalValue = versionValues.reduce((a, b) => a + b, 0) / versionValues.length;
                        if (selectedMetric === 'time_spent_learn') {{
                            totalRow += `<td><strong>${{totalValue.toFixed(2)}}</strong></td>`;
                        }} else {{
                            totalRow += `<td><strong>${{totalValue.toFixed(2)}}</strong></td>`;
                        }}
                    }}
                }} else {{
                    totalRow += '<td>-</td>';
                }}
            }}
            
            // "All Versions" column for total row
            const allMethodVersionValues = [];
            for (const method of methods) {{
                for (const version of versions) {{
                    const value = metricData[method]?.[version];
                    if (value !== null && value !== undefined) {{
                        allMethodVersionValues.push(value);
                    }}
                }}
            }}
            
            if (allMethodVersionValues.length > 0) {{
                let grandTotal;
                if (selectedMetric === 'approved_visits_percentage' || selectedMetric === 'ecd_completed_intervention_percentage') {{
                    const sorted = allMethodVersionValues.slice().sort((a, b) => a - b);
                    const n = sorted.length;
                    grandTotal = n % 2 === 0 
                        ? (sorted[n/2 - 1] + sorted[n/2]) / 2 
                        : sorted[Math.floor(n/2)];
                    totalRow += `<td><strong>${{grandTotal.toFixed(1)}}%</strong></td>`;
                }} else {{
                    grandTotal = allMethodVersionValues.reduce((a, b) => a + b, 0) / allMethodVersionValues.length;
                    if (selectedMetric === 'time_spent_learn') {{
                        totalRow += `<td><strong>${{grandTotal.toFixed(2)}}</strong></td>`;
                    }} else {{
                        totalRow += `<td><strong>${{grandTotal.toFixed(2)}}</strong></td>`;
                    }}
                }}
            }} else {{
                totalRow += '<td>-</td>';
            }}
            
            totalRow += '</tr>';
            rows += totalRow;
            
            tbody.innerHTML = rows;
        }}
        
        // Function to update FLW visit spacing table based on selected metric
        function updateFLWVisitSpacingTable() {{
            const metricSelect = document.getElementById('flwVisitSpacingMetric');
            const selectedMetric = metricSelect.value;
            const tbody = document.getElementById('flwVisitSpacingTableBody');
            
            if (!flwActivityMetricsData || !flwActivityMetricsData[selectedMetric]) {{
                tbody.innerHTML = '<tr><td colspan="7" class="text-center">No data available for selected metric</td></tr>';
                return;
            }}
            
            const metricData = flwActivityMetricsData[selectedMetric];
            const methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown'];
            const versions = ['V3', 'V4', 'V5', 'V6', 'Control'];
            
            let rows = '';
            
            // Generate rows for each method
            for (const method of methods) {{
                let row = `<tr><td><strong>${{method}}</strong></td>`;
                const versionValues = [];
                
                // Add version columns
                for (const version of versions) {{
                    const value = metricData[method]?.[version];
                    if (value !== null && value !== undefined) {{
                        // Both metrics are averages, display with 2 decimal places
                        row += `<td>${{value.toFixed(2)}}</td>`;
                        versionValues.push(value);
                    }} else {{
                        row += '<td>-</td>';
                    }}
                }}
                
                // "All Versions" column - average of averages
                if (versionValues.length > 0) {{
                    const allVersionsValue = versionValues.reduce((a, b) => a + b, 0) / versionValues.length;
                    row += `<td><strong>${{allVersionsValue.toFixed(2)}}</strong></td>`;
                }} else {{
                    row += '<td>-</td>';
                }}
                
                row += '</tr>';
                rows += row;
            }}
            
            // Add "Total (All Methods)" row
            let totalRow = '<tr><td><strong>Total (All Methods)</strong></td>';
            for (const version of versions) {{
                const versionValues = methods
                    .map(method => metricData[method]?.[version])
                    .filter(v => v !== null && v !== undefined);
                
                if (versionValues.length > 0) {{
                    const totalValue = versionValues.reduce((a, b) => a + b, 0) / versionValues.length;
                    totalRow += `<td><strong>${{totalValue.toFixed(2)}}</strong></td>`;
                }} else {{
                    totalRow += '<td>-</td>';
                }}
            }}
            
            // "All Versions" column for total row - average of averages
            const allMethodVersionValues = [];
            for (const method of methods) {{
                for (const version of versions) {{
                    const value = metricData[method]?.[version];
                    if (value !== null && value !== undefined) {{
                        allMethodVersionValues.push(value);
                    }}
                }}
            }}
            
            if (allMethodVersionValues.length > 0) {{
                const grandTotal = allMethodVersionValues.reduce((a, b) => a + b, 0) / allMethodVersionValues.length;
                totalRow += `<td><strong>${{grandTotal.toFixed(2)}}</strong></td>`;
            }} else {{
                totalRow += '<td>-</td>';
            }}
            
            totalRow += '</tr>';
            rows += totalRow;
            
            tbody.innerHTML = rows;
        }}
        
        // Function to update tag table header based on mode
        function updateTagTableHeader(mode) {{
            const header = document.getElementById('tagTableHeader');
            if (!header) return;
            
            if (mode === 'gs_score') {{
                header.innerHTML = `
                    <tr>
                        <th rowspan="2">Tag</th>
                        <th colspan="2">Total</th>
                        <th colspan="2">Scenario</th>
                        <th colspan="2">Microlearning</th>
                        <th colspan="2">Microlearning vaccines</th>
                        <th colspan="2">Motivational interviewing</th>
                        <th colspan="2">Visit check in</th>
                        <th colspan="2">Unknown</th>
                    </tr>
                    <tr>
                        <th>Median GS</th>
                        <th>-</th>
                        <th>Median GS</th>
                        <th>-</th>
                        <th>Median GS</th>
                        <th>-</th>
                        <th>Median GS</th>
                        <th>-</th>
                        <th>Median GS</th>
                        <th>-</th>
                        <th>Median GS</th>
                        <th>-</th>
                        <th>Median GS</th>
                        <th>-</th>
                    </tr>
                `;
            }} else {{
                header.innerHTML = `
                    <tr>
                        <th rowspan="2">Tag</th>
                        <th colspan="2">Total Sessions</th>
                        <th colspan="2">Scenario</th>
                        <th colspan="2">Microlearning</th>
                        <th colspan="2">Microlearning vaccines</th>
                        <th colspan="2">Motivational interviewing</th>
                        <th colspan="2">Visit check in</th>
                        <th colspan="2">Unknown</th>
                    </tr>
                    <tr>
                        <th>Count</th>
                        <th>%</th>
                        <th>Count</th>
                        <th>%</th>
                        <th>Count</th>
                        <th>%</th>
                        <th>Count</th>
                        <th>%</th>
                        <th>Count</th>
                        <th>%</th>
                        <th>Count</th>
                        <th>%</th>
                        <th>Count</th>
                        <th>%</th>
                    </tr>
                `;
            }}
        }}
        
        // Function to update tag table based on selected versions and tags
        function updateTagTable() {{
            const versionSelect = document.getElementById('versionFilterTags');
            const tagSelect = document.getElementById('tagFilterTags');
            const tableBody = document.getElementById('tagTableBody');
            const modeRadios = document.querySelectorAll('input[name="tagDisplayMode"]');
            if (!versionSelect || !tagSelect || !tableBody || !modeRadios.length) return;
            
            // Get selected mode
            const selectedMode = Array.from(modeRadios).find(r => r.checked)?.value || 'count';
            
            // Update header
            updateTagTableHeader(selectedMode);
            
            if (selectedMode === 'gs_score') {{
                if (!tagGScoresData || Object.keys(tagGScoresData).length === 0) {{
                    tableBody.innerHTML = '<tr><td colspan="15" class="text-center">No GS score data available</td></tr>';
                    return;
                }}
                
                // Get selected versions
                const selectedVersions = Array.from(versionSelect.selectedOptions).map(opt => opt.value);
                const versionsToShow = selectedVersions.length > 0 ? selectedVersions : Object.keys(tagGScoresData).filter(v => v !== 'All Versions');
                
                // Get selected tags
                const selectedTags = Array.from(tagSelect.selectedOptions).map(opt => opt.value);
                const tagsToTrack = [
                    'safe', 'unsafe', 'acceptable', 'unacceptable',
                    'refrigerator_example', 'not_refrigerator_example',
                    'bot_performance_good', 'bot_performance_bad',
                    'coaching_good', 'coaching_undetermined', 'coaching_bad',
                    'engagement_good', 'engagement_bad',
                    'user_knowledge_good', 'user_knowledge_bad',
                    'user_ai_response'
                ];
                const tagsToShow = selectedTags.length > 0 ? selectedTags : tagsToTrack;
                
                const methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown'];
                
                let html = '';
                
                // Generate rows for each selected tag
                tagsToShow.forEach(tag => {{
                    html += `<tr><td><strong>${{tag}}</strong></td>`;
                    
                    // Collect all GS scores for this tag across selected versions
                    const allScores = [];
                    versionsToShow.forEach(version => {{
                        if (tagGScoresData[version] && tagGScoresData[version][tag]) {{
                            const score = tagGScoresData[version][tag].total;
                            if (score !== undefined && score !== null) {{
                                allScores.push(score);
                            }}
                        }}
                    }});
                    
                    // Calculate total median
                    const totalMedian = allScores.length > 0 ? allScores.reduce((a, b) => a + b, 0) / allScores.length : null;
                    if (totalMedian !== null) {{
                        // Calculate median properly
                        const sorted = allScores.slice().sort((a, b) => a - b);
                        const mid = Math.floor(sorted.length / 2);
                        const median = sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
                        html += `<td>${{median.toFixed(1)}}</td><td>-</td>`;
                    }} else {{
                        html += '<td>-</td><td>-</td>';
                    }}
                    
                    // Median by method (aggregated across selected versions)
                    const methodScores = {{}};
                    methods.forEach(method => methodScores[method] = []);
                    
                    versionsToShow.forEach(version => {{
                        if (tagGScoresData[version] && tagGScoresData[version][tag]) {{
                            methods.forEach(method => {{
                                const score = tagGScoresData[version][tag][method];
                                if (score !== undefined && score !== null) {{
                                    methodScores[method].push(score);
                                }}
                            }});
                        }}
                    }});
                    
                    methods.forEach(method => {{
                        const scores = methodScores[method];
                        if (scores.length > 0) {{
                            const sorted = scores.slice().sort((a, b) => a - b);
                            const mid = Math.floor(sorted.length / 2);
                            const median = sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
                            html += `<td>${{median.toFixed(1)}}</td><td>-</td>`;
                        }} else {{
                            html += '<td>-</td><td>-</td>';
                        }}
                    }});
                    
                    html += '</tr>';
                }});
                
                // Add Total row (not applicable for GS scores, but keep for consistency)
                html += '<tr><td><strong>Total</strong></td>';
                html += '<td><strong>-</strong></td><td><strong>-</strong></td>';
                methods.forEach(() => {{
                    html += '<td><strong>-</strong></td><td><strong>-</strong></td>';
                }});
                html += '</tr>';
                
                tableBody.innerHTML = html;
            }} else {{
                // Count mode (original logic)
                if (!tagCountsData) {{
                    tableBody.innerHTML = '<tr><td colspan="15" class="text-center">No tag data available</td></tr>';
                    return;
                }}
                
                // Get selected versions
                const selectedVersions = Array.from(versionSelect.selectedOptions).map(opt => opt.value);
                const versionsToShow = selectedVersions.length > 0 ? selectedVersions : Object.keys(tagCountsData).filter(v => v !== 'All Versions');
                
                // Get selected tags
                const selectedTags = Array.from(tagSelect.selectedOptions).map(opt => opt.value);
                const tagsToTrack = [
                    'safe', 'unsafe', 'acceptable', 'unacceptable',
                    'refrigerator_example', 'not_refrigerator_example',
                    'bot_performance_good', 'bot_performance_bad',
                    'coaching_good', 'coaching_undetermined', 'coaching_bad',
                    'engagement_good', 'engagement_bad',
                    'user_knowledge_good', 'user_knowledge_bad',
                    'user_ai_response'
                ];
                const tagsToShow = selectedTags.length > 0 ? selectedTags : tagsToTrack;
                
                const methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown'];
                
                // Calculate total tagged sessions per method across selected versions
                const totalTaggedByMethod = {{}};
                methods.forEach(method => totalTaggedByMethod[method] = 0);
                let totalTaggedSessions = 0;
                
                versionsToShow.forEach(version => {{
                    if (tagCountsData[version] && tagCountsData[version]['_tagged_sessions']) {{
                        totalTaggedSessions += tagCountsData[version]['_tagged_sessions'].total || 0;
                        methods.forEach(method => {{
                            totalTaggedByMethod[method] += tagCountsData[version]['_tagged_sessions'][method] || 0;
                        }});
                    }}
                }});
                
                let html = '';
                
                // Generate rows for each selected tag
                tagsToShow.forEach(tag => {{
                    html += `<tr><td><strong>${{tag}}</strong></td>`;
                    
                    // Total count across selected versions
                    let totalCount = 0;
                    versionsToShow.forEach(version => {{
                        if (tagCountsData[version] && tagCountsData[version][tag]) {{
                            totalCount += tagCountsData[version][tag].total || 0;
                        }}
                    }});
                    
                    // Total percentage
                    const totalPercentage = totalTaggedSessions > 0 ? (totalCount / totalTaggedSessions * 100) : 0;
                    html += `<td>${{totalCount}}</td><td>${{totalPercentage.toFixed(1)}}%</td>`;
                    
                    // Count by method (aggregated across selected versions)
                    const methodTotals = {{}};
                    methods.forEach(method => methodTotals[method] = 0);
                    
                    versionsToShow.forEach(version => {{
                        if (tagCountsData[version] && tagCountsData[version][tag]) {{
                            methods.forEach(method => {{
                                methodTotals[method] += tagCountsData[version][tag][method] || 0;
                            }});
                        }}
                    }});
                    
                    methods.forEach(method => {{
                        const count = methodTotals[method];
                        // Percentage: count for this method / total count for this tag
                        const percentage = totalCount > 0 ? (count / totalCount * 100) : 0;
                        html += `<td>${{count}}</td><td>${{percentage.toFixed(1)}}%</td>`;
                    }});
                    
                    html += '</tr>';
                }});
                
                // Add Total row
                html += '<tr><td><strong>Total</strong></td>';
                html += `<td><strong>${{totalTaggedSessions}}</strong></td><td><strong>100.0%</strong></td>`;
                
                // Total by method - sum across selected versions
                const totalByMethod = {{}};
                methods.forEach(method => totalByMethod[method] = 0);
                
                versionsToShow.forEach(version => {{
                    if (tagCountsData[version] && tagCountsData[version]['_tagged_sessions']) {{
                        methods.forEach(method => {{
                            totalByMethod[method] += tagCountsData[version]['_tagged_sessions'][method] || 0;
                        }});
                    }}
                }});
                
                methods.forEach(method => {{
                    const count = totalByMethod[method];
                    const percentage = totalTaggedSessions > 0 ? (count / totalTaggedSessions * 100) : 0;
                    html += `<td><strong>${{count}}</strong></td><td><strong>${{percentage.toFixed(1)}}%</strong></td>`;
                }});
                
                html += '</tr>';
                
                tableBody.innerHTML = html;
            }}
        }}
        
        // Function to update tag combination table header based on mode
        function updateTagCombinationTableHeader(mode) {{
            const header = document.getElementById('tagCombinationTableHeader');
            if (!header) return;
            
            const versionNames = {json.dumps([m['version_name'] for m in metrics])};
            
            if (mode === 'gs_score') {{
                header.innerHTML = `
                    <tr>
                        <th>Method</th>
                        ${{versionNames.map(v => `<th colspan="2">${{v}}</th>`).join('')}}
                    </tr>
                    <tr>
                        <th></th>
                        ${{versionNames.map(() => '<th>Median GS</th><th>-</th>').join('')}}
                    </tr>
                `;
            }} else {{
                header.innerHTML = `
                    <tr>
                        <th>Method</th>
                        ${{versionNames.map(v => `<th colspan="2">${{v}}</th>`).join('')}}
                    </tr>
                    <tr>
                        <th></th>
                        ${{versionNames.map(() => '<th>Count</th><th>%</th>').join('')}}
                    </tr>
                `;
            }}
        }}
        
        // Function to update tag combination table
        function updateTagCombinationTable() {{
            const select = document.getElementById('tagCombinationFilter');
            const tableBody = document.getElementById('tagCombinationTableBody');
            const modeRadios = document.querySelectorAll('input[name="tagCombinationDisplayMode"]');
            if (!select || !tableBody || !modeRadios.length) return;
            
            // Get selected mode
            const selectedMode = Array.from(modeRadios).find(r => r.checked)?.value || 'count';
            
            // Update header
            updateTagCombinationTableHeader(selectedMode);
            
            // Get selected tags
            const selectedTags = Array.from(select.selectedOptions).map(opt => opt.value);
            
            if (selectedTags.length === 0) {{
                const numCols = {len(metrics) * 2 + 1};
                tableBody.innerHTML = '<tr><td colspan="' + numCols + '" class="text-center">Select one or more tags to see results</td></tr>';
                return;
            }}
            
            const methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown'];
            const versionNames = {json.dumps([m['version_name'] for m in metrics])};
            
            if (selectedMode === 'gs_score') {{
                if (!tagCombinationGSData || Object.keys(tagCombinationGSData).length === 0) {{
                    const numCols = {len(metrics) * 2 + 1};
                    tableBody.innerHTML = '<tr><td colspan="' + numCols + '" class="text-center">No GS score data available</td></tr>';
                    return;
                }}
                
                // Calculate GS scores for each version/method combination
                const gsScores = {{}};
                
                versionNames.forEach(version => {{
                    gsScores[version] = {{}};
                    methods.forEach(method => {{
                        gsScores[version][method] = [];
                        
                        if (tagCombinationGSData[version] && tagCombinationGSData[version][method]) {{
                            const sessionsData = tagCombinationGSData[version][method].sessions || {{}};
                            const gsScoresData = tagCombinationGSData[version][method].gs_scores || {{}};
                            
                            // Collect GS scores for sessions that have ALL selected tags
                            Object.keys(sessionsData).forEach(sessionId => {{
                                const sessionTags = sessionsData[sessionId] || [];
                                const hasAllTags = selectedTags.every(tag => sessionTags.includes(tag));
                                if (hasAllTags && gsScoresData[sessionId] !== undefined && gsScoresData[sessionId] !== null) {{
                                    gsScores[version][method].push(gsScoresData[sessionId]);
                                }}
                            }});
                        }}
                    }});
                }});
                
                // Generate table rows
                let html = '';
                methods.forEach(method => {{
                    html += `<tr><td><strong>${{method}}</strong></td>`;
                    versionNames.forEach(version => {{
                        const scores = gsScores[version][method] || [];
                        if (scores.length > 0) {{
                            // Calculate median
                            const sorted = scores.slice().sort((a, b) => a - b);
                            const mid = Math.floor(sorted.length / 2);
                            const median = sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
                            html += `<td>${{median.toFixed(1)}}</td><td>-</td>`;
                        }} else {{
                            html += '<td>-</td><td>-</td>';
                        }}
                    }});
                    html += '</tr>';
                }});
                
                tableBody.innerHTML = html;
            }} else {{
                // Count mode (original logic)
                if (!tagCombinationData) {{
                    const numCols = {len(metrics) * 2 + 1};
                    tableBody.innerHTML = '<tr><td colspan="' + numCols + '" class="text-center">No tag data available</td></tr>';
                    return;
                }}
                
                // Calculate counts for each version/method combination
                const counts = {{}};
                const totalTagged = {{}};
                
                versionNames.forEach(version => {{
                    counts[version] = {{}};
                    totalTagged[version] = {{}};
                    methods.forEach(method => {{
                        counts[version][method] = 0;
                        totalTagged[version][method] = 0;
                        
                        if (tagCombinationData[version] && tagCombinationData[version][method]) {{
                            const sessionsData = tagCombinationData[version][method].sessions || {{}};
                            totalTagged[version][method] = tagCombinationData[version][method].total_tagged || 0;
                            
                            // Count sessions that have ALL selected tags
                            Object.keys(sessionsData).forEach(sessionId => {{
                                const sessionTags = sessionsData[sessionId] || [];
                                const hasAllTags = selectedTags.every(tag => sessionTags.includes(tag));
                                if (hasAllTags) {{
                                    counts[version][method]++;
                                }}
                            }});
                        }}
                    }});
                }});
                
                // Generate table rows
                let html = '';
                methods.forEach(method => {{
                    html += `<tr><td><strong>${{method}}</strong></td>`;
                    versionNames.forEach(version => {{
                        const count = counts[version][method] || 0;
                        const total = totalTagged[version][method] || 0;
                        const percentage = total > 0 ? (count / total * 100) : 0;
                        html += `<td>${{count}}</td><td>${{percentage.toFixed(1)}}%</td>`;
                    }});
                    html += '</tr>';
                }});
                
                tableBody.innerHTML = html;
            }}
        }}
        
        // Table rows for refrigerator filter toggle (as JSON strings for safe embedding)
        const summaryTableRows = {json.dumps(table_rows)};
        const summaryTableRowsRefrigerator = {json.dumps(table_rows_refrigerator)};
        const refrigeratorRateTableRows = {json.dumps(method_table_rows)};
        const refrigeratorRateTableRowsRefrigerator = {json.dumps(method_table_rows_refrigerator)};
        const averageRatingTableRows = {json.dumps(rating_table_rows)};
        const averageRatingTableRowsRefrigerator = {json.dumps(rating_table_rows_refrigerator)};
        const sessionCountTableRows = {json.dumps(volume_summary_table_rows)};
        const sessionCountTableRowsRefrigerator = {json.dumps(volume_summary_table_rows_refrigerator)};
        
        let progressionChart = null;
        let volumeChart = null;
        let ratingDistributionChart = null;
        
        // Function to update rating distribution chart
        function updateRatingDistributionChart() {{
            const methodSelect = document.getElementById('ratingChartMethodFilter');
            const versionSelect = document.getElementById('ratingChartVersionFilter');
            const canvas = document.getElementById('ratingDistributionChart');
            
            if (!methodSelect || !versionSelect || !canvas || !ratingDistributionData) return;
            
            const selectedMethod = methodSelect.value;
            const selectedVersion = versionSelect.value;
            
            // Get data based on filters
            let percentages = {{}};
            let total = 0;
            
            if (selectedMethod === 'all' && selectedVersion === 'all') {{
                // All sessions
                percentages = ratingDistributionData.all?.percentages || {{}};
                total = ratingDistributionData.all?.total || 0;
            }} else if (selectedMethod !== 'all' && selectedVersion === 'all') {{
                // Filter by method only
                const methodData = ratingDistributionData.by_method?.percentages?.[selectedMethod] || {{}};
                const methodCounts = ratingDistributionData.by_method?.counts?.[selectedMethod] || {{}};
                percentages = methodData;
                total = Object.values(methodCounts).reduce((sum, count) => sum + count, 0);
            }} else if (selectedMethod === 'all' && selectedVersion !== 'all') {{
                // Filter by version only
                const versionData = ratingDistributionData.by_version?.percentages?.[selectedVersion] || {{}};
                const versionCounts = ratingDistributionData.by_version?.counts?.[selectedVersion] || {{}};
                percentages = versionData;
                total = Object.values(versionCounts).reduce((sum, count) => sum + count, 0);
            }} else {{
                // Filter by both method and version
                const methodVersionData = ratingDistributionData.by_method_version?.percentages?.[selectedMethod]?.[selectedVersion] || {{}};
                const methodVersionCounts = ratingDistributionData.by_method_version?.counts?.[selectedMethod]?.[selectedVersion] || {{}};
                percentages = methodVersionData;
                total = Object.values(methodVersionCounts).reduce((sum, count) => sum + count, 0);
            }}
            
            // Prepare data for chart (ratings 1-5)
            const labels = ['1', '2', '3', '4', '5'];
            const data = labels.map(rating => percentages[parseInt(rating)] || 0);
            
            // Destroy existing chart if it exists
            if (ratingDistributionChart) {{
                ratingDistributionChart.destroy();
            }}
            
            // Create new chart
            const ctx = canvas.getContext('2d');
            ratingDistributionChart = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: labels,
                    datasets: [{{
                        label: 'Percentage of Sessions',
                        data: data,
                        backgroundColor: 'rgba(54, 162, 235, 0.6)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: false
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    const rating = context.label;
                                    const percentage = context.parsed.y;
                                    const count = Math.round((percentage / 100) * total);
                                    return `Rating ${{rating}}: ${{percentage.toFixed(1)}}% (${{count}} sessions)`;
                                }}
                            }}
                        }},
                        title: {{
                            display: true,
                            text: `Total Sessions: ${{total}}`
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            max: 100,
                            ticks: {{
                                callback: function(value) {{
                                    return value + '%';
                                }}
                            }},
                            title: {{
                                display: true,
                                text: 'Percentage of Sessions (%)'
                            }}
                        }},
                        x: {{
                            title: {{
                                display: true,
                                text: 'Rating'
                            }}
                        }}
                    }}
                }}
            }});
        }}
        
        // Initialize rating distribution chart on page load
        if (document.getElementById('ratingDistributionChart')) {{
            updateRatingDistributionChart();
        }}
        
        // Function to toggle cohort rows (expand/collapse)
        function toggleCohort(cohort) {{
            const detailRows = document.querySelectorAll(`tr.cohort-detail[data-cohort="${{cohort}}"]`);
            const headerRow = document.querySelector(`tr.cohort-header[data-cohort="${{cohort}}"]`);
            const icon = document.getElementById(`icon-${{cohort}}`);
            
            if (detailRows.length === 0 || !headerRow) return;
            
            const isExpanded = detailRows[0].style.display !== 'none';
            
            if (isExpanded) {{
                // Collapse: hide detail rows
                detailRows.forEach(row => {{
                    row.style.display = 'none';
                }});
                if (icon) {{
                    icon.className = 'fas fa-chevron-right cohort-icon';
                }}
            }} else {{
                // Expand: show detail rows, keep header row visible
                detailRows.forEach(row => {{
                    row.style.display = 'table-row';
                }});
                if (icon) {{
                    icon.className = 'fas fa-chevron-down cohort-icon';
                }}
            }}
            
            // Update display after toggle
            updateGSBracketsTable();
        }}
        
        // Function to update GS Brackets table (count vs percentage)
        function updateGSBracketsTable() {{
            const modeRadios = document.querySelectorAll('input[name="gsBracketsDisplayMode"]');
            const selectedMode = modeRadios.length > 0 ? Array.from(modeRadios).find(r => r.checked)?.value || 'count' : 'count';
            const isPercentage = selectedMode === 'percentage';
            
            // Process all rows (header, detail, and total rows)
            const allRows = document.querySelectorAll('#gsBracketsTable tbody tr');
            
            allRows.forEach(row => {{
                // Get all bracket cells with data-count (exclude the Total column which is the last cell)
                const allCells = row.querySelectorAll('td');
                const bracketCells = row.querySelectorAll('td[data-count]');
                const totalCell = allCells[allCells.length - 1]; // Last cell is Total column
                
                if (!totalCell || bracketCells.length === 0) return;
                
                // Extract total from the last cell (Total column) - preserve the <strong> tag if present
                const totalText = totalCell.textContent.trim();
                const totalMatch = totalText.match(/\\d+/);
                const total = totalMatch ? parseFloat(totalMatch[0]) : 0;
                
                bracketCells.forEach(cell => {{
                    const count = parseFloat(cell.getAttribute('data-count')) || 0;
                    
                    if (isPercentage) {{
                        if (total > 0) {{
                            const percentage = (count / total * 100);
                            cell.textContent = percentage.toFixed(1) + '%';
                        }} else {{
                            cell.textContent = '-';
                        }}
                    }} else {{
                        // Show count
                        cell.textContent = count;
                    }}
                }});
                
                // Total column should always show the actual total, never percentage
                // (it's already correct, just make sure it's not modified)
            }});
        }}
        
        // Initialize table on page load
        if (document.getElementById('gsBracketsTable')) {{
            updateGSBracketsTable();
        }}
        
        function filterProgressionDataByParticipant(progressionDataView, progressionSessionData, participantIds) {{
            if (!participantIds || participantIds.length === 0) {{
                return progressionDataView;
            }}
            
            // Create a set of allowed participant IDs (case-insensitive)
            const allowedParticipantIds = new Set(participantIds.map(id => id.toLowerCase()));
            
            // Filter session data by participant IDs
            const filteredSessions = progressionSessionData.filter(session => {{
                return allowedParticipantIds.has(session.participant_id.toLowerCase());
            }});
            
            // Rebuild progression data from filtered sessions
            const filtered = Object.create(null);  // Empty object
            const grouped = Object.create(null);  // Empty object for grouping
            
            for (const session of filteredSessions) {{
                const {{session_number, user_words, method, version}} = session;
                
                // Determine which keys this session belongs to based on the view structure
                // We need to match the structure of progressionDataView
                for (const key in progressionDataView) {{
                    if (!grouped[key]) {{
                        grouped[key] = Object.create(null);
                    }}
                    
                    // Check if this session matches this key
                    let matches = false;
                    if (key === method) {{
                        matches = true;
                    }} else if (key === `${{method}}_${{version}}`) {{
                        matches = true;
                    }} else if (key === version) {{
                        matches = true;
                    }}
                    
                    if (matches) {{
                        if (!grouped[key][session_number]) {{
                            grouped[key][session_number] = [];
                        }}
                        grouped[key][session_number].push(user_words);
                    }}
                }}
            }}
            
            // Calculate averages for each key and session number
            for (const key in progressionDataView) {{
                filtered[key] = Object.create(null);
                if (grouped[key]) {{
                    for (const sessionNum in grouped[key]) {{
                        const wordCounts = grouped[key][sessionNum];
                        if (wordCounts && wordCounts.length > 0) {{
                            filtered[key][sessionNum] = wordCounts.reduce((a, b) => a + b, 0) / wordCounts.length;
                        }} else {{
                            filtered[key][sessionNum] = progressionDataView[key][sessionNum] || 0;
                        }}
                    }}
                }} else {{
                    // No matching sessions, set to 0
                    for (const sessionNum in progressionDataView[key]) {{
                        filtered[key][sessionNum] = 0;
                    }}
                }}
            }}
            
            return filtered;
        }}
        
        function updateProgressionChart() {{
            const view = document.getElementById('progressionView').value;
            const excludeOutliers = document.getElementById('excludeOutliersGlobal').checked;
            const participantIds = window.currentParticipantFilter || [];
            
            let data = excludeOutliers ? progressionDataFiltered[view] : progressionData[view];
            let sessionData = excludeOutliers ? progressionSessionDataFiltered : progressionSessionData;
            
            // Apply participant filter
            if (participantIds.length > 0) {{
                data = filterProgressionDataByParticipant(data, sessionData, participantIds);
            }}
            
            if (progressionChart) {{
                progressionChart.destroy();
            }}
            
            const ctx = document.getElementById('progressionChart').getContext('2d');
            
            // Prepare datasets
            const datasets = [];
            const colors = [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', 
                '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384'
            ];
            
            let colorIndex = 0;
            for (const [key, values] of Object.entries(data)) {{
                if (Object.keys(values).length === 0) continue;
                
                const sessionNumbers = Object.keys(values).map(Number).sort((a, b) => a - b);
                const wordCounts = sessionNumbers.map(sessionNum => values[sessionNum] || 0);
                
                datasets.push({{
                    label: key,
                    data: wordCounts.map((count, index) => ({{
                        x: sessionNumbers[index],
                        y: count
                    }})),
                    borderColor: colors[colorIndex % colors.length],
                    backgroundColor: colors[colorIndex % colors.length] + '20',
                    tension: 0.1,
                    fill: false
                }});
                colorIndex++;
            }}
            
            progressionChart = new Chart(ctx, {{
                type: 'line',
                data: {{
                    datasets: datasets
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        x: {{
                            type: 'linear',
                            position: 'bottom',
                            title: {{
                                display: true,
                                text: 'Session Number'
                            }},
                            min: 1,
                            max: 22
                        }},
                        y: {{
                            title: {{
                                display: true,
                                text: 'Average Words per Session'
                            }},
                            beginAtZero: true
                        }}
                    }},
                    plugins: {{
                        legend: {{
                            display: true,
                            position: 'top'
                        }},
                        title: {{
                            display: true,
                            text: 'User Verbosity Progression Across Sessions'
                        }}
                    }}
                }}
            }});
        }}
        
        function filterDataByDateRange(data, startDate, endDate, aggregation) {{
            // Filter time periods based on date range
            if (!startDate && !endDate) {{
                return data;
            }}
            
            const filtered = Object.create(null);
            const timePeriods = Object.keys(data).sort();
            
            timePeriods.forEach(timePeriod => {{
                let periodDate;
                
                // Parse time period based on aggregation
                if (aggregation === 'day') {{
                    periodDate = new Date(timePeriod + 'T00:00:00');
                }} else if (aggregation === 'week') {{
                    periodDate = new Date(timePeriod + 'T00:00:00');
                }} else if (aggregation === 'month') {{
                    periodDate = new Date(timePeriod + '-01T00:00:00');
                }} else {{
                    periodDate = new Date(timePeriod + 'T00:00:00');
                }}
                
                // Check if period is within date range
                const afterStart = !startDate || periodDate >= new Date(startDate);
                const beforeEnd = !endDate || periodDate <= new Date(endDate + 'T23:59:59');
                
                if (afterStart && beforeEnd) {{
                    filtered[timePeriod] = data[timePeriod];
                }}
            }});
            
            return filtered;
        }}
        
        function updateVolumeChart() {{
            const aggregation = document.getElementById('volumeAggregation').value;
            const refrigeratorOnly = document.getElementById('refrigeratorOnly').checked;
            const participantIds = window.currentParticipantFilter || [];
            let volumeData;
            
            // Select data based on aggregation level and refrigerator filter
            if (refrigeratorOnly) {{
                if (aggregation === 'day') {{
                    volumeData = volumeDataRefrigeratorDay;
                }} else if (aggregation === 'week') {{
                    volumeData = volumeDataRefrigeratorWeek;
                }} else if (aggregation === 'month') {{
                    volumeData = volumeDataRefrigeratorMonth;
                }} else {{
                    volumeData = volumeDataRefrigeratorWeek;
                }}
            }} else {{
                if (aggregation === 'day') {{
                    volumeData = volumeDataDay;
                }} else if (aggregation === 'week') {{
                    volumeData = volumeDataWeek;
                }} else if (aggregation === 'month') {{
                    volumeData = volumeDataMonth;
                }} else {{
                    volumeData = volumeDataWeek;
                }}
            }}
            
            // Apply participant filter (participantIds already declared above)
            if (participantIds.length > 0) {{
                volumeData = filterVolumeDataByParticipant(volumeData, volumeSessionMaps, participantIds, aggregation);
            }}
            
            // Apply date range filter
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            volumeData = filterDataByDateRange(volumeData, startDate, endDate, aggregation);
            
            if (volumeChart) {{
                volumeChart.destroy();
            }}
            
            const ctx = document.getElementById('volumeChart').getContext('2d');
            
            // Get all time periods sorted (after filtering)
            const timePeriods = Object.keys(volumeData).sort();
            
            // Define versions and methods
            const versions = ['Control', 'V3', 'V4', 'V5', 'V6'];
            const methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown'];
            
            // Define colors for methods
            const methodColors = {{
                'Scenario': '#FF6384',
                'Microlearning': '#36A2EB',
                'Microlearning vaccines': '#FFCE56',
                'Motivational interviewing': '#4BC0C0',
                'Visit check in': '#9966FF',
                'Unknown': '#C9CBCF'
            }};
            
            // Prepare datasets - create labels with version for each time period
            // Format: "2024-01-15 - Control", "2024-01-15 - V3", etc.
            const labels = [];
            const datasets = [];
            
            // Create a dataset for each method
            methods.forEach(method => {{
                const data = [];
                
                timePeriods.forEach(timePeriod => {{
                    versions.forEach(version => {{
                        const value = volumeData[timePeriod]?.[version]?.[method] || 0;
                        data.push(value);
                    }});
                }});
                
                datasets.push({{
                    label: method,
                    data: data,
                    backgroundColor: methodColors[method]
                }});
            }});
            
            // Create labels: for each time period, create labels for each version
            timePeriods.forEach(timePeriod => {{
                versions.forEach(version => {{
                    labels.push(`${{timePeriod}} - ${{version}}`);
                }});
            }});
            
            volumeChart = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: labels,
                    datasets: datasets
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        x: {{
                            stacked: true,
                            title: {{
                                display: true,
                                text: 'Time'
                            }},
                            ticks: {{
                                maxRotation: 45,
                                minRotation: 45
                            }}
                        }},
                        y: {{
                            stacked: true,
                            title: {{
                                display: true,
                                text: 'Number of Sessions'
                            }},
                            beginAtZero: true
                        }}
                    }},
                    plugins: {{
                        legend: {{
                            display: true,
                            position: 'right'
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    const label = context.dataset.label || '';
                                    const value = context.parsed.y;
                                    if (value > 0) {{
                                        return label + ': ' + value;
                                    }}
                                    return '';
                                }}
                            }}
                        }},
                        title: {{
                            display: true,
                            text: 'Volume of Session per Coach Version'
                        }}
                    }}
                }}
            }});
        }}
        
        // Helper function to calculate median from array
        function calculateMedian(values) {{
            if (!values || values.length === 0) return 0;
            const sorted = values.filter(v => v > 0).sort((a, b) => a - b);
            if (sorted.length === 0) return 0;
            const mid = Math.floor(sorted.length / 2);
            return sorted.length % 2 === 0 
                ? (sorted[mid - 1] + sorted[mid]) / 2 
                : sorted[mid];
        }}
        
        // Update median words table based on outlier filter (deprecated - now handled by updateTablesForRefrigeratorFilter)
        function updateMedianWordsTable() {{
            updateTablesForRefrigeratorFilter();
        }}
        
        // Legacy function for backward compatibility
        function updateMedianWordsTableLegacy() {{
            const excludeOutliers = document.getElementById('excludeOutliersGlobal').checked;
            const table = document.getElementById('medianWordsTable');
            if (!table || !metricsData) return;
            
            const tbody = table.querySelector('tbody');
            if (!tbody) return;
            
            // Clear existing rows
            tbody.innerHTML = '';
            
            // Get all unique methods
            const methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown'];
            
            // Store values for global calculation (per version and across all versions)
            const globalValues = metricsData.map(() => []);
            const allVersionsValues = [];  // For "All Versions" column
            
            // Generate rows
            methods.forEach(method => {{
                const row = document.createElement('tr');
                const methodCell = document.createElement('td');
                methodCell.innerHTML = `<strong>${{method}}</strong>`;
                row.appendChild(methodCell);
                
                const methodAllVersions = [];  // Collect values across all versions for this method
                
                metricsData.forEach((metric, idx) => {{
                    const cell = document.createElement('td');
                    const version_name = metric.version_name || '';
                    const data = excludeOutliers ? metric.median_words_by_method_filtered : metric.median_words_by_method;
                    const method_data = data[method] || Object.create(null);
                    
                    let value = 0.0;
                    if (version_name === 'Control bot') {{
                        if (method === 'Unknown') {{
                            value = typeof method_data === 'object' ? (method_data.Control || 0.0) : (method_data || 0.0);
                        }}
                    }} else {{
                        const version_key = version_name.replace('Coaching bot ', '');
                        value = typeof method_data === 'object' ? (method_data[version_key] || 0.0) : (method_data || 0.0);
                    }}
                    
                    // Store value for global calculation
                    if (value > 0) {{
                        globalValues[idx].push(value);
                        methodAllVersions.push(value);
                    }}
                    
                    if (value > 0) {{
                        cell.textContent = value.toFixed(1);
                    }} else {{
                        cell.textContent = '-';
                    }}
                    row.appendChild(cell);
                }});
                
                // Add "All Versions" column for this method
                const allVersionsCell = document.createElement('td');
                if (methodAllVersions.length > 0) {{
                    const allVersionsMedian = calculateMedian(methodAllVersions);
                    if (allVersionsMedian > 0) {{
                        allVersionsCell.textContent = allVersionsMedian.toFixed(1);
                        allVersionsCell.style.fontWeight = 'bold';
                        allVersionsValues.push(allVersionsMedian);
                    }} else {{
                        allVersionsCell.textContent = '-';
                        allVersionsValues.push(0);
                    }}
                }} else {{
                    allVersionsCell.textContent = '-';
                    allVersionsValues.push(0);
                }}
                row.appendChild(allVersionsCell);
                
                tbody.appendChild(row);
            }});
            
            // Add Total row
            const totalRow = document.createElement('tr');
            totalRow.style.backgroundColor = '#f8f9fa';
            const totalCell = document.createElement('td');
            totalCell.innerHTML = `<strong>Total (All Methods)</strong>`;
            totalRow.appendChild(totalCell);
            
            globalValues.forEach(values => {{
                const cell = document.createElement('td');
                const globalMedian = calculateMedian(values);
                if (globalMedian > 0) {{
                    cell.textContent = globalMedian.toFixed(1);
                    cell.style.fontWeight = 'bold';
                }} else {{
                    cell.textContent = '-';
                }}
                totalRow.appendChild(cell);
            }});
            
            // Add "All Versions" column for Total row
            const totalAllVersionsCell = document.createElement('td');
            const totalAllVersionsMedian = calculateMedian(allVersionsValues.filter(v => v > 0));
            if (totalAllVersionsMedian > 0) {{
                totalAllVersionsCell.textContent = totalAllVersionsMedian.toFixed(1);
                totalAllVersionsCell.style.fontWeight = 'bold';
            }} else {{
                totalAllVersionsCell.textContent = '-';
            }}
            totalRow.appendChild(totalAllVersionsCell);
            
            tbody.appendChild(totalRow);
        }}
        
        // Update median messages table based on outlier filter (deprecated - now handled by updateTablesForRefrigeratorFilter)
        function updateMedianMessagesTable() {{
            updateTablesForRefrigeratorFilter();
        }}
        
        // Legacy function for backward compatibility
        function updateMedianMessagesTableLegacy() {{
            const excludeOutliers = document.getElementById('excludeOutliersGlobal').checked;
            const table = document.getElementById('medianMessagesTable');
            if (!table || !metricsData) return;
            
            const tbody = table.querySelector('tbody');
            if (!tbody) return;
            
            // Clear existing rows
            tbody.innerHTML = '';
            
            // Get all unique methods
            const methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown'];
            
            // Store values for global calculation (per version and across all versions)
            const globalValues = metricsData.map(() => []);
            const allVersionsValues = [];  // For "All Versions" column
            
            // Generate rows
            methods.forEach(method => {{
                const row = document.createElement('tr');
                const methodCell = document.createElement('td');
                methodCell.innerHTML = `<strong>${{method}}</strong>`;
                row.appendChild(methodCell);
                
                const methodAllVersions = [];  // Collect values across all versions for this method
                
                metricsData.forEach((metric, idx) => {{
                    const cell = document.createElement('td');
                    const version_name = metric.version_name || '';
                    const data = excludeOutliers ? metric.median_messages_by_method_filtered : metric.median_messages_by_method;
                    const method_data = data[method] || Object.create(null);
                    
                    let value = 0.0;
                    if (version_name === 'Control bot') {{
                        if (method === 'Unknown') {{
                            value = typeof method_data === 'object' ? (method_data.Control || 0.0) : (method_data || 0.0);
                        }}
                    }} else {{
                        const version_key = version_name.replace('Coaching bot ', '');
                        value = typeof method_data === 'object' ? (method_data[version_key] || 0.0) : (method_data || 0.0);
                    }}
                    
                    // Store value for global calculation
                    if (value > 0) {{
                        globalValues[idx].push(value);
                        methodAllVersions.push(value);
                    }}
                    
                    if (value > 0) {{
                        cell.textContent = value.toFixed(1);
                    }} else {{
                        cell.textContent = '-';
                    }}
                    row.appendChild(cell);
                }});
                
                // Add "All Versions" column for this method
                const allVersionsCell = document.createElement('td');
                if (methodAllVersions.length > 0) {{
                    const allVersionsMedian = calculateMedian(methodAllVersions);
                    if (allVersionsMedian > 0) {{
                        allVersionsCell.textContent = allVersionsMedian.toFixed(1);
                        allVersionsCell.style.fontWeight = 'bold';
                        allVersionsValues.push(allVersionsMedian);
                    }} else {{
                        allVersionsCell.textContent = '-';
                        allVersionsValues.push(0);
                    }}
                }} else {{
                    allVersionsCell.textContent = '-';
                    allVersionsValues.push(0);
                }}
                row.appendChild(allVersionsCell);
                
                tbody.appendChild(row);
            }});
            
            // Add Total row
            const totalRow = document.createElement('tr');
            totalRow.style.backgroundColor = '#f8f9fa';
            const totalCell = document.createElement('td');
            totalCell.innerHTML = `<strong>Total (All Methods)</strong>`;
            totalRow.appendChild(totalCell);
            
            globalValues.forEach(values => {{
                const cell = document.createElement('td');
                const globalMedian = calculateMedian(values);
                if (globalMedian > 0) {{
                    cell.textContent = globalMedian.toFixed(1);
                    cell.style.fontWeight = 'bold';
                }} else {{
                    cell.textContent = '-';
                }}
                totalRow.appendChild(cell);
            }});
            
            // Add "All Versions" column for Total row
            const totalAllVersionsCell = document.createElement('td');
            const totalAllVersionsMedian = calculateMedian(allVersionsValues.filter(v => v > 0));
            if (totalAllVersionsMedian > 0) {{
                totalAllVersionsCell.textContent = totalAllVersionsMedian.toFixed(1);
                totalAllVersionsCell.style.fontWeight = 'bold';
            }} else {{
                totalAllVersionsCell.textContent = '-';
            }}
            totalRow.appendChild(totalAllVersionsCell);
            
            tbody.appendChild(totalRow);
        }}
        
        // Apply global filters to charts
        function applyGlobalFilters() {{
            // Update volume chart with date filters
            if (document.getElementById('volumeChart')) {{
                updateVolumeChart();
            }}
            
            // Update progression chart with outlier filter
            if (document.getElementById('progressionChart')) {{
                updateProgressionChart();
            }}
            
            // Update all tables based on refrigerator filter (includes median words/messages)
            updateTablesForRefrigeratorFilter();
            
            // Note: Date filtering for progression chart would require session-level date data
            // which is not currently available in the JavaScript
            
            // Show feedback
            const feedback = document.createElement('div');
            feedback.className = 'alert alert-info alert-dismissible fade show mt-2';
            feedback.innerHTML = `
                <strong>Filters Applied:</strong> Charts have been updated. 
                <small>Note: Summary tables require dashboard regeneration to reflect date/participant filters.</small>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            // Remove existing feedback if any
            const existingFeedback = document.querySelector('.filter-feedback');
            if (existingFeedback) {{
                existingFeedback.remove();
            }}
            
            feedback.classList.add('filter-feedback');
            const filterSection = document.querySelector('#filterCollapse .card-body');
            if (filterSection) {{
                filterSection.appendChild(feedback);
                // Auto-dismiss after 5 seconds
                setTimeout(() => {{
                    if (feedback.parentNode) {{
                        feedback.remove();
                    }}
                }}, 5000);
            }}
        }}
        
        // Update tables based on refrigerator filter
        function updateTablesForRefrigeratorFilter() {{
            const refrigeratorOnly = document.getElementById('refrigeratorOnly').checked;
            
            // Update Summary Metrics table
            const summaryTableBody = document.getElementById('summaryMetricsTableBody');
            if (summaryTableBody) {{
                summaryTableBody.innerHTML = refrigeratorOnly ? summaryTableRowsRefrigerator : summaryTableRows;
            }}
            
            // Update Refrigerator Rate table
            const refrigeratorRateTableBody = document.getElementById('refrigeratorRateTableBody');
            if (refrigeratorRateTableBody) {{
                refrigeratorRateTableBody.innerHTML = refrigeratorOnly ? refrigeratorRateTableRowsRefrigerator : refrigeratorRateTableRows;
                // Preserve the calculation mode after updating the table
                updateRefrigeratorCalculationMode();
            }}
            
            // Update Average Rating table
            const averageRatingTableBody = document.getElementById('averageRatingTableBody');
            if (averageRatingTableBody) {{
                averageRatingTableBody.innerHTML = refrigeratorOnly ? averageRatingTableRowsRefrigerator : averageRatingTableRows;
            }}
            
            // Update Session Count table
            const sessionCountTableBody = document.getElementById('sessionCountTableBody');
            if (sessionCountTableBody) {{
                sessionCountTableBody.innerHTML = refrigeratorOnly ? sessionCountTableRowsRefrigerator : sessionCountTableRows;
            }}
            
            // Update median words and messages tables (they use metricsData which needs to be filtered)
            // These tables are dynamically generated, so we need to update them with filtered data
            if (refrigeratorOnly) {{
                // Use refrigerator-filtered metrics
                const filteredMetricsData = metricsData.map(metric => metric.refrigerator_filtered || metric);
                updateMedianWordsTableWithData(filteredMetricsData);
                updateMedianMessagesTableWithData(filteredMetricsData);
            }} else {{
                // Use regular metrics
                updateMedianWordsTableWithData(metricsData);
                updateMedianMessagesTableWithData(metricsData);
            }}
        }}
        
        // Update refrigerator rate table based on calculation mode
        function updateRefrigeratorCalculationMode() {{
            const mode = document.querySelector('input[name="refrigeratorCalcMode"]:checked')?.value || 'annotated';
            const tableBody = document.getElementById('refrigeratorRateTableBody');
            
            if (!tableBody) {{
                console.warn('refrigeratorRateTableBody not found');
                return;
            }}
            
            // Get all table cells (td elements) - exclude the first column (method names)
            const rows = tableBody.querySelectorAll('tr');
            let cellsUpdated = 0;
            
            rows.forEach(row => {{
                // Get all td elements except the first one (method name)
                const cells = row.querySelectorAll('td:not(:first-child)');
                
                cells.forEach(cell => {{
                    const annotatedValue = cell.getAttribute('data-mode-annotated');
                    const explicitValue = cell.getAttribute('data-mode-explicit');
                    
                    // Skip if no data attributes
                    if (!annotatedValue && !explicitValue) {{
                        return;
                    }}
                    
                    let displayValue;
                    if (mode === 'annotated') {{
                        displayValue = annotatedValue;
                    }} else {{
                        displayValue = explicitValue;
                    }}
                    
                    // Update the cell content
                    if (displayValue && displayValue !== '-') {{
                        const numValue = parseFloat(displayValue);
                        if (!isNaN(numValue)) {{
                            cell.textContent = numValue.toFixed(1) + '%';
                            cellsUpdated++;
                        }} else {{
                            cell.textContent = displayValue;
                        }}
                    }} else {{
                        cell.textContent = '-';
                    }}
                }});
            }});
            
            console.log('Updated ' + cellsUpdated + ' cells for mode: ' + mode);
        }}
        
        // Update tables for participant filter
        function updateTablesForParticipantFilter() {{
            const participantIds = window.currentParticipantFilter || [];
            
            if (participantIds.length === 0) {{
                // No participant filter, use regular data
                return;
            }}
            
            // Create a set of allowed session IDs
            const allowedSessionIds = new Set();
            for (const [sessionId, participantId] of Object.entries(sessionParticipantMap)) {{
                if (participantIds.some(pid => pid.toLowerCase() === participantId.toLowerCase())) {{
                    allowedSessionIds.add(sessionId);
                }}
            }}
            
            // Filter volume summary table (Session Count by Method and Version)
            updateVolumeSummaryTableForParticipant(allowedSessionIds);
            
            // Note: Other tables (Average FLW Score, Median Words/Messages) require session-level data
            // that is not currently stored. These would need to be recalculated from filtered sessions.
            // For now, we show a message that participant filtering for these tables requires
            // dashboard regeneration with participant filter applied.
        }}
        
        // Update volume summary table for participant filter
        function updateVolumeSummaryTableForParticipant(allowedSessionIds) {{
            const table = document.getElementById('sessionCountTableBody');
            if (!table) return;
            
            // Get current aggregation (default to week)
            const aggregation = document.getElementById('volumeAggregation')?.value || 'week';
            const sessionMap = volumeSessionMaps[aggregation] || Object.create(null);
            
            // Recalculate counts by method and version
            const counts = {{
                'Control': Object.create(null),
                'V3': Object.create(null),
                'V4': Object.create(null),
                'V5': Object.create(null),
                'V6': Object.create(null)
            }};
            
            const methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown'];
            const versions = ['Control', 'V3', 'V4', 'V5', 'V6'];
            
            // Initialize counts
            versions.forEach(version => {{
                methods.forEach(method => {{
                    counts[version][method] = 0;
                }});
            }});
            
            // Count sessions across all time periods
            for (const timeKey in sessionMap) {{
                for (const version in sessionMap[timeKey]) {{
                    for (const method in sessionMap[timeKey][version]) {{
                        const sessionIds = sessionMap[timeKey][version][method] || [];
                        const matchingSessions = sessionIds.filter(sid => allowedSessionIds.has(sid));
                        if (counts[version] && counts[version][method] !== undefined) {{
                            counts[version][method] += matchingSessions.length;
                        }}
                    }}
                }}
            }}
            
            // Update table HTML
            let html = '';
            methods.forEach(method => {{
                html += '<tr><td><strong>' + method + '</strong></td>';
                let methodTotal = 0;
                versions.forEach(version => {{
                    const count = counts[version][method] || 0;
                    html += '<td>' + count + '</td>';
                    methodTotal += count;
                }});
                // All Versions column (median across versions)
                html += '<td>' + methodTotal + '</td>';
                html += '</tr>';
            }});
            
            // Total row
            html += '<tr style="background-color: #f8f9fa;"><td><strong>Total (All Methods)</strong></td>';
            let versionTotals = Object.create(null);
            versions.forEach(version => {{
                let total = 0;
                methods.forEach(method => {{
                    total += counts[version][method] || 0;
                }});
                versionTotals[version] = total;
                html += '<td style="font-weight: bold;">' + total + '</td>';
            }});
            // All Versions total
            const allVersionsTotal = Object.values(versionTotals).reduce((a, b) => a + b, 0);
            html += '<td style="font-weight: bold;">' + allVersionsTotal + '</td>';
            html += '</tr>';
            
            table.innerHTML = html;
        }}
        
        // Helper function to update median words table with specific data
        function updateMedianWordsTableWithData(data) {{
            const excludeOutliers = document.getElementById('excludeOutliersGlobal').checked;
            const table = document.getElementById('medianWordsTable');
            if (!table || !data) return;
            
            // Get display mode
            const modeRadios = document.querySelectorAll('input[name="wordsDisplayMode"]');
            const selectedMode = modeRadios.length > 0 ? Array.from(modeRadios).find(r => r.checked)?.value || 'per_session' : 'per_session';
            const isPerMessage = selectedMode === 'per_message';
            
            const tbody = table.querySelector('tbody');
            if (!tbody) return;
            
            // Clear existing rows
            tbody.innerHTML = '';
            
            // Get all unique methods
            const methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown'];
            
            // Store values for global calculation (per version and across all versions)
            const globalValues = data.map(() => []);
            const allVersionsValues = [];
            
            // Generate rows
            methods.forEach(method => {{
                const row = document.createElement('tr');
                const methodCell = document.createElement('td');
                methodCell.innerHTML = `<strong>${{method}}</strong>`;
                row.appendChild(methodCell);
                
                const methodAllVersions = [];
                
                data.forEach((metric, idx) => {{
                    const cell = document.createElement('td');
                    const version_name = metric.version_name || '';
                    const wordsTableData = excludeOutliers ? metric.median_words_by_method_filtered : metric.median_words_by_method;
                    const messagesTableData = excludeOutliers ? metric.median_messages_by_method_filtered : metric.median_messages_by_method;
                    const words_method_data = wordsTableData[method];
                    const messages_method_data = messagesTableData[method];
                    
                    let wordsValue = 0.0;
                    let messagesValue = 0.0;
                    
                    // Get words value
                    if (words_method_data === undefined || words_method_data === null) {{
                        wordsValue = 0.0;
                    }} else if (typeof words_method_data === 'number') {{
                        wordsValue = words_method_data;
                    }} else if (typeof words_method_data === 'object') {{
                        if (version_name === 'Control bot') {{
                            if (method === 'Unknown') {{
                                wordsValue = words_method_data.Control || 0.0;
                            }}
                        }} else {{
                            const version_key = version_name.replace('Coaching bot ', '');
                            wordsValue = words_method_data[version_key] || 0.0;
                        }}
                    }}
                    
                    // Get messages value
                    if (messages_method_data === undefined || messages_method_data === null) {{
                        messagesValue = 0.0;
                    }} else if (typeof messages_method_data === 'number') {{
                        messagesValue = messages_method_data;
                    }} else if (typeof messages_method_data === 'object') {{
                        if (version_name === 'Control bot') {{
                            if (method === 'Unknown') {{
                                messagesValue = messages_method_data.Control || 0.0;
                            }}
                        }} else {{
                            const version_key = version_name.replace('Coaching bot ', '');
                            messagesValue = messages_method_data[version_key] || 0.0;
                        }}
                    }}
                    
                    // Calculate final value
                    let value = 0.0;
                    if (isPerMessage) {{
                        // Divide words by messages
                        if (messagesValue > 0 && wordsValue > 0) {{
                            value = wordsValue / messagesValue;
                        }}
                    }} else {{
                        value = wordsValue;
                    }}
                    
                    if (value > 0) {{
                        cell.textContent = value.toFixed(1);
                        globalValues[idx].push(value);
                        methodAllVersions.push(value);
                    }} else {{
                        cell.textContent = '-';
                    }}
                    row.appendChild(cell);
                }});
                
                // Add "All Versions" column
                const allVersionsCell = document.createElement('td');
                if (methodAllVersions.length > 0) {{
                    const allVersionsMedian = calculateMedian(methodAllVersions);
                    if (allVersionsMedian > 0) {{
                        allVersionsCell.textContent = allVersionsMedian.toFixed(1);
                        allVersionsCell.style.fontWeight = 'bold';
                        allVersionsValues.push(allVersionsMedian);
                    }} else {{
                        allVersionsCell.textContent = '-';
                    }}
                }} else {{
                    allVersionsCell.textContent = '-';
                }}
                row.appendChild(allVersionsCell);
                
                tbody.appendChild(row);
            }});
            
            // Add Total row
            const totalRow = document.createElement('tr');
            totalRow.style.backgroundColor = '#f8f9fa';
            const totalCell = document.createElement('td');
            totalCell.innerHTML = `<strong>Total (All Methods)</strong>`;
            totalRow.appendChild(totalCell);
            
            globalValues.forEach(values => {{
                const cell = document.createElement('td');
                const globalMedian = calculateMedian(values);
                if (globalMedian > 0) {{
                    cell.textContent = globalMedian.toFixed(1);
                    cell.style.fontWeight = 'bold';
                }} else {{
                    cell.textContent = '-';
                }}
                totalRow.appendChild(cell);
            }});
            
            // Add "All Versions" column for Total row
            const totalAllVersionsCell = document.createElement('td');
            const totalAllVersionsMedian = calculateMedian(allVersionsValues.filter(v => v > 0));
            if (totalAllVersionsMedian > 0) {{
                totalAllVersionsCell.textContent = totalAllVersionsMedian.toFixed(1);
                totalAllVersionsCell.style.fontWeight = 'bold';
            }} else {{
                totalAllVersionsCell.textContent = '-';
            }}
            totalRow.appendChild(totalAllVersionsCell);
            
            tbody.appendChild(totalRow);
        }}
        
        // Helper function to update median messages table with specific data
        function updateMedianMessagesTableWithData(data) {{
            const excludeOutliers = document.getElementById('excludeOutliersGlobal').checked;
            const table = document.getElementById('medianMessagesTable');
            if (!table || !data) return;
            
            const tbody = table.querySelector('tbody');
            if (!tbody) return;
            
            // Clear existing rows
            tbody.innerHTML = '';
            
            // Get all unique methods
            const methods = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown'];
            
            // Store values for global calculation (per version and across all versions)
            const globalValues = data.map(() => []);
            const allVersionsValues = [];
            
            // Generate rows
            methods.forEach(method => {{
                const row = document.createElement('tr');
                const methodCell = document.createElement('td');
                methodCell.innerHTML = `<strong>${{method}}</strong>`;
                row.appendChild(methodCell);
                
                const methodAllVersions = [];
                
                data.forEach((metric, idx) => {{
                    const cell = document.createElement('td');
                    const version_name = metric.version_name || '';
                    const tableData = excludeOutliers ? metric.median_messages_by_method_filtered : metric.median_messages_by_method;
                    const method_data = tableData[method];
                    
                    let value = 0.0;
                    if (method_data === undefined || method_data === null) {{
                        value = 0.0;
                    }} else if (typeof method_data === 'number') {{
                        // Direct number value (already filtered by version)
                        value = method_data;
                    }} else if (typeof method_data === 'object') {{
                        // Object with version keys
                        if (version_name === 'Control bot') {{
                            if (method === 'Unknown') {{
                                value = method_data.Control || 0.0;
                            }}
                        }} else {{
                            const version_key = version_name.replace('Coaching bot ', '');
                            value = method_data[version_key] || 0.0;
                        }}
                    }}
                    
                    if (value > 0) {{
                        cell.textContent = value.toFixed(1);
                        globalValues[idx].push(value);
                        methodAllVersions.push(value);
                    }} else {{
                        cell.textContent = '-';
                    }}
                    row.appendChild(cell);
                }});
                
                // Add "All Versions" column
                const allVersionsCell = document.createElement('td');
                if (methodAllVersions.length > 0) {{
                    const allVersionsMedian = calculateMedian(methodAllVersions);
                    if (allVersionsMedian > 0) {{
                        allVersionsCell.textContent = allVersionsMedian.toFixed(1);
                        allVersionsCell.style.fontWeight = 'bold';
                        allVersionsValues.push(allVersionsMedian);
                    }} else {{
                        allVersionsCell.textContent = '-';
                    }}
                }} else {{
                    allVersionsCell.textContent = '-';
                }}
                row.appendChild(allVersionsCell);
                
                tbody.appendChild(row);
            }});
            
            // Add Total row
            const totalRow = document.createElement('tr');
            totalRow.style.backgroundColor = '#f8f9fa';
            const totalCell = document.createElement('td');
            totalCell.innerHTML = `<strong>Total (All Methods)</strong>`;
            totalRow.appendChild(totalCell);
            
            globalValues.forEach(values => {{
                const cell = document.createElement('td');
                const globalMedian = calculateMedian(values);
                if (globalMedian > 0) {{
                    cell.textContent = globalMedian.toFixed(1);
                    cell.style.fontWeight = 'bold';
                }} else {{
                    cell.textContent = '-';
                }}
                totalRow.appendChild(cell);
            }});
            
            // Add "All Versions" column for Total row
            const totalAllVersionsCell = document.createElement('td');
            const totalAllVersionsMedian = calculateMedian(allVersionsValues.filter(v => v > 0));
            if (totalAllVersionsMedian > 0) {{
                totalAllVersionsCell.textContent = totalAllVersionsMedian.toFixed(1);
                totalAllVersionsCell.style.fontWeight = 'bold';
            }} else {{
                totalAllVersionsCell.textContent = '-';
            }}
            totalRow.appendChild(totalAllVersionsCell);
            
            tbody.appendChild(totalRow);
        }}
        
        // Reset global filters
        function resetGlobalFilters() {{
            // Reset date filters
            document.getElementById('startDate').value = '';
            document.getElementById('endDate').value = '';
            
            // Reset participant filter (clear textarea)
            const participantTextarea = document.getElementById('participantFilter');
            if (participantTextarea) {{
                participantTextarea.value = '';
            }}
            window.currentParticipantFilter = [];
            
            // Reset outlier filter (uncheck)
            document.getElementById('excludeOutliersGlobal').checked = false;
            
            // Reset refrigerator filter (uncheck)
            document.getElementById('refrigeratorOnly').checked = false;
            
            // Note: excludeSplitSessions and excludeTestSessions are checked by default
            // and should remain checked as they're data quality filters
            
            // Apply the reset filters
            applyGlobalFilters();
        }}
        
        // Apply participant filter to all charts and tables
        function applyParticipantFilter() {{
            const participantTextarea = document.getElementById('participantFilter');
            if (!participantTextarea) {{
                console.error('Participant filter textarea not found');
                return;
            }}
            
            const participantText = participantTextarea.value.trim();
            let participantIds = [];
            
            if (participantText) {{
                // Split by newlines and filter out empty lines
                participantIds = participantText.split('\\n')
                    .map(id => id.trim())
                    .filter(id => id.length > 0);
            }}
            
            console.log('Applying participant filter:', participantIds);
            
            // Store current filter state
            window.currentParticipantFilter = participantIds;
            
            // Apply filters to all charts and tables
            applyGlobalFilters();
            
            // Show feedback
            const existingFeedback = participantTextarea.parentNode.querySelector('.alert');
            if (existingFeedback) {{
                existingFeedback.remove();
            }}
            
            const feedback = document.createElement('div');
            feedback.className = 'alert alert-info mt-2';
            if (participantIds.length > 0) {{
                // Check if participant IDs exist in the map (case-insensitive)
                const participantIdValues = Object.values(sessionParticipantMap);
                const participantIdValuesLower = participantIdValues.map(id => id.toLowerCase());
                const foundCount = participantIds.filter(id => {{
                    return participantIdValues.includes(id) || participantIdValuesLower.includes(id.toLowerCase());
                }}).length;
                
                // Get sample participant IDs for debugging
                const sampleIds = Array.from(new Set(participantIdValues)).slice(0, 3);
                
                if (foundCount === 0) {{
                    feedback.className = 'alert alert-warning mt-2';
                    feedback.innerHTML = `<i class="fas fa-exclamation-triangle me-1"></i>Warning: No sessions found for the provided participant ID(s). Check browser console for sample participant IDs.`;
                    console.warn('Participant IDs not found. Sample participant IDs in data:', sampleIds);
                }} else {{
                    feedback.innerHTML = `<i class="fas fa-info-circle me-1"></i>Participant filter applied: Showing data for ${{foundCount}} of ${{participantIds.length}} participant(s). Tables require dashboard regeneration for full filtering.`;
                }}
            }} else {{
                feedback.innerHTML = `<i class="fas fa-info-circle me-1"></i>Participant filter cleared: Showing all participants.`;
            }}
            participantTextarea.parentNode.appendChild(feedback);
            
            // Remove feedback after 8 seconds (longer for warnings)
            setTimeout(() => {{
                if (feedback.parentNode) {{
                    feedback.remove();
                }}
            }}, 8000);
        }}
        
        // Filter volume data by participant IDs using session mappings
        function filterVolumeDataByParticipant(volumeData, volumeSessionMaps, participantIds, aggregation) {{
            if (!participantIds || participantIds.length === 0) {{
                return volumeData;
            }}
            
            // Create a set of allowed session IDs
            const allowedSessionIds = new Set();
            let foundParticipant = false;
            
            // Create a set of participant IDs for faster lookup (case-insensitive)
            const participantIdSet = new Set(participantIds.map(id => id.toLowerCase()));
            const participantIdMap = new Map(participantIds.map(id => [id.toLowerCase(), id]));
            
            for (const [sessionId, participantId] of Object.entries(sessionParticipantMap)) {{
                // Try exact match first
                if (participantIds.includes(participantId)) {{
                    allowedSessionIds.add(sessionId);
                    foundParticipant = true;
                }} else if (participantIdSet.has(participantId.toLowerCase())) {{
                    // Case-insensitive match
                    allowedSessionIds.add(sessionId);
                    foundParticipant = true;
                }}
            }}
            
            // Debug logging
            const sampleParticipantIds = Array.from(new Set(Object.values(sessionParticipantMap))).slice(0, 5);
            console.log('Participant filter debug:', {{
                participantIds: participantIds,
                foundParticipant: foundParticipant,
                allowedSessionIdsCount: allowedSessionIds.size,
                sessionParticipantMapSize: Object.keys(sessionParticipantMap).length,
                sampleParticipantIds: sampleParticipantIds,
                volumeSessionMapsKeys: Object.keys(volumeSessionMaps),
                aggregation: aggregation
            }});
            
            // Check if participant IDs match any in the map (case-insensitive)
            const participantIdSetFromMap = new Set(Object.values(sessionParticipantMap));
            const matchingIds = participantIds.filter(id => {{
                // Try exact match
                if (participantIdSetFromMap.has(id)) return true;
                // Try case-insensitive match
                for (const pid of participantIdSetFromMap) {{
                    if (pid.toLowerCase() === id.toLowerCase()) return true;
                }}
                return false;
            }});
            
            if (matchingIds.length === 0) {{
                console.warn('No matching participant IDs found. Searched for:', participantIds);
                console.warn('Sample participant IDs in data:', sampleParticipantIds);
                // Return empty data structure
                const empty = Object.create(null);
                for (const timeKey in volumeData) {{
                    empty[timeKey] = Object.create(null);
                    for (const version in volumeData[timeKey]) {{
                        empty[timeKey][version] = Object.create(null);
                        for (const method in volumeData[timeKey][version]) {{
                            empty[timeKey][version][method] = 0;
                        }}
                    }}
                }}
                return empty;
            }}
            
            if (!foundParticipant) {{
                console.warn('Participant IDs found but no sessions mapped:', matchingIds);
                // Return empty data structure
                const empty = Object.create(null);
                for (const timeKey in volumeData) {{
                    empty[timeKey] = Object.create(null);
                    for (const version in volumeData[timeKey]) {{
                        empty[timeKey][version] = Object.create(null);
                        for (const method in volumeData[timeKey][version]) {{
                            empty[timeKey][version][method] = 0;
                        }}
                    }}
                }}
                return empty;
            }}
            
            // Recalculate volume data by filtering sessions
            const filtered = Object.create(null);
            const sessionMap = volumeSessionMaps[aggregation] || Object.create(null);
            
            let totalMatchingSessions = 0;
            
            for (const timeKey in volumeData) {{
                filtered[timeKey] = Object.create(null);
                for (const version in volumeData[timeKey]) {{
                    filtered[timeKey][version] = Object.create(null);
                    for (const method in volumeData[timeKey][version]) {{
                        // Count only sessions that match participant filter
                        const sessionIds = sessionMap[timeKey]?.[version]?.[method] || [];
                        const matchingSessions = sessionIds.filter(sid => allowedSessionIds.has(sid));
                        filtered[timeKey][version][method] = matchingSessions.length;
                        totalMatchingSessions += matchingSessions.length;
                    }}
                }}
            }}
            
            console.log('Volume filter result:', {{
                totalMatchingSessions: totalMatchingSessions,
                allowedSessionIdsCount: allowedSessionIds.size,
                timeKeysCount: Object.keys(filtered).length
            }});
            
            return filtered;
        }}
        
        // Filter progression data by participant IDs
        function filterProgressionDataByParticipant(progressionData, participantIds) {{
            if (!participantIds || participantIds.length === 0) {{
                return progressionData;
            }}
            
            // Create a set of allowed participant IDs
            const allowedParticipantIds = new Set(participantIds);
            
            // Note: Progression data structure doesn't directly include participant IDs
            // We need to filter at the source. For now, return original data
            // and add a note that full filtering requires regeneration
            return progressionData;
        }}
        
        // Initialize chart on page load
        document.addEventListener('DOMContentLoaded', function() {{
            window.currentParticipantFilter = [];  // Initialize participant filter
            updateProgressionChart();
            updateVolumeChart();
            // Initialize refrigerator calculation mode
            updateRefrigeratorCalculationMode();
            updateTablesForRefrigeratorFilter();  // Initialize tables
            
            // Add event listeners for date inputs to auto-apply filters
            const startDateInput = document.getElementById('startDate');
            const endDateInput = document.getElementById('endDate');
            
            if (startDateInput) {{
                startDateInput.addEventListener('change', function() {{
                    // Only update volume chart (progression chart doesn't support date filtering yet)
                    if (document.getElementById('volumeChart')) {{
                        updateVolumeChart();
                    }}
                }});
            }}
            
            if (endDateInput) {{
                endDateInput.addEventListener('change', function() {{
                    // Only update volume chart (progression chart doesn't support date filtering yet)
                    if (document.getElementById('volumeChart')) {{
                        updateVolumeChart();
                    }}
                }});
            }}
        }});
    </script>
</body>
</html>
        """
        
        return html_content
    
    def generate_dashboard(self) -> str:
        """Generate the complete version comparison dashboard"""
        print("Generating Simple Version Comparison Dashboard...")
        
        # Load sessions (filtered by relevant experiments)
        sessions = self.load_sessions_from_files()
        if not sessions:
            print("No sessions found!")
            return None
        
        # Extract session IDs for message loading
        session_ids = [session.get('id') for session in sessions if session.get('id')]
        
        # Load messages (filtered by session IDs)
        messages_data = self.load_messages_from_files(session_ids)
        
        # Calculate metrics for each version
        metrics = []
        for version_name, version_config in self.coaching_bot_versions.items():
            print(f"Calculating metrics for {version_name}...")
            
            # Filter sessions for this version
            version_sessions = []
            for session in sessions:
                session_id = session.get('id')
                session_messages = messages_data.get(session_id, [])
                if self.matches_version(session, version_config, session_messages):
                    version_sessions.append(session)
            
            print(f"  Found {len(version_sessions)} sessions for {version_name}")
            
            # Calculate metrics (both with and without refrigerator filter)
            metric = self.calculate_metrics_for_version(version_name, version_sessions, messages_data, refrigerator_only=False)
            metric_refrigerator = self.calculate_metrics_for_version(version_name, version_sessions, messages_data, refrigerator_only=True)
            # Store both versions
            metric['refrigerator_filtered'] = metric_refrigerator
            metrics.append(metric)
        
        # Calculate median words and messages by method and version (needs all sessions)
        # Calculate both with and without outlier filtering
        print("Calculating median words and messages by method and version...")
        median_words_by_method = self.calculate_median_words_by_method_and_version(sessions, messages_data, exclude_outliers=False)
        median_words_by_method_filtered = self.calculate_median_words_by_method_and_version(sessions, messages_data, exclude_outliers=True)
        median_messages_by_method = self.calculate_median_messages_by_method_and_version(sessions, messages_data, exclude_outliers=False)
        median_messages_by_method_filtered = self.calculate_median_messages_by_method_and_version(sessions, messages_data, exclude_outliers=True)
        
        # Filter sessions to only refrigerator examples for refrigerator-filtered median calculations
        refrigerator_sessions = []
        for session in sessions:
            session_id = session.get('id')
            session_messages = messages_data.get(session_id, [])
            if not self.should_exclude_session(session, session_messages):
                if self.has_refrigerator_example_tag(session, session_messages):
                    refrigerator_sessions.append(session)
        
        # Calculate median words and messages for refrigerator-filtered sessions
        print("Calculating median words and messages for refrigerator-filtered sessions...")
        median_words_by_method_refrigerator = self.calculate_median_words_by_method_and_version(refrigerator_sessions, messages_data, exclude_outliers=False)
        median_words_by_method_filtered_refrigerator = self.calculate_median_words_by_method_and_version(refrigerator_sessions, messages_data, exclude_outliers=True)
        median_messages_by_method_refrigerator = self.calculate_median_messages_by_method_and_version(refrigerator_sessions, messages_data, exclude_outliers=False)
        median_messages_by_method_filtered_refrigerator = self.calculate_median_messages_by_method_and_version(refrigerator_sessions, messages_data, exclude_outliers=True)
        
        # Add the median data to each metric, filtered by version (both filtered and unfiltered)
        for metric in metrics:
            version_name = metric.get('version_name', '')
            filtered_words = {}
            filtered_messages = {}
            filtered_words_outlier = {}
            filtered_messages_outlier = {}
            
            for method in median_words_by_method:
                filtered_words[method] = {}
                filtered_messages[method] = {}
                filtered_words_outlier[method] = {}
                filtered_messages_outlier[method] = {}
                
                # For Control bot, only show data under Unknown method
                if version_name == 'Control bot':
                    if method == 'Unknown':
                        # Show Control bot data
                        filtered_words[method] = median_words_by_method[method].get('Control', {})
                        filtered_messages[method] = median_messages_by_method[method].get('Control', {})
                        filtered_words_outlier[method] = median_words_by_method_filtered[method].get('Control', {})
                        filtered_messages_outlier[method] = median_messages_by_method_filtered[method].get('Control', {})
                    else:
                        # Show empty for specific methods
                        filtered_words[method] = {}
                        filtered_messages[method] = {}
                        filtered_words_outlier[method] = {}
                        filtered_messages_outlier[method] = {}
                else:
                    # For coaching bots, show data for their version
                    version_key = version_name.replace('Coaching bot ', '')
                    filtered_words[method] = median_words_by_method[method].get(version_key, {})
                    filtered_messages[method] = median_messages_by_method[method].get(version_key, {})
                    filtered_words_outlier[method] = median_words_by_method_filtered[method].get(version_key, {})
                    filtered_messages_outlier[method] = median_messages_by_method_filtered[method].get(version_key, {})
            
            metric['median_words_by_method'] = filtered_words
            metric['median_messages_by_method'] = filtered_messages
            metric['median_words_by_method_filtered'] = filtered_words_outlier
            metric['median_messages_by_method_filtered'] = filtered_messages_outlier
            
            # Add median data to refrigerator_filtered metric
            if 'refrigerator_filtered' in metric:
                version_name = metric.get('version_name', '')
                filtered_words_r = {}
                filtered_messages_r = {}
                filtered_words_outlier_r = {}
                filtered_messages_outlier_r = {}
                
                for method in median_words_by_method_refrigerator:
                    filtered_words_r[method] = {}
                    filtered_messages_r[method] = {}
                    filtered_words_outlier_r[method] = {}
                    filtered_messages_outlier_r[method] = {}
                    
                    # For Control bot, only show data under Unknown method
                    if version_name == 'Control bot':
                        if method == 'Unknown':
                            filtered_words_r[method] = median_words_by_method_refrigerator[method].get('Control', {})
                            filtered_messages_r[method] = median_messages_by_method_refrigerator[method].get('Control', {})
                            filtered_words_outlier_r[method] = median_words_by_method_filtered_refrigerator[method].get('Control', {})
                            filtered_messages_outlier_r[method] = median_messages_by_method_filtered_refrigerator[method].get('Control', {})
                    else:
                        # For coaching bots, show data for their version
                        version_key = version_name.replace('Coaching bot ', '')
                        filtered_words_r[method] = median_words_by_method_refrigerator[method].get(version_key, {})
                        filtered_messages_r[method] = median_messages_by_method_refrigerator[method].get(version_key, {})
                        filtered_words_outlier_r[method] = median_words_by_method_filtered_refrigerator[method].get(version_key, {})
                        filtered_messages_outlier_r[method] = median_messages_by_method_filtered_refrigerator[method].get(version_key, {})
                
                metric['refrigerator_filtered']['median_words_by_method'] = filtered_words_r
                metric['refrigerator_filtered']['median_messages_by_method'] = filtered_messages_r
                metric['refrigerator_filtered']['median_words_by_method_filtered'] = filtered_words_outlier_r
                metric['refrigerator_filtered']['median_messages_by_method_filtered'] = filtered_messages_outlier_r
        
        # Calculate session progression data for line graph (both with and without outliers)
        # Also get session-level data for filtering
        print("Calculating session progression data...")
        progression_data, progression_session_data = self.calculate_session_progression_data(sessions, messages_data, exclude_outliers=False, return_session_data=True)
        progression_data_filtered, progression_session_data_filtered = self.calculate_session_progression_data(sessions, messages_data, exclude_outliers=True, return_session_data=True)
        
        # Calculate rating statistics
        print("Calculating rating statistics...")
        rating_stats = self.calculate_rating_statistics(sessions, messages_data)
        
        # Calculate session volume data for all aggregation levels (both with and without refrigerator filter)
        # Also get session mappings to track which sessions contribute to each count
        print("Calculating session volume data...")
        volume_data_day, volume_session_map_day = self.calculate_session_volume_by_time(sessions, messages_data, aggregation='day', refrigerator_only=False, return_session_mapping=True)
        volume_data_week, volume_session_map_week = self.calculate_session_volume_by_time(sessions, messages_data, aggregation='week', refrigerator_only=False, return_session_mapping=True)
        volume_data_month, volume_session_map_month = self.calculate_session_volume_by_time(sessions, messages_data, aggregation='month', refrigerator_only=False, return_session_mapping=True)
        
        volume_data = {
            'day': volume_data_day,
            'week': volume_data_week,
            'month': volume_data_month
        }
        volume_session_maps = {
            'day': volume_session_map_day,
            'week': volume_session_map_week,
            'month': volume_session_map_month
        }
        
        volume_data_refrigerator = {
            'day': self.calculate_session_volume_by_time(sessions, messages_data, aggregation='day', refrigerator_only=True),
            'week': self.calculate_session_volume_by_time(sessions, messages_data, aggregation='week', refrigerator_only=True),
            'month': self.calculate_session_volume_by_time(sessions, messages_data, aggregation='month', refrigerator_only=True)
        }
        
        # Create session_id -> participant_id mapping for client-side filtering
        session_participant_map = {}
        for session in sessions:
            session_id = session.get('id')
            participant_id = session.get('participant', {}).get('identifier', '')
            if session_id and participant_id:
                session_participant_map[session_id] = participant_id
        
        # Load GS data and calculate GS metrics
        print("Loading GS visit data...")
        gs_data = self.load_gs_visit_list()
        
        flw_breakdown = None
        avg_gs_scores = None
        if gs_data:
            print("Calculating FLW breakdown by GS tiers...")
            flw_breakdown = self.calculate_flw_breakdown_by_gs_tiers(gs_data)
            
            print("Calculating average GS scores by version and method...")
            avg_gs_scores = self.calculate_avg_gs_by_version_and_method(sessions, messages_data, gs_data)
        
        # Calculate tag counts
        print("Calculating tag counts by version and method...")
        tag_counts = self.calculate_tag_counts_by_version_and_method(sessions, messages_data)
        
        # Calculate tag GS scores
        tag_gs_scores = None
        if gs_data:
            print("Calculating tag GS scores by version and method...")
            tag_gs_scores = self.calculate_tag_gs_scores_by_version_and_method(sessions, messages_data, gs_data)
        
        # Prepare tag combination data
        print("Preparing tag combination data...")
        tag_combination_data = self.prepare_tag_combination_data(sessions, messages_data)
        
        # Prepare tag combination GS data
        tag_combination_gs_data = None
        if gs_data:
            print("Preparing tag combination GS data...")
            tag_combination_gs_data = self.prepare_tag_combination_gs_data(sessions, messages_data, gs_data)
        
        # Calculate today/yesterday preference tendency
        print("Calculating today/yesterday preference tendency...")
        today_yesterday_tendency = self.calculate_today_yesterday_tendency_by_version_and_method(sessions, messages_data)
        
        # Debug: Print statistics
        if today_yesterday_tendency and '_stats' in today_yesterday_tendency:
            total_questions = 0
            total_responses = 0
            for version_stats in today_yesterday_tendency['_stats'].values():
                for method_stats in version_stats.values():
                    total_questions += method_stats.get('sessions_with_question', 0)
                    total_responses += method_stats.get('sessions_with_response', 0)
            print(f"  Found {total_questions} sessions with today/yesterday questions")
            print(f"  Found {total_responses} sessions with valid responses")
        
        # Calculate average ratings for "today" and "yesterday" responses
        print("Calculating average ratings by preference...")
        avg_rating_today = self.calculate_average_rating_by_preference(sessions, messages_data, 'today')
        avg_rating_yesterday = self.calculate_average_rating_by_preference(sessions, messages_data, 'yesterday')
        
        # Calculate rating distribution
        print("Calculating rating distribution...")
        rating_distribution = self.calculate_rating_distribution(sessions, messages_data)
        
        # Load FLW activity data and calculate metrics
        print("Loading FLW activity data...")
        flw_activity_data = self.load_flw_activity_data()
        
        flw_activity_metrics = {}
        if flw_activity_data:
            print("Calculating FLW activity metrics...")
            flw_activity_metrics['approved_visits_percentage'] = self.calculate_flw_activity_metrics(sessions, messages_data, flw_activity_data, 'approved_visits_percentage')
            flw_activity_metrics['ecd_completed_intervention_percentage'] = self.calculate_flw_activity_metrics(sessions, messages_data, flw_activity_data, 'ecd_completed_intervention_percentage')
            flw_activity_metrics['visits_before_gs1'] = self.calculate_flw_activity_metrics(sessions, messages_data, flw_activity_data, 'visits_before_gs1')
            flw_activity_metrics['time_spent_learn'] = self.calculate_flw_activity_metrics(sessions, messages_data, flw_activity_data, 'time_spent_learn')
            flw_activity_metrics['post_test_tries'] = self.calculate_flw_activity_metrics(sessions, messages_data, flw_activity_data, 'post_test_tries')
            flw_activity_metrics['avg_distance_km_between_visits'] = self.calculate_flw_activity_metrics(sessions, messages_data, flw_activity_data, 'avg_distance_km_between_visits')
            flw_activity_metrics['avg_minutes_between_visits'] = self.calculate_flw_activity_metrics(sessions, messages_data, flw_activity_data, 'avg_minutes_between_visits')
        
        # Generate HTML
        html_content = self.generate_dashboard_html(metrics, progression_data, rating_stats, progression_data_filtered, volume_data, volume_data_refrigerator, session_participant_map, volume_session_maps, progression_session_data, progression_session_data_filtered, sessions, messages_data, flw_breakdown, avg_gs_scores, tag_counts, tag_combination_data, today_yesterday_tendency, avg_rating_today, avg_rating_yesterday, tag_gs_scores, tag_combination_gs_data, rating_distribution, flw_activity_metrics)
        
        # Save to file
        output_file = self.output_dir / "version_comparison_dashboard.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Dashboard generated: {output_file}")
        return str(output_file)

def main():
    """Main entry point"""
    dashboard = SimpleVersionComparisonDashboard()
    output_file = dashboard.generate_dashboard()
    
    if output_file and os.path.exists(output_file):
        webbrowser.open(f"file://{os.path.abspath(output_file)}")
        print(f"Dashboard opened: {output_file}")
        print("Note: For full functionality, serve via HTTP server:")
        print(f"cd {os.path.dirname(output_file)} && python3 -m http.server 8002")
    else:
        print("Failed to generate dashboard")

if __name__ == "__main__":
    main()
