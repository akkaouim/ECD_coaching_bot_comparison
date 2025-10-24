#!/usr/bin/env python3
"""
Analyze message content to find different patterns of rating questions.
"""

import json
import re
from pathlib import Path
from collections import Counter
from typing import Dict, List, Set

def load_sample_messages(num_files: int = 100) -> List[Dict]:
    """Load a sample of message files for analysis."""
    messages_dir = Path("../data/consolidated/messages")
    
    if not messages_dir.exists():
        print("Error: Messages directory not found")
        return []
    
    message_files = list(messages_dir.glob("messages_*.json"))
    print(f"Found {len(message_files)} message files")
    
    # Take a sample for analysis
    sample_files = message_files[:num_files]
    print(f"Analyzing {len(sample_files)} message files...")
    
    messages_data = []
    for message_file in sample_files:
        try:
            with open(message_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
                messages = session_data.get('messages', [])
                if messages:
                    messages_data.extend(messages)
        except Exception as e:
            print(f"Warning: Could not load {message_file.name}: {e}")
            continue
    
    print(f"Loaded {len(messages_data)} messages for analysis")
    return messages_data

def find_rating_patterns(messages: List[Dict]) -> Dict:
    """Find different patterns of rating questions in messages."""
    rating_patterns = {
        'rating_questions': [],
        'rating_keywords': set(),
        'rating_numbers': set(),
        'usefulness_mentions': [],
        'rate_mentions': [],
        'score_mentions': [],
        'feedback_mentions': []
    }
    
    # Keywords to look for
    rating_keywords = [
        'rate', 'rating', 'score', 'useful', 'usefulness', 'helpful', 'feedback',
        'satisfied', 'satisfaction', 'experience', 'session', 'coaching'
    ]
    
    number_patterns = [
        r'\b[1-5]\b',  # Single digits 1-5
        r'\bone\b', r'\btwo\b', r'\bthree\b', r'\bfour\b', r'\bfive\b',  # Written numbers
        r'\b1-5\b', r'\b1 to 5\b', r'\b1 through 5\b'  # Range patterns
    ]
    
    for message in messages:
        if message.get('role') != 'assistant':
            continue
            
        content = message.get('content', '').lower()
        
        # Look for rating-related keywords
        for keyword in rating_keywords:
            if keyword in content:
                rating_patterns['rating_keywords'].add(keyword)
        
        # Look for number patterns
        for pattern in number_patterns:
            if re.search(pattern, content):
                rating_patterns['rating_numbers'].add(pattern)
        
        # Look for specific phrases
        if 'useful' in content and ('rate' in content or 'rating' in content):
            rating_patterns['usefulness_mentions'].append(content[:200] + '...')
        
        if 'rate' in content and ('1' in content or '2' in content or '3' in content or '4' in content or '5' in content):
            rating_patterns['rate_mentions'].append(content[:200] + '...')
        
        if 'score' in content:
            rating_patterns['score_mentions'].append(content[:200] + '...')
        
        if 'feedback' in content:
            rating_patterns['feedback_mentions'].append(content[:200] + '...')
        
        # Look for any message that might be asking for a rating
        if any(keyword in content for keyword in ['rate', 'rating', 'score']) and any(num in content for num in ['1', '2', '3', '4', '5']):
            rating_patterns['rating_questions'].append(content[:300] + '...')
    
    return rating_patterns

def analyze_rating_responses(messages: List[Dict]) -> Dict:
    """Analyze potential rating responses from users."""
    user_ratings = []
    
    for message in messages:
        if message.get('role') != 'user':
            continue
            
        content = message.get('content', '').strip()
        
        # Look for single digit responses
        if re.match(r'^\s*[1-5]\s*$', content):
            user_ratings.append(('single_digit', content))
        
        # Look for written number responses
        written_numbers = {
            'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5'
        }
        content_lower = content.lower()
        for word, num in written_numbers.items():
            if content_lower == word:
                user_ratings.append(('written_number', content))
        
        # Look for responses with context
        if re.search(r'\b[1-5]\b', content) and len(content) < 50:
            user_ratings.append(('context_rating', content))
    
    return user_ratings

def main():
    print("Analyzing rating patterns in messages...")
    
    # Load sample messages
    messages = load_sample_messages(200)  # Analyze 200 files for patterns
    
    if not messages:
        print("No messages found")
        return
    
    print(f"\nAnalyzing {len(messages)} messages...")
    
    # Find rating patterns
    patterns = find_rating_patterns(messages)
    
    print(f"\n=== RATING PATTERN ANALYSIS ===")
    print(f"Rating keywords found: {sorted(patterns['rating_keywords'])}")
    print(f"Number patterns found: {sorted(patterns['rating_numbers'])}")
    
    print(f"\n=== USEFULNESS MENTIONS ({len(patterns['usefulness_mentions'])}) ===")
    for i, mention in enumerate(patterns['usefulness_mentions'][:5]):  # Show first 5
        print(f"{i+1}. {mention}")
    
    print(f"\n=== RATE MENTIONS ({len(patterns['rate_mentions'])}) ===")
    for i, mention in enumerate(patterns['rate_mentions'][:5]):  # Show first 5
        print(f"{i+1}. {mention}")
    
    print(f"\n=== SCORE MENTIONS ({len(patterns['score_mentions'])}) ===")
    for i, mention in enumerate(patterns['score_mentions'][:5]):  # Show first 5
        print(f"{i+1}. {mention}")
    
    print(f"\n=== FEEDBACK MENTIONS ({len(patterns['feedback_mentions'])}) ===")
    for i, mention in enumerate(patterns['feedback_mentions'][:5]):  # Show first 5
        print(f"{i+1}. {mention}")
    
    print(f"\n=== POTENTIAL RATING QUESTIONS ({len(patterns['rating_questions'])}) ===")
    for i, question in enumerate(patterns['rating_questions'][:10]):  # Show first 10
        print(f"{i+1}. {question}")
    
    # Analyze user responses
    user_ratings = analyze_rating_responses(messages)
    print(f"\n=== POTENTIAL USER RATINGS ({len(user_ratings)}) ===")
    for i, (type_, content) in enumerate(user_ratings[:10]):  # Show first 10
        print(f"{i+1}. [{type_}] {content}")

if __name__ == "__main__":
    main()
