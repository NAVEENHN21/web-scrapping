from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

# Style IDs for different variants
style_ids = ["36733413", "36733414", "32020006"]

# Create URLs using style IDs
base_url = "https://www.myntra.com/trousers/spykar/spykar-men-straight-fit-mid-rise-cargos/{styleid}/buy"
urls = [base_url.format(styleid=style_id) for style_id in style_ids]

# Update with the actual URLs
urls[1] = "https://www.myntra.com/yoga-mats/cult/cult-anti-slip-grip-yoga-mat-with-carry-strap-/36733414/buy"
urls[2] = "https://www.myntra.com/trousers/spykar/spykar-men-straight-fit-mid-rise-cargos/32020006/buy"

# Create reviews URLs
reviews_urls = [f"https://www.myntra.com/reviews/{style_id}" for style_id in style_ids]

# Create DataFrame with the new column structure
Rating = pd.DataFrame({
    'Myntra_StyleID': style_ids,
    'Product_URL': urls,
    'Reviews_URL': reviews_urls,
    'Selling_Price': "",
    'MRP': "",
    'Rating_out_of_5': "",      # 4.3 (the rating number)
    'Total_no_of_ratings': "",  # 6 (verified buyers count)
    'Customer_Reviews': ""      # 4 (customer reviews count)
})

# Set up Selenium WebDriver
options = Options()
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
options.add_argument('--disable-images')  # Faster loading

driver = webdriver.Chrome(options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

def extract_complete_price(price_text):
    """Extract complete price from text including all digits"""
    if not price_text or price_text == "Price not found":
        return "Price not found"
    
    # Clean the text
    price_text = re.sub(r'\s+', ' ', price_text.strip())
    print(f"Price text to extract: '{price_text}'")
    
    # Look for complete price patterns - FIXED REGEX PATTERNS
    # Improved patterns to capture full prices
    price_patterns = [
        r'₹\s*([\d,]+(?:\.\d{2})?)',  # ₹1,299 or ₹1,299.00 or ₹12,999
        r'₹\s*(\d+)',                 # ₹1299 or ₹12999
        r'([\d,]+(?:\.\d{2})?)',      # 1,299 or 1,299.00 or 12,999
        r'(\d+)',                     # 1299 or 12999
    ]
    
    for pattern in price_patterns:
        price_matches = re.findall(pattern, price_text)
        if price_matches:
            # Take the last match (often the complete price)
            full_price = price_matches[-1]
            print(f"Extracted price: '{full_price}' from pattern '{pattern}'")
            
            # Remove commas to get clean numeric value
            clean_price = full_price.replace(',', '')
            return clean_price
    
    return "Price not found"

# Loop through the URLs
j = 0
while j < len(urls):
    try:
        # Open the product page for price information
        product_url = urls[j]
        reviews_url = reviews_urls[j]
        style_id = style_ids[j]
        
        print(f"\n{'='*80}")
        print(f"Scraping Product {j + 1}/{len(urls)} (StyleID: {style_id})")
        print(f"Product URL: {product_url}")
        
        # STEP 1: Get price information from product page
        driver.get(product_url)
        time.sleep(6)

        # Parse the product page with BeautifulSoup
        product_soup = BeautifulSoup(driver.page_source, "html.parser")

        # DEBUG: Let's see what price elements are available
        print("\n=== DEBUG PRICE ELEMENTS ===")
        
        # EXTRACT SELLING PRICE - Current price
        selling_price = "Price not found"
        
        # Myntra's selling price selectors (current price)
        selling_price_selectors = [
            "span.pdp-price",
            "div.pdp-price", 
            "[data-testid='pdp-price']",
            ".pdp-product-price",
            ".selling-price",
            ".price-discounted",
            ".discounted-price",
            ".pdp-discount-container"  # Added container that might have both prices
        ]
        
        for selector in selling_price_selectors:
            try:
                price_elements = product_soup.select(selector)
                for price_element in price_elements:
                    if price_element and price_element.text.strip():
                        price_text = price_element.text.strip()
                        print(f"Selling price selector '{selector}': '{price_text}'")
                        extracted_price = extract_complete_price(price_text)
                        if extracted_price != "Price not found":
                            selling_price = extracted_price
                            print(f"✅ Selected selling price: {selling_price}")
                            break
                if selling_price != "Price not found":
                    break
            except Exception as e:
                continue

        # EXTRACT MRP - Original price (strikethrough)
        mrp = "MRP not found"
        
        # Myntra's MRP selectors (original/strikethrough price)
        mrp_selectors = [
            ".pdp-mrp s",
            ".pdp-mrp .strike",
            ".pdp-price-strike",
            ".original-price",
            ".mrp",
            "s.a-price-whole",
            ".strike",
            ".price-strike",
            "[class*='strike']",
            "[class*='mrp']",
            "[class*='original']",
            ".pdp-discount-container"  # Added container that might have both prices
        ]
        
        print("\n=== DEBUG MRP ELEMENTS ===")
        for selector in mrp_selectors:
            try:
                mrp_elements = product_soup.select(selector)
                for mrp_element in mrp_elements:
                    if mrp_element and mrp_element.text.strip():
                        mrp_text = mrp_element.text.strip()
                        print(f"MRP selector '{selector}': '{mrp_text}'")
                        extracted_mrp = extract_complete_price(mrp_text)
                        if extracted_mrp != "MRP not found":
                            mrp = extracted_mrp
                            print(f"✅ Selected MRP: {mrp}")
                            break
                if mrp != "MRP not found":
                    break
            except Exception as e:
                continue

        # NEW APPROACH: Look for price blocks that contain multiple prices
        if mrp == "MRP not found" or selling_price == "Price not found":
            print("\n=== DEBUG PRICE BLOCKS ===")
            # Look for divs that contain both prices
            price_containers = product_soup.find_all(['div', 'span'], class_=re.compile(r'price|pdp-price|discount', re.IGNORECASE))
            for container in price_containers:
                container_text = container.get_text(strip=True)
                if '₹' in container_text:
                    print(f"Price container: '{container_text}'")
                    # Extract all prices from this container using improved regex
                    all_prices = re.findall(r'₹\s*([\d,]+)', container_text)
                    if all_prices:
                        print(f"All prices found: {all_prices}")
                        if len(all_prices) >= 2:
                            # Usually the first price is MRP, second is selling price
                            mrp_candidate = all_prices[0].replace(',', '')
                            selling_candidate = all_prices[1].replace(',', '')
                            
                            if mrp == "MRP not found":
                                mrp = mrp_candidate
                                print(f"✅ Found MRP in container: {mrp}")
                            if selling_price == "Price not found":
                                selling_price = selling_candidate
                                print(f"✅ Found selling price in container: {selling_price}")
                        elif len(all_prices) == 1:
                            # Only one price found
                            single_price = all_prices[0].replace(',', '')
                            if selling_price == "Price not found":
                                selling_price = single_price
                                print(f"✅ Found single price in container: {selling_price}")
                            if mrp == "MRP not found":
                                mrp = single_price
                                print(f"✅ Using single price as MRP: {mrp}")

        # Enhanced JavaScript approach
        if mrp == "MRP not found" or selling_price == "Price not found":
            print("\n=== DEBUG JAVASCRIPT PRICES ===")
            try:
                # Enhanced JavaScript to find prices
                price_script = """
                var prices = [];
                // Look for elements with price-related classes or attributes
                var selectors = [
                    '[class*="price"], [class*="Price"], [class*="mrp"], [class*="MRP"]',
                    '.pdp-price', '.pdp-mrp', '.selling-price', '.original-price',
                    '[data-testid*="price"]', '.strike', '.price-strike'
                ];
                
                selectors.forEach(function(selector) {
                    var elements = document.querySelectorAll(selector);
                    elements.forEach(function(el) {
                        if (el.textContent && el.textContent.includes('₹')) {
                            var text = el.textContent.trim();
                            // Only add if it looks like a price (contains numbers)
                            if (/\\d/.test(text)) {
                                prices.push({
                                    text: text,
                                    html: el.outerHTML,
                                    class: el.className
                                });
                            }
                        }
                    });
                });
                return prices;
                """
                prices_js = driver.execute_script(price_script)
                print(f"JavaScript found {len(prices_js)} price elements")
                
                for price_info in prices_js:
                    price_text = price_info['text']
                    print(f"JS Price: '{price_text}' | Class: '{price_info['class']}'")
                    extracted_price = extract_complete_price(price_text)
                    
                    if extracted_price != "Price not found":
                        # Determine if it's MRP or selling price based on context
                        html_lower = price_info['html'].lower()
                        class_lower = price_info['class'].lower()
                        
                        is_mrp = any(keyword in html_lower or keyword in class_lower 
                                   for keyword in ['strike', 'mrp', 'original'])
                        is_selling = any(keyword in html_lower or keyword in class_lower 
                                       for keyword in ['selling', 'discount', 'pdp-price'])
                        
                        if is_mrp and mrp == "MRP not found":
                            mrp = extracted_price
                            print(f"✅ JavaScript identified as MRP: {mrp}")
                        elif is_selling and selling_price == "Price not found":
                            selling_price = extracted_price
                            print(f"✅ JavaScript identified as selling price: {selling_price}")
                        elif mrp == "MRP not found":
                            mrp = extracted_price
                            print(f"✅ JavaScript assigned to MRP: {mrp}")
                        elif selling_price == "Price not found":
                            selling_price = extracted_price
                            print(f"✅ JavaScript assigned to selling price: {selling_price}")
                            
            except Exception as e:
                print(f"JavaScript price extraction failed: {e}")

        # If MRP still not found but selling price found, assume no discount
        if mrp == "MRP not found" and selling_price != "Price not found":
            mrp = selling_price
            print("ℹ️ No discount found, MRP same as selling price")

        # STEP 2: Get ratings and reviews from reviews page
        print(f"\nReviews URL: {reviews_url}")
        driver.get(reviews_url)
        time.sleep(5)

        # Parse the reviews page with BeautifulSoup
        reviews_soup = BeautifulSoup(driver.page_source, "html.parser")
        page_text = reviews_soup.get_text()

        # EXTRACT RATING OUT OF 5 - Number before star like "4.3"
        rating_out_of_5 = "Not found"
        
        rating_patterns = [
            r'(\d+\.?\d?)\s*[*★⭐]',
            r'RATING\s*(\d+\.?\d?)',
            r'Rating:\s*(\d+\.?\d?)',
        ]
        
        for pattern in rating_patterns:
            rating_match = re.search(pattern, page_text, re.IGNORECASE)
            if rating_match:
                rating_out_of_5 = rating_match.group(1)
                print(f"Found Rating_out_of_5: {rating_out_of_5}")
                break

        # EXTRACT TOTAL NUMBER OF RATINGS - Verified buyers count
        total_no_of_ratings = "Not found"
        
        verified_patterns = [
            r'(\d+)\s*Verified\s*Buyers?',
            r'Verified\s*Buyers?\s*:\s*(\d+)',
            r'(\d+)\s*Buyers?\s*Verified',
        ]
        
        for pattern in verified_patterns:
            verified_match = re.search(pattern, page_text, re.IGNORECASE)
            if verified_match:
                total_no_of_ratings = verified_match.group(1)
                print(f"Found Total_no_of_ratings: {total_no_of_ratings}")
                break

        # EXTRACT CUSTOMER REVIEWS COUNT
        customer_reviews = "Not found"
        
        reviews_patterns = [
            r'Customer\s*Reviews?\s*\((\d+)\)',
            r'Reviews?\s*\((\d+)\)',
            r'All\s*Reviews?\s*\((\d+)\)',
        ]
        
        for pattern in reviews_patterns:
            reviews_match = re.search(pattern, page_text, re.IGNORECASE)
            if reviews_match:
                customer_reviews = reviews_match.group(1)
                print(f"Found Customer_Reviews: {customer_reviews}")
                break

        # Fallback for reviews
        if customer_reviews == "Not found" and total_no_of_ratings != "Not found":
            customer_reviews = total_no_of_ratings

        # Check if no reviews
        no_reviews_text = reviews_soup.find(text=re.compile(r'no reviews|be the first', re.IGNORECASE))
        if no_reviews_text and rating_out_of_5 == "Not found":
            rating_out_of_5 = "No Ratings"
            total_no_of_ratings = "0"
            customer_reviews = "0"

        # Update DataFrame
        Rating.loc[j, "Selling_Price"] = f"₹{selling_price}" if selling_price != "Price not found" else selling_price
        Rating.loc[j, "MRP"] = f"₹{mrp}" if mrp != "MRP not found" else mrp
        Rating.loc[j, "Rating_out_of_5"] = rating_out_of_5
        Rating.loc[j, "Total_no_of_ratings"] = total_no_of_ratings
        Rating.loc[j, "Customer_Reviews"] = customer_reviews

        print(f"\n✅ FINAL RESULTS - StyleID: {style_id}")
        print(f"   Selling_Price: ₹{selling_price}")
        print(f"   MRP: ₹{mrp}")
        print(f"   Rating_out_of_5: {rating_out_of_5}")
        print(f"   Total_no_of_ratings: {total_no_of_ratings}")
        print(f"   Customer_Reviews: {customer_reviews}")

        j += 1

    except Exception as e:
        print(f"❌ Error scraping URL {j + 1}: {e}")
        import traceback
        traceback.print_exc()
        time.sleep(3)

# Close the driver
driver.quit()

# Final output
final_df = Rating[['Myntra_StyleID', 'Selling_Price', 'MRP', 'Rating_out_of_5', 'Total_no_of_ratings', 'Customer_Reviews']]

print("\n" + "="*80)
print("FINAL RESULTS:")
print("="*80)
print(final_df)

# Save to CSV
output_file = 'myntra_products_complete_data.csv'
final_df.to_csv(output_file, index=False)
print(f"\n✅ Data saved to {output_file}")