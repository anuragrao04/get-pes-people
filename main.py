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

if (len(sys.argv) != 2):
    print("Usage: python3 main.py <current-year>")
    sys.exit()


today = datetime.today().strftime("%Y-%m-%d")

# delete the .db file if exists
if (os.path.exists(f'pes-people-{today}.db')):
    os.remove(f'pes-people-{today}.db')

database_mutex = threading.Lock()


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

print("Starting Fetch...")
current_year = int(sys.argv[1])


def fetchDataAndStore(prn):
    data = {
        'loginId': prn
    }

    response = requests.post(url, headers=headers, data=data)
    response_text = response.text
    soup = BeautifulSoup(response_text, 'html.parser')
    tbody = soup.find(
        'tbody', {'id': 'knowClsSectionModalTableDate'})
    # When class and section is not found,
    # the response is some bs that says 'class and section details
    # are not available'
    # no table is returned in this case.
    # So the above statement would throw an error.
    # If this is the case, we can move on from this PRN
    if (tbody is None):
        return

    first_row = tbody.find('tr')

    srn = first_row.find_all('td')[1].text
    name = first_row.find_all('td')[2].text
    semester = first_row.find_all('td')[3].text
    section = first_row.find_all('td')[4].text
    cycle = first_row.find_all('td')[5].text
    branch = first_row.find_all('td')[7].text
    if (prn[3] == '1'):
        campus = "RR"
    else:
        campus = "EC"

    # table name format: CAMPUS_SEMESTER_SECTION_BRANCH_CYCLE

    table_name = f"{campus}_{semester}_{section}_{branch}_{cycle}"
    # sanitize table name
    table_name = table_name.replace(" ", "_")
    table_name = table_name.replace("-", "_")
    table_name = table_name.replace("/", "_")
    table_name = table_name.replace("(", "_")
    table_name = table_name.replace(")", "_")
    table_name = table_name.replace(".", "_")
    table_name = table_name.replace("&", "_")

    with database_mutex:
        sqliteConnection = sqlite3.connect(f'pes-people-{today}.db')
        cursor = sqliteConnection.cursor()
        # if table doesn't exist, create it
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} (id INT PRIMARY KEY, prn TEXT, srn TEXT, name TEXT)")
        # the ID will be an auto incrementing integer. We don't need to increment it manually
        # that column is an alias to ROWID. See SQLITE Docs for more info
        cursor.execute(
            f"INSERT INTO {table_name} (prn, srn, name) VALUES (?, ?, ?)", (prn, srn, name))

        sqliteConnection.commit()

    print(f"Inserted {prn} into {table_name}")


with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = []

    # for every campus
    for campus in [1, 2]:
        # for every year
        for year in range(current_year-4, current_year+1):
            # for every PRN from 0 ... 7999
            # although the real PRN is 5 digits, 8000 is enough in my experience
            # increase in the future if PES decides to hoard more people
            for prn_number in range(0, 8000):
                # expand prn_number to 5 digits
                padded_prn_number = str(prn_number).zfill(5)
                prn = f"PES{campus}{year}{padded_prn_number}"
                futures.append(executor.submit(fetchDataAndStore, prn))

    for future in concurrent.futures.as_completed(futures):
        try:
            future.result()
        except Exception as e:
            print(f"Error processing: {e}")
