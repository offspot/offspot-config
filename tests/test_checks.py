from typing import Union

import pytest  # pyright: ignore [reportMissingImports]
from yaml import SafeLoader as Loader
from yaml import load as yaml_load

from offspot_runtime.checks import (
    CheckResponse,
    is_valid_ap_config,
    is_valid_compose,
    is_valid_dhcp_range,
    is_valid_domain,
    is_valid_ethernet_config,
    is_valid_firmware_for,
    is_valid_hostname,
    is_valid_interface_name,
    is_valid_ipv4,
    is_valid_network,
    is_valid_ssid,
    is_valid_timezone,
    is_valid_tld,
    is_valid_wifi_channel,
    is_valid_wifi_country_code,
    is_valid_wpa2_passphrase,
    port_in_range,
)


def test_checkresponse_api():
    assert CheckResponse(True)
    assert CheckResponse(True).passed
    assert CheckResponse(True, "ERROR")
    assert CheckResponse(True, "ERROR").help_text
    assert CheckResponse(True, "ERROR").passed
    assert not CheckResponse(False)
    assert not CheckResponse(False).passed
    assert not CheckResponse(False, "ERROR")
    assert CheckResponse(False, "ERROR").help_text
    assert not CheckResponse(False, "ERROR").passed
    assert CheckResponse(True).raise_for_status() is None
    with pytest.raises(ValueError):
        CheckResponse(False, "ERROR!").raise_for_status()


@pytest.mark.parametrize(
    "timezone, should_pass",
    [
        (1, False),
        ("", False),
        ("UTC", True),
        ("utc", False),
        ("Africa/Bamako", True),
        ("Europe/Paris", True),
        ("CEST", False),
    ],
)
def test_timezones(timezone: str, should_pass: bool):
    check = is_valid_timezone(timezone)
    assert check.passed == should_pass


@pytest.mark.parametrize(
    "hostname, should_pass",
    [
        (1, False),
        ("", False),
        ("kiwix", True),
        ("my lab", False),
        ("not/a/folder", False),
        ("this.is.good", True),
        ("this-is.also-ok.right", True),
        ("underscore_aint", False),
    ],
)
def test_hostnames(hostname: str, should_pass: bool):
    check = is_valid_hostname(hostname)
    assert check.passed == should_pass


@pytest.mark.parametrize(
    "chipset, firmware, should_pass",
    [
        (1, "raspios", False),
        ("", "raspios", False),
        ("brcm43455", 1, False),
        ("brcm43455", "", False),
        ("brcm43455", "raspios", True),
        ("brcm43455", "supports-19_2021-11-30", True),
        ("brcm43455", "supports-24_2021-10-05_noap+sta", True),
        ("brcm43455", "supports-32_2015-03-01_unreliable", True),
        ("brcm43430", "raspios", True),
        ("brcm43430", "supports-30_2018-09-28", True),
        ("brcm43455", "supports-30_2018-09-28", False),
        ("brcm43430", "supports-19_2021-11-30", False),
        ("brcm43430", "supports-24_2021-10-05_noap+sta", False),
        ("brcm43430", "supports-32_2015-03-01_unreliable", False),
    ],
)
def test_firmwares(chipset: str, firmware: str, should_pass: bool):
    check = is_valid_firmware_for(chipset=chipset, firmware=firmware)
    assert check.passed == should_pass


def test_ipv4_api():
    assert is_valid_ipv4("192.168.1.1").passed
    assert is_valid_ipv4("192.168.1.1", usable=True).passed
    assert is_valid_ipv4("192.168.1.1", usable=True).passed
    assert is_valid_ipv4("192.168.1.1", usable=False).passed
    assert not is_valid_ipv4("192.168.1.0", usable=True).passed
    assert is_valid_ipv4("192.168.1.0", usable=False).passed
    assert is_valid_ipv4(ip_addr="192.168.1.1").passed
    assert is_valid_ipv4(ip_addr="192.168.1.1", usable=True).passed
    assert is_valid_ipv4(ip_addr="192.168.1.1", usable=False).passed
    assert not is_valid_ipv4(ip_addr="192.168.1.0", usable=True).passed
    assert is_valid_ipv4(ip_addr="192.168.1.0", usable=False).passed


@pytest.mark.parametrize(
    "address, usable, should_pass",
    [
        ("192.168.1.1", True, True),
        ("192.168.1.0", True, False),  # network not usable
        ("192.168.1.0", False, True),  # network not usable
        ("172.16.0.255", False, True),  # broadcast not usable
        ("172.16.0.255", True, False),  # broadcast not usable
        ("", False, False),
        ("garbage", False, False),
        ("192.168.l.2", True, False),  # l (letter) instead of 1
        ("255.255.255.0", False, True),  # netmask
        ("255.255.255.0", True, False),  # netmask not usable
        ("10.0.0.1/32", True, False),  # CIDR not accepted
        ("8.8.8.8", True, True),  # publics are OK
        ("127.0.0.1", True, False),  # loopback is not
        ("169.254.0.1", True, False),  # link-local is not
        ("240.0.0.1", True, False),  # reserved are not
        ("0.0.0.0", True, False),  # nosec B104 # unspecified is not
        (1, True, False),
        ("999.9.9.9", True, False),
    ],
)
def test_ipv4(address: str, usable: bool, should_pass: bool):
    check = is_valid_ipv4(address, usable=usable)
    assert check.passed == should_pass


def test_is_valid_ethernet_config_api():
    # TODO
    ...


@pytest.mark.parametrize(
    "network_type, address, routers, dns, should_pass",
    [
        ("dhcp", "", [], [], True),
        ("", "", [], [], False),
        ("static", "", [], [], False),
        ("static", "127.0.0.1", [], [], False),
        # network address
        ("static", "192.168.1.0", [], [], False),
        # missing routers and dns
        ("static", "192.168.1.1", [], [], False),
        # missing dns
        ("static", "192.168.1.1", ["192.168.1.200"], [], False),
        # invalid dns
        ("static", "192.168.1.1", ["192.168.1.200"], ["0.0.0.0"], False),  # nosec B104
        # invalid router
        ("static", "192.168.1.1", ["192.168.1.0"], ["192.168.1.2"], False),
        ("static", "192.168.1.1", ["192.168.1.10"], ["1.1.1.1"], True),
    ],
)
def test_is_valid_ethernet_config(
    network_type: str,
    address: str,
    routers: list[str],
    dns: list[str],
    should_pass: bool,
):
    check = is_valid_ethernet_config(
        network_type=network_type, address=address, routers=routers, dns=dns
    )
    assert check.passed == should_pass


@pytest.mark.parametrize(
    "range_str, with_address, should_pass",
    [
        ("", "", False),
        (1, None, False),
        ("192.168.1.1,192.168.1.200,255.255.255.0,1h", "192.168.1.254", True),
        ("192.168.1.1,192.168.1.200,255.255.0.0,1h", "192.168.2.1", True),
        # start is incorrect (network address)
        ("192.168.1.0,192.168.1.200,255.255.255.0,1h", "192.168.1.254", False),
        # end is incorrect (broadcast address)
        ("192.168.1.1,192.168.1.255,255.255.255.0,1h", "192.168.1.254", False),
        # start of range is same as host
        ("192.168.1.1,192.168.1.254,255.255.255.0,1h", "192.168.1.1", False),
        # end of range is same as host
        ("192.168.1.1,192.168.1.254,255.255.255.0,1h", "192.168.1.254", False),
        # host not compatible with range
        ("192.168.1.1,192.168.1.254,255.255.255.0,1h", "192.168.2.1", False),
        # incorrect ttl suffix
        ("192.168.1.1,192.168.1.254,255.255.255.0,1y", "192.168.1.100", False),
        # incorrect ttl value
        ("192.168.1.1,192.168.1.254,255.255.255.0,am", "192.168.1.100", False),
        # missing ttl suffix
        ("192.168.1.1,192.168.1.254,255.255.255.0,1", "192.168.1.100", False),
        # infinite ttl is valid
        ("192.168.1.1,192.168.1.254,255.255.255.0,infinite", "192.168.1.100", True),
        # incorrect address
        ("192.168.1.1,192.168.1.254,255.255.255.0,1y", 1, False),
        ("192.168.1.1,192.168.1.254,255.255.255.0,1y", "0.0.0.0", False),  # nosec B104
        # incorrect netmask
        ("192.168.1.1,192.168.1.254,32,1y", "192.168.1.100", False),
        ("192.168.1.1,192.168.1.254,1.1.1.1,1y", "192.168.1.100", False),
        # start == end
        ("192.168.1.1,192.168.1.1,255.255.255.0,1h", "192.168.1.254", False),
        # end is broadcast
        ("192.168.1.1,192.168.1.255,255.255.255.0,1h", "192.168.1.254", False),
        # end not in network
        ("192.168.1.1,192.168.2.10,255.255.255.0,1h", "192.168.1.200", False),
        # end before start
        ("192.168.1.10,192.168.1.9,255.255.255.0,1h", "192.168.1.200", False),
    ],
)
def test_is_valid_dhcp_range(range_str: str, with_address: str, should_pass: bool):
    check = is_valid_dhcp_range(range_str, with_address=with_address)
    assert check.passed == should_pass


def test_is_valid_network_api():
    # TODO
    ...


@pytest.mark.parametrize(
    "network, with_address, allow_any, should_pass",
    [
        ("", "", False, False),
        (1, None, False, False),
        ("127.0.0.1", "127.0.0.1", False, False),
        ("192.168.1.0/24", 1, False, False),
        ("192.168.1.0/24", "0.0.0.0", False, False),  # nosec B104
        ("192.168.1.0/24", "172.16.16.1", False, False),
        ("127.0.0.1", "127.0.0.1", True, False),
        ("127.0.0.1/32", "127.0.0.1", True, False),
        ("192.168.1.0/30", "192.168.1.1", False, True),
        ("169.254.0.0/16", "169.254.0.1", False, False),
    ],
)
def test_is_valid_network(
    network: str, with_address: str, allow_any: bool, should_pass: bool
):
    check = is_valid_network(network, with_address=with_address, allow_any=allow_any)
    assert check.passed == should_pass


@pytest.mark.parametrize(
    "name, should_pass",
    [
        (1, False),
        ("", False),
        ("eth0", True),
        ("wlan1", True),
        ("enp0s5", True),
        ("Eth0", False),
        ("1eth", False),
        ("e1", False),
        ("eth0a", False),
    ],
)
def test_is_valid_interface_name(name: str, should_pass: bool):
    check = is_valid_interface_name(name)
    assert check.passed == should_pass


@pytest.mark.parametrize(
    "ssid, should_pass",
    [
        (1, False),
        ("kiwix", True),
        ("An bɛɛ bɛ ɲogɔŋ bolow", True),
        ("this is fine ;,.?{}()*&^%$#@!", True),
        ("", False),
        ("!Hello", False),
        ("Hello!", True),
        ("#Hello", False),
        (";Hello", False),
        ("]Hello", False),
        ("\tHello", False),
        ("Me + You", False),
        ("hello\tworld", False),
        ("hello ]", False),
        ('SSID "DROP TABLE users', False),
        ("This is just about a tad too long", False),
    ],
)
def test_is_valid_ssid(ssid: str, should_pass: bool):
    check = is_valid_ssid(ssid)
    assert check.passed == should_pass


@pytest.mark.parametrize(
    "passphrase, should_pass",
    [
        (1, False),
        ("kiwix", False),
        ("pas d'accent là bas", False),
        ("", False),
        ("abcdefgh", True),
        ("abcdefghabcdefghabcdefghabcdefghabcdefghabcdefghabcdefghabcdefg", True),
        ("abcdefghabcdefghabcdefghabcdefghabcdefghabcdefghabcdefghabcdefgh", False),
    ],
)
def test_is_valid_wpa2_passphrase(passphrase: str, should_pass: bool):
    check = is_valid_wpa2_passphrase(passphrase)
    assert check.passed == should_pass


@pytest.mark.parametrize(
    "channel, should_pass",
    [
        ("", False),
        ("6", False),
        (-1, False),
        (0, False),
        (1, True),
        (2, True),
        (3, True),
        (4, True),
        (5, True),
        (6, True),
        (7, True),
        (8, True),
        (9, True),
        (10, True),
        (11, True),
        (12, True),
        (13, True),
        (14, True),
        (15, False),
        (110, False),
    ],
)
def test_is_valid_wifi_channel(channel: int, should_pass: bool):
    check = is_valid_wifi_channel(channel)
    assert check.passed == should_pass
    if check.passed and channel > 11:
        assert check.help_text


@pytest.mark.parametrize(
    "tld, should_pass",
    [
        ("", False),
        (1, False),
        ("hotspot", True),
        (".hotspot", False),
        ("offspot", True),
        ("local", False),
        ("com", True),
    ],
)
def test_is_valid_tld(tld: str, should_pass: bool):
    check = is_valid_tld(tld)
    assert check.passed == should_pass


@pytest.mark.parametrize(
    "domain, should_pass",
    [
        ("", False),
        (1, False),
        ("hotspot", True),
        (".hotspot", False),
        ("my domain", False),
        ("my-domain", True),
        ("a.b.c.d.e.f.g.h", True),
        ("my_domain", False),
    ],
)
def test_is_valid_domain(domain: str, should_pass: bool):
    check = is_valid_domain(domain)
    assert check.passed == should_pass


@pytest.mark.parametrize(
    "country_code, should_pass",
    [
        (0, False),
        ("", False),
        ("00", False),
        ("US", True),
        ("ML", True),
        ("MLI", False),
    ],
)
def test_is_valid_wifi_country_code(country_code: str, should_pass: bool):
    assert is_valid_wifi_country_code(country_code).passed == should_pass


def test_is_valid_ap_config():
    defaults = {
        "ssid": "",
        "hide": False,
        "passphrase": None,
        "address": "192.168.2.1",
        "as_gateway": False,
        "spoof": "auto",
        "tld": "offspot",
        "domain": "generic",
        "welcome": "goto.generic",
        "channel": 11,
        "country": "US",
        "interface": "wlan0",
        "dhcp_range": "192.168.2.2,192.168.2.254,255.255.255.0,1h",
        "network": "192.168.2.0/24",
        "dns": ["8.8.8.8", "1.1.1.1"],
        "captured_address": "192.168.0.1",
        "other_interfaces": [],
        "except_interfaces": [],
        "nodhcp_interfaces": [],
    }
    config = defaults.copy()
    assert not is_valid_ap_config(**config)

    config = defaults.copy()
    config["ssid"] = "working!"
    assert is_valid_ap_config(**config)

    config["hide"] = "yes"
    assert not is_valid_ap_config(**config)
    config["hide"] = True
    assert is_valid_ap_config(**config)

    config["passphrase"] = "ɛɛɛɛɛ NOT OK"
    assert not is_valid_ap_config(**config)
    config["passphrase"] = "this is OK"
    assert is_valid_ap_config(**config)

    config["channel"] = 15
    assert not is_valid_ap_config(**config)
    config["channel"] = 6
    assert is_valid_ap_config(**config)

    config["country"] = "AAA"
    assert not is_valid_ap_config(**config)
    config["country"] = "FR"
    assert is_valid_ap_config(**config)

    config["interface"] = "wifi"
    assert not is_valid_ap_config(**config)
    config["interface"] = "wlan0"
    assert is_valid_ap_config(**config)

    config["dhcp_range"] = "192.168.2.1,192.168.2.254,255.255.255.0,1h"
    assert not is_valid_ap_config(**config)
    config["dhcp_range"] = "192.168.2.2,192.168.2.254,255.255.255.0,1h"
    assert is_valid_ap_config(**config)

    config["network"] = "192.168.2.2"
    assert not is_valid_ap_config(**config)
    config["network"] = "192.168.2.0/24"
    assert is_valid_ap_config(**config)

    config["address"] = "0.0.0.0"  # nosec B104
    assert not is_valid_ap_config(**config)
    config["address"] = "192.168.2.3"
    assert is_valid_ap_config(**config)

    config["as_gateway"] = 3
    assert not is_valid_ap_config(**config)
    config["as_gateway"] = True
    assert is_valid_ap_config(**config)

    config["spoof"] = "yes"
    assert not is_valid_ap_config(**config)
    config["spoof"] = True
    assert is_valid_ap_config(**config)

    config["tld"] = ".abadaboum"
    assert not is_valid_ap_config(**config)
    config["tld"] = "hotspot"
    assert is_valid_ap_config(**config)

    config["domain"] = "hot_spot"
    assert not is_valid_ap_config(**config)
    config["domain"] = "project"
    assert is_valid_ap_config(**config)

    config["welcome"] = "goto.hot_spot"
    assert not is_valid_ap_config(**config)
    config["welcome"] = "goto.project"
    assert is_valid_ap_config(**config)

    config["dns"] = 1
    assert not is_valid_ap_config(**config)
    config["dns"] = ["240.0.0.1"]
    assert not is_valid_ap_config(**config)
    config["dns"] = ["1.1.1.1"]
    assert is_valid_ap_config(**config)

    for key in ("other_interfaces", "except_interfaces", "nodhcp_interfaces"):
        config[key] = 1
        assert not is_valid_ap_config(**config)
        config[key] = ["wifi"]
        assert not is_valid_ap_config(**config)
        config[key] = ["eth1"]
        assert is_valid_ap_config(**config)


def test_port_in_range_api():
    # TODO
    ...


@pytest.mark.parametrize(
    "range_or_port, expected, should_pass",
    [
        (1, 80, False),
        ("", 80, False),
        ("80", 80, True),
        ("81", 80, False),
        ("8000-8100", 8010, True),
        ("8000-8100", 80, False),
    ],
)
def test_port_in_range(
    range_or_port: str, expected: Union[str, int], should_pass: bool
):
    assert port_in_range(range_or_port, expected=expected) == should_pass


def test_is_valid_compose_api():
    # TODO
    ...


def test_is_valid_compose_minimal():
    # invalid compose
    assert not is_valid_compose(None)  # type: ignore
    assert not is_valid_compose({})

    # services not a dict
    assert not is_valid_compose({"services": []}, require_services=False)

    # empty compose
    compose = {"services": {}}
    assert is_valid_compose(
        compose=compose, require_services=False, require_image=False, required_ports=[]
    )
    assert not is_valid_compose(
        compose=compose, require_services=True, require_image=False, required_ports=[]
    )

    # service is not a dict
    compose = {"services": {"kiwix": "ghcr.io/kiwix-tools"}}
    assert not is_valid_compose(compose=compose)

    # service has no image
    compose = {"services": {"kiwix": {"build": "."}}}
    assert is_valid_compose(
        compose=compose, require_services=True, require_image=False, required_ports=[]
    )
    assert not is_valid_compose(
        compose=compose, require_services=True, require_image=False, required_ports=[80]
    )
    assert not is_valid_compose(
        compose=compose, require_services=True, require_image=True, required_ports=[]
    )

    # service has image
    compose = {"services": {"kiwix": {"image": "ghcr.io/kiwix/kiwix-tools:latest"}}}
    assert is_valid_compose(
        compose=compose, require_services=True, require_image=True, required_ports=[]
    )
    assert not is_valid_compose(
        compose=compose, require_services=True, require_image=True, required_ports=[80]
    )

    # image is not a string
    assert not is_valid_compose({"services": {"kiwix": {"image": 1}}})

    # host-mode network and ports are incompatible
    assert not is_valid_compose(
        {
            "services": {
                "kiwix": {"image": "hop", "network_mode": "host", "ports": ["80"]}
            }
        }
    )

    # ports not a list
    assert not is_valid_compose({"services": {"kiwix": {"image": "-", "ports": "80"}}})


@pytest.mark.parametrize(
    "port, required_ports, should_pass",
    [
        (80, [], True),
        (80, [80], False),
        ("80", [80], False),
        ("81:80", [80], False),
        ("80:81", [80], True),
        ("81:80/tcp", [80], False),
        ("80:80/tcp", [80], True),
        ("81:80/udp", [80], False),
        ("80:80/udp", [80], False),
        ("8000-8100:9000-9100", [8010], True),
        ("8000-8100:9000-9100", [9010], False),
        ("8000-8100:9000-9100/tcp", [8010], True),
        ("8000-8100:9000-9100/tcp", [9010], False),
        ("8000-8100:9000-9100/udp", [8010], False),
        ("8000-8100:9000-9100/udp", [9010], False),
        ({"target": 81, "published": 80}, [80], True),
        ({"target": 81, "published": "70-90"}, [80], True),
        ({"target": 81, "published": 80, "protocol": "udp"}, [80], False),
        ({"target": 81, "published": 80, "protocol": "tcp"}, [80], True),
        ({"target": 81, "published": 80, "protocol": "tcp"}, [8080], False),
    ],
)
def test_is_valid_compose_ports(
    port: str, required_ports: list[int], should_pass: bool
):
    compose = {
        "services": {
            "kiwix": {"image": "ghcr.io/kiwix/kiwix-tools:latest", "ports": [port]}
        }
    }
    check = is_valid_compose(
        compose=compose,
        require_services=True,
        require_image=True,
        required_ports=required_ports,
    )
    assert check.passed == should_pass


def test_is_valid_compose_sample():
    compose = yaml_load(
        """
services:
  reverse-proxy:
    container_name: reverse-proxy
    image: caddy:2.6.1-alpine
    volumes:
      - "/data/conf/Caddyfile-host:/etc/caddy/Caddyfile:ro"
      - "/data/conf/caddy/config:/config/caddy:rw"
      - "/data/conf/caddy/data:/data/caddy:rw"
    command: caddy run --resume --config /etc/caddy/Caddyfile --adapter caddyfile
    environment:
      FQDN: demo.offspot
      KIWIX_FQDN: kiwix.demo.offspot
      KIWIX_LINK: kiwix:80
    ports:
      - "80:80"
      - "443:443"
      - "2020:2020"
      - "192.168.1.1:2020:2020"
      - 1023
    expose:
      - "2020"
    networks:
      - frontend
      - backend
  kiwix:
    container_name: kiwix
    image: ghcr.io/offspot/kiwix-serve:dev
    command: /bin/sh -c "kiwix-serve /data/*.zim"
    volumes:
      - "/data/content/zims:/data:ro"
    expose:
      - "80"
    networks:
      - backend
networks:
  frontend:
  backend:
""",
        Loader=Loader,
    )
    assert is_valid_compose(
        compose=compose,
        require_services=True,
        require_image=True,
        required_ports=[80, 443],
    )
