#!/usr/bin/env python3
"""
Find actual examples of today/yesterday preference questions in messages
"""

import json
import re
from pathlib import Path
from collections import defaultdict

def load_messages():
    """Load sample messages"""
    messages_dir = Path("../data/consolidated/messages")
    if not messages_dir.exists():
        print(f"Error: {messages_dir} not found")
        return {}
    
    messages_data = {}
    message_files = list(messages_dir.glob("messages_*.json"))  # Load all
    
    for message_file in message_files:
        try:
            with open(message_file, 'r', encoding='utf-8') as f:
                message_data = json.load(f)
                if 'messages' in message_data:
                    session_id = message_file.stem.replace('messages_', '')
                    messages_data[session_id] = message_data['messages']
        except Exception as e:
            continue
    
    return messages_data

def find_today_yesterday_questions(messages_data):
    """Find messages containing today/yesterday questions"""
    question_examples = []
    
    for session_id, messages in messages_data.items():
        for message in messages:
            if message.get('role') == 'assistant':
                content = message.get('content', '').lower()
                original_content = message.get('content', '')
                
                # Look for any mention of both "today" and "yesterday" (including possessive forms)
                has_today = 'today' in content or "today's" in content
                has_yesterday = 'yesterday' in content or "yesterday's" in content
                
                if has_today and has_yesterday:
                    # Check if it looks like a question
                    question_indicators = [
                        'which', 'what', 'do you', 'did you', 'would you', 
                        'prefer', 'find', 'useful', 'better', '?'
                    ]
                    if any(indicator in content for indicator in question_indicators):
                        question_examples.append({
                            'session_id': session_id,
                            'content': original_content[:500],  # First 500 chars
                            'full_content': original_content
                        })
    
    return question_examples

def main():
    print("Loading messages...")
    messages_data = load_messages()
    print(f"Loaded {len(messages_data)} sessions")
    
    print("\nSearching for today/yesterday questions...")
    examples = find_today_yesterday_questions(messages_data)
    
    print(f"\nFound {len(examples)} messages containing both 'today' and 'yesterday'")
    print("\nFirst 10 examples:")
    print("=" * 80)
    
    for i, example in enumerate(examples[:10], 1):
        print(f"\nExample {i} (Session: {example['session_id']}):")
        print("-" * 80)
        print(example['content'])
        print()
    
    # Also check for variations
    print("\n" + "=" * 80)
    print("Checking for other patterns...")
    
    # Check for "prefer" with "today" or "yesterday"
    prefer_examples = []
    for session_id, messages in messages_data.items():
        for message in messages:
            if message.get('role') == 'assistant':
                content = message.get('content', '').lower()
                if 'prefer' in content and ('today' in content or 'yesterday' in content):
                    prefer_examples.append({
                        'session_id': session_id,
                        'content': message.get('content', '')[:500]
                    })
    
    print(f"\nFound {len(prefer_examples)} messages with 'prefer' and 'today'/'yesterday'")
    if prefer_examples:
        print("\nFirst 5 examples:")
        for i, example in enumerate(prefer_examples[:5], 1):
            print(f"\nExample {i} (Session: {example['session_id']}):")
            print("-" * 80)
            print(example['content'])

if __name__ == "__main__":
    main()

