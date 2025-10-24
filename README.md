# Version Comparison Dashboard

A web-based dashboard for comparing different versions of coaching bots in the OpenChatStudio (OCS) system.

## Features

- **Summary Metrics**: Overview of sessions, annotations, and ratings by bot version
- **Performance Analysis**: Refrigerator example rates and FLW scores by method and version
- **User Engagement**: Median user words per session with progression analysis
- **Interactive Charts**: Line graphs showing session progression over time
- **Method Detection**: Automatic detection of coaching methods (Scenario, Microlearning, etc.)
- **Enhanced Rating Detection**: Comprehensive pattern matching for 68% rating extraction (vs. 0.07% basic)
- **Data Quality Filtering**: Excludes split sessions and test sessions for accurate analysis
- **Dynamic Statistics**: Real-time rating coverage metrics displayed as footnotes

## Quick Start

1. **Generate Dashboard**:
   ```bash
   python version_comparison_simple.py
   ```

2. **View Dashboard**:
   - Open `output/version_comparison/version_comparison_dashboard.html` in your browser
   - Or serve via HTTP: `cd output/version_comparison && python3 -m http.server 8002`

## Data Requirements

The dashboard expects data files in the following structure:
```
../data/consolidated/sessions/session_*.json
../data/consolidated/messages/message_*.json
```

## Dashboard Sections

### Summary Tab
- Summary metrics by version (sessions, annotations, ratings)

### Performance Tab  
- Refrigerator example rate by method and version
- Average FLW score by method and version

### User Engagement Tab
- Median user words per session by method and version
- Session progression analysis with interactive line graphs

### Definitions Tab
- Version definitions and experiment ID mappings
- Coaching method detection criteria
- Metric calculation explanations

## Data Quality and Filtering

The dashboard applies comprehensive filtering to ensure data quality:

- **Split Sessions Excluded**: Sessions with no participant messages (bot-only interactions)
- **Test Sessions Excluded**: Sessions with participant IDs ending in @dimagi.com (internal testing)
- **Consistent Filtering**: All tables, graphs, and metrics use the same exclusion criteria
- **Enhanced Rating Detection**: Comprehensive pattern matching improves rating extraction from 0.07% to 68% of sessions

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