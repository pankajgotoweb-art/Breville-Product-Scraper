"""
breville_scraper.py
Purpose: Read product URLs from an Excel file and scrape product details from Breville product pages.
Author: Pankaj Kumar
Date: 2025-06-18
Usage: python breville_scraper.py --input input.xlsx --output out.xlsx
"""

import os
import time
import random
import argparse
import logging
from typing import List, Dict, Any
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# ---- Defaults / CONFIG ----
DEFAULT_MAX_RETRIES = 2
BATCH_SAVE_SIZE = 20  # auto-save after this many rows

# ---- Logging ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ---- Helpers ----
def setup_driver() -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    opts.add_argument("--start-maximized")
    opts.page_load_strategy = "eager"
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=opts
    )
    driver.set_page_load_timeout(60)
    return driver

def human_scroll(driver: webdriver.Chrome) -> None:
    """Scroll a page in small steps to ensure lazy-loaded content appears."""
    try:
        height = driver.execute_script("return document.body.scrollHeight")
        step = random.randint(200, 400)
        for y in range(0, height, step):
            driver.execute_script(f"window.scrollTo(0, {y})")
            time.sleep(random.uniform(0.25, 0.7))
        time.sleep(random.uniform(0.5, 1.0))
    except WebDriverException:
        logger.debug("Scrolling failed; continuing.")

def safe_get(driver: webdriver.Chrome, url: str, max_retries: int = DEFAULT_MAX_RETRIES) -> None:
    """Navigate to URL with a small retry-on-timeout strategy."""
    for attempt in range(1, max_retries + 2):
        try:
            driver.get(url)
            human_scroll(driver)
            return
        except TimeoutException:
            logger.warning("Attempt %d timed out for %s; stopping load and retrying...", attempt, url)
            driver.execute_script("window.stop();")
            time.sleep(1.5 * attempt)
    raise TimeoutException(f"Failed to load {url} after {max_retries+1} attempts")

def safe_find_text(driver: webdriver.Chrome, xpath: str, timeout: float = 4.0) -> str:
    """Try explicit wait for element then return text or empty string."""
    try:
        wait = WebDriverWait(driver, timeout)
        el = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        return el.text.strip()
    except Exception:
        # fallback: try direct find (faster if element already present), otherwise return ""
        try:
            return driver.find_element(By.XPATH, xpath).text.strip()
        except Exception:
            return ""

def get_all_images(driver: webdriver.Chrome, xpath: str) -> List[str]:
    try:
        imgs = driver.find_elements(By.XPATH, f"{xpath}//img")
        return [img.get_attribute("src") for img in imgs if img.get_attribute("src")]
    except Exception:
        return []

def process_row(driver: webdriver.Chrome, row: pd.Series) -> Dict[str, Any]:
    url = str(row.get("URL", "")).strip()
    input_title = str(row.get("Title", "")).strip()
    logger.info("Processing: %s", url)

    scraped = {
        "Input Title": input_title,
        "URL": url,
        "Title": "",
        "Price": "",
        "Color Text": "",
        "Description Text": "",
        "Specification Text": "",
        "Teaser Text": "",
        "Images": [],
        "Support Docs": [],
        "Swatch Model Sections": []
    }

    try:
        safe_get(driver, url)
    except TimeoutException as e:
        logger.error("Timeout loading %s: %s", url, e)
        raise

    time.sleep(random.uniform(1.0, 2.5))  # short pause after load

    scraped["Title"] = safe_find_text(driver, "//h1")
    scraped["Price"] = safe_find_text(driver, '//div[@class="pdp-productPrice"]')
    scraped["Color Text"] = safe_find_text(driver, '//p[@class="xps-text xps-text-p3-bold pdp-atc-controls__color"]')
    scraped["Description Text"] = safe_find_text(driver, '//div[@class="xps-card-tile xps-card-tile-content-center"]')
    scraped["Specification Text"] = safe_find_text(driver, '//div[@class="xps-product-specifications"]')
    scraped["Teaser Text"] = safe_find_text(driver, '//div[@class="xps-teaser__content"]')
    scraped["Images"] = get_all_images(driver, '//ul[@id="splide03-list"]')

    # Support docs (link + text)
    try:
        links = driver.find_elements(By.XPATH, '//a[@class="xps-support-doc-item-link"]')
        scraped["Support Docs"] = [{"text": l.text.strip(), "href": l.get_attribute("href")} for l in links if l.get_attribute("href")]
    except Exception:
        scraped["Support Docs"] = []

    # Swatch handling
    try:
        swatches = driver.find_elements(By.XPATH, '//div[@class="xps-swatchpicker-container"]//button')
        models = []
        for sw in swatches:
            try:
                driver.execute_script("arguments[0].click();", sw)
                time.sleep(0.8)
                models.append(safe_find_text(driver, '//div[@class="pdp-atc-controls-model-section"]'))
            except Exception:
                continue
        scraped["Swatch Model Sections"] = models
    except Exception:
        scraped["Swatch Model Sections"] = []

    return scraped

def save_results(results: List[Dict[str, Any]], path: str) -> None:
    """Save results to Excel; overwrite intentionally for simplicity."""
    pd.DataFrame(results).to_excel(path, index=False)
    logger.info("Saved %d rows to %s", len(results), path)

# ---- Main runnable ----
def main(args):
    os.makedirs(args.output_folder, exist_ok=True)
    driver = setup_driver()
    results = []
    failed = []
    df = pd.read_excel(args.input_file)

    try:
        for idx, row in df.iterrows():
            try:
                scraped = process_row(driver, row)
                results.append(scraped)
            except Exception as e:
                url = str(row.get("URL", ""))
                failed.append(url)
                logger.exception("Failed to scrape %s", url)

            # periodic save
            if (idx + 1) % args.batch_size == 0:
                save_results(results, args.output_file)

        # final save
        save_results(results, args.output_file)

        if failed:
            pd.DataFrame({"Failed URLs": failed}).to_excel(os.path.join(args.output_folder, "failed_urls.xlsx"), index=False)
            logger.warning("There were %d failed URLs. See failed_urls.xlsx", len(failed))

    finally:
        driver.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Breville product scraper")
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output-folder", required=True)
    parser.add_argument("--output-file", default=None)
    parser.add_argument("--batch-size", type=int, default=BATCH_SAVE_SIZE)
    parsed = parser.parse_args()

    output_file = parsed.output_file or os.path.join(parsed.output_folder, "breville_scraped_output.xlsx")
    parsed.output_file = output_file
    main(parsed)