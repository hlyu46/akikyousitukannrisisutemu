import requests
from bs4 import BeautifulSoup
import os
import json
import re

# This script is designed to run in an environment with tesseract and poppler installed (e.g. GitHub Actions)
try:
    from pdf2image import convert_from_path
    import pytesseract
except ImportError:
    print("Warning: pdf2image or pytesseract not installed. This script is intended to run on GitHub Actions.")

PAGE_URL = "https://rais.skr.u-ryukyu.ac.jp/dc/?p=16037"
DATA_FILE = "data.json"

def fetch_latest_pdf_url():
    print("Fetching announcement page...")
    response = requests.get(PAGE_URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    for a_tag in soup.find_all('a', href=True):
        if a_tag['href'].endswith('.pdf'):
            print(f"Found PDF URL: {a_tag['href']}")
            return a_tag['href']
    raise Exception("Could not find a .pdf link on the page.")

def download_pdf(url, output_path="latest.pdf"):
    print("Downloading PDF...")
    response = requests.get(url)
    response.raise_for_status()
    with open(output_path, 'wb') as f:
        f.write(response.content)
    print("Download complete.")

def process_pdf(pdf_path):
    print("Converting PDF to images...")
    # Requires poppler installed
    images = convert_from_path(pdf_path)
    
    # We only care about the first page based on the format
    image = images[0]
    
    print("Running OCR on the image...")
    # Use Japanese language pack
    text = pytesseract.image_to_string(image, lang='jpn')
    
    return parse_ocr_text(text)

def parse_ocr_text(text):
    print("Parsing OCR text...")
    
    classrooms = [
        "1-118", "1-217", "2-100", "2-101", "2-104", "2-200", "2-201", "2-205", "2-300", "2-301", 
        "2-302", "2-305", "3-101", "3-102", "3-103", "3-104", "3-201", "3-202", "3-203", "3-204", 
        "3-205", "3-301", "3-302", "3-303", "3-304", "3-305", "4-101", "4-103", "4-104"
    ]
    days = ['月', '火', '水', '木', '金']
    
    availability_data = {day: {} for day in days}
    
    # Find lines that start with 1-7 and contain ○ or ×
    # This is a simplified best-effort parser since raw OCR can be messy.
    # In a real production scenario, bounding box analysis is preferred.
    lines = text.split('\n')
    
    day_idx = 0
    current_period = 1
    
    for line in lines:
        line = line.strip().replace(" ", "").replace("〇", "○").replace("X", "×").replace("x", "×")
        if not line:
            continue
            
        # Match lines starting with a period number followed by circles and crosses
        match = re.match(r'^([1-7])(.*[○×].*)$', line)
        if match:
            period = match.group(1)
            symbols_str = match.group(2)
            
            # Extract just the circles and crosses
            symbols = [c for c in symbols_str if c in '○×']
            
            if len(symbols) > 10: # Rough check to ensure it's a valid data row
                # Map to classrooms
                available_rooms = []
                for i, symbol in enumerate(symbols):
                    if i < len(classrooms) and symbol == '○':
                        available_rooms.append(classrooms[i])
                        
                if day_idx < len(days):
                    availability_data[days[day_idx]][period] = available_rooms
                
                current_period += 1
                if current_period > 7:
                    current_period = 1
                    day_idx += 1
                    
    return availability_data

def main():
    try:
        pdf_url = fetch_latest_pdf_url()
        download_pdf(pdf_url)
        
        # In a local test without tesseract, we skip the actual OCR and just print instructions
        try:
            import pytesseract
            new_data = process_pdf("latest.pdf")
            
            # Only update if we successfully parsed some data
            has_data = any(len(periods) > 0 for periods in new_data.values())
            if has_data:
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(new_data, f, ensure_ascii=False, indent=2)
                print("Successfully updated data.json")
            else:
                print("OCR parsed no valid data. Not updating data.json to prevent breaking the site.")
                
        except ImportError:
            print("Dependencies for OCR missing locally. Skipping OCR processing.")
            print("This script will run properly in the GitHub Actions environment.")
            
    except Exception as e:
        print(f"Error during execution: {e}")

if __name__ == "__main__":
    main()
