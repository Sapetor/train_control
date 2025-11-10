"""
Simple Train Launcher
======================
Launches a single-train dashboard for a specific train ID.

Usage:
    python launch_train.py trainA       # Launch Train A on port 8050
    python launch_train.py trainB 8051  # Launch Train B on port 8051
    python launch_train.py trainC 8052  # Launch Train C on port 8052
"""

import sys
import json

# Import train_control_platform module first
import train_control_platform
from train_control_platform import (
    TrainControlDashboard,
    NetworkManager,
    DataManager,
    StepResponseDataManager,
    DeadbandDataManager,
    UDPReceiver,
    MQTTParameterSync,
    MQTT_TOPICS
)

def load_train_config(train_id):
    """Load configuration for a specific train"""
    try:
        with open('trains_config.json', 'r') as f:
            config = json.load(f)

        if train_id not in config['trains']:
            print(f"ERROR: Train '{train_id}' not found in trains_config.json")
            print(f"Available trains: {list(config['trains'].keys())}")
            sys.exit(1)

        train = config['trains'][train_id]
        if not train.get('enabled', True):
            print(f"ERROR: Train '{train_id}' is disabled in configuration")
            sys.exit(1)

        return train, config

    except FileNotFoundError:
        print("ERROR: trains_config.json not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print("ERROR: trains_config.json is not valid JSON")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python launch_train.py <train_id> [port]")
        print("Example: python launch_train.py trainA")
        print("Example: python launch_train.py trainB 8051")
        sys.exit(1)

    train_id = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8050

    # Load train configuration
    train_config, global_config = load_train_config(train_id)

    print(f"\n{'='*60}")
    print(f"LAUNCHING TRAIN: {train_config['name']} ({train_id})")
    print(f"{'='*60}")
    print(f"UDP Port:      {train_config['udp_port']}")
    print(f"MQTT Prefix:   {train_config['mqtt_prefix']}")
    print(f"Dashboard:     http://127.0.0.1:{port}")
    print(f"{'='*60}\n")

    # CRITICAL: Override global MQTT_TOPICS before creating dashboard
    # This ensures all MQTT operations use train-specific topics
    print(f"[MQTT] Generating train-specific topics...")
    mqtt_prefix = train_config['mqtt_prefix']

    for key in list(MQTT_TOPICS.keys()):
        original_topic = MQTT_TOPICS[key]
        if original_topic.startswith('trenes/'):
            # Replace 'trenes/' with train-specific prefix
            train_control_platform.MQTT_TOPICS[key] = original_topic.replace('trenes/', f'{mqtt_prefix}/', 1)
        else:
            # Add prefix if topic doesn't start with trenes/
            train_control_platform.MQTT_TOPICS[key] = f'{mqtt_prefix}/{original_topic}'

    print(f"[MQTT] Topics configured for {mqtt_prefix}")
    print(f"[MQTT] Example topics:")
    print(f"  - Kp:   {train_control_platform.MQTT_TOPICS['kp']}")
    print(f"  - Sync: {train_control_platform.MQTT_TOPICS['sync']}")
    print(f"  - Step: {train_control_platform.MQTT_TOPICS['step_sync']}")
    print()

    # Create train-specific data managers
    data_manager = DataManager(train_id=train_id)
    step_data_manager = StepResponseDataManager(train_id=train_id)
    deadband_data_manager = DeadbandDataManager(train_id=train_id)

    # Create UDP receiver for this train
    udp_receiver = UDPReceiver(
        data_manager=data_manager,
        port=train_config['udp_port']
    )

    # Create network manager (shared)
    network_manager = NetworkManager()

    # Create dashboard for this train
    dashboard = TrainControlDashboard(
        network_manager=network_manager,
        data_manager=data_manager,
        udp_receiver=udp_receiver
    )

    # Override data managers with train-specific ones
    dashboard.step_data_manager = step_data_manager
    dashboard.deadband_data_manager = deadband_data_manager

    print(f"[TRAIN {train_id}] Dashboard initialized")
    print(f"[TRAIN {train_id}] MQTT topics using prefix: {mqtt_prefix}")
    print(f"[TRAIN {train_id}] UDP receiver on port: {train_config['udp_port']}")

    # CRITICAL FIX: Auto-configure network and start MQTT connection
    # This allows parameter updates to work immediately without manual network config
    print(f"\n[NETWORK] Auto-configuring network for {train_id}...")

    # Set network configuration from trains_config.json
    network_ip = global_config.get('network_ip', '192.168.137.1')  # Default or from config
    mqtt_broker_ip = global_config.get('mqtt_broker_ip', network_ip)

    network_manager.set_selected_ip(network_ip)
    network_manager.mqtt_broker_ip = mqtt_broker_ip

    # Start UDP receiver
    udp_receiver.ip = network_ip
    udp_receiver.port = train_config['udp_port']
    udp_success = udp_receiver.start()

    # Start MQTT client for parameter synchronization
    mqtt_success = dashboard.mqtt_sync.connect(mqtt_broker_ip, network_manager.mqtt_port)

    if udp_success and mqtt_success:
        print(f"[NETWORK] ✓ UDP receiver started on {network_ip}:{train_config['udp_port']}")
        print(f"[NETWORK] ✓ MQTT client connected to {mqtt_broker_ip}:{network_manager.mqtt_port}")
        print(f"[NETWORK] ✓ Ready to send/receive parameters")
    elif udp_success:
        print(f"[NETWORK] ✓ UDP receiver started")
        print(f"[NETWORK] ✗ MQTT connection failed - parameters won't sync")
    else:
        print(f"[NETWORK] ✗ Network initialization failed")

    print(f"\nStarting dashboard on http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop\n")

    # Disable Flask request logging to reduce terminal spam
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)  # Only show errors, not every request

    # Run dashboard
    dashboard.run(
        host='127.0.0.1',
        port=port,
        debug=False,
        use_reloader=False
    )

if __name__ == '__main__':
    main()
