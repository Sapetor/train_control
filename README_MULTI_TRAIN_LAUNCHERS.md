# Multi-Train Dashboard Launchers

These scripts allow you to run multiple independent train dashboards simultaneously, each on its own port.

## Quick Start

### Running a Single Train

**Train A (default):**
```bash
python run_trainA.py
```
Access at: http://127.0.0.1:8050

**Train B:**
```bash
python run_trainB.py
```
Access at: http://127.0.0.1:8051

**Train C:**
```bash
python run_trainC.py
```
Access at: http://127.0.0.1:8052

### Running Multiple Trains Simultaneously

Open multiple terminal windows:

**Terminal 1:**
```bash
python run_trainA.py
```

**Terminal 2:**
```bash
python run_trainB.py
```

**Terminal 3:**
```bash
python run_trainC.py
```

Then access each dashboard:
- Train A: http://127.0.0.1:8050
- Train B: http://127.0.0.1:8051
- Train C: http://127.0.0.1:8052

## Configuration Summary

| Train | Dashboard URL | UDP Port | MQTT Topics | ESP32 Config Command |
|-------|--------------|----------|-------------|---------------------|
| Train A | http://127.0.0.1:8050 | 5555 | `trenes/trainA/*` | `SET_TRAIN:trainA:5555` |
| Train B | http://127.0.0.1:8051 | 5556 | `trenes/trainB/*` | `SET_TRAIN:trainB:5556` |
| Train C | http://127.0.0.1:8052 | 5557 | `trenes/trainC/*` | `SET_TRAIN:trainC:5557` |

## ESP32 Configuration

For each ESP32, configure via serial monitor (115200 baud):

### Train A ESP32:
```
SET_TRAIN:trainA:5555
SET_BROKER:192.168.137.1
SET_WIFI:YourNetwork:YourPassword
```

### Train B ESP32:
```
SET_TRAIN:trainB:5556
SET_BROKER:192.168.137.1
SET_WIFI:YourNetwork:YourPassword
```

### Train C ESP32:
```
SET_TRAIN:trainC:5557
SET_BROKER:192.168.137.1
SET_WIFI:YourNetwork:YourPassword
```

## Features

✅ **Independent Control** - Each train has its own dashboard and controls
✅ **Data Isolation** - Separate CSV files: `trainA_experiment_*.csv`, `trainB_experiment_*.csv`, etc.
✅ **MQTT Isolation** - Train-specific topics prevent cross-talk
✅ **UDP Isolation** - Different ports for each train's data stream
✅ **No Conflicts** - Trains operate completely independently

## Network Configuration

1. Start the desired train dashboard(s)
2. In each dashboard, go to **Network Configuration** tab
3. Select your network interface (usually the hotspot: `192.168.137.1`)
4. Click **"Apply Configuration"**
5. Dashboard will start UDP receiver and MQTT connection

The configuration is saved and will auto-load next time!

## Troubleshooting

### Port Already in Use
If you see an error like `Address already in use`:
- Another dashboard is already running on that port
- Stop it with `Ctrl+C` and try again
- Or use a different port by editing the launcher script

### No Data from ESP32
1. Verify ESP32 is configured with correct train ID and UDP port
2. Check ESP32 STATUS command shows correct configuration
3. Ensure network interface is selected in dashboard
4. Check ESP32 and computer are on same network

### MQTT Not Connecting
1. Verify MQTT broker is running on the selected network interface
2. Check firewall isn't blocking port 1883
3. Ensure ESP32 shows `MQTT: CONNECTED` in STATUS

## Stopping Dashboards

Press `Ctrl+C` in each terminal window to stop the dashboard.

## Advanced: Running on Different Network

To share dashboards on your local network (so others can access):

Edit the launcher script and change:
```python
dashboard.run(host='127.0.0.1', port=8050, ...)
```
To:
```python
dashboard.run(host='0.0.0.0', port=8050, ...)
```

Then access from other computers:
- Train A: `http://YOUR_IP:8050`
- Train B: `http://YOUR_IP:8051`
- Train C: `http://YOUR_IP:8052`

**Security Note:** Only do this on trusted networks!
