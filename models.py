from dataclasses import dataclass
from typing import List, Dict, Tuple
from ipaddress import IPv4Network
from config import Config

@dataclass
class WanInterface:
    name: str
    ip: str
    netmask: str
    gateway: str
    is_primary: bool = True
    
    def __hash__(self):
        return hash(self.ip)

@dataclass
class TunnelInterface:
    name: str
    source_wan: WanInterface
    destination_wan: WanInterface
    local_ip: str
    remote_ip: str
    is_primary: bool
    remote_device: str
    remote_as: str

class NetworkAddress:
    def __init__(self, address_string: str):
        if '/' in address_string:
            ip, prefix = address_string.split('/')
            self.ip = ip.strip()
            self.netmask = str(IPv4Network(f"0.0.0.0/{prefix}").netmask)
        else:
            parts = address_string.strip().split()
            self.ip = parts[0]
            self.netmask = parts[1] if len(parts) > 1 else "255.255.255.0"

    @property
    def network(self) -> str:
        return f"{self.ip} {self.netmask}"

    @property
    def network_address(self) -> str:
        return str(IPv4Network(f"{self.ip}/{self.netmask}", strict=False).network_address)

class Device:
    def __init__(self, row: Dict):
        self.name = row['device_name']
        self.site_id = int(row['site_id'])
        self.location = row['location']
        self.is_hub = False
        self._track_counter = Config.TRACK_BASE
        self._tunnel_counter = 0
        self.base_tunnel_number = (self.site_id * 100) % 10000

        self.wan_interfaces = []
        self.tunnel_interfaces = []
        self.bgp_as_numbers = self._parse_csv_list(row['bgp_as_number'])
        self.bgp_neighbor_as = self._parse_csv_list(row['bgp_neighbor_as'])
        self.local_networks = [NetworkAddress(net) for net in self._parse_csv_list(row['local_networks'])]
        self.encryption_key = row.get('encryption_key', 'cisco123')
        
        self._initialize_wan_interfaces(row)

    def _initialize_wan_interfaces(self, row: Dict):
        wan_ips = self._parse_csv_list(row['wan_ips'])
        wan_ints = self._parse_csv_list(row['wan_interfaces'])
        wan_gateways = self._parse_csv_list(row['wan_gateways'])
        
        for i, (ip, intf, gw) in enumerate(zip(wan_ips, wan_ints, wan_gateways)):
            net = NetworkAddress(ip)
            self.wan_interfaces.append(WanInterface(
                name=intf,
                ip=net.ip,
                netmask=net.netmask,
                gateway=gw,
                is_primary=(i == 0)
            ))

    @staticmethod
    def _parse_csv_list(value: str) -> List[str]:
        return [item.strip() for item in value.split(',') if item.strip()]

    def generate_tunnel_name(self) -> str:
        tunnel_number = self.base_tunnel_number + self._tunnel_counter
        if tunnel_number > 10000:
            raise ValueError(f"Tunnel number {tunnel_number} exceeds maximum allowed value of 10000")
        tunnel_name = f"tunnel{tunnel_number}"
        self._tunnel_counter += 1
        return tunnel_name

    def get_local_network_address(self) -> Tuple[str, str]:
        if self.local_networks:
            network = IPv4Network(f"{self.local_networks[0].ip}/{self.local_networks[0].netmask}", strict=False)
            return str(list(network.hosts())[0]), str(network.netmask)
        return None, None

    def generate_track_id(self) -> int:
        track_id = self._track_counter
        self._track_counter += 1
        return track_id
    
class InternetRouter:
    def __init__(self, name: str, as_number: str):
        self.name = name
        self.as_number = as_number
        self.interfaces = []

    def add_interface(self, name: str, network: NetworkAddress, gateway: str):
        self.interfaces.append({
            'name': name,
            'ip': gateway,
            'netmask': network.netmask,
            'network': network.ip
        })

    @staticmethod
    def generate_config(router: 'InternetRouter') -> str:
        config = f"""!
! Configuration for {router.name}
! AS Number: {router.as_number}
!
"""
        # Interface configuration
        for idx, intf in enumerate(router.interfaces, 1):
            config += f"""
interface GigabitEthernet0/{idx}
 description WAN Interface for {intf['network']}
 ip address {intf['ip']} {intf['netmask']}
 no shutdown
"""
        
        # BGP configuration
        config += f"""
router bgp {router.as_number}
 bgp log-neighbor-changes
 bgp bestpath compare-routerid
"""
        
        # Add networks to BGP
        for intf in router.interfaces:
            config += f" network {intf['network']} mask {intf['netmask']}\n"
            
        return config