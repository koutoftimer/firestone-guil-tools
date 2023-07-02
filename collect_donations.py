#!./venv/bin/python
import json
import logging
import os
import subprocess
from pathlib import Path

import requests
import pyautogui

from db import save_donations_to_db

DONATIONS_RECT = 448, 174, 535, 885


class MainScreen:
    GUILD_BUTTON_LOC = 1869, 469

    @staticmethod
    def go_to_guild_screen():
        pyautogui.moveTo(*MainScreen.GUILD_BUTTON_LOC)
        pyautogui.click()
        pyautogui.sleep(1)


class GuildScreen:
    TREASURE_BUTTON_LOC = 321, 733

    @staticmethod
    def open_treasury():
        pyautogui.moveTo(*GuildScreen.TREASURE_BUTTON_LOC)
        pyautogui.click()
        pyautogui.sleep(1)


DONATION_SCREENSHOTS = [Path('1.png'), Path('2.png')]


def take_donations_screenshots():
    for path in DONATION_SCREENSHOTS:
        if path.exists():
            path.unlink()
    MainScreen.go_to_guild_screen()
    GuildScreen.open_treasury()
    # scroll top
    pyautogui.moveTo(DONATIONS_RECT[0] + DONATIONS_RECT[2] // 2,
                     DONATIONS_RECT[1] + DONATIONS_RECT[3] // 2)
    pyautogui.sleep(1)
    pyautogui.scroll(50)
    pyautogui.sleep(1)
    # top donators
    pyautogui.screenshot(DONATION_SCREENSHOTS[0], region=DONATIONS_RECT)
    pyautogui.sleep(5)
    # scroll bottom
    pyautogui.scroll(-50)
    pyautogui.sleep(1)
    # rest donators
    pyautogui.screenshot(DONATION_SCREENSHOTS[1], region=DONATIONS_RECT)
    pyautogui.sleep(5)
    # get back to main screen
    pyautogui.press('esc', presses=2, interval=1)


def ocr_screenshot(screenshot: str) -> dict[str, int]:
    raw = subprocess.getoutput(fr'''
        tesseract {screenshot} - \
            --psm 6 --oem 0 --tessdata-dir ./tessdata/ \
            -l eng+rus+chi_sim+chi_tra+jpn
    ''')
    NICK_CORRECTIONS = {
        'eItooth': 'eltooth',
        'シ ヤ ガー': 'ジャガー',
        'シ ヤ ガ 一': 'ジャガー',
    }
    data = {}
    for line in raw.splitlines():
        if ' ' not in line:
            continue
        nick, donation = line.rsplit(maxsplit=1)
        nick = NICK_CORRECTIONS.get(nick, nick)
        data[nick] = int(donation.replace(',', ''))
    return data


def ocr(screenshots: list[Path]):
    data = {}
    for path in screenshots:
        data.update(**ocr_screenshot(str(path)))
    return data


def push_updates_to_pythonanywhere(data: dict[str, int]):
    sync_host = os.environ.get('SYNC_HOST', 'outoftime.pythonanywhere.com')
    logging.info(f"Sync DB with {sync_host}: {data}")
    with open('auth.json') as fp:
        auth = json.load(fp)
    body = {
        'auth': auth,
        'data': data,
    }
    requests.post(f'https://{sync_host}/firestone/update', json=body)


def main():
    logging.getLogger().setLevel(logging.DEBUG)
    pyautogui.FAILSAFE = True

    # TODO: rewrite with python ffi for libx11
    subprocess.getoutput(
        "xdotool search --name '^Firestone$' windowactivate --sync")
    take_donations_screenshots()

    data = ocr(DONATION_SCREENSHOTS)
    logging.debug(f'OCR {data}')
    save_donations_to_db(data)

    # replicate data to pythonanywhere
    push_updates_to_pythonanywhere(data)


if __name__ == "__main__":
    main()
