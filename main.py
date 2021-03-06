from netmiko import ConnectHandler
import telnetlib
import argparse
import logging
import getpass
import yaml
import os
import ipaddress

def get_platform_by_hostname(hostname):
    dtype = hostname.split('-')[0]
    if dtype == "mx":
        return "juniper_junos"
    elif dtype == "swe":
        return "extreme_exos"
    elif dtype == "sw":
        return "cisco_ios"
    elif dtype == "mt":
        return "mikrotik_routeros"
    else:
        return "mikrotik_routeros"

def get_full_hostname(dev, def_domain):
    try:
        addr = ipaddress.ip_address(dev)
        logging.info(f"{dev} is an ip address")
        return dev
    except ValueError:
        logging.info(f"{dev} is a hostname")
        return dev + def_domain

# logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    '''
    This script is designed to exec multiple cmds on several network devices described in YAML file
    First, it will read config with some private parameters
    Second, it will get login|password for the user
    Third, it will read the file
    Fourth, it will exec the cmds on the devices
    '''
    with open(os.path.dirname(__file__) + "/config.yml") as f:
        config = yaml.safe_load(f)
        def_domain = config["def_domain"]

    parser = argparse.ArgumentParser(description="Multiple commands executor")
    parser.add_argument('-l', action="store", dest="login", default=getpass.getuser(),
                        help="Common login for the network equipment")
    parser.add_argument('fname', action="store", help="File with devices and commands")
    args = parser.parse_args()

    logging.info(f"Asking for password of user {args.login}")
    pwd = getpass.getpass()

    with open(args.fname) as f:
        logging.info("Reading config")
        data = yaml.safe_load(f)

    for dev in data.keys():
        logging.info(f"Logging into {dev}")

        # There might be a custom login
        # We check that and ask for a custom password
        if data[dev].get("login") is None:
            dev_login = args.login
            dev_pwd = pwd
        else:
            dev_login = data[dev].get("login")
            dev_pwd = getpass.getpass(f"{dev_login}'s password on {dev}:")

        # There might be a clearly stated platform
        dev_platform = data[dev].get("platform") or get_platform_by_hostname(dev)

        # Now, we create a dictionary for netmiko library
        device_params = {
            "device_type": dev_platform,
            "host": get_full_hostname(dev, def_domain),
            "username": dev_login,
            "password": dev_pwd,
            "verbose": True
        }

        # In case we need to go to enable mode with specific password
        if data[dev].get("enable"):
            device_params["secret"] = getpass.getpass(f"{dev}'s enable password:")

        # Check if there is a custom port
        if data[dev].get("port"):
            device_params["port"] = data[dev].get("port")

        # First try, SSH
        try:
            with ConnectHandler(**device_params) as ssh:
                if data[dev].get("enable"):
                    logging.info(ssh.enable())

                for cmd in data[dev]["cmds"]:
                    print(f"{cmd}")
                    res = ssh.send_command_timing(cmd)
                    print(f"{res}\n")

        except Exception as err:
            # logging.warning(f"SSH failed with {err}")
            logging.warning(f"SSH failed with {err}, trying Telnet")
            try:
                def_timeout = 2
                dev_port = device_params.get("port") or 23
                with telnetlib.Telnet(device_params["host"], dev_port) as tn:
                    #Logging in
                    tn.read_until(b":",timeout=def_timeout)
                    tn.write(dev_login.encode("ascii") + b'\n')

                    tn.read_until(b':', timeout=def_timeout)
                    tn.write(dev_pwd.encode("ascii") + b'\n')
                    auth_res = tn.read_until(b'#', timeout=def_timeout)
                    if auth_res.decode("ascii").find(dev) == -1:
                        raise ConnectionRefusedError(f"{auth_res.decode('ascii')}")

                    # Executing commands
                    print(f"Successfully logged into {dev} via Telnet")
                    if data[dev].get("enable"):
                        logging.info("Trying enable mode")
                        tn.write("enable".encode("ascii") + b'\n')
                        res = tn.read_until(b'#', timeout=def_timeout)
                        print(f"{res.decode('ascii')}\n")
                        tn.write(device_params["secret"].encode("ascii") + b'\n')
                        res = tn.read_until(b'#', timeout=def_timeout)
                        print(f"{res.decode('ascii')}\n")

                    for cmd in data[dev]["cmds"]:
                        tn.write(cmd.encode("ascii") + b'\n')
                        res = tn.read_until(b'#', timeout=def_timeout)
                        print(f"{res.decode('ascii')}\n")
            except Exception as tn_err:
                logging.warning(f"Auth failed, received:\n{tn_err}")
                logging.warning(f"Telnet failed either, skipping {dev}")
