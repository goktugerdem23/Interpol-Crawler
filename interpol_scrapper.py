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

# Global counters for unique and duplicate records
count = 0
duplicate_count = 0

# Function to wait until Selenium Grid is ready for use
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

# Function to send data to RabbitMQ
def send_to_rabbitMQ(message):
    try:
        # Define RabbitMQ connection parameters
        connection_parameters = pika.ConnectionParameters('rabbitmq')
        connection = pika.BlockingConnection(connection_parameters)
        channel = connection.channel()
        
        # Declare the queue to ensure it exists
        channel.queue_declare('interpol-data')
        
        # Publish the message to the queue
        channel.basic_publish(exchange='', routing_key="interpol-data", body=message)
        print(f"{message} has been sent to queue")
        connection.close()
    except Exception as e:
        print(f"An error occurred while sending to RabbitMQ: {e}")

# Function to generate regex patterns for filtering names
def generate_regex_patterns():
    letters = [chr(i) for i in range(ord('A'), ord('Z') + 1)]  # Generate all uppercase letters
    patterns = []
    for first in letters:
        for second in letters:
            patterns.append(f"^{first}{second}.*")  # Create patterns like ^AA.*, ^AB.*, etc.
    return patterns

# Function to scrape data from the Interpol Red Notices page
def scrape_interpol_data(driver):
    global count, duplicate_count
    unique_data = set()  # Set to store unique records and prevent duplicates

    # Parse the page source using BeautifulSoup
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    
    # Find all items with the class 'redNoticeItem'
    wanted = soup.find_all('div', class_='redNoticeItem')

    # Loop through each person data found
    for person in wanted:
        try:
            # Extract person's details
            name = person.find('a').text.strip()
            age = person.find_next('span', class_='age').text.strip()
            nationality = person.find_next('span', class_='nationalities').text.strip()
            img_tag = person.find('img')
            img_url = img_tag['src'] if img_tag else None

            # Skip if any essential detail is missing
            if not (name and age and nationality):
                continue

            # Create a unique key based on name, age, and nationality
            unique_key = (name, age, nationality)
            if unique_key in unique_data:
                duplicate_count += 1
            else:
                unique_data.add(unique_key)
                count += 1
                
                # Prepare the data as a JSON object
                data = {
                    "Name": name,
                    "Age": age,
                    "Nationality": nationality,
                    "img_url": img_url
                }
                data_json = json.dumps(data)
                print(data)
                
                # Send the data to RabbitMQ
                send_to_rabbitMQ(data_json)

        except Exception as e:
            print(f"Error occurred while scraping data: {e}")

    print(f"{count} unique persons have been recorded")
    print(f"{duplicate_count} duplicate data found")

# Function to click the "Next" button and navigate to the next page
def click_next_button(driver):
    try:
        # Wait for the 'Next' button to be clickable
        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "nextElement"))
        )
        next_button.click()  # Click the button
        time.sleep(3)
        return True
    except (StaleElementReferenceException, NoSuchElementException, TimeoutException):
        print("Reached the last page or the next button is not clickable.")
        return False

# Main function to orchestrate the scraping process
def main():
    # Configure Chrome WebDriver options
    chrome_options = Options()
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--start-maximized")

    # URL of the Interpol Red Notices page
    url = "https://www.interpol.int/en/How-we-work/Notices/Red-Notices/View-Red-Notices"
    
    # Set up the Selenium WebDriver to use the remote Selenium Grid
    driver = webdriver.Remote(
        command_executor="http://selenium:4444/wd/hub",
        options=chrome_options
    )
    driver.get(url)

    # Generate regex patterns for name filters and define age ranges
    regex_patterns = generate_regex_patterns()
    age_ranges = [(0, 30), (31, 60), (61, 100)]  # Age groups for filtering

    global count, duplicate_count

    # Loop through each combination of name pattern and age range
    for regex_pattern in regex_patterns:
        for age_range in age_ranges:
            print(f"Scraping data with pattern: {regex_pattern}, and age range: {age_range}")

            try:
                # Apply filters on the webpage
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

                # Scrape data from the current page and navigate through pagination
                scrape_interpol_data(driver)
                while click_next_button(driver):
                    scrape_interpol_data(driver)

            except Exception as e:
                print(f"Error while filtering data: {e}")

    print(f"Scraping completed. Total unique records: {count}")
    print(f"Total duplicates: {duplicate_count}")
    driver.quit()

# Run the main function when the script is executed
if __name__ == "__main__":
    main()
