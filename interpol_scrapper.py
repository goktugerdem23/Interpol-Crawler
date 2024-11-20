from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
import requests
import pika
import time
import json
import os
# Global sayaçlar
count = 0
duplicate_count = 0


    


def wait_for_selenium():
    url = "http://selenium:4444/wd/hub/status"
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print("Selenium is ready!")
                break
        except requests.exceptions.RequestException:
            print("Waiting for Selenium to be ready...")
        time.sleep(10)

wait_for_selenium()


def send_to_rabbitMQ(message):
    try:
        connection_parameters = pika.ConnectionParameters('rabbitmq')
        connection = pika.BlockingConnection(connection_parameters)
        channel = connection.channel()
        channel.queue_declare('interpol-data')
        channel.basic_publish(exchange='', routing_key="interpol-data", body=message)
        print(f"{message} has been sent to queue")
        connection.close()
    except Exception as e:
        print(f"An error occurred while sending to RabbitMQ: {e}")


def generate_regex_patterns():
    letters = [chr(i) for i in range(ord('A'), ord('Z') + 1)]  
    patterns = []
    for first in letters:
        for second in letters:
            patterns.append(f"^{first}{second}.*")
    return patterns

def scrape_interpol_data(driver):
    global count, duplicate_count
    unique_data = set()

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    wanted = soup.find_all('div', class_='redNoticeItem')

    for person in wanted:
        try:
            name = person.find('a').text.strip()
            age = person.find_next('span', class_='age').text.strip()
            nationality = person.find_next('span', class_='nationalities').text.strip()
            img_tag = person.find('img')
            img_url = img_tag['src'] if img_tag else None

            if not (name and age and nationality):
                continue

            unique_key = (name, age, nationality)
            if unique_key in unique_data:
                duplicate_count += 1
            else:
                unique_data.add(unique_key)
                count += 1
                data = {
                    "Name": name,
                    "Age": age,
                    "Nationality": nationality,
                    "img_url": img_url
                }
                data_json = json.dumps(data)
                print(data)
                # sent_to_file(data_json)
                send_to_rabbitMQ(data_json)

        except Exception as e:
            print(f"Error occurred while scraping data: {e}")

    print(f"{count} unique persons have been recorded")
    print(f"{duplicate_count} duplicate data found")


def click_next_button(driver):
    try:
        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "nextElement"))
        )
        next_button.click()
        time.sleep(3)
        return True
    except (StaleElementReferenceException, NoSuchElementException, TimeoutException):
        print("Reached the last page or the next button is not clickable.")
        return False


def main():
    chrome_options = Options()
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--start-maximized")

    url = "https://www.interpol.int/en/How-we-work/Notices/Red-Notices/View-Red-Notices"
    driver = webdriver.Remote(
        command_executor="http://selenium:4444/wd/hub",
        options=chrome_options
    )
    driver.get(url)

    regex_patterns = generate_regex_patterns()
    age_ranges = [(0, 30), (31, 60), (61, 100)]

    global count, duplicate_count

    for regex_pattern in regex_patterns:
        for age_range in age_ranges:
            print(f"Scraping data with pattern: {regex_pattern}, and age range: {age_range}")

            try:
                name_filter = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[1]/div[6]/div/div[1]/div/div/form/div[2]/input"))
                )
                name_filter.clear()
                name_filter.send_keys(regex_pattern)

                min_age_filter = driver.find_element(By.XPATH, "/html/body/div[1]/div[1]/div[6]/div/div[1]/div/div/form/div[5]/input[1]")
                min_age_filter.clear()
                min_age_filter.send_keys(str(age_range[0]))

                max_age_filter = driver.find_element(By.XPATH, "/html/body/div[1]/div[1]/div[6]/div/div[1]/div/div/form/div[5]/input[2]")
                max_age_filter.clear()
                max_age_filter.send_keys(str(age_range[1]))

                filter_button = driver.find_element(By.NAME, "submit")
                filter_button.click()
                time.sleep(3)

                scrape_interpol_data(driver)
                while click_next_button(driver):
                    scrape_interpol_data(driver)

            except Exception as e:
                print(f"Error while filtering data: {e}")

    print(f"Scraping completed. Total unique records: {count}")
    print(f"Total duplicates: {duplicate_count}")
    driver.quit()

if __name__ == "__main__":
    main()
