#!./venv/bin/python
from pathlib import Path

import pyautogui

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
    pyautogui.moveTo(DONATIONS_RECT[0], DONATIONS_RECT[1])
    pyautogui.sleep(1)
    pyautogui.scroll(50)
    pyautogui.sleep(1)
    # top donators
    pyautogui.screenshot('full.png')
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


def main():
    pyautogui.FAILSAFE = True
    take_donations_screenshots()


if __name__ == "__main__":
    pyautogui.sleep(5)
    main()
