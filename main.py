import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium import webdriver

options = Options()
options.add_argument("--headless")
service = Service("/usr/bin/geckodriver")
driver = webdriver.Firefox(service=service, options=options)


def get_element_text(ad, by, value):
    try:
        return ad.find_element(by, value).text.strip()
    except:
        return None


def get_element_attr(ad, by, value, attr):
    """Finds an element and returns its attribute if present, otherwise None."""
    try:
        return ad.find_element(by, value).get_attribute(attr)
    except:
        return None


def parse_listings(driver):
    ads = driver.find_elements(By.CLASS_NAME, "EntityList-item")
    listings = []

    for ad in ads:
        listing = {
            "title": get_element_text(ad, By.CLASS_NAME, "entity-title"),
            "price": get_element_text(ad, By.CLASS_NAME, "price"),
            "location": get_element_text(ad, By.CLASS_NAME, "location"),
            "link": get_element_attr(ad, By.TAG_NAME, "a", "href")
        }
        listings.append(listing)

    return listings


price = 450
page = 1
all_data = []

for page in range(1, 10):  # Limit to avoid an infinite loop
    url = f"https://www.njuskalo.hr/iznajmljivanje-stanova/zagreb?price%5Bmax%5D={price}&numberOfRooms%5Bmin%5D=studio-apartment&numberOfRooms%5Bmax%5D&resultsPerPage=25&page={page}"
    driver.get(url)

    data = parse_listings(driver)

    if not data:
        print("🚫 No more listings. Stopping.")
        break

    all_data.extend(data)
    print(f"✅ Data collected from page {page}")

else:
    print("⚠️ Maximum number of pages reached.")

driver.quit()

df = pd.DataFrame(all_data)
df.to_csv("njuskalo_listings.csv", index=False, encoding="utf-8")
print("✅ All data saved in njuskalo_listings.csv")

df = df.dropna(subset=["title", "price", "link"], how="any")
df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

formatted_list = [
    f"{row['title']}, {row['price']}, {row['link']}"
    for i, row in df.iterrows()
]

with open("cleaned_listings.txt", "w", encoding="utf-8") as f:
    f.write("\n\n".join(formatted_list))

print("✅ Data cleaned and saved in cleaned_listings.txt")
