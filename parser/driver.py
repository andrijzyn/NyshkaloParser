from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options


def initiate():
    options = Options()
    options.add_argument("--headless")
    options.binary_location = '/opt/waterfox/waterfox'

    service = Service('/usr/bin/geckodriver')

    return webdriver.Firefox(service=service, options=options)
