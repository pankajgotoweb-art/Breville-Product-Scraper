import os
import time
import random
import pandas as pd

from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- Configuration ---
INPUT_FILE = r"D:\Pankaj Data\000000000\2025\June\18\Input File\breville-LINK.xlsx"
OUTPUT_FOLDER = r"D:\Pankaj Data\000000000\2025\June\18\output File"
OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, "breville_scraped_output.xlsx")

MAX_RETRIES = 2
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- Read Input ---
df = pd.read_excel(INPUT_FILE)

# --- Selenium Setup ---
options = webdriver.ChromeOptions()
options.add_argument('--start-maximized')
options.page_load_strategy = 'eager'

driver = webdriver.Chrome(
    service=ChromeService(ChromeDriverManager().install()),
    options=options
)
driver.set_page_load_timeout(60)
wait = WebDriverWait(driver, 10)
actions = ActionChains(driver)

# --- Helper Functions ---
def safe_get(url: str):
    for attempt in range(1, MAX_RETRIES + 2):
        try:
            driver.get(url)
            human_scroll()
            return
        except TimeoutException:
            print(f"[!] Attempt {attempt} timed out for {url!r}, stopping load...")
            driver.execute_script("window.stop();")
            time.sleep(1.5 * attempt)
    raise TimeoutException(f"Failed to load {url!r} after {MAX_RETRIES+1} attempts")

def human_scroll():
    scroll_height = driver.execute_script("return document.body.scrollHeight")
    for y in range(0, scroll_height, random.randint(200, 400)):
        driver.execute_script(f"window.scrollTo(0, {y})")
        time.sleep(random.uniform(0.3, 0.8))
    time.sleep(random.uniform(0.5, 1.5))

def get_text(xpath: str) -> str:
    try:
        return driver.find_element(By.XPATH, xpath).text.strip()
    except NoSuchElementException:
        return ""

def get_html(xpath: str) -> str:
    try:
        return driver.find_element(By.XPATH, xpath).get_attribute("innerHTML").strip()
    except NoSuchElementException:
        return ""

def get_all_images() -> List[str]:
    for list_id in ["splide01-list", "splide03-list"]:
        try:
            imgs = driver.find_elements(By.XPATH, f'//ul[@id="{list_id}"]//img')
            if imgs:
                return [img.get_attribute("src") for img in imgs if img.get_attribute("src")]
        except NoSuchElementException:
            continue
    return []

def get_all_links(xpath: str) -> List[Dict]:
    try:
        els = driver.find_elements(By.XPATH, xpath)
        return [{"text": el.text.strip(), "href": el.get_attribute("href")} for el in els]
    except NoSuchElementException:
        return []

def get_all_teaser_html() -> str:
    try:
        container = driver.find_element(By.XPATH, '//div[@class="xps-teaser__content"]').find_element(By.XPATH, "..")
        sibling_divs = container.find_elements(By.XPATH, './*')
        return "\n\n".join(el.get_attribute("outerHTML") for el in sibling_divs if el.tag_name.lower() == "div")
    except Exception:
        return ""

# --- Main Scraping Logic ---
results = []
retry_list = []
start_time = time.time()

try:
    for idx, row in df.iterrows():
        url = row.get("URL", "").strip()
        input_title = row.get("Title", "").strip()
        print(f"[{idx+1}/{len(df)}] Loading: {url}")

        try:
            safe_get(url)
        except TimeoutException as e:
            print(f"  ✗ {e}")
            retry_list.append(url)
            continue

        time.sleep(random.uniform(2, 4))

        scraped = {
            "Input Title": input_title,
            "URL": url,
            "Title": get_text("//h1"),
            "Price": get_text('//div[@class="pdp-productPrice"]'),
            "Color Text": get_text('//p[@class="xps-text xps-text-p3-bold pdp-atc-controls__color"]'),
            "Description Text": get_text('//div[@class="xps-card-tile xps-card-tile-content-center"]'),
            "Description HTML": get_html('//div[@class="xps-card-tile xps-card-tile-content-center"]'),
            "Specification Text": get_text('//div[@class="xps-product-specifications"]'),
            "Specification HTML": get_html('//div[@class="xps-product-specifications"]'),
            "Teaser HTML": get_all_teaser_html(),
            "Images": get_all_images(),
            "Support Docs": get_all_links('//a[@class="xps-support-doc-item-link"]'),
        }

        try:
            swatches = driver.find_elements(By.XPATH, '//div[@class="xps-swatchpicker-container"]//button')
            models = []
            for sw in swatches:
                try:
                    driver.execute_script("arguments[0].click();", sw)
                    time.sleep(1)
                    models.append(get_text('//div[@class="pdp-atc-controls-model-section"]'))
                except Exception:
                    continue
            scraped["Swatch Model Sections"] = models
        except Exception:
            scraped["Swatch Model Sections"] = []

        results.append(scraped)
        print(f"  ✓ Scraped: {input_title or url}")

    pd.DataFrame(results).to_excel(OUTPUT_FILE, index=False)
    print(f"→ Saved all scraped results: {len(results)} rows")

    if retry_list:
        pd.DataFrame({"Failed URLs": retry_list})\
            .to_excel(os.path.join(OUTPUT_FOLDER, "breville_failed_urls.xlsx"), index=False)
        print(f"⚠️ {len(retry_list)} URLs failed; see 'breville_failed_urls.xlsx'")

    print(f"\n✅ Scraping completed in {round((time.time() - start_time)/60, 2)} minutes.")

finally:
    driver.quit()
