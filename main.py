import pandas as pd
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium import webdriver

options = Options()
options.add_argument("--headless")
service = Service("/usr/bin/geckodriver")
driver = webdriver.Firefox(service=service, options=options)

excluded_word = ""
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

def download_image(url, filename):
    try:
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
            continue  # Пропускаємо дублі

        seen_links.add(link)

        img_filename = f"images/{title.replace(' ', '_')}.jpg" if img_url else None
        if img_url:
            download_image(img_url, img_filename)

        listings.append({
            "title": title,
            "price": price,
            "link": link,
            "image": img_filename
        })

    return listings

price = 200
all_data = []

for page in range(1, 10):
    url = f"https://www.njuskalo.hr/iznajmljivanje-stanova/zagreb?price[min]=150&price[max]={price}&resultsPerPage=25&page={page}"
    driver.get(url)

    data = parse_listings(driver)
    if not data:
        print("🚫 No more listings. Stopping.")
        break

    all_data.extend(data)
    print(f"✅ Data collected from page {page}")

driver.quit()

df = pd.DataFrame(all_data)
df.to_excel("njuskalo_listings.xlsx", index=False)
print("✅ Data saved in njuskalo_listings.xlsx")
