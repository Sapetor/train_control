# Fix Proposal: Multi-Train MQTT Topic Isolation

**Date**: 2025-11-10
**Branch**: `claude/debug-pid-train-experiments-011CUzTGGAByFmCZzecp3dv2`
**Issue**: PID parameters not updating, cross-train interference

---

## Overview

This document provides **concrete code changes** to fix the MQTT topic isolation issue in the multi-train system. All changes maintain backward compatibility with single-train mode.

---

## Change #1: Add get_topic() Helper Method to TrainControlDashboard

**File**: `train_control_platform.py`
**Location**: After `__init__` method (around line 1467)
**Purpose**: Provide backward-compatible topic lookup

### Code to Add

```python
def get_topic(self, topic_key):
    """
    Get train-specific MQTT topic if available, else global topic.

    This ensures backward compatibility:
    - Single-train mode: uses global MQTT_TOPICS
    - Multi-train mode: uses self.mqtt_topics (set by multi_train_wrapper)

    Args:
        topic_key: Key from MQTT_TOPICS dict (e.g., 'kp', 'step_sync')

    Returns:
        str: Train-specific topic or global topic

    Example:
        # Single-train mode:
        self.get_topic('kp') → 'trenes/carroD/p'

        # Multi-train mode (Train A):
        self.get_topic('kp') → 'trenes/trainA/carroD/p'
    """
    if hasattr(self, 'mqtt_topics') and self.mqtt_topics:
        return self.mqtt_topics.get(topic_key, MQTT_TOPICS[topic_key])
    return MQTT_TOPICS[topic_key]
```

**Insert After**: Line 1467 (after setup_callbacks() call in __init__)

---

## Change #2: Initialize mqtt_topics in __init__

**File**: `train_control_platform.py`
**Location**: Line 1048 (TrainControlDashboard.__init__)
**Purpose**: Prepare for train-specific topics

### Code Change

**Insert After Line 1054** (after `self.experiment_mode = 'pid'`):

```python
# Initialize train-specific MQTT topics (will be overridden by multi_train_wrapper)
self.mqtt_topics = None  # Will use global MQTT_TOPICS if None
self.train_config = None  # Will be set by multi_train_wrapper
```

---

## Change #3: Update MQTTParameterSync to Accept Topics

**File**: `train_control_platform.py`
**Location**: Lines 246-404 (MQTTParameterSync class)

### 3a. Update __init__ Method

**OLD** (Line 249-273):
```python
def __init__(self):
    self.client = None
    self.broker_ip = DEFAULT_MQTT_BROKER
    self.broker_port = DEFAULT_MQTT_PORT
    self.connected = False
    # ... rest of init
```

**NEW**:
```python
def __init__(self, mqtt_topics=None):
    """
    Initialize MQTT parameter sync.

    Args:
        mqtt_topics: Dict of train-specific topics, or None to use global MQTT_TOPICS
    """
    self.client = None
    self.broker_ip = DEFAULT_MQTT_BROKER
    self.broker_port = DEFAULT_MQTT_PORT
    self.connected = False

    # Use provided topics or fallback to global
    self.mqtt_topics = mqtt_topics if mqtt_topics is not None else MQTT_TOPICS

    # ... rest of existing init code (lines 255-273)
```

### 3b. Update _on_connect Method

**OLD** (Lines 307-331):
```python
def _on_connect(self, client, userdata, flags, rc):
    if rc == 0:
        self.connected = True
        timestamp = time.strftime('%H:%M:%S')
        print(f"[MQTT {timestamp}] Parameter sync connected successfully")
        # Subscribe to parameter confirmation topics
        topics = [
            MQTT_TOPICS['kp_status'],
            MQTT_TOPICS['ki_status'],
            MQTT_TOPICS['kd_status'],
            MQTT_TOPICS['ref_status']
        ]
        for topic in topics:
            result = client.subscribe(topic)
            print(f"[MQTT {timestamp}] Subscribed to {topic}, result: {result}")

        # Subscribe to step response confirmation topics
        step_topics = [
            MQTT_TOPICS['step_amplitude_status'],
            MQTT_TOPICS['step_time_status'],
            MQTT_TOPICS['step_direction_status'],
            MQTT_TOPICS['step_vbatt_status']
        ]
        for topic in step_topics:
            result = client.subscribe(topic)
            print(f"[MQTT {timestamp}] Subscribed to {topic}, result: {result}")

        # Request current parameters from ESP32 by publishing a "request" signal
        print(f"[MQTT {timestamp}] Requesting current parameters from ESP32...")
        client.publish(MQTT_TOPICS['request_params'], "1")
        client.publish(MQTT_TOPICS['step_request_params'], "1")
```

**NEW** (Replace lines 307-331):
```python
def _on_connect(self, client, userdata, flags, rc):
    if rc == 0:
        self.connected = True
        timestamp = time.strftime('%H:%M:%S')
        print(f"[MQTT {timestamp}] Parameter sync connected successfully")

        # Subscribe to parameter confirmation topics (using instance topics)
        topics = [
            self.mqtt_topics['kp_status'],
            self.mqtt_topics['ki_status'],
            self.mqtt_topics['kd_status'],
            self.mqtt_topics['ref_status']
        ]
        for topic in topics:
            result = client.subscribe(topic)
            print(f"[MQTT {timestamp}] Subscribed to {topic}, result: {result}")

        # Subscribe to step response confirmation topics (using instance topics)
        step_topics = [
            self.mqtt_topics['step_amplitude_status'],
            self.mqtt_topics['step_time_status'],
            self.mqtt_topics['step_direction_status'],
            self.mqtt_topics['step_vbatt_status']
        ]
        for topic in step_topics:
            result = client.subscribe(topic)
            print(f"[MQTT {timestamp}] Subscribed to {topic}, result: {result}")

        # Request current parameters from ESP32 (using instance topics)
        print(f"[MQTT {timestamp}] Requesting current parameters from ESP32...")
        client.publish(self.mqtt_topics['request_params'], "1")
        client.publish(self.mqtt_topics['step_request_params'], "1")
```

### 3c. Update _on_message Method

**OLD** (Lines 345-370):
```python
# Update confirmed parameters based on topic
if topic == MQTT_TOPICS['kp_status']:
    self.confirmed_params['kp'] = value
    print(f"[MQTT {timestamp}] Updated Kp to {value}")
elif topic == MQTT_TOPICS['ki_status']:
    self.confirmed_params['ki'] = value
    print(f"[MQTT {timestamp}] Updated Ki to {value}")
elif topic == MQTT_TOPICS['kd_status']:
    self.confirmed_params['kd'] = value
    print(f"[MQTT {timestamp}] Updated Kd to {value}")
elif topic == MQTT_TOPICS['ref_status']:
    self.confirmed_params['reference'] = value
    print(f"[MQTT {timestamp}] Updated Reference to {value}")
# Handle step response parameter confirmations
elif topic == MQTT_TOPICS['step_amplitude_status']:
    self.step_confirmed_params['amplitude'] = value
    print(f"[MQTT {timestamp}] Updated Step Amplitude to {value}")
elif topic == MQTT_TOPICS['step_time_status']:
    self.step_confirmed_params['time'] = value
    print(f"[MQTT {timestamp}] Updated Step Time to {value}")
elif topic == MQTT_TOPICS['step_direction_status']:
    self.step_confirmed_params['direction'] = int(value)
    print(f"[MQTT {timestamp}] Updated Step Direction to {int(value)}")
elif topic == MQTT_TOPICS['step_vbatt_status']:
    self.step_confirmed_params['vbatt'] = value
    print(f"[MQTT {timestamp}] Updated Step VBatt to {value}")
```

**NEW** (Replace lines 345-370):
```python
# Update confirmed parameters based on topic (using instance topics)
if topic == self.mqtt_topics['kp_status']:
    self.confirmed_params['kp'] = value
    print(f"[MQTT {timestamp}] Updated Kp to {value}")
elif topic == self.mqtt_topics['ki_status']:
    self.confirmed_params['ki'] = value
    print(f"[MQTT {timestamp}] Updated Ki to {value}")
elif topic == self.mqtt_topics['kd_status']:
    self.confirmed_params['kd'] = value
    print(f"[MQTT {timestamp}] Updated Kd to {value}")
elif topic == self.mqtt_topics['ref_status']:
    self.confirmed_params['reference'] = value
    print(f"[MQTT {timestamp}] Updated Reference to {value}")
# Handle step response parameter confirmations (using instance topics)
elif topic == self.mqtt_topics['step_amplitude_status']:
    self.step_confirmed_params['amplitude'] = value
    print(f"[MQTT {timestamp}] Updated Step Amplitude to {value}")
elif topic == self.mqtt_topics['step_time_status']:
    self.step_confirmed_params['time'] = value
    print(f"[MQTT {timestamp}] Updated Step Time to {value}")
elif topic == self.mqtt_topics['step_direction_status']:
    self.step_confirmed_params['direction'] = int(value)
    print(f"[MQTT {timestamp}] Updated Step Direction to {int(value)}")
elif topic == self.mqtt_topics['step_vbatt_status']:
    self.step_confirmed_params['vbatt'] = value
    print(f"[MQTT {timestamp}] Updated Step VBatt to {value}")
```

---

## Change #4: Pass Topics to MQTTParameterSync

**File**: `train_control_platform.py`
**Location**: Line 1070 (in TrainControlDashboard.__init__)

**OLD**:
```python
# Initialize MQTT parameter sync
self.mqtt_sync = MQTTParameterSync()
```

**NEW**:
```python
# Initialize MQTT parameter sync with train-specific topics
# Use self.mqtt_topics if set by multi_train_wrapper, else use global MQTT_TOPICS
mqtt_topics = getattr(self, 'mqtt_topics', None) or MQTT_TOPICS
self.mqtt_sync = MQTTParameterSync(mqtt_topics=mqtt_topics)
```

---

## Change #5: Update All Callback MQTT_TOPICS References

### Strategy

**Find Pattern**: `MQTT_TOPICS\['([^']+)'\]`
**Replace With**: `self.get_topic('$1')`

**Total Occurrences**: ~50

### 5a. Update PID Parameter Callback

**File**: `train_control_platform.py`
**Location**: Lines 2933-2944

**OLD**:
```python
if trigger_id in ['kp-slider', 'kp-send-btn']:
    print(f"[PID MQTT] Sending Kp={kp} to {MQTT_TOPICS['kp']} @ {self.network_manager.mqtt_broker_ip}")
    publish.single(MQTT_TOPICS['kp'], kp, hostname=self.network_manager.mqtt_broker_ip)
elif trigger_id in ['ki-slider', 'ki-send-btn']:
    print(f"[PID MQTT] Sending Ki={ki} to {MQTT_TOPICS['ki']} @ {self.network_manager.mqtt_broker_ip}")
    publish.single(MQTT_TOPICS['ki'], ki, hostname=self.network_manager.mqtt_broker_ip)
elif trigger_id in ['kd-slider', 'kd-send-btn']:
    print(f"[PID MQTT] Sending Kd={kd} to {MQTT_TOPICS['kd']} @ {self.network_manager.mqtt_broker_ip}")
    publish.single(MQTT_TOPICS['kd'], kd, hostname=self.network_manager.mqtt_broker_ip)
elif trigger_id in ['reference-slider', 'ref-send-btn']:
    print(f"[PID MQTT] Sending Ref={reference} to {MQTT_TOPICS['reference']} @ {self.network_manager.mqtt_broker_ip}")
    publish.single(MQTT_TOPICS['reference'], reference, hostname=self.network_manager.mqtt_broker_ip)
```

**NEW**:
```python
if trigger_id in ['kp-slider', 'kp-send-btn']:
    print(f"[PID MQTT] Sending Kp={kp} to {self.get_topic('kp')} @ {self.network_manager.mqtt_broker_ip}")
    publish.single(self.get_topic('kp'), kp, hostname=self.network_manager.mqtt_broker_ip)
elif trigger_id in ['ki-slider', 'ki-send-btn']:
    print(f"[PID MQTT] Sending Ki={ki} to {self.get_topic('ki')} @ {self.network_manager.mqtt_broker_ip}")
    publish.single(self.get_topic('ki'), ki, hostname=self.network_manager.mqtt_broker_ip)
elif trigger_id in ['kd-slider', 'kd-send-btn']:
    print(f"[PID MQTT] Sending Kd={kd} to {self.get_topic('kd')} @ {self.network_manager.mqtt_broker_ip}")
    publish.single(self.get_topic('kd'), kd, hostname=self.network_manager.mqtt_broker_ip)
elif trigger_id in ['reference-slider', 'ref-send-btn']:
    print(f"[PID MQTT] Sending Ref={reference} to {self.get_topic('reference')} @ {self.network_manager.mqtt_broker_ip}")
    publish.single(self.get_topic('reference'), reference, hostname=self.network_manager.mqtt_broker_ip)
```

### 5b. Update Experiment Start/Stop Callbacks

**File**: `train_control_platform.py`
**Location**: Lines 2817-2871

**Changes** (8 occurrences):

| Line | OLD | NEW |
|------|-----|-----|
| 2817 | `publish.single(MQTT_TOPICS['sync'], 'False', ...)` | `publish.single(self.get_topic('sync'), 'False', ...)` |
| 2823 | `publish.single(MQTT_TOPICS['step_request_params'], '1', ...)` | `publish.single(self.get_topic('step_request_params'), '1', ...)` |
| 2836 | `publish.single(MQTT_TOPICS['step_sync'], 'True', ...)` | `publish.single(self.get_topic('step_sync'), 'True', ...)` |
| 2848 | `publish.single(MQTT_TOPICS['step_sync'], 'False', ...)` | `publish.single(self.get_topic('step_sync'), 'False', ...)` |
| 2849 | `publish.single(MQTT_TOPICS['step_amplitude'], 0.0, ...)` | `publish.single(self.get_topic('step_amplitude'), 0.0, ...)` |
| 2858 | `publish.single(MQTT_TOPICS['sync'], 'True', ...)` | `publish.single(self.get_topic('sync'), 'True', ...)` |
| 2866 | `publish.single(MQTT_TOPICS['step_sync'], 'False', ...)` | `publish.single(self.get_topic('step_sync'), 'False', ...)` |
| 2871 | `publish.single(MQTT_TOPICS['sync'], 'False', ...)` | `publish.single(self.get_topic('sync'), 'False', ...)` |

### 5c. Update Mode Switching Callbacks

**File**: `train_control_platform.py`
**Location**: Lines 2635-2641, 1740-1756

**Changes** (4 occurrences):

| Line | OLD | NEW |
|------|-----|-----|
| 2635 | `publish.single(MQTT_TOPICS['sync'], 'False', ...)` | `publish.single(self.get_topic('sync'), 'False', ...)` |
| 2641 | `publish.single(MQTT_TOPICS['step_sync'], 'False', ...)` | `publish.single(self.get_topic('step_sync'), 'False', ...)` |
| 1743 | `publish.single(MQTT_TOPICS['sync'], 'False', ...)` | `publish.single(self.get_topic('sync'), 'False', ...)` |
| 1750 | `publish.single(MQTT_TOPICS['step_request_params'], '1', ...)` | `publish.single(self.get_topic('step_request_params'), '1', ...)` |
| 1756 | `publish.single(MQTT_TOPICS['step_sync'], 'False', ...)` | `publish.single(self.get_topic('step_sync'), 'False', ...)` |

### 5d. Update Step Response Parameter Callbacks

**File**: `train_control_platform.py`
**Location**: Lines 3100-3250 (approximate)

**Pattern** (repeated for amplitude, time, direction, vbatt):
```python
# OLD:
publish.single(MQTT_TOPICS['step_amplitude'], amplitude, hostname=...)

# NEW:
publish.single(self.get_topic('step_amplitude'), amplitude, hostname=...)
```

**Search for all lines containing**:
- `MQTT_TOPICS['step_amplitude']`
- `MQTT_TOPICS['step_time']`
- `MQTT_TOPICS['step_direction']`
- `MQTT_TOPICS['step_vbatt']`
- `MQTT_TOPICS['step_request_params']`

Replace with `self.get_topic('...')`

### 5e. Update Deadband Callbacks

**File**: `train_control_platform.py`
**Location**: Lines 3450-3600 (approximate)

**Search for**:
- `MQTT_TOPICS['deadband_sync']`
- `MQTT_TOPICS['deadband_direction']`
- `MQTT_TOPICS['deadband_threshold']`
- `MQTT_TOPICS['deadband_apply']`
- `MQTT_TOPICS['deadband_request_params']`

Replace with `self.get_topic('...')`

---

## Change #6: Update Multi-Train Wrapper Initialization

**File**: `multi_train_wrapper.py`
**Location**: Lines 97-116

**Current Code** (already correct):
```python
# Create dashboard instance for this train
dashboard = TrainControlDashboard(
    network_manager=self.network_manager,
    data_manager=data_manager,
    udp_receiver=udp_receiver
)

# Override data managers with train-specific ones
dashboard.step_data_manager = step_data_manager
dashboard.deadband_data_manager = deadband_data_manager

# Store train config for MQTT topic generation
dashboard.train_config = train_config

# Generate and store train-specific MQTT topics
dashboard.mqtt_topics = self._generate_train_topics(train_config.mqtt_prefix)
```

**Action**: No changes needed - this code already correctly sets `dashboard.mqtt_topics`

**Verify**: Line 112 sets `dashboard.mqtt_topics` before any callbacks are registered

---

## Automated Find-Replace Script

To help with the 50+ replacements, here's a Python script:

```python
#!/usr/bin/env python3
import re

def replace_mqtt_topics(file_path):
    """Replace MQTT_TOPICS['key'] with self.get_topic('key')"""

    with open(file_path, 'r') as f:
        content = f.read()

    # Pattern: MQTT_TOPICS['key'] or MQTT_TOPICS["key"]
    pattern = r"MQTT_TOPICS\[(['\"])([^'\"]+)\1\]"
    replacement = r"self.get_topic('\2')"

    new_content = re.sub(pattern, replacement, content)

    # Count replacements
    count = len(re.findall(pattern, content))

    with open(file_path, 'w') as f:
        f.write(new_content)

    return count

if __name__ == '__main__':
    count = replace_mqtt_topics('train_control_platform.py')
    print(f"Replaced {count} occurrences of MQTT_TOPICS[...]")
```

**Usage**:
```bash
python replace_mqtt_topics.py
# Output: Replaced 50 occurrences of MQTT_TOPICS[...]
```

---

## Testing Plan

### Step 1: Verify Single-Train Mode (Backward Compatibility)

```bash
# Run original single-train mode
python train_control_platform.py
```

**Test Checklist**:
- [ ] Dashboard starts without errors
- [ ] Network configuration works
- [ ] MQTT connects successfully
- [ ] PID sliders send parameters immediately
- [ ] ESP32 confirmed parameters appear within 500ms
- [ ] Experiment start/stop works
- [ ] Step response parameters work
- [ ] Console shows train-specific topics (if multi-train) or global topics (if single-train)

### Step 2: Verify Multi-Train Mode (Train Isolation)

```bash
# Run multi-train wrapper
python multi_train_wrapper.py
```

**Test Checklist**:
- [ ] All trains load successfully
- [ ] Landing page shows all trains
- [ ] Each train dashboard accessible via URL
- [ ] Train A: Adjust Kp=100 → only ESP32 A responds
- [ ] Train B: Adjust Ki=50 → only ESP32 B responds
- [ ] Train A: Start experiment → only Train A starts
- [ ] Train B: Stop experiment → only Train B stops
- [ ] Console shows correct train-specific topics

### Step 3: MQTT Traffic Validation

```bash
# Terminal 1: Monitor MQTT traffic
mosquitto_sub -h 192.168.137.1 -t "trenes/#" -v

# Terminal 2: Access Train A dashboard
# http://192.168.137.1:8050/train/trainA

# Terminal 3: Access Train B dashboard
# http://192.168.137.1:8050/train/trainB
```

**Expected Traffic** (Train A adjusts Kp=100):
```
trenes/trainA/carroD/p 100
trenes/trainA/carroD/p/status 100
```

**Expected Traffic** (Train B adjusts Ki=50):
```
trenes/trainB/carroD/i 50
trenes/trainB/carroD/i/status 50
```

**Should NOT see**:
```
trenes/carroD/p 100  # ❌ Global topic (indicates bug not fixed)
trenes/carroD/i 50   # ❌ Global topic (indicates bug not fixed)
```

---

## Implementation Steps

### Step 1: Backup Current Code
```bash
cd /home/user/train_control
cp train_control_platform.py train_control_platform_backup_$(date +%Y%m%d_%H%M%S).py
```

### Step 2: Apply Changes 1-4 (Core Infrastructure)
1. Add `get_topic()` method after line 1467
2. Add `self.mqtt_topics = None` at line 1054
3. Update `MQTTParameterSync.__init__()` to accept `mqtt_topics` parameter
4. Update `MQTTParameterSync._on_connect()` to use `self.mqtt_topics`
5. Update `MQTTParameterSync._on_message()` to use `self.mqtt_topics`
6. Update `TrainControlDashboard.__init__` line 1070 to pass topics to MQTT sync

### Step 3: Test Core Infrastructure
```bash
python train_control_platform.py
# Verify dashboard starts without errors
```

### Step 4: Apply Change 5 (50+ Callback Updates)
**Option A**: Manual replacement (error-prone)
**Option B**: Use find-replace script (recommended)

```bash
# Run automated replacement
python replace_mqtt_topics.py
```

### Step 5: Test Single-Train Mode
```bash
python train_control_platform.py
# Follow "Testing Plan - Step 1"
```

### Step 6: Test Multi-Train Mode
```bash
python multi_train_wrapper.py
# Follow "Testing Plan - Step 2"
```

### Step 7: Commit and Push
```bash
git add train_control_platform.py
git commit -m "Fix: MQTT topic isolation for multi-train support

- Add get_topic() helper method for train-specific topic lookup
- Update MQTTParameterSync to accept train-specific topics
- Replace 50+ MQTT_TOPICS references with self.get_topic()
- Maintains backward compatibility with single-train mode
- Fixes PID parameter sync issue and cross-train interference"

git push -u origin claude/debug-pid-train-experiments-011CUzTGGAByFmCZzecp3dv2
```

---

## Rollback Plan

If issues occur:
```bash
# Restore backup
cp train_control_platform_backup_YYYYMMDD_HHMMSS.py train_control_platform.py

# Or git reset
git checkout HEAD -- train_control_platform.py
```

---

## Expected Results

### Before Fix
```
[MQTT 14:23:45] Subscribed to trenes/carroD/p/status  ❌ Global topic
[PID MQTT] Sending Kp=100 to trenes/carroD/p  ❌ Global topic
ESP32 confirmed parameters: Waiting for parameters...  ❌ Never receives
```

### After Fix (Single-Train)
```
[MQTT 14:23:45] Subscribed to trenes/carroD/p/status  ✅ Global topic (correct for single-train)
[PID MQTT] Sending Kp=100 to trenes/carroD/p  ✅ Global topic (correct)
ESP32 confirmed parameters: Kp=100.0, Ki=50.0, Kd=25.0 ✓  ✅ Immediate confirmation
```

### After Fix (Multi-Train A)
```
[MQTT 14:23:45] Subscribed to trenes/trainA/carroD/p/status  ✅ Train-specific topic
[PID MQTT] Sending Kp=100 to trenes/trainA/carroD/p  ✅ Train-specific topic
ESP32 confirmed parameters: Kp=100.0, Ki=50.0, Kd=25.0 ✓  ✅ Immediate confirmation
```

### After Fix (Multi-Train B)
```
[MQTT 14:23:45] Subscribed to trenes/trainB/carroD/p/status  ✅ Train-specific topic
[PID MQTT] Sending Kp=75 to trenes/trainB/carroD/p  ✅ Train-specific topic
ESP32 confirmed parameters: Kp=75.0, Ki=30.0, Kd=10.0 ✓  ✅ Independent from Train A
```

---

## Questions & Answers

**Q: Will this break single-train mode?**
A: No - `get_topic()` falls back to global `MQTT_TOPICS` when `self.mqtt_topics` is None

**Q: Do I need to update ESP32 firmware?**
A: No - ESP32 firmware already uses train-specific topics (configured via universal firmware)

**Q: How many lines of code change?**
A: ~70 lines total (10 new lines, 60 modifications)

**Q: Can I test incrementally?**
A: Yes - changes 1-4 are testable before change 5

**Q: What if I miss some MQTT_TOPICS references?**
A: Use grep to find remaining: `grep -n "MQTT_TOPICS\[" train_control_platform.py`

---

## Success Criteria

- [ ] Zero console errors on startup
- [ ] PID parameters update within 500ms
- [ ] ESP32 confirmed parameters display with ✓
- [ ] Multi-train dashboards operate independently
- [ ] MQTT traffic shows train-specific topics
- [ ] Single-train mode still works
- [ ] All 50+ MQTT_TOPICS references replaced
- [ ] Tests pass for both modes

---

**Ready to implement**: All changes documented with exact line numbers and code snippets.
