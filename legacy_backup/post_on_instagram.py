import shutil
import traceback
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from automation import v1_generate_prompts, check_if_automatic1111_is_active, close_automatic1111, get_driver, \
    get_location
from time import sleep
from utils import get_gspread_client, send_messages
from datetime import datetime
import os
import pyperclip

driver = None

options = uc.ChromeOptions()
gsheet = get_gspread_client()


def post_on_instagram(image_urls, caption, location):
    global driver
    i = 0
    # download the image locally
    downloaded_urls = []
    for img_url in image_urls:
        res = requests.get(img_url, stream=True)
        if res.status_code == 200:
            with open(f"/Users/rikenshah/Desktop/Fun/insta-model/temp{i}.png", 'wb') as f:
                shutil.copyfileobj(res.raw, f)
                downloaded_urls.append(f"/Users/rikenshah/Desktop/Fun/insta-model/temp{i}.png")
                print('Image successfully Downloaded: ', img_url)
                i += 1
        else:
            print(f"Failed to download {img_url}")

    if driver is None:
        driver = get_driver()
        # driver = uc.Chrome(
        #     options=options, user_data_dir=os.getcwd() + "/profile"
        # )
        driver.get("https://www.instagram.com/aashvithemodel")
    else:
        driver.tab_new("https://www.instagram.com/aashvithemodel")
    sleep(10)
    driver.find_element(By.XPATH, "//div[text()='Create']").click()
    sleep(2)
    driver.find_element(By.XPATH,
                        "//form/input[@accept='image/jpeg,image/png,image/heic,image/heif,video/mp4,video/quicktime']").send_keys(
        "\n".join(downloaded_urls))
    sleep(5)
    driver.find_element(By.XPATH, "//div[text()='Next']").click()
    sleep(1.2)
    driver.find_element(By.XPATH, "//div[text()='Next']").click()
    sleep(.9)
    driver.find_element(By.XPATH, "//div[@aria-label='Write a caption...']").click()
    sleep(1)
    caption_element = driver.find_element(By.XPATH,
                                          "//div[@aria-label='Write a caption...']")
    pyperclip.copy(caption)
    caption_element.send_keys(Keys.COMMAND, "v")
    sleep(4)
    # driver.find_element(By.XPATH, "//div[@aria-label='Write a caption...']")
    # sleep(1)
    caption_element.send_keys(Keys.ENTER)
    sleep(2)
    driver.find_element(By.XPATH, "//span[text()='Accessibility']").click()
    sleep(1.2)
    driver.find_element(By.XPATH, "//*[@placeholder='Write alt text...']").send_keys(
        f"Aashvi at {location}")
    sleep(1)
    driver.find_element(By.XPATH, "//*[@name='creation-location-input']").send_keys(location)
    sleep(4)
    driver.find_element(By.XPATH, f"//span[contains(text(),'{location}')]").click()
    sleep(2)
    driver.find_element(By.XPATH, "//div[text()='Share']").click()
    print(f"Successfully post {image_urls} on instagram")
    sleep(20)


def scheduled_posts_on_instagram():
    content = gsheet.get_all_records(value_render_option="FORMULA")
    posted_on_instagram = gsheet.find('posted_on_instagram')
    group_id = ""
    image_urls = []
    caption = ""
    location = ""
    start_index = None
    end_index = None
    indexes = []
    for row in content:
        if row['index'] == '':
            break
        if row['approved'] == 'y' and row['posted_on_instagram'] == '' and row['type'] == "posts" and (
                row["group_id"] == group_id or group_id == ""):
            if row["image"] == "" or row["caption"] == "" or row["location"] == "" or row["group_id"] == "":
                print(f"Missing values for {row['index']} row")
                continue

            if group_id == "":
                start_index = row["index"]
                group_id = row["group_id"]

            image_url = row["image"].replace('=IMAGE("', "").replace('", 4, 120, 120)', "")
            indexes.append(row["index"])
            image_urls.append(image_url)

            if row['caption'] != '-':
                raw_caption = """ #digitalmodel #fashionista #fashiongram #styleblogger #fashionblogger #fashionmodel #modelling
                #modelswanted #modelsearch #modelphotography #modelpose #modelstatus #modelsofinstagram #modelife 
                #digitalinfluencer #VirtualModel #DigitalFashion""".replace("\n", "").strip()

                max_hashtags = 30

                mentions = """@thevarunmayya @acknowledge.ai @eluna.ai"""
                extracted_caption = row["caption"][row["caption"].find("#"):].strip()
                raw_caption_count = raw_caption.count("#")
                extracted_caption_count = extracted_caption.count("#")

                caption_to_remove_from_raw = extracted_caption_count + raw_caption_count - max_hashtags

                if caption_to_remove_from_raw > 0:
                    raw_caption = "#" + " #".join(raw_caption.split(" #")[1:caption_to_remove_from_raw])

                if raw_caption == "#":
                    raw_caption = ""

                caption = row["caption"][
                          :row["caption"].find("#"):] + "\n\n\n" + extracted_caption + raw_caption + "\n\n\n" + mentions

            main_location = get_location()
            location = row["location"].replace(f",{main_location}", "").strip()
            # print(f"Posting with URL: {image_url}, Caption: {caption}, Location: {location}")

    if len(image_urls) > 0:
        post_on_instagram(image_urls[:6], caption, location)
        for i in indexes[:6]:
            gsheet.update_cell(posted_on_instagram.row + i, posted_on_instagram.col,
                               datetime.now().strftime("%Y-%m-%d %H:%M"))
        send_messages("Successfully posted on instagram, checkout https://www.instagram.com/aashvithemodel")
    else:
        send_messages("No posts to post on instagram, please check the sheet")


if __name__ == '__main__':
    try:
        scheduled_posts_on_instagram()
        driver = None
    except Exception as e:
        print("Error while posting on instagram", e)
        send_messages(f"Error while posting on instagram\n {e} \n {traceback.print_exc()}", )
    finally:
        if driver is not None:
            driver.quit()

    if not check_if_automatic1111_is_active():
        send_messages("Automatic1111 is not active, please update the url \n Process has been stopped")
        exit(0)

    try:
        v1_generate_prompts()
    except Exception as e:
        print("Error while generating prompts", e)
        send_messages(f"Error while generating prompts\n {e} \n {traceback.print_exc()}", )
    finally:
        close_automatic1111()
