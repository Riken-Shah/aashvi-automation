from automation import uc, get_driver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from time import sleep
from utils import send_messages
import os


def run_post_processing_collab():
    driver = get_driver()
    driver.get("https://colab.research.google.com/drive/16GcEQSd0ryVjTTuzxxJwiBv2ya-F4BMG")
    sleep(30)
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.COMMAND + Keys.F9)
    sleep(30)
    max_attempt = 20 # 30 * 20 = 600 seconds = 10 minutes
    while max_attempt > 0:
        try:
            driver.find_element(By.CSS_SELECTOR, ".cell.running")
            sleep(30)
            print(f"trying again in 30 seconds for {max_attempt} times")
            max_attempt -= 1
        except NoSuchElementException:
            break
    try:
        driver.find_element(By.CSS_SELECTOR, ".cell.running")
        print("Post processing collab still running after 10 minutes. Please check.")
        send_messages("Post processing collab still running after 10 minutes. Please check.")
    except NoSuchElementException:
        pass
    driver.quit()


if __name__ == '__main__':
    try:
        run_post_processing_collab()
    except Exception as e:
        print(f"Post processing collab failed. Please check. {e}")
        send_messages(f"Post processing collab failed. Please check. {e}")
