#!/usr/bin/env python3
"""
ESP32 Train Configuration Tool
Configures universal train firmware via serial commands

Usage:
    python configure_train.py               # Auto-detect COM port and interactive mode
    python configure_train.py --port COM3   # Specify COM port
    python configure_train.py --train trainA --udp 5555 --port COM3  # Direct config
"""

import serial
import serial.tools.list_ports
import time
import sys
import argparse

class TrainConfigurator:
    def __init__(self, port=None, baudrate=115200, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

    def detect_esp32_port(self):
        """Auto-detect ESP32 COM port"""
        print("\nDetecting ESP32 devices...")
        ports = serial.tools.list_ports.comports()

        esp32_ports = []
        for port in ports:
            # ESP32 typically shows as CP210x or CH340
            if any(keyword in port.description.upper() for keyword in ['CP210', 'CH340', 'USB-SERIAL', 'USB SERIAL', 'UART']):
                esp32_ports.append(port)
                print(f"  Found: {port.device} - {port.description}")

        if not esp32_ports:
            print("\n⚠ No ESP32 devices detected!")
            print("Available ports:")
            for port in ports:
                print(f"  {port.device} - {port.description}")
            return None

        if len(esp32_ports) == 1:
            print(f"\n✓ Auto-selected: {esp32_ports[0].device}")
            return esp32_ports[0].device

        # Multiple ESP32s found - let user choose
        print("\nMultiple ESP32 devices found:")
        for i, port in enumerate(esp32_ports):
            print(f"  [{i+1}] {port.device} - {port.description}")

        while True:
            try:
                choice = int(input("\nSelect port (1-{}): ".format(len(esp32_ports))))
                if 1 <= choice <= len(esp32_ports):
                    selected_port = esp32_ports[choice-1].device
                    print(f"✓ Selected: {selected_port}")
                    return selected_port
            except (ValueError, KeyboardInterrupt):
                print("Invalid selection")
                return None

    def connect(self):
        """Connect to ESP32 serial port"""
        if not self.port:
            self.port = self.detect_esp32_port()
            if not self.port:
                return False

        try:
            print(f"\nConnecting to {self.port} at {self.baudrate} baud...")
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            time.sleep(2)  # Wait for ESP32 to reset

            # Flush any startup messages
            self.serial.reset_input_buffer()

            print("✓ Connected!")
            return True

        except serial.SerialException as e:
            print(f"✗ Failed to connect: {e}")
            return False

    def disconnect(self):
        """Disconnect from serial port"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("\nDisconnected.")

    def send_command(self, command):
        """Send command to ESP32 and return response"""
        if not self.serial or not self.serial.is_open:
            print("✗ Not connected!")
            return None

        try:
            # Send command
            self.serial.write((command + '\n').encode())
            time.sleep(0.5)

            # Read response (multiple lines)
            response = []
            while self.serial.in_waiting:
                line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    response.append(line)
                    print(f"  {line}")
                time.sleep(0.05)

            return response

        except Exception as e:
            print(f"✗ Error sending command: {e}")
            return None

    def configure_train(self, train_id, udp_port):
        """Configure train with ID and UDP port"""
        print(f"\n{'='*50}")
        print(f"Configuring ESP32:")
        print(f"  Train ID: {train_id}")
        print(f"  UDP Port: {udp_port}")
        print(f"{'='*50}\n")

        command = f"SET_TRAIN:{train_id}:{udp_port}"
        print(f"Sending: {command}")

        response = self.send_command(command)

        if response:
            # Check for success
            if any('Configuration saved' in line for line in response):
                print("\n✓ Configuration saved successfully!")
                print("ESP32 will reboot in 3 seconds...")
                time.sleep(3)
                return True
            elif any('ERROR' in line for line in response):
                print("\n✗ Configuration failed!")
                return False

        return False

    def get_configuration(self):
        """Get current configuration from ESP32"""
        print("\nQuerying current configuration...")
        return self.send_command("GET_TRAIN")

    def get_status(self):
        """Get ESP32 status"""
        print("\nQuerying status...")
        return self.send_command("STATUS")

    def reset_configuration(self):
        """Reset ESP32 configuration"""
        print("\nResetting configuration...")
        confirm = input("Are you sure you want to reset? (yes/no): ")

        if confirm.lower() == 'yes':
            self.send_command("RESET_TRAIN")
            print("\nESP32 will reboot...")
            return True
        else:
            print("Reset cancelled.")
            return False

    def interactive_menu(self):
        """Interactive configuration menu"""
        print("\n" + "="*50)
        print("ESP32 Train Configuration Tool")
        print("="*50)

        if not self.connect():
            return

        while True:
            print("\n--- Main Menu ---")
            print("1. Configure Train (Set ID + UDP Port)")
            print("2. Get Current Configuration")
            print("3. Get Status")
            print("4. Reset Configuration")
            print("5. Exit")

            try:
                choice = input("\nSelect option (1-5): ")

                if choice == '1':
                    train_id = input("Enter Train ID (e.g., trainA): ").strip()
                    udp_port_str = input("Enter UDP Port (e.g., 5555): ").strip()

                    try:
                        udp_port = int(udp_port_str)
                        if 1024 <= udp_port <= 65535:
                            self.configure_train(train_id, udp_port)
                        else:
                            print("✗ Port must be between 1024 and 65535")
                    except ValueError:
                        print("✗ Invalid port number")

                elif choice == '2':
                    self.get_configuration()

                elif choice == '3':
                    self.get_status()

                elif choice == '4':
                    self.reset_configuration()

                elif choice == '5':
                    break

                else:
                    print("Invalid option")

            except KeyboardInterrupt:
                print("\nExiting...")
                break

        self.disconnect()

def main():
    parser = argparse.ArgumentParser(
        description='ESP32 Train Configuration Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode with auto-detection
  python configure_train.py

  # Specify COM port for interactive mode
  python configure_train.py --port COM3

  # Direct configuration (non-interactive)
  python configure_train.py --train trainA --udp 5555 --port COM3

  # Get current configuration
  python configure_train.py --get-config --port COM3

  # Reset configuration
  python configure_train.py --reset --port COM3
        """
    )

    parser.add_argument('--port', help='Serial port (e.g., COM3 or /dev/ttyUSB0)')
    parser.add_argument('--train', help='Train ID (e.g., trainA, trainB)')
    parser.add_argument('--udp', type=int, help='UDP port number (e.g., 5555)')
    parser.add_argument('--get-config', action='store_true', help='Get current configuration')
    parser.add_argument('--reset', action='store_true', help='Reset configuration')
    parser.add_argument('--baudrate', type=int, default=115200, help='Baud rate (default: 115200)')

    args = parser.parse_args()

    configurator = TrainConfigurator(port=args.port, baudrate=args.baudrate)

    # Direct configuration mode
    if args.train and args.udp:
        if not configurator.connect():
            sys.exit(1)

        success = configurator.configure_train(args.train, args.udp)
        configurator.disconnect()
        sys.exit(0 if success else 1)

    # Get configuration mode
    elif args.get_config:
        if not configurator.connect():
            sys.exit(1)

        configurator.get_configuration()
        configurator.disconnect()
        sys.exit(0)

    # Reset mode
    elif args.reset:
        if not configurator.connect():
            sys.exit(1)

        configurator.reset_configuration()
        configurator.disconnect()
        sys.exit(0)

    # Interactive mode (default)
    else:
        configurator.interactive_menu()

if __name__ == "__main__":
    main()
