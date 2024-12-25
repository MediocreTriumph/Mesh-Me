from typing import Set
import csv
from pathlib import Path

def validate_csv_headers(file_path: str) -> bool:
    required_headers: Set[str] = {
        'device_name', 'site_id', 'location', 'wan_ips', 'wan_interfaces',
        'wan_gateways', 'local_networks', 'bgp_as_number', 'bgp_neighbor_as'
    }
    
    try:
        with open(file_path, 'r') as f:
            headers = set(next(csv.reader(f), []))
            
        missing_headers = required_headers - headers
        if missing_headers:
            raise ValueError(f"Missing required headers: {', '.join(missing_headers)}")
        return True
    except Exception as e:
        raise ValueError(f"Error validating CSV headers: {e}")