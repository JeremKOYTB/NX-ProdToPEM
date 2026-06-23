import os
import sys
import struct
import math
import subprocess
import importlib.util
import webbrowser
import signal
import json
import re
import urllib.request
import urllib.error
import ast

def ensure_dependencies():
    if importlib.util.find_spec("cryptography") is None:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"], 
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print("[-] Error: Auto-installation failed. Please run: pip install cryptography")
            sys.exit(1)
            
    if importlib.util.find_spec("darkdetect") is None:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "darkdetect"], 
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print("[-] Error: Auto-installation failed. Please run: pip install darkdetect")
            sys.exit(1)

ensure_dependencies()

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFrame, QMessageBox, QFileDialog, QSizePolicy, QGridLayout,
                             QGraphicsOpacityEffect, QDialog, QComboBox, QCheckBox)
from PyQt6.QtCore import Qt, QTimer, QByteArray, QThread, pyqtSignal, QPropertyAnimation, QSize
from PyQt6.QtGui import QIcon, QPixmap, QColor, QDragEnterEvent, QDropEvent
import darkdetect

BASE_FONT = "\"Segoe UI Variable\", \"Segoe UI\", \"Roboto\", sans-serif"

THEMES = {
    "dark": {
        "bg": "#3C3C44", "bg_input": "#32323A", "text": "#E8E8E8", "text_title": "#FFFFFF", 
        "text_dim": "#B0B0B8", "card": "#4A4A54", "border": "#555560", "border_hover": "#626270",
        "accent": "#C4A1FF", "accent_hover": "#8C54FF", "btn_text": "#2B2B30", "btn_hover_text": "#FFFFFF",
        "warn": "#EF5350", "warn_hover": "#2F1C1C", "warn_border": "#FF6B6B"
    },
    "light": {
        "bg": "#F0F0F5", "bg_input": "#F9F9FB", "text": "#1D1D1F", "text_title": "#000000", 
        "text_dim": "#8E8E93", "card": "#FFFFFF", "border": "#D1D1D6", "border_hover": "#E5E5EA",
        "accent": "#8C54FF", "accent_hover": "#743DE5", "btn_text": "#FFFFFF", "btn_hover_text": "#FFFFFF",
        "warn": "#EF5350", "warn_hover": "#FFEBEE", "warn_border": "#D32F2F"
    }
}

def get_stylesheet(is_dark):
    c = THEMES["dark"] if is_dark else THEMES["light"]
    return f"""
    QMainWindow, QDialog, QMessageBox {{ background-color: {c['bg']}; color: {c['text']}; }}
    QWidget {{ font-family: {BASE_FONT}; font-size: 10pt; }}
    QLabel {{ color: {c['text']}; }}
    QMessageBox QLabel {{ color: {c['text']}; background-color: transparent; }}
    QFrame#Card {{ background-color: {c['card']}; border-radius: 8px; border: 1px solid {c['border']}; }}
    QLabel#CardTitle {{ color: {c['text_title']}; font-size: 13pt; font-weight: 700; padding-bottom: 0px; }}
    QLabel#CardVersion {{ color: {c['text_dim']}; font-size: 9pt; font-weight: 500; padding-bottom: 2px; }}
    QLineEdit {{ background-color: {c['bg_input']}; border: 1px solid {c['border']}; border-radius: 6px; padding: 6px 10px; color: {c['text']}; font-size: 10pt; min-height: 20px; }}
    QLineEdit:focus {{ border: 1px solid {c['accent']}; background-color: {c['bg']}; }}
    QComboBox {{ background-color: {c['bg_input']}; border: 1px solid {c['border']}; border-radius: 6px; padding: 5px; color: {c['text']}; }}
    QCheckBox {{ color: {c['text']}; }}
    QPushButton {{ background-color: {c['border']}; color: {c['text']}; border-radius: 6px; padding: 6px 14px; font-weight: 600; border: 1px solid {c['border_hover']}; min-height: 20px; }}
    QPushButton:hover {{ background-color: {c['border_hover']}; }}
    QPushButton:pressed {{ background-color: {c['accent']}; color: {c['btn_text']}; border: 1px solid {c['accent']}; }}
    #btnHeader {{ font-size: 9pt; font-weight: normal; padding: 4px 12px; border-radius: 4px; background-color: transparent; border: 1px solid {c['text_dim']}; color: {c['text']}; }}
    #btnHeader:hover {{ color: {c['text_title']}; border-color: {c['accent']}; background-color: {c['border_hover']}; }}
    #btnHelp {{ background-color: transparent; border: 1px solid {c['text_dim']}; color: {c['text_dim']}; border-radius: 11px; min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px; font-weight: bold; font-size: 9pt; }}
    #btnHelp:hover {{ color: {c['accent']}; border-color: {c['accent']}; background-color: {c['border']}; }}
    #btnHelpHidden {{ background-color: transparent; border: none; min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px; }}
    #btnExecute {{ background-color: {c['accent']}; color: {c['btn_text']}; font-size: 11pt; font-weight: bold; padding: 10px 24px; border-radius: 6px; border: none; min-width: 200px; }}
    #btnExecute:hover {{ background-color: {c['accent_hover']}; color: {c['btn_hover_text']}; }}
    #btnExecute:disabled {{ background-color: {c['border']}; color: {c['text_dim']}; }}
    #btnAdvancedLogs, #btnRestart, #btnResetConfig, #btnReportIssue {{ font-size: 9pt; font-weight: normal; padding: 4px 12px; border-radius: 4px; min-width: 110px; max-width: 110px; }}
    #btnAdvancedLogs {{ background-color: transparent; border: 1px solid {c['border']}; color: {c['text_dim']}; }}
    #btnAdvancedLogs:checked {{ background-color: {c['accent']}; border-color: {c['accent']}; color: {c['btn_text']}; font-weight: bold; }}
    #btnAdvancedLogs:checked:hover {{ background-color: {c['accent_hover']}; border-color: {c['accent_hover']}; color: {c['btn_hover_text']}; }}
    #btnAdvancedLogs:hover:!checked {{ color: {c['text_title']}; border-color: {c['text_dim']}; }}
    #btnRestart {{ background-color: transparent; border: 1px solid {c['warn']}; color: {c['warn']}; }}
    #btnRestart:hover {{ background-color: {c['warn_hover']}; color: {c['warn_border']}; border-color: {c['warn_border']}; }}
    #btnResetConfig, #btnReportIssue {{ background-color: transparent; border: 1px solid {c['text_dim']}; color: {c['text_dim']}; }}
    #btnResetConfig:hover {{ color: {c['warn']}; border-color: {c['warn']}; background-color: {c['warn_hover']}; }}
    #btnReportIssue:hover {{ color: {c['accent']}; border-color: {c['accent']}; background-color: {c['border_hover']}; }}
    #btnSocial {{ background-color: transparent; border: none; padding: 2px; border-radius: 4px; }}
    #btnSocial:hover {{ background-color: {c['border_hover']}; }}
    """

SVG_LOGO_DATA = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
    <rect width="128" height="128" rx="28" fill="#4A4A54"/>
    <path d="M64 22 C48 22, 36 34, 36 50 L36 60 L92 60 L92 50 C92 34, 80 22, 64 22 Z" fill="none" stroke="#C4A1FF" stroke-width="8" stroke-linejoin="round" stroke-linecap="round"/>
    <rect x="24" y="56" width="80" height="52" rx="12" fill="#32323A" stroke="#555560" stroke-width="4"/>
    <circle cx="64" cy="78" r="7" fill="#C4A1FF"/>
    <path d="M64 85 L64 96" stroke="#C4A1FF" stroke-width="5" stroke-linecap="round"/>
</svg>"""

SVG_X_DARK = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><path fill="#E8E8E8" d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>"""
SVG_X_LIGHT = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><path fill="#1D1D1F" d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>"""

SVG_GITHUB_DARK = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><path fill="#E8E8E8" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.008.069-.008 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/></svg>"""
SVG_GITHUB_LIGHT = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><path fill="#1D1D1F" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.008.069-.008 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/></svg>"""

SVG_DISCORD_DARK = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><path fill="#E8E8E8" d="M20.317 4.37a19.791 19.791 0 00-4.885-1.515.074.074 0 00-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 00-5.487 0 12.64 12.64 0 00-.617-1.25.077.077 0 00-.079-.037A19.736 19.736 0 003.677 4.37a.07.07 0 00-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 00.031.057 19.9 19.9 0 005.993 3.03.078.078 0 00.084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.094 13.094 0 01-1.873-.894.077.077 0 01-.008-.128c.126-.093.252-.19.372-.287a.075.075 0 01.077-.011c3.92 1.793 8.18 1.793 12.061 0a.073.073 0 01.078.009c.12.099.246.195.373.289a.075.075 0 01-.006.127 12.298 12.298 0 01-1.873.894.077.077 0 01-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 00.084.028 19.839 19.839 0 006.002-3.03a.077.077 0 00.032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 00-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.156-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.156 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.156-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.156 2.418z"/></svg>"""
SVG_DISCORD_LIGHT = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><path fill="#1D1D1F" d="M20.317 4.37a19.791 19.791 0 00-4.885-1.515.074.074 0 00-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 00-5.487 0 12.64 12.64 0 00-.617-1.25.077.077 0 00-.079-.037A19.736 19.736 0 003.677 4.37a.07.07 0 00-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 00.031.057 19.9 19.9 0 005.993 3.03.078.078 0 00.084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.094 13.094 0 01-1.873-.894.077.077 0 01-.008-.128c.126-.093.252-.19.372-.287a.075.075 0 01.077-.011c3.92 1.793 8.18 1.793 12.061 0a.073.073 0 01.078.009c.12.099.246.195.373.289a.075.075 0 01-.006.127 12.298 12.298 0 01-1.873.894.077.077 0 01-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 00.084.028 19.839 19.839 0 006.002-3.03a.077.077 0 00.032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 00-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.156-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.156 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.156-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.156 2.418z"/></svg>"""

class DropLineEdit(QLineEdit):
    def __init__(self, expected_filename=None, is_directory=False, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.expected_filename = expected_filename
        self.is_directory = is_directory

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        urls = e.mimeData().urls()
        if urls:
            filepath = urls[0].toLocalFile()
            if self.is_directory:
                if os.path.isdir(filepath):
                    self.setText(filepath)
                else:
                    QMessageBox.critical(self, "Invalid Drop", "A directory is required for this field.")
            else:
                if os.path.isfile(filepath):
                    actual_name = os.path.basename(filepath)
                    if self.expected_filename and actual_name.lower() != self.expected_filename.lower():
                        msg = f"The dropped file is named '{actual_name}' instead of '{self.expected_filename}'.\n\nDo you want to use it anyway?"
                        box = QMessageBox(QMessageBox.Icon.Question, "Unexpected Filename", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self.window())
                        if box.exec() == QMessageBox.StandardButton.Yes:
                            self.setText(filepath)
                    else:
                        self.setText(filepath)
                else:
                    QMessageBox.critical(self, "Invalid Drop", "A file is required for this field.")

class ThreadLogger:
    def __init__(self, signal):
        self.signal = signal
    def log(self, msg):
        self.signal.emit(msg)

class ConversionThread(QThread):
    log_signal = pyqtSignal(str)
    success_signal = pyqtSignal(bytes, str, str)
    error_signal = pyqtSignal(str)

    def __init__(self, p_path, k_path, out_dir):
        super().__init__()
        self.p_path = p_path
        self.k_path = k_path
        self.out_dir = out_dir

    def run(self):
        thread_log = ThreadLogger(self.log_signal)
        try:
            thread_log.log(f"[LOG] Cryptographic engine execution started in thread {int(self.currentThreadId())}.")
            thread_log.log(f"[LOG] Performing strict memory allocation constraints for {self.p_path}")
            
            with open(self.p_path, 'rb') as f:
                raw_prodinfo_data = f.read()
            
            thread_log.log(f"[LOG] Memory buffer allocated: {len(raw_prodinfo_data)} bytes read from PRODINFO.")
            
            is_cal0_clear = (raw_prodinfo_data[:4] == b"CAL0")
            required_keys = {'ssl_rsa_kek'}
            if not is_cal0_clear:
                thread_log.log("[LOG] Magic CAL0 not detected. Scheduling AES-XTS full sector decryption cycle. Adding 'bis_key_00'.")
                required_keys.add('bis_key_00')

            keys = get_keys(self.k_path, required_keys, thread_log)
            ssl_rsa_kek = keys.get('ssl_rsa_kek')
            if not ssl_rsa_kek: 
                raise ValueError("The encryption key 'ssl_rsa_kek' is missing from your prod.keys file.")

            if not is_cal0_clear:
                bis_key_00 = keys.get('bis_key_00')
                if not bis_key_00: 
                    raise ValueError("The encryption key 'bis_key_00' is missing from your prod.keys file.")
                decrypted_data = decrypt_prodinfo(raw_prodinfo_data, bis_key_00, thread_log)
                if not decrypted_data:
                    raise ValueError("Failed to decrypt PRODINFO. Invalid file or bad 'bis_key_00'.")
            else:
                thread_log.log("[LOG] Plaintext CAL0 payload confirmed. Bypassing AES-XTS routine.")
                decrypted_data = raw_prodinfo_data

            unified_pem, cert_info = extract_and_build_pem(decrypted_data, ssl_rsa_kek, thread_log)
            
            thread_log.log("[LOG] Freeing cryptographic buffers to prevent memory leaks and ensure app stability.")
            del raw_prodinfo_data
            del decrypted_data
            del keys

            self.success_signal.emit(unified_pem, self.out_dir, cert_info)
        except Exception as e:
            self.error_signal.emit(str(e))

class UpdateCheckerThread(QThread):
    finished = pyqtSignal(dict, str)

    def run(self):
        url = "https://api.github.com/repos/JeremKOYTB/NX-ProdToPEM/releases/latest"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'NX-ProdToPEM-Updater'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
            self.finished.emit(data, "")
        except Exception as e:
            self.finished.emit({}, str(e))

class AboutDialog(QDialog):
    def __init__(self, parent, is_dark, version):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.MSWindowsFixedSizeDialogHint)
        self.is_dark = is_dark
        self.version = version
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        top_layout = QHBoxLayout()
        
        logo_lbl = QLabel(self)
        px_logo = QPixmap()
        px_logo.loadFromData(QByteArray(SVG_LOGO_DATA))
        logo_lbl.setPixmap(px_logo.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        top_layout.addWidget(logo_lbl, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        top_layout.addStretch(1)
        
        social_layout = QHBoxLayout()
        social_layout.setSpacing(8)

        btn_x = QPushButton(self)
        btn_x.setObjectName("btnSocial")
        px_x = QPixmap()
        px_x.loadFromData(QByteArray(SVG_X_DARK if self.is_dark else SVG_X_LIGHT))
        btn_x.setIcon(QIcon(px_x))
        btn_x.setIconSize(QSize(24, 24))
        btn_x.clicked.connect(lambda: webbrowser.open("https://x.com/JeremKOYTB"))

        btn_git = QPushButton(self)
        btn_git.setObjectName("btnSocial")
        px_git = QPixmap()
        px_git.loadFromData(QByteArray(SVG_GITHUB_DARK if self.is_dark else SVG_GITHUB_LIGHT))
        btn_git.setIcon(QIcon(px_git))
        btn_git.setIconSize(QSize(24, 24))
        btn_git.clicked.connect(lambda: webbrowser.open("https://github.com/JeremKOYTB"))

        btn_disc = QPushButton(self)
        btn_disc.setObjectName("btnSocial")
        px_disc = QPixmap()
        px_disc.loadFromData(QByteArray(SVG_DISCORD_DARK if self.is_dark else SVG_DISCORD_LIGHT))
        btn_disc.setIcon(QIcon(px_disc))
        btn_disc.setIconSize(QSize(24, 24))
        btn_disc.clicked.connect(self.copy_discord)

        social_layout.addWidget(btn_x)
        social_layout.addWidget(btn_git)
        social_layout.addWidget(btn_disc)
        
        top_layout.addLayout(social_layout)
        layout.addLayout(top_layout)

        info_lbl = QLabel(self)
        info_lbl.setWordWrap(True)
        info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_lbl.setText(
            f"<b>NX-ProdToPEM GUI</b><br>"
            f"Version: {self.version}<br><br>"
            f"Created by JérémKO.<br><br>"
            f"A utility to decrypt PRODINFO.bin and generate a certificat.pem for SSL/TLS authentication.<br><br>"
            f"Thanks to the authors of NxCertDump for the initial research on the CAL0/PRODINFO structure."
        )
        layout.addWidget(info_lbl)

        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.setFixedSize(380, 260)

    def copy_discord(self):
        QApplication.clipboard().setText("jeremko")
        QMessageBox.information(self, "Discord", "Discord username 'jeremko' copied to clipboard!")

class UpdateManagerDialog(QDialog):
    def __init__(self, parent, current_version):
        super().__init__(parent)
        self.parent_win = parent
        self.current_version = current_version
        self.setWindowTitle("Update Manager")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.MSWindowsFixedSizeDialogHint)
        self.setFixedSize(450, 240)
        self.releases_data = []
        self.cached_releases = []
        self.init_ui()
        self.fetch_all_releases()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        self.beta_checkbox = QCheckBox("Include main branch [not recommended]", self)
        self.beta_checkbox.stateChanged.connect(self.toggle_beta_mode)
        layout.addWidget(self.beta_checkbox)

        self.info_lbl = QLabel("Select an available release version:", self)
        layout.addWidget(self.info_lbl)

        self.version_combo = QComboBox(self)
        layout.addWidget(self.version_combo)

        self.warn_lbl = QLabel("", self)
        self.warn_lbl.setWordWrap(True)
        self.warn_lbl.setStyleSheet("color: #EF5350; font-size: 9pt;")
        layout.addWidget(self.warn_lbl)

        self.version_combo.currentIndexChanged.connect(self.check_version_dependencies)

        btn_layout = QHBoxLayout()
        self.btn_install = QPushButton("Install Selected Version", self)
        self.btn_install.clicked.connect(self.install_version)
        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_install)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def toggle_beta_mode(self, state):
        self.version_combo.clear()
        self.warn_lbl.setText("")
        
        if self.parent_win.btn_advanced.isChecked():
            self.parent_win.logger.log(f"[LOG] Beta mode toggled: {state == Qt.CheckState.Checked.value}")
            
        for text, data in self.cached_releases:
            self.version_combo.addItem(text, data)
            
        if state == Qt.CheckState.Checked.value:
            self.btn_install.setEnabled(False)
            QTimer.singleShot(100, self.fetch_beta_source)
        else:
            self.btn_install.setEnabled(self.version_combo.count() > 0)

    def fetch_all_releases(self):
        url = "https://api.github.com/repos/JeremKOYTB/NX-ProdToPEM/releases"
        if self.parent_win.btn_advanced.isChecked():
            self.parent_win.logger.log(f"[LOG] Fetching all releases from GitHub API...")
            
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'NX-ProdToPEM-Updater'})
            with urllib.request.urlopen(req, timeout=5) as response:
                self.releases_data = json.loads(response.read().decode('utf-8'))
            
            self.cached_releases = []
            for rel in self.releases_data:
                tag = rel.get("tag_name", "")
                if tag:
                    self.cached_releases.append((tag, rel))
                    self.version_combo.addItem(tag, rel)
            self.btn_install.setEnabled(self.version_combo.count() > 0)
            if self.parent_win.btn_advanced.isChecked():
                self.parent_win.logger.log(f"[LOG] Successfully parsed {len(self.cached_releases)} release tags.")
        except Exception as e:
            self.warn_lbl.setText(f"Failed to load releases: {e}")
            self.btn_install.setEnabled(False)

    def fetch_beta_source(self):
        url = "https://raw.githubusercontent.com/JeremKOYTB/NX-ProdToPEM/refs/heads/main/NX-ProdToPEM-GUI.py"
        if self.parent_win.btn_advanced.isChecked():
            self.parent_win.logger.log(f"[LOG] Fetching main branch source...")
            
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'NX-ProdToPEM-Updater'})
            with urllib.request.urlopen(req, timeout=5) as response:
                code = response.read().decode('utf-8')
            
            match = re.search(r'ExplicitAppUserModelID\("JeremKOYTB\.NXProdToPEM\.Gui\.([^"\']+)"\)', code)
            beta_version = match.group(1) if match else "Unknown"
            
            if self.parent_win.btn_advanced.isChecked():
                self.parent_win.logger.log(f"[LOG] Main branch version identifier parsed: v{beta_version}")
                
            self.version_combo.insertItem(0, f"main branch (v{beta_version})", url)
            self.version_combo.setCurrentIndex(0)
            self.warn_lbl.setText("WARNING: These versions are actively under development. Reliability might be lower. Only install if explicitly required.")
            self.btn_install.setEnabled(True)
        except Exception as e:
            self.warn_lbl.setText(f"Failed to fetch main branch source: {e}")
            self.btn_install.setEnabled(False)

    def check_version_dependencies(self, index):
        if index < 0:
            return
            
        current_text = self.version_combo.currentText()
        if "main branch" in current_text:
            self.warn_lbl.setText("WARNING: These versions are actively under development. Reliability might be lower. Only install if explicitly required.")
            return

        selected_text = current_text.lstrip("v")
        if selected_text == "1.0.0":
            self.warn_lbl.setText("CRITICAL: Version 1.0.0 does not include an update manager. If you downgrade, automatic updates will no longer function, requiring a manual re-installation from GitHub later.")
        else:
            self.warn_lbl.setText("")

    def install_version(self):
        current_data = self.version_combo.currentData()
        if isinstance(current_data, str):
            download_url = current_data
        else:
            rel = current_data
            if not rel:
                return
            assets = rel.get("assets", [])
            download_url = next((a["browser_download_url"] for a in assets if a["name"] == "NX-ProdToPEM-GUI.py"), None)
            if not download_url:
                tag = rel.get("tag_name", "v1.2.1")
                download_url = f"https://raw.githubusercontent.com/JeremKOYTB/NX-ProdToPEM/{tag}/NX-ProdToPEM-GUI.py"

        if download_url:
            if self.parent_win.btn_advanced.isChecked():
                self.parent_win.logger.log(f"[LOG] Triggering download from: {download_url}")
            self.parent_win.download_and_restart(download_url)
            self.accept()

def get_keys(keys_path, required_keys, logger=None):
    if logger:
        logger.log(f"[LOG] Loading keys from: {keys_path}")
        logger.log("[LOG] Parsing text stream into hexadecimal map. Encoding context: utf-8.")
    keys = {}
    try:
        with open(keys_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_idx, line in enumerate(f, 1):
                line = line.strip()
                if '=' in line:
                    k_str, v_str = [x.strip() for x in line.split('=', 1)]
                    if k_str in required_keys:
                        keys[k_str] = bytes.fromhex(v_str)
                        if logger:
                            logger.log(f"[LOG] Match found for '{k_str}' ({len(keys[k_str])} bytes) at line {line_idx}.")
                        if len(keys) == len(required_keys):
                            if logger:
                                logger.log("[LOG] All required keys extracted successfully.")
                            break
    except Exception as e:
        raise RuntimeError(f"Failed to read keys file: {e}")
    return keys

def decrypt_prodinfo(encrypted_data, bis_key_00, logger=None):
    sector_size = 0x4000
    total_sectors = len(encrypted_data) // sector_size
    decrypted_data = bytearray()
    
    if logger:
        logger.log(f"[LOG] Starting AES-XTS decryption (Block size: {hex(sector_size)}, Sectors: {total_sectors}).")

    for i in range(0, len(encrypted_data), sector_size):
        if logger and i % (sector_size * 10) == 0:
            logger.log(f"[LOG] Decrypting AES-XTS block offset 0x{i:08X} to 0x{i+sector_size:08X}...")
        
        chunk = encrypted_data[i:i+sector_size]
        if len(chunk) < 16:
            decrypted_data += chunk
            continue
            
        tweak = (i // sector_size).to_bytes(16, 'little')
        cipher = Cipher(algorithms.AES(bis_key_00), modes.XTS(tweak), backend=default_backend())
        decrypted_data += cipher.decryptor().update(chunk)

    if logger:
        logger.log("[LOG] Decryption complete. Validating CAL0 signature...")

    if decrypted_data[:4] != b"CAL0":
        if logger:
            viewer = decrypted_data[:4]
            logger.log(f"[LOG] Signature mismatch. Found: {viewer}")
        return None
        
    if logger:
        logger.log("[LOG] CAL0 signature verified.")
        
    return bytes(decrypted_data)

def recover_rsa_private_key(n, e, d, logger=None):
    if logger:
        logger.log(f"[LOG] Reconstructing RSA key (N: {n.bit_length()} bits, D: {d.bit_length()} bits).")
        logger.log(f"[LOG] Calculating Euler's totient approximation matrix for D length {d.bit_length()}...")
        
    k = d * e - 1
    t, r = 0, k
    
    while r % 2 == 0:
        t += 1
        r //= 2

    cracked = False
    for attempt in range(1, 101):
        if logger and attempt % 25 == 0:
            logger.log(f"[LOG] Factorization loop checkpoint: attempt {attempt}/100...")
            
        g = 2 if attempt == 1 else 3
        y = pow(g, r, n)
        if y == 1 or y == n - 1:
            continue
        for j in range(1, t):
            x = pow(y, 2, n)
            if x == 1:
                cracked = True
                if logger:
                    logger.log(f"[LOG] Prime factorization succeeded on attempt {attempt}.")
                break
            if x == n - 1:
                break
            y = x
        if cracked:
            break
            
    if not cracked:
        raise RuntimeError("Mathematical factorization of the RSA key failed.")

    p = math.gcd(y - 1, n)
    q = n // p
    if p < q: p, q = q, p
    
    if logger:
        logger.log("[LOG] Validating extracted P and Q factors...")
        
    if p * q != n:
        raise ValueError("RSA Mathematical Integrity Error: Extracted factors P and Q do not evaluate back to the original Modulus N.")

    if logger:
        logger.log("[LOG] Validating Euler's Totient alignment...")
    phi = (p - 1) * (q - 1)
    if (e * d) % phi != 1:
        raise ValueError("RSA Mathematical Integrity Error: Public and Private exponents are unaligned with the factorization matrix.")

    if logger:
        logger.log("[LOG] RSA matrices verified. Building private key context.")

    public_numbers = rsa.RSAPublicNumbers(e, n)
    private_numbers = rsa.RSAPrivateNumbers(
        p=p, q=q, d=d, dmp1=d % (p - 1), dmq1=d % (q - 1), 
        iqmp=pow(q, -1, p), public_numbers=public_numbers
    )
    return private_numbers.private_key(default_backend())

def extract_and_build_pem(cal0_data, ssl_rsa_kek, logger=None):
    if logger:
        logger.log("[LOG] Locating public certificate at offset 0x0AD0.")
        
    cert_size = struct.unpack("<I", cal0_data[0x0AD0:0x0AD4])[0]
    if logger:
        logger.log(f"[LOG] Certificate size descriptor: {cert_size} bytes.")
        
    if cert_size == 0 or cert_size > 0x1000:
        raise ValueError("Invalid certificate size. PRODINFO might be blank or wiped (e.g., Incognito).")
        
    cert_data = cal0_data[0x0AE0:0x0AE0+cert_size]
    
    if logger:
        logger.log("[LOG] Decoding ASN.1 DER certificate.")
    cert = x509.load_der_x509_certificate(cert_data, default_backend())
    
    try:
        expiration_date = cert.not_valid_after_utc
    except AttributeError:
        expiration_date = cert.not_valid_after

    if logger:
        logger.log("[LOG] Parsing x509 structure to extract metadata...")
        logger.log(f"[LOG] Subject: {cert.subject.rfc4514_string()}")
        logger.log(f"[LOG] Issuer: {cert.issuer.rfc4514_string()}")
        logger.log(f"[LOG] Valid until: {expiration_date}")

    cert_info = f"Subject: {cert.subject.rfc4514_string()}\nIssuer: {cert.issuer.rfc4514_string()}\nExpiration: {expiration_date}"
    
    if logger:
        logger.log("[LOG] Isolating encrypted private RSA key parameters at offset 0x3AE0.")
    ssl_ext_key = cal0_data[0x3AE0:0x3AE0+0x110]
    iv = ssl_ext_key[:0x10]
    encrypted_d = ssl_ext_key[0x10:]
    
    cipher_dec = Cipher(algorithms.AES(ssl_rsa_kek), modes.CTR(iv), backend=default_backend())
    decrypted_d_bytes = cipher_dec.decryptor().update(encrypted_d) + cipher_dec.decryptor().finalize()

    if logger:
        logger.log("[LOG] Re-encrypting exponent to validate AES-CTR integrity...")
    cipher_enc = Cipher(algorithms.AES(ssl_rsa_kek), modes.CTR(iv), backend=default_backend())
    re_encrypted_d = cipher_enc.encryptor().update(decrypted_d_bytes) + cipher_enc.encryptor().finalize()
    if re_encrypted_d != encrypted_d:
        raise ValueError("AES Reverse Integrity Error: Re-encrypted block mismatch. Payload or hardware keys are corrupted.")

    private_key = recover_rsa_private_key(cert.public_key().public_numbers().n, cert.public_key().public_numbers().e, int.from_bytes(decrypted_d_bytes, 'big'), logger)
    
    if logger:
        logger.log("[LOG] Running test signature to validate Private/Public RSA pair.")
    test_payload = b"NX-ProdToPEM-Integrity-Check"
    try:
        signature = private_key.sign(
            test_payload,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        cert.public_key().verify(
            signature,
            test_payload,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        if logger:
            logger.log("[LOG] RSA pairing verified successfully.")
    except Exception as e:
        raise ValueError(f"RSA Cryptographic Integrity Error: Reconstructed private key cannot validate the certificate chain. Details: {e}")
    
    if logger:
        logger.log("[LOG] Generating final OpenSSL PEM encoded strings.")
    clean_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    return clean_key + cert.public_bytes(serialization.Encoding.PEM), cert_info

class TerminalLineRewriter:
    def __init__(self):
        self.last_state = None
        self.line_count = 0
        self.history = []

    def log(self, text):
        print(text)
        self.history.append(text)
        self.line_count += 1

    def force_clear(self):
        if self.line_count > 0:
            for _ in range(self.line_count):
                sys.stdout.write('\x1b[1A\x1b[2K')
            self.line_count = 0
            sys.stdout.flush()

    def set_verbose_state(self, active):
        if self.last_state == active: return
        self.force_clear()
        msg = "[LOG] Verbose mode activated." if active else "[LOG] Verbose mode deactivated."
        print(msg)
        self.history.append(msg)
        self.line_count = 1
        sys.stdout.flush()
        self.last_state = active

    def export(self, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(self.history))

class MainWindowProdToPEM(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NX-ProdToPEM (GUI)")
        
        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(SVG_LOGO_DATA))
        self.setWindowIcon(QIcon(pixmap))
        
        self.logger = TerminalLineRewriter()
        self.current_theme_dark = darkdetect.isDark()
        self.config_filename = "config-prodtopem.txt"
        self.config_allowed = True
        self.is_restarting = False
        self.startup_warning_accepted = False
        self.app_version = "1.2.1"
        
        self.spinner_frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.spinner_idx = 0
        self.spinner_timer = QTimer(self)
        self.spinner_timer.timeout.connect(self.update_spinner)
        self.is_auto_check = False
        
        self.rainbow_timer = QTimer(self)
        self.rainbow_timer.timeout.connect(self.update_rainbow)
        self.rainbow_hue = 0
        
        self.init_ui()
        self.load_configuration_file()
        
        if self.btn_advanced.isChecked():
            self.logger.log("[LOG] GUI initialized.")
        
        self.prodinfo_le.textChanged.connect(self.save_configuration_file)
        self.keys_le.textChanged.connect(self.save_configuration_file)
        self.output_le.textChanged.connect(self.save_configuration_file)
        
        self.theme_timer = QTimer(self)
        self.theme_timer.timeout.connect(self.check_system_theme)
        self.theme_timer.start(1000)

        QTimer.singleShot(200, self.check_startup_warning)
        QTimer.singleShot(500, lambda: self.start_update_check(auto=True))

    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        self.card_frame = QFrame(self)
        self.card_frame.setObjectName("Card")
        self.card_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        card_layout = QVBoxLayout(self.card_frame)
        card_layout.setContentsMargins(15, 12, 15, 12)
        card_layout.setSpacing(10)
        
        header_layout = QGridLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_about = QPushButton("About")
        self.btn_about.setObjectName("btnHeader")
        self.btn_about.clicked.connect(self.show_about)
        
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title_lbl = QLabel("NX-ProdToPEM GUI", title_container)
        title_lbl.setObjectName("CardTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        version_lbl = QLabel(f"v{self.app_version}", title_container)
        version_lbl.setObjectName("CardVersion")
        version_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_layout.addWidget(title_lbl)
        title_layout.addWidget(version_lbl)
        
        right_container = QWidget()
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        
        self.btn_update = QPushButton("Check for Updates")
        self.btn_update.setObjectName("btnHeader")
        self.btn_update.clicked.connect(self.manual_check_updates)
        
        self.lbl_spinner = QLabel("")
        self.lbl_spinner.setMinimumWidth(15)
        self.lbl_spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.opacity_effect = QGraphicsOpacityEffect(self.lbl_spinner)
        self.lbl_spinner.setGraphicsEffect(self.opacity_effect)
        
        self.pulse_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.pulse_anim.setStartValue(1.0)
        self.pulse_anim.setKeyValueAt(0.5, 0.3)
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.setLoopCount(-1)
        
        right_layout.addWidget(self.lbl_spinner, alignment=Qt.AlignmentFlag.AlignVCenter)
        right_layout.addWidget(self.btn_update, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        header_layout.addWidget(self.btn_about, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        header_layout.addWidget(title_container, 0, 1, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        header_layout.addWidget(right_container, 0, 2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        
        header_layout.setColumnStretch(0, 1)
        header_layout.setColumnStretch(1, 0)
        header_layout.setColumnStretch(2, 1)
        
        card_layout.addLayout(header_layout)
        
        grid_container = QWidget(self.card_frame)
        grid_container.setObjectName("CardGrid")
        grid_layout = QGridLayout(grid_container)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(12)
        
        prodinfo_lbl = QLabel("PRODINFO.bin path:", grid_container)
        prodinfo_lbl.setMinimumWidth(130)
        self.prodinfo_le = DropLineEdit(expected_filename="PRODINFO.bin", is_directory=False, parent=grid_container)
        btn_browse_prodinfo = QPushButton("Browse...", grid_container)
        btn_browse_prodinfo.clicked.connect(self.browse_prodinfo)
        btn_help_prodinfo = QPushButton("?", grid_container)
        btn_help_prodinfo.setObjectName("btnHelp")
        btn_help_prodinfo.clicked.connect(self.show_help_prodinfo)
        
        grid_layout.addWidget(prodinfo_lbl, 0, 0, Qt.AlignmentFlag.AlignVCenter)
        grid_layout.addWidget(self.prodinfo_le, 0, 1, Qt.AlignmentFlag.AlignVCenter)
        grid_layout.addWidget(btn_browse_prodinfo, 0, 2, Qt.AlignmentFlag.AlignVCenter)
        grid_layout.addWidget(btn_help_prodinfo, 0, 3, Qt.AlignmentFlag.AlignVCenter)
        
        keys_lbl = QLabel("prod.keys path:", grid_container)
        keys_lbl.setMinimumWidth(130)
        self.keys_le = DropLineEdit(expected_filename="prod.keys", is_directory=False, parent=grid_container)
        btn_browse_keys = QPushButton("Browse...", grid_container)
        btn_browse_keys.clicked.connect(self.browse_keys)
        btn_help_keys = QPushButton("?", grid_container)
        btn_help_keys.setObjectName("btnHelp")
        btn_help_keys.clicked.connect(self.show_help_keys)
        
        grid_layout.addWidget(keys_lbl, 1, 0, Qt.AlignmentFlag.AlignVCenter)
        grid_layout.addWidget(self.keys_le, 1, 1, Qt.AlignmentFlag.AlignVCenter)
        grid_layout.addWidget(btn_browse_keys, 1, 2, Qt.AlignmentFlag.AlignVCenter)
        grid_layout.addWidget(btn_help_keys, 1, 3, Qt.AlignmentFlag.AlignVCenter)

        output_lbl = QLabel("Destination folder:", grid_container)
        output_lbl.setMinimumWidth(130)
        self.output_le = DropLineEdit(expected_filename=None, is_directory=True, parent=grid_container)
        self.output_le.setPlaceholderText("Optional")
        btn_browse_output = QPushButton("Browse...", grid_container)
        btn_browse_output.clicked.connect(self.browse_output)
        
        btn_help_hidden = QPushButton(grid_container)
        btn_help_hidden.setObjectName("btnHelpHidden")
        
        grid_layout.addWidget(output_lbl, 2, 0, Qt.AlignmentFlag.AlignVCenter)
        grid_layout.addWidget(self.output_le, 2, 1, Qt.AlignmentFlag.AlignVCenter)
        grid_layout.addWidget(btn_browse_output, 2, 2, Qt.AlignmentFlag.AlignVCenter)
        grid_layout.addWidget(btn_help_hidden, 2, 3, Qt.AlignmentFlag.AlignVCenter)
        
        card_layout.addWidget(grid_container)
        main_layout.addWidget(self.card_frame)
        
        bottom_container = QWidget(central_widget)
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        left_bottom_layout = QVBoxLayout()
        left_bottom_layout.setSpacing(4)
        
        self.btn_restart = QPushButton("Restart App", bottom_container)
        self.btn_restart.setObjectName("btnRestart")
        self.btn_restart.clicked.connect(self.restart_application)
        
        self.btn_reset_config = QPushButton("Reset Config", bottom_container)
        self.btn_reset_config.setObjectName("btnResetConfig")
        self.btn_reset_config.clicked.connect(self.reset_configuration_file)
        
        left_bottom_layout.addWidget(self.btn_restart)
        left_bottom_layout.addWidget(self.btn_reset_config)
        
        self.btn_execute = QPushButton("Generate certificat.pem", bottom_container)
        self.btn_execute.setObjectName("btnExecute")
        self.btn_execute.clicked.connect(self.process_conversion)
        
        right_bottom_layout = QVBoxLayout()
        right_bottom_layout.setSpacing(4)
        
        self.btn_advanced = QPushButton("Advanced Logs", bottom_container)
        self.btn_advanced.setObjectName("btnAdvancedLogs")
        self.btn_advanced.setCheckable(True)
        self.btn_advanced.clicked.connect(self.toggle_advanced_logs)
        
        self.btn_report_issue = QPushButton("Report Issue", bottom_container)
        self.btn_report_issue.setObjectName("btnReportIssue")
        self.btn_report_issue.clicked.connect(lambda: webbrowser.open("https://github.com/JeremKOYTB/NX-ProdToPEM/issues/new"))
        
        right_bottom_layout.addWidget(self.btn_advanced)
        right_bottom_layout.addWidget(self.btn_report_issue)
        
        bottom_layout.addLayout(left_bottom_layout)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.btn_execute, 0, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        bottom_layout.addStretch(1)
        bottom_layout.addLayout(right_bottom_layout)
        
        main_layout.addWidget(bottom_container)
        
        self.setFixedSize(720, 350)

    def update_spinner(self):
        self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_frames)
        self.lbl_spinner.setText(self.spinner_frames[self.spinner_idx])
        
    def update_rainbow(self):
        self.rainbow_hue = (self.rainbow_hue + 5) % 360
        color = QColor.fromHsv(self.rainbow_hue, 200, 255).name()
        self.card_frame.setStyleSheet(f"QFrame#Card {{ border: 2px solid {color}; }}")

    def manual_check_updates(self):
        if self.btn_advanced.isChecked():
            self.logger.log("[LOG] Manual update check requested.")
        self.start_update_check(auto=False)

    def start_update_check(self, auto=False):
        self.pulse_anim.stop()
        self.opacity_effect.setOpacity(1.0)
        self.is_auto_check = auto
        self.lbl_spinner.setText(self.spinner_frames[0])
        self.spinner_timer.start(100)
        self.btn_update.setEnabled(False)
        
        if self.btn_advanced.isChecked():
            self.logger.log(f"[LOG] Querying GitHub API for releases (Auto: {auto})...")
            
        self.update_thread = UpdateCheckerThread()
        self.update_thread.finished.connect(self.process_update_check_result)
        self.update_thread.start()

    def process_update_check_result(self, data, error_str):
        self.spinner_timer.stop()
        self.btn_update.setEnabled(True)
        
        if error_str:
            self.lbl_spinner.setText("✖")
            self.pulse_anim.setDuration(1000)
            self.pulse_anim.start()
            
            if self.btn_advanced.isChecked():
                self.logger.log(f"[LOG] Update check failed: {error_str}")
            
            if "403" in error_str:
                rate_msg = (
                    "Update check is currently impossible because GitHub has temporarily blocked "
                    "update requests on your IP address due to API rate limits.\n\n"
                    "This is not a serious issue and the application remains fully functional, "
                    "but it cannot verify if it is running the latest version at this moment.\n\n"
                    "If you are unsure whether you are up to date, you can check the repository manually on GitHub."
                )
                QMessageBox.warning(self, "API Rate Limit Exceeded", rate_msg)
            elif ("getaddrinfo failed" in error_str or "11001" in error_str):
                if not self.is_auto_check:
                    network_msg = (
                        "Unable to establish a connection to the internet.\n\n"
                        "The application could not reach GitHub servers to check for updates. "
                        "Please verify your network connection and try again.\n\n"
                        "You can still continue to use all certificate decryption features normally."
                    )
                    QMessageBox.warning(self, "Network Connection Error", network_msg)
            elif not self.is_auto_check:
                QMessageBox.warning(self, "Error", f"Failed to check for updates:\n{error_str}")
            return
            
        latest_version = data.get("tag_name", "").lstrip("v")
        changelog = data.get("body", "No changelog provided.")
        assets = data.get("assets", [])
        
        if self.btn_advanced.isChecked():
            self.logger.log(f"[LOG] GitHub API responded. Latest remote version: v{latest_version}")

        if not latest_version:
            self.lbl_spinner.setText("❓")
            self.pulse_anim.setDuration(1000)
            self.pulse_anim.start()
            if not self.is_auto_check:
                msg = "The latest update data could not be found on GitHub.\n\nThere might be an issue with the currently published release. Please verify the status or open an issue on the repository.\n\nWould you like to open the repository to check?"
                if QMessageBox(QMessageBox.Icon.Warning, "Release Not Found", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self).exec() == QMessageBox.StandardButton.Yes:
                    webbrowser.open("https://github.com/JeremKOYTB/NX-ProdToPEM")
                return

        download_url = next((a["browser_download_url"] for a in assets if a["name"] == "NX-ProdToPEM-GUI.py"), None)
        if not download_url:
            download_url = f"https://raw.githubusercontent.com/JeremKOYTB/NX-ProdToPEM/v{latest_version}/NX-ProdToPEM-GUI.py"

        try:
            def parse_ver(v_str):
                return [int(x) for x in v_str.split('.')]
            current_parsed = parse_ver(self.app_version)
            latest_parsed = parse_ver(latest_version)
        except Exception:
            current_parsed = [0]
            latest_parsed = [0]

        if current_parsed < latest_parsed:
            self.lbl_spinner.setText("⬇️")
            self.pulse_anim.setDuration(2500)
            self.pulse_anim.start()
            
            if self.btn_advanced.isChecked():
                self.logger.log(f"[LOG] Update available! (v{self.app_version} -> v{latest_version}). Prompting user.")
                
            msg = f"A new stable version (v{latest_version}) is available!\n\nUpdating is highly recommended to ensure everything works properly.\n\nChangelog:\n{changelog}"
            box = QMessageBox(QMessageBox.Icon.Information, "Update Recommended", msg, QMessageBox.StandardButton.NoButton, self)
            
            btn_upgrade = box.addButton("Upgrade", QMessageBox.ButtonRole.YesRole)
            btn_cancel = box.addButton("Cancel", QMessageBox.ButtonRole.NoRole)
            btn_all = box.addButton("View All Versions", QMessageBox.ButtonRole.ActionRole)
            
            box.setDefaultButton(btn_upgrade)
            box.setEscapeButton(btn_cancel)
            
            box_layout = box.layout()
            if box_layout:
                for i in range(box_layout.count()):
                    item = box_layout.itemAt(i)
                    if item and item.layout():
                        btn_box_layout = item.layout()
                        btn_box_layout.removeWidget(btn_all)
                        btn_box_layout.insertWidget(0, btn_all)
                        break

            box.exec()
            
            if box.clickedButton() == btn_all:
                dialog = UpdateManagerDialog(self, self.app_version)
                dialog.exec()
            elif box.clickedButton() == btn_upgrade:
                self.download_and_restart(download_url)
                
        elif current_parsed > latest_parsed:
            self.lbl_spinner.setText("⚠️")
            self.pulse_anim.setDuration(1000)
            self.pulse_anim.start()
            
            if self.btn_advanced.isChecked():
                self.logger.log("[LOG] Local version is newer than remote stable. Assuming beta/development branch.")
                
            if not self.is_auto_check:
                msg = f"You are currently running a main branch version (v{self.app_version}), which is newer than the latest stable release (v{latest_version}).\n\nNew features are prioritized here, but reliability might be lower. Use this current version at your own risk."
                box = QMessageBox(QMessageBox.Icon.Warning, "Main branch version detected!", msg, QMessageBox.StandardButton.NoButton, self)
                
                btn_downgrade = box.addButton("Downgrade", QMessageBox.ButtonRole.YesRole)
                btn_cancel = box.addButton("Cancel", QMessageBox.ButtonRole.NoRole)
                btn_all = box.addButton("View All Versions", QMessageBox.ButtonRole.ActionRole)
                
                box.setDefaultButton(btn_cancel)
                box.setEscapeButton(btn_cancel)
                
                box_layout = box.layout()
                if box_layout:
                    for i in range(box_layout.count()):
                        item = box_layout.itemAt(i)
                        if item and item.layout():
                            btn_box_layout = item.layout()
                            btn_box_layout.removeWidget(btn_all)
                            btn_box_layout.insertWidget(0, btn_all)
                            break

                box.exec()
                
                if box.clickedButton() == btn_all:
                    dialog = UpdateManagerDialog(self, self.app_version)
                    dialog.exec()
                elif box.clickedButton() == btn_downgrade:
                    self.download_and_restart(download_url)
        else:
            self.lbl_spinner.setText("✔")
            QTimer.singleShot(5000, lambda: self.lbl_spinner.setText("") if self.lbl_spinner.text() == "✔" else None)
            
            if self.btn_advanced.isChecked():
                self.logger.log("[LOG] Application is up to date.")
                
            if not self.is_auto_check:
                msg = f"Everything is fine! You are already using the latest version (v{self.app_version}).\n\nCurrent Changelog:\n{changelog}"
                box = QMessageBox(QMessageBox.Icon.Information, "Up to Date", msg, QMessageBox.StandardButton.NoButton, self)
                
                btn_reinstall = box.addButton("Reinstall", QMessageBox.ButtonRole.YesRole)
                btn_cancel = box.addButton("Cancel", QMessageBox.ButtonRole.NoRole)
                btn_all = box.addButton("View All Versions", QMessageBox.ButtonRole.ActionRole)
                
                box.setDefaultButton(btn_cancel)
                box.setEscapeButton(btn_cancel)
                
                box_layout = box.layout()
                if box_layout:
                    for i in range(box_layout.count()):
                        item = box_layout.itemAt(i)
                        if item and item.layout():
                            btn_box_layout = item.layout()
                            btn_box_layout.removeWidget(btn_all)
                            btn_box_layout.insertWidget(0, btn_all)
                            break

                box.exec()
                
                if box.clickedButton() == btn_all:
                    dialog = UpdateManagerDialog(self, self.app_version)
                    dialog.exec()
                elif box.clickedButton() == btn_reinstall:
                    self.download_and_restart(download_url)

    def download_and_restart(self, url):
        if getattr(sys, 'frozen', False):
            msg = "The application is currently running as a compiled executable.\n\nAuto-updating is disabled to prevent system conflicts. Please download the new version manually from GitHub."
            QMessageBox.information(self, "Manual Update Required", msg)
            webbrowser.open("https://github.com/JeremKOYTB/NX-ProdToPEM/releases/latest")
            return

        if self.btn_advanced.isChecked():
            self.logger.log(f"[LOG] Initiating code download from: {url}")
            
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'NX-ProdToPEM-Updater'})
            with urllib.request.urlopen(req, timeout=10) as response:
                new_code = response.read()

            if self.btn_advanced.isChecked():
                self.logger.log(f"[LOG] Downloaded {len(new_code)} bytes. Validating payload integrity...")

            if len(new_code) < 10000:
                raise ValueError("Downloaded payload is suspiciously small. Integrity verification failed.")

            if self.btn_advanced.isChecked():
                self.logger.log("[LOG] Parsing AST to verify Python syntax structure...")
            try:
                ast.parse(new_code)
                if self.btn_advanced.isChecked():
                    self.logger.log("[LOG] AST validation passed. Syntax is correct.")
            except SyntaxError as syntax_err:
                raise ValueError(f"Downloaded payload contains syntax errors: {syntax_err}")
            except Exception as ast_err:
                raise ValueError(f"Downloaded payload failed AST verification: {ast_err}")
            
            target_file = os.path.abspath(sys.argv[0])
            temp_file = target_file + ".update.tmp"
            
            if self.btn_advanced.isChecked():
                self.logger.log(f"[LOG] Performing atomic write to temporary file: {temp_file}")
                
            with open(temp_file, "wb") as f:
                f.write(new_code)
                
            if self.btn_advanced.isChecked():
                self.logger.log(f"[LOG] Replacing current execution file.")
                
            os.replace(temp_file, target_file)
                
            QMessageBox.information(self, "Success", "Update downloaded and integrity validated. The application will now restart.")
            self.is_restarting = True
            QApplication.quit()
        except Exception as e:
            QMessageBox.warning(self, "Download Error", f"Failed to install the update safely:\n{e}")

    def show_about(self):
        dialog = AboutDialog(self, self.current_theme_dark, self.app_version)
        dialog.exec()

    def check_startup_warning(self):
        if not self.startup_warning_accepted:
            msg = (
                "Welcome!\n\n"
                "This software is provided 'as-is'. In the event of any errors or console bans, "
                "the author declines all responsibility.\n\n"
                "This tool has been validated on an Erista Switch running system version 22.1.0, "
                "but any other Switch + OS configurations are not 100% guaranteed to be OK.\n"
                "If you have any doubts, do not hesitate to discuss it with the author.\n\n"
                "ALSO:\n"
                "All files required by this tool must absolutely not be shared on the internet.\n\n"
                "This is extremely dangerous because anyone can get your console banned. "
                "Be vigilant with what you share online."
            )
            QMessageBox.warning(self, "Disclaimer", msg, QMessageBox.StandardButton.Ok)
            self.startup_warning_accepted = True
            self.save_configuration_file()

    def load_configuration_file(self):
        cwd = os.getcwd()
        if not os.access(cwd, os.R_OK):
            self.config_allowed = False
            QTimer.singleShot(100, lambda: QMessageBox.warning(self, "Read Permission Denied", "The application cannot read directory permissions. Saved configurations will not be loaded."))
            self.fallback_auto_detect()
            return

        if not os.path.exists(self.config_filename):
            self.fallback_auto_detect()
            return

        try:
            with open(self.config_filename, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.prodinfo_le.setText(data.get("prodinfo_path", ""))
            self.keys_le.setText(data.get("keys_path", ""))
            self.output_le.setText(data.get("output_path", ""))
            
            advanced_state = data.get("advanced_logs", False)
            self.btn_advanced.setChecked(advanced_state)
            if advanced_state:
                self.logger.set_verbose_state(True)
                self.logger.log("[LOG] Configuration loaded successfully.")
                self.logger.log(f"[LOG] PRODINFO path: '{data.get('prodinfo_path', '')}'")
                self.logger.log(f"[LOG] Keys path: '{data.get('keys_path', '')}'")
                
            self.startup_warning_accepted = data.get("startup_warning_accepted", False)
                
            if data.get("version") != self.app_version:
                if self.btn_advanced.isChecked():
                    self.logger.log("[LOG] Version mismatch in config. Updating JSON structure.")
                QTimer.singleShot(100, lambda: QMessageBox.warning(self, "Configuration Note", "The config-prodtopem.txt file has been updated."))
                self.save_configuration_file()
                
        except Exception:
            QTimer.singleShot(100, lambda: QMessageBox.warning(self, "Configuration Altered", "The configuration file appears to be corrupted.\n\nIt has been skipped and will be reconstructed."))
            self.fallback_auto_detect()
            self.save_configuration_file()

    def save_configuration_file(self):
        if not self.config_allowed: return
        if not os.access(os.getcwd(), os.W_OK):
            self.config_allowed = False
            QMessageBox.warning(self, "Write Permission Denied", "The application has lost write permissions in this folder.\n\nSettings will not be saved.")
            return

        try:
            data = {
                "version": self.app_version,
                "prodinfo_path": self.prodinfo_le.text(),
                "keys_path": self.keys_le.text(),
                "output_path": self.output_le.text(),
                "advanced_logs": self.btn_advanced.isChecked(),
                "startup_warning_accepted": self.startup_warning_accepted
            }
            if self.btn_advanced.isChecked():
                self.logger.log(f"[LOG] Saving configuration to: '{self.config_filename}'")
            with open(self.config_filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception:
            self.config_allowed = False
            QMessageBox.warning(self, "Saving Error", "An error occurred while saving the configuration settings.")

    def reset_configuration_file(self):
        if self.btn_advanced.isChecked():
            self.logger.log("[LOG] Resetting configuration file fields as requested by user.")
        
        self.prodinfo_le.blockSignals(True)
        self.keys_le.blockSignals(True)
        self.output_le.blockSignals(True)
        
        self.prodinfo_le.clear()
        self.keys_le.clear()
        self.output_le.clear()
        
        self.prodinfo_le.blockSignals(False)
        self.keys_le.blockSignals(False)
        self.output_le.blockSignals(False)
        
        self.save_configuration_file()
        
        if self.btn_advanced.isChecked():
            self.logger.log("[LOG] Configuration cleared and UI updated successfully.")
            
        QMessageBox.information(self, "Config Reset", "Configuration fields have been completely cleared and reset.")

    def fallback_auto_detect(self):
        if self.btn_advanced.isChecked():
            self.logger.log("[LOG] Scanning current directory for default file names (PRODINFO.bin / prod.keys)...")
        if os.path.exists("PRODINFO.bin"): 
            self.prodinfo_le.setText(os.path.abspath("PRODINFO.bin"))
        if os.path.exists("prod.keys"): 
            self.keys_le.setText(os.path.abspath("prod.keys"))
        self.output_le.setText("")

    def check_system_theme(self):
        is_dark = darkdetect.isDark()
        if is_dark != self.current_theme_dark:
            if self.btn_advanced.isChecked():
                self.logger.log(f"[LOG] OS Theme change detected. IsDark: {is_dark}")
            self.current_theme_dark = is_dark
            QApplication.instance().setStyleSheet(get_stylesheet(is_dark))

    def browse_prodinfo(self):
        if self.btn_advanced.isChecked():
            self.logger.log("[LOG] Opening file dialog for PRODINFO.bin")
        filepath, _ = QFileDialog.getOpenFileName(self, "Select PRODINFO.bin", "", "Binary files (*.bin);;All files (*.*)")
        if filepath:
            if self.btn_advanced.isChecked():
                self.logger.log(f"[LOG] Selected PRODINFO path: '{filepath}'")
            if os.path.basename(filepath).lower() != "prodinfo.bin":
                msg = f"The selected file is named '{os.path.basename(filepath)}' instead of 'PRODINFO.bin'.\n\nWould you like to select a different file?"
                if QMessageBox(QMessageBox.Icon.Question, "Unexpected Filename", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self).exec() == QMessageBox.StandardButton.Yes:
                    self.browse_prodinfo()
                    return
            self.prodinfo_le.setText(filepath)

    def browse_keys(self):
        if self.btn_advanced.isChecked():
            self.logger.log("[LOG] Opening file dialog for prod.keys")
        filepath, _ = QFileDialog.getOpenFileName(self, "Select prod.keys", "", "Key files (*.keys);;Text files (*.txt);;All files (*.*)")
        if filepath:
            if self.btn_advanced.isChecked():
                self.logger.log(f"[LOG] Selected Keys path: '{filepath}'")
            if os.path.basename(filepath).lower() != "prod.keys":
                msg = f"The selected file is named '{os.path.basename(filepath)}' instead of 'prod.keys'.\n\nWould you like to select a different file?"
                if QMessageBox(QMessageBox.Icon.Question, "Unexpected Filename", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self).exec() == QMessageBox.StandardButton.Yes:
                    self.browse_keys()
                    return
            self.keys_le.setText(filepath)

    def browse_output(self):
        if self.btn_advanced.isChecked():
            self.logger.log("[LOG] Opening directory dialog for destination folder.")
        dirpath = QFileDialog.getExistingDirectory(self, "Select Destination Folder", "")
        if dirpath: 
            if self.btn_advanced.isChecked():
                self.logger.log(f"[LOG] Output path set to: '{dirpath}'")
            self.output_le.setText(dirpath)

    def toggle_advanced_logs(self):
        self.logger.set_verbose_state(self.btn_advanced.isChecked())
        self.save_configuration_file()

    def trigger_log_export(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Logs", "nx_prodtopem_logs.txt", "Text Files (*.txt);;All Files (*.*)")
        if filepath:
            self.logger.export(filepath)
            QMessageBox.information(self, "Logs Exported", f"Logs successfully saved to:\n{filepath}")

    def restart_application(self):
        if self.btn_advanced.isChecked():
            self.logger.log("[LOG] User requested manual application restart.")
        if QMessageBox(QMessageBox.Icon.Question, "Confirm Restart", "Are you sure you want to completely restart NX-ProdToPEM GUI?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self).exec() == QMessageBox.StandardButton.Yes:
            self.is_restarting = True
            self.logger.force_clear()
            QApplication.quit()

    def show_help_prodinfo(self):
        msg = (
            "How to get your PRODINFO.bin:\n\n"
            "You do not need to perform a full eMMC dump.\n"
            "1. Open the Hekate bootloader menu.\n"
            "2. Dump your console's partitions\n(choose \"eMMC SYS\", not \"eMMC RAW GPP\").\n\n"
            "This method is much faster than a full dump. Once finished, you will find your file here:\n"
            "SD:/backup/xxxxxxxx/partitions/PRODINFO.bin\n\n"
            "('xxxxxxxx' varies based on your console's unique hardware ID.)"
        )
        QMessageBox(QMessageBox.Icon.Information, "PRODINFO.bin Help", msg, QMessageBox.StandardButton.Ok, self).exec()

    def show_help_keys(self):
        msg = (
            "How to get your prod.keys:\n\n"
            "Your prod.keys file must contain at least the 'bis_key_00' and 'ssl_rsa_kek' keys.\n\n"
            "To download Lockpick_RCM with up-to-date system support, use this repository:\n\n"
            "https://github.com/THZoria/Lockpick_RCMaster \n\n"
            "Once keys are dumped, you will find them here:\n"
            "SD:/switch/prod.keys\n\n"
            "Would you like to open this link in your web browser now?"
        )
        if QMessageBox(QMessageBox.Icon.Question, "prod.keys Help", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self).exec() == QMessageBox.StandardButton.Yes:
            if self.btn_advanced.isChecked():
                self.logger.log("[LOG] Opening web browser: THZoria/Lockpick_RCMaster")
            webbrowser.open("https://github.com/THZoria/Lockpick_RCMaster")

    def handle_thread_log(self, msg):
        if self.btn_advanced.isChecked():
            self.logger.log(msg)

    def handle_conversion_success(self, pem_data, out_dir, cert_info):
        self.btn_execute.setEnabled(True)
        self.rainbow_timer.start(50)
        
        pem_output = os.path.join(out_dir, "certificat.pem")
        if self.btn_advanced.isChecked():
            self.logger.log(f"[LOG] Writing {len(pem_data)} bytes to {pem_output}...")
            self.logger.log("[LOG] Done!")
            
        with open(pem_output, "wb") as f_out:
            f_out.write(pem_data)
            
        if self.btn_advanced.isChecked():
            success_msg = (
                "The certificat.pem file has been successfully generated!\n\n"
                f"Certificate details:\n{cert_info}\n\n"
                "Do you want to safely close the application now to clean up resources?"
            )
        else:
            success_msg = (
                "The certificat.pem file has been successfully generated!\n\n"
                "Do you want to safely close the application now to clean up resources?"
            )
        
        box = QMessageBox(QMessageBox.Icon.Information, "Extraction Successful", success_msg, QMessageBox.StandardButton.NoButton, self)
        btn_yes = box.addButton("Yes", QMessageBox.ButtonRole.YesRole)
        btn_no = box.addButton("No", QMessageBox.ButtonRole.NoRole)
        
        btn_save_logs = None
        if self.btn_advanced.isChecked():
            btn_save_logs = box.addButton("Save Logs to File", QMessageBox.ButtonRole.ActionRole)
            
        box.setDefaultButton(btn_yes)
        box.exec()
        
        if box.clickedButton() == btn_save_logs:
            self.trigger_log_export()
            self.rainbow_timer.stop()
            self.card_frame.setStyleSheet("")
        elif box.clickedButton() == btn_yes:
            self.window().logger.log("[LOG] Executing safe teardown to prevent memory leaks and ensure app stability.")
            QApplication.quit()
        else:
            self.rainbow_timer.stop()
            self.card_frame.setStyleSheet("")

    def handle_conversion_error(self, err_msg):
        self.btn_execute.setEnabled(True)
        if self.btn_advanced.isChecked():
            self.logger.log(f"[LOG] Critical Thread Error: {err_msg}")
            
        error_msg = f"An issue occurred during execution:\n\n{err_msg}\n\nWould you like to open the issue tracker?"
        box = QMessageBox(QMessageBox.Icon.Critical, "Critical Error", error_msg, QMessageBox.StandardButton.NoButton, self)
        btn_yes = box.addButton("Yes", QMessageBox.ButtonRole.YesRole)
        btn_no = box.addButton("No", QMessageBox.ButtonRole.NoRole)
        
        btn_save_logs = None
        if self.btn_advanced.isChecked():
            btn_save_logs = box.addButton("Save Logs to File", QMessageBox.ButtonRole.ActionRole)
            
        box.setDefaultButton(btn_no)
        box.exec()
        
        if box.clickedButton() == btn_save_logs:
            self.trigger_log_export()
        elif box.clickedButton() == btn_yes: 
            webbrowser.open("https://github.com/JeremKOYTB/NX-ProdToPEM/issues/new")

    def process_conversion(self):
        self.save_configuration_file()
        p_path = self.prodinfo_le.text()
        k_path = self.keys_le.text()
        out_dir = self.output_le.text()
        is_verbose = self.btn_advanced.isChecked()

        if is_verbose:
            self.logger.log("[LOG] Starting PRODINFO to PEM conversion.")
            self.logger.log(f"[LOG] Input PRODINFO: '{p_path}'")
            self.logger.log(f"[LOG] Input Keys: '{k_path}'")

        if not p_path or not os.path.exists(p_path):
            if is_verbose:
                self.logger.log("[LOG] Error: PRODINFO.bin file not found at specified path.")
            return QMessageBox.critical(self, "File Missing", "The selected PRODINFO.bin file could not be found.")
        if not k_path or not os.path.exists(k_path):
            if is_verbose:
                self.logger.log("[LOG] Error: prod.keys file not found at specified path.")
            return QMessageBox.critical(self, "File Missing", "The selected prod.keys file could not be found.")

        if not out_dir.strip(): 
            out_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
            if is_verbose:
                self.logger.log(f"[LOG] No output directory specified. Defaulting to: '{out_dir}'")

        if not os.path.exists(out_dir) or not os.access(out_dir, os.W_OK):
            if is_verbose:
                self.logger.log(f"[LOG] Destination folder is invalid or lacks write permissions: '{out_dir}'")
            QMessageBox.warning(self, "Permission Denied", "The destination folder is invalid or missing write permissions.\nPlease select an alternative folder.")
            alternative_dir = QFileDialog.getExistingDirectory(self, "Select Authorized Destination Folder", "")
            if alternative_dir:
                out_dir = alternative_dir
                self.output_le.setText(out_dir)
                self.save_configuration_file()
            else: return

        pem_output = os.path.join(out_dir, "certificat.pem")
        if is_verbose:
            self.logger.log(f"[LOG] Output target: '{pem_output}'")
        
        if os.path.exists(pem_output):
            if is_verbose:
                self.logger.log("[LOG] certificat.pem already exists. Prompting user for overwrite confirmation.")
            if QMessageBox(QMessageBox.Icon.Warning, "File Conflict", "A 'certificat.pem' file already exists in the selected destination folder.\n\nDo you want to overwrite it?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self).exec() != QMessageBox.StandardButton.Yes:
                if is_verbose:
                    self.logger.log("[LOG] User cancelled overwrite. Operation aborted.")
                return

        self.btn_execute.setEnabled(False)
        self.conversion_thread = ConversionThread(p_path, k_path, out_dir)
        self.conversion_thread.log_signal.connect(self.handle_thread_log)
        self.conversion_thread.success_signal.connect(self.handle_conversion_success)
        self.conversion_thread.error_signal.connect(self.handle_conversion_error)
        self.conversion_thread.start()

def handle_interrupt(window_instance):
    if window_instance.btn_advanced.isChecked():
        window_instance.window().logger.log("[LOG] SIGINT (Ctrl+C) detected, prompting user for exit.")
    box = QMessageBox(QMessageBox.Icon.Question, "Exit?", "Ctrl+C was detected in the terminal.\n\nDo you want to close?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, window_instance)
    box.setDefaultButton(QMessageBox.StandardButton.No)
    box.setWindowFlags(box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
    if box.exec() == QMessageBox.StandardButton.Yes:
        window_instance.logger.log("[LOG] Safe shutdown initiated to prevent memory leaks and ensure app stability.")
        window_instance.logger.force_clear()
        QApplication.quit()
        sys.exit(0)

if __name__ == "__main__":
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("JeremKOYTB.NXProdToPEM.Gui.1.2.1")

    app = QApplication(sys.argv)
    app.setStyleSheet(get_stylesheet(darkdetect.isDark()))
        
    window = MainWindowProdToPEM()
    window.show()
    
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)
    
    signal.signal(signal.SIGINT, lambda sig, frame: handle_interrupt(window))
    
    exit_code = app.exec()
    
    if window.is_restarting:
        del window
        del app
        os.execv(sys.executable, ['"' + sys.executable + '"'] + sys.argv)
        
    sys.exit(exit_code)
