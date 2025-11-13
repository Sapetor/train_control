#!/bin/bash
# MQTT Debug Script - Test if messages are being published

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== MQTT Debug Test ===${NC}\n"

# Get broker IP from user
read -p "Enter MQTT Broker IP (from dashboard Network tab): " BROKER_IP

echo -e "\n${YELLOW}Monitoring ALL MQTT topics for 30 seconds...${NC}"
echo -e "${YELLOW}Actions to try:${NC}"
echo -e "  1. Click 'Start Experiment' in PID tab"
echo -e "  2. Change Kp parameter"
echo -e "  3. Click 'Start Step Response'"
echo -e "  4. Click 'Start Deadband Calibration'"
echo -e "\n${GREEN}Listening...${NC}\n"

# Monitor all topics under trenes/
timeout 30 mosquitto_sub -h $BROKER_IP -t "trenes/#" -v

echo -e "\n${YELLOW}=== Test Complete ===${NC}"
echo -e "\nDid you see any messages?"
echo -e "  ${GREEN}YES${NC} → ESP32 should receive them (check ESP32 serial)"
echo -e "  ${RED}NO${NC}  → Dashboard not publishing (check MQTT broker running)"
