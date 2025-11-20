import time
import pandas as pd
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import random
import re

# Example DataFrame with ASINs
Rating = pd.DataFrame({
    "ASIN": [
        "B0F6CRFWHS",
        "B0F4KSRGGC",
        "B0DGLV8B86",
        "B0DG2XBPY1",
        "B0F4KV3JC2",
        "B09QQKXSLW",
        "B0BY2VKVPS",
        "B0FRZ8HTFV",
        "B0DFM1634X",
        "B0F74NN9B4"
    ]
})

# Build URLs from ASINs
Rating["URL"] = Rating["ASIN"].apply(lambda x: f"https://www.amazon.in/dp/{x}?th=1")

# Add empty columns for scraped data
Rating["Price"] = ""
Rating["MRP"] = ""
Rating["Rating(out of 5 stars)"] = ""
Rating["Total Review"] = ""

# Convert URLs to list
urls = Rating["URL"].tolist()

# User-agent rotation
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
]

# Selenium options
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument(f"user-agent={random.choice(user_agents)}")
options.add_argument("--log-level=3")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# Initialize WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def extract_price(price_text):
    """Extract numeric price from text"""
    if price_text == "Not found":
        return price_text
    
    # Find all numbers with currency symbols and commas
    matches = re.findall(r'[₹$€£]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', price_text)
    if matches:
        # Take the first match and remove commas
        return matches[0].replace(',', '')
    return price_text

# Loop through the URLs
j = 0
while j < len(urls):
    try:
        url = urls[j]
        asin = Rating.loc[j, "ASIN"]
        print(f"Scraping {asin} ({j + 1}/{len(urls)}): {url}")
        driver.get(url)
        time.sleep(random.uniform(5, 8))  # delay to mimic human

        # Parse page with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Extract rating
        rating_element = soup.find("span", {"class": "a-icon-alt"})
        rating = rating_element.text.strip() if rating_element else "Not found"

        # Extract review count
        reviews_element = soup.find("span", {"id": "acrCustomerReviewText"})
        reviews_text = reviews_element.text.strip() if reviews_element else "Not found"

        # Extract current price
        price_text = "Not found"
        price_element = (soup.find("span", {"id": "priceblock_ourprice"}) or
                        soup.find("span", {"id": "priceblock_dealprice"}) or
                        soup.find("span", {"class": "a-price-whole"}) or
                        soup.find("span", {"class": "a-offscreen"}))
        
        if price_element:
            price_text = price_element.get_text(strip=True)
            price_text = extract_price(price_text)

        # Extract MRP (strikethrough price) - Multiple strategies
        mrp_text = "Not found"
        
        # Strategy 1: Look for strikethrough price with class
        mrp_elements = soup.find_all("span", {"class": "a-price a-text-price"})
        
        # Strategy 2: Look for price in a-text-price with strike element
        if not mrp_elements:
            mrp_elements = soup.select('span.a-text-price s.a-text-price')
        
        # Strategy 3: Look for any element with strike tag
        if not mrp_elements:
            mrp_elements = soup.find_all("span", {"class": "a-text-strike"})
        
        # Strategy 4: Look for price block savings price (the amount saved)
        if not mrp_elements:
            savings_element = soup.find("td", {"class": "a-span12 a-color-price a-size-base"})
            if savings_element:
                savings_text = savings_element.get_text(strip=True)
                # Extract MRP from savings text if it contains "M.R.P."
                if "M.R.P." in savings_text:
                    mrp_match = re.search(r'M\.R\.P\.:\s*[₹$€£]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', savings_text)
                    if mrp_match:
                        mrp_text = mrp_match.group(1).replace(',', '')
        
        # Strategy 5: Look for base price in deal blocks
        if not mrp_elements and mrp_text == "Not found":
            mrp_elements = soup.find_all("span", {"class": "a-text-price"})
        
        # Process found MRP elements
        if mrp_elements and mrp_text == "Not found":
            for el in mrp_elements:
                text = el.get_text(strip=True)
                if re.search(r"\d", text):  # Check if contains numbers
                    cleaned_text = extract_price(text)
                    # Only use if it's different from current price and looks like a higher price
                    if (cleaned_text != "Not found" and 
                        cleaned_text != price_text and 
                        (price_text == "Not found" or 
                         (cleaned_text.replace('.', '').isdigit() and price_text.replace('.', '').isdigit() and 
                          float(cleaned_text) > float(price_text)))):
                        mrp_text = cleaned_text
                        break
        
        # Final fallback: If MRP not found but price is found, assume no discount
        if mrp_text == "Not found" and price_text != "Not found":
            mrp_text = price_text  # No discount, MRP same as current price

        # Save results
        Rating.loc[j, "Price"] = price_text
        Rating.loc[j, "MRP"] = mrp_text
        Rating.loc[j, "Rating(out of 5 stars)"] = rating
        Rating.loc[j, "Total Review"] = reviews_text

        print(f"✅ {asin} | Price: {price_text} | MRP: {mrp_text} | Rating: {rating} | Reviews: {reviews_text}")

        j += 1  # go to next ASIN

    except Exception as e:
        print(f"❌ Error scraping ASIN {Rating.loc[j, 'ASIN']}: {e}")
        print("Retrying the same ASIN...")
        time.sleep(random.uniform(3, 6))  # retry delay

# Close driver
driver.quit()

# Reorder columns for Excel output
final_df = Rating[["ASIN", "Price", "MRP", "Rating(out of 5 stars)", "Total Review"]]

# Save to Excel
output_file = "amazon_scraped_data.xlsx"
final_df.to_excel(output_file, index=False)

print("\nScraping Complete!")
print(final_df)
print(f"\n✅ Data saved to {output_file}")