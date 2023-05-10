# Middle East Technical University
# Department of Electrical and Electronics Engineering
# EE494 Engineering Design II
# Team:     Manchester Untitled
# Project:  Aid for Blind People

# # # # # # # # # # # # # # # # # #
# MAIN DECISION MAKING ALGORITHM  #
# # # # # # # # # # # # # # # # # #

import asyncio
import cv2
import re
import statistics
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from ultralytics import YOLO
from ultralytics.yolo.utils.plotting import Annotator
from webdriver_manager.chrome import ChromeDriverManager


class GlobalVariables:
    def __init__(self, current_state):
        self.current_state = current_state
        self.classes = []
        self.confidences = []
        self.ahead_idle = []
        self.here_idle = []
        self.bin_idle = []
        self.ring_idle = []


async def capture_async(gvars, capture, model):
    await asyncio.sleep(0.1)
    while True:
        await asyncio.sleep(0.0001)
        success, frame = capture.read()
        results = model(source=frame, stream=True, verbose=False)
        for result in results:
            annotated = result.plot()
            boxes = result.boxes
            classes = []
            confidences = []
            for box in boxes:
                classes.append(box.cls.cpu())
                confidences.append(box.conf.cpu())
            gvars.classes = classes
            gvars.confidences = confidences
            cv2.imshow("Result", annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break


async def data_channel_periodic(obj, sender, button):
    await asyncio.sleep(0.1)
    while True:
        await asyncio.sleep(5),
        ahead_mode = statistics.mode(obj.ahead_idle)
        here_mode = statistics.mode(obj.here_idle)
        bin_mode = statistics.mode(obj.bin_idle)
        ring_mode = statistics.mode(obj.ring_idle)
        if ahead_mode != 0 or here_mode != 0 or bin_mode != 0 or ring_mode != 0:
            message_str = "1:" + str(ahead_mode) + ":" + str(here_mode) + ":" + str(bin_mode) + ":" + str(ring_mode)
            sender.send_keys(message_str)
            await asyncio.sleep(0.1)
            button.click()
            await asyncio.sleep(0.1)
        obj.ahead_idle = []
        obj.here_idle = []
        obj.bin_idle = []
        obj.ring_idle = []


async def data_channel_send(message, sender, button):
    await asyncio.sleep(0.1)
    sender.send_keys(message)
    await asyncio.sleep(0.1)
    button.click()
    await asyncio.sleep(0.1)


def data_channel_reader(driver):
    html_file_string = driver.page_source
    chat_string = re.search('Sent: CONNECTED<br>(.*)</div>', html_file_string)
    messages = chat_string.group(1).split("<br>")
    messages.pop()
    received_list = []

    for message in messages:
        if "Received:" in message:
            received_list.append(message)

    if len(received_list) == 0:
        return "CANCEL"

    command = received_list[-1].split("Received: ")

    if command[1] == "CROSS" or command[1] == "SIGN" or command[1] == "CANCEL":
        return command[1]


async def main():
    await asyncio.sleep(0.1)
    global_vars = GlobalVariables("IDLE")
    current_state = "IDLE"
    capture = cv2.VideoCapture(0)
    object_tracking_model = YOLO('best.pt')
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
    driver.implicitly_wait(0.5)
    driver.get("https://mert.damgoai.com:5443/WebRTCAppEE/player.html")
    await asyncio.sleep(1)
    text_box_sender = driver.find_element(By.ID, "dataTextbox")
    text_box_stream_name = driver.find_element(By.ID, "streamName")
    start_button = driver.find_element(By.ID, "start_play_button")
    option_button = driver.find_element(By.ID, "options")
    send_button = driver.find_element(By.ID, "send")
    text_box_stream_name.clear()
    text_box_stream_name.send_keys("manu31")
    start_button.click()
    await asyncio.sleep(1)
    option_button.click()
    text_box_sender.send_keys("CONNECTED")
    send_button.click()
    capture_task = asyncio.create_task(capture_async(global_vars, capture, object_tracking_model))
    sender_task = asyncio.create_task(data_channel_periodic(global_vars, text_box_sender, send_button))

    while True:
        await asyncio.sleep(0.01)

        # STATE 1 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if current_state == "IDLE":
            if sender_task.done():
                sender_task = asyncio.create_task(data_channel_periodic(global_vars, text_box_sender, send_button))

            command = data_channel_reader(driver)
            if command == "SIGN":
                current_state = "SIGN_CHECK"
                await data_channel_send("IDLE-SIGN", text_box_sender, send_button)
                sender_task.cancel()
                continue
            elif command == "CROSS":
                current_state = "CROSS_CHECK"
                await data_channel_send("IDLE-CROSS", text_box_sender, send_button)
                sender_task.cancel()
                continue

            aheads = []
            heres = []
            bins = []
            rings = []
            if len(global_vars.classes) != 0:
                for cls in global_vars.classes:
                    if cls == 0:
                        aheads.append(cls)
                    elif cls == 1:
                        heres.append(cls)
                    elif cls == 2:
                        bins.append(cls)
                    elif cls == 3:
                        rings.append(cls)
                global_vars.ahead_idle.append(len(aheads))
                global_vars.here_idle.append(len(heres))
                global_vars.bin_idle.append(len(bins))
                global_vars.ring_idle.append(len(rings))

        # STATE 2 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "SIGN_CHECK":
            command = data_channel_reader(driver)

        # STATE 3 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "SIGN_MAIN":
            command = data_channel_reader(driver)
            if command == "CANCEL":
                current_state = "IDLE"
                await data_channel_send("SIGN-IDLE", text_box_sender, send_button)
                continue

        # STATE 4 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "SIGN_DEAD":
            command = data_channel_reader(driver)
            if command == "CANCEL":
                current_state = "IDLE"
                await data_channel_send("SIGN-IDLE", text_box_sender, send_button)
                continue

        # STATE 5 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "CROSS_CHECK":
            command = data_channel_reader(driver)

        # STATE 6 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "CROSS_AHEAD":
            command = data_channel_reader(driver)
            if command == "CANCEL":
                current_state = "IDLE"
                await data_channel_send("CROSS-IDLE", text_box_sender, send_button)
                continue

        # STATE 7 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "CROSS_HERE":
            command = data_channel_reader(driver)

        # STATE 8 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "CROSS_LEFT":
            command = data_channel_reader(driver)
            if command == "CANCEL":
                current_state = "IDLE"
                await data_channel_send("CROSS-IDLE", text_box_sender, send_button)
                continue

        # STATE 9 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "CROSS_LEFT_CHECK":
            command = data_channel_reader(driver)
            if command == "CANCEL":
                current_state = "IDLE"
                await data_channel_send("CROSS-IDLE", text_box_sender, send_button)
                continue

        # STATE 10 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "CROSS_RIGHT":
            command = data_channel_reader(driver)
            if command == "CANCEL":
                current_state = "IDLE"
                await data_channel_send("CROSS-IDLE", text_box_sender, send_button)
                continue

        # STATE 11 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "CROSS_RIGHT_CHECK":
            command = data_channel_reader(driver)
            if command == "CANCEL":
                current_state = "IDLE"
                await data_channel_send("CROSS-IDLE", text_box_sender, send_button)
                continue

        # STATE 12 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "CROSS_DEAD":
            command = data_channel_reader(driver)
            if command == "CANCEL":
                current_state = "IDLE"
                await data_channel_send("CROSS-IDLE", text_box_sender, send_button)
                continue

        else:
            print("ERROR")


if __name__ == '__main__':
    asyncio.run(main())
