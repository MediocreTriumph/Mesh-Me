# gui.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import csv
from typing import List
from models import Device, NetworkAddress, InternetRouter
from network import NetworkBuilder
from generators import ConfigGenerator
from config import NetworkTopology, Config
from utils import validate_csv_headers

class Application:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Mesh Network Configuration Generator")
        self.setup_ui()

    def setup_ui(self):
        # File selection
        file_frame = ttk.Frame(self.root, padding="10")
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(file_frame, text="Select CSV File", command=self.select_file).grid(row=0, column=0, padx=5)
        self.file_label = ttk.Label(file_frame, text="No file selected")
        self.file_label.grid(row=0, column=1, padx=5)

        # Topology selection
        topology_frame = ttk.Frame(self.root, padding="10")
        topology_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.topology_var = tk.StringVar(value=NetworkTopology.FULL_MESH)
        ttk.Radiobutton(topology_frame, text="Full Mesh", variable=self.topology_var, 
                       value=NetworkTopology.FULL_MESH, command=self.toggle_selection_frames).grid(row=0, column=0, padx=5)
        ttk.Radiobutton(topology_frame, text="Hub-Spoke", variable=self.topology_var,
                       value=NetworkTopology.HUB_SPOKE, command=self.toggle_selection_frames).grid(row=0, column=1, padx=5)
        ttk.Radiobutton(topology_frame, text="Peer to Peer", variable=self.topology_var,
                       value=NetworkTopology.PEER_TO_PEER, command=self.toggle_selection_frames).grid(row=0, column=2, padx=5)

        # Device selection
        self.device_frame = ttk.Frame(self.root, padding="10")
        self.device_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        ttk.Label(self.device_frame, text="Select Devices to Configure:").grid(row=0, column=0, sticky=tk.W)
        self.device_listbox = tk.Listbox(self.device_frame, selectmode=tk.MULTIPLE, height=5)
        self.device_listbox.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.device_frame.grid_remove()  # Hide by default

        # Hub selection
        self.hub_frame = ttk.Frame(self.root, padding="10")
        self.hub_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        ttk.Label(self.hub_frame, text="Select Hub Sites:").grid(row=0, column=0, sticky=tk.W)
        self.hub_listbox = tk.Listbox(self.hub_frame, selectmode=tk.MULTIPLE, height=5)
        self.hub_listbox.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.hub_frame.grid_remove()

        # Internet Router checkbox
        self.include_internet = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.root, text="Include Internet Router Configuration", 
                       variable=self.include_internet).grid(row=4, column=0, pady=5)

        # Generate button
        ttk.Button(self.root, text="Generate Configuration", 
                  command=self.generate_config).grid(row=5, column=0, pady=10)

    def select_file(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if filename:
            self.csv_file = filename
            self.file_label.config(text=Path(filename).name)
            self.load_devices()

    def load_devices(self):
        try:
            if not validate_csv_headers(self.csv_file):
                raise ValueError("Invalid CSV headers")
                
            with open(self.csv_file, 'r') as f:
                reader = csv.DictReader(f)
                self.devices = [Device(row) for row in reader]
            
            # Clear and populate both listboxes
            self.hub_listbox.delete(0, tk.END)
            self.device_listbox.delete(0, tk.END)
            for device in self.devices:
                self.hub_listbox.insert(tk.END, device.name)
                self.device_listbox.insert(tk.END, device.name)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error loading CSV file: {str(e)}")

    def toggle_selection_frames(self):
        topology = self.topology_var.get()
        if topology == NetworkTopology.HUB_SPOKE:
            self.hub_frame.grid()
            self.device_frame.grid_remove()
        elif topology == NetworkTopology.PEER_TO_PEER:
            self.device_frame.grid()
            self.hub_frame.grid_remove()
        else:  # FULL_MESH
            self.hub_frame.grid_remove()
            self.device_frame.grid_remove()

    def get_selected_devices(self) -> List[str]:
        selection = self.device_listbox.curselection()
        return [self.device_listbox.get(i) for i in selection]

    def get_selected_hubs(self) -> List[str]:
        selection = self.hub_listbox.curselection()
        return [self.hub_listbox.get(i) for i in selection]

    def validate_input(self) -> bool:
        if not hasattr(self, 'csv_file'):
            messagebox.showerror("Error", "Please select a CSV file")
            return False
            
        topology = self.topology_var.get()
        
        if topology == NetworkTopology.PEER_TO_PEER:
            selected_devices = self.get_selected_devices()
            if not selected_devices:
                messagebox.showerror("Error", "Please select devices")
                return False
            if len(selected_devices) != 2:
                messagebox.showerror("Error", "Please select exactly two devices")
                return False
        elif topology == NetworkTopology.HUB_SPOKE and not self.get_selected_hubs():
            messagebox.showerror("Error", "Please select at least one hub site")
            return False
            
        return True

    def generate_config(self):
        if not self.validate_input():
            return

        try:
            topology = self.topology_var.get()
            hub_sites = self.get_selected_hubs() if topology == NetworkTopology.HUB_SPOKE else None
            
            # For peer-to-peer, only use selected devices
            if topology == NetworkTopology.PEER_TO_PEER:
                selected_devices = self.get_selected_devices()
                devices_to_configure = [d for d in self.devices if d.name in selected_devices]
            else:
                devices_to_configure = self.devices
            
            network_builder = NetworkBuilder(devices_to_configure, topology, hub_sites)
            network_builder.build()
            
            output_dir = filedialog.askdirectory(title="Select Output Directory")
            if not output_dir:
                return
                
            for device in devices_to_configure:
                config = ConfigGenerator.generate_device_config(device)
                output_file = Path(output_dir) / f"{device.name}_config.txt"
                with open(output_file, 'w') as f:
                    f.write(config)

            if self.include_internet.get():
                self._generate_internet_router_config(output_dir, devices_to_configure)
            
            messagebox.showinfo("Success", "Configuration files generated successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error generating configuration: {str(e)}")

    def _generate_internet_router_config(self, output_dir: str, devices_to_configure=None):
        internet_router = InternetRouter(Config.INTERNET_ROUTER_NAME, Config.INTERNET_ROUTER_AS)
        
        # Use either the selected devices or all devices
        devices = devices_to_configure if devices_to_configure else self.devices
        
        for device in devices:
            for wan in device.wan_interfaces:
                net = NetworkAddress(f"{wan.ip} {wan.netmask}")
                internet_router.add_interface(f"WAN-{device.name}", net, wan.gateway)
    
        config = InternetRouter.generate_config(internet_router)
        output_file = Path(output_dir) / f"{Config.INTERNET_ROUTER_NAME}_config.txt"
        with open(output_file, 'w') as f:
            f.write(config)

    def run(self):
        self.root.mainloop()