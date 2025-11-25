from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

# Example DataFrame with FSN + URL
fsns = [
    "SGEG7C8UFCXKGQC5",
    "SPBGAME4WWPKHGN3",
    "FWTGYFHMXXTS8HPK"
]

# Initialize DataFrame with additional columns
Rating = pd.DataFrame({
    "ASIN": fsns,
    "Price": "",
    "MRP": "",
    "Rating out of 5": "",
    "Total Ratings": "",
    "Total Reviews": ""
})

urls = [f"https://www.flipkart.com/item/p/itmf?pid={fsn}&lid" for fsn in fsns]

# Set up Selenium WebDriver
options = webdriver.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--log-level=3")
# Remove headless for debugging
# options.add_argument("--headless")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def extract_rating_and_reviews(text):
    """Extract rating, total ratings and total reviews from text"""
    if not text or text == "N/A":
        return "N/A", "N/A", "N/A"
    
    # Pattern to match: "4.3 ★ 7,620 Ratings & 454 Reviews"
    pattern = r'(\d+\.?\d?)\s*★\s*([\d,]+)\s*Ratings?\s*&\s*([\d,]+)\s*Reviews?'
    match = re.search(pattern, text)
    
    if match:
        rating = match.group(1)
        total_ratings = match.group(2)
        total_reviews = match.group(3)
        return rating, total_ratings, total_reviews
    
    return "N/A", "N/A", "N/A"

# Loop through the URLs
for j, url in enumerate(urls):
    try:
        print(f"\nScraping URL {j + 1}/{len(urls)}: {url}")
        driver.get(url)
        time.sleep(5)  # Increased wait time for page load

        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # DEBUG: Save page source for inspection
        with open(f"debug_page_{j}.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        # ---------- Extract Price ----------
        price_selectors = [
            "div.Nx9bqj", 
            "div._30jeq3",
            "div._16Jk6d",
            "[class*='price']",
            ".CxhGGd"
        ]
        price = "N/A"
        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element and price_element.text.strip():
                price = price_element.text.strip()
                print(f"Found price with selector '{selector}': {price}")
                break

        # ---------- Extract MRP ----------
        mrp_selectors = [
            "div.yRaY8j",
            "div._3I9_wc",
            "div._2p6lqe",
            "s._2p6lqe",
            ".A6+E6v"
        ]
        mrp = "N/A"
        for selector in mrp_selectors:
            mrp_element = soup.select_one(selector)
            if mrp_element and mrp_element.text.strip():
                mrp = mrp_element.text.strip()
                print(f"Found MRP with selector '{selector}': {mrp}")
                break

        # ---------- Extract Rating out of 5 ----------
        rating_selectors = [
            "div._3LWZlK",  # Main rating selector
            "div.XQDdHH",
            "[class*='rating']",
            "div._1lRcqv",  # Alternative rating selector
            ".gUuXy-._16VRIQ"  # Rating in the reviews section
        ]
        
        rating = "N/A"
        for selector in rating_selectors:
            rating_element = soup.select_one(selector)
            if rating_element and rating_element.text.strip():
                rating_text = rating_element.text.strip()
                # Check if it's a numeric rating
                if re.match(r'^\d+\.?\d*$', rating_text):
                    rating = rating_text
                    print(f"Found rating with selector '{selector}': {rating}")
                    break

        # ---------- Extract Total Ratings and Reviews ----------
        ratings_reviews_selectors = [
            "span._2_R_DZ",
            "span.Wphh3N",
            "div.row._2afbiS",
            "span._13vcmD",
            "span.gUuXy-._2D5lwg",  # Ratings & reviews count
            "div._3uSWvT"  # Ratings count
        ]
        
        total_ratings = "N/A"
        total_reviews = "N/A"
        
        for selector in ratings_reviews_selectors:
            element = soup.select_one(selector)
            if element and element.text.strip():
                text = element.text.strip()
                print(f"Found ratings/reviews text with selector '{selector}': {text}")
                
                # Extract using regex
                rating_match = re.search(r'(\d+[,]?\d*)\s*Ratings?', text)
                reviews_match = re.search(r'(\d+[,]?\d*)\s*Reviews?', text)
                
                if rating_match:
                    total_ratings = rating_match.group(1)
                if reviews_match:
                    total_reviews = reviews_match.group(1)
                
                if total_ratings != "N/A" or total_reviews != "N/A":
                    break

        # Alternative approach: Look for the combined ratings & reviews text
        if total_ratings == "N/A" and total_reviews == "N/A":
            combined_selectors = [
                "span._2_R_DZ",
                "div._1uJVNT",
                "span.gUuXy-._2D5lwg"
            ]
            
            for selector in combined_selectors:
                element = soup.select_one(selector)
                if element and element.text.strip():
                    combined_text = element.text.strip()
                    print(f"Found combined text with selector '{selector}': {combined_text}")
                    
                    # Try to extract both ratings and reviews
                    extracted_rating, extracted_ratings, extracted_reviews = extract_rating_and_reviews(combined_text)
                    
                    if extracted_rating != "N/A" and rating == "N/A":
                        rating = extracted_rating
                    if extracted_ratings != "N/A":
                        total_ratings = extracted_ratings
                    if extracted_reviews != "N/A":
                        total_reviews = extracted_reviews
                    
                    if total_ratings != "N/A" or total_reviews != "N/A":
                        break

        # Final fallback: Use JavaScript to find rating elements
        if rating == "N/A":
            try:
                rating_script = """
                var ratingElements = document.querySelectorAll('div._3LWZlK, div.XQDdHH, [class*="rating"]');
                for (var i = 0; i < ratingElements.length; i++) {
                    var text = ratingElements[i].textContent.trim();
                    if (text && /^\\d+\\.?\\d*$/.test(text)) {
                        return text;
                    }
                }
                return "N/A";
                """
                rating_js = driver.execute_script(rating_script)
                if rating_js != "N/A":
                    rating = rating_js
                    print(f"Found rating via JavaScript: {rating}")
            except Exception as e:
                print(f"JavaScript rating extraction failed: {e}")

        # Store results in DataFrame
        Rating.loc[j, "Price"] = price
        Rating.loc[j, "MRP"] = mrp
        Rating.loc[j, "Rating out of 5"] = rating
        Rating.loc[j, "Total Ratings"] = total_ratings
        Rating.loc[j, "Total Reviews"] = total_reviews

        # Print in the desired format
        print(f"\n✅ RESULTS - ASIN: {Rating.loc[j, 'ASIN']} | Price: {price} | MRP: {mrp} | Rating out of 5: {rating} | Total Ratings: {total_ratings} | Total Reviews: {total_reviews}")

    except Exception as e:
        print(f"❌ Error scraping URL {j + 1}: {e}")
        import traceback
        traceback.print_exc()
        Rating.loc[j, ["Price", "MRP", "Rating out of 5", "Total Ratings", "Total Reviews"]] = "N/A"

driver.quit()

# Reorder columns as required
Rating = Rating[["ASIN", "Price", "MRP", "Rating out of 5", "Total Ratings", "Total Reviews"]]

# Save to Excel
output_file = "flipkart_output.xlsx"
Rating.to_excel(output_file, index=False)

print("\nScraping Complete! Data saved to", output_file)

# Print final results in the desired format
print("\n" + "="*100)
print("FINAL RESULTS:")
print("="*100)
for index, row in Rating.iterrows():
    print(f"ASIN: {row['ASIN']} | Price: {row['Price']} | MRP: {row['MRP']} | Rating out of 5: {row['Rating out of 5']} | Total Ratings: {row['Total Ratings']} | Total Reviews: {row['Total Reviews']}")