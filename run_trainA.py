"""
Train A Launcher
================
Launches Train Control Dashboard for Train A

Configuration:
- Dashboard: http://127.0.0.1:8050
- UDP Port: 5555
- MQTT Topics: trenes/trainA/*
- ESP32 Config: SET_TRAIN:trainA:5555
"""

from train_control_platform import NetworkManager, DataManager, UDPReceiver, TrainControlDashboard

if __name__ == '__main__':
    print("=" * 60)
    print("  TRAIN A CONTROL DASHBOARD")
    print("=" * 60)
    print("  Dashboard URL: http://127.0.0.1:8050")
    print("  UDP Port: 5555")
    print("  MQTT Topics: trenes/trainA/*")
    print("=" * 60)
    print()

    # Create instances
    network_manager = NetworkManager()
    data_manager = DataManager(train_id='trainA')
    udp_receiver = UDPReceiver(data_manager)

    # Create dashboard
    dashboard = TrainControlDashboard(network_manager, data_manager, udp_receiver)

    # Run on default port 8050
    dashboard.run(host='127.0.0.1', port=8050, debug=False, use_reloader=False)
