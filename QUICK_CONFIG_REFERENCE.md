# ESP32 Universal Firmware - Quick Reference Card

## Serial Commands (115200 baud)

```
SET_TRAIN:trainID:port    Configure train
GET_TRAIN                 Show configuration
RESET_TRAIN               Clear configuration
STATUS                    Show status
```

## Python Tool

```bash
# Interactive mode
python configure_train.py

# Direct config
python configure_train.py --train trainA --udp 5555 --port COM3

# Check config
python configure_train.py --get-config --port COM3
```

## LED Status

| Pattern | Meaning |
|---------|---------|
| Fast blink (200ms) | Not configured |
| Slow blink (1s) | Connecting |
| Solid ON | Ready |
| 3 flashes | Config saved |

## Example Configurations

| Train | Command |
|-------|---------|
| Train A | `SET_TRAIN:trainA:5555` |
| Train B | `SET_TRAIN:trainB:5556` |
| Train C | `SET_TRAIN:trainC:5557` |

## MQTT Topics Generated

For `trainA`:
- `trenes/trainA/sync` - Start PID
- `trenes/trainA/carroD/p` - Set Kp
- `trenes/trainA/step/sync` - Start Step Response
- `trenes/trainA/deadband/sync` - Start Deadband Cal

## Troubleshooting Quick Fixes

| Issue | Solution |
|-------|----------|
| Fast LED blink | Send `SET_TRAIN:trainA:5555` |
| Garbled serial text | Set baud to 115200 |
| Config not saving | Use alphanumeric ID only |
| MQTT not working | Check train ID matches dashboard |
| UDP not received | Verify UDP port is unique |

## Setup Checklist

- [ ] Upload `tren_esp_universal.ino` to ESP32
- [ ] Connect serial monitor (115200 baud)
- [ ] Send `SET_TRAIN:trainID:port` command
- [ ] Wait for 3 LED flashes + reboot
- [ ] Verify with `GET_TRAIN` command
- [ ] Check WiFi connection (IP shown)
- [ ] Check MQTT connection (topics shown)
- [ ] Test UDP data in dashboard
- [ ] Label ESP32 physically

## Port Assignments Tracker

| ESP32 # | Train ID | UDP Port | Date | Location |
|---------|----------|----------|------|----------|
| 1 | trainA | 5555 | | |
| 2 | trainB | 5556 | | |
| 3 | trainC | 5557 | | |
| 4 | | 5558 | | |
| 5 | | 5559 | | |

---
**Print this page for quick reference during configuration**
