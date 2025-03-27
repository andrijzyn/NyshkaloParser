import os
import pandas as pd
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium import webdriver
from openpyxl import Workbook
from openpyxl.drawing.image import Image
from time import sleep

# Налаштування Selenium
options = Options()
options.add_argument("--headless")
service = Service("/usr/bin/geckodriver")
driver = webdriver.Firefox(service=service, options=options)

# Додаємо JavaScript для блокування реклами
block_ads_script = """
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

# Запуск JS скрипту для блокування реклами на сторінці
driver.execute_script(block_ads_script)

# Папка для збереження фото
image_folder = "images"
os.makedirs(image_folder, exist_ok=True)

# Сет для унікальних посилань (фільтр дублікатів)
seen_links = set()

def get_element_text(ad, by, value):
    try:
        return ad.find_element(by, value).text.strip()
    except:
        return None

def get_element_attr(ad, by, value, attr):
    try:
        return ad.find_element(by, value).get_attribute(attr)
    except:
        return None

def download_image(url, title):
    try:
        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)[:50]  # Безпечна назва файлу
        filename = os.path.join(image_folder, f"{safe_title}.jpg")
        img_data = requests.get(url, timeout=5).content
        with open(filename, "wb") as img_file:
            img_file.write(img_data)
        return filename
    except:
        return None

def parse_listings(driver):
    ads = driver.find_elements(By.CLASS_NAME, "EntityList-item")
    listings = []

    for ad in ads:
        title = get_element_text(ad, By.CLASS_NAME, "entity-title")
        price = get_element_text(ad, By.CLASS_NAME, "price")
        link = get_element_attr(ad, By.TAG_NAME, "a", "href")
        img_url = get_element_attr(ad, By.TAG_NAME, "img", "src")

        if not title or not link or link in seen_links:
            continue

        seen_links.add(link)
        img_filename = download_image(img_url, title) if img_url else None

        listings.append({
            "title": title,
            "price": price,
            "link": link,
            "image": img_filename
        })

    return listings

# Збір даних
max_price = 400
min_price = 300
all_data = []

for page in range(1, 10):
    url = f"https://www.njuskalo.hr/iznajmljivanje-stanova/zagreb?price[min]={min_price}&price[max]={max_price}&resultsPerPage=25&page={page}"
    driver.get(url)

    data = parse_listings(driver)

    if not data:
        print("🚫 No more listings. Stopping.")
        break

    all_data.extend(data)
    print(f"✅ Data collected from page {page}")

driver.quit()

# Створення Excel-файлу
excel_file = "njuskalo_listings.xlsx"
wb = Workbook()
wb.remove(wb.active)  # Видаляємо стандартний аркуш

for item in all_data:
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
