import firebase_admin
from firebase_admin import firestore
from selenium import webdriver
import time
import pandas

from selenium.common.exceptions import StaleElementReferenceException

# open file / collection with site names ->
# add site names to collection ->
# loop through collection ->
# get all ignition data according to site name
# find last events + hives that failed ->
# add failed hives to collection ->
# loop through collection ->
# if hive received treatment, add to string for google form puls succeeded / if not puls - didn't succeed / if no data - no data received
#  start google form bot

cred_obj = firebase_admin.credentials.Certificate('service_account.json')
default_app = firebase_admin.initialize_app(cred_obj)

CURRENT_TIMESTAMP = 1646179200000
GOOGLE_FORM_LINK = "Google form link"
CHROME_DRIVER_PATH = "Chrome driver path"

sites = []
data = pandas.read_json("sites.json")
for site in data.to_dict().values():
    sites.append(site)

db = firestore.client()

driver = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH)
driver.get(GOOGLE_FORM_LINK)


def search(ignitions, device_id):
    ign_exists = False
    for ign in ignitions:
        if ign["timestamp"] > CURRENT_TIMESTAMP and ign["deviceID"] == device_id:
            ign_exists = True
    return ign_exists


def retrieve_ignitions_data(hive):
    ignitions = []
    doc_ref = db.collection("test_hives").document(hive).collection("ignitions")
    docs = doc_ref.stream()
    hive_ign_flag = "success"
    for ignition in docs:
        ign_data = ignition.to_dict()
        try:
            if ign_data["timestamp"] >= CURRENT_TIMESTAMP:
                ignitions.append(ign_data)
            for ign in ignitions:
                if ign["timestamp"] > CURRENT_TIMESTAMP and ign["delta"] < 2:
                    hive_ign_flag = -1
                elif ign["timestamp"] > CURRENT_TIMESTAMP and ign["delta"] >= 2:
                    hive_ign_flag = 1
                elif ign["timestamp"] == CURRENT_TIMESTAMP and ign["delta"] < 2 and not search(ignitions, ign["deviceID"]):
                    hive_ign_flag = 0
        except KeyError:
            continue
    return hive_ign_flag


def retrieve_hives_data(site):
    hives_success = []
    failed_hives = []
    no_data_hives = []
    doc_ref = db.collection('test_hives')
    docs = doc_ref.stream()
    for hive in docs:
        hive_data = hive.to_dict()
        # default global hives ids are with B, so don't need them, they are not on the field
        if site["id"] in hive_data["sites"] and hive_data["globalHiveId"][0] != "B":
            ignitions_data = retrieve_ignitions_data(hive_data["globalHiveId"])
            if ignitions_data == "success":
                continue
            else:
                if ignitions_data > 0:
                    hives_success.append(hive_data["globalHiveId"])
                elif ignitions_data < 0:
                    failed_hives.append(hive_data["globalHiveId"])
                elif ignitions_data == 0:
                    no_data_hives.append(hive_data["globalHiveId"])
    if len(hives_success) > 0 or len(failed_hives) > 0 or len(no_data_hives) > 0:
        result = "בוצע פולס מרחוק להתקנים שכשלו ב02:00 (3.1 ס""מ): "
        if len(hives_success) > 0:
            for hive_id in hives_success:
                result += hive_id + " "
            result += " - פולס הצליח "
        if len(failed_hives) > 0:
            for hive_id in failed_hives:
                result += hive_id + " "
            result += " - פולס לא הצליח "
        if len(no_data_hives) > 0:
            for hive_id in no_data_hives:
                result += hive_id + " "
            result += " - לא קיבלנו דאטה"
        select = driver.find_element_by_xpath("//*[@id='mG61Hd']/div[2]/div/div[2]/div[1]/div/div/div[2]/div/div[1]")
        select.click()
        time.sleep(2)
        options = driver.find_elements_by_css_selector('.vRMGwf')
        for i in options:
            try:
                if i.text == site["form_name"]:
                    i.click()
            except StaleElementReferenceException:
                continue
        time.sleep(2)
        select_employee = driver.find_element_by_xpath("//*[@id='mG61Hd']/div[2]/div/div[2]/div[2]/div/div/div[2]/div/div[1]")
        select_employee.click()
        time.sleep(2)
        options_employee = driver.find_elements_by_css_selector('.vRMGwf')
        [i.click() for i in options_employee if i.text == "קטרין"]
        time.sleep(2)
        address = driver.find_element_by_css_selector('.KHxj8b')
        checkbox = driver.find_element_by_css_selector('#i35 .fsHoPb')
        checkbox.click()
        time.sleep(2)
        address.send_keys(result)
        time.sleep(2)
        submit = driver.find_element_by_css_selector('.l4V7wb')
        submit.click()
        time.sleep(2)
        driver.refresh()


for site in sites:
    retrieve_hives_data(site)

time.sleep(2)
driver.close()