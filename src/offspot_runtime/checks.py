import ipaddress
import re
import zoneinfo
from typing import Any, NamedTuple, Optional, Union

import iso3166

RE_HOSTNAME = re.compile(
    r"^([a-zA-Z0-9](?:(?:[a-zA-Z0-9-]*|(?<!-)\.(?![-.]))*[a-zA-Z0-9]+)?)$"
)
RE_HOTSPOT_TLD = re.compile(r"^[a-zA-Z][a-zA-Z0-9\-]*$")
RE_TIMEZONE = re.compile(r"^([a-zA-Z0-9\-\_\/]){1,80}$")
RE_SSID = re.compile(r'^[^!#;+\]/"\t][^+\]/"\t]{0,31}$')
RE_PASSPHRASE = re.compile(r"^[\u0020-\u007e]{8,63}$")  # Basic Latin
RE_IFACE_NAME = re.compile(r"^[a-z][a-z0-9]+[0-9]+$")
RE_COUNTRY_CODE = re.compile(r"[a-zA-Z]{2}")
FIRMWARES = {  # chipset: firmwares list
    "brcm43455": [
        "raspios",
        "supports-19_2021-11-30",
        "supports-24_2021-10-05_noap+sta",
        "supports-32_2015-03-01_unreliable",
    ],
    "brcm43430": ["raspios", "supports-30_2018-09-28"],
}


def port_in_range(range_or_port: str, expected: Union[str, int]) -> bool:
    """whether expected port is in the range_or_port compose string"""
    if not isinstance(range_or_port, str) or not isinstance(expected, (str, int)):
        return False

    if not all(part.isdigit() for part in str(range_or_port).split("-")):
        return False

    expected = int(expected)
    # not a range but a single port
    if "-" not in range_or_port:
        return int(range_or_port) == expected

    start, end = (int(item) for item in range_or_port.split("-", 1))
    return expected >= start and expected <= end


class CheckResponse(NamedTuple):
    """Check Response Interface"""

    passed: Optional[bool] = False
    help_text: str = ""

    def __bool__(self) -> bool:
        return self.passed or False

    def raise_for_status(self):
        if not self.passed:
            raise ValueError(self.help_text)


def is_valid_timezone(name: str) -> CheckResponse:
    """whether name represents a valid Timezone value"""
    if not isinstance(name, str):
        return CheckResponse(False, "Incorrect type")

    if not RE_TIMEZONE.match(name):
        return CheckResponse(False, f"Invalid zone format “{name}”")

    if name not in zoneinfo.available_timezones():
        return CheckResponse(False, f"Zone “{name}” not found")

    return CheckResponse(True)


def is_valid_hostname(name: str) -> CheckResponse:
    """whether name represents a valid hostname value"""
    if not isinstance(name, str):
        return CheckResponse(False, "Incorrect type")
    parts = [len(part) for part in name.split(".")]
    if (
        len(name) > 255
        or len(parts) > 64
        or min(parts) < 1
        or max(parts) > 63
        or not RE_HOSTNAME.match(name)
    ):
        return CheckResponse(False, f"Invalid hostname “{name}”")

    return CheckResponse(True)


def is_valid_compose(
    compose: dict[str, Any],
    *,
    require_services: Optional[bool] = True,
    require_image: Optional[bool] = True,
    required_ports: Optional[list[int]] = None,
) -> CheckResponse:
    """whether compose represents a valid-looking docker-compose Dict

    require_services: disable to allow empty compose
    require_image: disable to allow service to not have an image: entry (build?)
    required_ports: makes sure said ports are exposed on host (TCP)"""
    if not isinstance(compose, dict):
        return CheckResponse(False, "Incorrect type")

    # make sure we have defined services
    if compose.get("services", None) is None:
        return CheckResponse(False, "Missing `services:`")
    services = compose.get("services", [])
    if require_services and not services:
        return CheckResponse(False, "No services defined")
    if not isinstance(services, dict):
        return CheckResponse(False, "`services:` is not a dict")

    # make sure we have `image` on all services (we dont support build)
    if require_image:
        for svcname, service in services.items():
            if not isinstance(service, dict):
                return CheckResponse(False, f"Service `{svcname}:` is not a dict")
            if not service.get("image"):
                return CheckResponse(
                    False,
                    f"Service `{svcname}` has no `image`. `build` is not supported",
                )
            if not isinstance(service["image"], str):
                return CheckResponse(
                    False, f"Service `{svcname}` image format is invalid"
                )

    # make sure requested ports are exposed on host
    # https://docs.docker.com/compose/compose-file/#ports
    exposes = {rp: False for rp in required_ports} if required_ports else {}
    for svcname, service in services.items():
        ports = service.get("ports")
        if service.get("network_mode") == "host" and ports:
            return CheckResponse(
                False,
                f"Service `{svcname}`: Host network mode "
                "is incompatible with `ports`",
            )
        if ports is None:
            continue

        if not isinstance(ports, list):
            return CheckResponse(False, f"Service `{svcname}`: ports must be a list")

        for port in ports:
            # using long syntax
            if isinstance(port, dict):
                if port.get("protocol", "tcp") != "tcp":
                    continue

                for rport in [key for key, st in exposes.items() if st is False]:
                    if port_in_range(str(port.get("published", "")), rport):
                        exposes[rport] = True
            # using short syntax
            elif isinstance(port, str):
                # not interested in container-only port
                if ":" not in port:
                    continue
                # we want only tcp (if defined as its default)
                if "/" in port:
                    if port.rsplit("/", 1)[-1] != "tcp":
                        continue
                # host can be either a port-def or an IP:port-def
                host = port.rsplit(":", 1)[0]
                if ":" in host:
                    host_port = host.rsplit(":", 1)[-1]
                else:
                    host_port = host
                for rport in [key for key, st in exposes.items() if st is False]:
                    if port_in_range(host_port, rport):
                        exposes[rport] = True
            # might be container-only port as int
            else:
                continue  # pragma: no cover (cpython#94974)

    missing_ports = [str(key) for key, st in exposes.items() if st is False]
    if missing_ports:
        return CheckResponse(
            False, f"Required TCP port·s ({','.join(missing_ports)}) missing"
        )

    return CheckResponse(True)


def is_valid_ipv4(ip_addr: str, *, usable: Optional[bool] = True) -> CheckResponse:
    """whether textual IP address is a valid IP Address value

    usable controls whether address must be usable (bit-set, not network) or not"""

    # ipaddress objects accepts a bunch of formats (int, bytes)
    if not isinstance(ip_addr, str):
        return CheckResponse(False, "Incorrect type")

    # ipaddress accepts CIDR, hostmask and netmask notations
    if not re.match(r"^[0-9\.]+$", ip_addr):
        return CheckResponse(False, "Incorrect format")

    # let ipaddress validate the core thing
    try:
        address = ipaddress.IPv4Interface(ip_addr)
    except ValueError:
        return CheckResponse(False, f"Not a valid IPv4: `{ip_addr}`")

    # # if requested, make sure it's a usable host IP
    if usable:
        network = ipaddress.IPv4Network((address.ip, 24), strict=False)
        # make sure it's not a network address (ends in .0)
        if address.ip == network.network_address:
            return CheckResponse(False, "Network address not accepted")
        # make sure it's not a /24 broadcast address (ends in .255)
        if address.ip == network.broadcast_address:
            return CheckResponse(False, "Broadcast address not accepted")

        if (
            address.is_link_local
            or address.is_loopback
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            return CheckResponse(False, "Unauthorized network")
    return CheckResponse(True)


def is_valid_ethernet_config(
    network_type: str, address: str, routers: list[str], dns: list[str]
) -> CheckResponse:
    """whether valid ethernet config values"""
    if network_type not in ("dhcp", "static"):
        return CheckResponse(False, f"Incorrect network type: {network_type}")

    if network_type == "dhcp":
        return CheckResponse(True)

    if not address:
        return CheckResponse(False, "Missing IP address")

    if not is_valid_ipv4(address):
        return CheckResponse(False, "IP address is not correct")

    if not routers or not isinstance(routers, list):
        return CheckResponse(False, "`routers` must be a non-empty list")

    for router in routers:
        if not is_valid_ipv4(router):
            return CheckResponse(False, f"Invalid router address: {router}")

    if not dns or not isinstance(dns, list):
        return CheckResponse(False, "`dns` must be a list")

    for server in dns:
        if not is_valid_ipv4(server):
            return CheckResponse(False, f"Invalid DNS server address: {server}")

    return CheckResponse(True)


def is_valid_ssid(ssid: str) -> CheckResponse:
    """whether name represents a valid Timezone value"""
    if not isinstance(ssid, str):
        return CheckResponse(False, "Incorrect type")

    if not RE_SSID.match(ssid):
        return CheckResponse(False, "Must be 32 chars max without: !#;+]/")

    return CheckResponse(True)


def is_valid_wpa2_passphrase(passphrase: str) -> CheckResponse:
    """whether passphrase is a valid WPA2 passphrase value"""
    if not isinstance(passphrase, str):
        return CheckResponse(False, "Incorrect type")

    if not RE_PASSPHRASE.match(passphrase):
        return CheckResponse(False, "Must be 8-63 long latin chars and symbols")
    return CheckResponse(True)


def is_valid_wifi_channel(channel: int) -> CheckResponse:
    """whether channel is a valid WiFi channel value"""
    if not isinstance(channel, int):
        return CheckResponse(False, "Incorrect type")

    if channel < 1 or channel > 14:
        return CheckResponse(False, "Must be 1-14 (1-11 for most places)")

    return CheckResponse(
        True, "Channels 12-14 are not allowed everywhere" if channel > 11 else ""
    )


def is_valid_tld(tld: str) -> CheckResponse:
    """whether tld is a valid hotspot (custom) tld value"""
    if not isinstance(tld, str):
        return CheckResponse(False, "Incorrect type")

    if tld in ("example", "invalid", "local", "localhost", "onion", "test"):
        return CheckResponse(False, f"Unauthorized tld `{tld}`")

    if not RE_HOTSPOT_TLD.match(tld):
        return CheckResponse(False, f"Invalid hotspot tld `{tld}`")

    return CheckResponse(True)


def is_valid_domain(domain: str) -> CheckResponse:
    """whether domain is a valid domain (no tld) value"""
    if not isinstance(domain, str):
        return CheckResponse(False, "Incorrect type")

    if not is_valid_hostname(domain):
        return CheckResponse(False, f"Invalid domain `{domain}`")

    return CheckResponse(True)


def is_valid_wifi_country_code(country_code: str) -> CheckResponse:
    """whether country_code is a valid WiFI Country Code value"""
    if not isinstance(country_code, str):
        return CheckResponse(False, "Incorrect type")

    if not RE_COUNTRY_CODE.match(country_code):
        return CheckResponse(False, "Country code must be 2 letters")

    if country_code not in [country.alpha2 for country in iso3166.countries]:
        return CheckResponse(False, f"Country code `{country_code}` not found")
    return CheckResponse(True)


def is_valid_dhcp_range(range_str: str, with_address: str) -> CheckResponse:
    """whether range_str is a valid hotspot range value

    Format: {start},{end},{netmask},{ttl}

    start, end, netmask are all IPv4 addresses
    ttl is either `infinite` or a value with a duration suffix (s, m, h, d, w)
    with_address confirms that rnage's network is same as with_address's"""

    if not isinstance(range_str, str):
        return CheckResponse(False, "Incorrect type for range_str")

    if not isinstance(with_address, str):
        return CheckResponse(False, "Incorrect type for address")

    # make we we got all parts
    if not range_str.count(",") == 3:
        return CheckResponse(False, "Incorrect range-string format")

    # validate all parts as IPs (and not network/broadcast)
    start_str, end_str, netmask_str, ttl_str = range_str.split(",")
    if not is_valid_ipv4(start_str):
        return CheckResponse(False, f"Range start is not a valid IPv4: `{start_str}`")
    start = ipaddress.IPv4Interface(start_str)
    if not is_valid_ipv4(end_str):
        return CheckResponse(False, "Range end is not a valid IPv4")
    end = ipaddress.IPv4Interface(end_str)
    # netmask is an IP address but not a host-usable one
    if not is_valid_ipv4(netmask_str, usable=False):
        return CheckResponse(False, "Range netmask is not a valid IPv4")
    netmask = ipaddress.IPv4Interface(netmask_str)
    if not is_valid_ipv4(with_address):
        return CheckResponse(False, "Range host address is not valid IPv4")
    host = ipaddress.IPv4Interface(with_address)

    # prevent common mistakes
    if start == end:
        return CheckResponse(False, "Start and end of range are identical")
    if start == host:
        return CheckResponse(False, "Range start cannot be same as host")
    if end == host:
        return CheckResponse(False, "Range end cannot be same as host")

    # make sure we got a correct netmask for address (start)
    try:
        network = ipaddress.IPv4Network((start.ip, netmask.ip.exploded), strict=False)
    except ipaddress.NetmaskValueError:
        return CheckResponse(False, "Range netmask is not a valid netmask")

    # make sure all three addresses are within same network (start cant be out
    # as network is created from it)
    if end not in network:
        return CheckResponse(False, "Range end is incorrect for netmask")
    if host not in network:
        return CheckResponse(False, "Range network is different from host network")

    # ensure start if before end!
    network_hosts = list(network.hosts())
    if network_hosts.index(start.ip) > network_hosts.index(end.ip):
        return CheckResponse(False, "Range start is after end")

    # compute the nb of available host addresses
    hosts = network_hosts[network_hosts.index(start.ip) : network_hosts.index(end.ip)]
    nb_hosts = len(hosts)
    # host must be in same network but doesnt have to be in the range (but can!)
    if host.ip in hosts:
        nb_hosts -= 1
    msg = f"{nb_hosts} available addresses"

    if len(str(ttl_str)) < 2:
        return CheckResponse(False, "Missing DHCP lease-time")

    if ttl_str == "infinite":
        return CheckResponse(True, msg)
    if ttl_str[-1] not in ("s", "m", "h", "d", "w"):
        return CheckResponse(False, f"Inccorect DHCP lease-time suffix `{ttl_str[-1]}`")
    if not ttl_str[:-1].isdigit():
        return CheckResponse(False, f"Incorrect DHCP lease-time value {ttl_str}")

    return CheckResponse(True, msg)


def is_valid_network(
    network: str, *, with_address: str, allow_any: Optional[bool] = False
) -> CheckResponse:
    """whether network is a valid hotspot network (CIDR) value

    network and with_address must be on same network"""
    # ipaddress objects accepts a bunch of formats (int, bytes)
    if not isinstance(network, str):
        return CheckResponse(False, "Incorrect type")

    try:
        net = ipaddress.IPv4Network(network)
    except Exception:
        return CheckResponse(False, f"Invalid network `{network}")

    if net.num_addresses < 2:
        return CheckResponse(False, f"Not enough hosts in network `{network}`")

    if not allow_any and (
        net.is_link_local
        or net.is_loopback
        or net.is_multicast
        or net.is_reserved
        or net.is_unspecified
    ):
        return CheckResponse(False, "Unauthorized network")

    if not isinstance(with_address, str):
        return CheckResponse(False, "Incorrect type for with_address")

    if not is_valid_ipv4(with_address):
        return CheckResponse(False, "with_address is not a valid IPv4")

    if ipaddress.IPv4Address(with_address) not in net:
        return CheckResponse(False, "Network is not compatible with address")

    return CheckResponse(True)


def is_valid_interface_name(name: str) -> CheckResponse:
    """whether name represents a valid network interface name value"""
    if not isinstance(name, str):
        return CheckResponse(False, "Incorrect type")

    if not RE_IFACE_NAME.match(name):
        return CheckResponse(False, f"Invalid interface name format “{name}”")

    return CheckResponse(True)


def is_valid_ap_config(
    *,
    ssid: str,
    hide: bool,
    passphrase: str,
    address: str,
    as_gateway: bool,
    spoof: Union[bool, str],
    tld: str,
    domain: str,
    welcome: str,
    channel: int,
    country: str,
    interface: str,
    dhcp_range: str,
    network: str,
    dns: list[str],
    captured_address: str,
    other_interfaces: list[str],
    except_interfaces: list[str],
    nodhcp_interfaces: list[str],
) -> CheckResponse:
    """whether valid ap config values"""
    check = is_valid_ssid(ssid)
    if not check.passed:
        return CheckResponse(False, f"SSID: {check.help_text}")

    if not isinstance(hide, bool):
        return CheckResponse(False, "Hide: Incorrect type")

    if passphrase:
        check = is_valid_wpa2_passphrase(passphrase)
        if not check.passed:
            return CheckResponse(False, f"Passphrase: {check.help_text}")

    if not is_valid_ipv4(address):
        return CheckResponse(False, "Invalid IPv4 address")

    if not isinstance(as_gateway, bool):
        return CheckResponse(False, "As-gateway: Incorrect type")

    if spoof not in (True, False, "auto"):
        return CheckResponse(False, f"Invalid spoof value `{spoof}`")

    check = is_valid_tld(tld)
    if not check.passed:
        return CheckResponse(False, f"TLD: {check.help_text}")

    check = is_valid_domain(domain)
    if not check.passed:
        return CheckResponse(False, f"Domain: {check.help_text}")

    if welcome and not is_valid_domain(welcome).passed:
        return CheckResponse(False, f"Welcome Domain: {check.help_text}")

    check = is_valid_wifi_channel(channel)
    if not check.passed:
        return CheckResponse(False, f"Channel: {check.help_text}")

    check = is_valid_wifi_country_code(country)
    if not check.passed:
        return CheckResponse(False, f"Country: {check.help_text}")

    check = is_valid_interface_name(interface)
    if not check.passed:
        return CheckResponse(False, f"Interface: {check.help_text}")

    check = is_valid_dhcp_range(dhcp_range, with_address=address)
    if not check.passed:
        return CheckResponse(False, f"DHCP-range: {check.help_text}")

    check = is_valid_network(network, with_address=address, allow_any=False)
    if not check.passed:
        return CheckResponse(False, f"Network: {check.help_text}")

    if not isinstance(dns, list):
        return CheckResponse(False, "DNS: Incorrect type")
    for index, server in enumerate(dns):
        check = is_valid_ipv4(server)
        if not check.passed:
            return CheckResponse(False, f"DNS #{index}: {check.help_text}")

    if not is_valid_ipv4(captured_address):
        return CheckResponse(False, "Invalid IPv4 captured_address")

    if not isinstance(other_interfaces, list):
        return CheckResponse(False, "Other-interfaces: Incorrect type")
    for index, iface in enumerate(other_interfaces):
        check = is_valid_interface_name(iface)
        if not check.passed:
            return CheckResponse(False, f"Other-interfaces #{index}: {check.help_text}")

    if not isinstance(except_interfaces, list):
        return CheckResponse(False, "Except-interfaces: Incorrect type")
    for index, iface in enumerate(except_interfaces):
        check = is_valid_interface_name(iface)
        if not check.passed:
            return CheckResponse(
                False, f"Except-interfaces #{index}: {check.help_text}"
            )

    if not isinstance(nodhcp_interfaces, list):
        return CheckResponse(False, "NoDHCPD-interfaces: Incorrect type")
    for index, iface in enumerate(nodhcp_interfaces):
        check = is_valid_interface_name(iface)
        if not check.passed:
            return CheckResponse(
                False, f"NoDHCPD-interfaces #{index}: {check.help_text}"
            )

    return CheckResponse(True)


def is_valid_firmware_for(chipset: str, firmware: str) -> CheckResponse:
    """whether name represents a valid Timezone value"""
    if chipset not in FIRMWARES.keys():
        return CheckResponse(False, "Incorrect WiFi chipset “{chipset}”")

    if firmware not in FIRMWARES[chipset]:
        return CheckResponse(
            False, "Incorrect firmware “{firmware}” for {chipset} chipset"
        )

    return CheckResponse(True)
