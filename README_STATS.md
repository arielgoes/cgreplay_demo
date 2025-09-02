# Online Statistics Dashboard Setup

This guide explains how to set up and run the online statistics dashboard for your video quality evaluation system.

## Overview

The online statistics system consists of:
- **Flask Backend** (`app.py`) - Serves API endpoints with real-time data from Google Sheets
- **Statistics Dashboard** (`stats.html`) - Interactive web interface with charts and metrics
- **Integration** - Button added to evaluation completion page

## Setup Instructions

### 1. Install Dependencies

```bash
pip install flask flask-cors
# Other dependencies should already be installed from requirements.txt
```

### 2. Google Sheets Credentials

Ensure you have `credentials.json` in the project directory for Google Sheets API access.

### 3. Start the Server

```bash
python app.py
```

The server will start on `http://localhost:5000`

## Usage

### For Users
1. Complete video evaluation as normal
2. After completion, click "📊 View Statistics Dashboard" button
3. View real-time statistics and insights

### Direct Access
- Main evaluation: `http://localhost:5000/`
- Statistics dashboard: `http://localhost:5000/stats`

## API Endpoints

- `GET /api/stats/overview` - Overall statistics summary
- `GET /api/stats/confusion_matrix` - Confusion matrix data
- `GET /api/stats/user_accuracy` - User performance distribution
- `GET /api/health` - Health check

## Features

### Statistics Dashboard Includes:
- **Overview Cards**: Total evaluations, participants, accuracy, data freshness
- **Accuracy by Scenario**: Bar chart showing performance by video type
- **Confusion Matrix**: Heatmap of actual vs perceived reality
- **User Distribution**: Histogram of user performance with metrics
- **Real-time Insights**: Automated analysis and recommendations

### Key Benefits:
- **Real-time Data**: Fetches fresh data from Google Sheets
- **Caching**: 5-minute cache to reduce API calls
- **Responsive Design**: Works on desktop and mobile
- **Dark Theme**: Matches evaluation interface
- **Interactive Charts**: Hover for details, zoom, etc.

## Troubleshooting

### Common Issues:
1. **"Error Loading Data"**: Check Google Sheets credentials and permissions
2. **Server won't start**: Ensure Flask dependencies are installed
3. **Charts not loading**: Check browser console for JavaScript errors

### Data Requirements:
- Google Sheet must have columns matching the expected format
- At least one evaluation record for statistics to display
- Service account must have read access to the sheet

## Customization

### Modify Chart Colors:
Edit CSS variables in `stats.html`:
```css
:root {
    --primary-color: #bb86fc;
    --secondary-color: #03dac6;
    /* ... */
}
```

### Add New Metrics:
1. Add API endpoint in `app.py`
2. Create chart function in `stats.html`
3. Call from `loadStatistics()`

### Change Cache Duration:
Modify `CACHE_DURATION` in `app.py` (default: 300 seconds)
