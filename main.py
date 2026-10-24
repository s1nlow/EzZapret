import ctypes
from ctypes import wintypes
import hashlib
import html
import json
import os
import queue
import re
import shutil
import ssl
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import urllib.error
import zipfile

from pathlib import Path

import customtkinter as ctk
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog


PROGRAM_NAME = "EzZapret"
PROGRAM_VERSION = "1.3.1"
PROJECT_GITHUB_URL = "https://github.com/s1nlow/EzZapret"
ZAPRET_GITHUB_URL = "https://github.com/Flowseal/zapret-discord-youtube"
ZAPRET_OWNER = "Flowseal"
ZAPRET_REPO = "zapret-discord-youtube"
ZAPRET_VERSION_URL = (
    "https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube/"
    "main/.service/version.txt"
)
ZAPRET_LATEST_URL = f"https://github.com/{ZAPRET_OWNER}/{ZAPRET_REPO}/releases/latest"
ZAPRET_ASSETS_URL = f"https://github.com/{ZAPRET_OWNER}/{ZAPRET_REPO}/releases/expanded_assets"
ZAPRET_IPSET_URL = (
    "https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube/"
    "main/.service/ipset-service.txt"
)
SERVICE_NAME = "zapret"
IPSET_SENTINEL = "203.0.113.113/32"
DEFAULT_GAME_TCP = "1024-65535"
DEFAULT_GAME_UDP = "1024-65535"
QUEUE_INTERVAL_MS = 40

USER_EDITABLE_FILES = {
    "list-general-user.txt": "Дополнительные домены для обхода.",
    "list-exclude-user.txt": "Домены, которые не нужно обходить.",
    "ipset-exclude-user.txt": "IP-адреса и подсети, которые не нужно обходить.",
    "ipset-all-user.txt": "Дополнительные IP и подсети для обхода.",
}

STOCK_LIST_FILES = {
    "list-general.txt": "Общий список доменов zapret.",
    "list-exclude.txt": "Стандартные доменные исключения zapret.",
    "ipset-exclude.txt": "Стандартные IP-исключения zapret.",
    "ipset-all.txt": "Актуальный системный список IPSet zapret.",
}

USER_LIST_FILES = tuple(USER_EDITABLE_FILES)

BASE_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)


def getResourcePath(*parts):
    bundleDir = Path(getattr(sys, "_MEIPASS", BASE_DIR))
    return bundleDir.joinpath(*parts)


ZAPRET_DIR = BASE_DIR / "zapret"
ICON_FILE = getResourcePath("assets", "EzZapret.ico")
SETTINGS_FILE = BASE_DIR / "settings.json"
TEMP_DIR = BASE_DIR / ".ezzapret_download"

COLORS = {
    "background": "#0F0D0B",
    "card": "#181411",
    "card2": "#211A15",
    "border": "#3A2B20",
    "text": "#F4ECE4",
    "muted": "#9D8E82",
    "button": "#302A25",
    "buttonHover": "#40372F",
    "orange": "#FF8A00",
    "orangeLight": "#FFB45B",
    "orangeDark": "#5A310B",
    "red": "#E56B6B",
    "green": "#79C98C",
}


class CircularButton(tk.Canvas):
    """A real circular button drawn on Canvas so its shape stays circular."""

    def __init__(self, parent, text, size, command, fontFamily="Segoe UI", fontSize=16):
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=COLORS["background"],
            bd=0,
            highlightthickness=0,
            relief="flat",
            cursor="hand2",
        )
        self.size = size
        self.command = command
        self.buttonText = text
        self.fontFamily = fontFamily
        self.fontSize = fontSize
        self.isEnabled = True
        self.isRunning = False
        self.isAccent = False
        self.isHover = False
        self.isPressed = False

        self.bind("<Enter>", self.onEnter)
        self.bind("<Leave>", self.onLeave)
        self.bind("<ButtonPress-1>", self.onPress)
        self.bind("<ButtonRelease-1>", self.onRelease)
        self.drawButton()

    def configure(self, cnf=None, **kwargs):
        """Keep a small configure API for callers that already use CTk buttons."""
        if cnf:
            kwargs.update(cnf)

        if "text" in kwargs:
            self.buttonText = kwargs.pop("text")
        if "state" in kwargs:
            self.setEnabled(kwargs.pop("state") != "disabled")
        if kwargs:
            super().configure(**kwargs)
        self.drawButton()

    config = configure

    def setText(self, text):
        self.buttonText = text
        self.drawButton()

    def setRunning(self, running):
        self.isRunning = running
        self.drawButton()

    def setEnabled(self, enabled):
        self.isEnabled = enabled
        self.isHover = False if not enabled else self.isHover
        self.drawButton()

    def setAccent(self, accent):
        self.isAccent = accent
        self.drawButton()

    def onEnter(self, _event):
        if self.isEnabled:
            self.isHover = True
            self.drawButton()

    def onLeave(self, _event):
        self.isHover = False
        self.isPressed = False
        self.drawButton()

    def onPress(self, _event):
        if self.isEnabled:
            self.isPressed = True
            self.drawButton()

    def onRelease(self, _event):
        if not self.isEnabled:
            return
        wasPressed = self.isPressed
        self.isPressed = False
        self.drawButton()
        if wasPressed and self.command:
            self.command()

    def drawButton(self):
        self.delete("all")

        if self.isAccent:
            fillColor = COLORS["orangeDark"]
            borderColor = COLORS["orange"]
            textColor = COLORS["orangeLight"]
        elif self.isRunning:
            fillColor = COLORS["background"]
            borderColor = COLORS["orange"]
            textColor = COLORS["orange"]
        else:
            fillColor = COLORS["background"]
            borderColor = COLORS["button"]
            textColor = COLORS["text"]

        if not self.isEnabled:
            fillColor = COLORS["background"]
            borderColor = COLORS["border"]
            textColor = COLORS["muted"]
        elif self.isHover:
            if self.isAccent:
                fillColor = "#74410F"
            else:
                fillColor = "#17120E"

        if self.isPressed and self.isEnabled:
            fillColor = "#211811" if not self.isAccent else "#5A310B"

        inset = 2
        self.create_oval(
            inset,
            inset,
            self.size - inset,
            self.size - inset,
            fill=fillColor,
            outline=borderColor,
            width=3 if (self.isRunning or self.isAccent) else 2,
        )

        textFont = tkfont.Font(
            family=self.fontFamily,
            size=self.fontSize,
            weight="bold" if self.size >= 100 else "normal",
        )
        self.create_text(
            self.size / 2,
            self.size / 2,
            text=self.buttonText,
            fill=textColor,
            font=textFont,
            anchor="center",
        )


class SmoothScrollableFrame(ctk.CTkFrame):
    """Canvas-based settings scroll area with gentle 60 FPS easing."""

    FRAME_TIME_MS = 16
    EASING = 0.22
    WHEEL_PIXELS = 78

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=kwargs.pop("fg_color", "transparent"), **kwargs)

        self.targetY = 0.0
        self.isAnimating = False
        self.animationId = None
        self.lastFrameTime = 0.0

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self,
            bg=COLORS["background"],
            highlightthickness=0,
            bd=0,
            relief="flat",
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ctk.CTkScrollbar(
            self,
            width=9,
            command=self.scrollbarCommand,
            fg_color=COLORS["background"],
            button_color=COLORS["button"],
            button_hover_color=COLORS["buttonHover"],
        )
        self.scrollbar.grid(row=0, column=1, sticky="ns", padx=(3, 2), pady=2)

        self.contentFrame = ctk.CTkFrame(
            self.canvas,
            fg_color="transparent",
            corner_radius=0,
        )
        self.windowId = self.canvas.create_window(
            (0, 0),
            window=self.contentFrame,
            anchor="nw",
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.contentFrame.bind("<Configure>", self.updateScrollRegion)
        self.canvas.bind("<Configure>", self.updateCanvasWidth)

        self.rootWindow = self.winfo_toplevel()
        self.rootWindow.bind("<MouseWheel>", self.onMouseWheel, add="+")
        self.rootWindow.bind("<Button-4>", self.onMouseWheel, add="+")
        self.rootWindow.bind("<Button-5>", self.onMouseWheel, add="+")

    def updateScrollRegion(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.syncTargetToView()

    def updateCanvasWidth(self, event):
        self.canvas.itemconfigure(self.windowId, width=event.width)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.syncTargetToView()

    def isInside(self, widget):
        current = widget
        while current is not None:
            if current == self:
                return True
            current = getattr(current, "master", None)
        return False

    def getMaxScrollPixels(self):
        contentHeight = self.contentFrame.winfo_height()
        viewHeight = self.canvas.winfo_height()
        return max(contentHeight - viewHeight, 0)

    def getCurrentScrollPixels(self):
        maxScroll = self.getMaxScrollPixels()
        if maxScroll <= 0:
            return 0.0
        return self.canvas.yview()[0] * maxScroll

    def syncTargetToView(self):
        if not self.isAnimating:
            self.targetY = self.getCurrentScrollPixels()

    def cancelAnimation(self):
        if self.animationId is None:
            return
        try:
            self.after_cancel(self.animationId)
        except tk.TclError:
            pass
        self.animationId = None

    def scrollbarCommand(self, *args):
        self.cancelAnimation()
        self.isAnimating = False
        self.canvas.yview(*args)
        self.targetY = self.getCurrentScrollPixels()

    def getWheelPixels(self, event):
        eventNumber = getattr(event, "num", None)
        if eventNumber == 4:
            return -self.WHEEL_PIXELS
        if eventNumber == 5:
            return self.WHEEL_PIXELS

        delta = getattr(event, "delta", 0)
        if not delta:
            return 0

        return -int((delta / 120.0) * self.WHEEL_PIXELS)

    def onMouseWheel(self, event):
        try:
            widget = self.winfo_containing(event.x_root, event.y_root)
        except tk.TclError:
            return

        if not self.isInside(widget):
            return

        maxScroll = self.getMaxScrollPixels()
        if maxScroll <= 0:
            return "break"

        if not self.isAnimating:
            self.targetY = self.getCurrentScrollPixels()

        self.targetY = max(
            0.0,
            min(maxScroll, self.targetY + self.getWheelPixels(event)),
        )
        self.startAnimation()
        return "break"

    def startAnimation(self):
        if self.isAnimating:
            return
        self.isAnimating = True
        self.lastFrameTime = time.monotonic()
        self.animateScroll()

    def animateScroll(self):
        maxScroll = self.getMaxScrollPixels()
        if maxScroll <= 0:
            self.isAnimating = False
            self.animationId = None
            return

        currentY = self.getCurrentScrollPixels()
        difference = self.targetY - currentY

        if abs(difference) < 0.5:
            self.canvas.yview_moveto(self.targetY / maxScroll)
            self.isAnimating = False
            self.animationId = None
            return

        now = time.monotonic()
        elapsed = max(now - self.lastFrameTime, 0.001)
        self.lastFrameTime = now

        frameFactor = 1.0 - pow(
            1.0 - self.EASING,
            elapsed / (self.FRAME_TIME_MS / 1000.0),
        )
        nextY = currentY + difference * frameFactor
        self.canvas.yview_moveto(nextY / maxScroll)
        self.animationId = self.after(self.FRAME_TIME_MS, self.animateScroll)


class EzZapretApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.settings = self.loadSettings()
        self.latestVersion = ""
        self.latestDownloadUrl = ""
        self.latestSha256 = ""
        self.updateCheckError = ""
        self.availableVersions = []
        self.selectedVersion = ""
        self.versionButtonMap = {}
        self.versionListBuilt = False
        self.isLoadingVersions = False
        self.releaseNotesCache = {}
        self.selectedChangelogVersion = ""
        self.changelogBackPage = "versions"
        self.changelogOriginPage = "versions"
        self.isBusy = False
        self.isRunning = False
        self.currentPage = "home"
        self.currentThread = None
        self.testProcess = None
        self.testThread = None
        self.eventQueue = queue.Queue()
        self.cancelTests = False
        self.restoreServiceAfterTests = False
        self.downloadPercent = 0

        self.title(PROGRAM_NAME)
        self.geometry("640x700")
        self.minsize(560, 620)
        self.configure(fg_color=COLORS["background"])
        self.setWindowIcon()
        self.positionWindow()
        self.protocol("WM_DELETE_WINDOW", self.closeApp)

        self.pages = {}
        self.buildPages()
        self.showPage("home")

        self.after(QUEUE_INTERVAL_MS, self.processQueue)
        self.refreshState()
        self.refreshInfoPage()
        self.refreshSettingsPage()
        self.setDownloadProgress(0)
        self.startStartupChecks()

    # -----------------------------
    # Window and pages
    # -----------------------------
    def positionWindow(self):
        """Center the window inside the Windows work area, above the taskbar."""
        windowWidth = 640
        windowHeight = 700

        if sys.platform.startswith("win"):
            try:
                rect = wintypes.RECT()
                result = ctypes.windll.user32.SystemParametersInfoW(
                    0x0030,
                    0,
                    ctypes.byref(rect),
                    0,
                )
                if result:
                    workWidth = rect.right - rect.left
                    workHeight = rect.bottom - rect.top
                    x = rect.left + max((workWidth - windowWidth) // 2, 0)
                    y = rect.top + max((workHeight - windowHeight) // 2, 0)
                    self.geometry(f"{windowWidth}x{windowHeight}+{x}+{y}")
                    return
            except Exception:
                pass

        screenWidth = self.winfo_screenwidth()
        screenHeight = self.winfo_screenheight()
        x = max((screenWidth - windowWidth) // 2, 0)
        y = max((screenHeight - windowHeight) // 2, 0)
        self.geometry(f"{windowWidth}x{windowHeight}+{x}+{y}")

    def setWindowIcon(self):
        if not ICON_FILE.exists():
            return
        try:
            self.iconbitmap(str(ICON_FILE))
        except tk.TclError:
            pass

    def buildPages(self):
        self.homePage = self.buildHomePage()
        self.infoPage = self.buildInfoPage()
        self.settingsPage = self.buildSettingsPage()
        self.testPage = self.buildTestPage()
        self.editorPage = self.buildEditorPage()
        self.versionPage = self.buildVersionPage()
        self.changelogPage = self.buildChangelogPage()
        self.diagnosticsPage = self.buildDiagnosticsPage()

        self.pages = {
            "home": self.homePage,
            "info": self.infoPage,
            "settings": self.settingsPage,
            "tests": self.testPage,
            "editor": self.editorPage,
            "versions": self.versionPage,
            "changelog": self.changelogPage,
            "diagnostics": self.diagnosticsPage,
        }

        for page in self.pages.values():
            page.pack_forget()

    def showPage(self, pageName):
        if pageName not in self.pages:
            return

        for page in self.pages.values():
            page.pack_forget()

        page = self.pages[pageName]
        page.pack(fill="both", expand=True)
        self.currentPage = pageName

        if pageName == "home":
            self.title(PROGRAM_NAME)
            self.updateHomeStrategyLabel()
        elif pageName == "info":
            self.title(f"{PROGRAM_NAME} - Информация")
            self.refreshInfoPage()
        elif pageName == "settings":
            self.title(f"{PROGRAM_NAME} - Параметры")
            self.refreshSettingsPage()
        elif pageName == "tests":
            self.title(f"{PROGRAM_NAME} - Проверка стратегий")
        elif pageName == "editor":
            self.title(f"{PROGRAM_NAME} - Редактор")
        elif pageName == "versions":
            self.title(f"{PROGRAM_NAME} - Версии zapret")
            if self.isLoadingVersions:
                self.versionStatusLabel.configure(
                    text="Загружаю список версий… Подождите загрузки..."
                )
            elif self.availableVersions:
                self.refreshVersionPage()
            else:
                self.refreshVersionPage()
        elif pageName == "changelog":
            self.title(f"{PROGRAM_NAME} - Что нового")
        elif pageName == "diagnostics":
            self.title(f"{PROGRAM_NAME} - Диагностика")

    def buildHeader(self, parent, titleText, backPage="home"):
        header = ctk.CTkFrame(parent, fg_color="transparent", height=58)
        header.pack(fill="x", padx=18, pady=(18, 4))
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(2, weight=1)

        if titleText == "Что нового":
            backCommand = lambda: self.showPage(self.changelogBackPage)
        else:
            backCommand = lambda: self.showPage(backPage)

        backButton = CircularButton(
            header,
            text="←",
            size=42,
            command=backCommand,
            fontFamily="Segoe UI Symbol",
            fontSize=18,
        )
        backButton.grid(row=0, column=0, sticky="w")

        titleLabel = ctk.CTkLabel(
            header,
            text=titleText,
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Segoe UI", size=23, weight="bold"),
            anchor="center",
        )
        titleLabel.grid(row=0, column=1)

        return header

    def buildHomePage(self):
        page = ctk.CTkFrame(self, fg_color=COLORS["background"], corner_radius=0)
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        topBar = ctk.CTkFrame(page, fg_color="transparent", height=42)
        topBar.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 0))
        topBar.grid_columnconfigure(0, weight=1)

        self.topStatusLabel = ctk.CTkLabel(
            topBar,
            text="",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            anchor="e",
        )
        self.topStatusLabel.grid(row=0, column=0, sticky="e")

        center = ctk.CTkFrame(page, fg_color="transparent")
        center.grid(row=1, column=0, sticky="nsew", padx=18)
        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(0, weight=1)
        center.grid_rowconfigure(2, weight=1)

        buttonHolder = ctk.CTkFrame(center, fg_color="transparent", width=264, height=264)
        buttonHolder.grid(row=1, column=0)
        buttonHolder.grid_propagate(False)
        buttonHolder.grid_columnconfigure(0, weight=1)
        buttonHolder.grid_rowconfigure(0, weight=1)

        self.mainButton = CircularButton(
            buttonHolder,
            text="Отключено",
            size=246,
            command=self.toggleService,
            fontFamily="Segoe UI",
            fontSize=24,
        )
        self.mainButton.grid(row=0, column=0)

        self.strategyStatusLabel = ctk.CTkLabel(
            center,
            text="",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=13),
        )
        self.strategyStatusLabel.grid(row=2, column=0, pady=(18, 24), sticky="s")

        bottom = ctk.CTkFrame(page, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        bottom.grid_columnconfigure(0, weight=0)
        bottom.grid_columnconfigure(1, weight=1)
        bottom.grid_columnconfigure(2, weight=0)
        bottom.grid_columnconfigure(3, weight=0)

        self.settingsButton = self.makeIconButton(
            bottom, "⚙", "Параметры", command=lambda: self.showPage("settings")
        )
        self.settingsButton.grid(row=0, column=0, sticky="w")

        self.updateButton = self.makeIconButton(
            bottom, "!", "Доступно обновление",
            command=lambda: self.showPage("settings"), accent=True
        )
        self.updateButton.grid(row=0, column=2, padx=(0, 8))

        self.infoButton = self.makeIconButton(
            bottom, "ⓘ", "Информация", command=lambda: self.showPage("info")
        )
        self.infoButton.grid(row=0, column=3, sticky="e")

        return page

    def makeIconButton(self, parent, iconText, tooltip, command, accent=False):
        button = CircularButton(
            parent,
            text=iconText,
            size=44,
            command=command,
            fontFamily="Segoe UI Symbol",
            fontSize=20,
        )
        button.setAccent(accent)
        button.tooltipText = tooltip
        return button

    def buildInfoPage(self):
        page = ctk.CTkFrame(self, fg_color=COLORS["background"], corner_radius=0)
        self.buildHeader(page, "Информация")

        card = self.makeCard(page)
        card.pack(fill="x", padx=18, pady=(0, 18))

        self.programVersionLabel = self.addInfoRow(card, "Версия программы", "")
        self.zapretVersionLabel = self.addInfoRow(card, "Версия zapret", "")

        self.makeLinkButton(card, "Репозиторий zapret", ZAPRET_GITHUB_URL)
        self.makeLinkButton(card, "GitHub проекта", PROJECT_GITHUB_URL)

        return page

    def addInfoRow(self, parent, title, value):
        titleLabel = ctk.CTkLabel(
            parent,
            text=title,
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        titleLabel.pack(fill="x", padx=20, pady=(18, 4))

        valueLabel = ctk.CTkLabel(
            parent,
            text=value,
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
            justify="left",
        )
        valueLabel.pack(fill="x", padx=20, pady=(0, 2))
        return valueLabel

    def makeLinkButton(self, parent, text, url):
        button = ctk.CTkButton(
            parent,
            text=text,
            fg_color="transparent",
            hover_color=COLORS["card2"],
            text_color=COLORS["orangeLight"],
            anchor="w",
            font=ctk.CTkFont(size=13),
            height=34,
            command=lambda: self.openUrl(url),
        )
        button.pack(fill="x", padx=14, pady=(4, 2))
        return button

    def addSectionTitle(self, parent, title):
        label = ctk.CTkLabel(
            parent,
            text=title,
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        label.pack(fill="x", padx=20, pady=(6, 8))

    def makeCard(self, parent):
        return ctk.CTkFrame(
            parent,
            fg_color=COLORS["card"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=16,
        )

    def buildSettingsPage(self):
        page = ctk.CTkFrame(self, fg_color=COLORS["background"], corner_radius=0)
        self.buildHeader(page, "Параметры")

        scroll = SmoothScrollableFrame(page)
        scroll.pack(fill="both", expand=True, padx=2, pady=(0, 10))
        content = scroll.contentFrame

        card = self.makeCard(content)
        card.pack(fill="x", padx=16, pady=(0, 12))

        self.updateInfoLabel = ctk.CTkLabel(
            card,
            text="",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
            wraplength=520,
        )
        self.updateInfoLabel.pack(fill="x", padx=20, pady=(18, 5))

        self.updateChangelogButton = ctk.CTkButton(
            card,
            text="Что нового?",
            height=34,
            corner_radius=9,
            fg_color=COLORS["button"],
            hover_color=COLORS["buttonHover"],
            text_color=COLORS["text"],
            command=self.openLatestChangelog,
        )
        self.updateChangelogButton.pack_forget()

        self.updateZapretButton = ctk.CTkButton(
            card,
            text="Обновить zapret",
            height=40,
            corner_radius=9,
            fg_color=COLORS["button"],
            hover_color=COLORS["buttonHover"],
            text_color=COLORS["text"],
            command=self.updateZapretClicked,
        )
        self.updateZapretButton.pack(fill="x", padx=20, pady=(0, 8))

        self.selectVersionButton = ctk.CTkButton(
            card,
            text="Выбрать версию",
            height=36,
            corner_radius=9,
            fg_color=COLORS["button"],
            hover_color=COLORS["buttonHover"],
            text_color=COLORS["text"],
            command=self.openVersionPage,
        )
        self.selectVersionButton.pack(fill="x", padx=20, pady=(0, 8))

        self.downloadStatusFrame = ctk.CTkFrame(card, fg_color="transparent")
        self.downloadStatusFrame.pack(fill="x", padx=20, pady=(0, 14))
        self.downloadStatusFrame.grid_columnconfigure(0, weight=1)

        self.downloadProgressFrame = ctk.CTkFrame(
            self.downloadStatusFrame,
            fg_color="transparent",
            height=22,
        )
        self.downloadProgressFrame.grid(row=0, column=0, sticky="ew")
        self.downloadProgressFrame.grid_columnconfigure(0, weight=1)

        self.downloadProgressBar = ctk.CTkProgressBar(
            self.downloadProgressFrame,
            height=8,
            corner_radius=4,
            fg_color=COLORS["button"],
            progress_color=COLORS["orange"],
        )
        self.downloadProgressBar.grid(row=0, column=0, sticky="ew", pady=6)
        self.downloadProgressBar.set(0)

        self.downloadPercentLabel = ctk.CTkLabel(
            self.downloadProgressFrame,
            text="0%",
            width=48,
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="e",
        )
        self.downloadPercentLabel.grid(row=0, column=1, padx=(12, 0))

        self.settingsStatusLabel = ctk.CTkLabel(
            self.downloadStatusFrame,
            text="",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
            wraplength=520,
        )
        self.settingsStatusLabel.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.downloadStatusFrame.pack_forget()

        self.addSectionTitle(card, "Game Filter")
        self.gameFilterSwitch = ctk.CTkSegmentedButton(
            card,
            values=["Disable", "TCP", "UDP", "TCP and UDP"],
            height=38,
            corner_radius=9,
            fg_color=COLORS["button"],
            selected_color=COLORS["orangeDark"],
            selected_hover_color="#74410F",
            unselected_color=COLORS["button"],
            unselected_hover_color=COLORS["buttonHover"],
            text_color=COLORS["muted"],
            command=self.gameFilterChanged,
        )
        self.gameFilterSwitch.pack(fill="x", padx=20, pady=(0, 15))

        self.addSectionTitle(card, "IPSet Filter")
        self.ipsetSwitch = ctk.CTkSegmentedButton(
            card,
            values=["None", "Loaded", "Any"],
            height=38,
            corner_radius=9,
            fg_color=COLORS["button"],
            selected_color=COLORS["orangeDark"],
            selected_hover_color="#74410F",
            unselected_color=COLORS["button"],
            unselected_hover_color=COLORS["buttonHover"],
            text_color=COLORS["muted"],
            command=self.ipsetChanged,
        )
        self.ipsetSwitch.pack(fill="x", padx=20, pady=(0, 15))

        self.addSectionTitle(card, "Стратегия обхода")
        self.strategyCombo = ctk.CTkOptionMenu(
            card,
            values=["Нет доступных стратегий"],
            height=40,
            corner_radius=9,
            fg_color=COLORS["card2"],
            button_color=COLORS["card2"],
            button_hover_color=COLORS["buttonHover"],
            dropdown_fg_color=COLORS["card2"],
            dropdown_hover_color=COLORS["orangeDark"],
            text_color=COLORS["text"],
            dropdown_text_color=COLORS["text"],
            command=self.strategyChanged,
        )
        self.strategyCombo.pack(fill="x", padx=20, pady=(0, 15))

        self.runTestsButton = ctk.CTkButton(
            card,
            text="Проверка стратегий",
            height=40,
            corner_radius=9,
            fg_color=COLORS["button"],
            hover_color=COLORS["buttonHover"],
            text_color=COLORS["text"],
            command=self.runTestsClicked,
        )
        self.runTestsButton.pack(fill="x", padx=20, pady=(0, 7))

        self.diagnosticsButton = ctk.CTkButton(
            card,
            text="Диагностика",
            height=40,
            corner_radius=9,
            fg_color=COLORS["button"],
            hover_color=COLORS["buttonHover"],
            text_color=COLORS["text"],
            command=self.openDiagnosticsPage,
        )
        self.diagnosticsButton.pack(fill="x", padx=20, pady=(0, 18))

        editCard = self.makeCard(content)
        editCard.pack(fill="x", padx=16, pady=(0, 12))

        self.addSectionTitle(editCard, "Пользовательские списки")
        infoLabel = ctk.CTkLabel(
            editCard,
            text=(
                "Здесь хранятся ваши добавленные адреса. Эти файлы не заменяются "
                "при обновлении zapret. Для IPSet EzZapret использует собственный "
                "ipset-all-user.txt и добавляет его строки к актуальному списку."
            ),
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
            wraplength=520,
        )
        infoLabel.pack(fill="x", padx=20, pady=(0, 10))

        # Выравниваем разделитель и описание во всех строках.
        # Используем ширину текста, а не количество символов:
        # названия файлов имеют разную ширину в обычном пропорциональном шрифте.
        listButtonFont = ctk.CTkFont(size=11)
        listTextFont = tkfont.Font(
            root=self,
            family=listButtonFont.cget("family"),
            size=listButtonFont.cget("size"),
        )
        maxFileWidth = max(
            listTextFont.measure(f"✎  {fileName}")
            for fileName in USER_EDITABLE_FILES
        )
        spaceWidth = max(listTextFont.measure(" "), 1)

        for fileName, description in USER_EDITABLE_FILES.items():
            fileWidth = listTextFont.measure(f"✎  {fileName}")
            paddingCount = max(
                2,
                int(round((maxFileWidth - fileWidth) / spaceWidth)) + 2,
            )
            padding = " " * paddingCount

            button = ctk.CTkButton(
                editCard,
                text=f"✎  {fileName}{padding}—  {description}",
                height=44,
                corner_radius=9,
                fg_color=COLORS["card2"],
                hover_color=COLORS["buttonHover"],
                text_color=COLORS["text"],
                anchor="w",
                font=listButtonFont,
                command=lambda name=fileName: self.openFileEditor(name),
            )
            button.pack(fill="x", padx=20, pady=(0, 6))

        hint = ctk.CTkLabel(
            editCard,
            text=(
                "Для удаления записи удалите её строку в редакторе. После сохранения "
                "при активном zapret служба будет перезапущена автоматически."
            ),
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            wraplength=520,
        )
        hint.pack(fill="x", padx=20, pady=(4, 10))

        backupButtons = ctk.CTkFrame(editCard, fg_color="transparent")
        backupButtons.pack(fill="x", padx=20, pady=(0, 16))
        backupButtons.grid_columnconfigure(0, weight=1)
        backupButtons.grid_columnconfigure(1, weight=1)

        self.exportSettingsButton = ctk.CTkButton(
            backupButtons,
            text="Экспорт настроек",
            height=38,
            corner_radius=9,
            fg_color=COLORS["button"],
            hover_color=COLORS["buttonHover"],
            text_color=COLORS["text"],
            command=self.exportUserSettings,
        )
        self.exportSettingsButton.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.importSettingsButton = ctk.CTkButton(
            backupButtons,
            text="Импорт настроек",
            height=38,
            corner_radius=9,
            fg_color=COLORS["button"],
            hover_color=COLORS["buttonHover"],
            text_color=COLORS["text"],
            command=self.importUserSettings,
        )
        self.importSettingsButton.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        resetCard = self.makeCard(content)
        resetCard.pack(fill="x", padx=16, pady=(0, 18))

        resetTitle = ctk.CTkLabel(
            resetCard,
            text="Сброс настроек",
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        resetTitle.pack(fill="x", padx=20, pady=(15, 5))

        resetInfo = ctk.CTkLabel(
            resetCard,
            text="Вернуть списки, Game Filter, IPSet и выбранную стратегию к стандартному состоянию установленной версии zapret.",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            wraplength=520,
        )
        resetInfo.pack(fill="x", padx=20, pady=(0, 10))

        self.resetZapretButton = ctk.CTkButton(
            resetCard,
            text="Сбросить настройки zapret",
            height=40,
            corner_radius=9,
            fg_color="#3A1717",
            hover_color="#552020",
            text_color="#FFDADA",
            command=self.resetZapretClicked,
        )
        self.resetZapretButton.pack(fill="x", padx=20, pady=(0, 16))

        return page

    def exportUserSettings(self):
        if self.isBusy or not (ZAPRET_DIR / "lists").exists():
            return
        defaultName = f"EzZapret-settings-{self.getInstalledZapretVersion() or 'backup'}.zip"
        filePath = filedialog.asksaveasfilename(
            title="Экспорт настроек EzZapret",
            defaultextension=".zip",
            initialfile=defaultName,
            filetypes=[("ZIP архив", "*.zip")],
        )
        if not filePath:
            return
        try:
            with zipfile.ZipFile(filePath, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("settings.json", json.dumps(self.settings, ensure_ascii=False, indent=2))
                listsDir = ZAPRET_DIR / "lists"
                for name in USER_LIST_FILES:
                    source = listsDir / name
                    if source.exists():
                        archive.write(source, f"lists/{name}")
            self.setTopStatus("Настройки экспортированы.")
        except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as error:
            self.showError(f"Не удалось экспортировать настройки: {error}")

    def importUserSettings(self):
        if self.isBusy:
            return
        filePath = filedialog.askopenfilename(
            title="Импорт настроек EzZapret",
            filetypes=[("ZIP архив", "*.zip")],
        )
        if not filePath:
            return
        try:
            with zipfile.ZipFile(filePath, "r") as archive:
                names = set(archive.namelist())
                settingsData = {}
                if "settings.json" in names:
                    settingsData = json.loads(archive.read("settings.json").decode("utf-8"))
                if not isinstance(settingsData, dict):
                    raise ValueError("settings.json имеет неверный формат.")

                listsDir = ZAPRET_DIR / "lists"
                listsDir.mkdir(parents=True, exist_ok=True)
                for name in USER_LIST_FILES:
                    archiveName = f"lists/{name}"
                    if archiveName in names:
                        content = archive.read(archiveName)
                        if len(content) > 2 * 1024 * 1024:
                            raise ValueError(f"Файл {name} слишком большой.")
                        (listsDir / name).write_bytes(content)

                allowedSettings = {"gameFilter", "ipset", "strategy"}
                for key in allowedSettings:
                    if key in settingsData and isinstance(settingsData[key], str):
                        self.settings[key] = settingsData[key]
                self.saveSettings()
                self.ensureUserLists()
                self.applySelectedSettingsBeforeStart()
                self.ensureValidStrategy()
                self.updateHomeStrategyLabel()
                self.refreshSettingsPage()
                if self.isRunning:
                    self.setBusy(True, "Применяю импортированные настройки…")
                    self.startWorker(self.restartCurrentServiceTask, self.onRestartFinished)
                else:
                    self.setTopStatus("Настройки импортированы.")
        except (OSError, zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
            self.showError(f"Не удалось импортировать настройки: {error}")

    def buildDiagnosticsPage(self):
        page = ctk.CTkFrame(self, fg_color=COLORS["background"], corner_radius=0)
        self.buildHeader(page, "Диагностика", "settings")

        self.diagnosticsStatusLabel = ctk.CTkLabel(
            page, text="Проверка ещё не запускалась.", text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12), anchor="w", wraplength=580
        )
        self.diagnosticsStatusLabel.pack(fill="x", padx=18, pady=(0, 8))

        self.runDiagnosticsButton = ctk.CTkButton(
            page, text="Запустить диагностику", height=40, corner_radius=9,
            fg_color=COLORS["button"], hover_color=COLORS["buttonHover"],
            text_color=COLORS["text"], command=self.runDiagnosticsClicked
        )
        self.runDiagnosticsButton.pack(fill="x", padx=18, pady=(0, 10))

        self.diagnosticsOutputBox = ctk.CTkTextbox(
            page, fg_color="#0B0A09", border_width=1,
            border_color=COLORS["border"], corner_radius=12,
            text_color="#EEE5DB", font=ctk.CTkFont(family="Consolas", size=11), wrap="word"
        )
        self.diagnosticsOutputBox.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        return page

    def openDiagnosticsPage(self):
        if self.isBusy:
            return
        self.showPage("diagnostics")
        self.runDiagnosticsClicked()

    def runDiagnosticsClicked(self):
        if self.isBusy:
            return
        self.diagnosticsOutputBox.delete("1.0", "end")
        self.diagnosticsStatusLabel.configure(text="Выполняю диагностику…")
        self.runDiagnosticsButton.configure(state="disabled")
        self.startWorker(self.runDiagnosticsTask, self.onDiagnosticsFinished)

    def runDiagnosticsTask(self, progress):
        lines = []
        def add(label, value):
            lines.append(f"{label}: {value}")
            progress(f"Проверяю: {label}")

        add("Windows", "Да" if self.isWindows() else "Нет")
        add("Права администратора", "Да" if self.isAdmin() else "Нет")
        add("Папка zapret", "Найдена" if ZAPRET_DIR.exists() else "Не найдена")
        add("service.bat", "Найден" if (ZAPRET_DIR / "service.bat").exists() else "Не найден")
        add("winws.exe", "Найден" if (ZAPRET_DIR / "bin" / "winws.exe").exists() else "Не найден")
        add("WinDivert", "Найден" if (ZAPRET_DIR / "bin" / "WinDivert.dll").exists() else "Не найден")
        add("Выбранная стратегия", self.settings.get("strategy", "general.bat"))
        gameCapability = self.getGameFilterCapability()
        gameCapabilityText = {
            "advanced": "Disable / TCP / UDP / TCP and UDP",
            "legacy": "Disable / Enable",
            "none": "Не поддерживается",
        }.get(gameCapability, "Неизвестно")
        add("Game Filter", gameCapabilityText)
        add("Служба zapret", "Запущена" if self.isServiceRunning() else "Не запущена")
        installed = self.getInstalledZapretVersion() or "Не определена"
        add("Установленная версия", installed)
        add("Последняя известная версия", self.latestVersion or "Не проверена")

        try:
            self.httpText("https://github.com")
            add("GitHub HTTPS", "Доступен")
        except Exception as error:
            add("GitHub HTTPS", f"Ошибка: {error}")

        return "\n".join(lines)

    def onDiagnosticsFinished(self, output):
        self.diagnosticsOutputBox.delete("1.0", "end")
        self.diagnosticsOutputBox.insert("1.0", output)
        self.diagnosticsStatusLabel.configure(text="Диагностика завершена.")
        self.runDiagnosticsButton.configure(state="normal")
        self.setTopStatus("Диагностика завершена.")

    def buildEditorPage(self):
        page = ctk.CTkFrame(self, fg_color=COLORS["background"], corner_radius=0)
        self.buildHeader(page, "Редактор", "settings")

        self.editorFileLabel = ctk.CTkLabel(
            page,
            text="",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        self.editorFileLabel.pack(fill="x", padx=18, pady=(0, 8))

        self.editorDescriptionLabel = ctk.CTkLabel(
            page,
            text="",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
            wraplength=580,
        )
        self.editorDescriptionLabel.pack(fill="x", padx=18, pady=(0, 6))

        self.editorPersistenceLabel = ctk.CTkLabel(
            page,
            text="",
            text_color=COLORS["orangeLight"],
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            wraplength=580,
        )
        self.editorPersistenceLabel.pack(fill="x", padx=18, pady=(0, 8))

        self.editorBox = ctk.CTkTextbox(
            page,
            fg_color="#0B0A09",
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=12,
            text_color="#EEE5DB",
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="none",
        )
        self.editorBox.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        addLineFrame = ctk.CTkFrame(page, fg_color="transparent")
        addLineFrame.pack(fill="x", padx=18, pady=(0, 10))
        addLineFrame.grid_columnconfigure(0, weight=1)

        self.editorLineEntry = ctk.CTkEntry(
            addLineFrame,
            placeholder_text="Добавить одну строку…",
            height=38,
            corner_radius=9,
            fg_color=COLORS["card2"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
        )
        self.editorLineEntry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.editorAddLineButton = ctk.CTkButton(
            addLineFrame,
            text="Добавить строку",
            width=150,
            height=38,
            corner_radius=9,
            fg_color=COLORS["orangeDark"],
            hover_color="#74410F",
            text_color=COLORS["orangeLight"],
            command=self.addEditorLine,
        )
        self.editorAddLineButton.grid(row=0, column=1)

        buttons = ctk.CTkFrame(page, fg_color="transparent")
        buttons.pack(fill="x", padx=18, pady=(0, 18))
        buttons.grid_columnconfigure(0, weight=1)
        buttons.grid_columnconfigure(1, weight=1)

        self.editorCancelButton = ctk.CTkButton(
            buttons,
            text="Отмена",
            height=40,
            corner_radius=9,
            fg_color=COLORS["button"],
            hover_color=COLORS["buttonHover"],
            command=lambda: self.showPage("settings"),
        )
        self.editorCancelButton.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.editorSaveButton = ctk.CTkButton(
            buttons,
            text="Сохранить",
            height=40,
            corner_radius=9,
            fg_color=COLORS["orangeDark"],
            hover_color="#74410F",
            text_color=COLORS["orangeLight"],
            command=self.saveFileEditor,
        )
        self.editorSaveButton.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        return page

    def buildVersionPage(self):
        page = ctk.CTkFrame(self, fg_color=COLORS["background"], corner_radius=0)
        self.buildHeader(page, "Версии zapret", "settings")

        self.versionStatusLabel = ctk.CTkLabel(
            page, text="Загрузка списка версий…", text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12), anchor="w"
        )
        self.versionStatusLabel.pack(fill="x", padx=18, pady=(0, 8))

        scroll = SmoothScrollableFrame(page)
        scroll.pack(fill="both", expand=True, padx=2, pady=(0, 10))
        self.versionListFrame = scroll.contentFrame
        self.versionButtonsFrame = ctk.CTkFrame(self.versionListFrame, fg_color="transparent")
        self.versionButtonsFrame.pack(fill="x", padx=16, pady=(0, 16))

        self.selectedVersionLabel = ctk.CTkLabel(
            page, text="", text_color=COLORS["orangeLight"],
            font=ctk.CTkFont(size=12), anchor="center"
        )
        self.selectedVersionLabel.pack(fill="x", padx=18, pady=(0, 6))

        self.downloadSelectedButton = ctk.CTkButton(
            page, text="Загрузить выбранную версию", height=40, corner_radius=9,
            fg_color=COLORS["button"], hover_color=COLORS["buttonHover"],
            text_color=COLORS["text"], command=self.downloadSelectedVersionClicked
        )
        self.downloadSelectedButton.pack(fill="x", padx=18, pady=(0, 18))
        self.downloadSelectedButton.configure(state="disabled")
        return page

    def buildChangelogPage(self):
        page = ctk.CTkFrame(self, fg_color=COLORS["background"], corner_radius=0)
        self.buildHeader(page, "Что нового", "versions")

        self.changelogVersionLabel = ctk.CTkLabel(
            page, text="", text_color=COLORS["orangeLight"],
            font=ctk.CTkFont(size=14, weight="bold"), anchor="center"
        )
        self.changelogVersionLabel.pack(fill="x", padx=18, pady=(0, 8))

        self.changelogStatusLabel = ctk.CTkLabel(
            page, text="", text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12), anchor="w", wraplength=580
        )
        self.changelogStatusLabel.pack(fill="x", padx=18, pady=(0, 8))

        self.changelogBox = ctk.CTkTextbox(
            page, fg_color="#0B0A09", border_width=1,
            border_color=COLORS["border"], corner_radius=12,
            text_color="#EEE5DB", font=ctk.CTkFont(size=12), wrap="word"
        )
        self.changelogBox.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        return page

    def refreshVersionPage(self):
        if not hasattr(self, "versionButtonsFrame"):
            return

        if self.isLoadingVersions:
            self.versionStatusLabel.configure(
                text="Загружаю список версий… Подождите загрузки..."
            )
            self.downloadSelectedButton.configure(state="disabled")
            return

        if not self.availableVersions:
            self.versionStatusLabel.configure(text="Версии пока не загружены.")
            self.selectedVersionLabel.configure(text="")
            self.downloadSelectedButton.configure(state="disabled")
            return

        self.versionStatusLabel.configure(
            text=f"Доступно версий: {len(self.availableVersions)}. Выберите нужную версию."
        )

        # При обычном выборе версии не пересоздаём весь список. Это устраняет
        # визуальное исчезновение кнопок и лишнюю работу Tkinter.
        if self.versionListBuilt and set(self.versionButtonMap) == set(self.availableVersions):
            self.updateVersionButtonStyles()
            self.updateSelectedVersionControls()
            return

        # Первый раз список строится целиком в отдельном контейнере. Пока он
        # строится, старый контейнер остаётся на месте. После завершения
        # заменяем его одним действием.
        newFrame = ctk.CTkFrame(self.versionListFrame, fg_color="transparent")
        newFrame.pack(fill="x", padx=16, pady=(0, 16))
        newFrame.pack_forget()

        newButtonMap = {}

        for version in self.availableVersions:
            row = ctk.CTkFrame(newFrame, fg_color="transparent")
            row.pack(fill="x", pady=(0, 6))
            row.grid_columnconfigure(0, weight=1)

            isSelected = version == self.selectedVersion
            versionButton = ctk.CTkButton(
                row,
                text=f"{version}  —  последняя" if version == self.latestVersion else version,
                height=42,
                corner_radius=9,
                fg_color=COLORS["orangeDark"] if isSelected else COLORS["button"],
                hover_color="#74410F" if isSelected else COLORS["buttonHover"],
                text_color=COLORS["orangeLight"] if isSelected else COLORS["text"],
                anchor="w",
                command=lambda value=version: self.selectVersion(value),
            )
            versionButton.grid(row=0, column=0, sticky="ew", padx=(0, 6))

            notesButton = ctk.CTkButton(
                row,
                text="Что нового?",
                width=116,
                height=42,
                corner_radius=9,
                fg_color=COLORS["button"],
                hover_color=COLORS["buttonHover"],
                text_color=COLORS["text"],
                command=lambda value=version: self.openChangelog(value, backPage="versions"),
            )
            notesButton.grid(row=0, column=1)
            newButtonMap[version] = versionButton

        oldFrame = self.versionButtonsFrame
        self.versionButtonsFrame = newFrame
        self.versionButtonMap = newButtonMap
        self.versionListBuilt = True
        oldFrame.destroy()
        newFrame.pack(fill="x", padx=16, pady=(0, 16))

        self.updateSelectedVersionControls()

    def updateVersionButtonStyles(self):
        for version, button in self.versionButtonMap.items():
            isSelected = version == self.selectedVersion
            button.configure(
                fg_color=COLORS["orangeDark"] if isSelected else COLORS["button"],
                hover_color="#74410F" if isSelected else COLORS["buttonHover"],
                text_color=COLORS["orangeLight"] if isSelected else COLORS["text"],
            )

    def updateSelectedVersionControls(self):
        if self.selectedVersion:
            self.selectedVersionLabel.configure(
                text=f"Выбрана версия: {self.selectedVersion}"
            )
            self.downloadSelectedButton.configure(
                state="normal" if not self.isBusy else "disabled"
            )
        else:
            self.selectedVersionLabel.configure(text="Версия не выбрана")
            self.downloadSelectedButton.configure(state="disabled")

    def openChangelog(self, version, backPage=None):
        if backPage in {"settings", "versions"}:
            self.changelogBackPage = backPage
        elif self.currentPage in {"settings", "versions"}:
            self.changelogBackPage = self.currentPage
        else:
            self.changelogBackPage = "versions"
        self.changelogOriginPage = self.changelogBackPage
        self.selectedChangelogVersion = version
        self.showPage("changelog")
        self.changelogVersionLabel.configure(text=f"zapret {version}")
        cached = self.releaseNotesCache.get(version)
        if cached:
            self.changelogStatusLabel.configure(text="Заметки релиза")
            self.changelogBox.delete("1.0", "end")
            self.changelogBox.insert("1.0", cached)
            return

        self.changelogStatusLabel.configure(text="Загружаю заметки релиза…")
        self.changelogBox.delete("1.0", "end")
        self.changelogBox.insert("1.0", "Загрузка…")
        self.startWorker(
            lambda progress: self.fetchReleaseNotes(version, progress),
            self.onChangelogLoaded,
            errorIsUpdateCheck=True,
        )

    def openLatestChangelog(self):
        if self.latestVersion:
            self.openChangelog(self.latestVersion, backPage="settings")

    def fetchReleaseNotes(self, version, progress):
        progress(f"Загружаю заметки zapret {version}…")
        encoded = urllib.parse.quote(version, safe="")
        url = f"https://github.com/{ZAPRET_OWNER}/{ZAPRET_REPO}/releases/tag/{encoded}"
        page = self.httpText(url)
        notes = self.extractReleaseNotes(page)
        if not notes:
            notes = "Для этой версии GitHub не опубликовал текст заметок релиза."
        return version, notes

    @staticmethod
    def extractReleaseNotes(page):
        from html.parser import HTMLParser

        class NotesParser(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.inNotes = False
                self.depth = 0
                self.parts = []
                self.skipDepth = 0

            def handle_starttag(self, tag, attrs):
                attrsDict = dict(attrs)
                classes = attrsDict.get("class", "")
                if not self.inNotes and "markdown-body" in classes.split():
                    self.inNotes = True
                    self.depth = 1
                    return
                if self.inNotes:
                    self.depth += 1
                    if tag in {"script", "style"}:
                        self.skipDepth = self.depth
                    if tag == "li":
                        self.parts.append("\n• ")
                    elif tag in {"p", "div", "h1", "h2", "h3", "h4", "br"}:
                        self.parts.append("\n")

            def handle_endtag(self, tag):
                if not self.inNotes:
                    return
                if self.skipDepth == self.depth:
                    self.skipDepth = 0
                if tag in {"p", "div", "h1", "h2", "h3", "h4", "li"}:
                    self.parts.append("\n")
                self.depth -= 1
                if self.depth <= 0:
                    self.inNotes = False

            def handle_data(self, data):
                if self.inNotes and not self.skipDepth:
                    self.parts.append(data)

        parser = NotesParser()
        parser.feed(page)
        text = html.unescape("".join(parser.parts))
        lines = []
        for line in text.splitlines():
            clean = re.sub(r"[ \t]+", " ", line).strip()
            if clean and (not lines or clean != lines[-1]):
                lines.append(clean)
        return "\n".join(lines).strip()

    def onChangelogLoaded(self, result):
        version, notes = result
        self.releaseNotesCache[version] = notes
        if self.selectedChangelogVersion != version:
            return
        self.changelogStatusLabel.configure(text="Заметки релиза")
        self.changelogBox.delete("1.0", "end")
        self.changelogBox.insert("1.0", notes)

    def selectVersion(self, version):
        if self.isBusy:
            return
        self.selectedVersion = version
        self.updateVersionButtonStyles()
        self.updateSelectedVersionControls()

    def openVersionPage(self):
        if self.isBusy:
            return
        if self.availableVersions:
            self.showPage("versions")
            self.refreshVersionPage()
            return

        self.isLoadingVersions = True
        self.versionStatusLabel.configure(
            text="Загружаю список версий… Подождите загрузки..."
        )
        self.selectedVersionLabel.configure(text="")
        self.downloadSelectedButton.configure(state="disabled")
        self.showPage("versions")
        self.startWorker(self.fetchAvailableVersions, self.onVersionsLoaded, errorIsUpdateCheck=True)

    def fetchAvailableVersions(self, progress):
        versions = []
        for pageNumber in range(1, 51):
            progress(f"Загружаю список версий zapret… страница {pageNumber}")
            pageUrl = f"https://github.com/{ZAPRET_OWNER}/{ZAPRET_REPO}/releases?page={pageNumber}"
            page = self.httpText(pageUrl)
            pattern = re.compile(
                rf"/Flowseal/{re.escape(ZAPRET_REPO)}/releases/tag/([^/?#\"<]+)",
                re.IGNORECASE,
            )
            pageVersions = []
            for rawVersion in pattern.findall(page):
                version = urllib.parse.unquote(html.unescape(rawVersion)).strip()
                if self.isValidVersion(version) and version not in pageVersions:
                    pageVersions.append(version)
            newVersions = [version for version in pageVersions if version not in versions]
            versions.extend(newVersions)
            if not pageVersions or not newVersions:
                break

        if not versions:
            raise RuntimeError("Не удалось получить список версий zapret с GitHub.")
        versions.sort(key=lambda value: self.parseVersion(value), reverse=True)
        return versions

    def onVersionsLoaded(self, versions):
        self.isLoadingVersions = False
        self.availableVersions = versions
        self.updateCheckError = ""
        self.refreshVersionPage()
        self.setTopStatus(f"Найдено версий zapret: {len(versions)}")

    def downloadSelectedVersionClicked(self):
        if self.isBusy or not self.selectedVersion:
            return
        installedVersion = self.getInstalledZapretVersion()
        if installedVersion == self.selectedVersion:
            self.showError(f"Версия zapret {self.selectedVersion} уже установлена.")
            return

        version = self.selectedVersion

        # Возвращаем пользователя в настройки до начала фоновой загрузки,
        # чтобы прогресс всегда был виден в одном месте.
        self.showPage("settings")
        self.showDownloadProgress()
        self.setDownloadProgress(0)
        self.settingsStatusLabel.configure(
            text=f"Подготавливаю загрузку zapret {version}…",
            text_color=COLORS["muted"],
        )
        self.setBusy(True, f"Загружаю zapret {version}…")
        self.startWorker(
            lambda progress: self.installVersionTask(version, progress),
            self.onSelectedVersionInstalled,
        )

    def installVersionTask(self, version, progress):
        progress(f"Подготавливаю zapret {version}…")
        downloadUrl, sha256Value = self.fetchReleaseAsset(version)
        release = {
            "version": version,
            "downloadUrl": downloadUrl,
            "sha256": sha256Value,
        }
        progress(f"Скачиваю zapret {version}…")
        self.downloadAndInstall(release, progress)
        return release

    def onSelectedVersionInstalled(self, release):
        self.latestVersion = self.latestVersion or release["version"]
        self.latestDownloadUrl = release["downloadUrl"]
        self.latestSha256 = release.get("sha256", "")
        self.setBusy(False, "")
        self.loadStrategies()
        self.ensureValidStrategy()
        self.refreshState()
        self.refreshInfoPage()
        self.refreshSettingsPage()
        self.setTopStatus(f"zapret установлен: {release['version']}")
        self.showPage("settings")

    def buildTestPage(self):
        page = ctk.CTkFrame(self, fg_color=COLORS["background"], corner_radius=0)
        self.buildHeader(page, "Проверка стратегий", "settings")

        self.testStatusLabel = ctk.CTkLabel(
            page,
            text="Подготовка тестирования…",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=13),
            anchor="w",
            justify="left",
        )
        self.testStatusLabel.pack(fill="x", padx=18, pady=(0, 8))

        self.testOutputBox = ctk.CTkTextbox(
            page,
            fg_color="#0B0A09",
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=12,
            text_color="#EEE5DB",
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="none",
        )
        self.testOutputBox.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        self.stopTestsButton = ctk.CTkButton(
            page,
            text="Остановить тест",
            height=40,
            corner_radius=9,
            fg_color=COLORS["button"],
            hover_color=COLORS["buttonHover"],
            command=self.stopTests,
        )
        self.stopTestsButton.pack(fill="x", padx=18, pady=(0, 18))
        self.stopTestsButton.configure(state="disabled")

        return page

    # -----------------------------
    # Settings
    # -----------------------------
    def loadSettings(self):
        defaults = {
            "gameFilter": "disabled",
            "ipset": "none",
            "strategy": "general.bat",
        }

        if not SETTINGS_FILE.exists():
            return defaults

        try:
            with SETTINGS_FILE.open("r", encoding="utf-8") as file:
                saved = json.load(file)
            if isinstance(saved, dict):
                defaults.update(saved)
        except (OSError, ValueError, TypeError):
            pass
        return defaults

    def saveSettings(self):
        tempFile = SETTINGS_FILE.with_suffix(".tmp")
        try:
            with tempFile.open("w", encoding="utf-8") as file:
                json.dump(self.settings, file, ensure_ascii=False, indent=2)
            tempFile.replace(SETTINGS_FILE)
        except OSError:
            pass

    # -----------------------------
    # Startup and update checking
    # -----------------------------
    def startStartupChecks(self):
        if not self.isWindows():
            self.showError("EzZapret рассчитан на Windows.")
            return

        if not self.isAdmin():
            self.showError("Нужны права администратора. Перезапускаю…")
            self.after(250, self.restartAsAdmin)
            return

        if not (ZAPRET_DIR / "service.bat").exists():
            self.setBusy(True, "Zapret не найден. Скачиваю последнюю версию…")
            self.startWorker(self.installLatestTask, self.onZapretInstalled)
            return

        self.ensureUserLists()
        if self.getIpSetStatus() == "loaded":
            self.syncUserIpSet()
        self.startWorker(self.fetchLatestRelease, self.onUpdateCheckFinished, errorIsUpdateCheck=True)

    def fetchLatestRelease(self, progress):
        progress("Проверяю последнюю версию zapret…")
        version = self.fetchLatestVersion()
        progress(f"Последняя версия: {version}")

        downloadUrl, sha256Value = self.fetchReleaseAsset(version)
        return {
            "version": version,
            "downloadUrl": downloadUrl,
            "sha256": sha256Value,
        }

    def fetchLatestVersion(self):
        try:
            text = self.httpText(f"{ZAPRET_VERSION_URL}?t={int(time.time())}")
            version = text.strip().splitlines()[0].strip()
            if self.isValidVersion(version):
                return version
            raise RuntimeError("GitHub вернул некорректный номер версии.")
        except Exception as firstError:
            try:
                response = self.httpOpen(ZAPRET_LATEST_URL, timeout=20)
                finalUrl = response.geturl()
                response.close()
                match = re.search(r"/releases/tag/([^/?#]+)", finalUrl)
                if match:
                    return urllib.parse.unquote(match.group(1))
            except Exception:
                pass
            raise RuntimeError(
                "Не удалось проверить последнюю версию zapret. "
                f"Источник GitHub недоступен: {firstError}"
            )

    def fetchReleaseAsset(self, version):
        assetName = f"zapret-discord-youtube-{version}.zip"
        encodedVersion = urllib.parse.quote(version, safe="")
        downloadUrl = (
            f"https://github.com/{ZAPRET_OWNER}/{ZAPRET_REPO}/releases/download/"
            f"{encodedVersion}/{urllib.parse.quote(assetName)}"
        )
        sha256Value = ""

        expandedUrl = f"{ZAPRET_ASSETS_URL}/{encodedVersion}"
        try:
            page = html.unescape(self.httpText(expandedUrl))
            hashPattern = re.compile(
                rf"{re.escape(assetName)}.*?sha256:([0-9a-fA-F]{{64}})",
                re.IGNORECASE | re.DOTALL,
            )
            hashMatch = hashPattern.search(page)
            if hashMatch:
                sha256Value = hashMatch.group(1).lower()
        except Exception:
            # The direct release URL is deterministic. SHA-256 is optional here
            # only when GitHub's assets page itself cannot be read.
            sha256Value = ""

        return downloadUrl, sha256Value

    def installLatestTask(self, progress):
        release = self.fetchLatestRelease(progress)
        progress(f"Скачиваю zapret {release['version']}…")
        self.downloadAndInstall(release, progress)
        return release

    def onZapretInstalled(self, release):
        self.setBusy(False, "")
        self.latestVersion = release["version"]
        self.latestDownloadUrl = release["downloadUrl"]
        self.latestSha256 = release.get("sha256", "")
        self.updateCheckError = ""
        self.loadStrategies()
        self.ensureValidStrategy()
        self.refreshState()
        self.refreshInfoPage()
        self.refreshSettingsPage()
        self.setTopStatus(f"zapret {release['version']} готов")

    def onUpdateCheckFinished(self, release):
        self.setBusy(False, "")
        self.latestVersion = release["version"]
        self.latestDownloadUrl = release["downloadUrl"]
        self.latestSha256 = release.get("sha256", "")
        self.updateCheckError = ""
        self.refreshState()
        self.refreshInfoPage()
        self.refreshSettingsPage()

        installedVersion = self.getInstalledZapretVersion()
        if installedVersion and self.isVersionNewer(self.latestVersion, installedVersion):
            self.setTopStatus(f"Доступно обновление zapret: {self.latestVersion}")
        else:
            self.setTopStatus("Версия zapret актуальна")

    # -----------------------------
    # GitHub download helpers
    # -----------------------------
    def getWindowsSslContext(self):
        context = ssl.create_default_context()

        if not hasattr(ssl, "enum_certificates"):
            return context

        certificates = []
        seenCertificates = set()

        for storeName in ("ROOT", "CA"):
            try:
                entries = ssl.enum_certificates(storeName)
            except OSError:
                continue

            for certificate, encoding, trust in entries:
                if encoding != "x509_asn":
                    continue

                try:
                    certificatePem = ssl.DER_cert_to_PEM_cert(certificate)
                except ValueError:
                    continue

                if certificatePem in seenCertificates:
                    continue

                seenCertificates.add(certificatePem)
                certificates.append(certificatePem)

        if certificates:
            try:
                context.load_verify_locations(cadata="".join(certificates))
            except ssl.SSLError:
                pass

        return context

    def httpOpen(self, url, timeout=20):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": f"{PROGRAM_NAME}/{PROGRAM_VERSION}",
                "Accept": "*/*",
                "Cache-Control": "no-cache",
            },
        )
        try:
            context = self.getWindowsSslContext()
            return urllib.request.urlopen(request, timeout=timeout, context=context)
        except urllib.error.HTTPError as error:
            if error.code == 403:
                raise RuntimeError(
                    "GitHub ответил 403. Это ограничение доступа GitHub, "
                    "а не ошибка установленной версии."
                ) from error
            raise RuntimeError(f"GitHub HTTP {error.code}: {error.reason}") from error
        except urllib.error.URLError as error:
            reason = error.reason
            reasonText = str(reason)
            if "CERTIFICATE_VERIFY_FAILED" in reasonText or "certificate verify failed" in reasonText.lower():
                raise RuntimeError(
                    "GitHub не прошёл проверку SSL-сертификата. "
                    "Возможна проблема с доверенными сертификатами Windows, VPN или HTTPS-фильтрацией. "
                    "Проверьте подключение и сертификаты системы."
                ) from error
            raise RuntimeError(f"Ошибка сети: {reason}") from error

    def httpText(self, url):
        with self.httpOpen(url, timeout=20) as response:
            return response.read().decode("utf-8", errors="replace")

    def downloadFile(self, url, targetFile, progress):
        progress("Скачивание: 0%")
        with self.httpOpen(url, timeout=60) as response, targetFile.open("wb") as output:
            total = int(response.headers.get("Content-Length", "0") or 0)
            downloaded = 0

            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                downloaded += len(chunk)

                if total:
                    percent = min(int(downloaded * 100 / total), 100)
                    progress(f"Скачивание: {percent}%")
                else:
                    progress(f"Скачано: {downloaded // 1024} КБ")

        progress("Скачивание: 100%")

    def downloadAndInstall(self, release, progress):
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR, ignore_errors=True)
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

        archiveName = f"zapret-{release['version']}.zip"
        archiveFile = TEMP_DIR / archiveName
        extractDir = TEMP_DIR / "extracted"
        extractDir.mkdir(parents=True, exist_ok=True)

        self.downloadFile(release["downloadUrl"], archiveFile, progress)
        if not zipfile.is_zipfile(archiveFile):
            raise RuntimeError("Скачанный файл не является корректным ZIP-архивом.")
        self.verifySha256(archiveFile, release.get("sha256", ""))

        progress("Распаковываю архив…")
        self.safeExtractZip(archiveFile, extractDir)
        sourceDir = self.findZapretRoot(extractDir)

        wasRunning = self.isServiceRunning()
        savedUserFiles = self.saveUserFiles() if ZAPRET_DIR.exists() else {}

        if wasRunning:
            progress("Останавливаю службу перед обновлением…")
            self.removeServiceSilently()

        backupDir = TEMP_DIR / "old_zapret"
        if backupDir.exists():
            shutil.rmtree(backupDir, ignore_errors=True)

        if ZAPRET_DIR.exists():
            ZAPRET_DIR.rename(backupDir)

        try:
            shutil.copytree(sourceDir, ZAPRET_DIR)
        except Exception:
            if ZAPRET_DIR.exists():
                shutil.rmtree(ZAPRET_DIR, ignore_errors=True)
            if backupDir.exists():
                backupDir.rename(ZAPRET_DIR)
            raise

        try:
            self.restoreUserFiles(savedUserFiles)
            self.ensureUserLists()
            self.applyGameFilterFile(self.settings.get("gameFilter", "disabled"))
            self.applyIpSetMode(self.settings.get("ipset", "none"), downloadLoadedList=False)
            if wasRunning:
                progress("Возвращаю выбранную стратегию…")
                self.installSelectedServiceSilently()
        except Exception:
            if self.isServiceRunning():
                self.removeServiceSilently()
            if ZAPRET_DIR.exists():
                shutil.rmtree(ZAPRET_DIR, ignore_errors=True)
            if backupDir.exists():
                backupDir.rename(ZAPRET_DIR)
            raise
        finally:
            shutil.rmtree(TEMP_DIR, ignore_errors=True)

    def verifySha256(self, filePath, expectedHash):
        if not expectedHash:
            return

        hasher = hashlib.sha256()
        with filePath.open("rb") as file:
            while True:
                chunk = file.read(1024 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)

        actualHash = hasher.hexdigest().lower()
        if actualHash != expectedHash.lower():
            raise RuntimeError("Проверка SHA-256 архива не прошла.")

    def safeExtractZip(self, archiveFile, extractDir):
        with zipfile.ZipFile(archiveFile) as archive:
            root = extractDir.resolve()
            for item in archive.infolist():
                destination = (extractDir / item.filename).resolve()
                if destination != root and root not in destination.parents:
                    raise RuntimeError("Архив содержит небезопасный путь.")
            archive.extractall(extractDir)

    def findZapretRoot(self, extractDir):
        candidates = [extractDir, *extractDir.iterdir()]
        for candidate in candidates:
            if self.isZapretRoot(candidate):
                return candidate

        for serviceFile in extractDir.rglob("service.bat"):
            if self.isZapretRoot(serviceFile.parent):
                return serviceFile.parent

        raise RuntimeError("Не удалось найти распакованный zapret с bin/winws.exe.")

    def isZapretRoot(self, folder):
        return (
            folder.is_dir()
            and (folder / "service.bat").exists()
            and (folder / "bin" / "winws.exe").exists()
        )

    def saveUserFiles(self):
        saved = {}
        listsDir = ZAPRET_DIR / "lists"
        if not listsDir.exists():
            return saved

        for fileName in USER_LIST_FILES:
            filePath = listsDir / fileName
            if filePath.is_file():
                saved[fileName] = filePath.read_bytes()
        return saved

    def restoreUserFiles(self, saved):
        listsDir = ZAPRET_DIR / "lists"
        listsDir.mkdir(parents=True, exist_ok=True)
        for name, content in saved.items():
            if name in USER_LIST_FILES:
                (listsDir / name).write_bytes(content)

    # -----------------------------
    # GUI state
    # -----------------------------
    def refreshState(self):
        self.isRunning = self.isServiceRunning()
        self.mainButton.setText("Включено" if self.isRunning else "Отключено")
        self.mainButton.setRunning(self.isRunning)
        self.updateHomeStrategyLabel()

        installedVersion = self.getInstalledZapretVersion()
        hasUpdate = (
            bool(installedVersion)
            and bool(self.latestVersion)
            and self.isVersionNewer(self.latestVersion, installedVersion)
        )
        self.updateButton.grid() if hasUpdate else self.updateButton.grid_remove()

    def updateHomeStrategyLabel(self, selectedStrategy=None):
        if not hasattr(self, "strategyStatusLabel"):
            return

        if selectedStrategy:
            strategy = selectedStrategy
        elif getattr(self, "isRunning", False):
            strategy = self.getInstalledStrategyName()
        else:
            strategy = self.settings.get("strategy", "general.bat")

        strategy = strategy or "general.bat"
        self.strategyStatusLabel.configure(text=f"Стратегия: {strategy}")

    def refreshInfoPage(self):
        if not hasattr(self, "programVersionLabel"):
            return

        self.programVersionLabel.configure(text=PROGRAM_VERSION)
        installedVersion = self.getInstalledZapretVersion()

        if not installedVersion:
            self.zapretVersionLabel.configure(text="Не установлен")
            return

        text = installedVersion
        if self.latestVersion and self.isVersionNewer(self.latestVersion, installedVersion):
            text += f"\nДоступно обновление: {self.latestVersion}"
        elif self.updateCheckError:
            text += f"\nПроверка обновления: {self.updateCheckError}"
        self.zapretVersionLabel.configure(text=text)

    def refreshSettingsPage(self):
        if not hasattr(self, "strategyCombo"):
            return

        actualGameFilter = self.getGameFilterStatus()
        actualIpSet = self.getIpSetStatus()
        self.settings["gameFilter"] = actualGameFilter
        self.settings["ipset"] = actualIpSet

        gameNames = {
            "disabled": "Disable",
            "enabled": "TCP and UDP",
            "tcp": "TCP",
            "udp": "UDP",
            "all": "TCP and UDP",
        }
        self.gameFilterSwitch.configure(values=["Disable", "TCP", "UDP", "TCP and UDP"])
        self.gameFilterSwitch.set(gameNames.get(actualGameFilter, "Disable"))

        ipsetNames = {"none": "None", "loaded": "Loaded", "any": "Any"}
        self.ipsetSwitch.set(ipsetNames.get(actualIpSet, "Loaded"))

        self.loadStrategies()
        selectedStrategy = self.settings.get("strategy", "general.bat")
        strategies = self.getStrategyList()
        if strategies:
            self.strategyCombo.set(selectedStrategy if selectedStrategy in strategies else strategies[0])
        else:
            self.strategyCombo.set("Нет доступных стратегий")

        if self.updateCheckError:
            self.updateInfoLabel.configure(
                text=f"Проверка обновления не выполнена: {self.updateCheckError}",
                text_color=COLORS["red"],
            )
            self.updateChangelogButton.pack_forget()
        else:
            installedVersion = self.getInstalledZapretVersion()
            if self.latestVersion and installedVersion and self.isVersionNewer(
                self.latestVersion, installedVersion
            ):
                self.updateInfoLabel.configure(
                    text=f"Доступна новая версия: {self.latestVersion}",
                    text_color=COLORS["orangeLight"],
                )
                self.updateChangelogButton.pack(
                    before=self.updateZapretButton,
                    fill="x",
                    padx=20,
                    pady=(0, 8),
                )
            elif self.latestVersion:
                self.updateInfoLabel.configure(
                    text="Установлена последняя доступная версия.",
                    text_color=COLORS["muted"],
                )
                self.updateChangelogButton.pack_forget()
            else:
                self.updateInfoLabel.configure(
                    text="Версия zapret пока не проверена.",
                    text_color=COLORS["muted"],
                )

        ready = not self.isBusy and (ZAPRET_DIR / "service.bat").exists()
        self.updateZapretButton.configure(state="normal" if ready else "disabled")
        self.selectVersionButton.configure(state="normal" if ready and not self.isBusy else "disabled")
        self.runTestsButton.configure(state="normal" if ready else "disabled")
        self.diagnosticsButton.configure(state="normal" if not self.isBusy else "disabled")
        self.resetZapretButton.configure(state="normal" if ready else "disabled")
        self.exportSettingsButton.configure(state="normal" if ready else "disabled")
        self.importSettingsButton.configure(state="normal" if not self.isBusy else "disabled")
        self.gameFilterSwitch.configure(state="normal" if not self.isBusy else "disabled")
        self.ipsetSwitch.configure(state="normal" if not self.isBusy else "disabled")
        self.strategyCombo.configure(state="normal" if not self.isBusy else "disabled")

    def loadStrategies(self):
        strategies = self.getStrategyList()
        if not strategies:
            strategies = ["Нет доступных стратегий"]
        try:
            self.strategyCombo.configure(values=strategies)
        except tk.TclError:
            pass

    def ensureValidStrategy(self):
        strategies = self.getStrategyList()
        if not strategies:
            return
        selected = self.settings.get("strategy")
        if selected not in strategies:
            self.settings["strategy"] = "general.bat" if "general.bat" in strategies else strategies[0]
            self.saveSettings()
            if hasattr(self, "strategyStatusLabel") and not self.isRunning:
                self.strategyStatusLabel.configure(
                    text=f"Стратегия: {self.settings['strategy']}",
                    text_color=COLORS["muted"],
                )

    # -----------------------------
    # Service control
    # -----------------------------
    def toggleService(self):
        if self.isBusy:
            return

        if not (ZAPRET_DIR / "service.bat").exists():
            self.showError("Папка zapret ещё не готова.")
            return

        if self.isServiceRunning():
            self.runServiceAction("remove")
        else:
            self.runServiceAction("install")

    def runServiceAction(self, action):
        self.setBusy(True, "Запускаю…" if action == "install" else "Выключаю…")
        self.startWorker(
            lambda progress: self.serviceActionTask(action, progress),
            lambda result: self.onServiceActionFinished(action, result),
        )

    def serviceActionTask(self, action, progress):
        if action == "remove":
            progress("Удаляю службу zapret…")
            self.removeServiceSilently()
            return False

        progress("Подготавливаю настройки zapret…")
        self.ensureUserLists()
        self.applySelectedSettingsBeforeStart()

        strategy = self.settings.get("strategy", "general.bat")
        progress(f"Устанавливаю стратегию {strategy}…")
        self.removeServiceSilently()
        self.installSelectedServiceDirect()
        return True

    def onServiceActionFinished(self, _action, _result):
        self.setBusy(False, "")
        self.refreshState()
        self.refreshInfoPage()
        self.refreshSettingsPage()
        self.setTopStatus("Включено" if self.isRunning else "Выключено")

    def buildStrategyServiceCommand(self, strategyName):
        strategyFile = ZAPRET_DIR / strategyName
        if not strategyFile.exists():
            raise RuntimeError(f"Файл стратегии не найден: {strategyName}")

        text = strategyFile.read_text(encoding="utf-8", errors="ignore")
        logicalLines = []
        currentLine = ""

        for rawLine in text.splitlines():
            line = rawLine.strip()
            if not line or line.startswith("::"):
                continue

            if currentLine:
                currentLine += " " + line
            else:
                currentLine = line

            if currentLine.endswith("^"):
                currentLine = currentLine[:-1].rstrip()
                continue

            logicalLines.append(currentLine)
            currentLine = ""

        if currentLine:
            logicalLines.append(currentLine)

        commandLine = ""
        for line in logicalLines:
            match = re.search(r'(?i)"?%BIN%[\\/]*winws\.exe"?\s+(.+)$', line)
            if match:
                commandLine = match.group(1).strip()
                break

        if not commandLine:
            raise RuntimeError(
                f"Не удалось найти команду winws.exe в стратегии {strategyName}."
            )

        binPath = str((ZAPRET_DIR / "bin").resolve()) + "\\"
        listsPath = str((ZAPRET_DIR / "lists").resolve()) + "\\"
        gameFilterTcp, gameFilterUdp = self.getGameFilterValues()
        gameFilterValue = gameFilterTcp if gameFilterTcp != "12" else gameFilterUdp

        commandLine = commandLine.replace("%BIN%", binPath)
        commandLine = commandLine.replace("%LISTS%", listsPath)
        commandLine = commandLine.replace("%GameFilterTCP%", gameFilterTcp)
        commandLine = commandLine.replace("%GameFilterUDP%", gameFilterUdp)
        commandLine = commandLine.replace("%GameFilter%", gameFilterValue)
        commandLine = commandLine.replace("%~dp0", str(ZAPRET_DIR.resolve()) + "\\")

        winwsPath = str((ZAPRET_DIR / "bin" / "winws.exe").resolve())
        return f'"{winwsPath}" {commandLine}'

    def getGameFilterValues(self):
        mode = self.getGameFilterStatus()
        if mode == "unsupported":
            return "12", "12"

        tcpRange = DEFAULT_GAME_TCP
        udpRange = DEFAULT_GAME_UDP

        flagFile = self.getGameFilterFile()
        if self.getGameFilterCapability() == "legacy":
            if mode == "enabled":
                return DEFAULT_GAME_TCP, DEFAULT_GAME_UDP
            return "12", "12"

        if flagFile.exists():
            try:
                text = flagFile.read_text(encoding="utf-8", errors="ignore")
                tcpMatch = re.search(r"^tcp=(.+)$", text, re.MULTILINE | re.IGNORECASE)
                udpMatch = re.search(r"^udp=(.+)$", text, re.MULTILINE | re.IGNORECASE)
                if tcpMatch:
                    tcpRange = tcpMatch.group(1).strip()
                if udpMatch:
                    udpRange = udpMatch.group(1).strip()
            except OSError:
                pass

        if mode == "tcp":
            return tcpRange, "12"
        if mode == "udp":
            return "12", udpRange
        if mode == "all":
            return tcpRange, udpRange
        return "12", "12"

    def installSelectedServiceDirect(self):
        strategy = self.settings.get("strategy", "general.bat")
        if strategy not in self.getStrategyList():
            raise RuntimeError("Не удалось найти выбранную стратегию.")

        serviceCommand = self.buildStrategyServiceCommand(strategy)
        self.runCommand(["netsh", "interface", "tcp", "set", "global", "timestamps=enabled"], check=False)

        self.runCommand(
            [
                "sc",
                "create",
                SERVICE_NAME,
                "binPath=",
                serviceCommand,
                "DisplayName=",
                "zapret",
                "start=",
                "auto",
            ],
            check=True,
        )
        self.runCommand(
            ["sc", "description", SERVICE_NAME, "Zapret DPI bypass software"],
            check=False,
        )
        self.runCommand(
            [
                "reg",
                "add",
                rf"HKLM\System\CurrentControlSet\Services\{SERVICE_NAME}",
                "/v",
                "zapret-discord-youtube",
                "/t",
                "REG_SZ",
                "/d",
                Path(strategy).stem,
                "/f",
            ],
            check=True,
        )
        self.runCommand(["sc", "start", SERVICE_NAME], check=True)

        for _ in range(25):
            if self.isServiceRunning():
                return
            time.sleep(0.4)

        raise RuntimeError("Служба создана, но не перешла в состояние RUNNING.")

    def runCommand(self, command, check=False, timeout=30):
        startupInfo = subprocess.STARTUPINFO()
        startupInfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupInfo.wShowWindow = subprocess.SW_HIDE

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="cp866",
            errors="ignore",
            startupinfo=startupInfo,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=timeout,
        )
        output = (result.stdout + "\n" + result.stderr).strip()
        if check and result.returncode != 0:
            raise RuntimeError(output or f"Команда завершилась с кодом {result.returncode}.")
        return result.returncode, output

    def isServiceRunning(self):
        try:
            result = subprocess.run(
                ["sc", "query", SERVICE_NAME],
                capture_output=True,
                text=True,
                encoding="cp866",
                errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5,
            )
            return result.returncode == 0 and "RUNNING" in result.stdout
        except (OSError, subprocess.TimeoutExpired):
            return False

    def getInstalledStrategyName(self):
        try:
            result = subprocess.run(
                [
                    "reg",
                    "query",
                    rf"HKLM\System\CurrentControlSet\Services\{SERVICE_NAME}",
                    "/v",
                    "zapret-discord-youtube",
                ],
                capture_output=True,
                text=True,
                encoding="cp866",
                errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5,
            )
            if result.returncode == 0:
                match = re.search(r"zapret-discord-youtube\s+REG_SZ\s+(.*)", result.stdout)
                if match:
                    return match.group(1).strip() + ".bat"
        except (OSError, subprocess.TimeoutExpired):
            pass
        return ""

    def getStrategyList(self):
        if not ZAPRET_DIR.exists():
            return []
        strategies = [
            path.name
            for path in ZAPRET_DIR.glob("*.bat")
            if path.name.lower() != "service.bat"
        ]
        strategies.sort(key=self.naturalSortKey)
        return strategies

    @staticmethod
    def naturalSortKey(value):
        return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]

    # -----------------------------
    # Game Filter and IPSet
    # -----------------------------
    def getGameFilterCapability(self):
        """Return the internal Game Filter format used by the installed zapret.

        The settings UI intentionally stays the same for every version. This
        method is only used internally to write the correct file format.
        """
        serviceFile = ZAPRET_DIR / "service.bat"
        utilsFile = ZAPRET_DIR / "utils" / "game_filter.enabled"
        legacyFile = ZAPRET_DIR / "bin" / "game_filter.enabled"

        if utilsFile.exists():
            return "advanced"
        if legacyFile.exists():
            return "legacy"

        if serviceFile.exists():
            try:
                text = serviceFile.read_text(encoding="utf-8", errors="ignore").lower()
            except OSError:
                text = ""

            if "gamefiltertcp" in text or "gamefilterudp" in text or "utils\\game_filter.enabled" in text:
                return "advanced"
            if "%gamefilter%" in text or "game_switch_status" in text or "bin\\game_filter.enabled" in text:
                return "legacy"

        # Newer Flowseal bundles use the advanced file format. If a version
        # has not created the file yet and its script is not explicit, prefer
        # the advanced format instead of breaking the UI with "Unavailable".
        if (ZAPRET_DIR / "utils").exists():
            return "advanced"
        return "legacy"

    def getGameFilterModes(self):
        # Keep one stable UI across zapret releases. The internal capability
        # only decides how the selected value is stored/applied.
        return ["Disable", "TCP", "UDP", "TCP and UDP"]

    def getGameFilterFile(self):
        capability = self.getGameFilterCapability()
        if capability == "legacy":
            return ZAPRET_DIR / "bin" / "game_filter.enabled"
        return ZAPRET_DIR / "utils" / "game_filter.enabled"

    def getGameFilterStatus(self):
        capability = self.getGameFilterCapability()
        flagFile = self.getGameFilterFile()

        if capability == "legacy":
            return "enabled" if flagFile.exists() else "disabled"

        if not flagFile.exists():
            return "disabled"

        try:
            text = flagFile.read_text(encoding="utf-8", errors="ignore")
            match = re.search(r"^mode=(.+)$", text, re.MULTILINE | re.IGNORECASE)
            if match:
                mode = match.group(1).strip().lower()
                if mode in {"disabled", "tcp", "udp", "all"}:
                    return mode
        except OSError:
            pass
        return "disabled"

    def applyGameFilterFile(self, mode):
        capability = self.getGameFilterCapability()
        flagFile = self.getGameFilterFile()
        flagFile.parent.mkdir(parents=True, exist_ok=True)

        if mode not in {"disabled", "tcp", "udp", "all", "enabled"}:
            raise RuntimeError("Неизвестный режим Game Filter.")

        if capability == "legacy":
            enabled = mode not in {"disabled"}
            if enabled:
                flagFile.write_text("ENABLED\n", encoding="utf-8")
            else:
                flagFile.unlink(missing_ok=True)
            return

        tcpRange = DEFAULT_GAME_TCP
        udpRange = DEFAULT_GAME_UDP
        if flagFile.exists():
            try:
                text = flagFile.read_text(encoding="utf-8", errors="ignore")
                tcpMatch = re.search(r"^tcp=(.+)$", text, re.MULTILINE | re.IGNORECASE)
                udpMatch = re.search(r"^udp=(.+)$", text, re.MULTILINE | re.IGNORECASE)
                if tcpMatch:
                    tcpRange = tcpMatch.group(1).strip()
                if udpMatch:
                    udpRange = udpMatch.group(1).strip()
            except OSError:
                pass

        if mode == "disabled":
            flagFile.unlink(missing_ok=True)
            return

        if mode == "enabled":
            mode = "all"

        flagFile.write_text(
            f"mode={mode}\n"
            f"tcp={tcpRange}\n"
            f"udp={udpRange}\n",
            encoding="utf-8",
        )

    def getIpSetStatus(self):
        listFile = ZAPRET_DIR / "lists" / "ipset-all.txt"
        if not listFile.exists():
            return "none"
        try:
            content = listFile.read_text(encoding="utf-8", errors="ignore").strip()
        except OSError:
            return "none"
        if not content:
            return "any"
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if lines == [IPSET_SENTINEL]:
            return "none"
        return "loaded"

    def applyIpSetMode(self, mode, downloadLoadedList=True):
        listsDir = ZAPRET_DIR / "lists"
        listsDir.mkdir(parents=True, exist_ok=True)
        listFile = listsDir / "ipset-all.txt"
        backupFile = listsDir / "ipset-all.txt.backup"

        if mode == "loaded":
            if listFile.exists() and self.getIpSetStatus() == "loaded":
                self.syncUserIpSet()
                return
            if backupFile.exists():
                if listFile.exists():
                    listFile.unlink()
                backupFile.rename(listFile)
                self.syncUserIpSet()
                return
            if downloadLoadedList:
                self.downloadIpSetTo(listFile)
                self.syncUserIpSet()
                return
            if listFile.exists() and self.getIpSetStatus() == "any":
                raise RuntimeError("Не удалось восстановить сохранённый IPSet.")
            self.downloadIpSetTo(listFile)
            self.syncUserIpSet()
            return

        if mode == "none":
            if listFile.exists() and self.getIpSetStatus() == "loaded":
                shutil.copy2(listFile, backupFile)
            listFile.write_text(IPSET_SENTINEL + "\n", encoding="utf-8")
            return

        if mode == "any":
            if listFile.exists() and self.getIpSetStatus() == "loaded":
                shutil.copy2(listFile, backupFile)
            listFile.write_text("", encoding="utf-8")
            return

        raise RuntimeError("Неизвестный режим IPSet.")

    def downloadIpSetTo(self, targetFile):
        with self.httpOpen(ZAPRET_IPSET_URL, timeout=30) as response:
            content = response.read()
        if not content.strip():
            raise RuntimeError("GitHub вернул пустой IPSet.")
        targetFile.write_bytes(content)

    def syncUserIpSet(self):
        """Merge EzZapret's persistent IP additions into the active IPSet file."""
        listsDir = ZAPRET_DIR / "lists"
        listFile = listsDir / "ipset-all.txt"
        userFile = listsDir / "ipset-all-user.txt"
        if not listFile.exists() or not userFile.exists():
            return

        currentLines = listFile.read_text(encoding="utf-8", errors="ignore").splitlines()
        userLines = userFile.read_text(encoding="utf-8", errors="ignore").splitlines()

        oldUserLines = getattr(self, "lastUserIpSetLines", set())
        userValues = {
            line.strip()
            for line in userLines
            if line.strip() and not line.lstrip().startswith("#")
        }
        currentValues = [line.strip() for line in currentLines if line.strip()]

        if currentValues == [IPSET_SENTINEL] or not currentValues:
            return

        filtered = [line for line in currentValues if line not in oldUserLines]
        existing = set(filtered)
        for line in userValues:
            if line not in existing:
                filtered.append(line)
                existing.add(line)

        if filtered != currentValues:
            listFile.write_text("\n".join(filtered) + "\n", encoding="utf-8")

        self.lastUserIpSetLines = userValues

    def gameFilterChanged(self, selected):
        names = {
            "Disable": "disabled",
            "TCP": "tcp",
            "UDP": "udp",
            "TCP and UDP": "all",
        }
        mode = names.get(selected)
        if mode is None:
            return
        self.applySettingsAndRestart("gameFilter", mode)

    def ipsetChanged(self, selected):
        names = {"None": "none", "Loaded": "loaded", "Any": "any"}
        mode = names.get(selected, "loaded")
        self.applySettingsAndRestart("ipset", mode)

    def applySettingsAndRestart(self, settingName, value):
        oldValue = self.settings.get(settingName)
        self.settings[settingName] = value
        self.saveSettings()

        try:
            if settingName == "gameFilter":
                self.applyGameFilterFile(value)
            elif settingName == "ipset":
                self.applyIpSetMode(value)
        except Exception as error:
            self.settings[settingName] = oldValue
            self.saveSettings()
            self.showError(str(error))
            self.refreshSettingsPage()
            return

        if self.isRunning:
            self.setBusy(True, "Перезапускаю zapret для применения настроек…")
            self.startWorker(self.restartCurrentServiceTask, self.onRestartFinished)
        else:
            self.settingsStatusLabel.configure(text="Настройка сохранена.", text_color=COLORS["muted"])

    def strategyChanged(self, selected):
        if selected == "Нет доступных стратегий" or not selected:
            return
        oldValue = self.settings.get("strategy")
        self.settings["strategy"] = selected
        self.saveSettings()
        self.ensureValidStrategy()
        self.updateHomeStrategyLabel(selected)
        self.strategyStatusLabel.configure(text_color=COLORS["muted"])
        self.setTopStatus(f"Выбрана стратегия: {selected}")

        if oldValue != selected and self.isRunning:
            self.setBusy(True, "Перезапускаю zapret с новой стратегией…")
            self.startWorker(self.restartCurrentServiceTask, self.onRestartFinished)
        else:
            self.settingsStatusLabel.configure(
                text=f"Выбрана стратегия: {selected}",
                text_color=COLORS["muted"],
            )

    def restartCurrentServiceTask(self, progress):
        progress("Останавливаю текущую стратегию…")
        self.removeServiceSilently()
        progress("Запускаю выбранную стратегию…")
        self.installSelectedServiceSilently()
        return True

    def onRestartFinished(self, _result):
        self.setBusy(False, "")
        self.refreshState()
        self.refreshSettingsPage()
        self.settingsStatusLabel.configure(
            text="Настройка применена.", text_color=COLORS["muted"]
        )

    # -----------------------------
    # List editor
    # -----------------------------
    def openFileEditor(self, fileName):
        if fileName not in USER_EDITABLE_FILES:
            return
        if self.isBusy:
            return

        filePath = ZAPRET_DIR / "lists" / fileName
        try:
            content = filePath.read_text(encoding="utf-8", errors="replace") if filePath.exists() else ""
        except OSError as error:
            self.showError(f"Не удалось открыть {fileName}: {error}")
            return

        self.editorFileName = fileName
        self.editorFileLabel.configure(text=f"lists\\{fileName}")
        self.editorDescriptionLabel.configure(text=USER_EDITABLE_FILES[fileName])
        if fileName == "ipset-all-user.txt":
            persistenceText = "Файл EzZapret: его строки сохраняются и добавляются к актуальному IPSet."
        else:
            persistenceText = "Пользовательский файл: не заменяется при обновлении zapret."
        self.editorPersistenceLabel.configure(text=persistenceText)
        self.editorLineEntry.delete(0, "end")
        self.editorBox.delete("1.0", "end")
        self.editorBox.insert("1.0", content)
        self.showPage("editor")

    def addEditorLine(self):
        fileName = getattr(self, "editorFileName", "")
        if fileName not in USER_EDITABLE_FILES or self.isBusy:
            return

        line = self.editorLineEntry.get().strip()
        if not line:
            return

        currentText = self.editorBox.get("1.0", "end-1c")
        if currentText and not currentText.endswith("\n"):
            currentText += "\n"
        self.editorBox.delete("1.0", "end")
        self.editorBox.insert("1.0", currentText + line + "\n")
        self.editorLineEntry.delete(0, "end")
        self.editorBox.see("end")

    def saveFileEditor(self):
        fileName = getattr(self, "editorFileName", "")
        if fileName not in USER_EDITABLE_FILES:
            return

        filePath = ZAPRET_DIR / "lists" / fileName
        tempPath = filePath.with_suffix(filePath.suffix + ".tmp")
        content = self.editorBox.get("1.0", "end-1c")

        try:
            filePath.parent.mkdir(parents=True, exist_ok=True)
            tempPath.write_text(content + "\n", encoding="utf-8")
            tempPath.replace(filePath)
        except OSError as error:
            self.showError(f"Не удалось сохранить {fileName}: {error}")
            return

        if fileName == "ipset-all-user.txt" and self.getIpSetStatus() == "loaded":
            self.syncUserIpSet()

        self.showPage("settings")
        self.refreshSettingsPage()
        if self.isRunning:
            self.setBusy(True, "Перезапускаю zapret для применения списка…")
            self.startWorker(self.restartCurrentServiceTask, self.onRestartFinished)
        else:
            self.settingsStatusLabel.configure(
                text=f"Файл {fileName} сохранён.", text_color=COLORS["muted"]
            )
            self.showPage("settings")

    # -----------------------------
    # Reset
    # -----------------------------
    def resetZapretClicked(self):
        if self.isBusy:
            return
        if not (ZAPRET_DIR / "service.bat").exists():
            self.showError("Папка zapret ещё не готова.")
            return
        self.showResetConfirmation()

    def showResetConfirmation(self):
        if hasattr(self, "resetOverlay") and self.resetOverlay.winfo_exists():
            return

        overlay = ctk.CTkFrame(
            self,
            fg_color=COLORS["background"],
            corner_radius=0,
        )
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.resetOverlay = overlay

        card = self.makeCard(overlay)
        card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.82)

        titleLabel = ctk.CTkLabel(
            card,
            text="Сбросить настройки?",
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        titleLabel.pack(fill="x", padx=20, pady=(20, 8))

        messageLabel = ctk.CTkLabel(
            card,
            text=(
                "Все изменения в list-general, ipset-all, list-exclude и ipset-exclude "
                "будут заменены стандартными файлами zapret. Также сбросятся Game Filter, "
                "IPSet и выбранная стратегия. Это действие нельзя отменить."
            ),
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
            wraplength=460,
        )
        messageLabel.pack(fill="x", padx=20, pady=(0, 16))

        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.pack(fill="x", padx=20, pady=(0, 20))
        buttons.grid_columnconfigure(0, weight=1)
        buttons.grid_columnconfigure(1, weight=1)

        cancelButton = ctk.CTkButton(
            buttons,
            text="Отмена",
            height=40,
            corner_radius=9,
            fg_color=COLORS["button"],
            hover_color=COLORS["buttonHover"],
            command=self.hideResetConfirmation,
        )
        cancelButton.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        confirmButton = ctk.CTkButton(
            buttons,
            text="Сбросить",
            height=40,
            corner_radius=9,
            fg_color="#4A1A1A",
            hover_color="#682323",
            text_color="#FFDADA",
            command=self.confirmResetZapret,
        )
        confirmButton.grid(row=0, column=1, padx=(5, 0), sticky="ew")

    def hideResetConfirmation(self):
        if hasattr(self, "resetOverlay") and self.resetOverlay.winfo_exists():
            self.resetOverlay.destroy()
            del self.resetOverlay

    def confirmResetZapret(self):
        self.hideResetConfirmation()
        self.setBusy(True, "Сбрасываю настройки zapret…")
        self.startWorker(self.resetZapretTask, self.onResetZapretFinished)

    def resetZapretTask(self, progress):
        installedVersion = self.getInstalledZapretVersion()
        if not installedVersion:
            raise RuntimeError("Не удалось определить установленную версию zapret.")

        wasRunning = self.isServiceRunning()
        if wasRunning:
            progress("Останавливаю службу zapret…")
            self.removeServiceSilently()

        listsDir = ZAPRET_DIR / "lists"
        listsDir.mkdir(parents=True, exist_ok=True)

        progress("Загружаю стандартные списки zapret…")
        for fileName in STOCK_LIST_FILES:
            content = self.fetchStockListFile(installedVersion, fileName)
            (listsDir / fileName).write_bytes(content)

        for fileName in USER_LIST_FILES:
            (listsDir / fileName).unlink(missing_ok=True)
        (listsDir / "ipset-all.txt.backup").unlink(missing_ok=True)
        (ZAPRET_DIR / "utils" / "game_filter.enabled").unlink(missing_ok=True)

        self.settings["gameFilter"] = "disabled"
        self.settings["ipset"] = "none"
        self.settings["strategy"] = "general.bat"
        self.saveSettings()

        self.ensureUserLists()
        self.applySelectedSettingsBeforeStart()

        if wasRunning:
            progress("Запускаю стандартную стратегию general.bat…")
            self.installSelectedServiceDirect()

        return True

    def fetchStockListFile(self, version, fileName):
        tag = urllib.parse.quote(version, safe="")
        remotePath = (
            ".service/ipset-service.txt"
            if fileName == "ipset-all.txt"
            else f"lists/{urllib.parse.quote(fileName)}"
        )
        url = (
            f"https://raw.githubusercontent.com/{ZAPRET_OWNER}/{ZAPRET_REPO}/"
            f"{tag}/{remotePath}?t={int(time.time())}"
        )
        with self.httpOpen(url, timeout=30) as response:
            content = response.read()

        if not content:
            raise RuntimeError(f"GitHub вернул пустой файл: {fileName}")
        return content

    def onResetZapretFinished(self, _result):
        self.setBusy(False, "")
        self.refreshState()
        self.refreshInfoPage()
        self.refreshSettingsPage()
        self.setTopStatus("Настройки zapret сброшены до стандартных.")

    # -----------------------------
    # Updates
    # -----------------------------
    def updateZapretClicked(self):
        if self.isBusy:
            return
        if not (ZAPRET_DIR / "service.bat").exists():
            self.showError("Папка zapret ещё не готова.")
            return

        self.setBusy(True, "Проверяю последнюю версию…")
        self.startWorker(self.fetchLatestRelease, self.onManualUpdateCheckFinished, errorIsUpdateCheck=True)

    def onManualUpdateCheckFinished(self, release):
        self.latestVersion = release["version"]
        self.latestDownloadUrl = release["downloadUrl"]
        self.latestSha256 = release.get("sha256", "")
        self.updateCheckError = ""

        installedVersion = self.getInstalledZapretVersion()
        if installedVersion and not self.isVersionNewer(release["version"], installedVersion):
            self.setBusy(False, "")
            self.refreshState()
            self.refreshInfoPage()
            self.refreshSettingsPage()
            self.setTopStatus("Установлена последняя доступная версия.")
            return

        self.setBusy(True, f"Обновляю zapret до {release['version']}…")
        self.startWorker(
            lambda progress: self.updateTask(release, progress),
            self.onZapretUpdateFinished,
        )

    def onUpdateCheckThenUpdate(self, release):
        self.latestVersion = release["version"]
        self.latestDownloadUrl = release["downloadUrl"]
        self.latestSha256 = release.get("sha256", "")
        self.updateCheckError = ""
        self.refreshSettingsPage()
        self.setBusy(True, f"Обновляю zapret до {self.latestVersion}…")
        self.startWorker(
            lambda progress: self.updateTask(release, progress),
            self.onZapretUpdateFinished,
        )

    def updateTask(self, release, progress):
        progress(f"Скачиваю zapret {release['version']}…")
        self.downloadAndInstall(release, progress)
        return release

    def onZapretUpdateFinished(self, release):
        self.setBusy(False, "")
        self.latestVersion = release["version"]
        self.updateCheckError = ""
        self.loadStrategies()
        self.ensureValidStrategy()
        self.refreshState()
        self.refreshInfoPage()
        self.refreshSettingsPage()
        self.setTopStatus(f"zapret обновлён до {release['version']}")

    # -----------------------------
     # Проверка стратегий
    # -----------------------------
    def runTestsClicked(self):
        if self.isBusy:
            return
        if not (ZAPRET_DIR / "service.bat").exists():
            self.showError("Папка zapret ещё не готова.")
            return

        self.showPage("tests")
        self.startTestsProcess()

    def startTestsProcess(self):
        self.cancelTests = False
        self.restoreServiceAfterTests = False
        self.testOutputBox.delete("1.0", "end")
        self.testStatusLabel.configure(text="Подготавливаю тестирование…")
        self.stopTestsButton.configure(state="normal")

        self.testThread = threading.Thread(target=self.runTestsTask, daemon=True)
        self.testThread.start()

    def runTestsTask(self):
        testFile = ZAPRET_DIR / "utils" / "test zapret.ps1"
        if not testFile.exists():
            self.eventQueue.put(("test_status", "Файл тестирования не найден."))
            self.eventQueue.put(("test_finished", 1))
            return

        command = (
            "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
            "$OutputEncoding=[System.Text.Encoding]::UTF8; "
            f"& '{str(testFile).replace(chr(39), chr(39) * 2)}'; exit $LASTEXITCODE"
        )

        startupInfo = subprocess.STARTUPINFO()
        startupInfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupInfo.wShowWindow = subprocess.SW_HIDE

        try:
            serviceWasRunning = self.isServiceRunning()
            serviceWasInstalled = self.isServiceInstalled()

            if serviceWasInstalled:
                self.eventQueue.put(
                    ("test_status", "Временно отключаю службу zapret для тестирования…")
                )
                self.removeServiceSilently()
                self.restoreServiceAfterTests = serviceWasRunning

            self.eventQueue.put(("test_status", "Проверка стратегий: Standard → All…"))

            process = subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    command,
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(ZAPRET_DIR),
                startupinfo=startupInfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            self.testProcess = process
            process.stdin.write("1\n1\n")
            process.stdin.flush()
        except OSError as error:
            self.eventQueue.put(("test_status", f"Ошибка запуска тестирования: {error}"))
            self.eventQueue.put(("test_finished", 1))
            self.testProcess = None
            return

        try:
            while True:
                if self.cancelTests:
                    try:
                        process.kill()
                    except OSError:
                        pass
                    break

                line = process.stdout.readline()
                if line:
                    self.eventQueue.put(("test_line", line))
                    combined = line.lower()
                    if "all tests finished" in combined or "press any key" in combined:
                        self.sendTestEnter()

                if process.poll() is not None:
                    break

            exitCode = process.wait()

            if self.restoreServiceAfterTests and not self.cancelTests:
                try:
                    self.eventQueue.put(("test_status", "Восстанавливаю службу zapret…"))
                    self.installSelectedServiceDirect()
                except Exception as error:
                    self.eventQueue.put(
                        (
                            "test_status",
                            f"Тесты завершены, но службу не удалось восстановить: {error}",
                        )
                    )

            self.eventQueue.put(("test_finished", exitCode))
        finally:
            self.testProcess = None
            self.restoreServiceAfterTests = False

    def sendTestEnter(self):
        if not self.testProcess or self.testProcess.poll() is not None:
            return
        try:
            self.testProcess.stdin.write("\n")
            self.testProcess.stdin.flush()
        except OSError:
            pass

    def stopTests(self):
        self.cancelTests = True
        if self.testProcess and self.testProcess.poll() is None:
            try:
                self.testProcess.kill()
            except OSError:
                pass
        self.stopTestsButton.configure(state="disabled")
        self.testStatusLabel.configure(text="Тестирование остановлено.")

    # -----------------------------
    # Worker queue
    # -----------------------------
    def startWorker(self, function, onFinished, errorIsUpdateCheck=False):
        def worker():
            try:
                result = function(lambda message: self.eventQueue.put(("progress", message)))
                self.eventQueue.put(("worker_finished", (onFinished, result)))
            except Exception as error:
                self.eventQueue.put(("worker_error", (str(error), errorIsUpdateCheck)))

        self.currentThread = threading.Thread(target=worker, daemon=True)
        self.currentThread.start()

    def processQueue(self):
        try:
            while True:
                eventType, payload = self.eventQueue.get_nowait()
                if eventType == "progress":
                    self.onBackgroundProgress(payload)
                elif eventType == "worker_finished":
                    callback, result = payload
                    callback(result)
                elif eventType == "worker_error":
                    errorText, errorIsUpdateCheck = payload
                    self.updateCheckError = errorText if errorIsUpdateCheck else ""
                    self.setBusy(False, "")
                    self.showError(errorText)
                    self.refreshState()
                    self.refreshInfoPage()
                    self.refreshSettingsPage()
                elif eventType == "test_line":
                    self.testOutputBox.insert("end", payload)
                    self.testOutputBox.see("end")
                elif eventType == "test_status":
                    self.testStatusLabel.configure(text=payload)
                elif eventType == "test_finished":
                    self.onTestFinished(payload)
        except queue.Empty:
            pass

        self.after(QUEUE_INTERVAL_MS, self.processQueue)

    def showDownloadProgress(self):
        if hasattr(self, "downloadStatusFrame") and not self.downloadStatusFrame.winfo_manager():
            self.downloadStatusFrame.pack(fill="x", padx=20, pady=(0, 14))

    def hideDownloadProgress(self, reset=True):
        if not hasattr(self, "downloadStatusFrame"):
            return
        self.downloadStatusFrame.pack_forget()
        self.settingsStatusLabel.configure(text="", text_color=COLORS["muted"])
        if reset:
            self.setDownloadProgress(0)

    def setDownloadProgress(self, percent):
        self.downloadPercent = max(0, min(int(percent), 100))
        if hasattr(self, "downloadProgressBar"):
            self.downloadProgressBar.set(self.downloadPercent / 100)
        if hasattr(self, "downloadPercentLabel"):
            self.downloadPercentLabel.configure(text=f"{self.downloadPercent}%")

    def onBackgroundProgress(self, text):
        match = re.search(r"Скачивание:\s*(\d+)%", text)
        isDownloadStep = (
            "Скачиваю zapret" in text
            or "Скачивание:" in text
            or "Распаковываю архив" in text
        )

        if isDownloadStep:
            self.showDownloadProgress()
            self.settingsStatusLabel.configure(text=text, text_color=COLORS["muted"])

        if match:
            self.setDownloadProgress(int(match.group(1)))

        self.setTopStatus(text)

    def onTestFinished(self, exitCode):
        self.stopTestsButton.configure(state="disabled")
        if self.cancelTests:
            return
        if exitCode == 0:
            self.testStatusLabel.configure(text="Тестирование завершено.")
        else:
            self.testStatusLabel.configure(text=f"Тестирование завершилось с кодом {exitCode}.")

    # -----------------------------
    # Shared helpers
    # -----------------------------
    def setBusy(self, busy, status):
        self.isBusy = busy
        self.mainButton.setEnabled(not busy)
        if busy:
            # The progress area is shown only for download/extract steps.
            self.setDownloadProgress(0)
        else:
            self.hideDownloadProgress(reset=True)
        self.refreshSettingsPage()
        if status:
            self.setTopStatus(status)

    def setTopStatus(self, text):
        if hasattr(self, "topStatusLabel"):
            self.topStatusLabel.configure(text=text)

    def showError(self, message):
        self.setTopStatus(message)
        if hasattr(self, "settingsStatusLabel"):
            self.settingsStatusLabel.configure(text=message, text_color=COLORS["red"])
        if hasattr(self, "strategyStatusLabel"):
            self.strategyStatusLabel.configure(text=message, text_color=COLORS["red"])

    def getInstalledZapretVersion(self):
        serviceFile = ZAPRET_DIR / "service.bat"
        if not serviceFile.exists():
            return ""
        try:
            text = serviceFile.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""

        match = re.search(r'set\s+"LOCAL_VERSION=([^\"]+)"', text, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    @staticmethod
    def isValidVersion(value):
        return bool(re.fullmatch(r"\d+(?:\.\d+)*[A-Za-z]?", value.strip().lstrip("vV")))

    @staticmethod
    def parseVersion(value):
        clean = value.strip().lstrip("vV")
        match = re.match(r"^(\d+(?:\.\d+)*)([A-Za-z]?)$", clean)
        if not match:
            return (0,), 0

        numbers = tuple(int(number) for number in match.group(1).split("."))
        suffix = match.group(2).lower()
        suffixValue = ord(suffix) - 96 if suffix else 0
        return numbers, suffixValue

    def isVersionNewer(self, newVersion, oldVersion):
        newNumbers, newSuffix = self.parseVersion(newVersion)
        oldNumbers, oldSuffix = self.parseVersion(oldVersion)
        maxLength = max(len(newNumbers), len(oldNumbers))
        newNumbers += (0,) * (maxLength - len(newNumbers))
        oldNumbers += (0,) * (maxLength - len(oldNumbers))
        return (newNumbers, newSuffix) > (oldNumbers, oldSuffix)

    def applySelectedSettingsBeforeStart(self):
        self.applyGameFilterFile(self.settings.get("gameFilter", "disabled"))
        self.applyIpSetMode(self.settings.get("ipset", "none"), downloadLoadedList=True)

    def ensureUserLists(self):
        listsDir = ZAPRET_DIR / "lists"
        listsDir.mkdir(parents=True, exist_ok=True)

        defaults = {
            "ipset-exclude-user.txt": "203.0.113.113/32\n",
            "list-general-user.txt": "# Never leave this file empty\ndomain.example.abc\n",
            "list-exclude-user.txt": "domain.example.abc\n",
            "ipset-all-user.txt": "# Дополнительные IP/подсети для EzZapret\n",
        }
        for fileName, content in defaults.items():
            filePath = listsDir / fileName
            if not filePath.exists():
                filePath.write_text(content, encoding="utf-8")

    def installSelectedServiceSilently(self):
        self.ensureUserLists()
        self.applySelectedSettingsBeforeStart()
        self.installSelectedServiceDirect()

    def removeServiceSilently(self):
        self.runCommand(["net", "stop", SERVICE_NAME], check=False, timeout=20)
        self.runCommand(["sc", "delete", SERVICE_NAME], check=False, timeout=20)
        self.runCommand(["taskkill", "/IM", "winws.exe", "/F"], check=False, timeout=10)

        self.runCommand(["net", "stop", "WinDivert"], check=False, timeout=15)
        self.runCommand(["sc", "delete", "WinDivert"], check=False, timeout=15)
        self.runCommand(["net", "stop", "WinDivert14"], check=False, timeout=15)
        self.runCommand(["sc", "delete", "WinDivert14"], check=False, timeout=15)

        for _ in range(20):
            if not self.isServiceInstalled():
                return
            time.sleep(0.3)

        if self.isServiceRunning():
            raise RuntimeError("Не удалось полностью удалить службу zapret.")

    def isServiceInstalled(self):
        try:
            result = subprocess.run(
                ["sc", "query", SERVICE_NAME],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5,
            )
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def openUrl(self, url):
        try:
            os.startfile(url)
        except OSError:
            pass

    def isWindows(self):
        return sys.platform.startswith("win")

    def isAdmin(self):
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except AttributeError:
            return False

    def restartAsAdmin(self):
        executable = sys.executable
        if getattr(sys, "frozen", False):
            params = ""
        else:
            params = subprocess.list2cmdline(sys.argv)
        ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, str(BASE_DIR), 1)
        self.destroy()

    def closeApp(self):
        self.cancelTests = True
        if self.testProcess and self.testProcess.poll() is None:
            try:
                self.testProcess.kill()
            except OSError:
                pass

        try:
            if self.isServiceRunning():
                self.removeServiceSilently()
        except RuntimeError:
            # Do not keep the GUI open forever when Windows refuses service removal.
            pass

        self.saveSettings()
        self.destroy()


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = EzZapretApp()
    app.mainloop()
