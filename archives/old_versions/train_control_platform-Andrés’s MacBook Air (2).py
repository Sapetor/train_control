"""
Train Control Platform - Unified ESP32 PID Control System
=========================================================

This platform combines UDP data collection and Dash dashboard into a single
application with advanced network configuration capabilities.

Features:
- Automatic network interface detection
- User-selectable IP addresses for complex network environments
- Integrated UDP receiver and Dash dashboard
- Real-time PID control and data visualization
- ESP32 setup guidance

Author: Generated for UAI SIMU Project
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import csv
import socket
import threading
import queue
import time
import os
import glob
import traceback
from datetime import datetime
import psutil
import json
import uuid

# =============================================================================
# Configuration Constants
# =============================================================================

# Network Configuration
DEFAULT_UDP_PORT = 5555
DEFAULT_MQTT_PORT = 1883
DEFAULT_MQTT_BROKER = '127.0.0.1'
UDP_TIMEOUT = 1.0  # seconds
MQTT_KEEPALIVE = 60  # seconds

# Dashboard Configuration
DASHBOARD_HOST = '127.0.0.1'
DASHBOARD_PORT = 8050
DATA_REFRESH_INTERVAL = 1000  # milliseconds
MQTT_STATUS_REFRESH_INTERVAL = 200  # milliseconds

# PID Control Limits
PID_KP_MAX = 250
PID_KI_MAX = 150
PID_KD_MAX = 150
REFERENCE_MIN = 1
REFERENCE_MAX = 100

# File Configuration
NETWORK_CONFIG_FILE = 'network_config.json'
CSV_FILE_PREFIX = 'experiment_'
MAX_DATA_QUEUE_SIZE = 1000

# MQTT Topics
MQTT_TOPICS = {
    # PID Control Topics
    'sync': 'trenes/sync',
    'kp': 'trenes/carroD/p',
    'ki': 'trenes/carroD/i',
    'kd': 'trenes/carroD/d',
    'reference': 'trenes/ref',
    'kp_status': 'trenes/carroD/p/status',
    'ki_status': 'trenes/carroD/i/status',
    'kd_status': 'trenes/carroD/d/status',
    'ref_status': 'trenes/carroD/ref/status',
    'request_params': 'trenes/carroD/request_params',
    
    # Step Response Topics
    'step_sync': 'trenes/step/sync',
    'step_amplitude': 'trenes/step/amplitude',
    'step_time': 'trenes/step/time',
    'step_direction': 'trenes/step/direction',
    'step_vbatt': 'trenes/step/vbatt',
    'step_amplitude_status': 'trenes/step/amplitude/status',
    'step_time_status': 'trenes/step/time/status',
    'step_direction_status': 'trenes/step/direction/status',
    'step_vbatt_status': 'trenes/step/vbatt/status',
    'step_request_params': 'trenes/step/request_params'
}

# =============================================================================
# Classes
# =============================================================================

class MQTTParameterSync:
    """Handles MQTT communication for PID parameter synchronization"""

    def __init__(self):
        self.client = None
        self.broker_ip = DEFAULT_MQTT_BROKER
        self.broker_port = DEFAULT_MQTT_PORT
        self.connected = False

        # Store confirmed parameter values from Arduino
        self.confirmed_params = {
            'kp': None,
            'ki': None,
            'kd': None,
            'reference': None
        }
        
        # Store confirmed step response parameters
        self.step_confirmed_params = {
            'amplitude': None,
            'time': None,
            'direction': None,
            'vbatt': None
        }

        # Callback for when parameters are confirmed
        self.on_params_updated = None
        self.on_step_params_updated = None

    def connect(self, broker_ip, broker_port=None):
        """Connect to MQTT broker"""
        try:
            self.broker_ip = broker_ip
            self.broker_port = broker_port or DEFAULT_MQTT_PORT

            self.client = mqtt.Client()
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message

            self.client.connect(broker_ip, self.broker_port, MQTT_KEEPALIVE)
            self.client.loop_start()
            print(f"MQTT parameter sync connected to {broker_ip}:{broker_port}")
            return True
        except Exception as e:
            print(f"MQTT parameter sync failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False

    def _on_connect(self, client, userdata, flags, rc):
        """Called when MQTT client connects"""
        if rc == 0:
            self.connected = True
            timestamp = time.strftime('%H:%M:%S')
            print(f"[MQTT {timestamp}] Parameter sync connected successfully")
            # Subscribe to parameter confirmation topics
            topics = [
                MQTT_TOPICS['kp_status'],
                MQTT_TOPICS['ki_status'],
                MQTT_TOPICS['kd_status'],
                MQTT_TOPICS['ref_status']
            ]
            for topic in topics:
                result = client.subscribe(topic)
                print(f"[MQTT {timestamp}] Subscribed to {topic}, result: {result}")

            # Subscribe to step response confirmation topics
            step_topics = [
                MQTT_TOPICS['step_amplitude_status'],
                MQTT_TOPICS['step_time_status'],
                MQTT_TOPICS['step_direction_status'],
                MQTT_TOPICS['step_vbatt_status']
            ]
            for topic in step_topics:
                result = client.subscribe(topic)
                print(f"[MQTT {timestamp}] Subscribed to {topic}, result: {result}")
            
            # Request current parameters from ESP32 by publishing a "request" signal
            print(f"[MQTT {timestamp}] Requesting current parameters from ESP32...")
            client.publish(MQTT_TOPICS['request_params'], "1")
            client.publish(MQTT_TOPICS['step_request_params'], "1")
        else:
            print(f"[MQTT ERROR] Parameter sync failed with code {rc}")

    def _on_message(self, client, userdata, msg):
        """Called when a message is received"""
        try:
            topic = msg.topic
            value = float(msg.payload.decode())

            timestamp = time.strftime('%H:%M:%S')
            print(f"[MQTT {timestamp}] Received message: {topic} = {value}")

            # Update confirmed parameters based on topic
            if topic == MQTT_TOPICS['kp_status']:
                self.confirmed_params['kp'] = value
                print(f"[MQTT {timestamp}] Updated Kp to {value}")
            elif topic == MQTT_TOPICS['ki_status']:
                self.confirmed_params['ki'] = value
                print(f"[MQTT {timestamp}] Updated Ki to {value}")
            elif topic == MQTT_TOPICS['kd_status']:
                self.confirmed_params['kd'] = value
                print(f"[MQTT {timestamp}] Updated Kd to {value}")
            elif topic == MQTT_TOPICS['ref_status']:
                self.confirmed_params['reference'] = value
                print(f"[MQTT {timestamp}] Updated Reference to {value}")
            # Handle step response parameter confirmations
            elif topic == MQTT_TOPICS['step_amplitude_status']:
                self.step_confirmed_params['amplitude'] = value
                print(f"[MQTT {timestamp}] Updated Step Amplitude to {value}")
            elif topic == MQTT_TOPICS['step_time_status']:
                self.step_confirmed_params['time'] = value
                print(f"[MQTT {timestamp}] Updated Step Time to {value}")
            elif topic == MQTT_TOPICS['step_direction_status']:
                self.step_confirmed_params['direction'] = int(value)
                print(f"[MQTT {timestamp}] Updated Step Direction to {int(value)}")
            elif topic == MQTT_TOPICS['step_vbatt_status']:
                self.step_confirmed_params['vbatt'] = value
                print(f"[MQTT {timestamp}] Updated Step VBatt to {value}")
            else:
                print(f"[MQTT {timestamp}] Unknown status topic: {topic}")

            print(f"[MQTT {timestamp}] Current confirmed params: {self.confirmed_params}")
            print(f"[MQTT {timestamp}] Current step confirmed params: {self.step_confirmed_params}")

            # Notify dashboard of parameter update
            if self.on_params_updated:
                print(f"[MQTT {timestamp}] Calling dashboard callback...")
                self.on_params_updated(self.confirmed_params.copy())
            else:
                print(f"[MQTT {timestamp}] No dashboard callback set!")
            
            # Push via WebSocket if available
            if hasattr(self, 'websocket_callback') and self.websocket_callback:
                try:
                    self.websocket_callback({'type': 'mqtt_update', 'params': self.confirmed_params})
                except:
                    pass
            
            # Push via WebSocket if available
            if hasattr(self, 'websocket_callback') and self.websocket_callback:
                try:
                    self.websocket_callback({'type': 'mqtt_update', 'params': self.confirmed_params})
                except:
                    pass

        except Exception as e:
            print(f"[MQTT ERROR] Error processing parameter confirmation: {e}")
            traceback.print_exc()

    def get_confirmed_params(self):
        """Get currently confirmed parameter values"""
        return self.confirmed_params.copy()


class NetworkManager:
    """Handles network interface detection and configuration"""

    def __init__(self):
        self.interfaces = {}
        self.selected_ip = None
        self.mqtt_broker_ip = '127.0.0.1'  # Default to localhost
        self.udp_port = 5555
        self.mqtt_port = 1883
        self.language = 'es'  # Default language
        self.config_file = 'network_config.json'
        self.load_config()

    def detect_interfaces(self):
        """Detect all available network interfaces and their IP addresses"""
        interfaces = {}

        try:
            # Get all network interfaces
            for interface_name, interface_addresses in psutil.net_if_addrs().items():
                for address in interface_addresses:
                    if address.family == socket.AF_INET:  # IPv4
                        ip = address.address
                        # Skip loopback and invalid IPs
                        if ip and ip != '127.0.0.1' and not ip.startswith('169.254'):
                            # Classify interface type
                            interface_type = self._classify_interface(interface_name, ip)
                            interfaces[f"{interface_type}: {ip}"] = {
                                'ip': ip,
                                'interface': interface_name,
                                'type': interface_type
                            }
        except Exception as e:
            print(f"Error detecting interfaces: {e}")
            # Fallback to basic detection
            interfaces["Default: 192.168.137.1"] = {
                'ip': '192.168.137.1',
                'interface': 'unknown',
                'type': 'Default'
            }

        self.interfaces = interfaces
        return interfaces

    def _classify_interface(self, interface_name, ip):
        """Classify interface type based on name and IP"""
        name_lower = interface_name.lower()

        if 'wifi' in name_lower or 'wlan' in name_lower or 'wireless' in name_lower:
            return 'WiFi'
        elif 'ethernet' in name_lower or 'eth' in name_lower:
            return 'Ethernet'
        elif 'vethernet' in name_lower or 'vmware' in name_lower or 'virtualbox' in name_lower:
            return 'Virtual'
        elif 'vlan' in name_lower:
            return 'VLAN'
        elif ip.startswith('192.168.137'):
            return 'Shared Network'
        elif ip.startswith('192.168.1'):
            return 'Home Network'
        elif ip.startswith('10.'):
            return 'Corporate'
        else:
            return 'Network'

    def get_interface_options(self):
        """Get formatted options for dropdown"""
        if not self.interfaces:
            self.detect_interfaces()

        options = [{'label': name, 'value': info['ip']}
                  for name, info in self.interfaces.items()]
        return options

    def set_selected_ip(self, ip):
        """Set the selected IP address"""
        self.selected_ip = ip
        self.save_config()
        return ip

    def load_config(self):
        """Load network configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.selected_ip = config.get('selected_ip')
                    self.mqtt_broker_ip = config.get('mqtt_broker_ip', '127.0.0.1')
                    self.udp_port = config.get('udp_port', 5555)
                    self.mqtt_port = config.get('mqtt_port', 1883)
                    self.language = config.get('language', 'es')
                    print(f"Loaded network config: IP={self.selected_ip}, Language={self.language}")
        except Exception as e:
            print(f"Error loading network config: {e}")

    def save_config(self):
        """Save network configuration to file"""
        try:
            config = {
                'selected_ip': self.selected_ip,
                'mqtt_broker_ip': self.mqtt_broker_ip,
                'udp_port': self.udp_port,
                'mqtt_port': self.mqtt_port,
            'language': self.language
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"Saved network config: IP={self.selected_ip}, UDP:{self.udp_port}, MQTT:{self.mqtt_port}, Language={self.language}")
        except Exception as e:
            print(f"Error saving network config: {e}")

    def update_ports(self, udp_port, mqtt_port):
        """Update port configuration and save"""
        self.udp_port = udp_port or 5555
        self.mqtt_port = mqtt_port or 1883
        self.save_config()

    def set_language(self, language):
        """Set language preference and save"""
        self.language = language
        self.save_config()

    def auto_apply_config(self, data_manager, existing_udp_receiver):
        """Auto-apply saved configuration if available"""
        if self.selected_ip:
            # Check if the saved IP is still available
            current_interfaces = self.detect_interfaces()
            available_ips = [info['ip'] for info in current_interfaces.values()]

            if self.selected_ip in available_ips:
                print(f"Auto-applying saved network config: {self.selected_ip}")

                # CSV file will be created by UDP receiver when it starts

                # Configure existing UDP receiver instead of creating new one
                existing_udp_receiver.ip = self.selected_ip
                existing_udp_receiver.port = self.udp_port
                success = existing_udp_receiver.start()

                return existing_udp_receiver, success
            else:
                print(f"Saved IP {self.selected_ip} no longer available, please reconfigure")
                self.selected_ip = None
                self.save_config()

        return None, False

class DataManager:
    """Manages thread-safe data sharing between UDP receiver and dashboard"""

    def __init__(self):
        self.data_queue = queue.Queue(maxsize=1000)
        self.latest_data = {}
        self.experiment_active = False
        self._csv_file = None  # Private variable
        self.data_lock = threading.Lock()
        self.initialized = False

        # Data reception statistics
        self.total_packets = 0
        self.last_packet_time = None
        self.connection_status = "Waiting for data"
        
        # WebSocket callback for push notifications
        self.websocket_callback = None
        
        # WebSocket callback for push notifications
        self.websocket_callback = None

    @property
    def csv_file(self):
        return self._csv_file

    @csv_file.setter
    def csv_file(self, value):
        self._csv_file = value

    def set_csv_file(self, filename):
        """Set the CSV file for data storage"""
        self.csv_file = filename
        self.initialized = True
        # Create CSV with headers
        try:
            with open(filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['time_event', 'input', 'referencia', 'error', 'kp', 'ki', 'kd', 'output_PID'])
        except Exception as e:
            print(f"Error creating CSV file: {e}")
            self.initialized = False

    def add_data(self, data_string):
        """Add new data from UDP receiver"""
        try:
            with self.data_lock:
                # Update statistics
                self.total_packets += 1
                self.last_packet_time = datetime.now()
                self.connection_status = "Connected"

                # Parse data - ESP32 sends: time_event,input,referencia,error,kp,ki,kd,output_PID
                data_parts = data_string.strip().split(',')
                if len(data_parts) >= 2:
                    timestamp = data_parts[0]
                    distance = float(data_parts[1]) if len(data_parts) > 1 else 0

                    # Parse additional fields if available
                    referencia = float(data_parts[2]) if len(data_parts) > 2 else None
                    error = float(data_parts[3]) if len(data_parts) > 3 else None
                    kp = float(data_parts[4]) if len(data_parts) > 4 else None
                    ki = float(data_parts[5]) if len(data_parts) > 5 else None
                    kd = float(data_parts[6]) if len(data_parts) > 6 else None
                    output_pid = float(data_parts[7]) if len(data_parts) > 7 else None

                    self.latest_data = {
                        'timestamp': timestamp,
                        'distance': distance,
                        'referencia': referencia,
                        'error': error,
                        'kp': kp,
                        'ki': ki,
                        'kd': kd,
                        'output_pid': output_pid,
                        'full_data': data_string,
                        'packet_count': self.total_packets
                    }

                    # Add to queue for dashboard
                    if not self.data_queue.full():
                        self.data_queue.put(self.latest_data)
                    
                    # Push update via WebSocket
                    if self.websocket_callback:
                        try:
                            self.websocket_callback({'type': 'data_update', 'data': self.latest_data})
                        except:
                            pass  # Don't let WebSocket errors break data collection

                    # Write to CSV (always write if file is set, for real-time monitoring)
                    if self.csv_file:
                        try:
                            with open(self.csv_file, 'a', newline='') as file:
                                file.write(data_string + '\n')
                        except Exception as write_error:
                            print(f"CSV write error: {write_error}")

                    # Packet info is now displayed in the dashboard only

                else:
                    if self.total_packets % 100 == 1:  # Only show errors occasionally
                        print(f"Data format error - expected at least 2 fields, got {len(data_parts)}")

        except Exception as e:
            print(f"Data processing error: {e}")

    def get_latest_data(self):
        """Get the latest data for dashboard"""
        with self.data_lock:
            return self.latest_data.copy() if self.latest_data else {}

    def get_connection_stats(self):
        """Get connection statistics for dashboard"""
        with self.data_lock:
            # Check if connection is stale (no data for 5 seconds)
            if self.last_packet_time:
                time_since_last = (datetime.now() - self.last_packet_time).total_seconds()
                if time_since_last > 5:
                    status = self.dashboard.t('connection_lost') if hasattr(self, 'dashboard') else "Connection lost"
                else:
                    status = self.connection_status
            else:
                status = self.connection_status

            return {
                'status': status,
                'total_packets': self.total_packets,
                'last_packet_time': self.last_packet_time.strftime("%H:%M:%S") if self.last_packet_time else "Never",
                'experiment_active': self.experiment_active
            }

    def start_experiment(self):
        """Start data collection experiment"""
        self.experiment_active = True

    def stop_experiment(self):
        """Stop data collection experiment"""
        self.experiment_active = False


class StepResponseDataManager(DataManager):
    """Manages step response experiment data with different CSV format"""
    
    def __init__(self):
        super().__init__()
        self.step_active = False
    
    def create_step_csv(self):
        """Create a new step response CSV file with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"step_response_{timestamp}.csv"
        csv_path = os.path.join(os.getcwd(), filename)
        self.set_csv_file(csv_path)
        return csv_path
    
    def set_csv_file(self, filename):
        """Create CSV with step response headers"""
        self.csv_file = filename
        self.initialized = True
        try:
            with open(filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['time2sinc', 'time_event', 'motor_dir', 'v_batt', 
                               'output_G', 'step_input', 'PWM_input'])
            print(f"Created step response CSV: {filename}")
        except Exception as e:
            print(f"Error creating step response CSV: {e}")
            self.initialized = False
    
    def add_data(self, data_string):
        """Parse step response data format: time2sinc,time_event,motor_dir,v_batt,output_G,step_input,PWM_input"""
        try:
            with self.data_lock:
                # Update statistics
                self.total_packets += 1
                self.last_packet_time = datetime.now()
                self.connection_status = "Connected"
                
                # Parse step response data
                data_parts = data_string.strip().split(',')
                if len(data_parts) >= 7:
                    self.latest_data = {
                        'time2sinc': float(data_parts[0]),
                        'time_event': float(data_parts[1]),
                        'motor_dir': int(float(data_parts[2])),
                        'v_batt': float(data_parts[3]),
                        'output_G': float(data_parts[4]),
                        'step_input': float(data_parts[5]),
                        'PWM_input': float(data_parts[6]),
                        'full_data': data_string,
                        'packet_count': self.total_packets
                    }
                    
                    # Add to queue for dashboard
                    if not self.data_queue.full():
                        self.data_queue.put(self.latest_data)
                    
                    # Push update via WebSocket
                    if self.websocket_callback:
                        try:
                            self.websocket_callback({'type': 'step_data_update', 'data': self.latest_data})
                        except:
                            pass
                    
                    # Write to CSV
                    if self.csv_file:
                        try:
                            with open(self.csv_file, 'a', newline='') as file:
                                file.write(data_string + '\n')
                        except Exception as write_error:
                            print(f"Step CSV write error: {write_error}")
                else:
                    if self.total_packets % 100 == 1:
                        print(f"Step data format error - expected 7 fields, got {len(data_parts)}")
        
        except Exception as e:
            print(f"Step data processing error: {e}")


class UDPReceiver:
    """Background UDP data receiver"""

    def __init__(self, data_manager, ip='0.0.0.0', port=5555):
        self.data_manager = data_manager
        self.ip = ip
        self.port = port
        self.socket = None
        self.running = False
        self.thread = None
        print(f"UDPReceiver initialized: IP={ip}, Port={port}")

    def set_data_manager(self, data_manager):
        """Switch to a different data manager (e.g., for step response mode)"""
        self.data_manager = data_manager
        print(f"UDP receiver now using {data_manager.__class__.__name__}")

    def start(self):
        """Start UDP receiver in background thread"""
        if self.running:
            return False

        try:
            # Create CSV file for this session if needed
            current_csv = self.data_manager.csv_file
            if current_csv and os.path.exists(current_csv):
                print(f"Using existing CSV file: {os.path.basename(current_csv)}")
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_filename = f"experiment_{timestamp}.csv"
                csv_path = os.path.join(os.getcwd(), csv_filename)
                print(f"Created new CSV file: {os.path.basename(csv_path)}")
                self.data_manager.set_csv_file(csv_path)

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.ip, self.port))
            self.socket.settimeout(1.0)  # 1 second timeout for graceful shutdown
            self.running = True

            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()

            print(f"UDP receiver started on {self.ip}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ Error starting UDP receiver on {self.ip}:{self.port}: {e}")
            return False

    def stop(self):
        """Stop UDP receiver"""
        self.running = False
        if self.socket:
            self.socket.close()
        if self.thread:
            self.thread.join(timeout=2)

    def _receive_loop(self):
        """Main UDP receiving loop"""
        print(f"UDP receiver thread started, listening on {self.ip}:{self.port}")
        timeout_count = 0

        while self.running:
            try:
                data, addr = self.socket.recvfrom(1024)
                data_string = data.decode('utf-8')
                # Data processing now handled in DataManager with reduced console output
                self.data_manager.add_data(data_string)
                timeout_count = 0  # Reset timeout counter on successful receive

            except socket.timeout:
                timeout_count += 1
                # Print status every 30 timeouts (30 seconds)
                if timeout_count % 30 == 0:
                    print(f"UDP receiver still listening on {self.ip}:{self.port} (no data for {timeout_count}s)")
                continue  # Keep running, just timeout
            except OSError as e:
                # Socket was closed, exit gracefully
                if self.running:
                    print(f"UDP socket closed: {e}")
                break
            except Exception as e:
                if self.running:  # Only print error if we're supposed to be running
                    print(f"UDP receive error: {e}")
                break
        print("UDP receiver stopped")

class TrainControlDashboard:
    """Enhanced Dash dashboard with network configuration and language support"""

    def __init__(self, network_manager, data_manager, udp_receiver):
        self.network_manager = network_manager
        self.data_manager = data_manager
        self.udp_receiver = udp_receiver
        
        # Track which experiment mode is active ('pid' or 'step')
        self.experiment_mode = 'pid'  # Default to PID mode
        
        # Create step response data manager
        self.step_data_manager = StepResponseDataManager()
        

        # Initialize current language from network manager

        self.current_language = self.network_manager.language

        

        # Initialize MQTT parameter sync
        self.mqtt_sync = MQTTParameterSync()
        self.confirmed_params = {
            'kp': 0.0,
            'ki': 0.0,
            'kd': 0.0,
            'reference': 10.0
        }

        # Set up callback for when parameters are confirmed by Arduino
        self.mqtt_sync.on_params_updated = self._on_params_confirmed

        # Store zoom state to preserve user zoom when data updates (separate for each graph)
        self.zoom_state = {
            'realtime-graph': {
                'xaxis.range[0]': None,
                'xaxis.range[1]': None,
                'yaxis.range[0]': None,
                'yaxis.range[1]': None,
                'user_has_zoomed': False
            },
            'historical-graph': {
                'xaxis.range[0]': None,
                'xaxis.range[1]': None,
                'yaxis.range[0]': None,
                'yaxis.range[1]': None,
                'user_has_zoomed': False
            }
        }

        # Language dictionaries
        self.translations = {
            'es': {
                'title': 'Sistema de Control PID para Tren',
                'subtitle': 'Plataforma unificada para experimentos de control de tren basados en ESP32 con configuración de red',
                'network_tab': '🔧 Configuración de Red',
                'control_tab': '🎛️ Control PID',
                'data_tab': '📊 Visualización de Datos',
                'network_config': 'Configuración de Red',
                'welcome': '👋 ¡Bienvenido! Comience configurando su conexión de red:',
                'select_interface': '1. Seleccione su interfaz de red del menú desplegable',
                'note_ip': '2. Anote la dirección IP para configurar en su ESP32',
                'apply_config': '3. Haga clic en "Aplicar Configuración"',
                'auto_saved': '4. ¡Su configuración se guarda automáticamente y se restaurará la próxima vez!',
                'select_network': 'Seleccionar Interfaz de Red:',
                'refresh_interfaces': 'Actualizar Interfaces',
                'apply_configuration': 'Aplicar Configuración',
                'udp_port': 'Puerto UDP:',
                'mqtt_port': 'Puerto MQTT:',
                'status': 'Estado',
                'ip_address': 'Dirección IP',
                'esp32_setup': 'Configuración ESP32',
                'pid_control': 'Control PID',
                'start_experiment': 'Iniciar Experimento',
                'stop_experiment': 'Detener Experimento',
                'kp_param': 'Parámetro Kp',
                'ki_param': 'Parámetro Ki',
                'kd_param': 'Parámetro Kd',
                'reference_distance': 'Distancia de Referencia (cm)',
                'realtime_graph': 'Gráfico en Tiempo Real',
                'historical_graph': 'Gráfico Histórico',
                'connection_status': 'Estado de Conexión',
                'total_packets': 'Total de Paquetes',
                'configure_network': 'Configure la red en la pestaña \'Red\' para comenzar',
                'distance_data_realtime': 'Datos del Sensor de Distancia en Tiempo Real',
                'time': 'Tiempo',
                'distance_cm': 'Distancia (cm)',
                'experiment_files_not_found': 'No se encontraron archivos de experimento - inicie el receptor UDP',
                'data_format_problem': 'Problema de formato de datos - columnas esperadas: time_event, input',
                'waiting_esp32_data': 'Esperando datos del ESP32... (archivo CSV vacío)',
                'waiting_data_file': 'Esperando datos...',
                'data_read_error': 'Error leyendo datos',
                'points': 'puntos',
                'csv_file_path': 'Archivo CSV',
                'language': 'Idioma',
                'configure_network_first': 'Configure la red primero para habilitar el registro de datos',
                'no_active_experiment': 'No hay experimento activo',
                'waiting_for_data': 'Esperando datos del ESP32...',
                'experiment_started': '¡Experimento iniciado!',
                'experiment_stopped': '¡Experimento detenido!',
                'configure_network_warning': '¡Configure la red primero!',
                'configuration_applied': '¡Configuración aplicada y guardada!',
                'udp_start_failed': 'Error al iniciar el receptor UDP',
                'connected': 'Conectado',
                'connection_lost': 'Conexión perdida',
                'receiving_data': 'Recibiendo datos',
                'waiting_for_data_status': 'Esperando datos',
                'packets': 'Paquetes',
                'last': 'Último',
                'never': 'Nunca',
                'status_unavailable': 'Estado no disponible',
                'download_csv': 'Descargar CSV',
                'download_experiment_data': 'Descargar Datos del Experimento',
                'no_data_to_download': 'No hay datos para descargar',
                'esp32_parameters': 'Parámetros ESP32',
                'esp32_confirmed_parameters': 'Parámetros ESP32 Confirmados',
                'esp32_waiting_parameters': 'ESP32: Esperando parámetros...',
                'network_not_configured': '⚠️ Red no configurada',
                'go_to_network_tab': 'Vaya a la pestaña Configuración de Red para configurar la conexión.',
                'esp32_connection_status': 'Estado de Conexión ESP32',
                'historical_data': 'Datos Históricos',
                'data_current_session': 'Datos de la sesión de experimento actual.',
                'data_storage': 'Almacenamiento de Datos',
                'total_packets_label': 'Total de Paquetes',
                'last_received': 'Último Recibido',
                'experiment_label': 'Experimento',
                'latest_data': 'Datos Más Recientes',
                'active': 'Activo',
                'stopped': 'Detenido',
                'welcome_network': '👋 ¡Bienvenido! Comience configurando su conexión de red:',
                'step_select_interface': '1. Seleccione su interfaz de red del menú desplegable a continuación',
                'step_note_ip': '2. Anote la dirección IP para configurar en su ESP32',
                'step_apply_config': '3. Haga clic en "Aplicar Configuración" para iniciar el sistema',
                'esp32_configuration': 'Configuración ESP32',
                'use_ip_address': 'Use esta dirección IP en su código ESP32 antes de flashear.',
                'port_configuration': 'Configuración de Puertos',
                'pid_parameters': 'Parámetros PID',
                'ip_address_to_configure': 'Dirección IP para configurar en ESP32:',
                'csv_file_path_label': 'Ruta del Archivo CSV:',
                'test_connection': 'Probar Conexión',
                'experiment_data_connection_status': 'Datos del Experimento y Estado de Conexión',
                'parameters_sent_esp32': 'Parámetros enviados al ESP32',
                'mqtt_communication_error': 'Error de comunicación MQTT',
                'parameters_configured': 'Parámetros configurados',
                'ready_to_start': 'Listo para iniciar experimento',
                'select_interface_placeholder': 'Seleccionar interfaz de red...',
                'mqtt_sync_not_available': 'MQTT sync no disponible',
                'connection_waiting_confirmation': 'Conectado, esperando confirmación...',
                'mqtt_not_connected': 'MQTT no conectado',
                'mqtt_not_available': 'MQTT: No disponible',
                'esp32_label': 'ESP32: ',
                'auto_loaded': 'Auto-cargado',
                'selected': 'Seleccionado',
                'interfaces_refreshed': 'Interfaces actualizadas',
                'network_interfaces_updated': 'Interfaces de red actualizadas',
                'select_an_interface': 'Seleccionar una interfaz',
                'configuration_applied_saved_mqtt': 'Configuración aplicada y guardada! MQTT sync habilitado.',
                'udp_started_mqtt_failed': 'UDP iniciado pero MQTT sync falló',
                'ready_apply_configuration': 'Listo para aplicar configuración',
                'current': 'Actual',
                'current_configuration_loaded': 'Configuración actual cargada',
                'no_interface_selected': 'Ninguna interfaz seleccionada',
                'configure_network_settings_above': 'Configure los ajustes de red arriba',
                'tab_not_found': 'Pestaña no encontrada',
                'pid_red_no_configurada': 'PID: Kp={kp:.1f}, Ki={ki:.1f}, Kd={kd:.1f}, Ref={ref}cm (Red no configurada)',
                'no_data_received': 'No se recibieron datos',
                'kp_label': 'Kp',
                'ki_label': 'Ki',
                'kd_label': 'Kd',
                'ref_label': 'Ref (cm)',
                'send_button': 'Enviar',
                'distance_label': 'Distancia',
                'reference_label': 'Referencia',
                'step_response_tab': '📈 Respuesta al Escalón',
                'step_response_title': 'Experimento de Respuesta al Escalón',
                'step_response_config': 'Configuración del Escalón',
                'battery_voltage': 'Voltaje de Batería (V)',
                'step_amplitude': 'Amplitud del Escalón (V)',
                'step_duration': 'Duración del Escalón (s)',
                'motor_direction': 'Dirección del Motor',
                'forward': 'Avanzar',
                'reverse': 'Retroceder',
                'step_response_graph': 'Gráfico de Respuesta al Escalón',
                'distance_response': 'Respuesta de Distancia',
                'step_input_label': 'Entrada Escalón',
                'pwm_input_label': 'Entrada PWM',
                'no_step_data': 'No hay datos de respuesta al escalón',
                'step_experiment_firmware': 'Requiere firmware de Respuesta al Escalón (trenUDP_esp)',
                'step_test_active': 'Prueba de escalón activa',
                'step_test_stopped': 'Prueba de escalón detenida',
                'step_esp32_status': 'Estado ESP32 (Escalón)',
                'configure_step_first': 'Configure los parámetros del escalón primero'
            },
            'en': {
                'title': 'Train PID Control System',
                'subtitle': 'Unified platform for ESP32-based train control experiments with network configuration',
                'network_tab': '🔧 Network Configuration',
                'control_tab': '🎛️ PID Control',
                'data_tab': '📊 Data Visualization',
                'network_config': 'Network Configuration',
                'welcome': '👋 Welcome! Start by configuring your network connection:',
                'select_interface': '1. Select your network interface from the dropdown below',
                'note_ip': '2. Note the IP address to configure in your ESP32',
                'apply_config': '3. Click "Apply Configuration"',
                'auto_saved': '4. Your settings are automatically saved and will be restored next time!',
                'select_network': 'Select Network Interface:',
                'refresh_interfaces': 'Refresh Interfaces',
                'apply_configuration': 'Apply Configuration',
                'udp_port': 'UDP Port:',
                'mqtt_port': 'MQTT Port:',
                'status': 'Status',
                'ip_address': 'IP Address',
                'esp32_setup': 'ESP32 Setup',
                'pid_control': 'PID Control',
                'start_experiment': 'Start Experiment',
                'stop_experiment': 'Stop Experiment',
                'kp_param': 'Kp Parameter',
                'ki_param': 'Ki Parameter',
                'kd_param': 'Kd Parameter',
                'reference_distance': 'Reference Distance (cm)',
                'realtime_graph': 'Real-time Graph',
                'historical_graph': 'Historical Graph',
                'connection_status': 'Connection Status',
                'total_packets': 'Total Packets',
                'configure_network': 'Configure network in the \'Network\' tab to start',
                'distance_data_realtime': 'Real-time Distance Sensor Data',
                'time': 'Time',
                'distance_cm': 'Distance (cm)',
                'experiment_files_not_found': 'No experiment files found - start UDP receiver',
                'data_format_problem': 'Data format problem - expected columns: time_event, input',
                'waiting_esp32_data': 'Waiting for ESP32 data... (empty CSV file)',
                'waiting_data_file': 'Waiting for data...',
                'data_read_error': 'Error reading data',
                'points': 'points',
                'csv_file_path': 'CSV File Path',
                'language': 'Language',
                'configure_network_first': 'Configure network first to enable data logging',
                'no_active_experiment': 'No active experiment',
                'waiting_for_data': 'Waiting for data from ESP32...',
                'experiment_started': 'Experiment started!',
                'experiment_stopped': 'Experiment stopped!',
                'configure_network_warning': 'Configure network first!',
                'configuration_applied': 'Configuration applied and saved!',
                'udp_start_failed': 'Failed to start UDP receiver',
                'connected': 'Connected',
                'connection_lost': 'Connection lost',
                'receiving_data': 'Receiving data',
                'waiting_for_data_status': 'Waiting for data',
                'packets': 'Packets',
                'last': 'Last',
                'never': 'Never',
                'status_unavailable': 'Status unavailable',
                'download_csv': 'Download CSV',
                'download_experiment_data': 'Download Experiment Data',
                'no_data_to_download': 'No data to download',
                'esp32_parameters': 'ESP32 Parameters',
                'esp32_confirmed_parameters': 'ESP32 Confirmed Parameters',
                'esp32_waiting_parameters': 'ESP32: Waiting for parameters...',
                'network_not_configured': '⚠️ Network not configured',
                'go_to_network_tab': 'Go to Network Configuration tab to set up connection.',
                'esp32_connection_status': 'ESP32 Connection Status',
                'historical_data': 'Historical Data',
                'data_current_session': 'Data from current experiment session.',
                'data_storage': 'Data Storage',
                'total_packets_label': 'Total Packets',
                'last_received': 'Last Received',
                'experiment_label': 'Experiment',
                'latest_data': 'Latest Data',
                'active': 'Active',
                'stopped': 'Stopped',
                'welcome_network': '👋 Welcome! Start by configuring your network connection:',
                'step_select_interface': '1. Select your network interface from the dropdown below',
                'step_note_ip': '2. Note the IP address to configure in your ESP32',
                'step_apply_config': '3. Click "Apply Configuration" to start the system',
                'esp32_configuration': 'ESP32 Configuration',
                'use_ip_address': 'Use this IP address in your ESP32 code before flashing.',
                'port_configuration': 'Port Configuration',
                'pid_parameters': 'PID Parameters',
                'ip_address_to_configure': 'IP Address to configure in ESP32:',
                'csv_file_path_label': 'CSV File Path:',
                'test_connection': 'Test Connection',
                'experiment_data_connection_status': 'Experiment Data & Connection Status',
                'parameters_sent_esp32': 'Parameters sent to ESP32',
                'mqtt_communication_error': 'MQTT communication error',
                'parameters_configured': 'Parameters configured',
                'ready_to_start': 'Ready to start experiment',
                'select_interface_placeholder': 'Select network interface...',
                'mqtt_sync_not_available': 'MQTT sync not available',
                'connection_waiting_confirmation': 'Connected, waiting for confirmation...',
                'mqtt_not_connected': 'MQTT not connected',
                'mqtt_not_available': 'MQTT: Not available',
                'esp32_label': 'ESP32: ',
                'auto_loaded': 'Auto-loaded',
                'selected': 'Selected',
                'interfaces_refreshed': 'Interfaces refreshed',
                'network_interfaces_updated': 'Network interfaces updated',
                'select_an_interface': 'Select an interface',
                'configuration_applied_saved_mqtt': 'Configuration applied and saved! MQTT sync enabled.',
                'udp_started_mqtt_failed': 'UDP started but MQTT sync failed',
                'ready_apply_configuration': 'Ready to apply configuration',
                'current': 'Current',
                'current_configuration_loaded': 'Current configuration loaded',
                'no_interface_selected': 'No interface selected',
                'configure_network_settings_above': 'Configure network settings above',
                'tab_not_found': 'Tab not found',
                'pid_red_no_configurada': 'PID: Kp={kp:.1f}, Ki={ki:.1f}, Kd={kd:.1f}, Ref={ref}cm (Network not configured)',
                'no_data_received': 'No data received',
                'kp_label': 'Kp',
                'ki_label': 'Ki',
                'kd_label': 'Kd',
                'ref_label': 'Ref (cm)',
                'send_button': 'Send',
                'distance_label': 'Distance',
                'reference_label': 'Reference',
                'step_response_tab': '📈 Step Response',
                'step_response_title': 'Step Response Experiment',
                'step_response_config': 'Step Configuration',
                'battery_voltage': 'Battery Voltage (V)',
                'step_amplitude': 'Step Amplitude (V)',
                'step_duration': 'Step Duration (s)',
                'motor_direction': 'Motor Direction',
                'forward': 'Forward',
                'reverse': 'Reverse',
                'step_response_graph': 'Step Response Graph',
                'distance_response': 'Distance Response',
                'step_input_label': 'Step Input',
                'pwm_input_label': 'PWM Input',
                'no_step_data': 'No step response data available',
                'step_experiment_firmware': 'Requires Step Response firmware (trenUDP_esp)',
                'step_test_active': 'Step test active',
                'step_test_stopped': 'Step test stopped',
                'step_esp32_status': 'ESP32 Status (Step)',
                'configure_step_first': 'Configure step parameters first'
            }
        }

        print(f"Dashboard initialized:")
        print(f"  - Dashboard data_manager ID: {id(self.data_manager)}")
        print(f"  - Dashboard data_manager CSV: {self.data_manager.csv_file}")
        print(f"  - UDP receiver data_manager ID: {id(self.udp_receiver.data_manager)}")
        print(f"  - UDP receiver data_manager CSV: {self.udp_receiver.data_manager.csv_file}")

        # Dashboard configuration with custom CSS
        external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap']
        self.app = dash.Dash(__name__, external_stylesheets=external_stylesheets,
                            suppress_callback_exceptions=True)
        
        # Setup message queue for push notifications
        self.websocket_messages = queue.Queue(maxsize=100)
        
        # Connect callback to data sources
        self.data_manager.websocket_callback = self._push_websocket_message
        self.mqtt_sync.websocket_callback = self._push_websocket_message
        
        # Setup message queue for push notifications
        self.websocket_messages = queue.Queue(maxsize=100)
        
        # Connect callback to data sources
        self.data_manager.websocket_callback = self._push_websocket_message
        self.mqtt_sync.websocket_callback = self._push_websocket_message

        # Modern color scheme
        self.colors = {
            'primary': '#1f2937',      # Dark gray
            'secondary': '#3b82f6',    # Blue
            'accent': '#10b981',       # Green
            'background': '#f8fafc',   # Light gray
            'surface': '#ffffff',      # White
            'text': '#1f2937',         # Dark gray
            'text_light': '#6b7280',   # Medium gray
            'success': '#10b981',      # Green
            'warning': '#f59e0b',      # Yellow
            'danger': '#ef4444',       # Red
            'train_primary': '#dc2626', # Train red
            'train_secondary': '#1e40af' # Train blue
        }

        self.setup_layout()
        self.setup_callbacks()

    def _handle_zoom_state(self, graph_id, relayout_data):
        """Handle zoom state updates for a specific graph"""
        if relayout_data and graph_id in self.zoom_state:
            zoom_state = self.zoom_state[graph_id]

            # User interacted with the graph (zoomed, panned, etc.)
            if 'xaxis.range[0]' in relayout_data:
                zoom_state['xaxis.range[0]'] = relayout_data['xaxis.range[0]']
                zoom_state['user_has_zoomed'] = True
            if 'xaxis.range[1]' in relayout_data:
                zoom_state['xaxis.range[1]'] = relayout_data['xaxis.range[1]']
                zoom_state['user_has_zoomed'] = True
            if 'yaxis.range[0]' in relayout_data:
                zoom_state['yaxis.range[0]'] = relayout_data['yaxis.range[0]']
                zoom_state['user_has_zoomed'] = True
            if 'yaxis.range[1]' in relayout_data:
                zoom_state['yaxis.range[1]'] = relayout_data['yaxis.range[1]']
                zoom_state['user_has_zoomed'] = True

            # Handle double-click (zoom reset)
            if 'xaxis.autorange' in relayout_data or 'yaxis.autorange' in relayout_data:
                zoom_state['user_has_zoomed'] = False
                zoom_state['xaxis.range[0]'] = None
                zoom_state['xaxis.range[1]'] = None
                zoom_state['yaxis.range[0]'] = None
                zoom_state['yaxis.range[1]'] = None

    def _apply_zoom_state(self, layout_config, graph_id):
        """Apply saved zoom state to layout configuration"""
        if graph_id in self.zoom_state:
            zoom_state = self.zoom_state[graph_id]
            if zoom_state['user_has_zoomed']:
                if zoom_state['xaxis.range[0]'] is not None and zoom_state['xaxis.range[1]'] is not None:
                    layout_config['xaxis_range'] = [zoom_state['xaxis.range[0]'], zoom_state['xaxis.range[1]']]
                if zoom_state['yaxis.range[0]'] is not None and zoom_state['yaxis.range[1]'] is not None:
                    layout_config['yaxis_range'] = [zoom_state['yaxis.range[0]'], zoom_state['yaxis.range[1]']]

    def _create_data_graph(self, graph_id, title_prefix=""):
        """Generic method to create a data graph with zoom preservation"""
        # Check if system is properly initialized
        if not self.data_manager.initialized:
            fig = px.line(title=self.t('configure_network'))
            fig.update_layout(
                plot_bgcolor=self.colors['surface'],
                paper_bgcolor=self.colors['background'],
                font_color=self.colors['text'],
                margin=dict(l=40, r=20, t=40, b=40)
            )
            return fig

        # Create a basic figure to start with
        fig = go.Figure()

        # Try to read current CSV data
        try:
            # Find the actual file being written to
            csv_files = glob.glob("experiment_*.csv")
            if not csv_files:
                fig.update_layout(
                    title=self.t('experiment_files_not_found'),
                    plot_bgcolor=self.colors['surface'],
                    paper_bgcolor=self.colors['background'],
                    font_color=self.colors['text'],
                    margin=dict(l=40, r=20, t=40, b=40)
                )
                return fig

            # Find the file that's actively being written (most recently modified)
            active_csv = max(csv_files, key=os.path.getmtime)
            file_size = os.path.getsize(active_csv)

            # Always read from the active file (the one being written to)
            if file_size > 100:  # File has more than just headers
                df = pd.read_csv(active_csv)

                if not df.empty:
                    # Check what columns we have and adapt accordingly
                    if 'time_event' in df.columns and 'input' in df.columns:
                        # Sort by time
                        df = df.sort_values('time_event')

                        # Add distance sensor data
                        fig.add_trace(go.Scatter(
                            x=df['time_event'],
                            y=df['input'],
                            mode='lines+markers',
                            name=self.t('distance_label'),
                            line=dict(color='blue'),
                            marker=dict(size=4)
                        ))

                        # Add reference line if available
                        if 'referencia' in df.columns:
                            fig.add_trace(go.Scatter(
                                x=df['time_event'],
                                y=df['referencia'],
                                mode='lines',
                                name=self.t('reference_label'),
                                line=dict(color='red', dash='dash')
                            ))

                        # Base layout configuration
                        layout_config = dict(
                            title=f'{title_prefix}{self.t("distance_data_realtime")} ({len(df)} {self.t("points")})',
                            xaxis_title=self.t('time'),
                            yaxis_title=self.t('distance_cm'),
                            plot_bgcolor=self.colors['surface'],
                            paper_bgcolor=self.colors['background'],
                            font_color=self.colors['text'],
                            showlegend=True,
                            margin=dict(l=40, r=20, t=40, b=40)
                        )

                        # Apply user zoom state if they have zoomed
                        self._apply_zoom_state(layout_config, graph_id)

                        fig.update_layout(**layout_config)
                        return fig

                    else:
                        # Columns don't match expected format
                        fig.update_layout(
                            title=self.t('data_format_problem'),
                            plot_bgcolor=self.colors['surface'],
                            paper_bgcolor=self.colors['background'],
                            font_color=self.colors['text'],
                            margin=dict(l=40, r=20, t=40, b=40)
                        )
                        return fig

                else:
                    # CSV exists but is empty
                    fig.update_layout(
                        title=self.t('waiting_esp32_data'),
                        plot_bgcolor=self.colors['surface'],
                        paper_bgcolor=self.colors['background'],
                        font_color=self.colors['text'],
                        margin=dict(l=40, r=20, t=40, b=40)
                    )
                    return fig

            else:
                # File exists but is too small (just headers)
                fig.update_layout(
                    title=f"{self.t('waiting_data_file')} (Archivo: {os.path.basename(active_csv)})",
                    plot_bgcolor=self.colors['surface'],
                    paper_bgcolor=self.colors['background'],
                    font_color=self.colors['text'],
                    margin=dict(l=40, r=20, t=40, b=40)
                )
                return fig

        except Exception as e:
            # Show error in graph title for debugging
            print(f"Graph update error: {e}")
            fig.update_layout(
                title=f"{self.t('data_read_error')}: {str(e)}",
                plot_bgcolor=self.colors['surface'],
                paper_bgcolor=self.colors['background'],
                font_color=self.colors['text'],
                margin=dict(l=40, r=20, t=40, b=40)
            )
            return fig

    def _on_params_confirmed(self, confirmed_params):
        """Called when Arduino confirms parameter values via MQTT"""
        # Update our confirmed parameters
        for key, value in confirmed_params.items():
            if value is not None:
                self.confirmed_params[key] = value

        # Store timestamp of last confirmation
        self.last_confirmation_time = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] Dashboard synced with Arduino parameters: {self.confirmed_params}")

    def _get_parameter_status_display(self):
        """Generate parameter status display showing confirmed vs sent values"""
        if not hasattr(self, 'mqtt_sync') or not self.mqtt_sync:
            return html.Div([
                html.Strong(self.t('esp32_parameters') + ": ", style={'color': self.colors['text']}),
                html.Span(self.t('mqtt_sync_not_available'), style={'color': self.colors['warning']})
            ])

        # Check MQTT connection status
        mqtt_connected = self.mqtt_sync.connected if hasattr(self.mqtt_sync, 'connected') else False
        confirmed = self.mqtt_sync.confirmed_params

        # Check if we have any confirmed parameters
        has_confirmed = any(v is not None for v in confirmed.values())

        # Debug info with timestamp (comment out verbose debug logging)
        # current_time = time.strftime('%H:%M:%S')
        # last_confirm_time = getattr(self, 'last_confirmation_time', 0)
        # time_since_confirm = time.time() - last_confirm_time if last_confirm_time > 0 else float('inf')
        # print(f"[DEBUG {current_time}] MQTT connected: {mqtt_connected}, Has confirmed params: {has_confirmed}")
        # print(f"[DEBUG {current_time}] Confirmed params: {confirmed}")
        # print(f"[DEBUG {current_time}] Time since last confirmation: {time_since_confirm:.1f}s")

        if has_confirmed:
            # Display confirmed parameters with better formatting
            confirmed_kp = f"{confirmed['kp']:.1f}" if confirmed['kp'] is not None else 'N/A'
            confirmed_ki = f"{confirmed['ki']:.1f}" if confirmed['ki'] is not None else 'N/A'
            confirmed_kd = f"{confirmed['kd']:.1f}" if confirmed['kd'] is not None else 'N/A'
            confirmed_ref = f"{confirmed['reference']:.1f}" if confirmed['reference'] is not None else 'N/A'

            return html.Div([
                html.Strong(self.t('esp32_confirmed_parameters') + ": ", style={'color': self.colors['text'], 'fontSize': '14px'}),
                html.Br(),
                html.Span(f"Kp={confirmed_kp}, Ki={confirmed_ki}, Kd={confirmed_kd}, Ref={confirmed_ref}cm",
                         style={'color': self.colors['success'], 'fontWeight': 'bold', 'fontSize': '13px',
                               'backgroundColor': '#e8f5e8', 'padding': '4px 8px', 'borderRadius': '4px'}),
                html.Span(" ✓", style={'color': self.colors['success'], 'fontSize': '18px', 'marginLeft': '8px'})
            ])
        else:
            connection_msg = self.t('connection_waiting_confirmation') if mqtt_connected else self.t('mqtt_not_connected')
            return html.Div([
                html.Strong(self.t('esp32_parameters') + ": ", style={'color': self.colors['text'], 'fontSize': '14px'}),
                html.Br(),
                html.Span(connection_msg, style={'color': self.colors['warning'], 'fontStyle': 'italic'})
            ])

    def _get_pid_connection_status(self):
        """Get compact MQTT parameter status for PID Control tab"""
        if not hasattr(self, 'mqtt_sync') or not self.mqtt_sync:
            return html.Span(self.t('mqtt_not_available'),
                           style={'color': self.colors['warning'], 'fontSize': '13px'})

        confirmed = self.mqtt_sync.confirmed_params
        has_confirmed = any(v is not None for v in confirmed.values())

        # Only print when parameters actually change, not every 200ms (reduced verbosity)
        # timestamp = time.strftime('%H:%M:%S')
        # if not hasattr(self, '_last_pid_params') or self._last_pid_params != confirmed:
        #     print(f"[PID CONNECTION STATUS {timestamp}] DISPLAY UPDATED: {confirmed}")
        #     self._last_pid_params = confirmed.copy()

        if has_confirmed:
            # Format confirmed parameters compactly for PID tab
            kp_val = f"{confirmed['kp']:.1f}" if confirmed['kp'] is not None else "?"
            ki_val = f"{confirmed['ki']:.1f}" if confirmed['ki'] is not None else "?"
            kd_val = f"{confirmed['kd']:.1f}" if confirmed['kd'] is not None else "?"
            ref_val = f"{confirmed['reference']:.1f}" if confirmed['reference'] is not None else "?"

            # Add timestamp to show when display was last updated
            current_time = time.strftime('%H:%M:%S')
            return html.Span([
                self.t('esp32_label'),
                html.Span(f"Kp={kp_val}, Ki={ki_val}, Kd={kd_val}, Ref={ref_val}cm",
                         style={'color': self.colors['success'], 'fontWeight': 'bold'}),
                html.Span(" ✓", style={'color': self.colors['success'], 'marginLeft': '5px'}),
                html.Span(f" ({current_time})", style={'color': self.colors['text_light'], 'fontSize': '11px', 'marginLeft': '8px'})
            ], style={'fontSize': '13px'})
        else:
            return html.Span(self.t('esp32_waiting_parameters'),
                           style={'color': self.colors['warning'], 'fontSize': '13px'})

    def t(self, key):
        """Get translation for current language"""
        return self.translations[self.current_language].get(key, key)

    def _push_websocket_message(self, message):
        """Push message to WebSocket queue"""
        try:
            self.websocket_messages.put_nowait(message)
        except queue.Full:
            pass  # Drop message if queue is full
    
    def _get_websocket_message(self):
        """Get message from WebSocket queue (non-blocking)"""
        try:
            return self.websocket_messages.get_nowait()
        except queue.Empty:
            return None

    def _push_websocket_message(self, message):
        """Push message to WebSocket queue"""
        try:
            self.websocket_messages.put_nowait(message)
        except queue.Full:
            pass  # Drop message if queue is full
    
    def _get_websocket_message(self):
        """Get message from WebSocket queue (non-blocking)"""
        try:
            return self.websocket_messages.get_nowait()
        except queue.Empty:
            return None

    def setup_layout(self):
        """Setup the dashboard layout"""
        self.app.layout = html.Div([

            dcc.Store(id='language-store', data={'language': 'es'}),
            dcc.Store(id='network-config-store', data={}),
            dcc.Store(id='mqtt-params-store', data={'last_update': 0}),
            
            # Data availability trigger for efficient updates
            dcc.Store(id='ws-message-store', data={}),
            dcc.Interval(id='fast-update-check', interval=100, n_intervals=0),  # 100ms check for new data

            # Global data refresh interval (always present)
            dcc.Interval(
                id='data-refresh-interval',
                disabled=False,
                n_intervals=0,
                interval=1000,  # 1000ms refresh (reduced from 500ms)
                max_intervals=-1
            ),

            # Fast MQTT status refresh interval
            dcc.Interval(
                id='mqtt-status-refresh',
                disabled=False,
                n_intervals=0,
                interval=200,  # 200ms refresh for immediate MQTT updates
                max_intervals=-1
            ),

            # Header with language toggle
            html.Div([
                html.Div([
                    html.H1(id='app-title', children=self.t('title'),
                           style={'color': 'white', 'margin': '0', 'fontSize': '20px', 'fontWeight': '600'}),
                    html.P(id='app-subtitle', children=self.t('subtitle'),
                          style={'color': 'rgba(255,255,255,0.8)', 'margin': '3px 0 0 0', 'fontSize': '13px'})
                ], style={'flex': '1'}),

                html.Div([
                    html.Label(id='language-label', children=self.t('language'),
                              style={'color': 'white', 'marginRight': '10px', 'fontSize': '14px'}),
                    dcc.Dropdown(
                        id='language-dropdown',
                        options=[
                            {'label': '🇪🇸 Español', 'value': 'es'},
                            {'label': '🇺🇸 English', 'value': 'en'}
                        ],
                        value=self.current_language,
                        style={
                            'width': '120px',
                            'color': '#333333',
                            'backgroundColor': 'white',
                            'fontSize': '14px',
                            'fontWeight': '500'
                        },
                        clearable=False,
                        optionHeight=40
                    )
                ], style={'display': 'flex', 'alignItems': 'center'})
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
                     'background': 'linear-gradient(135deg, #dc2626 0%, #1e40af 100%)',
                     'color': 'white', 'padding': '12px 16px', 'borderRadius': '8px', 'marginBottom': '16px'}),

            # Experiment controls at the top (always visible) - Compact design without title
            html.Div(id='top-experiment-controls', style={
                'background': '#f8fafc', 'padding': '8px 16px', 'borderRadius': '6px',
                'border': '1px solid #e5e7eb', 'marginBottom': '12px'
            }, children=[
                html.Div([
                    html.Button(id='start-experiment-btn', children=self.t('start_experiment'), n_clicks=0,
                               style={'backgroundColor': self.colors['success'], 'color': 'white', 'border': 'none',
                                     'padding': '6px 16px', 'borderRadius': '6px', 'fontSize': '13px',
                                     'fontWeight': '500', 'marginRight': '12px', 'cursor': 'pointer',
                                     'transition': 'all 0.2s ease', 'minWidth': '110px'}),
                    html.Button(id='stop-experiment-btn', children=self.t('stop_experiment'), n_clicks=0,
                               style={'backgroundColor': self.colors['danger'], 'color': 'white', 'border': 'none',
                                     'padding': '6px 16px', 'borderRadius': '6px', 'fontSize': '13px',
                                     'fontWeight': '500', 'marginRight': '12px', 'cursor': 'pointer',
                                     'transition': 'all 0.2s ease', 'minWidth': '110px'}),
                    html.Div(id='experiment-status-top', style={'display': 'inline-block', 'marginLeft': '15px',
                                                               'fontSize': '13px', 'color': self.colors['text_light']})
                ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'})
            ]),

            # Tabs - Compact design
            dcc.Tabs(id='main-tabs', value='control-tab', children=[
                dcc.Tab(label=self.t('network_tab'), value='network-tab'),
                dcc.Tab(label=self.t('control_tab'), value='control-tab'),
                dcc.Tab(label=self.t('step_response_tab'), value='step-response-tab'),
                dcc.Tab(label=self.t('data_tab'), value='data-tab')
            ], style={'marginBottom': '12px', 'height': '36px'}, content_style={'padding': '12px'}),

            # Experiment mode store
            dcc.Store(id='experiment-mode-store', data={'mode': 'pid'}),
            
            # Tab content
            html.Div(id='tab-content')
        ], style={'backgroundColor': self.colors['background'], 'minHeight': '100vh', 'padding': '16px'})

    def create_network_tab(self):
        """Create network configuration tab content"""
        return html.Div([
            html.H3(self.t('network_config'), style={'color': self.colors['text']}),

            # Helpful instructions
            html.Div([
                html.P(self.t('welcome_network'),
                      style={'fontSize': '16px', 'color': self.colors['text'], 'marginBottom': '5px'}),
                html.P(self.t('step_select_interface'),
                      style={'color': self.colors['text'], 'marginBottom': '5px'}),
                html.P(self.t('step_note_ip'),
                      style={'color': self.colors['text'], 'marginBottom': '5px'}),
                html.P(self.t('step_apply_config'),
                      style={'color': self.colors['text'], 'marginBottom': '15px'})
            ], style={'backgroundColor': '#e8f4f8', 'padding': '15px', 'borderRadius': '5px', 'marginBottom': '20px'}),

            # Network interface selection
            html.Div([
                html.Label(self.t('select_network'),
                          style={'fontWeight': 'bold', 'color': self.colors['text']}),
                dcc.Dropdown(
                    id='interface-dropdown',
                    options=self.network_manager.get_interface_options(),
                    value=None,
                    placeholder=self.t('select_interface_placeholder'),
                    style={'marginBottom': '10px'}
                ),
                html.Div(id='interface-status', style={'color': self.colors['text']})
            ], style={'marginBottom': '20px'}),

            # ESP32 Configuration Display
            html.Div([
                html.H4(self.t('esp32_configuration'), style={'color': self.colors['text']}),
                html.Div([
                    html.Label(self.t('ip_address_to_configure'),
                              style={'fontWeight': 'bold'}),
                    html.Div(id='esp32-ip-display',
                            style={'fontSize': '24px', 'fontWeight': 'bold',
                                  'color': self.colors['train_primary'], 'marginBottom': '10px'}),
                    html.P(self.t('use_ip_address'),
                          style={'fontStyle': 'italic', 'color': self.colors['text']})
                ])
            ], style={'border': '2px solid #007bff', 'padding': '15px', 'borderRadius': '5px',
                     'backgroundColor': '#e7f3ff', 'marginBottom': '20px'}),

            # Port Configuration
            html.Div([
                html.H4(self.t('port_configuration'), style={'color': self.colors['text']}),
                html.Div([
                    html.Label(self.t('udp_port')),
                    dcc.Input(id='udp-port-input', type='number', value=5555,
                             style={'marginLeft': '10px', 'marginRight': '20px'}),
                    html.Label(self.t('mqtt_port')),
                    dcc.Input(id='mqtt-port-input', type='number', value=1883,
                             style={'marginLeft': '10px'})
                ])
            ], style={'marginBottom': '20px'}),

            # Control buttons
            html.Div([
                html.Button(self.t('apply_configuration'), id='apply-config-btn',
                           style={'marginRight': '10px', 'backgroundColor': self.colors['success']}),
                html.Button(self.t('test_connection'), id='test-connection-btn',
                           style={'marginRight': '10px', 'backgroundColor': self.colors['warning']}),
                html.Button(self.t('refresh_interfaces'), id='refresh-interfaces-btn',
                           style={'backgroundColor': self.colors['secondary']})
            ]),

            # Status display
            html.Div(id='network-status', style={'marginTop': '20px'})
        ])

    def create_control_tab(self):
        """Create PID control tab content"""
        return html.Div([
            # Two-column layout
            html.Div([
                # Left column - Controls
                html.Div([
                    # PID Controls Card - Compact with input boxes
                    html.Div([
                        html.H4(self.t('pid_parameters'), style={'textAlign': 'center', 'color': self.colors['primary'],
                                                        'marginBottom': '12px', 'fontSize': '14px', 'fontWeight': '500'}),

                        # Kp slider + input
                        html.Div([
                            html.Div([
                                html.Label(f"{self.t('kp_label')}: ", style={'fontWeight': '500', 'color': self.colors['text'], 'fontSize': '12px', 'marginBottom': '4px'}),
                                html.Div([
                                    dcc.Input(id='kp-input', type='number', value=0, min=0, max=250, step=0.1,
                                             style={'width': '70px', 'height': '24px', 'fontSize': '11px', 'padding': '2px 4px', 'marginRight': '4px'}),
                                    html.Button(self.t('send_button'), id='kp-send-btn', n_clicks=0,
                                               style={'height': '24px', 'fontSize': '10px', 'padding': '0 6px', 'backgroundColor': self.colors['accent'],
                                                     'color': 'white', 'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer'})
                                ], style={'display': 'flex', 'alignItems': 'center'})
                            ], style={'marginBottom': '6px'}),
                            dcc.Slider(
                                id='kp-slider',
                                min=0, max=150, value=0, step=0.1,
                                marks={i*100: str(i*100) for i in range(3)},
                                tooltip={'placement': 'bottom', 'always_visible': False}
                            )
                        ], style={'marginBottom': '12px'}),

                        # Ki slider + input
                        html.Div([
                            html.Div([
                                html.Label(f"{self.t('ki_label')}: ", style={'fontWeight': '500', 'color': self.colors['text'], 'fontSize': '12px', 'marginBottom': '4px'}),
                                html.Div([
                                    dcc.Input(id='ki-input', type='number', value=0, min=0, max=250, step=0.1,
                                             style={'width': '70px', 'height': '24px', 'fontSize': '11px', 'padding': '2px 4px', 'marginRight': '4px'}),
                                    html.Button(self.t('send_button'), id='ki-send-btn', n_clicks=0,
                                               style={'height': '24px', 'fontSize': '10px', 'padding': '0 6px', 'backgroundColor': self.colors['accent'],
                                                     'color': 'white', 'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer'})
                                ], style={'display': 'flex', 'alignItems': 'center'})
                            ], style={'marginBottom': '6px'}),
                            dcc.Slider(
                                id='ki-slider',
                                min=0, max=150, value=0, step=0.1,
                                marks={i*100: str(i*100) for i in range(3)},
                                tooltip={'placement': 'bottom', 'always_visible': False}
                            )
                        ], style={'marginBottom': '12px'}),

                        # Kd slider + input
                        html.Div([
                            html.Div([
                                html.Label(f"{self.t('kd_label')}: ", style={'fontWeight': '500', 'color': self.colors['text'], 'fontSize': '12px', 'marginBottom': '4px'}),
                                html.Div([
                                    dcc.Input(id='kd-input', type='number', value=0, min=0, max=250, step=0.1,
                                             style={'width': '70px', 'height': '24px', 'fontSize': '11px', 'padding': '2px 4px', 'marginRight': '4px'}),
                                    html.Button(self.t('send_button'), id='kd-send-btn', n_clicks=0,
                                               style={'height': '24px', 'fontSize': '10px', 'padding': '0 6px', 'backgroundColor': self.colors['accent'],
                                                     'color': 'white', 'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer'})
                                ], style={'display': 'flex', 'alignItems': 'center'})
                            ], style={'marginBottom': '6px'}),
                            dcc.Slider(
                                id='kd-slider',
                                min=0, max=150, value=0, step=0.1,
                                marks={i*100: str(i*100) for i in range(3)},
                                tooltip={'placement': 'bottom', 'always_visible': False}
                            )
                        ], style={'marginBottom': '12px'}),

                        # Reference distance + input
                        html.Div([
                            html.Div([
                                html.Label(f"{self.t('ref_label')}: ", style={'fontWeight': '500', 'color': self.colors['text'], 'fontSize': '12px', 'marginBottom': '4px'}),
                                html.Div([
                                    dcc.Input(id='ref-input', type='number', value=10, min=1, max=100, step=0.5,
                                             style={'width': '70px', 'height': '24px', 'fontSize': '11px', 'padding': '2px 4px', 'marginRight': '4px'}),
                                    html.Button(self.t('send_button'), id='ref-send-btn', n_clicks=0,
                                               style={'height': '24px', 'fontSize': '10px', 'padding': '0 6px', 'backgroundColor': self.colors['accent'],
                                                     'color': 'white', 'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer'})
                                ], style={'display': 'flex', 'alignItems': 'center'})
                            ], style={'marginBottom': '6px'}),
                            dcc.Slider(
                                id='reference-slider',
                                min=1, max=100, value=10, step=0.5,
                                marks={i*50: f"{i*50}" for i in range(3)},
                                tooltip={'placement': 'bottom', 'always_visible': False}
                            )
                        ], style={'marginBottom': '12px'})

                    ], style={'background': 'white', 'padding': '12px', 'borderRadius': '8px',
                             'boxShadow': '0 1px 4px rgba(0,0,0,0.1)', 'marginBottom': '12px'}),

                    # Connection Status Card
                    html.Div([
                        html.H4(self.t('connection_status'), style={'color': self.colors['primary'], 'marginBottom': '15px'}),
                        html.Div(id='connection-status-indicator', style={'marginBottom': '10px'}),
                        html.Div(id='data-status', style={'color': self.colors['text_light'], 'fontSize': '14px'})
                    ], style={'background': 'white', 'padding': '20px', 'borderRadius': '12px',
                             'boxShadow': '0 2px 8px rgba(0,0,0,0.1)', 'marginBottom': '20px'})

                ], style={'width': '35%', 'paddingRight': '20px'}),

                # Right column - Graph
                html.Div([
                    html.Div([
                        html.H4(self.t('realtime_graph'), style={'textAlign': 'center', 'color': self.colors['primary'], 'marginBottom': '8px', 'fontSize': '16px'}),
                        dcc.Graph(id='realtime-graph',
                                 figure=px.line(),
                                 style={'height': '350px'})
                    ], style={'background': 'white', 'padding': '12px', 'borderRadius': '8px',
                             'boxShadow': '0 1px 4px rgba(0,0,0,0.1)', 'marginBottom': '12px'})
                ], style={'width': '65%'})

            ], style={'display': 'flex', 'gap': '20px'})
        ])

    def create_data_tab(self):
        """Create data visualization tab content"""
        return html.Div([
            html.H3(self.t('experiment_data_connection_status'), style={'color': self.colors['text']}),

            # Data connection status panel
            html.Div([
                html.H4(self.t('esp32_connection_status'), style={'color': self.colors['text']}),
                html.Div(id='detailed-connection-status',
                        style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '5px'})
            ], style={'marginBottom': '20px'}),

            # Historical data visualization
            html.Div([
                html.H4(self.t('historical_data'), style={'color': self.colors['text']}),
                html.P(self.t('data_current_session'),
                      style={'color': self.colors['text']}),
                dcc.Graph(id='historical-graph', figure=px.line())
            ], style={'marginBottom': '20px'}),

            # File information and download
            html.Div([
                html.H4(self.t('data_storage'), style={'color': self.colors['text']}),
                html.Div([
                    html.Label(self.t('csv_file_path_label'), style={'fontWeight': 'bold'}),
                    html.Div(id='csv-file-path', style={'fontFamily': 'monospace', 'marginTop': '5px', 'marginBottom': '10px'}),
                    html.Button(
                        id='download-csv-btn',
                        children=self.t('download_csv'),
                        n_clicks=0,
                        style={
                            'backgroundColor': self.colors['accent'],
                            'color': 'white',
                            'border': 'none',
                            'padding': '8px 16px',
                            'borderRadius': '5px',
                            'fontSize': '14px',
                            'cursor': 'pointer',
                            'marginTop': '5px'
                        }
                    ),
                    dcc.Download(id="download-csv-file")
                ])
            ])
        ])


    def create_step_response_tab(self):
        """Create step response experiment tab"""
        return html.Div([
            html.H3(self.t('step_response_title'), style={'color': self.colors['text'], 'marginBottom': '20px'}),
            
            html.Div([
                # Left column - Configuration Panel
                html.Div([
                    html.Div([
                        html.H4(self.t('step_response_config'), 
                               style={'color': self.colors['primary'], 'marginBottom': '15px', 'fontSize': '16px'}),
                        
                        # Battery Voltage
                        html.Div([
                            html.Label(f"{self.t('battery_voltage')}: ", 
                                     style={'fontWeight': '500', 'fontSize': '12px', 'marginBottom': '4px'}),
                            html.Div([
                                dcc.Input(id='vbatt-input', type='number', 
                                        value=8.4, min=0, max=8.4, step=0.1,
                                        style={'width': '70px', 'height': '24px', 'fontSize': '11px', 
                                              'padding': '2px 4px', 'marginRight': '4px'}),
                                html.Button(self.t('send_button'), id='vbatt-send-btn', n_clicks=0,
                                          style={'height': '24px', 'fontSize': '10px', 'padding': '0 6px',
                                                'backgroundColor': self.colors['accent'], 'color': 'white',
                                                'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer'})
                            ], style={'display': 'flex', 'alignItems': 'center'}),
                            dcc.Slider(id='vbatt-slider', min=0, max=8.4, value=8.4, step=0.1,
                                     marks={i*2: f"{i*2}" for i in range(5)},
                                     tooltip={'placement': 'bottom', 'always_visible': False})
                        ], style={'marginBottom': '15px'}),
                        
                        # Step Amplitude
                        html.Div([
                            html.Label(f"{self.t('step_amplitude')}: ", 
                                     style={'fontWeight': '500', 'fontSize': '12px', 'marginBottom': '4px'}),
                            html.Div([
                                dcc.Input(id='amplitude-input', type='number',
                                        value=3.0, min=0, max=8.4, step=0.1,
                                        style={'width': '70px', 'height': '24px', 'fontSize': '11px',
                                              'padding': '2px 4px', 'marginRight': '4px'}),
                                html.Button(self.t('send_button'), id='amplitude-send-btn', n_clicks=0,
                                          style={'height': '24px', 'fontSize': '10px', 'padding': '0 6px',
                                                'backgroundColor': self.colors['accent'], 'color': 'white',
                                                'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer'})
                            ], style={'display': 'flex', 'alignItems': 'center'}),
                            dcc.Slider(id='amplitude-slider', min=0, max=8.4, value=3.0, step=0.1,
                                     marks={i*2: f"{i*2}" for i in range(5)},
                                     tooltip={'placement': 'bottom', 'always_visible': False})
                        ], style={'marginBottom': '15px'}),
                        
                        # Step Duration
                        html.Div([
                            html.Label(f"{self.t('step_duration')}: ",
                                     style={'fontWeight': '500', 'fontSize': '12px', 'marginBottom': '4px'}),
                            html.Div([
                                dcc.Input(id='duration-input', type='number',
                                        value=5.0, min=0, max=20, step=0.5,
                                        style={'width': '70px', 'height': '24px', 'fontSize': '11px',
                                              'padding': '2px 4px', 'marginRight': '4px'}),
                                html.Button(self.t('send_button'), id='duration-send-btn', n_clicks=0,
                                          style={'height': '24px', 'fontSize': '10px', 'padding': '0 6px',
                                                'backgroundColor': self.colors['accent'], 'color': 'white',
                                                'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer'})
                            ], style={'display': 'flex', 'alignItems': 'center'}),
                            dcc.Slider(id='duration-slider', min=0, max=20, value=5.0, step=0.5,
                                     marks={i*5: f"{i*5}s" for i in range(5)},
                                     tooltip={'placement': 'bottom', 'always_visible': False})
                        ], style={'marginBottom': '15px'}),
                        
                        # Motor Direction
                        html.Div([
                            html.Label(f"{self.t('motor_direction')}: ",
                                     style={'fontWeight': '500', 'fontSize': '12px', 'marginBottom': '8px'}),
                            dcc.RadioItems(
                                id='direction-radio',
                                options=[
                                    {'label': f" {self.t('forward')}", 'value': 1},
                                    {'label': f" {self.t('reverse')}", 'value': 0}
                                ],
                                value=1,
                                style={'fontSize': '12px'}
                            )
                        ], style={'marginBottom': '20px'}),
                        
                        # ESP32 Status Display
                        html.Div([
                            html.H5(self.t('step_esp32_status'), 
                                   style={'fontSize': '13px', 'marginBottom': '8px', 'color': self.colors['text']}),
                            html.Div(id='step-esp32-status',
                                   style={'fontSize': '12px', 'padding': '8px', 'backgroundColor': '#f8f9fa',
                                         'borderRadius': '4px', 'minHeight': '60px'})
                        ], style={'marginTop': '20px'})
                        
                    ], style={'background': 'white', 'padding': '15px', 'borderRadius': '8px',
                             'boxShadow': '0 1px 4px rgba(0,0,0,0.1)'})
                ], style={'width': '35%', 'paddingRight': '20px'}),
                
                # Right column - Graph
                html.Div([
                    html.Div([
                        html.H4(self.t('step_response_graph'),
                               style={'textAlign': 'center', 'color': self.colors['primary'],
                                     'marginBottom': '8px', 'fontSize': '16px'}),
                        dcc.Graph(id='step-response-graph',
                                 figure=px.line(),
                                 style={'height': '400px'})
                    ], style={'background': 'white', 'padding': '12px', 'borderRadius': '8px',
                             'boxShadow': '0 1px 4px rgba(0,0,0,0.1)'})
                ], style={'width': '65%'})
                
            ], style={'display': 'flex', 'gap': '20px'})
        ])

    def setup_callbacks(self):
        """Setup all dashboard callbacks"""

        # Fast data availability check - triggers updates when new data arrives
        @self.app.callback(
            Output('ws-message-store', 'data'),
            Input('fast-update-check', 'n_intervals'),
            prevent_initial_call=True
        )
        def check_data_availability(n):
            """Check if new data is available and trigger updates"""
            # Try to get message from queue (non-blocking)
            message = self._get_websocket_message()
            if message:
                return {'timestamp': time.time(), 'message': message, 'n': n}
            raise PreventUpdate


        # Language change callback
        @self.app.callback(
            [Output('language-store', 'data'),
             Output('app-title', 'children'),
             Output('app-subtitle', 'children'),
             Output('language-label', 'children'),
             Output('start-experiment-btn', 'children'),
             Output('stop-experiment-btn', 'children'),
             Output('main-tabs', 'children')],
             Input('language-dropdown', 'value')
        )
        def change_language(selected_language):
            self.current_language = selected_language
            self.network_manager.set_language(selected_language)
            return (
                {'language': selected_language},
                self.t('title'),
                self.t('subtitle'),
                self.t('language'),
                self.t('start_experiment'),
                self.t('stop_experiment'),
                [
                    dcc.Tab(label=self.t('network_tab'), value='network-tab'),
                    dcc.Tab(label=self.t('control_tab'), value='control-tab'),
                    dcc.Tab(label=self.t('data_tab'), value='data-tab')
                ]
            )

        # Slider value display callbacks
        @self.app.callback(
            [Output('kp-value', 'children'),
             Output('ki-value', 'children'),
             Output('kd-value', 'children'),
             Output('ref-value', 'children')],
            [Input('kp-slider', 'value'),
             Input('ki-slider', 'value'),
             Input('kd-slider', 'value'),
             Input('reference-slider', 'value')]
        )
        def update_slider_values(kp, ki, kd, ref):
            return f"{kp:.1f}", f"{ki:.1f}", f"{kd:.1f}", f"{ref:.1f}cm"

        # Track active tab for experiment mode
        @self.app.callback(
            Output('experiment-mode-store', 'data'),
            Input('main-tabs', 'value')
        )
        def track_experiment_mode(active_tab):
            """Track which experiment mode is active based on tab"""
            if active_tab == 'step-response-tab':
                self.experiment_mode = 'step'
                return {'mode': 'step'}
            else:
                self.experiment_mode = 'pid'
                return {'mode': 'pid'}
        
        # Track active tab for experiment mode
        @self.app.callback(
            Output('tab-content', 'children'),
            [Input('main-tabs', 'value'),
             Input('language-store', 'data')]
        )
        def render_tab_content(active_tab, language_data):
            if language_data:
                self.current_language = language_data.get('language', 'en')

            if active_tab == 'network-tab':
                return self.create_network_tab()
            elif active_tab == 'control-tab':
                return self.create_control_tab()
            elif active_tab == 'data-tab':
                return self.create_data_tab()
            elif active_tab == 'step-response-tab':
                return self.create_step_response_tab()
            return html.Div(self.t('tab_not_found'))

        # Network configuration callbacks
        @self.app.callback(
            [Output('esp32-ip-display', 'children'),
             Output('interface-status', 'children'),
             Output('network-status', 'children')],
            [Input('interface-dropdown', 'value'),
             Input('apply-config-btn', 'n_clicks'),
             Input('refresh-interfaces-btn', 'n_clicks')],
            [State('udp-port-input', 'value'),
             State('mqtt-port-input', 'value')],
            prevent_initial_call=True
        )
        def handle_network_config(selected_ip, apply_clicks, refresh_clicks, udp_port, mqtt_port):
            ctx = callback_context

            # Check if we have auto-applied configuration
            if self.network_manager.selected_ip and not ctx.triggered:
                return (self.network_manager.selected_ip,
                       f"{self.t('auto_loaded')}: {self.network_manager.selected_ip}",
                       html.Div("✓ " + self.t('current_configuration_loaded'), style={'color': self.colors['success']}))

            if ctx.triggered:
                trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

                if trigger_id == 'refresh-interfaces-btn':
                    self.network_manager.detect_interfaces()
                    # Preserve current selection if available
                    current_ip = self.network_manager.selected_ip
                    if current_ip:
                        return current_ip, f"{self.t('selected')}: {current_ip}", self.t('interfaces_refreshed')
                    return self.t('select_an_interface'), self.t('interfaces_refreshed'), self.t('network_interfaces_updated')

                elif trigger_id == 'apply-config-btn' and selected_ip:
                    # Apply configuration
                    self.network_manager.set_selected_ip(selected_ip)
                    self.network_manager.update_ports(udp_port, mqtt_port)

                    # Stop current UDP receiver
                    self.udp_receiver.stop()

                    # Update UDP receiver configuration
                    self.udp_receiver.ip = selected_ip
                    self.udp_receiver.port = self.network_manager.udp_port

                    # Start UDP receiver
                    success = self.udp_receiver.start()

                    # Start MQTT parameter sync
                    mqtt_success = False
                    if success:
                        mqtt_success = self.mqtt_sync.connect(selected_ip, self.network_manager.mqtt_port)

                    if success and mqtt_success:
                        status_color = self.colors['success']
                        status_msg = self.t('configuration_applied_saved_mqtt')
                    elif success:
                        status_color = self.colors['warning']
                        status_msg = self.t('udp_started_mqtt_failed')
                    else:
                        status_color = self.colors['danger']
                        status_msg = self.t('udp_start_failed')

                    return (selected_ip,
                           f"{self.t('selected')}: {selected_ip}",
                           html.Div(status_msg, style={'color': status_color}))

            if selected_ip:
                return selected_ip, f"{self.t('selected')}: {selected_ip}", self.t('ready_apply_configuration')

            # Check if we have a saved configuration to display
            if self.network_manager.selected_ip:
                return (self.network_manager.selected_ip,
                       f"{self.t('current')}: {self.network_manager.selected_ip}",
                       self.t('current_configuration_loaded'))

            return self.t('select_an_interface'), self.t('no_interface_selected'), self.t('configure_network_settings_above')

        @self.app.callback(
            [Output('interface-dropdown', 'options'),
             Output('interface-dropdown', 'value')],
            Input('refresh-interfaces-btn', 'n_clicks')
        )
        def refresh_interface_options(n_clicks):
            options = self.network_manager.get_interface_options()
            # Set default value to saved IP if available and still exists
            default_value = None
            if self.network_manager.selected_ip:
                available_ips = [opt['value'] for opt in options]
                if self.network_manager.selected_ip in available_ips:
                    default_value = self.network_manager.selected_ip
            return options, default_value

        @self.app.callback(
            [Output('udp-port-input', 'value'),
             Output('mqtt-port-input', 'value')],
            Input('refresh-interfaces-btn', 'n_clicks')
        )
        def load_saved_ports(n_clicks):
            return self.network_manager.udp_port, self.network_manager.mqtt_port

        # PID control callbacks
        @self.app.callback(
            Output('experiment-status-top', 'children'),
            [Input('start-experiment-btn', 'n_clicks'),
             Input('stop-experiment-btn', 'n_clicks')]
        )
        def handle_experiment_control(start_clicks, stop_clicks):
            ctx = callback_context

            if ctx.triggered:
                trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

                if trigger_id == 'start-experiment-btn':
                    if self.network_manager.selected_ip:
                        # Determine which experiment mode based on active tab
                        if self.experiment_mode == 'step':
                            # Switch UDP receiver to step response data manager
                            self.udp_receiver.set_data_manager(self.step_data_manager)
                            self.step_data_manager.start_experiment()
                            # Create new step response CSV
                            csv_path = self.step_data_manager.create_step_csv()
                            print(f"Started step response experiment: {csv_path}")
                            publish.single(MQTT_TOPICS['step_sync'], 'True', hostname=self.network_manager.mqtt_broker_ip)
                        else:
                            # Switch UDP receiver to PID data manager

                            self.udp_receiver.set_data_manager(self.data_manager)

                            self.data_manager.start_experiment()
                            publish.single(MQTT_TOPICS['sync'], 'True', hostname=self.network_manager.mqtt_broker_ip)
                        return html.Div(self.t('experiment_started'), style={'color': self.colors['success']})
                    else:
                        return html.Div(self.t('configure_network_warning'), style={'color': self.colors['danger']})

                elif trigger_id == 'stop-experiment-btn':
                    if self.experiment_mode == 'step':
                        self.step_data_manager.stop_experiment()
                        publish.single(MQTT_TOPICS['step_sync'], 'False', hostname=self.network_manager.mqtt_broker_ip)
                    else:
                        self.data_manager.stop_experiment()
                        publish.single(MQTT_TOPICS['sync'], 'False', hostname=self.network_manager.mqtt_broker_ip)

            return self.t('ready_to_start')

        # PID parameter callbacks - sliders send immediately, inputs need button clicks
        @self.app.callback(
            Output('data-status', 'children'),
            [Input('kp-slider', 'value'),
             Input('ki-slider', 'value'),
             Input('kd-slider', 'value'),
             Input('reference-slider', 'value'),
             Input('kp-send-btn', 'n_clicks'),
             Input('ki-send-btn', 'n_clicks'),
             Input('kd-send-btn', 'n_clicks'),
             Input('ref-send-btn', 'n_clicks')],
            [State('kp-input', 'value'),
             State('ki-input', 'value'),
             State('kd-input', 'value'),
             State('ref-input', 'value')]
        )
        def update_pid_parameters(kp_slider, ki_slider, kd_slider, ref_slider,
                                 kp_send_clicks, ki_send_clicks, kd_send_clicks, ref_send_clicks,
                                 kp_input, ki_input, kd_input, ref_input):
            ctx = callback_context

            # Determine which control was used based on what triggered the callback
            if ctx.triggered:
                trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

                # Handle different triggers: sliders vs send buttons
                if trigger_id == 'kp-slider':
                    kp, ki, kd, reference = kp_slider, ki_slider, kd_slider, ref_slider
                elif trigger_id == 'kp-send-btn':
                    kp, ki, kd, reference = kp_input if kp_input is not None else kp_slider, ki_slider, kd_slider, ref_slider
                elif trigger_id == 'ki-slider':
                    kp, ki, kd, reference = kp_slider, ki_slider, kd_slider, ref_slider
                elif trigger_id == 'ki-send-btn':
                    kp, ki, kd, reference = kp_slider, ki_input if ki_input is not None else ki_slider, kd_slider, ref_slider
                elif trigger_id == 'kd-slider':
                    kp, ki, kd, reference = kp_slider, ki_slider, kd_slider, ref_slider
                elif trigger_id == 'kd-send-btn':
                    kp, ki, kd, reference = kp_slider, ki_slider, kd_input if kd_input is not None else kd_slider, ref_slider
                elif trigger_id == 'reference-slider':
                    kp, ki, kd, reference = kp_slider, ki_slider, kd_slider, ref_slider
                elif trigger_id == 'ref-send-btn':
                    kp, ki, kd, reference = kp_slider, ki_slider, kd_slider, ref_input if ref_input is not None else ref_slider
                else:
                    # Default to slider values
                    kp, ki, kd, reference = kp_slider, ki_slider, kd_slider, ref_slider
            else:
                # Default to slider values when no trigger (shouldn't happen)
                kp, ki, kd, reference = kp_slider, ki_slider, kd_slider, ref_slider

            # Show parameters but don't send MQTT if not configured
            if not self.network_manager.selected_ip:
                return self.t('pid_red_no_configurada').format(kp=kp, ki=ki, kd=kd, ref=reference)

            if ctx.triggered:
                try:
                    # Send MQTT only for sliders (immediate) and send buttons (on click)
                    if trigger_id in ['kp-slider', 'kp-send-btn']:
                        publish.single(MQTT_TOPICS['kp'], kp, hostname=self.network_manager.mqtt_broker_ip)
                    elif trigger_id in ['ki-slider', 'ki-send-btn']:
                        publish.single(MQTT_TOPICS['ki'], ki, hostname=self.network_manager.mqtt_broker_ip)
                    elif trigger_id in ['kd-slider', 'kd-send-btn']:
                        publish.single(MQTT_TOPICS['kd'], kd, hostname=self.network_manager.mqtt_broker_ip)
                    elif trigger_id in ['reference-slider', 'ref-send-btn']:
                        publish.single(MQTT_TOPICS['reference'], reference, hostname=self.network_manager.mqtt_broker_ip)

                    # Simple status since ESP32 parameters are now shown above
                    return self.t('parameters_sent_esp32')

                except Exception as e:
                    return self.t('mqtt_communication_error')

            # Simple default status
            return self.t('parameters_configured')

        # Real-time data visualization with zoom preservation
        @self.app.callback(
            Output('realtime-graph', 'figure'),
            [Input('data-refresh-interval', 'n_intervals'),
             Input('realtime-graph', 'relayoutData'),
             Input('ws-message-store', 'data')],
            prevent_initial_call=True
        )
        def update_realtime_graph(n_intervals, relayout_data, ws_data):
            # Handle zoom state updates from user interaction
            ctx = callback_context
            if ctx.triggered:
                trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
                if trigger_id == 'realtime-graph':
                    self._handle_zoom_state('realtime-graph', relayout_data)

            return self._create_data_graph('realtime-graph')

        # Connection status callback - now responds to language changes and MQTT updates
        @self.app.callback(
            Output('connection-status-indicator', 'children'),
            [Input('data-refresh-interval', 'n_intervals'),
             Input('mqtt-status-refresh', 'n_intervals'),
             Input('language-store', 'data')],
            prevent_initial_call=False
        )
        def update_connection_status(n_intervals, mqtt_intervals, language_data):
            try:
                # Update current language from store
                if language_data and 'language' in language_data:
                    self.current_language = language_data['language']

                stats = self.data_manager.get_connection_stats()

                # Status color and message based on connection (now translated)
                if stats['status'] == 'Connected':
                    color = self.colors['success']
                    icon = '🟢'
                    status_text = self.t('connected')
                elif stats['status'] == 'Connection lost':
                    color = self.colors['danger']
                    icon = '🔴'
                    status_text = self.t('connection_lost')
                elif stats['total_packets'] > 0:
                    color = self.colors['success']
                    icon = '🟢'
                    status_text = self.t('receiving_data')
                else:
                    color = self.colors['text']
                    icon = '🟡'
                    status_text = self.t('waiting_for_data_status')

                # Format last packet time with translation
                last_time = stats['last_packet_time'] if stats['last_packet_time'] != "Never" else self.t('never')

                # Add MQTT parameter status (the main thing the user wants to see!)
                mqtt_status = self._get_pid_connection_status()

                return html.Div([
                    # UDP Connection status
                    html.Div([
                        html.Span(f"{icon} {status_text}",
                                 style={'color': color, 'fontWeight': 'bold', 'marginRight': '20px'}),
                        html.Span(f"{self.t('packets')}: {stats['total_packets']}",
                                 style={'color': self.colors['text'], 'marginRight': '20px'}),
                        html.Span(f"{self.t('last')}: {last_time}",
                                 style={'color': self.colors['text']})
                    ], style={'fontSize': '14px', 'marginBottom': '8px'}),

                    # MQTT Parameter Status (NEW - this is what shows current ESP32 values)
                    html.Div([
                        mqtt_status
                    ], style={'fontSize': '14px', 'borderTop': '1px solid #eee', 'paddingTop': '8px'})
                ])
            except Exception as e:
                return html.Div(self.t('status_unavailable'),
                               style={'color': self.colors['danger'], 'fontSize': '14px'})

        # Detailed connection status for data tab
        @self.app.callback(
            Output('detailed-connection-status', 'children'),
            [Input('data-refresh-interval', 'n_intervals'),
             Input('mqtt-status-refresh', 'n_intervals')],
            prevent_initial_call=True
        )
        def update_detailed_connection_status(n_intervals, mqtt_intervals):
            # Reduced verbosity - comment out repetitive status prints
            # timestamp = time.strftime('%H:%M:%S')
            # print(f"[CONNECTION STATUS {timestamp}] Callback triggered - intervals: data={n_intervals}, mqtt={mqtt_intervals}")
            # print(f"[CONNECTION STATUS {timestamp}] MQTT sync confirmed params: {self.mqtt_sync.confirmed_params if hasattr(self, 'mqtt_sync') else 'N/A'}")

            if not self.data_manager.initialized:
                # print(f"[CONNECTION STATUS] Data manager not initialized")
                return html.Div([
                    html.P(self.t('network_not_configured'), style={'color': self.colors['warning'], 'marginBottom': '5px'}),
                    html.P(self.t('go_to_network_tab'), style={'color': self.colors['text']})
                ])

            stats = self.data_manager.get_connection_stats()
            latest_data = self.data_manager.get_latest_data()

            # Status sections
            status_color = self.colors['success'] if stats['status'] == 'Connected' else self.colors['danger']

            return html.Div([
                # Connection status
                html.Div([
                    html.Strong(self.t('status') + ": ", style={'color': self.colors['text']}),
                    html.Span(stats['status'], style={'color': status_color, 'fontWeight': 'bold'})
                ], style={'marginBottom': '10px'}),

                # Statistics
                html.Div([
                    html.Div([
                        html.Strong(self.t('total_packets_label') + ": ", style={'color': self.colors['text']}),
                        html.Span(str(stats['total_packets']))
                    ], style={'display': 'inline-block', 'marginRight': '30px'}),

                    html.Div([
                        html.Strong(self.t('last_received') + ": ", style={'color': self.colors['text']}),
                        html.Span(stats['last_packet_time'])
                    ], style={'display': 'inline-block', 'marginRight': '30px'}),

                    html.Div([
                        html.Strong(self.t('experiment_label') + ": ", style={'color': self.colors['text']}),
                        html.Span(self.t('active') if stats['experiment_active'] else self.t('stopped'),
                                style={'color': self.colors['success'] if stats['experiment_active'] else self.colors['text']})
                    ], style={'display': 'inline-block'})
                ], style={'marginBottom': '10px'}),

                # Latest data
                html.Div([
                    html.Strong(self.t('latest_data') + ": ", style={'color': self.colors['text']}),
                    html.Span(latest_data.get('full_data', self.t('no_data_received')) if latest_data else self.t('no_data_received'),
                            style={'fontFamily': 'monospace', 'backgroundColor': '#f1f1f1', 'padding': '2px 5px', 'borderRadius': '3px'})
                ]) if latest_data else html.Div([
                    html.Strong(self.t('latest_data') + ": ", style={'color': self.colors['text']}),
                    html.Span(self.t('no_data_received'), style={'color': self.colors['warning']})
                ]),

                # MQTT Parameter Status
                html.Div([
                    html.Hr(style={'margin': '15px 0'}),
                    self._get_parameter_status_display()
                ], style={'marginTop': '15px'})
            ])

        # Historical graph for data tab with zoom preservation
        @self.app.callback(
            Output('historical-graph', 'figure'),
            [Input('data-refresh-interval', 'n_intervals'),
             Input('historical-graph', 'relayoutData')]
        )
        def update_historical_graph(n_intervals, relayout_data, ws_data):
            # Handle zoom state updates from user interaction for historical graph
            ctx = callback_context
            if ctx.triggered:
                trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
                if trigger_id == 'historical-graph':
                    self._handle_zoom_state('historical-graph', relayout_data)

            return self._create_data_graph('historical-graph', title_prefix="Historical: ")

        # Data tab callbacks
        @self.app.callback(
            Output('csv-file-path', 'children'),
            Input('data-refresh-interval', 'n_intervals'),
            prevent_initial_call=True
        )
        def update_csv_path(n_intervals):
            # Show the actual active file being read from
            csv_files = glob.glob("experiment_*.csv")
            if csv_files:
                active_csv = max(csv_files, key=os.path.getmtime)
                file_size = os.path.getsize(active_csv)
                return f"{active_csv} ({file_size} bytes)"
            return self.t('configure_network_enable_logging')

        # CSV download callback
        @self.app.callback(
            Output("download-csv-file", "data"),
            Input("download-csv-btn", "n_clicks"),
            prevent_initial_call=True
        )
        def download_csv(n_clicks):
            if n_clicks:
                # Find the active CSV file
                csv_files = glob.glob("experiment_*.csv")
                if csv_files:
                    active_csv = max(csv_files, key=os.path.getmtime)
                    file_size = os.path.getsize(active_csv)

                    # Only download if file has data (more than just headers)
                    if file_size > 100:  # Has more than just headers
                        return dcc.send_file(active_csv)
                    else:
                        # File exists but is empty - no data to download
                        return None
                else:
                    # No CSV files found
                    return None
            return None


        # Step Response Parameter Callbacks
        @self.app.callback(
            Output('step-esp32-status', 'children'),
            [Input('amplitude-slider', 'value'),
             Input('amplitude-send-btn', 'n_clicks'),
             Input('duration-slider', 'value'),
             Input('duration-send-btn', 'n_clicks'),
             Input('vbatt-slider', 'value'),
             Input('vbatt-send-btn', 'n_clicks'),
             Input('direction-radio', 'value'),
             Input('mqtt-status-refresh', 'n_intervals')],
            [State('amplitude-input', 'value'),
             State('duration-input', 'value'),
             State('vbatt-input', 'value')]
        )
        def update_step_parameters(amp_slider, amp_clicks, dur_slider, dur_clicks,
                                  vbatt_slider, vbatt_clicks, direction, mqtt_intervals,
                                  amp_input, dur_input, vbatt_input):
            ctx = callback_context
            
            if not self.network_manager.selected_ip:
                return html.Div(self.t('network_not_configured'), 
                              style={'color': self.colors['warning']})
            
            if ctx.triggered:
                trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
                
                try:
                    # Determine which parameter changed and send via MQTT
                    if trigger_id in ['amplitude-slider', 'amplitude-send-btn']:
                        value = amp_input if trigger_id == 'amplitude-send-btn' else amp_slider
                        publish.single(MQTT_TOPICS['step_amplitude'], value, 
                                     hostname=self.network_manager.mqtt_broker_ip)
                    elif trigger_id in ['duration-slider', 'duration-send-btn']:
                        value = dur_input if trigger_id == 'duration-send-btn' else dur_slider
                        publish.single(MQTT_TOPICS['step_time'], value,
                                     hostname=self.network_manager.mqtt_broker_ip)
                    elif trigger_id in ['vbatt-slider', 'vbatt-send-btn']:
                        value = vbatt_input if trigger_id == 'vbatt-send-btn' else vbatt_slider
                        publish.single(MQTT_TOPICS['step_vbatt'], value,
                                     hostname=self.network_manager.mqtt_broker_ip)
                    elif trigger_id == 'direction-radio':
                        publish.single(MQTT_TOPICS['step_direction'], direction,
                                     hostname=self.network_manager.mqtt_broker_ip)
                except Exception as e:
                    return html.Div(f"{self.t('mqtt_communication_error')}: {str(e)}",
                                  style={'color': self.colors['danger']})
            
            # Display confirmed parameters from ESP32
            return self._get_step_parameter_status_display()
        
        # Step Response Graph Update
        @self.app.callback(
            Output('step-response-graph', 'figure'),
            [Input('data-refresh-interval', 'n_intervals')]
        )
        def update_step_graph(n_intervals):
            """Update step response graph with 3 traces: distance, step input, PWM"""
            try:
                # Find step response CSV files
                csv_files = glob.glob("step_response_*.csv")
                if not csv_files:
                    fig = px.line(title=self.t('no_step_data'))
                    fig.update_layout(
                        plot_bgcolor=self.colors['surface'],
                        paper_bgcolor=self.colors['background'],
                        font_color=self.colors['text']
                    )
                    return fig
                
                # Get most recent file
                active_csv = max(csv_files, key=os.path.getmtime)
                file_size = os.path.getsize(active_csv)
                
                if file_size < 150:  # File has only headers
                    fig = px.line(title=self.t('waiting_for_data'))
                    fig.update_layout(
                        plot_bgcolor=self.colors['surface'],
                        paper_bgcolor=self.colors['background'],
                        font_color=self.colors['text']
                    )
                    return fig
                
                # Read and parse data
                df = pd.read_csv(active_csv)
                
                if df.empty:
                    fig = px.line(title=self.t('waiting_for_data'))
                    fig.update_layout(
                        plot_bgcolor=self.colors['surface'],
                        paper_bgcolor=self.colors['background']
                    )
                    return fig
                
                # Create figure with 3 traces
                fig = go.Figure()
                
                # Trace 1: Distance response (output_G)
                fig.add_trace(go.Scatter(
                    x=df['time_event'] / 1000,  # Convert ms to seconds
                    y=df['output_G'],
                    mode='lines',
                    name=self.t('distance_response'),
                    line=dict(color='blue', width=2)
                ))
                
                # Trace 2: Step input
                fig.add_trace(go.Scatter(
                    x=df['time_event'] / 1000,
                    y=df['step_input'],
                    mode='lines',
                    name=self.t('step_input_label'),
                    line=dict(color='red', dash='dash', width=2)
                ))
                
                # Trace 3: PWM input
                fig.add_trace(go.Scatter(
                    x=df['time_event'] / 1000,
                    y=df['PWM_input'],
                    mode='lines',
                    name=self.t('pwm_input_label'),
                    line=dict(color='green', dash='dot', width=1.5)
                ))
                
                fig.update_layout(
                    title=f"{self.t('step_response_graph')} ({len(df)} {self.t('points')})",
                    xaxis_title=f"{self.t('time')} (s)",
                    yaxis_title=self.t('distance_cm'),
                    plot_bgcolor=self.colors['surface'],
                    paper_bgcolor=self.colors['background'],
                    font_color=self.colors['text'],
                    showlegend=True,
                    legend=dict(x=0.02, y=0.98),
                    margin=dict(l=40, r=20, t=40, b=40),
                    hovermode='x unified'
                )
                
                return fig
                
            except Exception as e:
                fig = px.line(title=f"{self.t('data_read_error')}: {str(e)}")
                fig.update_layout(
                    plot_bgcolor=self.colors['surface'],
                    paper_bgcolor=self.colors['background']
                )
                return fig

    def _get_step_parameter_status_display(self):
        """Display confirmed step response parameters from ESP32"""
        if not hasattr(self, 'mqtt_sync') or not self.mqtt_sync:
            return html.Span(self.t('mqtt_not_available'),
                           style={'color': self.colors['warning']})
        
        confirmed = self.mqtt_sync.step_confirmed_params
        has_confirmed = any(v is not None for v in confirmed.values())
        
        if has_confirmed:
            amp = f"{confirmed['amplitude']:.1f}" if confirmed['amplitude'] is not None else "?"
            time_val = f"{confirmed['time']:.1f}" if confirmed['time'] is not None else "?"
            direction = self.t('forward') if confirmed['direction'] == 1 else self.t('reverse')
            vbatt = f"{confirmed['vbatt']:.1f}" if confirmed['vbatt'] is not None else "?"
            
            return html.Div([
                html.Strong(self.t('esp32_confirmed_parameters') + ": ", 
                          style={'fontSize': '12px'}),
                html.Br(),
                html.Span(f"Amp={amp}V, Time={time_val}s, Dir={direction}, VBatt={vbatt}V",
                         style={'color': self.colors['success'], 'fontWeight': 'bold', 
                               'fontSize': '11px', 'backgroundColor': '#e8f5e8',
                               'padding': '4px 8px', 'borderRadius': '4px'}),
                html.Span(" ✓", style={'color': self.colors['success'], 'fontSize': '16px'})
            ])
        else:
            return html.Span(self.t('esp32_waiting_parameters'),
                           style={'color': self.colors['warning'], 'fontSize': '11px'})


    def run(self, host='127.0.0.1', port=8050, debug=True):
        """Run the dashboard"""
        self.app.run(host=host, port=port, debug=debug)

# Global instances
network_manager = NetworkManager()
data_manager = DataManager()

# Create UDP receiver instance
udp_receiver = UDPReceiver(data_manager)

# Create dashboard with shared instances
dashboard = TrainControlDashboard(network_manager, data_manager, udp_receiver)

# Verify all components share the same DataManager
print(f"DataManager instances match:")
print(f"  - Global data_manager: {id(data_manager)}")
print(f"  - UDP receiver data_manager: {id(udp_receiver.data_manager)}")
print(f"  - Dashboard data_manager: {id(dashboard.data_manager)}")

if __name__ == '__main__':
    print("Starting Train Control Platform...")
    print("Detecting network interfaces...")

    # Detect available interfaces
    interfaces = network_manager.detect_interfaces()
    print(f"Found {len(interfaces)} network interfaces:")
    for name, info in interfaces.items():
        print(f"  - {name}")

    # Show UDP receiver status
    print(f"\nUDP Receiver Status:")
    print(f"  - IP: {udp_receiver.ip}")
    print(f"  - Port: {udp_receiver.port}")
    print(f"  - Running: {udp_receiver.running}")
    if network_manager.selected_ip:
        print(f"  - Auto-configured: Yes (using {network_manager.selected_ip})")
    else:
        print(f"  - Auto-configured: No (configure in dashboard)")

    print("\nStarting dashboard at http://127.0.0.1:8050")
    print("Configure network settings in the 'Network Configuration' tab")

    try:
        dashboard.run(debug=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
        udp_receiver.stop()