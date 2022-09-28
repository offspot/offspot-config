#!/usr/bin/env python3

""" Configures WiFi Access Point (using hostapd and dnsmasq)

    Refs:
        https://en.wikipedia.org/wiki/List_of_WLAN_channels#2.4_GHz_(802.11b/g/n/ax)
"""

import argparse
import fcntl
import inspect
import pathlib
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
from typing import Optional

parent = pathlib.Path(inspect.getfile(inspect.currentframe())).parent.resolve()
if parent not in sys.path:
    sys.path.insert(0, str(parent))

from offspot_config_lib import (  # noqa: E402
    IPTABLES_DIR,
    Config,
    __version__,
    ensure_folder,
    fail_error,
    fail_invalid,
    is_valid_ip,
    restart_service,
    simple_run,
    succeed,
    warn_unless_root,
)

NAME = pathlib.Path(__file__).stem
NETWORK_TYPES = ("dhcp", "static")
RE_SSID = re.compile(r'^[^!#;+\]/"\t][^+\]/"\t]{0,31}$')
RE_PASSPHRASE = re.compile(r"^[\u0020-\u007e]{8,63}$")
RFKILL_PATH = pathlib.Path("/usr/sbin/rfkill")
IPTABLES_PATH = pathlib.Path("/usr/sbin/iptables")
DEFAULT_CHANNEL = 11
DEFAULT_ADDRESS = "192.168.2.1"
DEFAULT_DNS = ["8.8.8.8", "1.1.1.1"]
DEFAULT_TLD = "offspot"
DEFAULT_DOMAIN = "generic"
DEFAULT_WELCOME_DOMAIN = "goto.generic"
HOSTAPD_CONF_PATH = pathlib.Path("/etc/hostapd/hostapd.conf")
DNSMASQ_CONF_PATH = pathlib.Path("/etc/dnsmasq.conf")
NF_MASQUERADE_RULES_PATH = IPTABLES_DIR / "offspot-masquerade.rules"
NF_FORWARDING_RULES_PATH = IPTABLES_DIR / "offspot-forwarding.rules"
INTERFACES_PATH = pathlib.Path("/etc/network/interfaces.d/offspot")
HOSTAPD_CONF_TEMPLATE = """
# interface name
interface={interface}

# socket access
ctrl_interface=/var/run/hostapd
ctrl_interface_group=0

# wlan card driver
driver=nl80211
# wifi ssid
ssid={ssid}
utf8_ssid=1
country_code={country_code}
# wifi mode (g for g and n)
hw_mode=g
# wifi channel
channel={channel}
# MAC address access control (0 = accept by default)
macaddr_acl=0
# dont hide the SSID
ignore_broadcast_ssid={ignore_broadcast}
{wpa2}
ieee80211n=1
wmm_enabled=1
"""
HOSTAPD_CONF_WPA2_TEMPLATE = """
# use WPA
auth_algs=1
# wpa version
wpa=2
# wpa passwd
wpa_passphrase={passphrase}
# wpa encryption
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""
DNSMASQ_CONF_TEMPLATE = """
# interface to listen on
interface={interface}
{other_interfaces_lines}
{except_interfaces_lines}

dhcp-range={dhcp_range}
{other_interfaces_ranges_lines}
{nodhcp_interfaces_lines}

expand-hosts
bogus-priv
domain={tld},{network},local

address=/{welcome_fqdn}/{address}
address=/{fqdn}/{address}
{servers}
no-hosts
"""
INTERFACES_CONF = """
allow-hotplug {interface}
iface {interface} inet static
address {address}
netmask {netmask}
"""

Config.init(NAME)
logger = Config.logger


def get_ip_address(interface: str) -> str:
    """IPv4 address configured for interface"""
    logger.debug(f"getting ip-address of {interface=}")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(
        fcntl.ioctl(
            s.fileno(),
            0x8915,
            struct.pack("256s", interface.encode("ASCII")[:15]),  # SIOCGIFADDR
        )[20:24]
    )


def set_ip_address(
    interface: str, address: str, netmask: Optional[str] = "255.255.255.0"
):
    """assign static IPv4 address to interface"""
    with open(INTERFACES_PATH, "w") as fh:
        fh.write(
            INTERFACES_CONF.format(
                interface=interface, address=address, netmask=netmask
            )
        )

    return simple_run(
        ["/usr/sbin/ifconfig", interface, address, "netmask", netmask, "up"]
    )


def dhcp_range_for(address: str):
    """generic dhcp range string from a class C address"""
    network = address.rsplit(".", 1)[0]
    return f"{network}.100,{network}.240,255.255.255.0,12h"


def unblock_wireless():
    """release software lock of wlan devices"""
    if simple_run([str(RFKILL_PATH), "unblock", "wifi"]) != 0:
        return 1

    if Config.debug:
        ps = subprocess.run(
            [str(RFKILL_PATH), "--output-all"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        logger.debug(f"rfkill status:\n{ps.stdout}\n---")


def write_hostapd_conf(hostapd_conf_path: pathlib.Path, **kwargs) -> int:
    """std-returncode, building and writing hostapd.conf from kwargs"""
    wpa2 = (
        HOSTAPD_CONF_WPA2_TEMPLATE.format(passphrase=kwargs["passphrase"])
        if kwargs["passphrase"]
        else ""
    )

    ensure_folder(hostapd_conf_path.parent)
    with open(hostapd_conf_path, "w") as fh:
        fh.write(
            HOSTAPD_CONF_TEMPLATE.format(
                ignore_broadcast="1" if kwargs["hide_ssid"] else 0,
                wpa2=wpa2,
                **kwargs,
            )
        )

    return 0


def write_dnsmasq_conf(dnsmasq_conf_path: pathlib.Path, **kwargs) -> int:
    """std-returncode, building and writing dnsmasq.conf from kwargs"""

    kwargs = dict(kwargs)  # work on a local copy
    kwargs["other_interfaces_lines"] = "\n".join(
        [
            f"interface={iface}"
            for iface in kwargs["other_interfaces"] + kwargs["nodhcp_interfaces"]
        ]
    )
    kwargs["other_interfaces_ranges_lines"] = "\n".join(
        [
            f"dhcp-range={dhcp_range_for(get_ip_address(iface))}"
            for iface in kwargs["other_interfaces"]
        ]
    )
    kwargs["except_interfaces_lines"] = "\n".join(
        [f"except-interface={iface}" for iface in kwargs["except_interfaces"]]
    )
    kwargs["nodhcp_interfaces_lines"] = "\n".join(
        [f"no-dhcp-interface={iface}" for iface in kwargs["nodhcp_interfaces"]]
    )

    # spoof-mode captures all dns requests (captive-portal-like)
    if kwargs["spoof"]:
        kwargs["servers"] = f"address=/#/{kwargs['address']}"
    # let clients use proper DNS servers
    elif kwargs["as_gateway"]:
        kwargs["servers"] = "\n".join([f"server={server}" for server in kwargs["dns"]])
    # no internet, no need for DNS
    else:
        kwargs["servers"] = ""

    # additional, static/local records
    kwargs["fqdn"] = f"{kwargs['domain']}.{kwargs['tld']}"
    kwargs["welcome_fqdn"] = f"{kwargs['welcome_domain']}.{kwargs['tld']}"

    # write to a temp file and check syntax first
    temp_conf = pathlib.Path(tempfile.NamedTemporaryFile(suffix=".conf").name)
    with open(temp_conf, "w") as fh:
        fh.write(DNSMASQ_CONF_TEMPLATE.format(**kwargs))
    if simple_run(["/usr/sbin/dnsmasq", "--test", "-C", str(temp_conf)]) != 0:
        return 1

    ensure_folder(dnsmasq_conf_path.parent)
    shutil.move(temp_conf, dnsmasq_conf_path)
    return 0


def enable_routing():
    """enable (and persist) IP routing in kernel"""
    with open("/etc/sysctl.d/offspot-ip-forward.conf", "w") as fh:
        fh.write("net.ipv4.ip_forward=1\n")

    return simple_run(["/usr/sbin/sysctl", "-p"])


def enable_masquerade_for(interface: str):
    """add (and persist) rule to masquerade traffic through interface (internet)"""
    table, rule = "nat", ["-A", "POSTROUTING", "-o", interface, "-j", "MASQUERADE"]
    if simple_run([str(IPTABLES_PATH), "-t", table] + rule) != 0:
        return 1
    ensure_folder(NF_MASQUERADE_RULES_PATH.parent)
    with open(NF_MASQUERADE_RULES_PATH, "w") as fh:
        fh.write(f"*{table}\n{' '.join(rule)}\nCOMMIT\n")
    return 0


def disable_masquerade():
    """remove masquerade rule from persiting ruleset. No live-disabling"""
    ensure_folder(NF_MASQUERADE_RULES_PATH.parent)
    with open(NF_MASQUERADE_RULES_PATH, "w") as fh:
        fh.write("")
    return 0


def enable_forwarding_for(interface: str) -> int:
    """add (and persist) rules to forward all traffic from/to interface (wireless)"""
    table, rule_in, rule_out = (
        "filter",
        ["-A", "FORWARD", "-i", interface, "-j", "ACCEPT"],
        ["-A", "FORWARD", "-o", interface, "-j", "ACCEPT"],
    )
    if (
        simple_run([str(IPTABLES_PATH), "-t", table] + rule_in) != 0
        or simple_run([str(IPTABLES_PATH), "-t", table] + rule_out) != 0
    ):
        return 1

    ensure_folder(NF_FORWARDING_RULES_PATH.parent)
    with open(NF_FORWARDING_RULES_PATH, "w") as fh:
        fh.write(f"*{table}\n{' '.join(rule_in)}\n{' '.join(rule_out)}\nCOMMIT\n")
    return 0


def disable_forwarding():
    """remove forwarding rule from persiting ruleset. No live-disabling"""
    ensure_folder(NF_FORWARDING_RULES_PATH.parent)
    with open(NF_FORWARDING_RULES_PATH, "w") as fh:
        fh.write("")
    return 0


def main(**kwargs) -> int:
    logger.info("Configuring WiFi AP")
    warn_unless_root()

    if not RE_SSID.match(kwargs["ssid"]):
        fail_invalid("Invalid SSID. Use 32 chars max without: !#;+]/")

    if kwargs["passphrase"] and not RE_PASSPHRASE.match(kwargs["passphrase"]):
        fail_invalid("Invalid Passphrase. Must be 8-63 long ASCII chars")

    if kwargs["channel"] < 1 or kwargs["channel"] > 14:
        fail_invalid("Invalid channel. Must be 1-14 (1-11 for most places)")

    if kwargs["channel"] > 11:
        logger.warning("Channels 12-14 are not allowed everywhere")

    if not is_valid_ip(kwargs["address"]):
        fail_invalid("Invalid IPv4 address")

    if not kwargs["dns"]:
        kwargs["dns"] = DEFAULT_DNS

    if kwargs["network"] is None:
        kwargs["network"] = re.sub(r"\.\d+$", ".0/24", kwargs["address"])

    kwargs["dhcp_range"] = dhcp_range_for(kwargs["address"])

    unblock_wireless()
    logger.debug("wireless unblocked")

    if write_hostapd_conf(hostapd_conf_path=HOSTAPD_CONF_PATH, **kwargs) != 0:
        fail_error("writing hostapd.conf failed")
    logger.debug("hostapd.conf checked and written")

    if restart_service("hostapd") != 0:
        fail_error("hostapd restart failed")
    logger.debug("hostapd restarted")

    if set_ip_address(kwargs["interface"], kwargs["address"]) != 0:
        fail_error("failed to set {kwargs['address']=} on {kwargs['interface']=}")
    logger.debug("ip-address set")

    if write_dnsmasq_conf(dnsmasq_conf_path=DNSMASQ_CONF_PATH, **kwargs) != 0:
        fail_error("writing dnsmasq.conf failed")
    logger.debug("dnsmasq.conf written")

    if restart_service("dnsmasq") != 0:
        fail_error("dnsmasq restart failed")
    logger.debug("dnsmasq restarted")

    # docker does it already
    if enable_routing() != 0:
        fail_error("failed to enable routing in kernel")
    logger.debug("routing enabled")

    if kwargs["as_gateway"]:
        if enable_masquerade_for("eth0") != 0:
            fail_error("failed to enable masquerade in packet filter")
        logger.debug("masquerade enabled")
    else:
        disable_masquerade()
        logger.debug("masquerade disabling requested")

    if (
        kwargs["as_gateway"]
        or kwargs["other_interfaces"]
        or kwargs["nodhcp_interfaces"]
    ):
        if enable_forwarding_for(kwargs["interface"]) != 0:
            fail_error("failed to enable forwarding in packet filter")
        logger.debug("forwarding enabled")
    else:
        disable_forwarding()
        logger.debug("forwarding disabling requested")

    succeed("Wireless AP configured")


def entrypoint():
    parser = argparse.ArgumentParser(
        prog=NAME,
        description="Configure Offspot's WiFi Access Point",
    )
    parser.add_argument("-V", "--version", action="version", version=__version__)
    parser.add_argument("--debug", action="store_true", dest="debug")

    parser.add_argument(
        help="SSID (Network Name)",
        dest="ssid",
    )

    parser.add_argument(
        "--hide",
        help="Hide SSID (Clients must know and enter its name to connect)",
        dest="hide_ssid",
        action="store_true",
        required=False,
    )

    parser.add_argument(
        "--passphrase",
        help="Passphrase/password to connect to the network. Defaults to Open Network",
        dest="passphrase",
        default="",
        required=False,
    )

    parser.add_argument(
        "--address",
        help="IP address to set on interface",
        dest="address",
        required=False,
        default=DEFAULT_ADDRESS,
    )

    parser.add_argument(
        "--as-gateway",
        help="Make this device act as a gateway to Internet (wired) "
        "for AP (wireless) clients (when connected)",
        dest="as_gateway",
        action="store_true",
        default=False,
        required=False,
    )

    parser.add_argument(
        "--tld",
        help=f"Top-level domain to use as local “domain”. Defaults to {DEFAULT_TLD}",
        dest="tld",
        default=DEFAULT_TLD,
        required=False,
    )

    parser.add_argument(
        "--domain",
        help=f"Domain name to use for services. Defaults to {DEFAULT_DOMAIN}.<tld>",
        dest="domain",
        default=DEFAULT_DOMAIN,
        required=False,
    )

    parser.add_argument(
        "--welcome",
        help="Another domain to respond to. "
        f"Defaults to {DEFAULT_WELCOME_DOMAIN}.<tld>",
        dest="welcome_domain",
        default=DEFAULT_WELCOME_DOMAIN,
        required=False,
    )

    parser.add_argument(
        "--channel",
        help=f"WiFi channel to use for the network. Defaults to {DEFAULT_CHANNEL}",
        dest="channel",
        default=DEFAULT_CHANNEL,
        type=int,
        required=False,
    )

    parser.add_argument(
        "--country",
        help="Country-code to apply frequencies limitations for. Defaults to FR",
        dest="country_code",
        default="FR",
        required=False,
    )

    parser.add_argument(
        "--interface",
        help="Interface to configure AP for. Defaults to wlan0",
        dest="interface",
        default="wlan0",
        required=False,
    )

    parser.add_argument(
        "--dhcp-range",
        help="IP addresses range for the AP clients. Use start,end,subnet,ttl format. "
        "Make sure to be on same network as interface's address. "
        "Defaults to .100-.240 12h for class C from interface's address.",
        dest="dhcp_range",
        required=False,
    )

    parser.add_argument(
        "--network",
        help="Network to advertise DHCP on. Defaults to .0/24 from interface's address",
        dest="network",
        default=None,
        required=False,
    )

    parser.add_argument(
        "--dns",
        help=f"DNS to set via DHCP when working as Internet gateway. "
        f'Defaults to {", ".join(DEFAULT_DNS)}',
        dest="dns",
        default=[],
        required=False,
        action="append",
    )

    parser.add_argument(
        "--other-interfaces",
        help="Additional interfaces to provide DNS and DHCP on.",
        dest="other_interfaces",
        default=[],
        required=False,
        action="append",
    )

    parser.add_argument(
        "--except-interfaces",
        help="Interfaces to specificaly not listen on",
        dest="except_interfaces",
        default=[],
        required=False,
        action="append",
    )

    parser.add_argument(
        "--nodhcp-interfaces",
        help="Interfaces to provide DNS (but not DHCP) on.",
        dest="nodhcp_interfaces",
        default=[],
        required=False,
        action="append",
    )

    parser.add_argument("--spoof", action="store_true", dest="spoof")

    kwargs = dict(parser.parse_args()._get_kwargs())
    Config.set_debug(kwargs.get("debug"))

    try:
        sys.exit(main(**kwargs))
    except Exception as exc:
        if Config.debug:
            logger.exception(exc)
        else:
            logger.error(exc)
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(entrypoint())
