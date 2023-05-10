# Middle East Technical University
# Department of Electrical and Electronics Engineering
# EE494 Engineering Design II
# Team:     Manchester Untitled
# Project:  Aid for Blind People

# # # # # # # # # # # # # # # # # #
# MAIN DECISION MAKING ALGORITHM  #
# # # # # # # # # # # # # # # # # #

import asyncio
import datetime
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
        self.ring_sign_checker = []
        self.bool_sign_checker = False
        self.ahead_cross_checker = []
        self.here_cross_checker = []
        self.bool_ahead_cross_checker = False
        self.bool_here_cross_checker = False
        self.here_ahead_state = []
        self.bool_ahead_state = False


async def capture_async(gvars, capture, model):
    await asyncio.sleep(0.1)
    while True:
        await asyncio.sleep(0.0001)
        success, frame = capture.read()
        results = model(source=frame, stream=True, device="cuda:0", verbose=False)
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


async def sign_checker_async(obj, flag):
    await asyncio.sleep(0.1)
    if flag is True:
        obj.ring_sign_checker = []
        obj.bool_sign_checker = False
        await asyncio.sleep(3)
        ring_mode = 0
        if len(obj.ring_sign_checker) != 0:
            ring_mode = statistics.mode(obj.ring_sign_checker)

        if ring_mode == 0:
            obj.bool_sign_checker = False
        else:
            obj.bool_sign_checker = True


async def cross_checker_async(obj, flag):
    await asyncio.sleep(0.1)
    if flag is True:
        obj.ahead_cross_checker = []
        obj.here_cross_checker = []
        await asyncio.sleep(3)
        ahead_mode = 0
        here_mode = 0
        if len(obj.ahead_cross_checker) != 0:
            ahead_mode = statistics.mode(obj.ahead_cross_checker)
        if len(obj.here_cross_checker) != 0:
            here_mode = statistics.mode(obj.here_cross_checker)

        if ahead_mode == 0:
            obj.bool_ahead_cross_checker = False
        else:
            obj.bool_ahead_cross_checker = True

        if here_mode == 0:
            obj.bool_here_cross_checker = False
        else:
            obj.bool_here_cross_checker = True


async def here_checker_async(obj):
    await asyncio.sleep(0.1)
    while True:
        obj.here_ahead_state = []
        obj.bool_ahead_state = False
        await asyncio.sleep(1)
        here_mode = 0
        if len(obj.here_ahead_state) != 0:
            here_mode = statistics.mode(obj.here_ahead_state)

        if here_mode != 0:
            obj.bool_ahead_state = True
            break


async def data_channel_periodic(obj, sender, button):
    await asyncio.sleep(0.1)
    while True:
        await asyncio.sleep(5)
        ahead_mode = 0
        here_mode = 0
        bin_mode = 0
        ring_mode = 0
        if len(obj.ahead_idle) != 0:
            ahead_mode = statistics.mode(obj.ahead_idle)
        if len(obj.here_idle) != 0:
            here_mode = statistics.mode(obj.here_idle)
        if len(obj.bin_idle) != 0:
            bin_mode = statistics.mode(obj.bin_idle)
        if len(obj.ring_idle) != 0:
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


def meter_calculator(height):
    x = 0.5/((5/9)*height)
    x = round(float(x))
    return x


def direction_determinator(x):
    if x <= 0.70:
        return "LEFT"
    elif x >= 0.80:
        return "RIGHT"
    else:
        return "FORWARD"


async def main():
    await asyncio.sleep(0.1)
    global_vars = GlobalVariables("IDLE")
    current_state = "IDLE"
    previous_state = "IDLE"
    capture = cv2.VideoCapture(2)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
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
    counter = 0
    capture_task = asyncio.create_task(capture_async(global_vars, capture, object_tracking_model))
    sender_task = asyncio.create_task(data_channel_periodic(global_vars, text_box_sender, send_button))
    sign_checker_task = asyncio.create_task(sign_checker_async(global_vars, False))
    cross_checker_task = asyncio.create_task(cross_checker_async(global_vars, False))

    while True:
        print(current_state)
        await asyncio.sleep(0.0001)

        # STATE 1 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if current_state == "IDLE":
            if sender_task.done():
                sender_task = asyncio.create_task(data_channel_periodic(global_vars, text_box_sender, send_button))
            command = data_channel_reader(driver)
            if command == "SIGN":
                current_state = "SIGN_CHECK"
                previous_state = "IDLE"
                sender_task.cancel()
                sign_checker_task = asyncio.create_task(sign_checker_async(global_vars, True))
                continue
            elif command == "CROSS":
                current_state = "CROSS_CHECK"
                previous_state = "IDLE"
                sender_task.cancel()
                cross_checker_task = asyncio.create_task(cross_checker_async(global_vars, True))
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
            rings = []
            if len(global_vars.classes) != 0:
                for cls in global_vars.classes:
                    if cls == 3:
                        rings.append(cls)
            global_vars.ring_sign_checker.append(len(rings))

            if sign_checker_task.done():
                if global_vars.bool_sign_checker is True:
                    current_state = "SIGN_MAIN"
                    previous_state = "SIGN_CHECK"
                    message = "2:1"
                    await data_channel_send(message, text_box_sender, send_button)
                    continue
                else:
                    current_state = "IDLE"
                    previous_state = "SIGN_CHECK"
                    message = "2:0"
                    await data_channel_send(message, text_box_sender, send_button)
                    await data_channel_send("Received: CANCEL", text_box_sender, send_button)
                    continue

        # STATE 3 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "SIGN_MAIN":
            command = data_channel_reader(driver)
            if command == "CANCEL":
                current_state = "IDLE"
                previous_state = "SIGN_MAIN"
                counter = 0
                message = "3:CANCEL"
                await data_channel_send(message, text_box_sender, send_button)
                continue

            if counter % 20 == 0:
                e = datetime.datetime.now()
                minute = e.minute
                yellow_red_minute = (20 - minute % 20) % 20
                brown_minute = (3 - minute % 15) % 15
                message = "3:" + str(yellow_red_minute) + ":" + str(brown_minute)
                await data_channel_send(message, text_box_sender, send_button)
            await asyncio.sleep(3)
            counter += 1

        # STATE 4 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "CROSS_CHECK":
            aheads = []
            heres = []
            if len(global_vars.classes) != 0:
                for cls in global_vars.classes:
                    if cls == 0:
                        aheads.append(cls)
                    elif cls == 1:
                        heres.append(cls)
            global_vars.ahead_cross_checker.append(len(aheads))
            global_vars.here_cross_checker.append(len(heres))

            if cross_checker_task.done():
                if global_vars.bool_here_cross_checker is True:
                    current_state = "CROSS_LEFT"
                    previous_state = "CROSS_CHECK"
                    message = "4:1"
                    await data_channel_send(message, text_box_sender, send_button)
                    continue
                elif global_vars.bool_ahead_cross_checker is True:
                    current_state = "CROSS_AHEAD"
                    previous_state = "CROSS_CHECK"
                    message = "4:2"
                    await data_channel_send(message, text_box_sender, send_button)
                    asyncio.create_task(here_checker_async(global_vars))
                    continue
                else:
                    current_state = "IDLE"
                    previous_state = "CROSS_CHECK"
                    message = "4:0"
                    await data_channel_send(message, text_box_sender, send_button)
                    await  data_channel_send("Received: CANCEL", text_box_sender, send_button)
                    continue

        # STATE 5 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "CROSS_AHEAD":
            command = data_channel_reader(driver)
            if command == "CANCEL":
                current_state = "IDLE"
                previous_state = "CROSS_AHEAD"
                message = "5:CANCEL"
                await data_channel_send(message, text_box_sender, send_button)
                continue

            heres = []
            if len(global_vars.classes) != 0:
                for cls in global_vars.classes:
                    if cls == 1:
                        heres.append(cls)
            global_vars.here_ahead_state.append(len(heres))

            if global_vars.bool_ahead_state is True:
                current_state = "CROSS_LEFT"
                previous_state = "CROSS_AHEAD"
                message = "5:1"
                await data_channel_send(message, text_box_sender, send_button)
                continue

        # STATE 6 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "CROSS_LEFT":
            command = data_channel_reader(driver)
            if command == "CANCEL":
                current_state = "IDLE"
                continue

        # STATE 7 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "CROSS_LEFT_CHECK":
            command = data_channel_reader(driver)
            if command == "CANCEL":
                current_state = "IDLE"
                continue

        # STATE 8 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "CROSS_RIGHT":
            command = data_channel_reader(driver)
            if command == "CANCEL":
                current_state = "IDLE"
                continue

        # STATE 9 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "CROSS_RIGHT_CHECK":
            command = data_channel_reader(driver)
            if command == "CANCEL":
                current_state = "IDLE"
                continue

        # STATE 10 # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        elif current_state == "CROSS_DEAD":
            command = data_channel_reader(driver)
            if command == "CANCEL":
                current_state = "IDLE"
                continue

        else:
            print("ERROR")


if __name__ == '__main__':
    asyncio.run(main())
