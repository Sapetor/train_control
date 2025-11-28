"""
Train D Launcher
================
Launches Train Control Dashboard for Train D

Configuration:
- Dashboard: http://127.0.0.1:8053
- UDP Port: 5558
- MQTT Topics: trenes/trainD/*
- ESP32 Config: SET_TRAIN:trainD:5558
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
    print("  TRAIN D CONTROL DASHBOARD")
    print("=" * 60)
    print("  Dashboard URL: http://127.0.0.1:8053")
    print("  UDP Port: 5558")
    print("  MQTT Topics: trenes/trainD/*")
    print("=" * 60)
    print()

    # Create train config
    train_config = TrainConfig(
        id='trainD',
        name='Train D',
        udp_port=5558,
        mqtt_prefix='trenes/trainD'
    )

    # Create instances
    network_manager = NetworkManager()
    data_manager = DataManager(train_id='trainD')
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
            dashboard.mqtt_topics[key] = topic.replace('trenes/', 'trenes/trainD/', 1)
        else:
            dashboard.mqtt_topics[key] = f'trenes/trainD/{topic}'

    # Initialize MQTT with train-specific topics
    dashboard._initialize_mqtt_sync()

    # Set correct UDP port for this train
    udp_receiver.port = train_config.udp_port

    # NOW create layout and callbacks with correct train config
    dashboard.setup_layout()

    # Assign layout to app (needed because train_config is set)
    dashboard.app.layout = dashboard.layout

    dashboard.setup_callbacks()

    # Run on port 8053
    # Use '0.0.0.0' to allow access from other computers on the network
    # Use '127.0.0.1' for localhost-only access
    # Directly call Flask's run method to ensure correct binding
    dashboard.app.server.run(host='0.0.0.0', port=8053, debug=False, use_reloader=False)
