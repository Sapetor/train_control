# Multi-Train MQTT Parameter Synchronization Issues

**Date**: 2025-11-10
**Status**: Critical bugs identified - PID parameters not updating correctly

---

## Executive Summary

The multi-train system has a **critical architectural issue**: all dashboard callbacks use the global `MQTT_TOPICS` dictionary instead of train-specific topic mappings. This causes:

1. **PID parameters not updating** until after experiment starts
2. **Cross-train interference** - all trains receive the same MQTT commands
3. **No train isolation** - parameter changes affect all trains simultaneously

**Root Cause**: The multi-train wrapper creates train-specific MQTT topics (`dashboard.mqtt_topics`) but the dashboard callbacks reference the global `MQTT_TOPICS` dictionary (~50 occurrences).

---

## Issue #1: PID Parameters Not Updating Until Experiment Starts

### Symptoms
- User adjusts PID sliders (Kp, Ki, Kd, Reference)
- ESP32 confirmed parameters section shows "Waiting for parameters..."
- Parameters only appear after starting the experiment
- MQTT status shows `MQTT connected: False` or "Waiting for confirmation"

### Root Cause Analysis

**Problem Location**: `train_control_platform.py:307-331` (MQTTParameterSync._on_connect)

```python
def _on_connect(self, client, userdata, flags, rc):
    # Subscribe to GLOBAL topics (wrong for multi-train!)
    topics = [
        MQTT_TOPICS['kp_status'],          # 'trenes/carroD/p/status'
        MQTT_TOPICS['ki_status'],          # 'trenes/carroD/i/status'
        ...
    ]
    for topic in topics:
        client.subscribe(topic)  # ❌ Wrong! Should use train-specific topics
```

**What Should Happen**:
- Train A dashboard subscribes to: `trenes/trainA/carroD/p/status`
- Train B dashboard subscribes to: `trenes/trainB/carroD/p/status`

**What Actually Happens**:
- Train A dashboard subscribes to: `trenes/carroD/p/status` (global topic)
- Train B dashboard subscribes to: `trenes/carroD/p/status` (same global topic!)
- ESP32 publishes to: `trenes/trainA/carroD/p/status` (train-specific)
- Dashboard never receives the message because it's subscribed to the wrong topic!

### Why Parameters Appear After Experiment Starts

When the experiment starts, the ESP32 might publish to both global and train-specific topics (depending on firmware configuration), or the user manually requests parameters via MQTT, temporarily syncing the values. This is **unreliable** and **not the intended behavior**.

---

## Issue #2: Cross-Train Interference (Multi-Train Mode)

### Symptoms
- Adjusting parameters on Train A dashboard affects Train B
- All trains respond to commands from any dashboard
- Multiple trains cannot be controlled independently

### Root Cause Analysis

**Problem Location**: All MQTT publish calls in callbacks use global topics

**Example** (`train_control_platform.py:2934-2944`):
```python
def update_pid_parameters(...):
    if trigger_id in ['kp-slider', 'kp-send-btn']:
        # ❌ Publishes to GLOBAL topic 'trenes/carroD/p'
        publish.single(MQTT_TOPICS['kp'], kp, hostname=self.network_manager.mqtt_broker_ip)
```

**What Should Happen**:
- Train A dashboard publishes to: `trenes/trainA/carroD/p`
- Train B dashboard publishes to: `trenes/trainB/carroD/p`
- Each ESP32 only listens to its own topic prefix

**What Actually Happens**:
- Train A dashboard publishes to: `trenes/carroD/p`
- Train B dashboard publishes to: `trenes/carroD/p`
- All ESP32s listen to `trenes/carroD/p`
- Result: **ALL trains receive the same command!**

---

## Issue #3: MQTTParameterSync Class Not Train-Aware

### Problem

The `MQTTParameterSync` class (lines 246-404) is designed for single-train operation:

```python
class MQTTParameterSync:
    def _on_connect(self, client, userdata, flags, rc):
        # Hardcoded to global MQTT_TOPICS
        topics = [MQTT_TOPICS['kp_status'], ...]
        for topic in topics:
            client.subscribe(topic)  # ❌ No train_id parameter
```

**Consequences**:
1. Cannot distinguish between trains
2. All instances subscribe to the same topics
3. All instances receive all messages (even from other trains)
4. Race conditions when multiple trains publish simultaneously

---

## Issue #4: 50+ Hardcoded MQTT_TOPICS References

### Affected Code Locations

Total occurrences: **50+**

**Key areas**:
- `MQTTParameterSync._on_connect()` - lines 307-331 (subscriptions)
- `MQTTParameterSync._on_message()` - lines 345-370 (topic matching)
- `update_pid_parameters()` callback - lines 2933-2944 (parameter publishing)
- `start/stop experiment` callbacks - lines 2817-2871 (sync commands)
- `update_step_parameters()` callback - lines 2879-3050 (step response)
- `track_experiment_mode()` callback - lines 2635-2641 (mode switching)
- `switch_experiment_mode()` - lines 1740-1756 (mode commands)

**Example Pattern (repeated 50+ times)**:
```python
# ❌ WRONG: Uses global topic
publish.single(MQTT_TOPICS['sync'], 'True', hostname=...)

# ✅ CORRECT: Should use train-specific topic
publish.single(self.get_topic('sync'), 'True', hostname=...)
```

---

## Issue #5: Step Response Experiment Validation Problem

### Symptoms
- User sets step response parameters (amplitude, time, direction)
- ESP32 doesn't receive parameters
- Dashboard shows "Configure step parameters first"
- Can't start experiment even after setting parameters

### Root Cause

**Same as Issue #1**: The dashboard publishes to global topics, but ESP32 listens to train-specific topics.

**Problem Location**: `train_control_platform.py:3149-3250` (step parameter callbacks)

```python
def update_step_amplitude(...):
    # ❌ Publishes to global 'trenes/step/amplitude'
    publish.single(MQTT_TOPICS['step_amplitude'], amplitude, hostname=...)
```

ESP32 expects: `trenes/trainA/step/amplitude`
Dashboard publishes: `trenes/step/amplitude`
Result: **Message never arrives at ESP32**

---

## Architecture Design Flaw

### Current (Broken) Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Multi-Train Wrapper (multi_train_wrapper.py)               │
│                                                             │
│  - Generates train-specific topics via _generate_train_topics()
│  - Stores in: dashboard.mqtt_topics                        │
│  - ❌ But dashboard callbacks never use this!              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ TrainControlDashboard (train_control_platform.py)          │
│                                                             │
│  Callbacks use GLOBAL topics:                              │
│  ❌ MQTT_TOPICS['kp_status']      → 'trenes/carroD/p/status'
│  ❌ MQTT_TOPICS['step_amplitude'] → 'trenes/step/amplitude'
│  ❌ MQTT_TOPICS['sync']           → 'trenes/sync'
│                                                             │
│  Should use TRAIN-SPECIFIC topics:                         │
│  ✅ self.mqtt_topics['kp_status'] → 'trenes/trainA/carroD/p/status'
│  ✅ self.mqtt_topics['step_amplitude'] → 'trenes/trainA/step/amplitude'
│  ✅ self.mqtt_topics['sync'] → 'trenes/trainA/sync'
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ MQTT Broker (mosquitto)                                     │
│                                                             │
│  Topic tree:                                                │
│  trenes/                                                    │
│    ├── trainA/                                              │
│    │     ├── carroD/p/status  ← ESP32 trainA publishes here
│    │     └── step/amplitude   ← ESP32 trainA listens here  │
│    ├── trainB/                                              │
│    │     ├── carroD/p/status  ← ESP32 trainB publishes here
│    │     └── step/amplitude   ← ESP32 trainB listens here  │
│    └── carroD/p/status  ← ❌ Dashboards subscribe HERE (wrong!)
└─────────────────────────────────────────────────────────────┘
```

---

## Proposed Fixes

### Fix #1: Add Train-Specific MQTT Topics to Dashboard

**Location**: `train_control_platform.py:1048` (TrainControlDashboard.__init__)

```python
class TrainControlDashboard:
    def __init__(self, network_manager, data_manager, udp_receiver):
        # ... existing code ...

        # NEW: Initialize train-specific MQTT topics
        self.mqtt_topics = MQTT_TOPICS.copy()  # Start with defaults
        self.train_config = None  # Will be set by multi_train_wrapper
```

### Fix #2: Add Helper Method to Get Topics

**Location**: `train_control_platform.py` (after __init__)

```python
def get_topic(self, topic_key):
    """
    Get train-specific MQTT topic if available, else global topic.

    This ensures backward compatibility:
    - Single-train mode: uses global MQTT_TOPICS
    - Multi-train mode: uses self.mqtt_topics (set by multi_train_wrapper)
    """
    if hasattr(self, 'mqtt_topics') and self.mqtt_topics:
        return self.mqtt_topics.get(topic_key, MQTT_TOPICS[topic_key])
    return MQTT_TOPICS[topic_key]
```

### Fix #3: Update MQTTParameterSync to Accept Topic Map

**Location**: `train_control_platform.py:246` (MQTTParameterSync class)

**Current**:
```python
class MQTTParameterSync:
    def __init__(self):
        # No way to pass train-specific topics
```

**Proposed**:
```python
class MQTTParameterSync:
    def __init__(self, mqtt_topics=None):
        """
        Initialize MQTT parameter sync.

        Args:
            mqtt_topics: Dict of train-specific topics, or None for global topics
        """
        self.mqtt_topics = mqtt_topics or MQTT_TOPICS
        # ... rest of init ...

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            # Use instance topics instead of global
            topics = [
                self.mqtt_topics['kp_status'],
                self.mqtt_topics['ki_status'],
                # ... etc
            ]
```

### Fix #4: Pass Topics When Creating MQTT Sync

**Location**: `train_control_platform.py:1070` (TrainControlDashboard.__init__)

**Current**:
```python
self.mqtt_sync = MQTTParameterSync()
```

**Proposed**:
```python
# Use train-specific topics if available, else global
mqtt_topics = getattr(self, 'mqtt_topics', MQTT_TOPICS)
self.mqtt_sync = MQTTParameterSync(mqtt_topics=mqtt_topics)
```

### Fix #5: Replace All MQTT_TOPICS References in Callbacks

**Strategy**: Use find-replace with validation

**Pattern to find**: `MQTT_TOPICS\['([^']+)'\]`
**Replace with**: `self.get_topic('$1')`

**Example transformations**:
```python
# BEFORE:
publish.single(MQTT_TOPICS['kp'], kp, hostname=...)

# AFTER:
publish.single(self.get_topic('kp'), kp, hostname=...)
```

**Files to update**:
- `train_control_platform.py` (~50 occurrences)

**Critical sections**:
1. Line 2934: `publish.single(MQTT_TOPICS['kp'], ...)`
2. Line 2937: `publish.single(MQTT_TOPICS['ki'], ...)`
3. Line 2940: `publish.single(MQTT_TOPICS['kd'], ...)`
4. Line 2943: `publish.single(MQTT_TOPICS['reference'], ...)`
5. Line 2817: `publish.single(MQTT_TOPICS['sync'], ...)`
6. Line 2836: `publish.single(MQTT_TOPICS['step_sync'], ...)`
7. ... (44 more occurrences)

---

## Implementation Priority

### Phase 1: Core MQTT Topic Isolation (CRITICAL - Fixes both issues)

1. ✅ Add `self.mqtt_topics` initialization to `TrainControlDashboard.__init__`
2. ✅ Add `get_topic()` helper method to `TrainControlDashboard`
3. ✅ Update `MQTTParameterSync.__init__()` to accept `mqtt_topics` parameter
4. ✅ Update `MQTTParameterSync._on_connect()` to use `self.mqtt_topics`
5. ✅ Update `MQTTParameterSync._on_message()` to use `self.mqtt_topics`
6. ✅ Update `TrainControlDashboard.__init__` to pass topics to MQTT sync

### Phase 2: Callback Updates (50+ changes)

1. ✅ Replace all `MQTT_TOPICS[...]` with `self.get_topic(...)` in:
   - PID parameter callbacks (lines 2878-2955)
   - Step response callbacks (lines 3100-3250)
   - Deadband callbacks (lines 3450-3600)
   - Experiment control callbacks (lines 2800-2874)
   - Mode switching callbacks (lines 2619-2650, 1728-1756)

### Phase 3: Testing & Validation

1. ✅ Test single-train mode (backward compatibility)
2. ✅ Test multi-train mode (train isolation)
3. ✅ Test parameter synchronization (immediate updates)
4. ✅ Test step response experiment
5. ✅ Test cross-train interference (should not occur)

---

## Testing Checklist

### Single-Train Mode (Backward Compatibility)
- [ ] Dashboard starts without multi_train_wrapper
- [ ] PID parameters update immediately when sliders moved
- [ ] ESP32 confirmed parameters appear within 500ms
- [ ] Step response parameters work correctly
- [ ] Experiment start/stop works
- [ ] MQTT status shows "Connected" with ✓ checkmark

### Multi-Train Mode (Train Isolation)
- [ ] Start multi_train_wrapper with 2+ trains
- [ ] Each dashboard shows correct train name
- [ ] Adjust Kp on Train A → only Train A ESP32 responds
- [ ] Adjust Ki on Train B → only Train B ESP32 responds
- [ ] Start experiment on Train A → only Train A starts
- [ ] Stop experiment on Train B → only Train B stops
- [ ] ESP32 confirmed parameters match each train independently
- [ ] Step response works independently per train
- [ ] CSV files have correct train ID prefixes

### MQTT Traffic Validation
```bash
# Monitor all MQTT traffic
mosquitto_sub -h 192.168.137.1 -t "trenes/#" -v

# Expected when adjusting Train A Kp=100:
trenes/trainA/carroD/p 100
trenes/trainA/carroD/p/status 100

# Expected when adjusting Train B Ki=50:
trenes/trainB/carroD/i 50
trenes/trainB/carroD/i/status 50

# ❌ Should NOT see:
trenes/carroD/p 100  # Global topic (old behavior)
```

---

## Risk Assessment

### High Risk Changes
- Updating `MQTTParameterSync` class signature
- Replacing 50+ MQTT_TOPICS references

### Mitigation Strategies
1. **Backward Compatibility**: Use `getattr(self, 'mqtt_topics', MQTT_TOPICS)` pattern
2. **Incremental Testing**: Test after each phase
3. **Git Branching**: Create feature branch for changes
4. **Rollback Plan**: Keep backup of working single-train version

---

## Expected Outcomes

### After Fix Implementation

**PID Parameter Updates**:
- Immediate ESP32 confirmation (200-500ms latency)
- Real-time display of confirmed parameters
- No need to start experiment first

**Multi-Train Isolation**:
- Each dashboard controls only its assigned train
- No cross-train interference
- Independent parameter sets per train
- Correct CSV file prefixes

**MQTT Architecture**:
- Clean topic hierarchy per train
- Proper pub/sub isolation
- Scalable to 10+ trains

---

## Related Files

- `/home/user/train_control/train_control_platform.py` (3,791 lines)
- `/home/user/train_control/multi_train_wrapper.py` (441 lines)
- `/home/user/train_control/trains_config.json` (configuration)
- `/home/user/train_control/CLAUDE.md` (project documentation)

---

## References

- CLAUDE.md: "Multi-Train Architecture (2025-11-09)" section
- CLAUDE.md: "MQTT Communication" section (lines defining MQTT_TOPICS)
- Exploration report: Detailed codebase analysis (2025-11-10)

---

**Next Steps**: Begin Phase 1 implementation with critical MQTT topic isolation fixes.
