"""
Train C Launcher
================
Launches Train Control Dashboard for Train C

Configuration:
- Dashboard: http://127.0.0.1:8052
- UDP Port: 5557
- MQTT Topics: trenes/trainC/*
- ESP32 Config: SET_TRAIN:trainC:5557
"""

from train_control_platform import NetworkManager, DataManager, UDPReceiver, TrainControlDashboard, MQTT_TOPICS
from dataclasses import dataclass

@dataclass
class TrainConfig:
    id: str
    name: str
    udp_port: int
    mqtt_prefix: str

if __name__ == '__main__':
    print("=" * 60)
    print("  TRAIN C CONTROL DASHBOARD")
    print("=" * 60)
    print("  Dashboard URL: http://127.0.0.1:8052")
    print("  UDP Port: 5557")
    print("  MQTT Topics: trenes/trainC/*")
    print("=" * 60)
    print()

    # Create train config
    train_config = TrainConfig(
        id='trainC',
        name='Train C',
        udp_port=5557,
        mqtt_prefix='trenes/trainC'
    )

    # Create instances
    network_manager = NetworkManager()
    data_manager = DataManager(train_id='trainC')
    udp_receiver = UDPReceiver(data_manager)

    # Create dashboard with skip_setup=True (we'll configure before setting up)
    dashboard = TrainControlDashboard(
        network_manager,
        data_manager,
        udp_receiver,
        skip_setup=True  # Don't create layout/callbacks yet
    )

    # Set train config for multi-train mode
    dashboard.train_config = train_config

    # Generate train-specific MQTT topics
    dashboard.mqtt_topics = {}
    for key, topic in MQTT_TOPICS.items():
        if topic.startswith('trenes/'):
            dashboard.mqtt_topics[key] = topic.replace('trenes/', 'trenes/trainC/', 1)
        else:
            dashboard.mqtt_topics[key] = f'trenes/trainC/{topic}'

    # Initialize MQTT with train-specific topics
    dashboard._initialize_mqtt_sync()

    # Set correct UDP port for this train
    udp_receiver.port = train_config.udp_port

    # NOW create layout and callbacks with correct train config
    dashboard.setup_layout()

    # Assign layout to app (needed because train_config is set)
    dashboard.app.layout = dashboard.layout

    dashboard.setup_callbacks()

    # Run on port 8052
    # Use '0.0.0.0' to allow access from other computers on the network
    # Use '127.0.0.1' for localhost-only access
    # Directly call Flask's run method to ensure correct binding
    dashboard.app.server.run(host='0.0.0.0', port=8052, debug=False, use_reloader=False)
