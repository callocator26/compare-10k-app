import streamlit as st
import re
import requests # This is the library we will use for web requests

# Note: The 'browsing' and 'google_search' tools are only available to the LLM's execution environment.
# For a Streamlit app deployed by you, standard Python libraries like 'requests' must be used for web fetching.

def get_10k_section(ticker, year, section_name="Item 1. Business"):
    """
    Fetches a company's 10-K filing from SEC EDGAR and extracts a specified section.
    Uses the 'requests' library for web fetching.
    """
    try:
        st.info(f"Searching SEC EDGAR for {ticker} {year} 10-K filings...")

        # Step 1: Construct the direct SEC EDGAR search URL for the company's 10-K filings.
        edgar_company_search_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-K&owner=exclude&count=100"
        
        # Use the requests library to get the HTML content of the search results page
        # Added User-Agent header to mimic a browser, as some websites block requests without it.
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        search_results_response = requests.get(edgar_company_search_url, headers=headers)
        search_results_response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        search_results_html = search_results_response.text
        
        st.info("Parsing EDGAR search results to find the specific 10-K document...")

        target_10k_url = ""
        
        # Find all table rows that contain a 10-K filing
        rows = re.findall(r'<tr[^>]*>(.*?)<\/tr>', search_results_html, re.DOTALL | re.IGNORECASE)

        for row_content in rows:
            # Check if '10-K' is in the row (form type)
            if re.search(r'<td>10-K<\/td>', row_content, re.IGNORECASE):
                # Check if the filing date for the requested year is in the row
                date_match = re.search(rf'<td>\s*{re.escape(str(year))}-\d{{2}}-\d{{2}}\s*<\/td>', row_content)
                if date_match:
                    # Now, find the actual document link (.htm) within this specific row
                    doc_link_match = re.search(r'<a\s+href="(\/Archives\/edgar\/data\/[^"]+\.htm)"[^>]*>', row_content, re.IGNORECASE)
                    if doc_link_match:
                        target_10k_url = f"https://www.sec.gov{doc_link_
