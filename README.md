# CGSynth Video Quality Evaluation Tool

A web-based tool for conducting video quality evaluation studies, specifically designed for comparing different video processing techniques.

## Overview

This project provides a complete solution for conducting video quality evaluation studies where participants compare pairs of videos and rate their quality. The system ensures consistent and reproducible results by using deterministic algorithms for video pair selection based on user IDs.

The project also includes tools for analyzing the collected data, extracting insights from the Google Sheet responses, and generating visualizations to compare when users correctly identified synthetic videos versus when they didn't. The analysis pipeline can be run with a single command, making it easy to generate insights from the collected data.

## Features

- **User Management**: Each participant gets a unique, persistent user ID
- **Deterministic Pairing**: Reproducible video pair selection using seeded randomization
- **Responsive Design**: Works on both desktop and mobile devices
- **Data Collection**: Records user ratings and additional feedback
- **Offline-First**: Works without an internet connection after initial load
- **Version Control**: Tracks video list versions and hashes for data integrity
- **Data Analysis**: Comprehensive analysis tools with visualization generation
- **Reproducibility**: Ability to retrieve exact video pairs shown to specific users
- **Sample Data Generation**: Tools to generate sample data for testing without accessing the Google Sheet

## Qoe Evaluation website

The Qoe Evaluation website is a web-based tool for conducting video quality evaluation studies, specifically designed for comparing different video processing techniques.

* **Website:** https://cgreplay-demo.onrender.com/

* **Backup website (Static without dashboard):** https://arielgoes.github.io/cgreplay_demo/

## Project Structure

### Website Components
- `index.html` - Main web interface for the evaluation tool
- `generate_video_list.py` - Script to generate a list of videos with versioning
- `retrieve_videos_from_user_hash_id.py` - Tool to reproduce exact video pairs shown to a user
- `video_list.json` - Configuration file listing all available videos
- `videos/` - Directory containing video files for evaluation
- `AppsScript/` - Google Apps Script for data collection (if using Google Sheets)

### Analysis Tools
- `download_qoe_data.py` - Downloads the data from the Google Sheet and saves it as a CSV file
- `analyze_qoe_data.py` - Analyzes the data and generates visualizations for accuracy metrics
- `generate_sample_data.py` - Generates sample data for testing the analysis without accessing the Google Sheet
- `run_analysis.sh` - Shell script to run the entire analysis pipeline in one command
- `requirements.txt` - List of Python package dependencies for the analysis tools
- `visualizations/` - Directory containing generated visualization outputs:
  - `overall_accuracy.png` - Bar chart showing the proportion of correct vs. incorrect guesses
  - `accuracy_by_type.png` - Bar chart showing the accuracy for different video type combinations
  - `confusion_matrix.png` - Heatmap showing the relationship between reality and user guesses
  - `user_accuracy_distribution.png` - Histogram showing the distribution of accuracy across users

## Getting Started

### Prerequisites

- Python 3.6+
- Modern web browser (Chrome, Firefox, Safari, or Edge)
- (Optional) Google account if using Google Sheets for data collection

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/arielgoes/cgreplay_demo.git
   cd cgreplay_demo
   ```

2. Place your video files in the `videos/` directory

3. Generate the video list:
   ```bash
   python3 generate_video_list.py
   ```
   This will create/update `video_list.json` with all videos found in the `videos/` directory.

### Running the Application

1. Start a local web server. For example, using Python's built-in server:
   ```bash
   python3 -m http.server 8000
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:8000
   ```

## Usage

### For Participants

1. Open the evaluation tool in your web browser
2. You'll be assigned a unique user ID (or can enter an existing one)
3. Follow the on-screen instructions to evaluate video pairs
4. For each pair, rate the quality difference between the two videos
5. Complete any additional questions
6. Submit your evaluation when finished

### For Researchers

To retrieve the exact video pairs shown to a specific user:

```bash
python3 retrieve_videos_from_user_hash_id.py USER_ID
```

This will output the list of video pairs that were shown to that user, allowing for result verification and analysis.

Additional options for the retrieval script:
```bash
# Output in CSV format
python3 retrieve_videos_from_user_hash_id.py USER_ID --csv

# Save output to a file
python3 retrieve_videos_from_user_hash_id.py USER_ID --save user_pairs.csv

# Generate pairs algorithmically instead of using CSV data
python3 retrieve_videos_from_user_hash_id.py USER_ID --generate
```

The script first attempts to load pairs directly from the QoE data CSV file. If no data is found or the `--generate` flag is used, it falls back to algorithmic generation using the same deterministic algorithm as the frontend.

## Data Collection

By default, the application logs evaluation data to the browser's console. To enable Google Sheets integration:

1. Create a new Google Sheet
2. Go to Extensions > Apps Script
3. Copy the contents of `AppsScript/webserver_connection_cgreplay_yes.gs` into the script editor
4. Deploy the script as a web app
5. Update the `SCRIPT_URL` in `index.html` with your web app URL

## Customization

### Adding New Videos

1. Place new video files in the `videos/` directory
2. Run `generate_video_list.py` to update the video list
3. The new videos will be included in the next evaluation session

### Modifying Questions

Edit the HTML form in `index.html` to add, remove, or modify the evaluation questions.

## Troubleshooting

- **Videos not loading**: Check the browser's developer console for errors
- **Data not submitting**: Verify the Google Apps Script is properly deployed and the URL is correct
- **Inconsistent pairs**: Ensure the same video list version is used for both evaluation and retrieval

## License

[Specify your license here]

## Acknowledgments

- Built with standard web technologies (HTML, CSS, JavaScript)
- Uses a custom implementation of a seeded random number generator for reproducibility
- Designed for academic and research use in video quality assessment studies

## Data Analysis Pipeline

After users complete video evaluations through the web interface, their responses are automatically collected in a Google Sheet. The project includes a comprehensive analysis pipeline to process this data and generate insights.

### Pipeline Overview

The complete data analysis pipeline consists of:

1. **Data Collection** → Users submit evaluations via web interface → Data stored in Google Sheet
2. **Data Download** → `download_qoe_data.py` retrieves data from Google Sheet as CSV
3. **Data Analysis** → `analyze_qoe_data.py` processes responses and calculates accuracy metrics
4. **Visualization Generation** → Creates 4 types of charts showing user performance patterns
5. **Results Interpretation** → Generated visualizations reveal insights about synthetic video detection

### Prerequisites

Before running the analysis scripts, you need to have Python 3.6+ installed. You can install all required packages using:

```bash
pip install -r requirements.txt
```

This will install:
- pandas
- matplotlib
- seaborn
- numpy
- requests
- google-api-python-client
- google-auth-httplib2
- google-auth-oauthlib

### Running the Analysis

#### Option 1: Run the Complete Pipeline (Recommended)

The easiest way to run the analysis is to use the provided shell script:

```bash
./run_analysis.sh
```

This automated pipeline will:
1. Check for required dependencies and install them if needed
2. Download the data from the Google Sheet using `download_qoe_data.py`
3. Analyze the data and generate visualizations using `analyze_qoe_data.py`
4. Display a summary of the generated visualizations

#### Option 2: Run Steps Individually

If you prefer to run the steps individually:

1. **Download the data**:
   ```bash
   python3 download_qoe_data.py
   ```
   - Downloads data from Google Sheet as `qoe_data.csv`
   - Uses direct CSV export URL for reliable data retrieval

2. **Analyze the data**:
   ```bash
   python3 analyze_qoe_data.py --csv qoe_data.csv
   ```
   - Processes user responses and calculates accuracy metrics
   - Generates visualizations in `visualizations/` directory

#### Option 3: Using Sample Data

If you want to test the analysis without accessing the Google Sheet, you can generate sample data:

```bash
python3 generate_sample_data.py
python3 analyze_qoe_data.py --csv sample_qoe_data.csv
```

### Generated Visualizations

The analysis generates the following visualizations in the `visualizations/` directory:

1. **`overall_accuracy.png`**: Bar chart showing the proportion of correct vs. incorrect synthetic video identifications
2. **`accuracy_by_type.png`**: Bar chart showing accuracy for different video type combinations (real vs real, synthetic vs synthetic, etc.)
3. **`confusion_matrix.png`**: Heatmap showing the relationship between actual video reality and user guesses
4. **`user_accuracy_distribution.png`**: Histogram showing how accuracy varies across different users

### How the Analysis Works

The analysis pipeline processes user responses through these steps:

1. **Video Classification**: Automatically classifies videos as synthetic or real based on filenames:
   - Videos with "interpolated" → synthetic
   - Videos with "original" → real
   - Videos with "degrad" → synthetic
   - Other videos → default to real

2. **Reality Determination**: For each video pair, determines the ground truth:
   - Both real → "Both are Real"
   - Both synthetic → "None are Real"
   - One real, one synthetic → "Video X is Real"

3. **Accuracy Calculation**: Compares user guesses against ground truth to calculate:
   - Overall accuracy (proportion of correct identifications)
   - Accuracy by video type combinations
   - Per-user accuracy distribution
   - Confusion matrix patterns

4. **Insight Generation**: Creates visualizations to reveal patterns in:
   - Which video types are hardest to identify
   - User performance variations
   - Common misidentification patterns

### Individual User Analysis

To analyze specific user performance, use the retrieval script:

```bash
python3 retrieve_videos_from_user_hash_id.py USER_ID --csv --save user_pairs.csv
```

This allows researchers to:
- See exactly which video pairs a user evaluated
- Reproduce their evaluation session
- Analyze individual performance patterns



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
