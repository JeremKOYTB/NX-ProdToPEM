# NX-ProdToPEM (CLI + GUI Version)

A utility designed to decrypt PRODINFO.bin and generate a valid certificat.pem for SSL/TLS authentication.

<p align="center">
  <img src="https://github.com/user-attachments/assets/e6854955-1195-423f-ae7c-4551416c26b6" width="200" alt="ProdToPEM" />
</p>

And you can use it, for example, for my [TriCoreDownloader](https://github.com/JeremKOYTB/TriCoreDownloader) :)

* Base Concept: This project is built upon the foundation provided by [NxCertDump](https://github.com/shadowninja108/NxCertDump).
Big thanks to the original authors for the initial research on the CAL0/PRODINFO structure.

> Tested Environment: Validated on an Erista Switch running firmware 22.1.0. Compatibility with other models (V2, Lite, OLED) or different firmware versions is not 100% guaranteed.

## ⚠️ Critical Security & Legal Disclaimer

* As-Is Software: This tool is provided "as-is" for research and educational purposes only. The author declines all responsibility for any errors, console bans, or restrictions resulting from its use.
* Sensitive Data: Your PRODINFO.bin, prod.keys, and the resulting certificat.pem contain unique, device-specific credentials. NEVER share these files online. Sharing them is extremely dangerous and can lead to permanent console bans.
* Vigilance: Be ultra-vigilant with what you do on the internet when you possess these files. Sending them to untrusted parties is a very bad idea.

---

## Features

* Dual Mode: Use the intuitive GUI for standard tasks or the CLI for direct script interaction.
* Advanced Logging: Toggleable verbose mode to track every cryptographic and file system operation in real-time.
* Persistent Configuration: Automatically saves your paths and settings in config-prodtopem.txt.
* Automated Dependencies: Built-in checks to ensure all required Python libraries are installed.

---

## Prerequisites

1. PRODINFO.bin: Your console's unique calibration partition.
2. prod.keys: A keyset file containing:
    * bis_key_00 (for PRODINFO decryption)
    * ssl_rsa_kek (for RSA parameter decryption)

---

## Installation

This script requires PyQt6, cryptography, and darkdetect. It will attempt to install the necessary libraries automatically upon the first launch.

Alternatively, you can install them manually:

pip install PyQt6 cryptography darkdetect

---

## Usage

### GUI Mode
1. Launch the application:
   python NX-ProdToPEM-GUI.py
2. Select your PRODINFO.bin and prod.keys via the interface.
3. (Optional) Choose a destination folder for the output file.
4. Click "Generate certificat.pem".

### CLI Mode
You can run the script directly from your terminal to utilize the same processing logic:
python NX-ProdToPEM-CLI.py --help

---

## How it works

1. Decryption: Uses AES-128-XTS to decrypt the PRODINFO.bin using bis_key_00.
2. Extraction: Parses the CAL0 partition to extract the DER-encoded public certificate and the encrypted RSA private exponent.
3. Factorization: Performs probabilistic prime factorization to recover the full RSA private key from the public modulus.
4. PEM Construction: Assembles the private key and public certificate into a unified PEM file.

---

## About the project

* AI Assistance: This tool has been highly optimized with the assistance of AI for cryptographic performance, GUI implementation, and logical structure.
* Contributing: This project is open-source and collaborative. If you notice any "odd" logic, non-idiomatic Python patterns, or potential improvements, please feel free to:
    * Open an Issue: If you find a bug or have a suggestion.
    * Submit a Pull Request: If you have a fix or an optimization to propose.

Your contributions to make this code more robust, efficient, and maintainable are highly appreciated!

## License

This project is licensed under the MIT License.
