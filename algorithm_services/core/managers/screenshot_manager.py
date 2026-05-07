"""
工作记录截图管理器
每天晚上 6 点到 8 点之间自动截图，作为工作记录
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import os
import random
import threading
from datetime import datetime
from pathlib import Path

import mss
from PIL import Image


class ScreenshotManager:
    """
    工作记录截图管理器
    定时截取屏幕并保存，每天最多截图3张
    """

    def __init__(self):
        self._thread = None
        self._stop_event = threading.Event()
        self.screenshot_folder = self._get_screenshot_folder()
        self.hour_start = 18
        self.hour_end = 20
        self.max_screenshots_per_day = 3
        self._daily_screenshot_count = 0
        self._last_screenshot_date = None

    def _get_screenshot_folder(self) -> str:
        folder = os.path.join(os.path.expanduser("~"), "Pictures", "YISIA_Screenshots")
        Path(folder).mkdir(parents=True, exist_ok=True)
        return folder

    def _check_and_reset_daily(self):
        today = datetime.now().date()
        if self._last_screenshot_date != today:
            self._daily_screenshot_count = 0
            self._last_screenshot_date = today

    def _can_take_screenshot(self) -> bool:
        self._check_and_reset_daily()
        if self._daily_screenshot_count >= self.max_screenshots_per_day:
            return False
        return True

    def start(self):
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                now = datetime.now()
                current_hour = now.hour

                if self.hour_start <= current_hour < self.hour_end:
                    if self._can_take_screenshot():
                        self._take_screenshot()
                        
                        if self._can_take_screenshot():
                            next_interval = random.randint(20, 40)
                            self._stop_event.wait(timeout=next_interval * 60)
                            continue
                self._stop_event.wait(timeout=60)

            except Exception:
                self._stop_event.wait(timeout=60)

    def _take_screenshot(self):
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)

            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"work_record_{timestamp}.png"
            filepath = os.path.join(self.screenshot_folder, filename)

            img.save(filepath, "PNG")
            self._daily_screenshot_count += 1

        except Exception:
            pass

    def take_screenshot_now(self):
        self._take_screenshot()


screenshot_manager = ScreenshotManager()
