#!/usr/bin/env python3
"""
Test script to verify Train Control Platform improvements
"""

import socket
import time
import random
import threading

def simulate_pid_data(ip='127.0.0.1', port=5555, duration=10):
    """Simulate PID control data from ESP32"""
    print(f"Starting PID data simulation to {ip}:{port}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    start_time = time.time()
    packet_count = 0
    
    while time.time() - start_time < duration:
        # Simulate PID data format: time_event,input,referencia,error,kp,ki,kd,output_PID
        timestamp = int((time.time() - start_time) * 1000)
        distance = 20 + random.uniform(-5, 5)  # Distance around 20cm
        reference = 25.0  # Target distance
        error = reference - distance
        kp, ki, kd = 10.0, 5.0, 2.0  # PID constants
        output_pid = kp * error  # Simplified PID output
        
        data = f"{timestamp},{distance:.2f},{reference:.2f},{error:.2f},{kp},{ki},{kd},{output_pid:.2f}"
        
        try:
            sock.sendto(data.encode(), (ip, port))
            packet_count += 1
            if packet_count % 10 == 0:
                print(f"Sent {packet_count} PID packets")
            time.sleep(0.1)  # 10Hz data rate
        except Exception as e:
            print(f"Error sending PID data: {e}")
            break
    
    sock.close()
    print(f"PID simulation complete. Sent {packet_count} packets.")

def simulate_step_response_data(ip='127.0.0.1', port=5555, duration=10):
    """Simulate Step Response data from ESP32"""
    print(f"Starting Step Response data simulation to {ip}:{port}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    start_time = time.time()
    packet_count = 0
    
    while time.time() - start_time < duration:
        # Simulate Step Response format: time2sinc,time_event,motor_dir,v_batt,output_G,step_input,PWM_input
        time2sync = int((time.time() - start_time) * 1000)
        time_event = time2sync
        motor_dir = 1  # Forward
        v_batt = 12.0 + random.uniform(-0.5, 0.5)  # Battery voltage
        output_g = 15.0 + random.uniform(-3, 3)  # System output
        step_input = 5.0 if time2sync < 5000 else 10.0  # Step at 5 seconds
        pwm_input = step_input * 25.5  # PWM value
        
        data = f"{time2sync},{time_event},{motor_dir},{v_batt:.2f},{output_g:.2f},{step_input:.2f},{pwm_input:.2f}"
        
        try:
            sock.sendto(data.encode(), (ip, port))
            packet_count += 1
            if packet_count % 10 == 0:
                print(f"Sent {packet_count} Step Response packets")
            time.sleep(0.1)  # 10Hz data rate
        except Exception as e:
            print(f"Error sending Step Response data: {e}")
            break
    
    sock.close()
    print(f"Step Response simulation complete. Sent {packet_count} packets.")

def test_mode_switching(ip='127.0.0.1', port=5555):
    """Test switching between PID and Step Response modes"""
    print("\n=== Testing Mode Switching ===")
    print("1. Start with PID data for 5 seconds...")
    simulate_pid_data(ip, port, 5)
    
    print("\n2. Switch to Step Response tab in UI and wait...")
    time.sleep(3)
    
    print("\n3. Send Step Response data for 5 seconds...")
    simulate_step_response_data(ip, port, 5)
    
    print("\n4. Switch back to PID tab in UI and wait...")
    time.sleep(3)
    
    print("\n5. Send PID data again for 5 seconds...")
    simulate_pid_data(ip, port, 5)
    
    print("\n=== Mode Switching Test Complete ===")

def test_queue_overflow(ip='127.0.0.1', port=5555):
    """Test data queue overflow handling"""
    print("\n=== Testing Queue Overflow Handling ===")
    print("Sending data at high rate to test queue overflow...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    start_time = time.time()
    packet_count = 0
    
    # Send 5000 packets as fast as possible
    for i in range(5000):
        timestamp = int((time.time() - start_time) * 1000)
        distance = 20 + random.uniform(-5, 5)
        data = f"{timestamp},{distance:.2f},25.0,5.0,10.0,5.0,2.0,50.0"
        
        try:
            sock.sendto(data.encode(), (ip, port))
            packet_count += 1
            # No sleep - send as fast as possible
        except Exception as e:
            print(f"Error: {e}")
            break
    
    sock.close()
    elapsed = time.time() - start_time
    print(f"Sent {packet_count} packets in {elapsed:.2f} seconds")
    print(f"Rate: {packet_count/elapsed:.0f} packets/second")
    print("Check console for queue overflow warnings")
    print("\n=== Queue Overflow Test Complete ===")

def main():
    print("Train Control Platform Test Suite")
    print("==================================")
    print("\nMake sure the Train Control Platform is running!")
    print("Start it with: python train_control_platform.py")
    
    # Get network config
    ip = input("\nEnter IP address (press Enter for 127.0.0.1): ").strip()
    if not ip:
        ip = '127.0.0.1'
    
    port_str = input("Enter UDP port (press Enter for 5555): ").strip()
    port = int(port_str) if port_str else 5555
    
    print(f"\nUsing {ip}:{port} for testing")
    
    while True:
        print("\n--- Test Menu ---")
        print("1. Test PID data simulation")
        print("2. Test Step Response data simulation")
        print("3. Test mode switching")
        print("4. Test queue overflow handling")
        print("5. Run all tests")
        print("0. Exit")
        
        choice = input("\nSelect test: ").strip()
        
        if choice == '1':
            simulate_pid_data(ip, port)
        elif choice == '2':
            simulate_step_response_data(ip, port)
        elif choice == '3':
            test_mode_switching(ip, port)
        elif choice == '4':
            test_queue_overflow(ip, port)
        elif choice == '5':
            print("\n=== Running All Tests ===")
            simulate_pid_data(ip, port, 5)
            time.sleep(2)
            simulate_step_response_data(ip, port, 5)
            time.sleep(2)
            test_mode_switching(ip, port)
            time.sleep(2)
            test_queue_overflow(ip, port)
            print("\n=== All Tests Complete ===")
        elif choice == '0':
            break
        else:
            print("Invalid choice")
    
    print("\nTest suite complete!")

if __name__ == '__main__':
    main()
