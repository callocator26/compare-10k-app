import streamlit as st
import re
# The 'requests' library is typically used for HTTP requests in Python.
# In this specific environment, 'browsing.browse' is the intended tool for web scraping.
# I'm including 'requests' here as a common dependency for web apps, but the primary
# fetching logic relies on 'browsing.browse' which is implicitly available in this context.
# If running locally without the 'browsing' tool, you would need to implement fetching
# using 'requests' or a similar library.


# Note: In the actual environment where this code runs, 'browsing' and 'google_search'
# are globally available tools. For local testing, you might need mock implementations
# or actual API calls if you have credentials.

def get_10k_section(ticker, year, section_name="Item 1. Business"):
    """
    Fetches a company's 10-K filing from SEC EDGAR and extracts a specified section.
    """
    try:
        st.info(f"Searching SEC EDGAR for {ticker} {year} 10-K filings...")

        # Step 1: Construct the direct SEC EDGAR search URL for the company's 10-K filings.
        # We use the ticker directly in the CIK parameter, as EDGAR often resolves it.
        # We also specify '10-K' type and limit results.
        # Fixed f-string syntax: use curly braces for variables, not dollar signs
        edgar_company_search_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-K&owner=exclude&count=100"
        
        # Use the browsing tool to get the HTML content of the search results page
        # The 'browsing' tool is available in this execution environment.
        # If running locally, this line would need to be replaced with a standard HTTP request (e.g., using 'requests.get(url).text')
        search_results_html = browsing.browse(query=f"Fetch EDGAR search results for {ticker} {year} 10-K", url=edgar_company_search_url)
        
        st.info("Parsing EDGAR search results to find the specific 10-K document...")

        target_10k_url = ""
        # Regex to find the specific 10-K link for the given year.
        # This regex looks for a table row that contains '10-K' (form type),
        # then captures the href to the actual HTML document (ending in .htm),
        # and also checks for the specific year in the filing date column.
        # The 's' flag allows '.' to match newlines, 'i' for case-insensitive.
        # It's important to find the link to the .htm document, not the .txt or .xml
        filing_regex = re.compile(
            r'<tr[^>]*>.*?<td[^>]*>10-K<\/td>.*?<td[^>]*><a\s+href="(\/Archives\\/edgar\\/data\\/[^"]+\.htm)"[^>]*>.*?<\/td>.*?<td[^>]*>\s*'
            + re.escape(str(year)) + r'-\d{2}-\d{2}\s*<\/td>.*?<\/tr>',
            re.DOTALL | re.IGNORECASE
        )

        match = filing_regex.search(search_results_html)

        if match and match.group(1):
            target_10k_url = f"https://www.sec.gov{match.group(1)}"
        
        if not target_10k_url:
            return None, f"Could not find a 10-K filing for {ticker} in fiscal year {year} on SEC EDGAR. Please ensure the ticker and year are correct, and that the filing exists on EDGAR."

        st.info(f"Found specific 10-K document URL: {target_10k_url}. Fetching content...")

        # Step 3: Browse the actual 10-K document URL to get its full HTML content.
        # If running locally, this line would need to be replaced with a standard HTTP request (e.g., using 'requests.get(url).text')
        full_10k_html = browsing.browse(query=f"Fetch full 10-K content from {target_10k_url}", url=target_10k_url)

        st.info(f"Extracting '{section_name}' section...")

        # Step 4: Extract the desired section.
        # This regex is a starting point and might need refinement for different filings.
        # It looks for the section title and captures content until the next major item.
        # Common pattern: "Item X. Section Title" followed by "Item Y. Next Section Title"
        # For simplicity, we'll assume Item 1. Business is followed by Item 1A. Risk Factors.
        # This is a common pattern but can vary.
        
        # Normalize HTML for easier parsing by removing multiple spaces and newlines
        normalized_html = re.sub(r'\s+', ' ', full_10k_html).replace('\n', ' ')

        # Define the regex for the target section and the section that follows it
        # This needs to be robust to variations like "Item 1. Business" or "ITEM 1. BUSINESS"
        # and also handle cases where there might be sub-items (e.g., Item 1A)
        
        # We need to be careful with the exact wording of section headers.
        # Let's try to capture content between the exact section and the next main Item.
        # This is a common pattern for 10-K documents.
        
        # For Item 1. Business, the next item is usually Item 1A. Risk Factors.
        # We use re.escape to handle periods in "Item 1. Business" correctly.
        # We also make the matching non-greedy (.*?)
        
        # First, try to find the content between the exact section and the next numbered Item.
        # This is more robust than assuming Item 1A always follows Item 1.
        section_regex = re.compile(
            rf'{re.escape(section_name)}\s*(.*?)(?:Item\s+\d+[A-Z]?\.\s+|$)',
            re.DOTALL | re.IGNORECASE
        )
        
        section_match = section_regex.search(normalized_html)

        extracted_text = ""
        if section_match:
            extracted_text = section_match.group(1).strip()
            
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

    except Exception as e:
        return None, f"An error occurred: {e}. This might be due to network issues, an invalid ticker/year, or a change in SEC EDGAR's website structure. Please try again."

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
