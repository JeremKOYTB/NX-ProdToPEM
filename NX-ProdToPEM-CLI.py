import argparse
import os
import sys
import struct
import math
import random
import subprocess
import importlib.util

def ensure_dependencies():
    if importlib.util.find_spec("cryptography") is None:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"], 
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print("[-] Error: Auto-installation failed. Please run: pip install cryptography")
            sys.exit(1)

ensure_dependencies()

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# --- CORE LOGIC ---

def log_msg(message, is_verbose):
    if is_verbose:
        print(message)

def get_keys(keys_path, required_keys, is_verbose=False):
    log_msg(f"[LOG] Opening keys file: {keys_path}", is_verbose)
    log_msg(f"[LOG] Target keys to find: {', '.join(required_keys)}", is_verbose)
    keys = {}
    try:
        with open(keys_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    k, v = line.split('=', 1)
                    k_str, v_str = k.strip(), v.strip()
                    
                    if k_str in required_keys:
                        keys[k_str] = bytes.fromhex(v_str)
                        log_msg(f"[LOG] Found required key: '{k_str}'", is_verbose)
                        
                        if len(keys) == len(required_keys):
                            log_msg("[LOG] All required keys found. Stopping file parsing early.", is_verbose)
                            break
    except Exception as e:
        raise RuntimeError(f"Failed to read keys file: {e}")
    return keys

def decrypt_prodinfo(encrypted_data, bis_key_00, is_verbose=False):
    sector_size = 0x4000
    decrypted_data = bytearray()
    backend = default_backend()
    total_sectors = len(encrypted_data) // sector_size
    log_msg(f"[LOG] Starting AES-XTS decryption (Sector size: {hex(sector_size)}, Total sectors: {total_sectors})", is_verbose)

    for i in range(0, len(encrypted_data), sector_size):
        chunk = encrypted_data[i:i+sector_size]
        if len(chunk) < 16:
            decrypted_data += chunk
            continue
            
        sector_idx = i // sector_size
        tweak = sector_idx.to_bytes(16, 'little')
        if sector_idx % 2 == 0:
            log_msg(f"[LOG] Decrypting sector {sector_idx}/{total_sectors}...", is_verbose)
            
        cipher = Cipher(algorithms.AES(bis_key_00), modes.XTS(tweak), backend=backend)
        decryptor = cipher.decryptor()
        decrypted_data += decryptor.update(chunk)

    if decrypted_data[:4] != b"CAL0":
        log_msg(f"[LOG] Decryption failed. Missing CAL0 magic header (Got: {decrypted_data[:4]})", is_verbose)
        return None

    return bytes(decrypted_data)

def recover_rsa_private_key(n, e, d, is_verbose=False):
    log_msg("[LOG] Starting RSA private key recovery from public parameters...", is_verbose)
    log_msg(f"[LOG] RSA Parameters: Modulus ({n.bit_length()} bits), Exponent e ({e}), Exponent d ({d.bit_length()} bits)", is_verbose)
    
    k = d * e - 1
    t = 0
    r = k
    
    while r % 2 == 0:
        t += 1
        r //= 2

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
                break
            if x == n - 1:
                break
            y = x
            
        if cracked:
            log_msg(f"[LOG] RSA factorization successful on attempt {attempt}/100", is_verbose)
            break
            
    if not cracked:
        raise RuntimeError("Mathematical factorization of the RSA key failed.")

    p = math.gcd(y - 1, n)
    q = n // p

    if p < q:
        p, q = q, p

    log_msg(f"[LOG] Recovered prime factor p ({p.bit_length()} bits)", is_verbose)
    log_msg(f"[LOG] Recovered prime factor q ({q.bit_length()} bits)", is_verbose)

    dp = d % (p - 1)
    dq = d % (q - 1)
    iqmp = pow(q, -1, p)

    public_numbers = rsa.RSAPublicNumbers(e, n)
    private_numbers = rsa.RSAPrivateNumbers(
        p=p, q=q, d=d, dmp1=dp, dmq1=dq, iqmp=iqmp, public_numbers=public_numbers
    )
    
    return private_numbers.private_key(default_backend())

def extract_and_build_pem(cal0_data, ssl_rsa_kek, is_verbose=False):
    log_msg("[LOG] Reading public certificate at offset 0x0AD0", is_verbose)
    cert_size = struct.unpack("<I", cal0_data[0x0AD0:0x0AD4])[0]
    log_msg(f"[LOG] Certificate size: {cert_size} bytes", is_verbose)
    
    if cert_size == 0 or cert_size > 0x1000:
        raise ValueError("Invalid certificate size. PRODINFO might be blank or wiped (e.g., Incognito).")
        
    cert_data = cal0_data[0x0AE0:0x0AE0+cert_size]
    cert = x509.load_der_x509_certificate(cert_data, default_backend())
    
    pub_numbers = cert.public_key().public_numbers()
    n = pub_numbers.n
    e = pub_numbers.e
    
    log_msg("[LOG] Reading encrypted RSA private key block at offset 0x3AE0", is_verbose)
    ssl_ext_key = cal0_data[0x3AE0:0x3AE0+0x110]
    iv = ssl_ext_key[:0x10]
    encrypted_d = ssl_ext_key[0x10:]
    
    log_msg(f"[LOG] Initialization Vector (IV): {iv.hex().upper()}", is_verbose)
    log_msg("[LOG] Decrypting RSA private exponent (AES-128-CTR)...", is_verbose)
    
    cipher = Cipher(algorithms.AES(ssl_rsa_kek), modes.CTR(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_d_bytes = decryptor.update(encrypted_d) + decryptor.finalize()
    
    d = int.from_bytes(decrypted_d_bytes, 'big')
    private_key = recover_rsa_private_key(n, e, d, is_verbose)
    
    log_msg("[LOG] Building final PEM certificate...", is_verbose)
    clean_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    clean_cert = cert.public_bytes(serialization.Encoding.PEM)

    return clean_key + clean_cert

# --- MAIN CLI INTERFACE ---

def main():
    parser = argparse.ArgumentParser(
        description="NX-ProdToPEM-CLI [v1.0.0]",
        epilog=(
            "USAGE EXAMPLES:\n"
            "  Standard extraction:  python NX-ProdToPEM-CLI.py -p PRODINFO.bin -k prod.keys\n"
            "  Verbose diagnostics:  python NX-ProdToPEM-CLI.py -p PRODINFO.bin -k prod.keys --logs"
        ),
        add_help=False,
        formatter_class=argparse.RawTextHelpFormatter
    )

    group_req = parser.add_argument_group('MANDATORY PARAMETERS')
    group_req.add_argument('-p', '--prodinfo', metavar='<FILE>', type=str, help="Target PRODINFO.bin partition file")
    group_req.add_argument('-k', '--keys', metavar='<FILE>', type=str, help="Target prod.keys cryptographic configuration")

    group_opt = parser.add_argument_group('OPTIONAL PARAMETERS')
    group_opt.add_argument('-o', '--output', metavar='<PATH>', type=str, default="certificat.pem", 
                           help="Destination file path for the extracted PEM\n(Default: ./certificat.pem)")
    group_opt.add_argument('-l', '--logs', action='store_true', help="Enable detailed logs")
    group_opt.add_argument('-h', '--help', action='help', help="Display this help message and exit")

    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    args = parser.parse_args()
    is_verbose = args.logs
    missing_files = False

    if is_verbose:
        print("[LOG] Verbose mode enabled.")
        log_msg(f"[LOG] Configuration -> PRODINFO: '{args.prodinfo}', Keys: '{args.keys}', Output: '{args.output}'", True)

    if not args.prodinfo:
        print("[-] Error: The mandatory -p (or --prodinfo) parameter is missing.")
        missing_files = True
    elif not os.path.exists(args.prodinfo):
        print(f"[-] Error: PRODINFO.bin could not be found at the path: {os.path.abspath(args.prodinfo)}")
        missing_files = True

    if not args.keys:
        print("[-] Error: The mandatory -k (or --keys) parameter is missing.")
        missing_files = True
    elif not os.path.exists(args.keys):
        print(f"[-] Error: prod.keys could not be found at the path: {os.path.abspath(args.keys)}")
        missing_files = True

    if missing_files:
        print("\n[-] Initialization aborted. Please check your arguments.")
        return 1

    try:
        print("[+] Inspecting PRODINFO payload...")
        with open(args.prodinfo, 'rb') as f:
            raw_prodinfo_data = f.read()

        is_cal0_clear = (raw_prodinfo_data[:4] == b"CAL0")
        required_keys = {'ssl_rsa_kek'}
        
        if is_cal0_clear:
            print("[+] Unencrypted CAL0 detected. Skipping partition decryption.")
            decrypted_data = raw_prodinfo_data
        else:
            print("[+] Encrypted partition detected. Proceeding with decryption.")
            required_keys.add('bis_key_00')

        print("[+] Parsing keyset...")
        keys = get_keys(args.keys, required_keys, is_verbose)
        
        ssl_rsa_kek = keys.get('ssl_rsa_kek')
        if not ssl_rsa_kek:
            print("[-] Error: 'ssl_rsa_kek' not found in prod.keys. This is needed for the RSA decryption.")
            return 1

        if not is_cal0_clear:
            bis_key_00 = keys.get('bis_key_00')
            if not bis_key_00:
                print("[-] Error: 'bis_key_00' not found in prod.keys. This is required to decrypt the partition.")
                return 1
                
            print("[+] Decrypting PRODINFO partition...")
            decrypted_data = decrypt_prodinfo(raw_prodinfo_data, bis_key_00, is_verbose)
            
            if not decrypted_data:
                print("[-] Error: Failed to decrypt PRODINFO. Invalid file or bad 'bis_key_00'.")
                print("\n[!] TROUBLESHOOTING:")
                print("    If both files belong to the same console, this error shouldn't happen.")
                print("    - Verify that you used the latest Lockpick_RCM payload.")
                print("    - Ensure no errors occurred during the key extraction process.")
                print("\n    If the problem persists:")
                print("    Please do not share your PRODINFO or prod.keys online.")
                print("    Please open an issue on GitHub so the author can investigate:")
                print("    https://github.com/JeremKOYTB/NX-ProdToPEM/issues")
                return 1
            print("[+] Magic CAL0 verified.")
            
        print("[+] Extracting RSA parameters...")
        unified_pem = extract_and_build_pem(decrypted_data, ssl_rsa_kek, is_verbose)
        
        log_msg(f"[LOG] Saving PEM file to: {args.output}", is_verbose)
        with open(args.output, "wb") as f_out:
            f_out.write(unified_pem)
            
        log_msg("[LOG] Process completed successfully.", is_verbose)
        print("[+] Success: Client certificate generated successfully.")
        print(f"[+] Output: {os.path.abspath(args.output)}")
        return 0
        
    except Exception as e:
        log_msg(f"[LOG] Error encountered during extraction: {str(e)}", is_verbose)
        print(f"[-] Extraction error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = 0
    try:
        exit_code = main() or 0
    except KeyboardInterrupt:
        print("\n[-] Operation cancelled by user.")
        exit_code = 1
    except SystemExit as e:
        exit_code = e.code if isinstance(e.code, int) else 1
    except Exception as e:
        print(f"\n[-] Critical runtime error: {e}")
        exit_code = 1
    
    print()
    input("Press Enter to exit...")
    sys.exit(exit_code)
