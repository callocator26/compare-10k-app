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
                # FIX: Construct the date regex pattern using string concatenation to avoid f-string syntax issues with curly braces
                date_pattern_for_regex = r'<td>\s*' + re.escape(str(year)) + r'-\d{2}-\d{2}\s*<\/td>'
                date_match = re.search(date_pattern_for_regex, row_content)
                
                if date_match:
                    # Now, find the actual document link (.htm) within this specific row
                    doc_link_match = re.search(r'<a\s+href="(\/Archives\/edgar\/data\/[^"]+\.htm)"[^>]*>', row_content, re.IGNORECASE)
                    if doc_link_match:
                        target_10k_url = f"https://www.sec.gov{doc_link_match.group(1)}"
                        break # Found the correct 10-K URL, exit loop

        if not target_10k_url:
            return None, f"Could not find a 10-K filing for {ticker} in fiscal year {year} on SEC EDGAR. Please ensure the ticker and year are correct, and that the filing exists on EDGAR. (Error finding document URL)"

        st.info(f"Found specific 10-K document URL: {target_10k_url}. Fetching content...")

        # Step 3: Use requests to get the full HTML content of the 10-K document.
        full_10k_response = requests.get(target_10k_url, headers=headers)
        full_10k_response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        full_10k_html = full_10k_response.text

        st.info(f"Extracting '{section_name}' section...")

        # Step 4: Extract the desired section.
        # Normalize HTML for easier parsing by removing multiple spaces and newlines
        normalized_html = re.sub(r'\s+', ' ', full_10k_html).replace('\n', ' ')

        # Find the start of the target section
        start_pattern = re.compile(rf'({re.escape(section_name)})', re.IGNORECASE)
        start_match = start_pattern.search(normalized_html)

        if not start_match:
            return None, f"Could not find the start of '{section_name}' section in the 10-K document."

        start_index = start_match.start()

        # Find the end of the section by looking for the next major item.
        end_pattern = re.compile(r'Item\s+\d+[A-Z]?\.\s+[A-Z][a-zA-Z\s]+', re.IGNORECASE)
        
        # Search for the next item *after* the current section's start
        end_match = end_pattern.search(normalized_html, start_index + len(section_name))

        if end_match:
            end_index = end_match.start()
            extracted_text = normalized_html[start_index:end_index].strip()
        else:
            # If no next item is found, take content until the end of the document
            extracted_text = normalized_html[start_index:].strip()

        # Remove the section title itself from the extracted text
        extracted_text = re.sub(start_pattern, '', extracted_text, 1) # Remove only the first occurrence

        # Additional cleaning steps for extracted HTML content
        extracted_text = re.sub(r'<[^>]*>', '', extracted_text) # Remove all HTML tags
        extracted_text = extracted_text.replace('&nbsp;', ' ') # Replace non-breaking spaces
        extracted_text = re.sub(r'&#\d+;', '', extracted_text) # Remove HTML entities
        extracted_text = re.sub(r'Page\s+\d+', '', extracted_text, flags=re.IGNORECASE) # Remove page numbers
        extracted_text = re.sub(r'\s*\d+\s*', ' ', extracted_text) # Remove standalone numbers (potential page numbers)
        extracted_text = re.sub(r'Table of Contents', '', extracted_text, flags=re.IGNORECASE) # Remove common noise
        extracted_text = re.sub(r'Item\s+\d+[A-Z]?\.\s+[A-Z][a-zA-Z\s]+', '', extracted_text) # Remove other item headers
        extracted_text = re.sub(r'\s{2,}', ' ', extracted_text).strip() # Reduce multiple spaces

        if extracted_text:
            # Attempt to extract company name from the document title
            company_name = ticker.upper() # Default to ticker
            title_match = re.search(r'<title>(.*?)</title>', full_10k_html, re.IGNORECASE)
            if title_match:
                # Heuristic: take the part before "10-K" or "FORM 10-K" in the title
                company_title_part = title_match.group(1)
                company_name_match = re.match(r'(.*?)(?:10-K|FORM 10-K)', company_title_part, re.IGNORECASE)
                if company_name_match:
                    company_name = company_name_match.group(1).strip()
                else:
                    company_name = company_title_part.strip() # Use full title if no 10-K marker

            return extracted_text, company_name
        else:
            return None, f"Could not extract '{section_name}' from the 10-K. The section structure might be different or the content is missing."

    except requests.exceptions.RequestException as e:
        return None, f"Network or HTTP error fetching data: {e}. Please check your internet connection or the SEC EDGAR URL."
    except Exception as e:
        return None, f"An unexpected error occurred during parsing: {e}. This might be due to a change in SEC EDGAR's website structure or an unusual filing format. Please try again."

# Streamlit App Layout
st.set_page_config(layout="wide", page_title="10-K Section Comparator")

st.title("SEC 10-K Section Comparator")
st.markdown("Compare sections of 10-K filings for public companies.")

# Input fields
ticker_input = st.text_input("Company Ticker Symbol (e.g., AAPL, MSFT, NAUT)", "NAUT").upper()
year_input = st.number_input("Fiscal Year (e.g., 2022, 2024)", min_value=1994, max_value=2025, value=2024, step=1)

# Button to trigger the comparison
if st.button("Fetch and Display 'Item 1. Business' Section"):
    if ticker_input and year_input:
        with st.spinner(f"Fetching and parsing {ticker_input}'s {year_input} 10-K..."):
            content, info = get_10k_section(ticker_input, year_input)
            
            if content:
                st.subheader(f"{info} - Item 1. Business ({year_input} 10-K)")
                st.markdown(content)
            else:
                st.error(info)
    else:
        st.warning("Please enter both a ticker symbol and a fiscal year.")

st.markdown("---")
st.markdown("### How to use this app:")
st.markdown("1. Enter the ticker symbol of a public company (e.g., AAPL).")
st.markdown("2. Enter the fiscal year for the 10-K filing you want to retrieve.")
st.markdown("3. Click the 'Fetch and Display' button.")
st.markdown("4. The app will attempt to find the 10-K on SEC EDGAR and extract 'Item 1. Business'.")
st.markdown("5. Future enhancements will include comparing sections across multiple years and using AI for detailed analysis.")
