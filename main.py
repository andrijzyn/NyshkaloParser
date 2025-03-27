import os
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium import webdriver
from openpyxl import Workbook
from openpyxl.drawing.image import Image

class AdParser:
    def __init__(self, min_price, max_price, geckodriver_path, image_folder="images"):
        self.options = Options()
        self.options.add_argument("--headless")
        self.service = Service(geckodriver_path)
        self.driver = webdriver.Firefox(service=self.service, options=self.options)
        
        self.image_folder = image_folder
        os.makedirs(self.image_folder, exist_ok=True)
        
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

    def download_image(self, url, title):
        """Завантаження зображення"""
        try:
            safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)[:50]
            filename = os.path.join(self.image_folder, f"{safe_title}.jpg")
            img_data = requests.get(url, timeout=5).content
            with open(filename, "wb") as img_file:
                img_file.write(img_data)
            return filename
        except Exception as e:
            print(f"Failed to download image {url}: {e}")
            return None

    def parse_listings(self):
        """Парсинг оголошень зі сторінки"""
        ads = self.driver.find_elements(By.CLASS_NAME, "EntityList-item")
        listings = []

        for ad in ads:
            title = self.get_element_text(ad, By.CLASS_NAME, "entity-title")
            price = self.get_element_text(ad, By.CLASS_NAME, "price")
            link = self.get_element_attr(ad, By.TAG_NAME, "a", "href")
            
            # Перевірка, чи є основне зображення
            img_url = self.get_element_attr(ad, By.XPATH, ".//img[contains(@class, 'main-image') or contains(@class, 'primary-image')]", "src")
            if not img_url:
                img_url = self.get_element_attr(ad, By.TAG_NAME, "img", "src")

            if not title or not link or link in self.seen_links:
                continue

            self.seen_links.add(link)
            img_filename = None

            if img_url:
                img_filename = self.download_image(img_url, title)

            listings.append({
                "title": title,
                "price": price,
                "link": link,
                "image": img_filename
            })

        return listings

    def collect_data(self, pages=10):
        all_data = []
        for page in range(1, pages + 1):
            url = "https://www.njuskalo.hr/iznajmljivanje-stanova?geo[locationIds]=1248%2C1249%2C1250%2C1251%2C1252%2C1253&price[max]=400"
            self.driver.get(url)

            data = self.parse_listings()

            if not data:
                print("🚫 No more listings. Stopping.")
                break

            all_data.extend(data)
            print(f"✅ Data collected from page {page}")
        
        return all_data

    def save_to_excel(self, data, excel_file="njuskalo_listings.xlsx"):
        """Збереження результатів у Excel"""
        wb = Workbook()
        wb.remove(wb.active)  # Видаляємо стандартний аркуш

        for item in data:
            title = item["title"][:30]  # Назва аркуша має обмеження по довжині
            sheet_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)

            ws = wb.create_sheet(title=sheet_name)
            ws.append(["Title", item["title"]])
            ws.append(["Price", item["price"]])
            ws.append(["Link", item["link"]])

            # Додаємо фото
            if item["image"] and os.path.exists(item["image"]):
                img = Image(item["image"])
                img.width, img.height = 200, 200  # Масштаб фото
                ws.add_image(img, "A5")  # Вставляємо в комірку A5

        wb.save(excel_file)
        print(f"✅ Data saved in {excel_file} with individual sheets")

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
    all_data = parser.collect_data(pages=10)

    # Зберігаємо результати в Excel
    parser.save_to_excel(all_data)

    # Закриваємо браузер
    parser.close_driver()