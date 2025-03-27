import os
import pandas as pd
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium import webdriver
from openpyxl import Workbook
from openpyxl.drawing.image import Image
import time

# Налаштування Selenium
options = Options()
options.add_argument("--headless")
service = Service("/usr/bin/geckodriver")
driver = webdriver.Firefox(service=service, options=options)

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

def download_image(url, folder, img_name):
    try:
        safe_img_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in img_name)[:50]
        filename = os.path.join(folder, f"{safe_img_name}.jpg")
        img_data = requests.get(url, timeout=5).content
        with open(filename, "wb") as img_file:
            img_file.write(img_data)
        return filename
    except:
        return None

def parse_listing_page(driver, link, title):
    driver.get(link)
    time.sleep(2)  # Даємо сторінці завантажитися
    
    image_elements = driver.find_elements(By.CLASS_NAME, "ClassifiedDetailGallery-sliderListItem--image")
    image_urls = [img.get_attribute("src") for img in image_elements if img.get_attribute("src")]

    listing_folder = os.path.join(image_folder, title[:30])
    os.makedirs(listing_folder, exist_ok=True)

    image_files = []
    for i, img_url in enumerate(image_urls):
        img_filename = download_image(img_url, listing_folder, f"{title[:30]}_{i+1}")
        if img_filename:
            image_files.append(img_filename)

    return image_files

def parse_listings(driver):
    ads = driver.find_elements(By.CLASS_NAME, "EntityList-item")
    listings = []

    for ad in ads:
        title = get_element_text(ad, By.CLASS_NAME, "entity-title")
        price = get_element_text(ad, By.CLASS_NAME, "price")
        link = get_element_attr(ad, By.TAG_NAME, "a", "href")

        if not title or not link or link in seen_links:
            continue

        seen_links.add(link)
        image_files = parse_listing_page(driver, link, title)

        listings.append({
            "title": title,
            "price": price,
            "link": link,
            "images": image_files
        })

    return listings

# Збір даних
max_price = 400
min_price = 300
all_data = []

for page in range(1, 10):
    url = f"https://www.njuskalo.hr/iznajmljivanje-stanova/zagreb?price%5Bmin%5D={min_price}&price%5Bmax%5D={max_price}&resultsPerPage=50&page={page}"
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

    # Додаємо всі фото
    for i, img_file in enumerate(item["images"]):
        if os.path.exists(img_file):
            img = Image(img_file)
            img.width, img.height = 200, 200  # Масштаб фото
            ws.add_image(img, f"A{5 + i*10}")  # Вставляємо з відступами

wb.save(excel_file)
print(f"✅ Data saved in {excel_file} with individual sheets")
