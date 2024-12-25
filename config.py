# config.py

class Config:
    PRIMARY_COMMUNITY = "65000:100"
    BACKUP_COMMUNITY = "65000:200"
    AS_PREPEND_COUNT = 3
    TUNNEL_BASE = 100
    TUNNEL_NETWORK = "172.26.0.0/15"
    INTERNET_ROUTER_NAME = "INTERNET-RTR"
    INTERNET_ROUTER_AS = "65000"
    SLA_FREQUENCY = 5
    SLA_TIMEOUT = 1
    SLA_THRESHOLD = 2
    TRACK_BASE = 100
    BFD_TEMPLATE_MULTI_TX = 100
    BFD_TEMPLATE_MULTI_RX = 100
    BFD_TEMPLATE_MULTI_MULT = 3
    BFD_TEMPLATE_SINGLE_TX = 50
    BFD_TEMPLATE_SINGLE_RX = 50
    BFD_TEMPLATE_SINGLE_MULT = 3
    BFD_INTERFACE_TX = 100
    BFD_INTERFACE_RX = 100
    BFD_INTERFACE_MULT = 5

class NetworkTopology:
    FULL_MESH = "full"
    HUB_SPOKE = "hub_spoke"
    PEER_TO_PEER = "peer"