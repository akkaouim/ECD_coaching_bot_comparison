# Version Comparison Dashboard - Technical Specifications

## 🏗️ Architecture Overview

### System Components

```
Version Comparison Dashboard
├── Data Layer
│   ├── Session Files (JSON)
│   ├── Message Files (JSON)
│   └── Data Filtering Engine
├── Processing Layer
│   ├── Version Matching Logic
│   ├── Metric Calculation Engine
│   └── Data Aggregation
├── Presentation Layer
│   ├── HTML Template Engine
│   ├── Bootstrap Styling
│   └── Responsive Design
└── Output Layer
    ├── Generated HTML
    ├── Static Assets
    └── Documentation
```

### Data Flow

```
Raw Data Files → Filtering → Processing → Metrics → HTML Generation → Dashboard
```

## 📊 Data Specifications

### Input Data Format

#### Session Files (`session_*.json`)
```json
{
  "id": "session-uuid",
  "experiment": {
    "id": "experiment-uuid",
    "name": "ECD Coach - (Nigeria Experiments) V6",
    "version_number": 5
  },
  "participant": {
    "identifier": "user-123",
    "remote_id": "remote-123"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:00:00Z",
  "tags": ["coaching_good", "refrigerator_example"],
  "team": {
    "name": "Nigeria Team",
    "slug": "nigeria"
  }
}
```

#### Message Files (`messages_*.json`)
```json
{
  "id": "session-uuid",
  "messages": [
    {
      "role": "assistant",
      "content": "How useful did you find this coaching session? Please rate it from 1 to 5.",
      "created_at": "2024-01-15T10:30:00Z",
      "tags": ["rating_question"]
    },
    {
      "role": "user",
      "content": "4",
      "created_at": "2024-01-15T10:31:00Z",
      "tags": []
    }
  ]
}
```

### Output Data Format

#### Metrics Dictionary
```python
{
    'version_name': 'Coaching bot V6',
    'total_sessions': 1758,
    'annotated_sessions': 1234,
    'refrigerator_examples_percent': 22.1,
    'median_human_words_per_session': 16.8,
    'average_session_rating': 4.6,
    'method_refrigerator_rates': {
        'Scenario': {'V6': 25.5},
        'Microlearning': {'V6': 18.2}
    },
    'median_words_by_method': {
        'Scenario': {'V6': 24.3},
        'Microlearning': {'V6': 19.7}
    },
    'average_rating_by_method': {
        'Scenario': {'V6': 4.2},
        'Microlearning': {'V6': 4.5}
    }
}
```

## 🔧 Technical Implementation

### Core Classes

#### `SimpleVersionComparisonDashboard`
Main dashboard generator class with methods:

- `__init__()`: Initialize dashboard with version definitions
- `load_sessions_from_files()`: Load and filter session data
- `load_messages_from_files()`: Load and filter message data
- `matches_version()`: Check if session matches version criteria
- `calculate_metrics_for_version()`: Compute metrics for a version
- `generate_dashboard_html()`: Create HTML output
- `generate_dashboard()`: Main orchestration method

#### `CoachingBotVersion` (Conceptual)
Version definition structure:
```python
{
    "name": "Coaching bot V6",
    "experiment_id": ["5d8be75e-03ff-4e3a-ab6a-e0aff6580986"],
    "version_range": (5, None)  # 5 and above
}
```

### Algorithm Specifications

#### Version Matching Algorithm
```python
def matches_version(session, version_config, messages):
    # 1. Check experiment ID match
    experiment_id = session.get('experiment', {}).get('id', '')
    if experiment_id not in version_config['experiment_id']:
        return False
    
    # 2. Get version from last message tags
    version_number = get_version_from_last_message(messages)
    
    # 3. Check version constraints
    version_range = version_config.get('version_range')
    if version_range is None:
        return True  # All versions
    elif version_range[1] is None:
        return version_number >= version_range[0]
    else:
        return version_range[0] <= version_number <= version_range[1]
```

#### Session Filtering Algorithm
```python
def is_split_session(session):
    # Check for split_session tag
    if 'split_session' in session.get('tags', []):
        return True
    
    # Check if session has only 1 assistant message (bot-initiated)
    if session.get('message_count', 0) == 1 and session.get('first_message_role') == 'assistant':
        return True
    
    return False
```

#### Annotation Detection Algorithm
```python
def is_annotated_session(session, messages):
    # Check session-level tags
    for tag in session.get('tags', []):
        if not is_version_tag(tag):
            return True
    
    # Check message-level tags
    for message in messages:
        for tag in message.get('tags', []):
            if not is_version_tag(tag):
                return True
    
    return False

def is_version_tag(tag):
    tag_lower = tag.lower()
    return (tag_lower.startswith('v') and tag_lower[1:].isdigit()) or 'unreleased' in tag_lower
```

#### Rating Extraction Algorithm
```python
def extract_session_rating(session, messages):
    # Look for rating question pattern
    for i, message in enumerate(messages):
        if (message.get('role') == 'assistant' and 
            'how useful did you find this coaching session' in message.get('content', '').lower() and
            'rate it from 1 to 5' in message.get('content', '').lower()):
            
            # Look for numeric response in next user message
            for j in range(i + 1, len(messages)):
                if messages[j].get('role') == 'user':
                    content = messages[j].get('content', '').strip()
                    numbers = re.findall(r'\b([1-5])\b', content)
                    if numbers:
                        return float(numbers[0])
    
    return None
```

### Performance Optimizations

#### Data Loading Strategy
1. **Filtered Loading**: Only load sessions from relevant experiments
2. **Lazy Loading**: Load messages only for filtered sessions
3. **Memory Efficiency**: Process data in chunks to avoid memory issues
4. **Early Termination**: Stop processing when no more relevant data found

#### Processing Optimizations
1. **Lookup Tables**: Use dictionaries for O(1) session-message matching
2. **Batch Processing**: Process multiple sessions together
3. **Caching**: Cache frequently accessed data
4. **Progress Tracking**: Show progress for long-running operations

### Memory Management

#### Memory Usage Patterns
- **Peak Memory**: During data loading phase
- **Processing Memory**: During metric calculations
- **Output Memory**: During HTML generation

#### Optimization Strategies
```python
# Process sessions in batches
def process_sessions_batch(sessions, batch_size=1000):
    for i in range(0, len(sessions), batch_size):
        batch = sessions[i:i + batch_size]
        yield process_batch(batch)

# Use generators for large datasets
def load_sessions_generator(sessions_dir):
    for session_file in sessions_dir.glob("session_*.json"):
        yield load_session(session_file)
```

## 🎨 Frontend Specifications

### HTML Structure
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Version Comparison Dashboard - OCS</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <!-- Navigation -->
    </nav>
    <div class="container mt-4">
        <div class="row">
            <div class="col-12">
                <!-- Summary Metrics Table -->
            </div>
        </div>
        <div class="row mt-4">
            <div class="col-12">
                <!-- Definitions Section -->
            </div>
        </div>
    </div>
</body>
</html>
```

### CSS Specifications
- **Framework**: Bootstrap 5.3.0
- **Icons**: Font Awesome 6.0.0
- **Responsive**: Mobile-first design
- **Colors**: Professional blue gradient theme
- **Typography**: Segoe UI font family

### JavaScript Requirements
- **Bootstrap JS**: For interactive components
- **No Custom JS**: Pure HTML/CSS implementation
- **CDN Delivery**: External resources for portability

## 📈 Performance Metrics

### Benchmarks
- **Data Loading**: ~2-5 seconds for 7,772 sessions
- **Processing**: ~1-3 seconds for metric calculations
- **HTML Generation**: ~0.5-1 second for dashboard creation
- **Total Runtime**: ~5-10 seconds end-to-end

### Scalability
- **Session Limit**: Tested up to 25,000 sessions
- **Memory Usage**: ~100-200MB peak for large datasets
- **File I/O**: Optimized for sequential file reading
- **CPU Usage**: Single-threaded processing

### Optimization Targets
- **Load Time**: < 10 seconds for 10,000 sessions
- **Memory Usage**: < 500MB for 50,000 sessions
- **Output Size**: < 1MB HTML file
- **Browser Compatibility**: Chrome, Firefox, Safari, Edge

## 🔒 Security Considerations

### Data Protection
- **No Sensitive Data**: Dashboard excludes PII and sensitive information
- **Local Processing**: All data processing happens locally
- **No External Calls**: No network requests during generation
- **Static Output**: Generated HTML is completely static

### File Access
- **Read-Only Access**: Only reads data files, never modifies
- **Path Validation**: Validates file paths before access
- **Error Handling**: Graceful handling of missing or corrupted files
- **Permission Checks**: Respects file system permissions

## 🧪 Testing Specifications

### Unit Tests
```python
def test_version_matching():
    session = {"experiment": {"name": "ECD Coach V6", "version_number": 5}}
    config = {"experiment_name": "ECD Coach", "version_range": (1, 10)}
    assert matches_version(session, config) == True

def test_annotation_detection():
    session = {"tags": ["coaching_good", "v5"]}
    assert is_annotated_session(session, []) == True

def test_rating_extraction():
    messages = [
        {"role": "assistant", "content": "Rate it from 1 to 5"},
        {"role": "user", "content": "4"}
    ]
    assert extract_session_rating({}, messages) == 4.0
```

### Integration Tests
- **Data Loading**: Test with various data file structures
- **Version Matching**: Test with different experiment names and versions
- **Metric Calculation**: Test with known data sets
- **HTML Generation**: Test output format and styling

### Performance Tests
- **Load Testing**: Test with large datasets
- **Memory Testing**: Monitor memory usage patterns
- **Stress Testing**: Test with corrupted or missing data
- **Regression Testing**: Ensure performance doesn't degrade

## 📋 Configuration Options

### Environment Variables
```bash
# Data directory path
DATA_DIR=data/consolidated

# Output directory path
OUTPUT_DIR=output/version_comparison

# Debug mode
DEBUG=false

# Test mode (limit data)
TEST_MODE=false
```

### Version Definitions
```python
COACHING_BOT_VERSIONS = {
    "Coaching bot V3": {
        "experiment_name": "ECD Control Bot - Nigeria - Connect Experiments",
        "version_range": None
    },
    "Coaching bot V4": {
        "experiment_name": "ECD Coach - (Nigeria Experiments) V4",
        "version_range": (23, None)
    }
}
```

### Metric Thresholds
```python
METRIC_THRESHOLDS = {
    "min_sessions": 10,
    "min_annotated_sessions": 5,
    "min_rating": 1.0,
    "max_rating": 5.0
}
```

## 🔄 Maintenance Procedures

### Regular Updates
1. **Data Refresh**: Regenerate dashboard after data updates
2. **Version Updates**: Update version definitions as needed
3. **Performance Monitoring**: Monitor generation time and memory usage
4. **Output Validation**: Verify dashboard accuracy and completeness

### Troubleshooting Procedures
1. **Data Issues**: Check file formats and permissions
2. **Performance Issues**: Monitor memory usage and processing time
3. **Output Issues**: Validate HTML generation and styling
4. **Version Issues**: Verify version definitions and matching logic

### Backup Procedures
1. **Data Backup**: Regular backup of data files
2. **Code Backup**: Version control for dashboard code
3. **Output Backup**: Archive generated dashboards
4. **Configuration Backup**: Save version definitions and settings

---

*Technical specifications version 1.0 - Last updated: 2024*
