# compare_10k_app.py

import streamlit as st
import requests
import re
from bs4 import BeautifulSoup
from difflib import HtmlDiff

# Helper to get the SEC CIK from ticker
def get_cik(ticker):
    ticker = ticker.upper()
    url = "https://www.sec.gov/files/company_tickers.json"
    r = requests.get(url, headers={"User-Agent": "10KComparer/1.0"})
    data = r.json()
    for item in data.values():
        if item['ticker'] == ticker:
            return str(item['cik_str']).zfill(10)
    return None

# Get filing URLs for selected years
def get_10k_urls(cik, years):
    urls = {}
    feed_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    r = requests.get(feed_url, headers={"User-Agent": "10KComparer/1.0"})
    data = r.json()
    for filing in data['filings']['recent']['form']: 
        idx = data['filings']['recent']['form'].index(filing)
        if filing == '10-K':
            year = data['filings']['recent']['filingDate'][idx][:4]
            if year in years:
                acc_num = data['filings']['recent']['accessionNumber'][idx].replace('-', '')
                doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_num}/index.json"
                doc_data = requests.get(doc_url, headers={"User-Agent": "10KComparer/1.0"}).json()
                for file in doc_data['directory']['item']:
                    if file['name'].endswith('.htm') or file['name'].endswith('.html'):
                        urls[year] = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_num}/{file['name']}"
                        break
    return urls

# Extract specific item from 10-K
def extract_item(html, item_number):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()
    pattern = re.compile(rf"item\\s+{item_number}[^\\n\\r]*", re.IGNORECASE)
    matches = list(pattern.finditer(text))
    if len(matches) >= 1:
        start = matches[0].end()
        end = matches[1].start() if len(matches) > 1 else len(text)
        return text[start:end].strip()
    return "Section not found."

# Compare two text versions
def compare_texts(text1, text2):
    diff = HtmlDiff()
    return diff.make_file(text1.splitlines(), text2.splitlines())

# Stre
