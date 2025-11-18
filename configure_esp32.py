#!/usr/bin/env python3
"""
ESP32 Train Configuration Tool
Configures ESP32 via USB serial port
"""

import serial
import serial.tools.list_ports
import sys
import time
import argparse

def list_serial_ports():
    """List all available serial ports"""
    ports = serial.tools.list_ports.comports()
    return [(port.device, port.description) for port in ports]

def send_command(ser, command, wait_time=2):
    """Send command to ESP32 and print response"""
    print(f"\n📤 Sending: {command}")
    ser.write((command + '\n').encode())
    time.sleep(wait_time)

    # Read all available response
    response = ""
    while ser.in_waiting > 0:
        response += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        time.sleep(0.1)

    if response:
        print("📥 Response:")
        print(response)
    else:
        print("⚠️  No response received")

    return response

def main():
    parser = argparse.ArgumentParser(description='Configure ESP32 Train via Serial Port')
    parser.add_argument('--port', '-p', help='Serial port (e.g., COM3 or /dev/ttyUSB0)')
    parser.add_argument('--train', '-t', help='Train ID (e.g., trainA)')
    parser.add_argument('--udp', '-u', type=int, help='UDP port (e.g., 5555)')
    parser.add_argument('--broker', '-b', help='MQTT broker IP (e.g., 192.168.1.100)')
    parser.add_argument('--status', '-s', action='store_true', help='Show current configuration')
    parser.add_argument('--reset', '-r', action='store_true', help='Reset configuration')
    parser.add_argument('--list', '-l', action='store_true', help='List available serial ports')

    args = parser.parse_args()

    # List ports if requested
    if args.list:
        print("\n🔌 Available Serial Ports:")
        print("=" * 60)
        ports = list_serial_ports()
        if ports:
            for device, description in ports:
                print(f"  {device}: {description}")
        else:
            print("  No serial ports found")
        print()
        return

    # Check if port is specified
    if not args.port:
        print("❌ Error: Please specify a serial port with --port")
        print("\nAvailable ports:")
        for device, description in list_serial_ports():
            print(f"  {device}: {description}")
        print("\nExample: python configure_esp32.py --port COM3 --train trainA --udp 5555")
        sys.exit(1)

    # Open serial connection
    try:
        print(f"\n🔗 Connecting to {args.port} at 115200 baud...")
        ser = serial.Serial(args.port, 115200, timeout=1)
        time.sleep(2)  # Wait for ESP32 to reset

        # Clear any initial output
        while ser.in_waiting > 0:
            ser.read(ser.in_waiting)
            time.sleep(0.1)

        print("✅ Connected!")

        # Execute commands based on arguments
        if args.status:
            send_command(ser, "STATUS")

        if args.train and args.udp:
            command = f"SET_TRAIN:{args.train}:{args.udp}"
            send_command(ser, command, wait_time=3)
        elif args.train or args.udp:
            print("⚠️  Warning: Both --train and --udp must be specified together")

        if args.broker:
            command = f"SET_BROKER:{args.broker}"
            send_command(ser, command, wait_time=3)

        if args.reset:
            print("\n⚠️  WARNING: This will erase all configuration!")
            confirm = input("Type 'yes' to confirm: ")
            if confirm.lower() == 'yes':
                send_command(ser, "RESET_TRAIN", wait_time=3)
            else:
                print("Reset cancelled")

        # If no specific action, show status
        if not (args.status or args.train or args.broker or args.reset):
            print("\n📊 Showing current configuration...")
            send_command(ser, "STATUS")
            print("\n💡 Tip: Use --help to see all available options")

        ser.close()
        print("\n✅ Done!")

    except serial.SerialException as e:
        print(f"❌ Error opening serial port: {e}")
        print("\nMake sure:")
        print("  1. The ESP32 is connected via USB")
        print("  2. No other program is using the serial port")
        print("  3. You have permission to access the port (try 'sudo' on Linux)")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        if 'ser' in locals() and ser.is_open:
            ser.close()
        sys.exit(0)

if __name__ == "__main__":
    print("=" * 60)
    print("ESP32 Train Configuration Tool")
    print("=" * 60)
    main()
