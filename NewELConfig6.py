#     15 Nov 2024 -- updated to ELSentry v2.0a beta


# After testing with various EncryptMeX modules, further testing
#
# v. 10b slightly obfuscating the key file to ElkeSummer.dat
# # Adding function access into common (common2)
#
# v 11a adds the ability to store the various passwords with the key
# for ease of use in testing, default values have been added.
# We expect that each separate EchoLeaf install will have this crypts.dat preservered somewhere.

# 
#    "database": "EchoLeaf", The name of the database in MySQL
#    "sysadminpassword": The encrypted password for the UI
#    "sysadmin": "demo", The unencrypted username for the UI
#    "host": "192.168.1.30",
#    "user": "echoleafaccess", Unencrypted Username for MySQL
#     "password": The encrypted password for MySQL
#
#    NewELConfig6.py  == add specific ip address

import json
#from common2 import load_key, encryptIT
from common import load_key, encryptIT

def create_config():
    """Creates the JSON configuration with encrypted passwords and stores additional details in crypts.dat."""
    key = load_key()
    sysadmin_password = input("Enter UI Password (default: demo): ") or "demo"
    encrypted_sysadmin_password = encryptIT(sysadmin_password, key)

    password = input("Enter Mysql Password (default: EchoLeaf1!): ") or "EchoLeaf1!"
    encrypted_password = encryptIT(password, key)
    
    ipaddress = input("Enter IP Host address (default: 127.0.0.1): ") or "127.0.0.1"

# Note. In this version explicit values cannot be overwritten
    config = {
        "database": "EchoLeaf",        # MySQL DB Name
        "sysadminpassword": encrypted_sysadmin_password,  # UI Password
        "sysadmin": "demo",   # UI Username (will be checked)
        "host": ipaddress, # Explicit host name
        "user": "echoleafaccess",  # MySQL user name
        "password": encrypted_password #MySQL password
    }

    # Load or create crypts.dat with error handling
    try:
        with open("crypts.dat", "r") as crypts_file:
            crypts_data = json.load(crypts_file)
    except FileNotFoundError:
        crypts_data = {}
    except json.decoder.JSONDecodeError as e:
        print(f"Error decoding crypts.dat: {e}")
        crypts_data = {} 

    # Add sysadmin_password details (store encrypted data as bytes)
    crypts_data["sysadmin_password"] = {
        "original_passphrase": encrypted_sysadmin_password.encode('utf-8'), 
        "decrypted_passphrase": sysadmin_password,
        "modified_passphrase": sysadmin_password + "_key",
        "passphrase_and_key": {
            sysadmin_password + "_key": key 
        }
    }

    # Add password details (store encrypted data as bytes)
    crypts_data["password"] = {
        "original_passphrase": encrypted_password.encode('utf-8'), 
        "decrypted_passphrase": password,
        "modified_passphrase": password + "_key",
        "passphrase_and_key": {
            password + "_key": key
        }
    }

    # Save updated crypts.dat (use bytes for encrypted data)
    with open("crypts.dat", "w") as crypts_file:
        json.dump(crypts_data, crypts_file, indent=4, default=lambda o: o.decode('utf-8') if isinstance(o, bytes) else o)

    # Save EL.config2.json as before
    with open("EL.config2.json", "w") as config_file:
        json.dump(config, config_file, indent=4)

if __name__ == "__main__":
    create_config()
