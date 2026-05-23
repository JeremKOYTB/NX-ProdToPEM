import os
import sys
import struct
import math
import random
import subprocess
import importlib.util
import webbrowser
import signal
import json

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
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFrame, QMessageBox, QFileDialog, QStyle, QSizePolicy, QGridLayout)
from PyQt6.QtCore import Qt, QTimer, QByteArray
from PyQt6.QtGui import QIcon, QPixmap
import darkdetect

BASE_FONT = "\"Segoe UI Variable\", \"Segoe UI\", \"Roboto\", sans-serif"

STYLESHEET_DARK = f"""
QMainWindow, QDialog, QMessageBox {{ background-color: #3C3C44; color: #E8E8E8; }}
QWidget {{ font-family: {BASE_FONT}; font-size: 10pt; }}
QLabel {{ color: #E8E8E8; }}
QMessageBox QLabel {{ color: #E8E8E8; background-color: transparent; }}
QFrame#Card {{ background-color: #4A4A54; border-radius: 8px; border: 1px solid #555560; }}
QLabel#CardTitle {{ color: #FFFFFF; font-size: 13pt; font-weight: 700; padding-bottom: 0px; }}
QLabel#CardVersion {{ color: #B0B0B8; font-size: 9pt; font-weight: 500; padding-bottom: 2px; }}
QLineEdit {{ background-color: #32323A; border: 1px solid #555560; border-radius: 6px; padding: 6px 10px; color: #E8E8E8; font-size: 10pt; min-height: 20px; }}
QLineEdit:focus {{ border: 1px solid #C4A1FF; background-color: #3C3C44; }}
QPushButton {{ background-color: #555560; color: #E8E8E8; border-radius: 6px; padding: 6px 14px; font-weight: 600; border: 1px solid #626270; min-height: 20px; }}
QPushButton:hover {{ background-color: #626270; }}
QPushButton:pressed {{ background-color: #C4A1FF; color: #3C3C44; border: 1px solid #C4A1FF; }}
#btnHelp {{ background-color: transparent; border: 1px solid #8A8A95; color: #B0B0B8; border-radius: 11px; min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px; font-weight: bold; font-size: 9pt; }}
#btnHelp:hover {{ color: #C4A1FF; border-color: #C4A1FF; background-color: #555560; }}
#btnHelpHidden {{ background-color: transparent; border: none; min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px; }}
#btnExecute {{ background-color: #C4A1FF; color: #2B2B30; font-size: 11pt; font-weight: bold; padding: 10px 24px; border-radius: 6px; border: none; min-width: 200px; }}
#btnExecute:hover {{ background-color: #8C54FF; color: #FFFFFF; }}
#btnAdvancedLogs, #btnRestart {{ font-size: 9pt; font-weight: normal; padding: 4px 12px; border-radius: 4px; min-width: 110px; max-width: 110px; }}
#btnAdvancedLogs {{ background-color: transparent; border: 1px solid #555560; color: #B0B0B8; }}
#btnAdvancedLogs:checked {{ background-color: #C4A1FF; border-color: #C4A1FF; color: #2B2B30; font-weight: bold; }}
#btnAdvancedLogs:checked:hover {{ background-color: #8C54FF; border-color: #8C54FF; color: #FFFFFF; }}
#btnAdvancedLogs:hover:!checked {{ color: #FFFFFF; border-color: #8A8A95; }}
#btnRestart {{ background-color: transparent; border: 1px solid #EF5350; color: #EF5350; }}
#btnRestart:hover {{ background-color: #2F1C1C; color: #FF6B6B; border-color: #FF6B6B; }}
"""

STYLESHEET_LIGHT = f"""
QMainWindow, QDialog, QMessageBox {{ background-color: #F0F0F5; color: #1D1D1F; }}
QWidget {{ font-family: {BASE_FONT}; font-size: 10pt; }}
QLabel {{ color: #1D1D1F; }}
QMessageBox QLabel {{ color: #1D1D1F; background-color: transparent; }}
QFrame#Card {{ background-color: #FFFFFF; border-radius: 8px; border: 1px solid #D1D1D6; }}
QLabel#CardTitle {{ color: #000000; font-size: 13pt; font-weight: 700; padding-bottom: 0px; }}
QLabel#CardVersion {{ color: #8E8E93; font-size: 9pt; font-weight: 500; padding-bottom: 2px; }}
QLineEdit {{ background-color: #F9F9FB; border: 1px solid #D1D1D6; border-radius: 6px; padding: 6px 10px; color: #1D1D1F; font-size: 10pt; min-height: 20px; }}
QLineEdit:focus {{ border: 1px solid #8C54FF; background-color: #FFFFFF; }}
QPushButton {{ background-color: #E5E5EA; color: #1D1D1F; border-radius: 6px; padding: 6px 14px; font-weight: 600; border: 1px solid #D1D1D6; min-height: 20px; }}
QPushButton:hover {{ background-color: #D1D1D6; }}
QPushButton:pressed {{ background-color: #8C54FF; color: #FFFFFF; border: 1px solid #8C54FF; }}
#btnHelp {{ background-color: transparent; border: 1px solid #8E8E93; color: #8E8E93; border-radius: 11px; min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px; font-weight: bold; font-size: 9pt; }}
#btnHelp:hover {{ color: #8C54FF; border-color: #8C54FF; background-color: #F0F0F5; }}
#btnHelpHidden {{ background-color: transparent; border: none; min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px; }}
#btnExecute {{ background-color: #8C54FF; color: #FFFFFF; font-size: 11pt; font-weight: bold; padding: 10px 24px; border-radius: 6px; border: none; min-width: 200px; }}
#btnExecute:hover {{ background-color: #743DE5; }}
#btnAdvancedLogs, #btnRestart {{ font-size: 9pt; font-weight: normal; padding: 4px 12px; border-radius: 4px; min-width: 110px; max-width: 110px; }}
#btnAdvancedLogs {{ background-color: transparent; border: 1px solid #D1D1D6; color: #8E8E93; }}
#btnAdvancedLogs:checked {{ background-color: #E6D9FF; border-color: #8C54FF; color: #8C54FF; font-weight: bold; }}
#btnAdvancedLogs:checked:hover {{ background-color: #D1BBFF; }}
#btnAdvancedLogs:hover:!checked {{ color: #1D1D1F; border-color: #8E8E93; }}
#btnRestart {{ background-color: transparent; border: 1px solid #EF5350; color: #EF5350; }}
#btnRestart:hover {{ background-color: #FFEBEE; color: #D32F2F; border-color: #D32F2F; }}
"""

SVG_LOGO_DATA = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
    <rect width="128" height="128" rx="28" fill="#4A4A54"/>
    <path d="M64 22 C48 22, 36 34, 36 50 L36 60 L92 60 L92 50 C92 34, 80 22, 64 22 Z" fill="none" stroke="#C4A1FF" stroke-width="8" stroke-linejoin="round" stroke-linecap="round"/>
    <rect x="24" y="56" width="80" height="52" rx="12" fill="#32323A" stroke="#555560" stroke-width="4"/>
    <circle cx="64" cy="78" r="7" fill="#C4A1FF"/>
    <path d="M64 85 L64 96" stroke="#C4A1FF" stroke-width="5" stroke-linecap="round"/>
</svg>"""

def get_keys(keys_path, required_keys, logger=None):
    if logger:
        logger.log(f"[LOG] File Access: Opening key configuration payload file stream: {keys_path}")
        logger.log(f"[LOG] Registry Search Target Maps: [{', '.join(required_keys)}]")
    keys = {}
    try:
        with open(keys_path, 'r', encoding='utf-8', errors='ignore') as f:
            for idx, line in enumerate(f, 1):
                line = line.strip()
                if '=' in line:
                    k, v = line.split('=', 1)
                    k_str, v_str = k.strip(), v.strip()
                    if k_str in required_keys:
                        keys[k_str] = bytes.fromhex(v_str)
                        if logger: 
                            logger.log(f"[LOG] [Line {idx}] Cryptographic verification: Match discovered for target '{k_str}' -> Hex decoded size: {len(keys[k_str])} bytes.")
                        if len(keys) == len(required_keys):
                            if logger: 
                                logger.log("[LOG] Extraction status: Evaluation loop terminated early. All required key profiles matched.")
                            break
                    elif logger:
                        pass
    except Exception as e:
        raise RuntimeError(f"Failed to read keys file: {e}")
    return keys

def decrypt_prodinfo(encrypted_data, bis_key_00, logger=None):
    sector_size = 0x4000
    decrypted_data = bytearray()
    backend = default_backend()
    total_sectors = len(encrypted_data) // sector_size
    if logger:
        logger.log(f"[LOG] Main Task Sequence: Initiating AES-XTS memory decipher process. Buffer footprint size: {len(encrypted_data)} bytes.")
        logger.log(f"[LOG] Partition mapping structure configuration parameters -> Block size boundary: {hex(sector_size)}, Sectors calculated: {total_sectors}")

    for i in range(0, len(encrypted_data), sector_size):
        chunk = encrypted_data[i:i+sector_size]
        sector_idx = i // sector_size
        
        if len(chunk) < 16:
            if logger: 
                logger.log(f"[LOG] Processing Exception at index {sector_idx}: Block fragment length ({len(chunk)} bytes) below cipher baseline requirements. Transferring raw data fragment.")
            decrypted_data += chunk
            continue
            
        tweak = sector_idx.to_bytes(16, 'little')
        if logger: 
            logger.log(f"[LOG] Decryption cycle: Tracing processing block step {sector_idx}/{total_sectors} (Byte block index: {hex(i)}). Calculated tweak vector value: {tweak.hex().upper()}")
            
        cipher = Cipher(algorithms.AES(bis_key_00), modes.XTS(tweak), backend=backend)
        decryptor = cipher.decryptor()
        decrypted_data += decryptor.update(chunk)

    if logger: 
        logger.log("[LOG] Decryption cycle complete: Finalizing pipeline tasks and proceeding to structural file validation checks.")

    if decrypted_data[:4] != b"CAL0":
        if logger:
            logger.log(f"[LOG] Structural integrity error: Identification magic header 'CAL0' validation step failed. Byte footprint header read out as: {decrypted_data[:4]}")
        return None

    if logger: 
        logger.log(f"[LOG] Structural integrity verification success: Confirmed valid 'CAL0' file signature footprint inside decrypted structure.")
    return bytes(decrypted_data)

def recover_rsa_private_key(n, e, d, logger=None):
    if logger:
        logger.log("[LOG] Mathematical Execution Engine: Triggered factor recovery algorithm process from public parameters.")
        logger.log(f"[LOG] Target context values -> Modulus metric size: {n.bit_length()} bits, Public exponent factor e: {e}, Private exponent string size: {d.bit_length()} bits")
    
    k = d * e - 1
    t = 0
    r = k
    if logger: 
        logger.log(f"[LOG] Evaluation phase initialize: Factoring bit congruence tracking arrays for alignment equation k = d*e - 1. Calculated integer length: {k.bit_length()} bits.")
    
    while r % 2 == 0:
        t += 1
        r //= 2
    if logger: 
        logger.log(f"[LOG] Parity logic tracking parameters computed -> Shifting bit vector count t: {t}, Reduced odd remainder vector length r: {r.bit_length()} bits.")

    cracked = False
    for attempt in range(1, 101):
        g = random.randrange(2, n - 1)
        y = pow(g, r, n)
        if y == 1 or y == n - 1:
            continue

        for j in range(1, t):
            x = pow(y, 2, n)
            if x == 1:
                cracked = True
                if logger: 
                    logger.log(f"[LOG] Evaluation loop milestone: Splitting condition reached and validated at test depth level j: {j}.")
                break
            if x == n - 1:
                break
            y = x
            
        if cracked:
            if logger: 
                logger.log(f"[LOG] Mathematical Execution Engine status: Asymmetric key modular cracking sequence succeeded on execution index attempt count: {attempt}/100")
            break
            
    if not cracked:
        if logger: 
            logger.log("[LOG] Mathematical Execution Engine error: Internal check loops failed to establish algebraic factoring convergence boundaries.")
        raise RuntimeError("Mathematical factorization of the RSA key failed.")

    if logger: 
        logger.log("[LOG] Resolution tasks: Factoring modulus components via execution of the Euclid Greatest Common Divisor algorithm.")
    p = math.gcd(y - 1, n)
    q = n // p

    if p < q:
        p, q = q, p

    if logger:
        logger.log(f"[LOG] Extracted root factor parameter p size values resolved to: {p.bit_length()} bits")
        logger.log(f"[LOG] Extracted root factor parameter q size values resolved to: {q.bit_length()} bits")

    if logger: 
        logger.log("[LOG] Resolution tasks: Mapping Chinese Remainder Theorem exponents variables (dp, dq, iqmp multiplication factors).")
    dp = d % (p - 1)
    dq = d % (q - 1)
    iqmp = pow(q, -1, p)

    if logger: 
        logger.log("[LOG] Matrix construction: Instantiating structural RSA asymmetric class container instances inside cryptography runtime environment context.")
    public_numbers = rsa.RSAPublicNumbers(e, n)
    private_numbers = rsa.RSAPrivateNumbers(
        p=p, q=q, d=d, dmp1=dp, dmq1=dq, iqmp=iqmp, public_numbers=public_numbers
    )
    
    return private_numbers.private_key(default_backend())

def extract_and_build_pem(cal0_data, ssl_rsa_kek, logger=None):
    if logger: 
        logger.log("[LOG] Cryptographic Pipeline: Locating factory public credentials container structures in decrypted raw partition space mapping.")
        logger.log("[LOG] Memory transaction: Interrogating sector header size descriptors located at data address offset index 0x0AD0.")
    cert_size = struct.unpack("<I", cal0_data[0x0AD0:0x0AD4])[0]
    if logger: 
        logger.log(f"[LOG] Data address metrics decoded -> Found target certificate byte size constraint tracking property: {cert_size} bytes.")
    
    if cert_size == 0 or cert_size > 0x1000:
        if logger: 
            logger.log(f"[LOG] Extraction sequence aborted: Target block segment boundaries mismatch configuration requirements (Size parameter returned: {cert_size} bytes).")
        raise ValueError("Invalid certificate size. PRODINFO might be blank or wiped (e.g., Incognito).")
        
    if logger: 
        logger.log(f"[LOG] Memory transaction: Slicing binary structural scope range array fields [0x0AE0 : {hex(0x0AE0+cert_size)}] out from working data memory maps.")
    cert_data = cal0_data[0x0AE0:0x0AE0+cert_size]
    
    if logger: 
        logger.log("[LOG] Parser action: Decoding ASN.1 DER elements down into functional high-level X509 identity component structures.")
    cert = x509.load_der_x509_certificate(cert_data, default_backend())
    
    pub_numbers = cert.public_key().public_numbers()
    n = pub_numbers.n
    e = pub_numbers.e
    if logger: 
        logger.log("[LOG] Key registration: Extraction variables resolved successfully. Retrieved public structural properties Modulus N and Exponent E from certificate container.")
    
    if logger: 
        logger.log("[LOG] Cryptographic Pipeline: Isolating encrypted internal private key storage blocks starting at partition offset address 0x3AE0.")
    ssl_ext_key = cal0_data[0x3AE0:0x3AE0+0x110]
    iv = ssl_ext_key[:0x10]
    encrypted_d = ssl_ext_key[0x10:]
    
    if logger:
        logger.log(f"[LOG] Stream engine state initialization -> Extracted Initialization Vector block slice (IV): {iv.hex().upper()}")
        logger.log(f"[LOG] Stream engine state initialization -> Payload cipher block target sequence length: {len(encrypted_d)} bytes.")
        logger.log("[LOG] Decryption routine: Activating localized AES-128-CTR execution streams to isolate underlying private exponent parameter maps.")
        
    cipher = Cipher(algorithms.AES(ssl_rsa_kek), modes.CTR(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_d_bytes = decryptor.update(encrypted_d) + decryptor.finalize()
    if logger: 
        logger.log("[LOG] Decryption routine success: Stream engine complete. Passing parameters down into verification factor loops.")
    
    d = int.from_bytes(decrypted_d_bytes, 'big')
    private_key = recover_rsa_private_key(n, e, d, logger)
    
    if logger: 
        logger.log("[LOG] Serialization stage: Processing encoding conversion procedures for private parameters into PKCS#1 Traditional OpenSSL PEM formatted text blocks.")
    clean_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    if logger: 
        logger.log("[LOG] Serialization stage: Processing serialization procedures for public identity records into standard public certificate PEM formatted text blocks.")
    clean_cert = cert.public_bytes(serialization.Encoding.PEM)

    if logger: 
        logger.log("[LOG] Data formatting sequence: Concat-merging verified private parameters block strings directly onto public certificate asset tracking strings.")
    return clean_key + clean_cert

class TerminalLineRewriter:
    def __init__(self):
        self.last_state = None
        self.line_count = 0

    def log(self, text):
        print(text)
        self.line_count += 1

    def force_clear(self):
        if self.line_count > 0:
            for _ in range(self.line_count):
                sys.stdout.write('\x1b[1A\x1b[2K')
            self.line_count = 0
            sys.stdout.flush()

    def set_verbose_state(self, active):
        if self.last_state == active:
            return
            
        if active:
            self.force_clear()
            print("[LOG] Verbose mode activated. Initializing console logging systems.")
            self.line_count = 1
        else:
            self.force_clear()
            print("[LOG] Verbose mode deactivated.")
            self.line_count = 1
            
        sys.stdout.flush()
        self.last_state = active

class MainWindowProdToPEM(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NX-ProdToPEM (GUI)")
        self.setFixedSize(620, 310)
        
        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(SVG_LOGO_DATA))
        self.setWindowIcon(QIcon(pixmap))
        
        self.logger = TerminalLineRewriter()
        self.current_theme_dark = darkdetect.isDark()
        self.config_filename = "config-prodtopem.txt"
        self.config_allowed = True
        self.is_restarting = False
        self.startup_warning_accepted = False
        
        self.init_ui()
        self.load_configuration_file()
        
        self.prodinfo_le.textChanged.connect(self.save_configuration_file)
        self.keys_le.textChanged.connect(self.save_configuration_file)
        self.output_le.textChanged.connect(self.save_configuration_file)
        
        self.theme_timer = QTimer(self)
        self.theme_timer.timeout.connect(self.check_system_theme)
        self.theme_timer.start(1000)

        QTimer.singleShot(200, self.check_startup_warning)

    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        card_frame = QFrame(self)
        card_frame.setObjectName("Card")
        card_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        card_layout = QVBoxLayout(card_frame)
        card_layout.setContentsMargins(15, 12, 15, 12)
        card_layout.setSpacing(10)
        
        title_lbl = QLabel("NX-ProdToPEM GUI", self)
        title_lbl.setObjectName("CardTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_lbl)
        
        version_lbl = QLabel("v1.0.0", self)
        version_lbl.setObjectName("CardVersion")
        version_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(version_lbl)
        
        grid_container = QWidget(card_frame)
        grid_layout = QGridLayout(grid_container)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(12)
        
        prodinfo_lbl = QLabel("PRODINFO.bin path:", grid_container)
        prodinfo_lbl.setMinimumWidth(130)
        self.prodinfo_le = QLineEdit(grid_container)
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
        self.keys_le = QLineEdit(grid_container)
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
        self.output_le = QLineEdit(grid_container)
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
        main_layout.addWidget(card_frame)
        
        bottom_container = QWidget(central_widget)
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_restart = QPushButton("Restart App", bottom_container)
        self.btn_restart.setObjectName("btnRestart")
        self.btn_restart.clicked.connect(self.restart_application)
        
        self.btn_advanced = QPushButton("Advanced Logs", bottom_container)
        self.btn_advanced.setObjectName("btnAdvancedLogs")
        self.btn_advanced.setCheckable(True)
        self.btn_advanced.clicked.connect(self.toggle_advanced_logs)
        
        btn_execute = QPushButton("Generate certificat.pem", bottom_container)
        btn_execute.setObjectName("btnExecute")
        btn_execute.clicked.connect(self.process_conversion)
        
        bottom_layout.addWidget(self.btn_restart, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(btn_execute, 0, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.btn_advanced, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        main_layout.addWidget(bottom_container)

    def check_startup_warning(self):
        if not self.startup_warning_accepted:
            if self.btn_advanced.isChecked():
                self.logger.log("[LOG] Runtime Event: Verification sequence triggered. Showing root safety alert confirmation window to user context.")
            msg = (
                "Welcome!\n\nThis software is provided 'as-is'. In the event of any errors or console bans, "
                "the author declines all responsibility.\n\n"
                "This tool has been validated on an Erista Switch running system version 22.1.0, "
                "but any other Switch + OS is not 100% guaranteed to be OK.\nIf you have any doubts "
                "about anything, do not hesitate to discuss it with the author.\n\n"
                "ALSO:\n"
                "All files required by this tool must absolutely not be shared on the internet.\n\n"
                "This is extremely dangerous because anyone can get you banned.\nBe vigilant with "
                "what you do on the internet when you possess these files, and if you decide to send them "
                "(which is a very bad idea)."
            )
            QMessageBox.warning(self, "Hey. Disclaimer.", msg, QMessageBox.StandardButton.Ok)
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
            
            if not isinstance(data, dict):
                raise ValueError()

            self.prodinfo_le.setText(data.get("prodinfo_path", ""))
            self.keys_le.setText(data.get("keys_path", ""))
            self.output_le.setText(data.get("output_path", ""))
            
            advanced_state = data.get("advanced_logs", False)
            self.btn_advanced.setChecked(advanced_state)
            if advanced_state:
                self.logger.set_verbose_state(True)
                self.logger.log("[LOG] Configuration Sync: Persisted settings successfully extracted from configuration block maps.")
                self.logger.log(f"[LOG] Parameter mapped -> PRODINFO target: '{data.get('prodinfo_path')}'")
                self.logger.log(f"[LOG] Parameter mapped -> Cryptographic keys target: '{data.get('keys_path')}'")
                self.logger.log(f"[LOG] Parameter mapped -> Destination path target: '{data.get('output_path')}'")
                
            self.startup_warning_accepted = data.get("startup_warning_accepted", False)
                
            if data.get("version") != "1.0.0":
                QTimer.singleShot(100, lambda: QMessageBox.warning(self, "!", "The config-prodtopem.txt file has been updated."))
                self.save_configuration_file()
                
        except Exception:
            QTimer.singleShot(100, lambda: QMessageBox.warning(self, "Configuration Altered", "The configuration file appears to be altered or corrupted.\n\nIt has been skipped and will be reconstructed."))
            self.fallback_auto_detect()
            self.save_configuration_file()

    def save_configuration_file(self):
        is_verbose = self.btn_advanced.isChecked()
        if not self.config_allowed:
            if is_verbose: 
                self.logger.log("[LOG] Configuration Aborted: Persistence task halted. Storage permissions flag evaluates to disabled.")
            return

        cwd = os.getcwd()
        if not os.access(cwd, os.W_OK):
            self.config_allowed = False
            QMessageBox.warning(self, "Write Permission Denied", "The application has lost write permissions in this folder.\n\nYour application paths and settings will not be saved.")
            return

        try:
            data = {
                "version": "1.0.0",
                "prodinfo_path": self.prodinfo_le.text(),
                "keys_path": self.keys_le.text(),
                "output_path": self.output_le.text(),
                "advanced_logs": self.btn_advanced.isChecked(),
                "startup_warning_accepted": self.startup_warning_accepted
            }
            if is_verbose:
                self.logger.log(f"[LOG] System Write Action: Syncing active properties array down to json data fields container -> '{self.config_filename}'")
            with open(self.config_filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception:
            self.config_allowed = False
            QMessageBox.warning(self, "Saving Error", "An error occurred while saving the configuration settings.\n\nFuture changes will not be saved.")

    def fallback_auto_detect(self):
        is_verbose = self.btn_advanced.isChecked()
        if is_verbose: 
            self.logger.log("[LOG] Fallback event: Scanning path tree execution paths to resolve default local cryptographic components.")
        if os.path.exists("PRODINFO.bin"):
            self.prodinfo_le.setText(os.path.abspath("PRODINFO.bin"))
            if is_verbose: 
                self.logger.log(f"[LOG] Local discover mapping: Matched PRODINFO binary default tracking profile -> '{os.path.abspath('PRODINFO.bin')}'")
        if os.path.exists("prod.keys"):
            self.keys_le.setText(os.path.abspath("prod.keys"))
            if is_verbose: 
                self.logger.log(f"[LOG] Local discover mapping: Matched key configuration default tracking profile -> '{os.path.abspath('prod.keys')}'")
        self.output_le.setText("")

    def check_system_theme(self):
        is_dark = darkdetect.isDark()
        if is_dark != self.current_theme_dark:
            is_verbose = self.btn_advanced.isChecked()
            if is_verbose: 
                self.logger.log(f"[LOG] System Event context changed: Operating system interface theme adjustment detected. Setting application visual state IsDark value properties to: {is_dark}")
            self.current_theme_dark = is_dark
            QApplication.instance().setStyleSheet(STYLESHEET_DARK if is_dark else STYLESHEET_LIGHT)

    def browse_prodinfo(self):
        is_verbose = self.btn_advanced.isChecked()
        if is_verbose: 
            self.logger.log("[LOG] UI Action Event: Launching system file interface window module for PRODINFO search paths targeting.")
        filepath, _ = QFileDialog.getOpenFileName(self, "Select PRODINFO.bin", "", "Binary files (*.bin);;All files (*.*)")
        if filepath:
            if is_verbose: 
                self.logger.log(f"[LOG] Workspace selection updated: File exploration routine target captured -> '{filepath}'")
            filename = os.path.basename(filepath)
            if filename.lower() != "prodinfo.bin":
                if is_verbose: 
                    self.logger.log(f"[LOG] Operational Warning: Selected profile filename variance found ('{filename}' used instead of expected static 'PRODINFO.bin'). Triggering validation prompts.")
                msg = f"The selected file is named '{filename}' instead of 'PRODINFO.bin'.\n\nWould you like to select a different file?"
                box = QMessageBox(QMessageBox.Icon.Question, "Unexpected Filename", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
                if box.exec() == QMessageBox.StandardButton.Yes:
                    self.browse_prodinfo()
                    return
            self.prodinfo_le.setText(filepath)
        elif is_verbose:
            self.logger.log("[LOG] Workspace selection cancelled: User dismissed system exploration explorer dialog module without confirming path target modifications.")

    def browse_keys(self):
        is_verbose = self.btn_advanced.isChecked()
        if is_verbose: 
            self.logger.log("[LOG] UI Action Event: Launching system file interface window module for core cryptographic key files search paths targeting.")
        filepath, _ = QFileDialog.getOpenFileName(self, "Select prod.keys", "", "Key files (*.keys);;Text files (*.txt);;All files (*.*)")
        if filepath:
            if is_verbose: 
                self.logger.log(f"[LOG] Workspace selection updated: Key profile tracking file target captured -> '{filepath}'")
            filename = os.path.basename(filepath)
            if filename.lower() != "prod.keys":
                if is_verbose: 
                    self.logger.log(f"[LOG] Operational Warning: Selected profile filename variance found ('{filename}' used instead of expected static 'prod.keys'). Triggering validation prompts.")
                msg = f"The selected file is named '{filename}' instead of 'prod.keys'.\n\nWould you like to select a different file?"
                box = QMessageBox(QMessageBox.Icon.Question, "Unexpected Filename", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
                if box.exec() == QMessageBox.StandardButton.Yes:
                    self.browse_keys()
                    return
            self.keys_le.setText(filepath)
        elif is_verbose:
            self.logger.log("[LOG] Workspace selection cancelled: User dismissed system exploration explorer dialog module without confirming key configuration target modifications.")

    def browse_output(self):
        is_verbose = self.btn_advanced.isChecked()
        if is_verbose: 
            self.logger.log("[LOG] UI Action Event: Launching operating system directory mapping tree module selector for destination formatting paths targeting.")
        dirpath = QFileDialog.getExistingDirectory(self, "Select Destination Folder", "")
        if dirpath:
            if is_verbose: 
                self.logger.log(f"[LOG] Workspace selection updated: Output target folder location parameter assigned -> '{dirpath}'")
            self.output_le.setText(dirpath)
        elif is_verbose:
            self.logger.log("[LOG] Workspace selection cancelled: User dismissed target selection modules without updating folder path property parameters.")

    def toggle_advanced_logs(self):
        self.logger.set_verbose_state(self.btn_advanced.isChecked())
        self.save_configuration_file()

    def restart_application(self):
        if self.btn_advanced.isChecked():
            self.logger.log("[LOG] UI Interaction trace: User command received to trigger sub-process teardown and master program restart sequence.")
        msg = "Are you sure you want to completely restart the application?"
        box = QMessageBox(QMessageBox.Icon.Question, "Confirm Restart", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.is_restarting = True
            self.logger.force_clear()
            sys.stdout.flush()
            QApplication.quit()

    def show_help_prodinfo(self):
        if self.btn_advanced.isChecked():
            self.logger.log("[LOG] User Interaction: Triggered help documentation for PRODINFO extraction.")
        
        msg = (
            "How to get your PRODINFO.bin:\n\n"
            "You do not need to perform a full eMMC dump.\n"
            "1. Open the Hekate bootloader menu.\n"
            "2. Select the tool to dump your console's partitions\n(choose \"eMMC SYS\", not \"eMMC RAW GPP\").\n\n"
            "This method is much faster than a full dump. Once finished, you will find your file here:\n"
            "SD:/backup/xxxxxxxx/partitions/PRODINFO.bin\n\n"
            "(Note: 'xxxxxxxx' is a placeholder that will vary based on your console's unique ID.)"
        )
        box = QMessageBox(QMessageBox.Icon.Information, "PRODINFO.bin?", msg, QMessageBox.StandardButton.Ok, self)
        box.exec()

    def show_help_keys(self):
        if self.btn_advanced.isChecked():
            self.logger.log("[LOG] User Interaction: Triggered documentation frame dialog box context for prod.keys verification metrics.")
        msg = (
            "How to get your prod.keys:\n\n"
            "Your prod.keys file must contain at least the 'bis_key_00' and 'ssl_rsa_kek' keys.\n\n"
            "To download a well-maintained version of Lockpick_RCM (at the time of writing) that supports the latest console system updates, you can use this repository:\n\n"
            "https://github.com/THZoria/Lockpick_RCMasternn"
            "Once the keys are dumped, you will find them here:\n"
            "SD:/switch/prod.keys\n\n"
            "Would you like to open this link in your web browser now?"
        )
        box = QMessageBox(QMessageBox.Icon.Question, "prod.keys?", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
        reply = box.exec()
        if reply == QMessageBox.StandardButton.Yes:
            if self.btn_advanced.isChecked():
                self.logger.log("[LOG] Web Browser Interface: Directing client socket request routing towards repository endpoint -> THZoria/Lockpick_RCMaster")
            webbrowser.open("https://github.com/THZoria/Lockpick_RCMaster")

    def process_conversion(self):
        self.save_configuration_file()
        p_path = self.prodinfo_le.text()
        k_path = self.keys_le.text()
        out_dir = self.output_le.text()
        is_verbose = self.btn_advanced.isChecked()

        if is_verbose:
            self.logger.log("[LOG] Conversion Task: Initializing data decryption and parsing verification sequences.")
            self.logger.log(f"[LOG] Mapping target validation checkpoints -> Source path target: '{p_path}'")
            self.logger.log(f"[LOG] Mapping target validation checkpoints -> Keys definition tracking file: '{k_path}'")
            self.logger.log(f"[LOG] Mapping target validation checkpoints -> Destination production output path: '{out_dir}'")

        if not p_path or not os.path.exists(p_path):
            if is_verbose:
                self.logger.log("[LOG] Conversion validation failure: Explicit target file pointer location for PRODINFO structure resolves to null value or file is completely missing on disk sectors.")
            QMessageBox.critical(self, "File Missing", "The selected PRODINFO.bin file could not be found.")
            return
        if not k_path or not os.path.exists(k_path):
            if is_verbose:
                self.logger.log("[LOG] Conversion validation failure: Explicit target file pointer location for cryptographic key properties resolves to null value or file is completely missing on disk sectors.")
            QMessageBox.critical(self, "File Missing", "The selected prod.keys file could not be found.")
            return

        if not out_dir.strip():
            out_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
            if is_verbose:
                self.logger.log(f"[LOG] Parsing runtime environment metrics: Optional output folder text field evaluates empty. Setting directory defaults context mapping directly to: {out_dir}")

        if not os.path.exists(out_dir) or not os.access(out_dir, os.W_OK):
            if is_verbose:
                self.logger.log(f"[LOG] Storage I/O check validation: Destination folder path properties mapping '{out_dir}' missing disk execution layer write authorization contexts, or folder is missing.")
            QMessageBox.warning(self, "Permission Denied", "The destination folder is invalid or missing write permissions.\nPlease select an alternative folder.")
            alternative_dir = QFileDialog.getExistingDirectory(self, "Select Authorized Destination Folder", "")
            if alternative_dir:
                out_dir = alternative_dir
                self.output_le.setText(out_dir)
                self.save_configuration_file()
            else:
                if is_verbose: 
                    self.logger.log("[LOG] Conversion state cancelled: Terminating active conversion processing pipeline because destination directory configurations are invalid.")
                return

        pem_output = os.path.join(out_dir, "certificat.pem")
        if is_verbose: 
            self.logger.log(f"[LOG] Verification routing target: Final output identity credentials asset destination set to path layout -> '{pem_output}'")
        
        if os.path.exists(pem_output):
            if is_verbose:
                self.logger.log(f"[LOG] Dynamic file block conflict: Asset collision match discovered at target location path: '{pem_output}'. Prompting user choice variables for file replacement action.")
            overwrite_msg = "A 'certificat.pem' file already exists in the selected destination folder.\n\nDo you want to overwrite it?"
            confirm_box = QMessageBox(QMessageBox.Icon.Warning, "File Conflict", overwrite_msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
            if confirm_box.exec() != QMessageBox.StandardButton.Yes:
                if is_verbose: 
                    self.logger.log("[LOG] Conversion execution status: File generation sequence stopped by user command because of file replace conflict.")
                return

        try:
            if is_verbose: 
                self.logger.log(f"[LOG] Storage I/O operations: Opening target partition backup file context reading streams securely: '{p_path}'")
            with open(p_path, 'rb') as f:
                raw_prodinfo_data = f.read()
            if is_verbose: 
                self.logger.log(f"[LOG] Storage I/O operations: Memory read transaction completed. Stored raw partition byte size into working memory cache size maps: {len(raw_prodinfo_data)} total bytes.")

            is_cal0_clear = (raw_prodinfo_data[:4] == b"CAL0")
            required_keys = {'ssl_rsa_kek'}
            
            if is_cal0_clear:
                if is_verbose: 
                    self.logger.log("[LOG] Stream evaluation discovery: Verified decrypted cleartext signature block structure parameters ('CAL0' sequence block header visible). Skipping lower-level block deciphering steps.")
                decrypted_data = raw_prodinfo_data
            else:
                if is_verbose: 
                    self.logger.log("[LOG] Stream evaluation discovery: Encrypted device calibration block format identified. Injecting sector layer cryptographic master identification key string requirements 'bis_key_00' into extraction registers.")
                required_keys.add('bis_key_00')

            if is_verbose: 
                self.logger.log("[LOG] Registry processing: Handing key data compilation processing tasks down into target collection dictionary routines.")
            keys = get_keys(k_path, required_keys, self.logger if is_verbose else None)
            ssl_rsa_kek = keys.get('ssl_rsa_kek')
            if not ssl_rsa_kek:
                raise ValueError("The encryption key 'ssl_rsa_kek' is missing from your prod.keys file.")

            if not is_cal0_clear:
                bis_key_00 = keys.get('bis_key_00')
                if not bis_key_00:
                    raise ValueError("The encryption key 'bis_key_00' is missing from your prod.keys file.")
                if is_verbose: 
                    self.logger.log("[LOG] Decryption execution module: Calling hardware partition decipher algorithms to unpack partition blocks framework layout layer structures.")
                decrypted_data = decrypt_prodinfo(raw_prodinfo_data, bis_key_00, self.logger if is_verbose else None)
                
                if not decrypted_data:
                    error_msg = (
                        "Failed to decrypt PRODINFO. Invalid file or bad 'bis_key_00'.\n\n"
                        "TROUBLESHOOTING:\n"
                        "If you are sure both files belong to the EXACT SAME console, this error should not happen.\n"
                        "- Verify that you used the latest up-to-date Lockpick_RCM payload.\n"
                        "- Ensure no errors occurred during the key extraction process.\n\n"
                        "If the problem persists and you are absolutely sure your files are valid:\n"
                        "DO NOT share your PRODINFO or prod.keys online.\n"
                        "Please open an issue on GitHub so the author can investigate:\n\n"
                        "https://github.com/JeremKOYTB/NX-ProdToPEM/issues"
                    )
                    raise ValueError(error_msg)
                
            if is_verbose: 
                self.logger.log("[LOG] Transformation stage: Routing decrypted data block matrices directly down through asymmetric factorization and public device token extraction logic steps.")
            unified_pem = extract_and_build_pem(decrypted_data, ssl_rsa_kek, self.logger if is_verbose else None)
            
            if is_verbose: 
                self.logger.log(f"[LOG] Production output transaction: Opening file write stream directly targeting destination mapping properties tree location index path -> '{pem_output}'")
            with open(pem_output, "wb") as f_out:
                f_out.write(unified_pem)
            if is_verbose: 
                self.logger.log(f"[LOG] Production output transaction: Stream operation closed successfully. Committed payload size output maps directly onto storage sectors: {len(unified_pem)} total text string characters bytes format records.")
                
            success_msg = (
                "The certificat.pem file has been successfully extracted and saved!\n\n"
                "⚠️ CRITICAL SECURITY WARNING:\n"
                "NEVER share or give this file to anyone under any circumstances! This file contains your unique device private keys. "
                "Be extremely careful with what you do with it.\n\n"
                "You can now use this certificate wherever you want, such as in TriCoreDownloader:\n\n"
                "https://github.com/JeremKOYTB/TriCoreDownloadernn"
                "Would you like to open the project repository link now?"
            )
            
            box = QMessageBox(QMessageBox.Icon.Information, "Extraction Successful", success_msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
            if box.exec() == QMessageBox.StandardButton.Yes:
                if is_verbose: 
                    self.logger.log("[LOG] External System Call: Initializing socket interface request tracking loops to redirect workspace defaults web routing parameters towards downstream project target repositories.")
                webbrowser.open("https://github.com/JeremKOYTB/TriCoreDownloader")

        except Exception as e:
            if is_verbose: 
                self.logger.log(f"[LOG] Critical Process Exception: Active conversion operation routine crashed during validation loop calculations. Exception stack log error output reports: {str(e)}")
            error_box = QMessageBox(QMessageBox.Icon.Critical, "Error", f"An issue occurred while converting your files:\n\n{str(e)}\n\nWould you like to open the issue tracker link to report this error?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
            error_box.setDefaultButton(QMessageBox.StandardButton.No)
            if error_box.exec() == QMessageBox.StandardButton.Yes:
                webbrowser.open("https://github.com/JeremKOYTB/NX-ProdToPEM/issues/new")

def handle_interrupt(window_instance):
    if window_instance.btn_advanced.isChecked():
        window_instance.logger.log("[LOG] Runtime Event: SIGINT context capture loop caught terminal user command request to break execution boundaries via keyboard input event shortcut.")
    msg = "Ctrl+C was detected in the terminal.\n\nDo you want to close?"
    box = QMessageBox(QMessageBox.Icon.Question, "Exit?", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, window_instance)
    box.setDefaultButton(QMessageBox.StandardButton.No)
    box.setWindowFlags(box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
    
    if box.exec() == QMessageBox.StandardButton.Yes:
        window_instance.logger.force_clear()
        QApplication.quit()
        sys.exit(0)

if __name__ == "__main__":
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("JeremKOYTB.NXProdToPEM.Gui.1.0.0")

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET_DARK if darkdetect.isDark() else STYLESHEET_LIGHT)
        
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