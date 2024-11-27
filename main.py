import logging
import concurrent.futures
import threading
import sqlite3
from datetime import datetime
import os
import sys
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv


load_dotenv()

# Validate command-line arguments
if len(sys.argv) != 2:
    print("Usage: python3 main.py <current-year>")
    sys.exit()

# Configure logging for normal logs
log_file = f'fetch_log_{datetime.today().strftime("%Y-%m-%d")}.log'
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Configure logging for errors only
error_log_file = f'fetch_error_{datetime.today().strftime("%Y-%m-%d")}.log'
error_logger = logging.getLogger("error_logger")
error_logger.setLevel(logging.ERROR)
error_handler = logging.FileHandler(error_log_file, mode='a')
error_handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"))
error_logger.addHandler(error_handler)

# Get today's date
today = datetime.today().strftime("%Y-%m-%d")

# Delete the .db file if it exists
if os.path.exists(f'pes-people-{today}.db'):
    os.remove(f'pes-people-{today}.db')
    logging.info("Existing database file deleted.")

database_mutex = threading.Lock()

# URL and headers for the POST request
url = "https://www.pesuacademy.com/Academy/getStudentClassInfo"

headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'X-Csrf-Token': os.getenv('X_CSRF_TOKEN'),
    'Cookie': os.getenv('COOKIE'),
    'Accept': '*/*',
    'Origin': 'https://www.pesuacademy.com',
    'Referer': 'https://www.pesuacademy.com/Academy/',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
}

logging.info("Starting Fetch...")
current_year = int(sys.argv[1])


def fetchDataAndStore(prn):
    # Prepare data for the POST request
    data = {'loginId': prn}

    try:
        # Make POST request
        response = requests.post(url, headers=headers, data=data)
        response_text = response.text

        # Parse the response
        soup = BeautifulSoup(response_text, 'html.parser')
        tbody = soup.find('tbody', {'id': 'knowClsSectionModalTableDate'})

        # When class and section is not found,
        # the response is some bs that says 'class and section details
        # are not available'
        # no table is returned in this case.
        # So the above statement would throw an error.
        # If this is the case, we can move on from this PRN
        if tbody is None:
            return

        # Extract information from the first row
        first_row = tbody.find('tr')

        srn = first_row.find_all('td')[1].text
        name = first_row.find_all('td')[2].text
        semester = first_row.find_all('td')[3].text
        section = first_row.find_all('td')[4].text
        cycle = first_row.find_all('td')[5].text

        dept = first_row.find_all('td')[6].text

        # srn is of the form PES2UG22CS121.
        # We need to extract "CS" (index -5 to -3)
        dept_from_srn = srn[-5:-3]

        # AIML people still show up as under CSE Dept
        if (dept_from_srn == "AM" and semester != "Sem-1"):
            dept = "AIML"

        # the campus is mentioned in dept inside brackets
        # throw that out the window
        dept = dept.split("(")[0].strip()

        # Determine campus based on PRN
        campus = "RR" if prn[3] == '1' else "EC"

        # table name format: CAMPUS_SEMESTER_SECTION_DEPT_CYCLE
        # Format table name
        table_name = f"{campus}_{semester}_{section}_{dept}_{cycle}"
        table_name = table_name.replace(" ", "_").replace("-", "_").replace("/", "_").replace(
            "(", "_").replace(")", "_").replace(".", "_").replace("&", "_").replace(",", "_").lower()

        with database_mutex:
            sqliteConnection = sqlite3.connect(f'pes-people-{today}.db')
            cursor = sqliteConnection.cursor()
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS `{table_name}` (id INT PRIMARY KEY, prn TEXT, srn TEXT, name TEXT)")
            cursor.execute(
                f"INSERT INTO `{table_name}` (prn, srn, name) VALUES (?, ?, ?)", (prn, srn, name))
            sqliteConnection.commit()

        logging.info(f"Inserted {prn} into {table_name}")

    except Exception as e:
        # Log the error for this PRN
        error_logger.error(f"Error processing PRN {prn}: {e}")


# Thread pool for concurrent execution
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = []

    for campus in [2, 1]:
        for year in range(current_year - 4, current_year+1):
            # for every PRN from 0 ... 5999
            # although the real PRN is 5 digits, 6000 is enough in my experience
            # increase in the future if PES decides to hoard more people
            for prn_number in range(1, 6000):
                padded_prn_number = str(prn_number).zfill(5)
                prn = f"PES{campus}{year}{padded_prn_number}"
                futures.append(executor.submit(fetchDataAndStore, prn))

    for future in concurrent.futures.as_completed(futures):
        try:
            # Wait for result
            future.result()
        except Exception as e:
            # Log any errors during thread execution
            error_logger.error(f"Error in thread execution: {e}")
