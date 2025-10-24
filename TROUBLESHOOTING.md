# Version Comparison Dashboard - Troubleshooting Guide

## 🚨 Common Issues and Solutions

### Data Loading Issues

#### Issue: "No sessions found"
**Symptoms:**
- Dashboard shows "No sessions found!" error
- Empty metrics table
- No data processing output

**Causes:**
- Missing data directory
- Incorrect file paths
- No matching experiment names
- Corrupted session files

**Solutions:**
```bash
# 1. Check data directory structure
ls -la data/consolidated/sessions/
ls -la data/consolidated/messages/

# 2. Verify file permissions
chmod -R 755 data/consolidated/

# 3. Check experiment names in version definitions
grep -r "experiment_name" version_comparison_simple.py

# 4. Test with sample session file
python -c "
import json
with open('data/consolidated/sessions/session_*.json', 'r') as f:
    session = json.load(f)
    print('Experiment:', session.get('experiment', {}).get('name'))
"
```

#### Issue: "No messages found"
**Symptoms:**
- Warning message about missing messages
- Empty message data in metrics
- Incomplete calculations

**Causes:**
- Missing messages directory
- Session ID mismatch between sessions and messages
- Corrupted message files

**Solutions:**
```bash
# 1. Check messages directory
ls -la data/consolidated/messages/

# 2. Verify session ID matching
python -c "
import os
sessions = [f.replace('session_', '').replace('.json', '') for f in os.listdir('data/consolidated/sessions/') if f.startswith('session_')]
messages = [f.replace('messages_', '').replace('.json', '') for f in os.listdir('data/consolidated/messages/') if f.startswith('messages_')]
print('Sessions without messages:', set(sessions) - set(messages))
print('Messages without sessions:', set(messages) - set(sessions))
"

# 3. Check message file format
python -c "
import json
with open('data/consolidated/messages/messages_*.json', 'r') as f:
    data = json.load(f)
    print('Has messages key:', 'messages' in data)
    print('Message count:', len(data.get('messages', [])))
"
```

### Performance Issues

#### Issue: Slow Data Loading
**Symptoms:**
- Long loading times (>30 seconds)
- High memory usage
- System becomes unresponsive

**Causes:**
- Large dataset size
- Inefficient file I/O
- Memory leaks
- System resource constraints

**Solutions:**
```python
# 1. Add progress tracking
def load_sessions_from_files(self):
    session_files = list(sessions_dir.glob("session_*.json"))
    print(f"Processing {len(session_files)} files...")
    
    for i, session_file in enumerate(session_files):
        if i % 1000 == 0:
            print(f"Processed {i}/{len(session_files)} files")
        # Process file...

# 2. Implement batch processing
def process_sessions_batch(self, sessions, batch_size=1000):
    for i in range(0, len(sessions), batch_size):
        batch = sessions[i:i + batch_size]
        yield self.process_batch(batch)

# 3. Add memory monitoring
import psutil
def monitor_memory(self):
    memory_usage = psutil.virtual_memory()
    print(f"Memory usage: {memory_usage.percent}%")
    if memory_usage.percent > 80:
        print("Warning: High memory usage")
```

#### Issue: Out of Memory
**Symptoms:**
- Python crashes with MemoryError
- System becomes unresponsive
- Process killed by system

**Causes:**
- Dataset too large for available memory
- Memory leaks in processing
- Inefficient data structures

**Solutions:**
```python
# 1. Implement streaming processing
def process_sessions_streaming(self):
    for session_file in sessions_dir.glob("session_*.json"):
        with open(session_file, 'r') as f:
            session = json.load(f)
            # Process immediately, don't store
            yield self.process_session(session)

# 2. Use generators instead of lists
def load_sessions_generator(self):
    for session_file in sessions_dir.glob("session_*.json"):
        yield self.load_session(session_file)

# 3. Clear unused variables
def process_large_dataset(self):
    sessions = self.load_sessions_from_files()
    # Process sessions
    del sessions  # Free memory
    gc.collect()  # Force garbage collection
```

### Version Matching Issues

#### Issue: "Zero sessions for version"
**Symptoms:**
- Version shows 0 sessions
- No data in metrics table
- Incorrect version filtering

**Causes:**
- Experiment name mismatch
- Version range constraints too restrictive
- Data format issues

**Solutions:**
```python
# 1. Debug version matching
def debug_version_matching(self, session, version_config):
    print(f"Session experiment: {session.get('experiment', {}).get('name')}")
    print(f"Version experiment: {version_config['experiment_name']}")
    print(f"Session version: {session.get('experiment', {}).get('version_number')}")
    print(f"Version range: {version_config.get('version_range')}")
    
    # Test matching logic
    experiment_match = version_config['experiment_name'].lower() in session.get('experiment', {}).get('name', '').lower()
    print(f"Experiment match: {experiment_match}")
    
    return experiment_match

# 2. Check experiment names in data
def analyze_experiment_names(self):
    experiments = set()
    for session_file in sessions_dir.glob("session_*.json"):
        with open(session_file, 'r') as f:
            session = json.load(f)
            experiments.add(session.get('experiment', {}).get('name'))
    
    print("Found experiments:")
    for exp in sorted(experiments):
        print(f"  - {exp}")

# 3. Relax version constraints
def test_version_ranges(self):
    for version_name, config in self.coaching_bot_versions.items():
        print(f"\n{version_name}:")
        print(f"  Experiment: {config['experiment_name']}")
        print(f"  Range: {config.get('version_range', 'All versions')}")
```

### Metric Calculation Issues

#### Issue: Incorrect Metrics
**Symptoms:**
- Metrics don't match expected values
- Zero values for all metrics
- Inconsistent calculations

**Causes:**
- Data format issues
- Algorithm bugs
- Missing data fields
- Calculation errors

**Solutions:**
```python
# 1. Add metric validation
def validate_metrics(self, metrics):
    for metric in metrics:
        assert metric['total_sessions'] >= 0, "Negative session count"
        assert 0 <= metric['refrigerator_examples_percent'] <= 100, "Invalid percentage"
        assert 0 <= metric['average_session_rating'] <= 5, "Invalid rating"
        print(f"✓ {metric['version_name']} metrics validated")

# 2. Debug metric calculations
def debug_metric_calculation(self, sessions, messages_data):
    print(f"Total sessions: {len(sessions)}")
    
    # Debug annotation detection
    annotated_count = 0
    for session in sessions:
        if self.is_annotated_session(session, messages_data.get(session['id'], [])):
            annotated_count += 1
    print(f"Annotated sessions: {annotated_count}")
    
    # Debug rating extraction
    ratings = []
    for session in sessions:
        rating = self.extract_session_rating(session, messages_data.get(session['id'], []))
        if rating:
            ratings.append(rating)
    print(f"Found ratings: {len(ratings)}")
    print(f"Average rating: {sum(ratings)/len(ratings) if ratings else 0}")

# 3. Test with known data
def test_with_sample_data(self):
    sample_session = {
        "id": "test-session",
        "experiment": {"name": "ECD Coach V6", "version_number": 5},
        "tags": ["coaching_good", "refrigerator_example"]
    }
    sample_messages = [
        {"role": "assistant", "content": "Rate it from 1 to 5"},
        {"role": "user", "content": "4"}
    ]
    
    # Test calculations
    assert self.is_annotated_session(sample_session, sample_messages) == True
    assert self.has_refrigerator_example_tag(sample_session, sample_messages) == True
    assert self.extract_session_rating(sample_session, sample_messages) == 4.0
```

### HTML Generation Issues

#### Issue: Dashboard Not Displaying
**Symptoms:**
- Blank page in browser
- CSS not loading
- JavaScript errors
- Broken layout

**Causes:**
- Missing CSS/JS resources
- HTML generation errors
- Browser compatibility issues
- File path problems

**Solutions:**
```python
# 1. Validate HTML output
def validate_html(self, html_content):
    # Check for required elements
    assert '<html' in html_content, "Missing HTML tag"
    assert '<head>' in html_content, "Missing head section"
    assert '<body>' in html_content, "Missing body section"
    assert 'bootstrap' in html_content, "Missing Bootstrap CSS"
    assert 'table' in html_content, "Missing data table"
    
    # Check for data
    assert 'Coaching bot' in html_content, "Missing version data"
    print("✓ HTML validation passed")

# 2. Test HTML generation
def test_html_generation(self):
    # Generate with sample data
    sample_metrics = [{
        'version_name': 'Test Version',
        'total_sessions': 100,
        'annotated_sessions': 50,
        'refrigerator_examples_percent': 25.0,
        'median_human_words_per_session': 15.0,
        'average_session_rating': 4.0
    }]
    
    html = self.generate_dashboard_html(sample_metrics)
    assert len(html) > 1000, "HTML too short"
    assert 'Test Version' in html, "Missing test data"
    print("✓ HTML generation test passed")

# 3. Check file permissions
def check_output_permissions(self):
    output_file = self.output_dir / "version_comparison_dashboard.html"
    if output_file.exists():
        print(f"Output file exists: {output_file}")
        print(f"File size: {output_file.stat().st_size} bytes")
        print(f"Readable: {os.access(output_file, os.R_OK)}")
        print(f"Writable: {os.access(output_file, os.W_OK)}")
    else:
        print("Output file not found")
```

### Browser Compatibility Issues

#### Issue: Dashboard Not Loading in Browser
**Symptoms:**
- Blank page
- CSS not applied
- JavaScript errors
- Layout broken

**Solutions:**
```bash
# 1. Check file permissions
ls -la version_comparison/version_comparison_dashboard.html

# 2. Test with different browsers
# Chrome, Firefox, Safari, Edge

# 3. Use HTTP server instead of file://
cd version_comparison
python3 -m http.server 8002
# Open: http://localhost:8002/version_comparison_dashboard.html

# 4. Check browser console for errors
# F12 → Console tab
```

## 🔧 Debugging Tools

### Debug Mode
```python
# Add debug mode to dashboard
class SimpleVersionComparisonDashboard:
    def __init__(self, debug=False):
        self.debug = debug
    
    def debug_print(self, message):
        if self.debug:
            print(f"DEBUG: {message}")
    
    def load_sessions_from_files(self):
        self.debug_print("Loading sessions...")
        # Add debug output throughout
```

### Logging
```python
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dashboard.log'),
        logging.StreamHandler()
    ]
)

def load_sessions_from_files(self):
    logging.info("Starting session loading")
    # Add logging throughout
```

### Performance Profiling
```python
import cProfile
import pstats

def profile_dashboard_generation(self):
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run dashboard generation
    self.generate_dashboard()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 functions
```

## 📊 Diagnostic Commands

### Data Validation
```bash
# Check data directory structure
find data/consolidated -name "*.json" | wc -l

# Check file sizes
du -sh data/consolidated/sessions/
du -sh data/consolidated/messages/

# Check file permissions
ls -la data/consolidated/sessions/ | head -5
ls -la data/consolidated/messages/ | head -5
```

### Performance Monitoring
```bash
# Monitor memory usage
python -c "
import psutil
print(f'Memory: {psutil.virtual_memory().percent}%')
print(f'CPU: {psutil.cpu_percent()}%')
"

# Monitor disk usage
df -h

# Check system resources
top -l 1 | grep "PhysMem"
```

### Network Testing
```bash
# Test CDN resources
curl -I https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css
curl -I https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css
```

## 🆘 Emergency Procedures

### Data Recovery
```bash
# Backup current data
cp -r data/consolidated data/consolidated_backup_$(date +%Y%m%d_%H%M%S)

# Restore from backup
cp -r data/consolidated_backup_YYYYMMDD_HHMMSS data/consolidated
```

### Dashboard Recovery
```bash
# Regenerate dashboard
python version_comparison_simple.py

# Check output
ls -la version_comparison/version_comparison_dashboard.html

# Test in browser
open version_comparison/version_comparison_dashboard.html
```

### System Recovery
```bash
# Clear Python cache
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete

# Reset environment
deactivate
source venv/bin/activate
pip install -r requirements.txt
```

## 📞 Support Contacts

### Internal Support
- **Technical Issues**: Development team
- **Data Issues**: Data management team
- **Performance Issues**: System administration

### External Resources
- **Bootstrap Documentation**: https://getbootstrap.com/docs/
- **Python Documentation**: https://docs.python.org/
- **JSON Schema**: https://json-schema.org/

### Escalation Procedures
1. **Level 1**: Check this troubleshooting guide
2. **Level 2**: Contact development team
3. **Level 3**: Escalate to system administration
4. **Level 4**: Contact external support if needed

---

*Troubleshooting guide version 1.0 - Last updated: 2024*
