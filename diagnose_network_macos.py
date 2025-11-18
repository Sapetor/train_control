#!/usr/bin/env python3
"""
macOS Network Diagnostic Tool
Helps diagnose why network interfaces aren't being detected by the Train Control Platform
"""

import socket
import psutil
import subprocess
import sys

print('=' * 70)
print('macOS Network Interface Diagnostic Tool')
print('=' * 70)

# Check if running on macOS
print('\n1. System Information:')
print('-' * 70)
try:
    result = subprocess.run(['uname', '-s'], capture_output=True, text=True, timeout=5)
    os_name = result.stdout.strip()
    print(f'   Operating System: {os_name}')
except:
    print('   Operating System: Unknown (uname not available)')

try:
    result = subprocess.run(['sw_vers'], capture_output=True, text=True, timeout=5)
    print(f'   macOS Version:\n{result.stdout}')
except:
    print('   macOS Version: Cannot determine (sw_vers not available)')

# Show all network interfaces
print('\n2. All Network Interfaces (from psutil):')
print('-' * 70)
all_interfaces = psutil.net_if_addrs()
stats = psutil.net_if_stats()

for iface in sorted(all_interfaces.keys()):
    print(f'\n   Interface: {iface}')

    # Show status
    if iface in stats:
        status = 'UP ✓' if stats[iface].isup else 'DOWN ✗'
        speed = stats[iface].speed
        print(f'     Status: {status}')
        print(f'     Speed: {speed} Mbps')

    # Show addresses
    for addr in all_interfaces[iface]:
        if addr.family == socket.AF_INET:  # IPv4
            print(f'     IPv4: {addr.address}')
            print(f'     Netmask: {addr.netmask}')
        elif addr.family == socket.AF_INET6:  # IPv6
            print(f'     IPv6: {addr.address[:30]}...')

# Check what interfaces would be shown in the dashboard
print('\n3. Interfaces That Will Appear in Dashboard:')
print('-' * 70)

detected_count = 0
for iface, addrs in all_interfaces.items():
    for addr in addrs:
        if addr.family == socket.AF_INET:
            ip = addr.address
            if ip and ip != '127.0.0.1' and not ip.startswith('169.254'):
                detected_count += 1
                print(f'   ✓ {iface}: {ip}')

if detected_count == 0:
    print('   ⚠️  NO INTERFACES WILL BE SHOWN IN DASHBOARD!')
    print('\n   This means:')
    print('     - All interfaces either have no IPv4 address')
    print('     - Or they only have loopback (127.x.x.x) or link-local (169.254.x.x) IPs')

# Try to get primary network interface info (macOS specific)
print('\n4. Primary Network Interface (macOS specific):')
print('-' * 70)
try:
    result = subprocess.run(['route', '-n', 'get', 'default'],
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        for line in result.stdout.split('\n'):
            if 'interface:' in line:
                primary_iface = line.split(':')[1].strip()
                print(f'   Primary Interface: {primary_iface}')

                # Check if this interface has an IPv4 address
                if primary_iface in all_interfaces:
                    has_ipv4 = False
                    for addr in all_interfaces[primary_iface]:
                        if addr.family == socket.AF_INET:
                            print(f'   ✓ Has IPv4: {addr.address}')
                            has_ipv4 = True
                    if not has_ipv4:
                        print(f'   ✗ NO IPv4 ADDRESS on primary interface!')
                        print(f'   This is why it does not appear in the dashboard.')
except Exception as e:
    print(f'   Cannot determine (route command failed): {e}')

# Check networksetup
try:
    result = subprocess.run(['networksetup', '-listallhardwareports'],
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print('\n5. Hardware Network Ports (networksetup):')
        print('-' * 70)
        print(result.stdout)
except Exception as e:
    print(f'\n5. Cannot check networksetup: {e}')

# Recommendations
print('\n6. Recommendations:')
print('-' * 70)

if detected_count == 0:
    print('   ⚠️  No usable network interfaces detected!')
    print('\n   To fix this:')
    print('     1. Make sure you are connected to WiFi or Ethernet')
    print('     2. Open System Preferences → Network')
    print('     3. Check that your connection shows "Connected"')
    print('     4. Verify you have an IP address assigned')
    print('     5. Try disconnecting and reconnecting to the network')
    print('\n   If you are using a VPN or cloud environment:')
    print('     - The virtual interface shown may be the only one available')
    print('     - Use that IP address for the dashboard')
elif detected_count == 1:
    print('   Only 1 interface detected.')
    print('   If this is not your expected network:')
    print('     1. Check System Preferences → Network')
    print('     2. Make sure WiFi/Ethernet is connected')
    print('     3. Verify the interface has an IPv4 address')
else:
    print(f'   ✓ Found {detected_count} usable interfaces.')
    print('   The dashboard should work correctly!')

print('\n' + '=' * 70)
print('Diagnostic complete. Please share this output if you need further help.')
print('=' * 70)
