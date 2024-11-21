from models import Device, InternetRouter
from config import Config
from ipaddress import IPv4Network

class ConfigGenerator:
    @staticmethod
    def generate_device_config(device: Device) -> str:
        config = f"""!
! Configuration for {device.name} ({device.location})
! Site ID: {device.site_id}
! Role: {'Hub' if device.is_hub else 'Spoke'}
!
"""
        config += ConfigGenerator._generate_failover_policy(device)
        config += ConfigGenerator._generate_interface_config(device)
        config += ConfigGenerator._generate_crypto_config(device)
        config += ConfigGenerator._generate_bgp_config(device)
        return config

    @staticmethod
    def _generate_failover_policy(device: Device) -> str:
        config = "\n! WAN Failover Policy\n"
        if len(device.wan_interfaces) > 1:
            config += """
! Interface health monitoring policy
policy-map type inspect dns preset_dns_map
 parameters
  message-length maximum client auto
  message-length maximum 512
  no tcp-inspection

policy-map global_policy
 class class-default
  inspect dns preset_dns_map
  inspect ftp
  inspect h323 h225
  inspect h323 ras
  inspect rsh
  inspect rtsp
  inspect esmtp
  inspect sqlnet
  inspect skinny
  inspect sunrpc
  inspect xdmcp
  inspect sip
  inspect netbios
  inspect tftp
  inspect ip-options
  inspect icmp
"""
        return config

    @staticmethod
    def _generate_interface_config(device: Device) -> str:
        config = """
! BFD Template Configuration
bfd-template multi-hop INTERFACES
 interval min-tx {0} min-rx {1} multiplier {2}

bfd-template single-hop default
 interval min-tx {3} min-rx {4} multiplier {5}

bfd slow-timers 2000
""".format(
        Config.BFD_TEMPLATE_MULTI_TX,
        Config.BFD_TEMPLATE_MULTI_RX,
        Config.BFD_TEMPLATE_MULTI_MULT,
        Config.BFD_TEMPLATE_SINGLE_TX,
        Config.BFD_TEMPLATE_SINGLE_RX,
        Config.BFD_TEMPLATE_SINGLE_MULT
    )

        local_ip, local_netmask = device.get_local_network_address()
        if local_ip and local_netmask:
            config += f"""
interface Vlan17
 nameif inside
 security-level 100
 ip address {local_ip} {local_netmask}
 no shutdown
"""

        for i, wan in enumerate(device.wan_interfaces):
            interface_name = f"outside-{wan.name.lower().replace('/', '_')}"

            config += f"""
interface {wan.name}
 nameif {interface_name}
 security-level 0
 ip address {wan.ip} {wan.netmask}
 bfd interval {Config.BFD_INTERFACE_TX} min_rx {Config.BFD_INTERFACE_RX} multiplier {Config.BFD_INTERFACE_MULT}
"""

        for tunnel in device.tunnel_interfaces:
            intf_name = f"SVTI-{device.location}-{tunnel.name}"
            config += f"""
interface {tunnel.name}
 nameif {intf_name}
 ip address {tunnel.local_ip} 255.255.255.248
 tunnel source interface outside-{tunnel.source_wan.name.lower().replace('/', '_')}
 tunnel destination {tunnel.destination_wan.ip}
 tunnel mode ipsec ipv4
 tunnel protection ipsec profile VPN-LAB-PROFILE
"""
        return config

    @staticmethod
    def _generate_crypto_config(device: Device) -> str:
        return f"""
! IPSec and IKEv2 Configuration
crypto ikev2 policy 1
 encryption aes-256
 integrity sha512 sha384 sha256
 group 21 20 14
 prf sha256
 lifetime seconds 86400

crypto ipsec ikev2 ipsec-proposal VPN-LAB
 protocol esp encryption aes-256
 protocol esp integrity sha-512

! VPN Group Policy Configuration
group-policy VPN-LAB-POLICY internal
group-policy VPN-LAB-POLICY attributes
 vpn-tunnel-protocol ikev2
 ipv6-tunnel-protocol none
 split-tunnel-policy tunnelall
 split-tunnel-network-list none
 default-domain none
 dns-server none
 dhcp-network-scope none

crypto ipsec profile VPN-LAB-PROFILE
 set ikev2 ipsec-proposal VPN-LAB
 set security-association lifetime seconds 1000

! Tunnel Group Configurations
{ConfigGenerator._generate_tunnel_groups(device)}
"""

    @staticmethod
    def _generate_tunnel_groups(device: Device) -> str:
        config = ""
        for tunnel in device.tunnel_interfaces:
            config += f"""
tunnel-group {tunnel.destination_wan.ip} type ipsec-l2l
tunnel-group {tunnel.destination_wan.ip} general-attributes
 default-group-policy VPN-LAB-POLICY
tunnel-group {tunnel.destination_wan.ip} ipsec-attributes
 ikev2 remote-authentication pre-shared-key {device.encryption_key}
 ikev2 local-authentication pre-shared-key {device.encryption_key}
tunnel-group {tunnel.destination_wan.ip} ikev2-ipsec-attributes
 isakmp keepalive threshold 15 retry 3
"""
        return config

    @staticmethod
    def _generate_bgp_config(device: Device) -> str:
        config = f"""
! BGP Configuration
router bgp {device.bgp_as_numbers[0]}
 bgp log-neighbor-changes
 bgp bestpath compare-routerid

 community-list standard PRIMARY permit {Config.PRIMARY_COMMUNITY}
 community-list standard BACKUP permit {Config.BACKUP_COMMUNITY}
 
 address-family ipv4 unicast
"""
        for tunnel in device.tunnel_interfaces:
            bfd_type = "single-hop" if tunnel.is_primary else ""
            config += f"""  neighbor {tunnel.remote_ip} remote-as {tunnel.remote_as}
  neighbor {tunnel.remote_ip} ebgp-multihop 2
  neighbor {tunnel.remote_ip} fall-over bfd {bfd_type}
  neighbor {tunnel.remote_ip} activate
  neighbor {tunnel.remote_ip} send-community
  neighbor {tunnel.remote_ip} route-map {'PRIMARY-OUT' if tunnel.is_primary else 'BACKUP-OUT'} out
"""

        for network in device.local_networks:
            config += f"  network {network.ip} mask {network.netmask}\n"

        if local_ip := device.get_local_network_address()[0]:
            network = IPv4Network(f"{local_ip}/{device.local_networks[0].netmask}", strict=False)
            config += f"  network {network.network_address} mask {network.netmask}\n"

        config += """  no auto-summary
  no synchronization
 exit-address-family

! Route Maps for Path Selection
route-map PRIMARY-OUT permit 10
 set community """ + Config.PRIMARY_COMMUNITY + """

route-map BACKUP-OUT permit 10
 set community """ + Config.BACKUP_COMMUNITY + """
 set as-path prepend""" + "".join([f" {device.bgp_as_numbers[0]}" for _ in range(Config.AS_PREPEND_COUNT)]) + "\n"

        return config
