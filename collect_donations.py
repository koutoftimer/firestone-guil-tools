#!./venv/bin/python
import argparse
import json
import logging
import os
import subprocess
from pathlib import Path

import cv2
import pyautogui
import pytesseract
import requests
import sqlalchemy.orm as orm

from db import save_donations_to_db, engine, User

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


DONATION_SCREENSHOTS = [
    Path('1.png'),
    Path('2.png'),
]


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
    pyautogui.screenshot(DONATION_SCREENSHOTS[0])
    pyautogui.sleep(5)
    # scroll bottom
    pyautogui.scroll(-50)
    pyautogui.sleep(1)
    # rest donators
    pyautogui.screenshot(DONATION_SCREENSHOTS[1])
    pyautogui.sleep(5)
    # get back to main screen
    pyautogui.press('esc', presses=2, interval=1)


def get_black_white(file_name):
    img = cv2.imread(file_name)

    cv2.imread(file_name)
    img2gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(img2gray, 200, 255, cv2.THRESH_BINARY)
    image_final = cv2.bitwise_and(img2gray, img2gray, mask=mask)
    _, new_img = cv2.threshold(
        image_final, 180, 255,
        cv2.THRESH_BINARY)  # for black text , cv.THRESH_BINARY_INV

    return new_img


def ocr_screenshot(screenshot: str) -> dict[str, int]:
    fullscreen = cv2.imread(screenshot)
    player = cv2.imread('samples/Player.png')
    result = cv2.matchTemplate(player, fullscreen, cv2.TM_SQDIFF_NORMED)
    _, _, (x, y), _ = cv2.minMaxLoc(result)
    x += 5
    y += 90

    black_white = get_black_white(screenshot)[
        y:y + DONATIONS_RECT[3],
        x:x + DONATIONS_RECT[2],
    ]

    raw = pytesseract.image_to_string(
        black_white,
        lang='rus+eng',
        config='--psm 6 --oem 0 --tessdata-dir ./tessdata/')
    # raw = subprocess.getoutput(fr'''
    #     tesseract {screenshot} - \
    #         --psm 6 --oem 0 --tessdata-dir ./tessdata/ \
    #         -l eng+rus
    # ''')
    # # -l eng+rus+chi_sim+chi_tra+jpn
    NICK_CORRECTIONS = {
        'eItooth': 'eltooth',
        'iack.e.hayes': 'jack.e.hayes',
        'シ ヤ ガー': 'ジャガー',
        'シ ヤ ガ 一': 'ジャガー',
    }
    data = {}
    for line in raw.splitlines():
        if ' ' not in line:
            continue
        nick, donation = line.rsplit(maxsplit=1)
        nick = NICK_CORRECTIONS.get(nick, nick)
        data[nick] = int(donation.replace(',', '').replace('о', '0'))
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

    parser = argparse.ArgumentParser()
    parser.add_argument('--new', action='store_true')
    parser.add_argument('--save', action='store_true')
    parser.add_argument('--upload', action='store_true')
    args = parser.parse_args()

    # TODO: rewrite with python ffi for libx11
    if args.new:
        pyautogui.FAILSAFE = True
        subprocess.getoutput(
            "xdotool search --name '^Firestone$' windowactivate --sync")
        take_donations_screenshots()

    data = ocr(DONATION_SCREENSHOTS)
    from pprint import pprint
    pprint(data)

    with orm.Session(engine) as session:
        old = set(nick[0] for nick in session.query(User.nick).filter_by(
            status='active').all())
    new = set(data.keys())

    if old != new:
        print(f"Old: {old}")
        print(
            f'Leavers: {old - new},\n new: {new - old},\n remains: {len(old & new)}'
        )
        while (ans :=
               input('Proced? (y/N): ')) not in ['y', 'Y', 'n', 'N', '']:
            pass
        if ans == '':
            ans = 'n'
        if ans.lower() == 'n':
            return

    if args.save:
        save_donations_to_db(data)

    if args.upload:
        # replicate data to pythonanywhere
        push_updates_to_pythonanywhere(data)


if __name__ == "__main__":
    main()
