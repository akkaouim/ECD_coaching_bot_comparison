# Version Comparison Dashboard - Usage Guide

## 🚀 Getting Started

### Prerequisites
Before using the Version Comparison Dashboard, ensure you have:

1. **Data Files Available**:
   - `data/consolidated/sessions/` - Contains session JSON files
   - `data/consolidated/messages/` - Contains message JSON files

2. **Python Environment**:
   - Python 3.8 or higher
   - Required packages installed (see main project requirements.txt)

3. **Data Structure**:
   - Session files: `session_*.json`
   - Message files: `messages_*.json`

### Quick Start

```bash
# 1. Navigate to the version comparison dashboard directory
cd version_comparison_dashboard

# 2. Generate the dashboard
python version_comparison_simple.py

# 3. View the dashboard
open version_comparison/version_comparison_dashboard.html
```

## 📊 Understanding the Dashboard

### Data Quality and Filtering

The dashboard applies comprehensive filtering to ensure accurate analysis:

- **Split Sessions Excluded**: Sessions with less than 3 participant messages (improved definition for better data quality)
- **Test Sessions Excluded**: Sessions with participant IDs ending in @dimagi.com (internal testing)
- **Consistent Filtering**: All tables, graphs, and metrics use the same exclusion criteria
- **Enhanced Rating Detection**: Comprehensive pattern matching improves rating extraction from 0.07% to 68% of sessions
- **Date Range Filtering**: Interactive date range filtering for Session Volume chart (client-side filtering)

### Dashboard Layout

The dashboard consists of six main sections:

1. **Header Section**
   - Dashboard title and navigation
   - Generation timestamp
   - Overview information
   - Global filters (date range, participant IDs, outlier exclusion, split/test session exclusion)

2. **Summary Metrics Table**
   - Core comparison metrics for each version
   - "Total (All Versions)" row showing aggregated totals across all versions
   - Summary Metrics - All Versions vs Refrigerator Examples table (exclusive to Summary tab)
   - Sortable and responsive table
   - Color-coded headers

3. **Method-Based Analysis Tables**
   - Refrigerator example rate by method and version (with "All Versions" column and "Total (All Methods)" row)
   - Median number of participant messages per session by method and version (with "All Versions" column and "Total (All Methods)" row, dynamic outlier filtering)
   - Median user words per session by method and version (with "All Versions" column and "Total (All Methods)" row, dynamic outlier filtering)
   - Average FLW score by method and version (with "All Versions" column and "Total (All Methods)" row, dynamic rating statistics)

4. **Session Volume Analysis**
   - Stacked bar chart showing session volume over time by coaching method and version
   - Aggregation options: day, week, month (default: week)
   - Date range filtering for interactive time-based analysis
   - Session count summary table by method and version (with "All Versions" column and "Total (All Methods)" row)

5. **Session Progression Analysis**
   - Interactive line graph with Chart.js
   - Dropdown to switch between view options
   - Outlier filtering checkbox for extreme sessions
   - Shows user verbosity progression across sessions

6. **Definitions Section**
   - Version definitions and criteria
   - Metric explanations
   - Technical details

### Key Metrics Explained

#### Sessions
- **What it measures**: Total number of bot-initiated interactions
- **Excludes**: Split sessions (user-initiated)
- **Interpretation**: Higher numbers indicate more usage

#### Annotated Sessions
- **What it measures**: Sessions with quality control tags
- **Includes**: Non-version tags (coaching_good, coaching_bad, etc.)
- **Excludes**: Sessions with only coaching method tags (coach_method_*)
- **Interpretation**: Higher numbers indicate more quality control activity

#### Refrigeration Examples
- **What it measures**: Percentage of annotated sessions with "refrigerator_example" tag
- **Calculation**: (Refrigerator sessions / Annotated sessions) × 100
- **Interpretation**: Higher percentages indicate more specific coaching scenarios

#### Median Human Words per Session
- **What it measures**: Median word count of user messages per session
- **Calculation**: Median of total user words across all sessions
- **Interpretation**: Higher numbers indicate more detailed user interactions

#### Average Session Rating
- **What it measures**: Mean user satisfaction rating (1-5 scale)
- **Source**: Extracted from user responses to rating questions
- **Interpretation**: Higher ratings indicate better user satisfaction

#### Refrigerator Example Rate by Method and Version
- **What it measures**: Percentage of annotated sessions with "refrigerator_example" tag, grouped by coaching method and bot version
- **Calculation**: (Refrigerator sessions / Annotated sessions) × 100 for each method-version combination
- **Method Detection**: Based on session tags (`coach_method_*`) or message content analysis
- **Interpretation**: Higher percentages indicate more specific coaching scenarios for that method and version
- **Aggregated Views**: 
  - "All Versions" column shows the average rate across all versions for each method
  - "Total (All Methods)" row shows the average rate across all methods for each version

#### Median Number of Participant Messages per Session by Method and Version
- **What it measures**: Median number of participant messages per session, grouped by coaching method and bot version
- **Calculation**: Median of total user message count across all sessions for each method-version combination
- **Interpretation**: Higher numbers indicate more interactive sessions for that method and version
- **Dynamic Filtering**: Table updates in real-time based on "Exclude outlier sessions" checkbox
- **Aggregated Views**: 
  - "All Versions" column shows the median across all versions for each method
  - "Total (All Methods)" row shows the median across all methods for each version

#### Median User Words per Session by Method and Version
- **What it measures**: Median word count of user messages per session, grouped by coaching method and bot version
- **Calculation**: Median of total user words across all sessions for each method-version combination
- **Outlier Filtering**: Optional checkbox to exclude sessions with >50 messages or >1000 words (updates table dynamically)
- **Session Numbering**: Chronological order per participant for line graph analysis
- **Interpretation**: Higher numbers indicate more detailed user interactions for that method and version
- **Aggregated Views**: 
  - "All Versions" column shows the median across all versions for each method
  - "Total (All Methods)" row shows the median across all methods for each version

#### Average FLW Score by Method and Version
- **What it measures**: Average session ratings (1-5 scale) grouped by coaching method and bot version
- **Calculation**: Average of user ratings for sessions ending with rating questions
- **Rating Scale**: 1 (not useful) to 5 (very useful)
- **Interpretation**: Higher ratings indicate better user satisfaction for that method and version
- **Aggregated Views**: 
  - "All Versions" column shows the average rating across all versions for each method
  - "Total (All Methods)" row shows the average rating across all methods for each version

#### Session Volume Analysis
- **What it measures**: Number of sessions over time, grouped by coaching method and bot version
- **Chart Type**: Stacked bar chart with methods stacked on top of each other
- **X-axis**: Time periods (day, week, or month based on aggregation level)
- **Y-axis**: Number of sessions
- **Aggregation Options**: Day, week (default), or month
- **Date Range Filtering**: Interactive date range filter for client-side filtering
- **Interpretation**: Shows session volume trends over time and distribution across methods and versions
- **Summary Table**: Session count by method and version with "All Versions" column and "Total (All Methods)" row

#### Session Progression Analysis
- **What it measures**: How user verbosity changes across successive sessions
- **X-axis**: Session number (1st, 2nd, 3rd, etc. session for each participant)
- **Y-axis**: Average number of words per session
- **View Options**: By method, by method and version, or by version only
- **Outlier Filtering**: Checkbox to exclude extreme sessions (>50 messages or >1000 words)
- **Data Limit**: First 22 sessions per participant
- **Interpretation**: Shows if users become more or less verbose over time

## 🔧 Advanced Usage

### Bot Categories

The dashboard compares five bot categories based on experiment IDs and version ranges:

- **Control bot**: Experiment ID: 1027993a-40c9-4484-a5fb-5c7e034dadcd (All versions)
- **Coaching bot V3**: Experiment ID: e2b4855f-8550-47ff-87d2-d92018676ff3 (All versions)
- **Coaching bot V4**: Experiment ID: b7621271-da98-459f-9f9b-f68335d09ad4 (Version 13 and above)
- **Coaching bot V5**: Experiment ID: 5d8be75e-03ff-4e3a-ab6a-e0aff6580986 (Version 1 to 4)
- **Coaching bot V6**: Experiment ID: 5d8be75e-03ff-4e3a-ab6a-e0aff6580986 (Version 5 and above)

### Customizing Bot Categories

Edit the `coaching_bot_versions` dictionary in `version_comparison_simple.py`:

```python
self.coaching_bot_versions = {
    "Your Custom Bot": {
        "experiment_id": ["your-experiment-id"],
        "version_range": (min_version, max_version)  # or None for all versions
    }
}
```

### Filtering by Date Range

To analyze specific time periods, modify the session loading logic:

```python
def load_sessions_from_files(self, start_date=None, end_date=None):
    # Add date filtering logic
    for session_file in session_files:
        session = json.load(f)
        session_date = datetime.fromisoformat(session['created_at'])
        if start_date and session_date < start_date:
            continue
        if end_date and session_date > end_date:
            continue
        # Process session...
```

### Adding Custom Metrics

Add new metrics by extending the `calculate_metrics_for_version` method:

```python
def calculate_metrics_for_version(self, version_name, sessions, messages_data):
    # Existing metrics...
    
    # Add custom metrics
    custom_metric = self.calculate_custom_metric(sessions, messages_data)
    
    return {
        # Existing metrics...
        'custom_metric': custom_metric
    }
```

## 📈 Interpreting Results

### Version Comparison Analysis

#### Session Volume
- **High session count**: Indicates popular/effective version
- **Low session count**: May indicate issues or limited deployment
- **Zero sessions**: Version not found in data or incorrect filtering

#### Quality Metrics
- **High annotation rate**: More quality control activity
- **High refrigeration examples**: More specific coaching scenarios
- **High word counts**: More detailed user interactions
- **High ratings**: Better user satisfaction

#### Trends to Look For
1. **Improvement over versions**: Later versions should show better metrics
2. **Consistency**: Similar metrics across versions indicate stable performance
3. **Anomalies**: Unusual patterns may indicate data issues or version problems

### Example Analysis

```
Coaching bot V3: 3,451 sessions, 15.2% refrigeration, 4.2 rating
Coaching bot V4: 2,563 sessions, 18.7% refrigeration, 4.4 rating
Coaching bot V6: 1,758 sessions, 22.1% refrigeration, 4.6 rating
```

**Interpretation**:
- V4 shows improvement in refrigeration examples over V3
- V6 shows the highest refrigeration examples and ratings
- V5 has no sessions (may not be deployed or filtered out)

## 🛠️ Troubleshooting

### Common Issues

#### "No sessions found"
- Check that `data/consolidated/sessions/` exists
- Verify session files are in correct format
- Check experiment name matching in version definitions

#### "No messages found"
- Check that `data/consolidated/messages/` exists
- Verify message files correspond to session files
- Check file naming convention

#### "Zero sessions for version"
- Verify experiment name matching
- Check version range constraints
- Review session data for correct experiment names

#### Performance Issues
- Use test mode for large datasets
- Consider date range filtering
- Check available system memory

### Debug Mode

Add debug output to understand data processing:

```python
def load_sessions_from_files(self):
    # Add debug output
    print(f"Looking for experiments: {list(relevant_experiments)}")
    for session_file in session_files[:5]:  # Check first 5 files
        with open(session_file, 'r') as f:
            session = json.load(f)
            print(f"Session experiment: {session.get('experiment', {}).get('name')}")
```

## 📊 Exporting Data

### Export Metrics to CSV

Add CSV export functionality:

```python
import csv

def export_metrics_to_csv(self, metrics, filename):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=metrics[0].keys())
        writer.writeheader()
        writer.writerows(metrics)
```

### Export Raw Data

Export session and message data for external analysis:

```python
def export_raw_data(self, sessions, messages_data, filename):
    export_data = {
        'sessions': sessions,
        'messages': messages_data,
        'generated_at': datetime.now().isoformat()
    }
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=2)
```

## 🔄 Automation

### Scheduled Generation

Create a script to generate dashboards automatically:

```bash
#!/bin/bash
# generate_version_dashboard.sh

cd /path/to/version_comparison_dashboard
python version_comparison_simple.py

# Copy to web server
cp version_comparison/version_comparison_dashboard.html /var/www/html/

# Send notification
echo "Version comparison dashboard updated" | mail -s "Dashboard Update" admin@example.com
```

### Integration with Main Dashboard

Link the version comparison dashboard from the main dashboard:

```html
<!-- Add to main dashboard -->
<a href="../version_comparison_dashboard/version_comparison/version_comparison_dashboard.html" 
   class="btn btn-primary">
   View Version Comparison
</a>
```

## 📝 Best Practices

### Data Management
- Keep data files organized in `data/consolidated/`
- Regularly update session and message data
- Backup data before major changes

### Dashboard Maintenance
- Regenerate dashboard after data updates
- Monitor dashboard performance with large datasets
- Keep version definitions up to date

### Analysis Workflow
1. Generate dashboard with latest data
2. Review metrics for each version
3. Identify trends and anomalies
4. Document findings and recommendations
5. Share results with stakeholders

---

*For technical support, refer to TECHNICAL_SPECS.md and TROUBLESHOOTING.md*
