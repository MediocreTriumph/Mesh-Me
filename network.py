from typing import List, Optional, Tuple
from itertools import product
from ipaddress import IPv4Network
from models import Device, TunnelInterface, WanInterface
from config import Config, NetworkTopology

class TunnelAddressManager:
    def __init__(self, network: str = Config.TUNNEL_NETWORK):
        self.base_network = IPv4Network(network)
        self.subnets = list(self.base_network.subnets(new_prefix=29))
        self.current_subnet_index = 0
        self.allocated_pairs = {}

    def get_tunnel_pair(self, wan1: str, wan2: str) -> Tuple[str, str]:
        key = tuple(sorted([wan1, wan2]))
        
        if key in self.allocated_pairs:
            pair = self.allocated_pairs[key]
            return (pair[0], pair[1]) if wan1 == key[0] else (pair[1], pair[0])

        if self.current_subnet_index >= len(self.subnets):
            raise ValueError("No more tunnel IP addresses available!")

        subnet = self.subnets[self.current_subnet_index]
        hosts = list(subnet.hosts())
        self.current_subnet_index += 1

        pair = (str(hosts[0]), str(hosts[1]))
        self.allocated_pairs[key] = pair
        
        return pair if wan1 == key[0] else (pair[1], pair[0])

class NetworkBuilder:
    def __init__(self, devices: List[Device], topology_type: str, hub_sites: Optional[List[str]] = None):
        self.devices = devices
        self.topology_type = topology_type
        self.hub_sites = hub_sites or []
        self.tunnel_manager = TunnelAddressManager()

        if topology_type == NetworkTopology.HUB_SPOKE and not hub_sites:
            raise ValueError("Hub sites must be specified for hub-spoke topology")

        for device in self.devices:
            device.is_hub = device.name in self.hub_sites

    def build(self):
        if self.topology_type == NetworkTopology.FULL_MESH:
            self._create_full_mesh()
        else:
            self._create_hub_spoke()

    def _create_full_mesh(self):
        for device1, device2 in product(self.devices, self.devices):
            if device1.name >= device2.name:
                continue
            self._create_device_pair_tunnels(device1, device2)

    def _create_hub_spoke(self):
        hub_devices = [d for d in self.devices if d.is_hub]
        spoke_devices = [d for d in self.devices if not d.is_hub]

        for hub1, hub2 in product(hub_devices, hub_devices):
            if hub1.name >= hub2.name:
                continue
            self._create_device_pair_tunnels(hub1, hub2)

        for hub, spoke in product(hub_devices, spoke_devices):
            self._create_device_pair_tunnels(hub, spoke)

    def _create_device_pair_tunnels(self, device1: Device, device2: Device):
        for wan1, wan2 in product(device1.wan_interfaces, device2.wan_interfaces):
            local_ip, remote_ip = self.tunnel_manager.get_tunnel_pair(wan1.ip, wan2.ip)
            
            device1.tunnel_interfaces.append(TunnelInterface(
                name=device1.generate_tunnel_name(),
                source_wan=wan1,
                destination_wan=wan2,
                local_ip=local_ip,
                remote_ip=remote_ip,
                is_primary=wan1.is_primary and wan2.is_primary,
                remote_device=device2.name,
                remote_as=device2.bgp_as_numbers[0]
            ))
            
            device2.tunnel_interfaces.append(TunnelInterface(
                name=device2.generate_tunnel_name(),
                source_wan=wan2,
                destination_wan=wan1,
                local_ip=remote_ip,
                remote_ip=local_ip,
                is_primary=wan1.is_primary and wan2.is_primary,
                remote_device=device1.name,
                remote_as=device1.bgp_as_numbers[0]
            ))