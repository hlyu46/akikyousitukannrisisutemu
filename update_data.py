import requests
from bs4 import BeautifulSoup
import os
import json
import re

# This script uses pdfplumber to accurately parse tables from the PDF
try:
    import pdfplumber
except ImportError:
    print("Warning: pdfplumber not installed. This script requires pdfplumber.")

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
    print("Extracting data from PDF using pdfplumber...")
    
    classrooms = [
        "1-118", "1-217", "2-100", "2-101", "2-104", "2-200", "2-201", "2-205", "2-300", "2-301", 
        "2-302", "2-305", "3-101", "3-102", "3-103", "3-104", "3-201", "3-202", "3-203", "3-204", 
        "3-205", "3-301", "3-302", "3-303", "3-304", "3-305", "4-101", "4-103", "4-104"
    ]
    days = ['月', '火', '水', '木', '金']
    
    availability_data = {day: {} for day in days}
    updated_at = "最新"
    
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        text = page.extract_text() or ""
        
        # 1. ページ内の日付を探す (例: 2026/7/17)
        date_match = re.search(r'(20\d{2}/\d{1,2}/\d{1,2})', text)
        if date_match:
            updated_at = date_match.group(1)
            
        # 2. 表の抽出
        tables = page.extract_tables()
        if not tables:
            print("No tables found in the PDF.")
            return None
            
        # 複数表がある場合、通常はメインのデータ表が後の方にある
        data_table = tables[-1] if len(tables) > 1 else tables[0]
            
        day_idx = 0
        
        for row in data_table:
            # 2列目が時限 (1〜7) かどうかでデータ行を判定
            if len(row) < 3:
                continue
                
            period_str = str(row[1]).strip()
            if period_str in ['1', '2', '3', '4', '5', '6', '7']:
                period = period_str
                
                available_rooms = []
                for i, cell in enumerate(row[2:]):
                    if i >= len(classrooms):
                        break
                        
                    cell_str = str(cell) if cell is not None else ""
                    # 結合セルや空セルはスキップ
                    if not cell_str.strip() or cell_str == 'None':
                        continue
                        
                    # 文字化けによるクロス(×)は '~' のような文字になるため、チルダが含まれていなければ空き(○)と判定
                    if '~' not in cell_str:
                        available_rooms.append(classrooms[i])
                        
                if day_idx < len(days):
                    availability_data[days[day_idx]][period] = available_rooms
                    
                # 7限目が終わったら次の曜日へ
                if period == '7':
                    day_idx += 1

    return {"updated_at": updated_at, "data": availability_data}

def main():
    try:
        pdf_url = fetch_latest_pdf_url()
        download_pdf(pdf_url)
        
        try:
            import pdfplumber
            new_data = process_pdf("latest.pdf")
            
            if new_data and any(len(periods) > 0 for periods in new_data["data"].values()):
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(new_data, f, ensure_ascii=False, indent=2)
                print(f"Successfully updated data.json (Date: {new_data['updated_at']})")
            else:
                print("Parsed no valid data. Not updating data.json to prevent breaking the site.")
                
        except ImportError:
            print("Dependencies for parsing (pdfplumber) missing.")
            
    except Exception as e:
        print(f"Error during execution: {e}")

if __name__ == "__main__":
    main()
