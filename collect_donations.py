#!./venv/bin/python
import json
import logging
import os
import sqlite3
import subprocess
from pathlib import Path
from typing import Iterable

import requests

DONATIONS_RECT = 448, 174, 535, 885


class MainScreen:
    GUILD_BUTTON_LOC = 1869, 469

    @staticmethod
    def go_to_guild_screen():
        import pyautogui
        pyautogui.moveTo(*MainScreen.GUILD_BUTTON_LOC)
        pyautogui.click()
        pyautogui.sleep(1)


class GuildScreen:
    TREASURE_BUTTON_LOC = 321, 733

    @staticmethod
    def open_treasury():
        import pyautogui
        pyautogui.moveTo(*GuildScreen.TREASURE_BUTTON_LOC)
        pyautogui.click()
        pyautogui.sleep(1)


DONATION_SCREENSHOTS = [Path('1.png'), Path('2.png')]


def take_donations_screenshots():
    import pyautogui
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


DB_FILENAME = './guild.db'


def save_donations_to_db(data: dict[str, int]):
    logging.info(f'Updating donations: {data}')
    update_member_status(data.keys())
    create_table = '''
    CREATE TABLE IF NOT EXISTS donations (
        user_id INTEGER NOT NULL,
        donation INTEGER NOT NULL,
        timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
        id INTEGER PRIMARY KEY ASC,
        FOREIGN KEY(user_id) REFERENCES user(id)
    )
    '''
    conn = sqlite3.connect(DB_FILENAME)
    cur = conn.cursor()
    cur.execute(create_table)
    cur.executemany(
        '''
        INSERT INTO donations (user_id, donation)
        VALUES ((SELECT id FROM users WHERE nickname = ?), ?)
        ''',
        tuple(data.items()),
    )
    conn.commit()


def update_member_status(active_members: Iterable[str]):
    create_table = '''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY ASC,
        nickname TEXT UNIQUE NOT NULL,
        status TEXT NOT NULL,
        comment TEXT
    )
    '''
    conn = sqlite3.connect(DB_FILENAME)
    cur = conn.cursor()
    cur.execute(create_table)

    # mark active member as leavers
    user_list = ','.join(f'"{v}"' for v in active_members)
    cur.execute(
        'UPDATE users SET status = "left" '
        f'WHERE users.status = "active" AND users.nickname NOT IN ({user_list})'
    )
    # add new members
    cur.executemany(
        'INSERT OR IGNORE INTO users (nickname, status) VALUES (?, "active")',
        zip(active_members),
    )
    # activate existing members
    cur.executemany(
        'UPDATE users SET status = "active" WHERE users.nickname = ?',
        zip(active_members),
    )
    conn.commit()


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
    import pyautogui
    logging.getLogger().setLevel(logging.INFO)
    pyautogui.FAILSAFE = True
    # TODO: rewrite with python ffi for libx11
    subprocess.getoutput(
        "xdotool search --name '^Firestone$' windowactivate --sync")
    take_donations_screenshots()
    data = ocr(DONATION_SCREENSHOTS)
    save_donations_to_db(data)
    # replicate data to pythonanywhere
    push_updates_to_pythonanywhere(data)


if __name__ == "__main__":
    main()
