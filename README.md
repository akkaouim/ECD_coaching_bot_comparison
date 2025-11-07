# Version Comparison Dashboard

A web-based dashboard for comparing different bot categories in the OpenChatStudio (OCS) system, including Control bot and Coaching bot versions.

## Features

- **Summary Metrics**: Overview of sessions, annotations, and ratings by bot version with "Total (All Versions)" aggregation row
- **Performance Analysis**: Refrigerator example rates and FLW scores by method and version with "All Versions" columns and "Total (All Methods)" rows
- **Session Volume Analysis**: 
  - Stacked bar chart showing session volume over time by coaching method and version
  - Aggregation options: day, week, month (default: week)
  - Date range filtering for interactive analysis
  - Summary table with session counts by method and version
- **User Engagement**: 
  - Median user words per session with progression analysis
  - Median participant messages per session by method and version
  - Outlier filtering for extreme sessions (>50 messages or >1000 words)
  - Dynamic table updates based on outlier filter
- **Interactive Charts**: Line graphs showing session progression over time with outlier filtering
- **Method Detection**: Automatic detection of coaching methods (Scenario, Microlearning, etc.)
- **Enhanced Rating Detection**: Comprehensive pattern matching for 68% rating extraction (vs. 0.07% basic)
- **Data Quality Filtering**: Excludes split sessions (less than 3 participant messages) and test sessions for accurate analysis
- **Dynamic Statistics**: Real-time rating coverage metrics displayed as footnotes
- **Outlier Detection**: Advanced filtering to exclude training sessions and extreme user interactions
- **Aggregated Views**: "All Versions" columns and "Total" rows across all method-based tables for comprehensive cross-version and cross-method analysis

## Quick Start

1. **Generate Dashboard**:
```bash
python version_comparison_simple.py
   ```

2. **View Dashboard**:
   - Open `output/version_comparison/version_comparison_dashboard.html` in your browser
   - Or serve via HTTP: `cd output/version_comparison && python3 -m http.server 8002`

## Bot Categories

The dashboard compares five bot categories:

- **Control bot**: Experiment ID: 1027993a-40c9-4484-a5fb-5c7e034dadcd (All versions)
- **Coaching bot V3**: Experiment ID: e2b4855f-8550-47ff-87d2-d92018676ff3 (All versions)
- **Coaching bot V4**: Experiment ID: b7621271-da98-459f-9f9b-f68335d09ad4 (Version 13 and above)
- **Coaching bot V5**: Experiment ID: 5d8be75e-03ff-4e3a-ab6a-e0aff6580986 (Version 1 to 4)
- **Coaching bot V6**: Experiment ID: 5d8be75e-03ff-4e3a-ab6a-e0aff6580986 (Version 5 and above)

## Data Requirements

The dashboard expects data files in the following structure:
```
../data/consolidated/sessions/session_*.json
../data/consolidated/messages/message_*.json
```

## Dashboard Sections

### Summary Tab
- Summary metrics by version (sessions, annotations, ratings)
- Summary Metrics - All Versions vs Refrigerator Examples table (aggregated comparison)

### Performance Tab  
- Refrigerator example rate by method and version
- Average FLW score by method and version

### User Engagement Tab
- Median number of participant messages per session by method and version (with "All Versions" column and "Total (All Methods)" row)
- Median user words per session by method and version (with outlier filtering, "All Versions" column, and "Total (All Methods)" row)
- Session progression analysis with interactive line graphs and outlier filtering

### Session Volume Tab
- Stacked bar chart showing volume of sessions per coach version over time
- Aggregation options: day, week, month (default: week)
- Date range filtering for interactive time-based analysis
- Session count summary table by method and version (with "All Versions" column and "Total (All Methods)" row)

### Definitions Tab
- Version definitions and experiment ID mappings
- Coaching method detection criteria
- Metric calculation explanations

## Data Quality and Filtering

The dashboard applies comprehensive filtering to ensure data quality:

- **Split Sessions Excluded**: Sessions with less than 3 participant messages (improved definition for better data quality)
- **Test Sessions Excluded**: Sessions with participant IDs ending in @dimagi.com (internal testing)
- **Outlier Sessions Filtered**: Optional filtering of extreme sessions (>50 messages or >1000 words)
- **Consistent Filtering**: All tables, graphs, and metrics use the same exclusion criteria
- **Enhanced Rating Detection**: Comprehensive pattern matching improves rating extraction from 0.07% to 68% of sessions
- **Date Range Filtering**: Interactive date range filtering for Session Volume chart (client-side filtering)

### Outlier Detection

The dashboard includes advanced outlier detection to identify and optionally exclude extreme sessions:

- **Message Count Threshold**: Sessions with >50 participant messages
- **Word Count Threshold**: Sessions with >1000 total participant words
- **Training Session Detection**: Identifies intensive practice/training sessions
- **Interactive Filtering**: Checkboxes allow real-time toggling between filtered and unfiltered views

## Version Detection

The dashboard identifies bot versions based on:
- **Experiment IDs**: Specific experiment identifiers
- **Version Tags**: Extracted from the last message in each session
- **Version Ranges**: Numeric ranges for different bot versions

## Coaching Methods

Methods are detected through:
1. **Session Tags**: `coach_method_*` tags
2. **Message Tags**: Tags in assistant messages
3. **Content Analysis**: Keyword matching in message content

## Requirements

- Python 3.7+
- Required packages listed in `requirements.txt`

## Deployment

This repository is configured for GitHub Pages deployment. The dashboard will be automatically available at:
`https://[username].github.io/[repository-name]/output/version_comparison/version_comparison_dashboard.html`