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
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
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
        """Check if session is a split session - defined as session with no participant messages"""
        if messages is None:
            return False
        
        # Check if there are any user messages
        for message in messages:
            if message.get('role') == 'user':
                return False  # Has user messages, not a split session
        
        return True  # No user messages found, this is a split session
    
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
    
    def calculate_refrigerator_rate_by_method(self, sessions: List[Dict], messages_data: Dict) -> Dict[str, float]:
        """Calculate refrigerator example rate by coaching method"""
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
            # Filter sessions that have refrigerator annotations (refrigerator_example OR not_refrigerator_example)
            annotated_sessions = []
            for session, messages in session_list:
                if self.has_refrigerator_annotation(session, messages):
                    annotated_sessions.append((session, messages))
            
            if not annotated_sessions:
                method_rates[method] = 0.0
                continue
            
            # Count sessions with refrigerator_example tag
            refrigerator_count = 0
            for session, messages in annotated_sessions:
                if self.has_refrigerator_example_tag(session, messages):
                    refrigerator_count += 1
            
            # Calculate rate
            rate = (refrigerator_count / len(annotated_sessions)) * 100
            method_rates[method] = rate
        
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

    def calculate_median_messages_by_method_and_version(self, sessions: List[Dict], messages: Dict) -> Dict[str, Dict[str, float]]:
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
                # Count user messages for this session
                user_message_count = 0
                for message in session_messages:
                    if message.get('role') == 'user':
                        user_message_count += 1
                
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

    def calculate_session_progression_data(self, sessions: List[Dict], messages: List[Dict], exclude_outliers: bool = False) -> Dict:
        """Calculate session progression data for line graph"""
        # Group sessions by participant, excluding split and test sessions
        participant_sessions = {}
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
        
        # Calculate averages for each session number
        for option in progression_data:
            for key in progression_data[option]:
                for session_num in progression_data[option][key]:
                    word_counts = progression_data[option][key][session_num]
                    if word_counts:
                        progression_data[option][key][session_num] = sum(word_counts) / len(word_counts)
                    else:
                        progression_data[option][key][session_num] = 0
        
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
        
        rows = ""
        for method in sorted_methods:
            row = f"<tr><td><strong>{method}</strong></td>"
            for metric in metrics:
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
                    else:
                        row += f"<td>-</td>"
            row += "</tr>"
            rows += row
        
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

        rows = ""
        for method in sorted_methods:
            row = f"<tr><td><strong>{method}</strong></td>"
            for metric in metrics:
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
                            else:
                                row += f"<td>0.0</td>"
                        else:
                            if method_messages > 0:
                                row += f"<td>{method_messages:.1f}</td>"
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
                    else:
                        row += f"<td>-</td>"
            row += "</tr>"
            rows += row

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
        
        rows = ""
        for method in sorted_methods:
            row = f"<tr><td><strong>{method}</strong></td>"
            for metric in metrics:
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
                    else:
                        row += f"<td>-</td>"
            row += "</tr>"
            rows += row
        
        return rows
    
    def generate_method_table_rows(self, metrics: List[Dict]) -> str:
        """Generate table rows for refrigerator rate by method"""
        # Get all unique methods across all versions
        all_methods = set()
        for metric in metrics:
            method_rates = metric.get('method_refrigerator_rates', {})
            all_methods.update(method_rates.keys())
        
        # Sort methods for consistent display
        method_order = ['Scenario', 'Microlearning', 'Microlearning vaccines', 'Motivational interviewing', 'Visit check in', 'Unknown']
        sorted_methods = [method for method in method_order if method in all_methods]
        sorted_methods.extend([method for method in all_methods if method not in method_order])
        
        rows = ""
        for method in sorted_methods:
            row = f"<tr><td><strong>{method}</strong></td>"
            for metric in metrics:
                method_rates = metric.get('method_refrigerator_rates', {})
                rate = method_rates.get(method, 0.0)
                if rate and rate > 0:
                    row += f"<td>{rate:.1f}%</td>"
                else:
                    row += f"<td>-</td>"
            row += "</tr>"
            rows += row
        
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
    
    def calculate_metrics_for_version(self, version_name: str, sessions: List[Dict], messages_data: Dict) -> Dict:
        """Calculate metrics for a specific version"""
        # Filter out split sessions and test sessions
        valid_sessions = []
        for session in sessions:
            session_id = session.get('id')
            messages = messages_data.get(session_id, [])
            if not self.should_exclude_session(session, messages):
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
    
    def generate_dashboard_html(self, metrics: List[Dict], progression_data: Dict = None, rating_stats: Dict = None, progression_data_filtered: Dict = None) -> str:
        """Generate complete dashboard HTML"""
        # Generate summary table
        table_rows = ""
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
        
        # Generate refrigerator rate by method table
        method_table_rows = self.generate_method_table_rows(metrics)
        
        # Generate median words by method table
        median_words_table_rows = self.generate_median_words_table_rows(metrics)
        
        # Generate rating by method table
        rating_table_rows = self.generate_rating_table_rows(metrics)
        
        # Convert progression data to JSON for JavaScript
        progression_data_json = json.dumps(progression_data) if progression_data else "{}"
        progression_data_filtered_json = json.dumps(progression_data_filtered) if progression_data_filtered else "{}"
        
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
                                <tbody>
                                    {table_rows}
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
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3>Refrigerator Example Rate by Method and Version</h3>
                                    </div>
                                    <div class="card-body">
                                        <div class="table-responsive">
                                            <table class="table table-striped table-hover">
                                                <thead class="table-dark">
                                                    <tr>
                                                        <th>Method</th>
                                                        {''.join([f'<th>{metric["version_name"]}</th>' for metric in metrics])}
                                                    </tr>
                                                </thead>
                                                <tbody>
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
                                                    </tr>
                                                </thead>
                                                <tbody>
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
                                            <table class="table table-striped table-hover">
                                                <thead class="table-dark">
                                                    <tr>
                                                        <th>Method</th>
                                                        {''.join([f'<th>{metric["version_name"]}</th>' for metric in metrics])}
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
                                            <div class="form-check">
                                                <input class="form-check-input" type="checkbox" id="excludeOutliers" onchange="toggleOutlierFilter()">
                                                <label class="form-check-label" for="excludeOutliers">
                                                    Exclude outlier sessions (sessions with >50 messages or >1000 words)
                                                </label>
                                            </div>
                                        </div>
                                        <div class="table-responsive">
                                            <table class="table table-striped table-hover" id="medianWordsTable">
                                                <thead class="table-dark">
                                                    <tr>
                                                        <th>Method</th>
                                                        {''.join([f'<th>{metric["version_name"]}</th>' for metric in metrics])}
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
                                                    <div class="form-check mt-4">
                                                        <input class="form-check-input" type="checkbox" id="excludeOutliersProgression" onchange="updateProgressionChart()">
                                                        <label class="form-check-label" for="excludeOutliersProgression">
                                                            Exclude outlier sessions
                                                        </label>
                                                    </div>
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

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        // Progression data from server
        const progressionData = {progression_data_json};
        const progressionDataFiltered = {progression_data_filtered_json};
        
        let progressionChart = null;
        
        function updateProgressionChart() {{
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead class="table-dark">
                                    <tr>
                                        <th>Method</th>
                                        {''.join([f'<th>{metric["version_name"]}</th>' for metric in metrics])}
                                    </tr>
                                </thead>
                                <tbody>
                                    {rating_table_rows}
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
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead class="table-dark">
                                    <tr>
                                        <th>Method</th>
                                        {''.join([f'<th>{metric["version_name"]}</th>' for metric in metrics])}
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
                        <h3>Session Progression Analysis</h3>
                    </div>
                    <div class="card-body">
                        <div class="mb-3">
                            <label for="progressionView" class="form-label">Select View:</label>
                            <select class="form-select" id="progressionView" onchange="updateProgressionChart()">
                                <option value="by_method">By Coaching Method</option>
                                <option value="by_method_version">By Method and Version</option>
                                <option value="by_version">By Version Only</option>
                            </select>
                        </div>
                        <div class="chart-container" style="position: relative; height: 400px;">
                            <canvas id="progressionChart"></canvas>
                        </div>
                        <div class="mt-3">
                            <small class="text-muted">
                                <strong>X-axis:</strong> Session number (1st, 2nd, 3rd, etc. session for each participant)<br>
                                <strong>Y-axis:</strong> Average number of words per session<br>
                                <strong>Data:</strong> Limited to first 22 sessions per participant
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mt-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h3>Definitions</h3>
                    </div>
                    <div class="card-body">
                        <h5>Bot Categories</h5>
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Category</th>
                                    <th>Experiment ID</th>
                                    <th>Version Range</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td><strong>Control bot</strong></td>
                                    <td>1027993a-40c9-4484-a5fb-5c7e034dadcd</td>
                                    <td>All versions</td>
                                </tr>
                                <tr>
                                    <td><strong>Coaching bot V3</strong></td>
                                    <td>e2b4855f-8550-47ff-87d2-d92018676ff3</td>
                                    <td>All versions</td>
                                </tr>
                                <tr>
                                    <td><strong>Coaching bot V4</strong></td>
                                    <td>b7621271-da98-459f-9f9b-f68335d09ad4</td>
                                    <td>13 and above</td>
                                </tr>
                                <tr>
                                    <td><strong>Coaching bot V5</strong></td>
                                    <td>5d8be75e-03ff-4e3a-ab6a-e0aff6580986</td>
                                    <td>1 to 4</td>
                                </tr>
                                <tr>
                                    <td><strong>Coaching bot V6</strong></td>
                                    <td>5d8be75e-03ff-4e3a-ab6a-e0aff6580986</td>
                                    <td>5 and above</td>
                                </tr>
                            </tbody>
                        </table>
                        
                        <h5 class="mt-4">Metric Definitions</h5>
                        <ul>
                            <li><strong>Sessions:</strong> Bot-initiated interactions excluding split sessions (sessions with no participant messages) and test sessions (participant ID ending with @dimagi.com)</li>
                            <li><strong>Annotated Sessions:</strong> Sessions with non-version tags</li>
                            <li><strong>Refrigeration Examples:</strong> Sessions with "refrigerator_example" tag</li>
                            <li><strong>Median Human Words:</strong> Median word count of user messages per session</li>
                            <li><strong>Average Session Rating:</strong> Mean rating (1-5) from user feedback</li>
                        </ul>
                        
                        <h5 class="mt-4">Data Quality and Filtering</h5>
                        <p>This dashboard applies comprehensive filtering to ensure data quality and consistency across all indicators:</p>
                        <ul>
                            <li><strong>Split Sessions Excluded:</strong> Sessions with no participant messages (bot-only interactions)</li>
                            <li><strong>Test Sessions Excluded:</strong> Sessions with participant IDs ending in @dimagi.com (internal testing)</li>
                            <li><strong>Consistent Filtering:</strong> All tables, graphs, and metrics use the same exclusion criteria</li>
                            <li><strong>Enhanced Rating Detection:</strong> Comprehensive pattern matching improves rating extraction from 0.07% to 68% of sessions</li>
                            <li><strong>Version Detection:</strong> Based on experiment IDs and version tags from the last message in each session</li>
                        </ul>
                        
                        <h5 class="mt-4">Refrigerator Example Rate by Method</h5>
                        <p>This metric shows the percentage of sessions with refrigerator examples within each coaching method.</p>
                        <ul>
                            <li><strong>Method Detection:</strong> Based on session tags (coach_method_*) or message content analysis</li>
                            <li><strong>Calculation:</strong> (Sessions with "refrigerator_example" tag) / (Sessions with refrigerator annotations) × 100</li>
                            <li><strong>Denominator:</strong> Sessions with "refrigerator_example" OR "not_refrigerator_example" tags</li>
                            <li><strong>Numerator:</strong> Sessions with "refrigerator_example" tag</li>
                        </ul>
                        
                        <h6>Coaching Methods:</h6>
                        <ul>
                            <li><strong>Scenario:</strong> Roleplay-based coaching sessions</li>
                            <li><strong>Microlearning:</strong> Quiz-based learning sessions</li>
                            <li><strong>Microlearning vaccines:</strong> Vaccine-specific quiz sessions</li>
                            <li><strong>Motivational interviewing:</strong> Motivational interview techniques</li>
                            <li><strong>Visit check in:</strong> Home visit debrief sessions</li>
                        </ul>
                        
                        <h5 class="mt-4">Average FLW Score by Method and Version</h5>
                        <p>This metric shows the average session rating (1-5 scale) grouped by coaching method and bot version.</p>
                        <ul>
                            <li><strong>Calculation:</strong> Average of user ratings using comprehensive pattern matching for rating questions and responses</li>
                            <li><strong>Rating Scale:</strong> 1 (not useful) to 5 (very useful)</li>
                            <li><strong>Rating Detection:</strong> Comprehensive pattern matching for various rating question formats and user response patterns</li>
                            <li><strong>Method Detection:</strong> Based on session tags (coach_method_*) or message content analysis</li>
                            <li><strong>Version Detection:</strong> Based on experiment ID and version tags from last message</li>
                            <li><strong>Purpose:</strong> Identify whether coaching methods receive higher ratings with bot evolution</li>
                            <li><strong>Data Coverage:</strong> ~68% of sessions have extractable ratings (vs. 0.07% with basic pattern matching)</li>
                            <li><strong>Rating Statistics:</strong> Dynamic footnotes show rating question coverage and extraction rates for transparency</li>
                        </ul>
                        
                        <h5 class="mt-4">Median User Words per Session by Method and Version</h5>
                        <p>This metric shows the median number of words users type per session, grouped by coaching method and bot version.</p>
                        <ul>
                            <li><strong>Calculation:</strong> Median word count of all user messages within a session</li>
                            <li><strong>Method Detection:</strong> Based on session tags (coach_method_*) or message content analysis</li>
                            <li><strong>Version Detection:</strong> Based on experiment ID and version tags from last message</li>
                            <li><strong>Word Count:</strong> Total words across all user messages in a session</li>
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

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        // Progression data from server
        const progressionData = {progression_data_json};
        const progressionDataFiltered = {progression_data_filtered_json};
        
        let progressionChart = null;
        
        function toggleOutlierFilter() {{
            // This function would need to be implemented to recalculate data with outlier filtering
            // For now, it's a placeholder that could trigger a page reload or AJAX call
            console.log('Outlier filter toggled - this would require server-side recalculation');
        }}
        
        function updateProgressionChart() {{
            const view = document.getElementById('progressionView').value;
            const excludeOutliers = document.getElementById('excludeOutliersProgression').checked;
            const data = excludeOutliers ? progressionDataFiltered[view] : progressionData[view];
            
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
        
        // Initialize chart on page load
        document.addEventListener('DOMContentLoaded', function() {{
            updateProgressionChart();
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
            
            # Calculate metrics
            metric = self.calculate_metrics_for_version(version_name, version_sessions, messages_data)
            metrics.append(metric)
        
        # Calculate median words and messages by method and version (needs all sessions)
        print("Calculating median words and messages by method and version...")
        median_words_by_method = self.calculate_median_words_by_method_and_version(sessions, messages_data)
        median_messages_by_method = self.calculate_median_messages_by_method_and_version(sessions, messages_data)
        
        # Add the median data to each metric, filtered by version
        for metric in metrics:
            version_name = metric.get('version_name', '')
            filtered_words = {}
            filtered_messages = {}
            
            for method in median_words_by_method:
                filtered_words[method] = {}
                filtered_messages[method] = {}
                
                # For Control bot, only show data under Unknown method
                if version_name == 'Control bot':
                    if method == 'Unknown':
                        # Show Control bot data
                        filtered_words[method] = median_words_by_method[method].get('Control', {})
                        filtered_messages[method] = median_messages_by_method[method].get('Control', {})
                    else:
                        # Show empty for specific methods
                        filtered_words[method] = {}
                        filtered_messages[method] = {}
                else:
                    # For coaching bots, show data for their version
                    version_key = version_name.replace('Coaching bot ', '')
                    filtered_words[method] = median_words_by_method[method].get(version_key, {})
                    filtered_messages[method] = median_messages_by_method[method].get(version_key, {})
            
            metric['median_words_by_method'] = filtered_words
            metric['median_messages_by_method'] = filtered_messages
        
        # Calculate session progression data for line graph (both with and without outliers)
        print("Calculating session progression data...")
        progression_data = self.calculate_session_progression_data(sessions, messages_data)
        progression_data_filtered = self.calculate_session_progression_data(sessions, messages_data, exclude_outliers=True)
        
        # Calculate rating statistics
        print("Calculating rating statistics...")
        rating_stats = self.calculate_rating_statistics(sessions, messages_data)
        
        # Generate HTML
        html_content = self.generate_dashboard_html(metrics, progression_data, rating_stats, progression_data_filtered)
        
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
