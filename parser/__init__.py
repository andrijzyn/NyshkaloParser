import tomllib
from . import driver

driver = driver.initiate()
driver.get("https://www.njuskalo.hr/")

with open("config.toml", "rb") as f:
    config = tomllib.load(f)
