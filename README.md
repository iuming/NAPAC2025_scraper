# NAPAC2025 Conference Web Scraper

**Author: Ming Liu**  
**Last Updated: November 3, 2025**

## Overview
This web scraper extracts all abstracts and papers from the NAPAC2025 conference proceedings hosted at https://meow.elettra.eu/97/. The scraper creates folders organized by session categories and downloads paper information in multiple formats (JSON, CSV, TXT).

**Note**: This scraper was originally designed for SRF2021 and has been adapted for NAPAC2025. The page structure uses dynamic JavaScript loading which has been accommodated in the parsing logic.

## File Description
- `scraper.py` - Main scraper script adapted for NAPAC2025
- `analyze_results.py` - Results analysis and summary generator
- `requirements.txt` - Python dependencies list
- `README.md` - This documentation
- `index.html` - Project homepage with statistics and links
- `data-explorer.html` - Interactive web interface for browsing papers

## Requirements
- Python 3.7+
- Stable internet connection

## Installation

1. Ensure Python 3.7 or higher is installed
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

## Usage

### Run the main scraper
```powershell
python scraper.py
```

The scraper will:
1. First run in test mode (scraping the first 3 sessions)
2. Prompt you whether to continue with full scraping
3. Generate comprehensive output files in `NAPAC2025_Data/`

### Analyze results
```powershell
python analyze_results.py
```

## Output Directory Structure

```
NAPAC2025_Data/
├── Sessions/                    # Session-categorized paper data
│   ├── SUTD - Sunday Tutorial/
│   │   ├── papers_data.json     # Detailed JSON data
│   │   ├── papers_data.csv      # CSV data (Excel compatible)
│   │   └── papers_summary.txt   # Human-readable text summary
│   ├── SUP - Sunday Student Poster Session/
│   └── ...
├── Presentations/               # Presentation files organized by session
├── Papers/                      # Paper files organized by session
├── Posters/                     # Poster files organized by session
├── NAPAC2025_Complete_Index.json  # Master data index (JSON format)
├── NAPAC2025_All_Papers.csv      # Complete papers CSV table
├── NAPAC2025_Final_Report.txt    # Final scraping report
└── Debug/                         # Debug information and page content
```

## Features

### Data Extraction
- Paper IDs and titles (adapted for NAPAC2025 format)
- Author information (extracted from inline text)
- Institution details
- Paper abstracts
- DOI information (format: `10.18429/JACoW-NAPAC2025-{paperID}`)
- PDF availability checking (when links are present)

### File Organization
- Automatic session-based folder creation (41 sessions for NAPAC2025)
- Three separate folders for different file types
- PDF files renamed with paper titles and type suffixes
- Multiple output formats (JSON, CSV, TXT)

### Error Handling
- Network request retry mechanism
- Comprehensive logging
- Statistics tracking for each file type

## Configuration Options

You can modify the following configurations in the script:

```python
# Base URL
base_url = "https://meow.elettra.eu/97/"

# Output directory
output_dir = "NAPAC2025_Data"

# Request delay (seconds)
delay_between_requests = 1-2

# Retry attempts
max_retries = 3
```

## Log Files
- `napac2025_scraper.log` - Main scraper log with timestamped entries

## Known Limitations & Notes

1. **Dynamic Loading**: NAPAC2025 uses JavaScript to load session lists. The scraper fetches the actual data from `html/session_list.html` rather than the main index page.

2. **PDF Links**: PDF availability detection is limited because the session pages use dynamic loading. PDF URLs are constructed heuristically and checked for existence. Not all PDFs may be detected or available.

3. **Author/Institution Parsing**: The NAPAC2025 page format is tightly packed (no spaces between paper ID, title, and author names). The parser uses pattern matching and may occasionally include extra metadata in titles or miss author details.

4. **Session Coverage**: Successfully loads all 41 sessions from NAPAC2025. Tutorial sessions (e.g., SUTD) may have fewer or no papers depending on the conference structure.

## Important Notes

1. **Network Stability**: Ensure stable internet connection; full scraping may take 5-10 minutes
2. **Storage Space**: Ensure sufficient disk space (output files are typically < 50MB for metadata, PDFs vary)
3. **Request Frequency**: Script includes 1-2 second delays between requests to avoid server overload
4. **Filename Restrictions**: PDF filenames are automatically sanitized for Windows/Unix compatibility

## FAQ

### Q: What if the scraping process is interrupted?
A: Re-run the script. Already downloaded files will be skipped, only new content will be processed.

### Q: Some papers show "No papers detected"?
A: This is normal for tutorial sessions or sessions with very few contributions. Check the Debug/ folder for raw page content to verify.

### Q: PDF downloads show ✗ (not available)?
A: NAPAC2025 pages use dynamic loading for PDF links. The scraper attempts heuristic URL construction but may not find all PDFs. You can manually verify PDF URLs by visiting the session pages.

### Q: How to scrape only specific sessions?
A: Modify the `sessions_config` list in the `load_sessions()` method or use test_mode with a custom session slice.

### Q: Output data format doesn't meet requirements?
A: Modify the `save_session_csv()` or `save_session_txt()` functions to customize output formats.

## Technical Support

If you encounter issues, please check:
1. Python version >= 3.7
2. All dependencies from `requirements.txt` are installed (`requests`, `beautifulsoup4`)
3. Network connection is stable
4. Target website (https://meow.elettra.eu/97/) is accessible

## Disclaimer

This script is for academic research purposes only. Please comply with relevant website terms of use and copyright regulations. Users are responsible for any consequences arising from using this script.

## Version History

### v6.0 (NAPAC2025 - November 2025)
- **Adapted for NAPAC2025 conference** at https://meow.elettra.eu/97/
- Handles dynamic JavaScript-loaded session lists
- Updated paper extraction for tightly-packed page format (no spaces between paper ID/title/author)
- Updated DOI pattern to `JACoW-NAPAC2025-{paperID}`
- Changed output directory to `NAPAC2025_Data`
- Updated log file to `napac2025_scraper.log`
- Loads 41 sessions from NAPAC2025

### v5.0 (SRF2021)
- SRF2021 conference support
- Three file types: Presentations, Papers, Posters
- Interactive web interface
- Enhanced data organization
- Comprehensive error handling
- Multi-format data export