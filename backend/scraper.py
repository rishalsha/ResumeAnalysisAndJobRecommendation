import os
import time
import random
import logging
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from dotenv import load_dotenv

load_dotenv()

# --------------------------------------------------
# AI-driven improvement suggestion logic
# --------------------------------------------------
def analyze_scraper_logic(scraper_config):
    suggestions = {}

    if not scraper_config.get("headless"):
        suggestions["webdriver"] = "Enable headless mode."

    if not scraper_config.get("user_agent"):
        suggestions.setdefault("webdriver", "")
        suggestions["webdriver"] += " Set a custom user-agent."

    if scraper_config.get("credentials_hardcoded"):
        suggestions["login"] = "Use environment variables for credentials."

    if not scraper_config.get("captcha_handling"):
        suggestions.setdefault("login", "")
        suggestions["login"] += " Add CAPTCHA handling or manual alert."

    if not scraper_config.get("retry_logic"):
        suggestions["error_handling"] = "Add retry logic with backoff."

    return suggestions


# --------------------------------------------------
# WebDriver Singleton
# --------------------------------------------------
_driver_instance = None

def get_driver(user_agent=None):
    global _driver_instance
    if _driver_instance:
        return _driver_instance

    options = Options()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Headless only if needed
    # options.add_argument("--headless=new")

    if user_agent:
        options.add_argument(f"user-agent={user_agent}")

    service = Service(r"C:\ChromeDriver\chromedriver.exe")
    _driver_instance = webdriver.Chrome(service=service, options=options)
    return _driver_instance


# --------------------------------------------------
# Human typing
# --------------------------------------------------
def human_typing(element, text):
    for ch in text:
        element.send_keys(ch)
        time.sleep(random.uniform(0.05, 0.15))
    time.sleep(random.uniform(0.3, 0.6))


# --------------------------------------------------
# LinkedIn Login
# --------------------------------------------------
def linkedin_login(driver, email, password, max_retries=3, backoff_factor=1.5):
    if not email or not password:
        logging.error("Missing credentials.")
        return False

    def save_diagnostics(tag):
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        driver.save_screenshot(f"login_{tag}_{ts}.png")
        with open(f"login_{tag}_{ts}.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"Login attempt {attempt}")

            driver.get("https://www.linkedin.com/login")
            wait = WebDriverWait(driver, 30)

            email_el = wait.until(EC.presence_of_element_located((By.NAME, "session_key")))
            pass_el = wait.until(EC.presence_of_element_located((By.NAME, "session_password")))

            human_typing(email_el, email)
            human_typing(pass_el, password)

            pass_el.send_keys(Keys.RETURN)

            try:
                WebDriverWait(driver, 15).until(EC.url_contains("/feed"))
                logging.info("Login successful")
                return True
            except TimeoutException:
                if "checkpoint" in driver.current_url:
                    logging.warning("CAPTCHA detected")
                    save_diagnostics("captcha")
                    return False

                save_diagnostics("login_failed")

        except Exception as e:
            logging.error(f"Login error: {e}")
            save_diagnostics("exception")

        sleep_time = backoff_factor * (2 ** (attempt - 1)) + random.uniform(0, 1)
        logging.info(f"Retrying after {sleep_time:.1f}s")
        time.sleep(sleep_time)

    return False


# --------------------------------------------------
# MAIN
# --------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
    )

    EMAIL = os.getenv("LINKEDIN_EMAIL")
    PASSWORD = os.getenv("LINKEDIN_PASSWORD")

    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"

    driver = get_driver(UA)

    success = linkedin_login(driver, EMAIL, PASSWORD)

    if success:
        with open("linkedin_cookies.txt", "w") as f:
            f.write(str(driver.get_cookies()))
    else:
        driver.save_screenshot("final_failure.png")

    config = {
        "headless": False,
        "user_agent": True,
        "credentials_hardcoded": False,
        "captcha_handling": False,
        "retry_logic": True,
    }

    for k, v in analyze_scraper_logic(config).items():
        print(f"{k}: {v}")

    # driver.quit()
