#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NAPAC2025 Conference Web Scraper

Author: Ming Liu
Date: November 03, 2025
Description: A web scraper adapted for the NAPAC2025 proceedings hosted at meow.elettra.eu.
             Extracts paper information organized by sessions, downloads PDFs, and exports
             data in multiple formats (JSON, CSV, TXT).

Website: https://meow.elettra.eu/97/
Features:
- Session-based paper extraction (parses NAPAC session index)
- PDF download with validation
- Multi-format data export
- Robust error handling and retry mechanisms
- Comprehensive logging
"""

import requests
from bs4 import BeautifulSoup
import os
import json
import time
import re
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path

class NAPAC2025Scraper:
    """
    Web scraper for NAPAC2025 proceedings hosted at meow.elettra.eu/97.

    This scraper extracts paper information from the NAPAC2025 website by reading
    the session index and parsing individual session pages. It reuses the existing
    download and export logic from the original SRF scraper.
    """

    def __init__(self, base_url: str = "https://meow.elettra.eu/97/", output_dir: str = "NAPAC2025_Data"):
        """
        Initialize the SRF2021 scraper.
        
        Args:
            base_url: Base URL of the SRF2021 conference website
            output_dir: Directory to store scraped data and PDFs
        """
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('napac2025_scraper.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # NAPAC2025 session configuration - will be populated dynamically
        self.sessions_config = []
        
        # Initialize directories and statistics
        self.create_directories()
        self.stats = {'total_papers': 0, 'downloaded_presentations': 0, 'downloaded_papers': 0, 'downloaded_posters': 0, 'errors': 0, 'sessions_processed': 0}

        # Load sessions dynamically
        self.load_sessions()
    
    def load_sessions(self):
        """Load session configuration from the NAPAC2025 website."""
        try:
            # NAPAC2025 uses dynamic loading: the actual session list is in html/session_list.html
            # with links stored in data-href attributes (e.g., 'session/1161-mowp/index.html')
            resp = self.session.get(urljoin(self.base_url, 'html/session_list.html'), timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            sessions = []
            # Find all anchors with data-href attribute
            anchors = soup.find_all('a', attrs={'data-href': True})
            
            for a in anchors:
                data_href = a.get('data-href')
                if not data_href:
                    continue

                # Only process session links (e.g., 'session/1161-mowp/index.html')
                if not data_href.startswith('session/'):
                    continue

                # Build full URL
                full_url = urljoin(self.base_url, data_href)
                
                # Extract session ID from path segment like '1161-mowp'
                parts = data_href.split('/')
                if len(parts) >= 2:
                    seg = parts[1]  # e.g., '1161-mowp'
                    if '-' in seg:
                        code = seg.split('-', 1)[1].upper()  # 'mowp' -> 'MOWP'
                    else:
                        code = seg.upper()
                else:
                    # Fallback: use first word from link text
                    text = a.get_text().strip()
                    code = text.split()[0].upper() if text else 'UNKNOWN'

                # Get full session name from link text
                name = a.get_text().strip()
                if not name:
                    name = code

                sessions.append({
                    'id': code,
                    'name': name,
                    'url': full_url
                })

            self.sessions_config = sessions
            self.logger.info(f"Loaded {len(self.sessions_config)} sessions from NAPAC2025 website")

        except Exception as e:
            self.logger.error(f"Failed to load sessions: {e}")
            self.sessions_config = []
    
    def create_directories(self):
        """Create necessary directory structure for output files."""
        self.output_dir.mkdir(exist_ok=True)
        (self.output_dir / "Presentations").mkdir(exist_ok=True)
        (self.output_dir / "Papers").mkdir(exist_ok=True)
        (self.output_dir / "Posters").mkdir(exist_ok=True)
        (self.output_dir / "Sessions").mkdir(exist_ok=True)
        (self.output_dir / "Debug").mkdir(exist_ok=True)
        self.logger.info(f"Created output directory: {self.output_dir}")
    
    def safe_filename(self, filename: str, max_length: int = 180) -> str:
        """
        Convert filename to safe filesystem name.
        
        Args:
            filename: Original filename
            max_length: Maximum allowed filename length
            
        Returns:
            Safe filename string
        """
        if not filename:
            return "unknown"
        
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*\r\n]', '_', filename)
        filename = re.sub(r'\s+', ' ', filename)
        filename = filename.strip(' ._')
        
        # Truncate if too long
        if len(filename) > max_length:
            filename = filename[:max_length].rsplit(' ', 1)[0]
        
        return filename or "unknown"
    
    def get_page_content(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """
        Get webpage content with retry mechanism.
        
        Args:
            url: URL to fetch
            retries: Number of retry attempts
            
        Returns:
            BeautifulSoup object or None if failed
        """
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return BeautifulSoup(response.text, 'html.parser')
            except requests.RequestException as e:
                self.logger.warning(f"Failed to fetch page (attempt {attempt + 1}/{retries}) {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    self.logger.error(f"Final failure fetching page {url}: {e}")
                    self.stats['errors'] += 1
        return None
    
    def extract_papers_from_session(self, soup: BeautifulSoup, session_id: str) -> List[Dict[str, Any]]:
        """
        Extract paper information from a session page.
        
        Args:
            soup: BeautifulSoup object of the session page
            session_id: Session ID (e.g., 'MOIAA')
            
        Returns:
            List of paper dictionaries
        """
        papers = []
        page_text = soup.get_text()

        # Save debug information
        debug_file = self.output_dir / "Debug" / f"{session_id}_page_text.txt"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(page_text)

        # NAPAC session pages list papers with tightly packed format:
        # "SUP001Title text hereT UPnnn-or-otheruselink...Author names..."
        # We need to extract: Paper ID (e.g., SUP001), Title (ends before author or secondary ID)
        
        # First, find all potential paper IDs (session prefix + 3 digits or 4 uppercase + 2 digits)
        # Pattern: match paper ID followed by capital letter (start of title)
        id_pattern = re.compile(r'\b([A-Z]{3,4}\d{2,3})([A-Z][^\n\r]*?)(?=\b[A-Z]{3,4}\d{2,3}|$)', re.DOTALL)
        
        papers = []
        for m in id_pattern.finditer(page_text):
            pid = m.group(1).strip()
            content = m.group(2).strip()
            
            # Skip if too short or if it's a secondary reference code (like TUP080)
            if len(content) < 20:
                continue
            
            # Extract title: it ends before common patterns
            # 1) Secondary paper code (e.g., "TUP080use link")
            # 2) Author names (e.g., "H. Alamprese")
            # 3) DOI/Citation text
            title = content
            
            # Remove secondary paper codes and "use link" phrases
            title = re.sub(r'[A-Z]{3,4}\d{2,3}use\s+link.*', '', title, flags=re.DOTALL)
            
            # Split at author pattern: capital initial + period + space + capitalized surname
            author_match = re.search(r'([A-Z]\.\s+[A-Z][a-z]+)', title)
            if author_match:
                title = title[:author_match.start()].strip()
            
            # Also try splitting at common metadata keywords
            for keyword in ['DOI:', 'About:', 'Cite:', 'Received:', 'Funding:']:
                if keyword in title:
                    title = title.split(keyword)[0].strip()
                    break
            
            # Filter short or empty titles
            if len(title) < 10:
                continue
            
            # Clean up trailing/leading whitespace
            title = ' '.join(title.split())
            
            page_num = ''
            
            # Use existing detail extractor
            paper_info = self.extract_paper_details_from_page(soup, pid, title, page_num)
            if paper_info and paper_info['title']:
                papers.append(paper_info)
                self.logger.info(f"  ✓ {pid}: {title[:50]}...")

        if not papers:
            self.logger.warning(f"No papers detected by pattern matching in session {session_id}")

        return papers
    
    def extract_paper_details_from_page(self, soup: BeautifulSoup, paper_id: str, title: str, page_num: str) -> Dict[str, Any]:
        """
        Extract detailed information for a single paper from the session page.
        
        Args:
            soup: BeautifulSoup object of the session page
            paper_id: Paper ID (e.g., 'SUP001')
            title: Paper title
            page_num: Page number
            
        Returns:
            Dictionary containing paper information
        """
        paper_info = {
            'paper_id': paper_id,
            'title': title,
            'authors': [],
            'institutions': [],
            'abstract': '',
            'presentation_url': '',
            'paper_url': '',
            'poster_url': '',
            'doi': f"https://doi.org/10.18429/JACoW-NAPAC2025-{paper_id}",
            'page_number': page_num,
            'presentation_available': False,
            'paper_available': False,
            'poster_available': False
        }
        
        # Find the paper section in the HTML using BeautifulSoup
        # Look for the contrib-ancor div with id matching this paper (lowercase)
        anchor_div = soup.find('div', class_='contrib-ancor', id=paper_id.lower())
        
        if anchor_div:
            # Get the contrib-header (next sibling)
            contrib_header = anchor_div.find_next_sibling('div', class_='contrib-header')
            # Get the contrib-subheader (sibling after header)
            contrib_subheader = contrib_header.find_next_sibling('div', class_='contrib-subheader') if contrib_header else None
            # Get other sections
            contrib_desc = contrib_subheader.find_next_sibling('div', class_='contrib-desc') if contrib_subheader else None
            contrib_authors = contrib_desc.find_next_sibling('div', class_='contrib-authors') if contrib_desc else None
            
            # Extract primary paper code from contrib-subheader
            # Pattern: <a data-href=session/xxxx/index.html#papercode>PAPERCODE</a>
            primary_code = None
            if contrib_subheader:
                primary_code_link = contrib_subheader.find('a', {'data-href': re.compile(r'session/.*#\w+')})
                if primary_code_link:
                    primary_code = primary_code_link.get_text().strip().upper()
                    self.logger.debug(f"Found primary code {primary_code} for {paper_id}")
            
            # If no primary code found (main session papers), use the paper_id itself
            if not primary_code:
                primary_code = paper_id
                self.logger.debug(f"Using paper_id as primary code: {primary_code}")
            
            # PDF URL is based on primary code
            paper_pdf_url = urljoin(self.base_url, f"pdf/{primary_code}.pdf")
            paper_info['paper_url'] = paper_pdf_url
            paper_info['paper_available'] = self.check_pdf_exists(paper_pdf_url)
            
            # Update DOI to use primary code
            paper_info['doi'] = f"https://doi.org/10.18429/JACoW-NAPAC2025-{primary_code}"
            
            # Extract authors from contrib-authors
            if contrib_authors:
                # Authors are in <li> tags with <b> for names
                author_items = contrib_authors.find_all('li')
                for item in author_items:
                    # Get bold author names
                    bold_authors = item.find_all('b')
                    for b in bold_authors:
                        author_name = b.get_text().strip().rstrip(',')
                        if author_name:
                            paper_info['authors'].append(author_name)
                    
                    # Get institution from <br> tag siblings
                    br_tag = item.find('br')
                    if br_tag and br_tag.next_sibling:
                        inst_text = br_tag.next_sibling.strip() if isinstance(br_tag.next_sibling, str) else br_tag.next_sibling.get_text().strip()
                        if inst_text and inst_text not in paper_info['institutions']:
                            paper_info['institutions'].append(inst_text)
            
            # Extract abstract from contrib-desc
            if contrib_desc:
                paper_info['abstract'] = contrib_desc.get_text().strip()
        
        else:
            self.logger.warning(f"Could not find detailed section for {paper_id} in HTML")
        
        return paper_info
    
    def check_pdf_exists(self, pdf_url: str) -> bool:
        """
        Check if PDF file exists and is accessible.
        
        Args:
            pdf_url: URL of the PDF file
            
        Returns:
            True if PDF exists and is accessible
        """
        try:
            response = self.session.head(pdf_url, timeout=10)
            return response.status_code == 200 and 'pdf' in response.headers.get('content-type', '').lower()
        except:
            return False
    
    def scrape_session(self, session: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Scrape all papers from a single session.
        
        Args:
            session: Session configuration dictionary
            
        Returns:
            List of paper dictionaries
        """
        self.logger.info(f"Scraping session: {session['name']}")
        
        soup = self.get_page_content(session['url'])
        if not soup:
            return []
        
        papers = self.extract_papers_from_session(soup, session['id'])
        
        self.stats['total_papers'] += len(papers)
        self.stats['sessions_processed'] += 1
        
        self.logger.info(f"Session {session['id']} results: {len(papers)} papers")
        
        # Display found papers
        for i, paper in enumerate(papers):
            pres_status = "✓" if paper['presentation_available'] else "✗"
            paper_status = "✓" if paper['paper_available'] else "✗"
            poster_status = "✓" if paper['poster_available'] else "✗"
            self.logger.info(f"  {i+1}. {paper['paper_id']}: {paper['title'][:50]}... [P:{pres_status} R:{paper_status} T:{poster_status}]")
        
        return papers
    
    def download_single_file(self, file_url: str, paper_info: Dict[str, Any], session_name: str, folder: str, file_type: str) -> bool:
        """
        Download a single file (presentation, paper, or poster).
        
        Args:
            file_url: URL of the file
            paper_info: Paper information dictionary
            session_name: Name of the session
            folder: Target folder name
            file_type: Type of file (presentation, paper, poster)
            
        Returns:
            True if download successful
        """
        try:
            session_dir = self.output_dir / folder / self.safe_filename(session_name)
            session_dir.mkdir(exist_ok=True, parents=True)
            
            # Use simple naming: PAPERID.pdf, PAPERID_talk.pdf, PAPERID_poster.pdf
            suffix = "_talk" if file_type == "presentation" else ("_poster" if file_type == "poster" else "")
            filename = f"{paper_info['paper_id']}{suffix}.pdf"
            
            filepath = session_dir / filename
            
            if filepath.exists():
                self.logger.info(f"{file_type.title()} already exists, skipping: {filename}")
                return True
            
            response = self.session.get(file_url, stream=True, timeout=60)
            response.raise_for_status()
            
            content_length = int(response.headers.get('content-length', 0))
            if content_length > 0 and content_length < 100:  # Skip obviously wrong small files
                self.logger.warning(f"{file_type.title()} file too small ({content_length} bytes), skipping: {paper_info['paper_id']}")
                return False
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.logger.info(f"✅ Downloaded {file_type}: {filename} ({content_length} bytes)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to download {file_type} {file_url}: {e}")
            self.stats['errors'] += 1
            return False
    
    def download_files(self, paper_info: Dict[str, Any], session_name: str):
        """
        Download all available files (presentation, paper, poster) for a paper.
        
        Args:
            paper_info: Paper information dictionary
            session_name: Name of the session
        """
        file_types = [
            ('presentation', paper_info['presentation_url'], paper_info['presentation_available'], 'Presentations'),
            ('paper', paper_info['paper_url'], paper_info['paper_available'], 'Papers'),
            ('poster', paper_info['poster_url'], paper_info['poster_available'], 'Posters')
        ]
        
        for file_type, url, available, folder in file_types:
            if available:
                success = self.download_single_file(url, paper_info, session_name, folder, file_type)
                if success:
                    self.stats[f'downloaded_{file_type}s'] += 1
    
    def save_session_data(self, session: Dict[str, str], papers: List[Dict[str, Any]]):
        """
        Save session data to files in multiple formats.
        
        Args:
            session: Session configuration dictionary
            papers: List of paper dictionaries
        """
        session_dir = self.output_dir / "Sessions" / self.safe_filename(session['name'])
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # JSON format
        json_file = session_dir / "papers_data.json"
        session_data = {
            'session_info': session,
            'papers': papers,
            'paper_count': len(papers),
            'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        
        # CSV format
        self.save_session_csv(session_dir, papers, session)
        
        # Text format
        self.save_session_txt(session_dir, session, papers)
        
        self.logger.info(f"Saved session data: {session['name']} ({len(papers)} papers)")
    
    def save_session_csv(self, session_dir: Path, papers: List[Dict[str, Any]], session: Dict[str, str]):
        """Save session data in CSV format."""
        import csv
        
        csv_file = session_dir / "papers_data.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            if not papers:
                return
                
            fieldnames = ['session_name', 'paper_id', 'title', 'authors', 'institutions', 'abstract', 
                         'presentation_url', 'presentation_available', 'paper_url', 'paper_available', 
                         'poster_url', 'poster_available', 'doi', 'page_number']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for paper in papers:
                row = {
                    'session_name': session['name'],
                    **paper
                }
                row['authors'] = '; '.join(paper['authors'])
                row['institutions'] = '; '.join(paper['institutions'])
                writer.writerow(row)
    
    def save_session_txt(self, session_dir: Path, session: Dict[str, str], papers: List[Dict[str, Any]]):
        """Save session data in text format."""
        txt_file = session_dir / "papers_summary.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"Session: {session['name']}\n")
            f.write(f"Session ID: {session['id']}\n")
            f.write(f"URL: {session['url']}\n")
            f.write(f"Scrape time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Paper count: {len(papers)}\n")
            available_presentations = sum(1 for p in papers if p.get('presentation_available', False))
            available_papers_count = sum(1 for p in papers if p.get('paper_available', False))
            available_posters = sum(1 for p in papers if p.get('poster_available', False))
            f.write(f"Available presentations: {available_presentations}/{len(papers)}\n")
            f.write(f"Available papers: {available_papers_count}/{len(papers)}\n")
            f.write(f"Available posters: {available_posters}/{len(papers)}\n")
            f.write("=" * 80 + "\n\n")
            
            for i, paper in enumerate(papers, 1):
                pres_status = "✓ Available" if paper.get('presentation_available', False) else "✗ Not available"
                paper_status = "✓ Available" if paper.get('paper_available', False) else "✗ Not available"
                poster_status = "✓ Available" if paper.get('poster_available', False) else "✗ Not available"
                f.write(f"{i}. Paper ID: {paper['paper_id']}\n")
                f.write(f"   Title: {paper['title']}\n")
                if paper['authors']:
                    f.write(f"   Authors: {', '.join(paper['authors'])}\n")
                if paper['institutions']:
                    f.write(f"   Institutions: {'; '.join(paper['institutions'])}\n")
                f.write(f"   Page: {paper.get('page_number', 'N/A')}\n")
                f.write(f"   Presentation Status: {pres_status}\n")
                f.write(f"   Paper Status: {paper_status}\n")
                f.write(f"   Poster Status: {poster_status}\n")
                f.write(f"   Presentation URL: {paper['presentation_url']}\n")
                f.write(f"   Paper URL: {paper['paper_url']}\n")
                f.write(f"   Poster URL: {paper['poster_url']}\n")
                if paper['doi']:
                    f.write(f"   DOI: {paper['doi']}\n")
                if paper['abstract']:
                    abstract_preview = paper['abstract'][:300] + '...' if len(paper['abstract']) > 300 else paper['abstract']
                    f.write(f"   Abstract: {abstract_preview}\n")
                f.write("-" * 60 + "\n")
    
    def create_final_summary(self, all_sessions_data: List[Dict]):
        """
        Create final summary report of all scraped data.
        
        Args:
            all_sessions_data: List of all session data dictionaries
        """
        # Calculate statistics
        total_presentations = sum(
            sum(1 for paper in session_data['papers'] if paper.get('presentation_available', False))
            for session_data in all_sessions_data
        )
        total_papers = sum(
            sum(1 for paper in session_data['papers'] if paper.get('paper_available', False))
            for session_data in all_sessions_data
        )
        total_posters = sum(
            sum(1 for paper in session_data['papers'] if paper.get('poster_available', False))
            for session_data in all_sessions_data
        )
        
        # Text summary
        summary_file = self.output_dir / "NAPAC2025_Final_Report.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("NAPAC2025 Conference Complete Scraping Report\n")
            f.write("=" * 60 + "\n")
            f.write(f"Scrape completion time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Sessions processed: {self.stats['sessions_processed']}\n")
            f.write(f"Total papers: {self.stats['total_papers']}\n")
            f.write(f"Available presentations: {total_presentations}\n")
            f.write(f"Available papers: {total_papers}\n")
            f.write(f"Available posters: {total_posters}\n")
            f.write(f"Successfully downloaded presentations: {self.stats['downloaded_presentations']}\n")
            f.write(f"Successfully downloaded papers: {self.stats['downloaded_papers']}\n")
            f.write(f"Successfully downloaded posters: {self.stats['downloaded_posters']}\n")
            f.write(f"Errors: {self.stats['errors']}\n\n")
            
            f.write("Session detailed statistics:\n")
            f.write("-" * 50 + "\n")
            for session_data in all_sessions_data:
                session = session_data['session_info']
                papers = session_data['papers']
                available_presentations = sum(1 for p in papers if p.get('presentation_available', False))
                available_papers_count = sum(1 for p in papers if p.get('paper_available', False))
                available_posters = sum(1 for p in papers if p.get('poster_available', False))
                
                f.write(f"Session: {session['name']}\n")
                f.write(f"   Papers: {len(papers)}\n")
                f.write(f"   Available presentations: {available_presentations}\n")
                f.write(f"   Available papers: {available_papers_count}\n")
                f.write(f"   Available posters: {available_posters}\n")
                f.write(f"   URL: {session['url']}\n")
                
                if papers:
                    f.write("   Paper list:\n")
                    for paper in papers:
                        pdf_icon = "PDF" if paper.get('pdf_available', False) else "---"
                        f.write(f"     [{pdf_icon}] {paper['paper_id']}: {paper['title'][:60]}...\n")
                f.write("\n")
        
        # JSON index
        master_json = self.output_dir / "NAPAC2025_Complete_Index.json"
        with open(master_json, 'w', encoding='utf-8') as f:
            json.dump({
                'scrape_info': {
                    'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'sessions_processed': self.stats['sessions_processed'],
                    'total_papers': self.stats['total_papers'],
                    'available_presentations': total_presentations,
                    'available_papers': total_papers,
                    'available_posters': total_posters,
                    'downloaded_presentations': self.stats['downloaded_presentations'],
                    'downloaded_papers': self.stats['downloaded_papers'],
                    'downloaded_posters': self.stats['downloaded_posters'],
                    'errors': self.stats['errors']
                },
                'sessions': all_sessions_data
            }, f, ensure_ascii=False, indent=2)

        # Create master CSV
        self.create_master_csv(all_sessions_data)
    
    def create_master_csv(self, all_sessions_data: List[Dict]):
        """Create master CSV file containing all papers."""
        import csv

        csv_file = self.output_dir / "NAPAC2025_All_Papers.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ['session_name', 'session_id', 'paper_id', 'title', 'authors', 'institutions', 
                         'abstract', 'presentation_url', 'presentation_available', 'paper_url', 'paper_available',
                         'poster_url', 'poster_available', 'doi', 'page_number']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for session_data in all_sessions_data:
                session_info = session_data['session_info']
                for paper in session_data['papers']:
                    row = {
                        'session_name': session_info['name'],
                        'session_id': session_info['id'],
                        **paper
                    }
                    row['authors'] = '; '.join(paper['authors'])
                    row['institutions'] = '; '.join(paper['institutions'])
                    writer.writerow(row)
    
    def run(self, test_mode: bool = False):
        """
        Run the main scraping process.
        
        Args:
            test_mode: If True, only process first 3 sessions for testing
            
        Returns:
            List of all session data
        """
        self.logger.info("Starting NAPAC2025 conference data scraping")
        start_time = time.time()
        
        try:
            sessions = self.sessions_config
            
            self.logger.info(f"Prepared to process {len(sessions)} sessions")
            
            if test_mode:
                sessions = sessions[:3]  # Test with first 3 sessions
                self.logger.info(f"Test mode: processing first 3 sessions")
            
            all_sessions_data = []
            
            # Process each session
            for i, session in enumerate(sessions, 1):
                self.logger.info(f"\nProcessing session {i}/{len(sessions)}: {session['name']}")
                
                try:
                    papers = self.scrape_session(session)
                    
                    if papers:
                        self.save_session_data(session, papers)
                        
                        # Download files for all papers in this session
                        for paper in papers:
                            self.download_files(paper, session['name'])
                            time.sleep(1)  # Avoid too frequent requests
                        
                        self.logger.info(f"✅ Session completed: {len(papers)} papers")
                        self.logger.info(f"   Presentations downloaded: {self.stats['downloaded_presentations']}")
                        self.logger.info(f"   Papers downloaded: {self.stats['downloaded_papers']}")
                        self.logger.info(f"   Posters downloaded: {self.stats['downloaded_posters']}")
                    else:
                        self.logger.info(f"⚠️ Session {session['id']} found no papers")
                    
                    all_sessions_data.append({
                        'session_info': session,
                        'papers': papers,
                        'paper_count': len(papers)
                    })
                    
                    time.sleep(2)  # Rest between sessions
                    
                except Exception as e:
                    self.logger.error(f"❌ Error processing session {session['name']}: {e}")
                    self.stats['errors'] += 1
                    continue
            
            # Create final report
            self.create_final_summary(all_sessions_data)
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"\n🎉 Scraping completed! Time elapsed: {elapsed_time:.2f} seconds")
            self.logger.info(f"📊 Final statistics:")
            self.logger.info(f"  ✅ Sessions processed: {self.stats['sessions_processed']}")
            self.logger.info(f"  📄 Total papers: {self.stats['total_papers']}")
            self.logger.info(f"  � Presentations downloaded: {self.stats['downloaded_presentations']}")
            self.logger.info(f"  📄 Papers downloaded: {self.stats['downloaded_papers']}")
            self.logger.info(f"  📋 Posters downloaded: {self.stats['downloaded_posters']}")
            self.logger.info(f"  ❌ Errors: {self.stats['errors']}")
            
            return all_sessions_data
            
        except Exception as e:
            self.logger.error(f"Critical error during scraping process: {e}")
            raise


def main():
    """Main function to run the NAPAC2025 scraper."""
    print("NAPAC2025 Conference Web Scraper")
    print("=" * 60)
    print("Comprehensive scraper for NAPAC2025 conference papers")
    print("Author: Ming Liu")
    print()

    scraper = NAPAC2025Scraper()
    
    try:
        print("Starting test mode...")
        results = scraper.run(test_mode=True)
        
        print("\n" + "="*60)
        print("Test completed successfully!")
        
        # Ask if user wants to continue with full scraping
        print("\nWould you like to continue with full scraping of all sessions?")
        choice = input("Enter 'y' to continue with full scraping, any other key to exit: ").lower().strip()
        
        if choice == 'y':
            print("\nStarting full scraping...")
            results = scraper.run(test_mode=False)
            
            print("\n" + "="*60)
            print("Full scraping completed successfully!")
            print(f"Output directory: {scraper.output_dir}")
            print("\nMain output files:")
            print("  📊 NAPAC2025_Final_Report.txt - Complete scraping report")
            print("  📈 NAPAC2025_All_Papers.csv - All papers Excel table")
            print("  🗂️ NAPAC2025_Complete_Index.json - Complete data index")
            print("  📁 Sessions/ - Session-categorized detailed data")
            print("  � Presentations/ - Downloaded presentation files")
            print("  📁 Papers/ - Downloaded paper files")
            print("  📁 Posters/ - Downloaded poster files")
            print("  🔍 Debug/ - Debug information and page content")
            print("\n💡 Each session contains JSON, CSV, TXT format data")
        
    except KeyboardInterrupt:
        print("\n⏹️ User interrupted scraping")
    except Exception as e:
        print(f"\n❌ Scraping failed: {e}")


if __name__ == "__main__":
    main()