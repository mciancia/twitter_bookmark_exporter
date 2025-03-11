from httpcore import TimeoutException
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


# Create Chrome options with a specific user data directory
chrome_options = Options()
chrome_options.add_argument("--user-data-dir=profile_dir")
# Optional: specify profile
chrome_options.add_argument("--profile-directory=Profile1")

# Add headless mode configuration
# chrome_options.add_argument("--headless=new")  # Use the new headless mode

# # Add Docker-compatible arguments
# chrome_options.add_argument("--no-sandbox")  # Required for Docker
# chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
# chrome_options.add_argument("--disable-gpu")  # Disable GPU hardware acceleration
chrome_options.add_argument("--window-size=1920,2160")  # Set window size for consistent rendering

# Initialize Chrome with these options
# driver = webdriver.Chrome()

# Initialize the Chrome browser
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(options=chrome_options, service=service)

# Alternative setup for Docker environment
# Uncomment these lines and comment out the above two lines when running in Docker
# service = Service('/usr/bin/chromedriver')  # Path to chromedriver in Docker
# driver = webdriver.Chrome(options=chrome_options, service=service)



# Navigate to Twitter
driver.get("https://twitter.com/login")


bookmarks_script = """
        // JavaScript to extract bookmarks
        const tweets = document.querySelectorAll('article[data-testid="tweet"]');
        let bookmarks = [];
        
        tweets.forEach(tweet => {
            const tweetText = tweet.querySelector('div[data-testid="tweetText"]')?.innerText || '';
            const tweetAuthor = tweet.querySelector('div[data-testid="User-Name"] a')?.innerText || '';
            const tweetUrl = tweet.querySelector('a[href*="/status/"]')?.href || '';
            
            // Extract tweet ID from the URL
            let tweetId = '';
            if (tweetUrl) {
                const urlParts = tweetUrl.split('/');
                const statusIndex = urlParts.indexOf('status');
                if (statusIndex !== -1 && statusIndex + 1 < urlParts.length) {
                    tweetId = urlParts[statusIndex + 1];
                }
            }
            
            bookmarks.push({
                text: tweetText,
                author: tweetAuthor,
                url: tweetUrl,
                id: tweetId,
            });
        });
        
        return bookmarks;
    """

# Function to scroll and extract all bookmarks
def extract_all_bookmarks(driver):
    all_bookmarks = []
    all_bookmarks_ids = set()
    while True:
        # Execute JavaScript to extract current bookmarks
        bookmarks_data = driver.execute_script(bookmarks_script)
        
        # for bookmark in bookmarks_data:
        #     all_bookmarks_ids.add(bookmark['id'])

        # If no new bookmarks were found, we've likely reached the end
        new_bookmarks = []
        for bookmark in bookmarks_data:
            if bookmark['id'] not in all_bookmarks_ids:
                new_bookmarks.append(bookmark)
                all_bookmarks_ids.add(bookmark['id'])
        if len(new_bookmarks) == 0:
            break
        # Add new bookmarks to our collection
        all_bookmarks.extend(new_bookmarks)
        print(len(all_bookmarks))
        print(bookmarks_data[0])
        
        # Scroll down to load more
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Wait for more content to load
        import time
        time.sleep(3)
    
    return all_bookmarks

def verify_login_status(driver, timeout=10):
    """
    Check login status by looking for profile avatar or username elements.
    
    Returns True if logged in, False otherwise.
    """
    driver.get("https://twitter.com/home")
    
    try:
        # Check for profile avatar which is only visible when logged in
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="AppTabBar_Profile_Link"]'))
        )
        return True
    except TimeoutException:
        return False


if __name__ == "__main__":
    username = os.environ.get("TWITTER_USERNAME")
    password = os.environ.get("TWITTER_PASSWORD")

    if not verify_login_status(driver): 
        # Wait for username field and enter credentials
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "text"))
        )
        username_field.send_keys(username)
        driver.find_element(By.XPATH, "//span[contains(text(), 'Dalej')]").click()

        # Handle password entry
        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "password"))
        )
        password_field.send_keys(password)
        driver.find_element(By.XPATH, "//span[contains(text(), 'Zaloguj się')]").click()

    # Wait for successful login
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "a[aria-label='Profile']"))
    )

    # Navigate to bookmarks
    driver.get("https://twitter.com/i/bookmarks")

    # Wait for bookmarks to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-testid='tweet']"))
    )


    import json

    # Extract all bookmarks
    all_bookmarks = extract_all_bookmarks(driver)

    # Save to JSON file
    with open('twitter_bookmarks.json', 'w', encoding='utf-8') as f:
        json.dump(all_bookmarks, f, ensure_ascii=False, indent=4)

    print(f"Successfully extracted {len(all_bookmarks)} bookmarks.")

    # Close the browser
    driver.quit()
