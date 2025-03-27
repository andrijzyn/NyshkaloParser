import os
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium import webdriver
from openpyxl import Workbook
from openpyxl.drawing.image import Image
import re

class AdParser:
    def __init__(self, min_price, max_price, geckodriver_path, banned_keywords, image_folder="images"):
        self.options = Options()
        self.options.add_argument("--headless")
        self.service = Service(geckodriver_path)
        self.driver = webdriver.Firefox(service=self.service, options=self.options)
        
        self.image_folder = image_folder
        os.makedirs(self.image_folder, exist_ok=True)
        
        self.seen_links = set()
        self.min_price = min_price
        self.max_price = max_price
        self.banned_keywords = banned_keywords
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

    def is_advertisement(self, title):
        """
        Функція для перевірки, чи є оголошення рекламним
        :param title: Назва оголошення
        :return: True, якщо оголошення рекламне, False в іншому випадку
        """
        title = title.upper()  # Перетворюємо на великий регістр для зручності порівняння
        for keyword in self.banned_keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', title):  # Перевірка на наявність ключового слова
                return True
        return False

    def parse_listings(self):
        ads = self.driver.find_elements(By.CLASS_NAME, "EntityList-item")
        listings = []
        ad_counter = 0  # Лічильник оголошень

        # Якщо не знайдено жодного оголошення на поточній сторінці, припиняємо збір даних
        if not ads:
            return listings, ad_counter

        for ad in ads:
            title = self.get_element_text(ad, By.CLASS_NAME, "entity-title")
            price = self.get_element_text(ad, By.CLASS_NAME, "price")
            link = self.get_element_attr(ad, By.TAG_NAME, "a", "href")
            img_url = self.get_element_attr(ad, By.TAG_NAME, "img", "src")

            if not title or not link or link in self.seen_links or self.is_advertisement(title):  # Перевірка на рекламу
                continue

            self.seen_links.add(link)
            img_filename = self.download_image(img_url, title) if img_url else None

            listings.append({
                "title": title,
                "price": price,
                "link": link,
                "image": img_filename
            })

            ad_counter += 1  # Інкрементуємо лічильник кожного разу, коли додається нове оголошення

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
    banned_keywords = [
        # Техніка та електроніка  
        "MOTOROLA", "SAMSUNG", "IPHONE", "XIAOMI", "PS4", "PS5", "XBOX", "TV", "LAPTOP", "PC", "COMPUTER",  
        "TABLET", "MONITOR", "HEADPHONES", "AUDIO", "GADGET", "CAMERA", "DRONE", "SMARTWATCH", "PRINTER",  

        # Автомобілі та запчастини  
        "TDI", "GOLF", "BMW", "AUDI", "MERCEDES", "FORD", "OPEL", "VOLKSWAGEN", "ŠKODA", "CAR", "VEHICLE",  
        "MOTOR", "ENGINE", "TURBO", "TRANSMISSION", "RIMS", "TIRES", "WHEELS", "OIL", "FUEL", "SUZUKI",
        "YAMAHA", "HONDA",

        # Побутові товари  
        "FURNITURE", "COUCH", "SOFA", "TABLE", "CHAIR", "WARDROBE", "BED", "MATTRESS", "KITCHEN",  
        "WASHING MACHINE", "FRIDGE", "MICROWAVE", "STOVE", "OVEN", "DISHWASHER",  

        # Мобільні тарифи та послуги  
        "PREPAID", "SIM CARD", "MOBILE PLAN", "INTERNET", "SUBSCRIPTION", "SERVICE", "PACKAGE",  

        # Знижки, акції, промо  
        "RATE", "NEO", "256GB", "NOVO", "NEW", "SALE", "DISCOUNT", "PROMO", "OFFER", "BLACK FRIDAY",  
        "CYBER MONDAY", "CLEARANCE", "SPECIAL PRICE", "ACTION", "BUNDLE", "FREE SHIPPING",  

        # Валюта, гроші, кредит  
        "EURO", "DOLLAR", "KUNA", "CREDIT", "LOAN", "FINANCE", "MONEY", "PAYMENT", "INSTALLMENT",  

        # Інші нецільові категорії  
        "MATRIX", "TICKET", "CONCERT", "EVENT", "VOUCHER", "GIFT CARD", "TOY", "BIKE", "SCOOTER",  
        "ELECTRIC SCOOTER", "GYM MEMBERSHIP", "TRAVEL", "VACATION", "HOTEL", "RESORT", "TENT", "CAMPING",
        "RALPH", "LAUREN", "PROROK"
    ]

    parser = AdParser(min_price, max_price, geckodriver_path, banned_keywords)

    # Запускаємо процес парсингу
    parser.start_driver()
    all_data, total_ads = parser.collect_data(pages=5)

    print(f"✅ Total ads collected: {total_ads}")

    # Зберігаємо результати в Excel
    parser.save_to_excel(all_data)

    # Закриваємо браузер
    parser.close_driver()
