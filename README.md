Breville Product Scraper (Python + Selenium)
This is a simple automation script I built to scrape product details from Breville’s website. The tool reads a list of product URLs from an Excel file, opens each page using Selenium, collects important information, and saves everything back into a new Excel sheet.
I created this to make repeated data collection faster and more accurate, especially when working with long lists of product pages.
________________________________________
What the script does
•	Reads URLs from an Excel file
•	Opens each Breville product page
•	Collects:
o	Product title
o	Price
o	Description
o	Specifications
o	Teaser text
o	Product images
o	Support documents
o	Swatch model variations
•	Handles multi-page sections
•	Adds random human-like delays
•	Retries failed pages
•	Saves final output to Excel
•	Creates a separate file for failed URLs
________________________________________
Technologies Used
•	Python
•	Selenium WebDriver
•	Pandas
•	Webdriver Manager
•	Excel Automation
________________________________________
How to Run
1.	Install the required packages:
2.	pip install -r requirements.txt
3.	Update the input and output file paths in the script.
4.	Run the script:
5.	python breville_scraper.py
6.	The scraped data will be saved in an Excel file inside your output folder.
________________________________________
Input File Format
Your Excel file should have a column named:
•	URL
•	(Optional) Title
Each row represents a product page you want to scrape.
________________________________________
Output
•	breville_scraped_output.xlsx – All extracted product data
•	breville_failed_urls.xlsx – Any URLs that failed after retries
________________________________________
Why I Built This
I often deal with product data in my work, and collecting information manually from multiple pages is time-consuming. This script helps automate that process and makes the workflow easier, especially when working with bulk data.
