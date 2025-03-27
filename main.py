import os
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium import webdriver
from openpyxl import Workbook
import re

class AdParser:
    def __init__(self, min_price, max_price, geckodriver_path):
        self.options = Options()
        self.options.add_argument("--headless")
        self.service = Service(geckodriver_path)
        self.driver = webdriver.Firefox(service=self.service, options=self.options)
        
        self.seen_links = set()
        self.min_price = min_price
        self.max_price = max_price
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
        """Запуск браузера та блокування реклами"""
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
            print("No ads found.")
            return listings, ad_counter

        for ad in ads:
            price = self.get_element_text(ad, By.CLASS_NAME, "price")
            link = self.get_element_attr(ad, By.TAG_NAME, "a", "href")

            if not link or not link.startswith("https://www.njuskalo.hr/nekretnine/") or link in self.seen_links:
                continue

            self.seen_links.add(link)

            listings.append({
                "price": price,
                "link": link,
            })

            ad_counter += 1  

        return listings, ad_counter

    def collect_data(self, pages=10):
        all_data = []
        total_ads = 0  # Лічильник загальної кількості оголошень

        for page in range(1, pages + 1):
            url = f"https://www.njuskalo.hr/iznajmljivanje-stanova?geo[locationIds]=1248%2C1249%2C1250%2C1251%2C1252%2C1253&price[max]={self.max_price}&page={page}"
            self.driver.get(url)

            data, ad_count = self.parse_listings()

            if not data:
                print(f"🚫 No listings found on page {page}. Moving to the next page.")
                continue  # Перехід до наступної сторінки, навіть якщо поточна порожня

            all_data.extend(data)
            total_ads += ad_count  # Додаємо до загальної кількості оголошень

            print(f"✅ Data collected from page {page}")

        return all_data, total_ads

    def save_to_excel(self, data, excel_file="njuskalo_listings.xlsx"):
        """Збереження результатів у Excel"""
        wb = Workbook()
        ws = wb.active
        
        ws.append(["Price", "Link"])  

        for item in data:
            ws.append([item["price"], item["link"]])

        wb.save(excel_file)
        print(f"✅ Data saved in {excel_file}")

    def close_driver(self):
        """Закриття браузера"""
        self.driver.quit()


if __name__ == "__main__":
    min_price = 300
    max_price = 400
    geckodriver_path = "/usr/bin/geckodriver"

    parser = AdParser(min_price, max_price, geckodriver_path)

    # Запускаємо процес парсингу
    parser.start_driver()
    all_data, total_ads = parser.collect_data(pages=5)

    print(f"✅ Total ads collected: {total_ads}")

    # Зберігаємо результати в Excel
    parser.save_to_excel(all_data)

    # Закриваємо браузер
    parser.close_driver()