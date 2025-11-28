"""
Train E Launcher
================
Launches Train Control Dashboard for Train E

Configuration:
- Dashboard: http://127.0.0.1:8054
- UDP Port: 5559
- MQTT Topics: trenes/trainE/*
- ESP32 Config: SET_TRAIN:trainE:5559
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
    print("  TRAIN E CONTROL DASHBOARD")
    print("=" * 60)
    print("  Dashboard URL: http://127.0.0.1:8054")
    print("  UDP Port: 5559")
    print("  MQTT Topics: trenes/trainE/*")
    print("=" * 60)
    print()

    # Create train config
    train_config = TrainConfig(
        id='trainE',
        name='Train E',
        udp_port=5559,
        mqtt_prefix='trenes/trainE'
    )

    # Create instances
    network_manager = NetworkManager()
    data_manager = DataManager(train_id='trainE')
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
            dashboard.mqtt_topics[key] = topic.replace('trenes/', 'trenes/trainE/', 1)
        else:
            dashboard.mqtt_topics[key] = f'trenes/trainE/{topic}'

    # Initialize MQTT with train-specific topics
    dashboard._initialize_mqtt_sync()

    # Set correct UDP port for this train
    udp_receiver.port = train_config.udp_port

    # NOW create layout and callbacks with correct train config
    dashboard.setup_layout()

    # Assign layout to app (needed because train_config is set)
    dashboard.app.layout = dashboard.layout

    dashboard.setup_callbacks()

    # Run on port 8054
    # Use '0.0.0.0' to allow access from other computers on the network
    # Use '127.0.0.1' for localhost-only access
    # Directly call Flask's run method to ensure correct binding
    dashboard.app.server.run(host='0.0.0.0', port=8054, debug=False, use_reloader=False)

