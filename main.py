import os
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium import webdriver
from openpyxl import Workbook, load_workbook
import re
from datetime import datetime

class AdParser:
    def __init__(self, min_price, max_price, max_square, geckodriver_path, save_dir="data"):
        self.options = Options()
        self.options.add_argument("--headless")
        self.service = Service(geckodriver_path)
        self.driver = webdriver.Firefox(service=self.service, options=self.options)
        
        self.seen_links = set()
        self.min_price = min_price
        self.max_price = max_price
        self.max_square = max_square
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
        
        self.block_ads_script = """
            var adSelectors = [
                'iframe[src*="amazon-adsystem.com"]',
                'iframe[src*="googlesyndication.com"]',
                'iframe[src*="googletagmanager.com"]',
                'iframe[src*="midas-network.com"]',
                'iframe[src*="privacy-center.org"]',
                'img[src*="defractal.com"]',
                'div[class*="ad"]',
                'script[src*="dotmetrics.net"]'
            ];
            adSelectors.forEach(function(selector) {
                var ads = document.querySelectorAll(selector);
                ads.forEach(function(ad) {
                    ad.remove();
                });
            });
        """
    
    def start_driver(self):
        self.driver.get("https://www.njuskalo.hr")
        self.driver.execute_script(self.block_ads_script)

    def get_element_text(self, ad, by, value):
        try:
            return ad.find_element(by, value).text.strip()
        except:
            return None

    def get_element_attr(self, ad, by, value, attr):
        try:
            return ad.find_element(by, value).get_attribute(attr)
        except:
            return None

    def parse_listings(self):
        ads = self.driver.find_elements(By.CLASS_NAME, "EntityList-item")
        listings = []
        ad_counter = 0  

        if not ads:
            return listings, ad_counter

        for ad in ads:
            price = self.get_element_text(ad, By.CLASS_NAME, "price")
            link = self.get_element_attr(ad, By.TAG_NAME, "a", "href")

            if not link or not link.startswith("https://www.njuskalo.hr/nekretnine/") or link in self.seen_links:
                continue

            self.seen_links.add(link)
            listings.append({"price": price, "link": link})
            ad_counter += 1  

        return listings, ad_counter

    def collect_data(self, pages=10):
        all_data = []
        total_ads = 0
        empty_pages = 0

        previous_links = self.load_previous_data()  # Отримуємо посилання з попереднього запуску

        for page in range(1, pages + 1):
            url = f"https://www.njuskalo.hr/iznajmljivanje-stanova?geo[locationIds]=1248%2C1249%2C1250%2C1251%2C1252%2C1253&price[max]={self.max_price}&page={page}&livingArea[max]={self.max_square}"
            self.driver.get(url)

            data, ad_count = self.parse_listings()

            if not data:
                empty_pages += 1
                if empty_pages >= 2:
                    break
                continue

            # Фільтруємо тільки унікальні оголошення
            unique_data = [ad for ad in data if ad["link"] not in previous_links]
            unique_count = len(unique_data)

            all_data.extend(unique_data)
            print(f"✅ Page {page}: {unique_count} unique listings found")

            total_ads += unique_count
            empty_pages = 0

        return all_data, total_ads

    def get_latest_file(self):
        files = [f for f in os.listdir(self.save_dir) if f.endswith(".xlsx")]
        if not files:
            return None
        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.save_dir, x)), reverse=True)
        return os.path.join(self.save_dir, files[0])

    def load_previous_data(self):
        """Завантажує унікальні посилання з останнього збереженого файлу"""
        last_file = self.get_latest_file()
        if not last_file:
            return set()
        
        wb = load_workbook(last_file)
        ws = wb.active
        
        return {row[1] for row in ws.iter_rows(min_row=2, values_only=True) if row[1]}

    def save_to_excel(self, data):
        date_str = datetime.now().strftime("%d %B_%H-%M")
        filename = f"njuskalo_listings {date_str}.xlsx"
        file_path = os.path.join(self.save_dir, filename)
        
        previous_links = self.load_previous_data()
        unique_data = [item for item in data if item["link"] not in previous_links]
        
        if not unique_data:
            print("✅ No new unique listings found.")
            return
        
        wb = Workbook()
        ws = wb.active
        ws.append(["Price", "Link"])
        
        for item in unique_data:
            ws.append([item["price"], item["link"]])
        
        wb.save(file_path)
        print(f"✅ Data saved in {file_path}")

    def close_driver(self):
        self.driver.quit()

if __name__ == "__main__":
    min_price, max_price, max_square = 300, 400, 45
    geckodriver_path = "/usr/bin/geckodriver"
    
    parser = AdParser(min_price, max_price, max_square, geckodriver_path)
    
    parser.start_driver()
    all_data, total_ads = parser.collect_data()
    print(f"✅ Total ads collected: {total_ads}")
    
    parser.save_to_excel(all_data)
    parser.close_driver()