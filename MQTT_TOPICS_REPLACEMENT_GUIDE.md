# MQTT_TOPICS Replacement Guide

## Overview
This guide shows the exact search-and-replace operations needed to update all MQTT_TOPICS references to use train-specific topics.

## Step 1: Find All MQTT_TOPICS References

Found 50 references to `MQTT_TOPICS['...]` in the codebase.

## Step 2: Replacement Pattern

**Pattern to find:**
```
MQTT_TOPICS\['([^']+)'\]
```

**Replace with:**
```
self.mqtt_topics['$1']
```

## Step 3: Manual Replacements Required

Since some references are in the MQTTParameterSync class, those need to use `self.topics` instead:

### In MQTTParameterSync class methods:

**Lines 308-311** (in `_on_connect`):
```python
# BEFORE:
MQTT_TOPICS['kp_status'],
MQTT_TOPICS['ki_status'],
MQTT_TOPICS['kd_status'],
MQTT_TOPICS['ref_status']

# AFTER:
self.topics['kp_status'],
self.topics['ki_status'],
self.topics['kd_status'],
self.topics['ref_status']
```

**Lines 319-322** (in `_on_connect`):
```python
# BEFORE:
MQTT_TOPICS['step_amplitude_status'],
MQTT_TOPICS['step_time_status'],
MQTT_TOPICS['step_direction_status'],
MQTT_TOPICS['step_vbatt_status']

# AFTER:
self.topics['step_amplitude_status'],
self.topics['step_time_status'],
self.topics['step_direction_status'],
self.topics['step_vbatt_status']
```

**Lines 330-331** (in `_on_connect`):
```python
# BEFORE:
client.publish(MQTT_TOPICS['request_params'], "1")
client.publish(MQTT_TOPICS['step_request_params'], "1")

# AFTER:
client.publish(self.topics['request_params'], "1")
client.publish(self.topics['step_request_params'], "1")
```

**Lines 345-367** (in `_on_message`):
```python
# BEFORE:
if topic == MQTT_TOPICS['kp_status']:
    self.confirmed_params['kp'] = float(payload)
elif topic == MQTT_TOPICS['ki_status']:
    self.confirmed_params['ki'] = float(payload)
elif topic == MQTT_TOPICS['kd_status']:
    self.confirmed_params['kd'] = float(payload)
elif topic == MQTT_TOPICS['ref_status']:
    self.confirmed_params['reference'] = float(payload)
elif topic == MQTT_TOPICS['step_amplitude_status']:
    self.confirmed_params['step_amplitude'] = float(payload)
elif topic == MQTT_TOPICS['step_time_status']:
    self.confirmed_params['step_time'] = float(payload)
elif topic == MQTT_TOPICS['step_direction_status']:
    self.confirmed_params['step_direction'] = int(payload)
elif topic == MQTT_TOPICS['step_vbatt_status']:
    self.confirmed_params['step_vbatt'] = float(payload)

# AFTER:
if topic == self.topics['kp_status']:
    self.confirmed_params['kp'] = float(payload)
elif topic == self.topics['ki_status']:
    self.confirmed_params['ki'] = float(payload)
elif topic == self.topics['kd_status']:
    self.confirmed_params['kd'] = float(payload)
elif topic == self.topics['ref_status']:
    self.confirmed_params['reference'] = float(payload)
elif topic == self.topics['step_amplitude_status']:
    self.confirmed_params['step_amplitude'] = float(payload)
elif topic == self.topics['step_time_status']:
    self.confirmed_params['step_time'] = float(payload)
elif topic == self.topics['step_direction_status']:
    self.confirmed_params['step_direction'] = int(payload)
elif topic == self.topics['step_vbatt_status']:
    self.confirmed_params['step_vbatt'] = float(payload)
```

### In TrainControlDashboard class methods:

All remaining references should be changed to `self.mqtt_topics`:

**Line 1743:**
```python
# BEFORE:
publish.single(MQTT_TOPICS['sync'], 'False', hostname=self.network_manager.mqtt_broker_ip)

# AFTER:
publish.single(self.mqtt_topics['sync'], 'False', hostname=self.network_manager.mqtt_broker_ip)
```

**Line 1750:**
```python
# BEFORE:
publish.single(MQTT_TOPICS['step_request_params'], '1', hostname=self.network_manager.mqtt_broker_ip)

# AFTER:
publish.single(self.mqtt_topics['step_request_params'], '1', hostname=self.network_manager.mqtt_broker_ip)
```

**Line 1756:**
```python
# BEFORE:
publish.single(MQTT_TOPICS['step_sync'], 'False', hostname=self.network_manager.mqtt_broker_ip)

# AFTER:
publish.single(self.mqtt_topics['step_sync'], 'False', hostname=self.network_manager.mqtt_broker_ip)
```

**Line 2635:**
```python
# BEFORE:
publish.single(MQTT_TOPICS['sync'], 'False', hostname=self.network_manager.mqtt_broker_ip)

# AFTER:
publish.single(self.mqtt_topics['sync'], 'False', hostname=self.network_manager.mqtt_broker_ip)
```

**Line 2641:**
```python
# BEFORE:
publish.single(MQTT_TOPICS['step_sync'], 'False', hostname=self.network_manager.mqtt_broker_ip)

# AFTER:
publish.single(self.mqtt_topics['step_sync'], 'False', hostname=self.network_manager.mqtt_broker_ip)
```

**Lines 2817-2849 (start/stop callbacks):**
```python
# BEFORE:
publish.single(MQTT_TOPICS['sync'], 'False', hostname=...)
publish.single(MQTT_TOPICS['step_request_params'], '1', hostname=...)
publish.single(MQTT_TOPICS['step_sync'], 'True', hostname=...)
publish.single(MQTT_TOPICS['step_sync'], 'False', hostname=...)
publish.single(MQTT_TOPICS['step_amplitude'], 0.0, hostname=...)
publish.single(MQTT_TOPICS['sync'], 'True', hostname=...)

# AFTER:
publish.single(self.mqtt_topics['sync'], 'False', hostname=...)
publish.single(self.mqtt_topics['step_request_params'], '1', hostname=...)
publish.single(self.mqtt_topics['step_sync'], 'True', hostname=...)
publish.single(self.mqtt_topics['step_sync'], 'False', hostname=...)
publish.single(self.mqtt_topics['step_amplitude'], 0.0, hostname=...)
publish.single(self.mqtt_topics['sync'], 'True', hostname=...)
```

Continue this pattern for all remaining references.

## Step 4: Automated Replacement Script

For safety, here's a Python script to perform the replacements:

```python
import re

def replace_mqtt_topics_in_class(file_path, class_name, old_pattern, new_pattern):
    """Replace MQTT_TOPICS references within a specific class"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the class definition
    class_pattern = rf'class {class_name}:.*?(?=\nclass |\Z)'

    def replace_in_class(match):
        class_content = match.group(0)
        # Replace all MQTT_TOPICS references
        updated_content = re.sub(old_pattern, new_pattern, class_content)
        return updated_content

    updated_content = re.sub(class_pattern, replace_in_class, content, flags=re.DOTALL)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    print(f"✓ Updated {class_name}")

# Replace in MQTTParameterSync
replace_mqtt_topics_in_class(
    'train_control_platform.py',
    'MQTTParameterSync',
    r"MQTT_TOPICS\['([^']+)'\]",
    r"self.topics['\1']"
)

# Replace in TrainControlDashboard
replace_mqtt_topics_in_class(
    'train_control_platform.py',
    'TrainControlDashboard',
    r"MQTT_TOPICS\['([^']+)'\]",
    r"self.mqtt_topics['\1']"
)

print("\n✓ All MQTT_TOPICS references updated!")
```

## Step 5: Verification

After making replacements, verify:

1. **Search for remaining global references:**
   ```bash
   grep -n "MQTT_TOPICS\[" train_control_platform.py
   ```

   Should return NO results (except in constant definition).

2. **Check class-specific references:**
   ```bash
   grep -n "self.topics\[" train_control_platform.py  # MQTTParameterSync
   grep -n "self.mqtt_topics\[" train_control_platform.py  # TrainControlDashboard
   ```

3. **Test MQTT communication:**
   - Start dashboard
   - Check console for train-specific topic names
   - Verify ESP32 receives on correct topics

## Common Issues

### Issue 1: Mixed references
**Problem:** Some methods use both `self.topics` and `self.mqtt_topics`
**Solution:** Ensure MQTTParameterSync uses `self.topics`, TrainControlDashboard uses `self.mqtt_topics`

### Issue 2: Hardcoded topic strings
**Problem:** Some publish calls might have hardcoded topic strings
**Solution:** Search for literal topic strings like `'trenes/sync'` and replace with topic dictionary references

### Issue 3: Callback topic subscriptions
**Problem:** Topic subscriptions in callbacks might not update
**Solution:** Ensure MQTT client reconnects when switching trains

## Complete Reference List

Here's the complete list of all MQTT_TOPICS keys that need replacement:

**PID Control Topics:**
- `sync`
- `kp`, `ki`, `kd`
- `reference`
- `kp_status`, `ki_status`, `kd_status`
- `ref_status`
- `request_params`

**Step Response Topics:**
- `step_sync`
- `step_amplitude`, `step_time`, `step_direction`, `step_vbatt`
- `step_amplitude_status`, `step_time_status`, `step_direction_status`, `step_vbatt_status`
- `step_request_params`

**Deadband Topics:**
- `deadband_sync`
- `deadband_direction`, `deadband_threshold`
- `deadband_apply`
- `deadband_direction_status`, `deadband_threshold_status`

## Next Steps

After completing MQTT_TOPICS replacement:

1. Update callback IDs with train prefixes (see CALLBACK_ID_UPDATE_GUIDE.md)
2. Test single train configuration
3. Test multi-train configuration
4. Verify MQTT topics in broker logs
