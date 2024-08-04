import os
import sys
import json
import asyncio
import aiohttp
import aiofiles
import time
import subprocess
from PIL import Image
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from requests.compat import urljoin
from bs4 import BeautifulSoup
import keyboard
import requests
from twocaptcha import TwoCaptcha
import psutil

# Determine the base path
base_path = (
    os.path.dirname(os.path.abspath(sys.executable))
    if getattr(sys, "frozen", False)
    else os.path.abspath(".")
)

# Set the path to the JSON file
json_file_path = os.path.join(base_path, "data.json")

# Open and read the JSON file
with open(json_file_path, "r") as file:
    data = json.load(file)
username = os.getlogin()
# Accessing data
email = data["Email"]
password = data["Password"]
centers = data["ApplicationCenter"]
service = data["ServiceType"]
applicant_type = data["ApplicantType"]
appointment = data["AppointmentType"]
f_name = data["FirstName"]
l_name = data["LastName"]
f_name2 = data["FirstName2"]
l_name2 = data["LastName2"]
api_key = "581459cf3d90ae165e53e551ec5e8881"
card = data["CardNumber"]
cvv = data["CVV"]
e_month = data["ExMonth"]
e_year = data["ExYear"]
passport = data["Passport"]

logged_in = False
profile_path = f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data"
path = "https://blsitalypakistan.com/account/login/"
driver = None
wait = None
short_wait = None


# Set up Chrome options

solver = TwoCaptcha(api_key)
def open_chrome():
    global driver, wait, short_wait

    # Close existing Chrome driver if it exists
    if driver:
        driver.quit()
        driver = None

    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={profile_path}")
    options.add_experimental_option("prefs", {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    })

    # Initialize the WebDriver with the options
    driver = webdriver.Chrome(options=options)

    # Initialize WebDriverWait
    wait = WebDriverWait(driver, 10)
    short_wait = WebDriverWait(driver, 3)



def close_chrome():
    """Closes all Chrome processes."""
    for process in psutil.process_iter(['pid', 'name']):
        try:
            if process.info['name'] == 'chrome.exe':
                process.terminate()
                print(f"Terminated Chrome process with PID {process.info['pid']}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def solve_captcha():
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')

    captcha_img_tag = soup.find('img', {'id': 'Imageid'})
    if not captcha_img_tag:
        # print('CAPTCHA image not found on the page')
        return None

    captcha_img_url = captcha_img_tag['src']

    # If the URL is relative, make it absolute by adding the base URL
    if not captcha_img_url.startswith('http'):
        captcha_img_url = requests.compat.urljoin(path, captcha_img_url)

    # Step 2: Download the CAPTCHA image
    img_response = requests.get(captcha_img_url)
    img = Image.open(BytesIO(img_response.content))

    # Save the image locally (optional, you can also keep it in memory)
    img_path = 'captcha.jpg'
    img.save(img_path)

    # Step 3: Send the image to 2Captcha for solving
    try:
        result = solver.normal(img_path)
    except Exception as e:
        print(f"Error solving CAPTCHA: {e}")
        return None
    else:
        print('solved: ' + str(result))
        return result['code']


async def log_in():
    global logged_in
    print(driver.current_url)
    if driver.current_url != path and driver.current_url == "https://blsitalypakistan.com/account/account_details":
        logged_in = True
        return
    elif driver.current_url != path and driver.current_url == "https://blsitalypakistan.com/":
        driver.get(path)
    try:
        captcha_code =  solve_captcha()
        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="form1"]/div[2]/input')
            )
        ).send_keys(email)
        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "/html/body/div[6]/div/div/div/div/div[2]/form/div[4]/input")
            )
        ).send_keys(password)
        if captcha_code:
            wait.until(
                EC.presence_of_element_located((By.ID, "captcha_code_reg"))
            ).send_keys(captcha_code)

        wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "/html/body/div[6]/div/div/div/div/div[2]/form/div[8]/button",
                )
            )
        ).click()

        # Check for incorrect CAPTCHA code and retry
        try:
            alert = WebDriverWait(driver,1).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.alert.alert-danger.alert-dismissable")
                )
            )
            if "Incorrect code !!!" in alert.text:
                driver.refresh()
                await log_in()
            else:
                logged_in = True
        except TimeoutException:
            logged_in = True

    except TimeoutException:
        if not logged_in:
            await log_in()

def ask_user_choice():
    print("Press 'q' to quit the program")
    print("Press 'r' to rerun the program")
    print("Press 's' to schedule the program")
    print("Waiting for your choice...")

    while True:
        if keyboard.is_pressed("q"):
            return "q"
        elif keyboard.is_pressed("r"):
            return "r"
        elif keyboard.is_pressed("s"):
            return "s"

def schedule_rerun():
    while True:
        try:
            minutes = float(
                input(
                    "Enter the number of minutes to wait before rerunning (e.g., 0.5 for half a minute): "
                ).strip()
            )
            if minutes <= 0:
                print("Please enter a positive number.")
                continue
            print(f"Scheduling the program to rerun in {minutes} minutes...")
            time.sleep(minutes * 60)
            break
        except ValueError:
            print("Invalid input. Please enter a valid number of minutes.")

def restart_program():
    try:
        executable = sys.executable
        script_path = sys.argv[0]
        subprocess.call([executable, script_path] + sys.argv[1:])
        sys.exit()  # Exit the current process
    except Exception as e:
        print(f"Error restarting the program: {e}")
        sys.exit(1)

async def appointment_reg():
    dropdown = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "valAppointmentType"))
    )

    # Create a Select object
    select = Select(dropdown)

    # Get all options in the dropdown
    options = select.options

    # Iterate through options and select the first one that is enabled
    for option in options:
        if option.is_enabled():
            select.select_by_visible_text(option.text)
            break
    select_element = driver.find_element(By.NAME, 'valApplicant[1][appointment_normal_time]')
    select = Select(select_element)
    select.select_by_index(0)  # Select the first option

    wait.until(
        EC.presence_of_element_located(
            (By.NAME, "valApplicant[1][first_name]")
        )
    ).send_keys(f_name)

    try:
        input_field = wait.until(
            EC.presence_of_element_located((By.NAME, "valApplicant[1][last_name]"))
        )
        # Use XPath to find the sibling input element)
        input_field.send_keys(l_name)
    except TimeoutException:
        print("Last name cannot be entered correctly, contact the developer")

    # Fill form for valApplicant[2]
    select_element = driver.find_element(By.NAME, 'valApplicant[2][appointment_normal_time]')
    select = Select(select_element)
    select.select_by_index(1)  # Select the first option

    wait.until(
        EC.presence_of_element_located(
            (By.NAME, "valApplicant[2][first_name]")
        )
    ).send_keys(f_name2)

    try:
        input_field = wait.until(
            EC.presence_of_element_located((By.NAME, "valApplicant[2][last_name]"))
        )
        # Use XPath to find the sibling input element
        input_field.send_keys(l_name2)
    except TimeoutException:
        print("Last name cannot be entered correctly, contact the developer")

    input_field = wait.until(
            EC.presence_of_element_located((By.NAME, "valApplicant[2][passport_number]"))
        )
        # Use XPath to find the sibling input element
    input_field.send_keys(passport)
    
    

# Use the Select class to interact with the dropdown


    wait.until(EC.element_to_be_clickable((By.ID, "agree"))).click()
    wait.until(EC.element_to_be_clickable((By.ID, "valBookNow"))).click()

    element = wait.until(
        EC.visibility_of_element_located(
            (
                By.XPATH,
                "/html/body/div[1]/div/div[2]/div[1]/form/div[5]/div[3]/div[1]/div[1]/input",
            )
        )
    )
    element.send_keys(card)

    dropdown = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "/html/body/div[1]/div/div[2]/div[1]/form/div[5]/div[3]/div[2]/div[1]",
            )
        )
    )
    dropdown.click()

    option_xpath = f"//ul[contains(@class, 'dropdown-content select-dropdown')]/li/span[text()='{e_month}']"
    option = wait.until(EC.element_to_be_clickable((By.XPATH, option_xpath)))
    option.click()

    dropdown = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "/html/body/div[1]/div/div[2]/div[1]/form/div[5]/div[3]/div[2]/div[2]",
            )
        )
    )
    dropdown.click()

    option_xpath = f"//ul[contains(@class, 'dropdown-content select-dropdown')]/li/span[text()='{e_year}']"
    option = wait.until(EC.element_to_be_clickable((By.XPATH, option_xpath)))
    option.click()

    # Validation code
    wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div[2]/div[1]/form/div[5]/div[3]/div[4]/div[1]/input"))).send_keys(cvv)
    # time.sleep(20)
    # Pay button
    wait.until(EC.element_to_be_clickable((By.ID, "btnPay"))).click()
    print("Appointment successfully booked")
    time.sleep(30000)
    return 1

async def main():
    global logged_in
    try:
        driver.get(path)
        
        await log_in()
        if logged_in:
            driver.execute_script("window.open('https://blsitalypakistan.com/bls_appmnt/bls-italy-appointment', '_blank');")
            driver.switch_to.window(driver.window_handles[1])
            for center in centers:
                Select(
                    wait.until(EC.element_to_be_clickable((By.ID, "valCenterLocationId")))
                ).select_by_visible_text(center)
                Select(
                    wait.until(EC.element_to_be_clickable((By.ID, "valCenterLocationTypeId")))
                ).select_by_visible_text(service)
                Select(
                    wait.until(EC.element_to_be_clickable((By.ID, "valAppointmentForMembers")))
                ).select_by_visible_text(applicant_type)
                success = False
                appointment_date_input = wait.until(
                    EC.element_to_be_clickable((By.ID, "valAppointmentDate"))
                )
                appointment_date_input.click()

                table = wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "table-condensed"))
                )
                available_dates = table.find_elements(By.CLASS_NAME, "label-available")
                if available_dates:
                    captcha_code = solve_captcha()
                    if captcha_code:
                        wait.until(
                            EC.presence_of_element_located((By.ID, "captcha_code_reg"))
                        ).send_keys(captcha_code)
                    available_dates[0].click()
                    await appointment_reg()
                else:
                    continue
        else:
            print("Login failed after multiple attempts.")

        return 1  # Successful execution

    except Exception as e:
        print(f"An error occurred: {e}")
        return 0  # Error occurred


def executor():
    while True:
        open_chrome()
        asyncio.run(main())
        close_chrome()
        time.sleep(10)


executor()




