# Comprehensive Fix: Multi-Train Issues

**Date**: 2025-11-10
**Issues**: PID plots missing, Step Response plots missing, Step Response needs restart

---

## Executive Summary

Three distinct but related issues identified in multi-train mode:

1. ✅ **PID plots don't show** - CSV glob pattern doesn't match train-prefixed filenames
2. ✅ **Step response plots don't show** - CSV glob pattern doesn't match train-prefixed filenames
3. ✅ **Step response needs restart** - MQTT topic isolation + parameter state issues

**Root Cause**: Multi-train architecture partially implemented - CSV files have train prefixes but graph code doesn't account for this.

---

## Issue #1 & #2: Graph CSV File Pattern Mismatch

### Problem

**PID Graphs** (Line 1524):
```python
csv_files = glob.glob("experiment_*.csv")
```

**Step Response Graphs** (Line 3273):
```python
csv_files = glob.glob("step_response_*.csv")
```

**What actually exists** in multi-train mode:
- `trainA_experiment_20251110_143052.csv`
- `trainA_step_response_20251110_143052.csv`

Result: `glob.glob()` returns empty list, graphs show "No files found"

### Solution: Train-Aware CSV Glob Patterns

Add helper method to get correct glob pattern:

```python
def _get_csv_glob_pattern(self, experiment_type='pid'):
    """
    Get CSV glob pattern based on train_id and experiment type.

    Args:
        experiment_type: 'pid', 'step', or 'deadband'

    Returns:
        str: Glob pattern like "trainA_experiment_*.csv" or "experiment_*.csv"
    """
    patterns = {
        'pid': 'experiment_*.csv',
        'step': 'step_response_*.csv',
        'deadband': 'deadband_*.csv'
    }

    base_pattern = patterns.get(experiment_type, 'experiment_*.csv')

    # Check if we have a train_id (multi-train mode)
    if hasattr(self, 'train_config') and self.train_config:
        train_id = self.train_config.id
        return f"{train_id}_{base_pattern}"
    elif hasattr(self, 'data_manager') and hasattr(self.data_manager, 'train_id') and self.data_manager.train_id:
        train_id = self.data_manager.train_id
        return f"{train_id}_{base_pattern}"
    else:
        # Single-train mode - no prefix
        return base_pattern
```

### Fix #1: Update PID Graph Code

**File**: `train_control_platform.py`
**Location**: Line 1524

**OLD**:
```python
csv_files = glob.glob("experiment_*.csv")
```

**NEW**:
```python
csv_files = glob.glob(self._get_csv_glob_pattern('pid'))
```

### Fix #2: Update Step Response Graph Code

**File**: `train_control_platform.py`
**Location**: Line 3273

**OLD**:
```python
csv_files = glob.glob("step_response_*.csv")
```

**NEW**:
```python
csv_files = glob.glob(self._get_csv_glob_pattern('step'))
```

### Fix #3: Update Deadband Graph Code (if exists)

Search for deadband glob patterns and apply same fix:
```python
csv_files = glob.glob(self._get_csv_glob_pattern('deadband'))
```

### Fix #4: Update CSV Download Callbacks

**Location**: Lines 2914-2978 (approximate)

**OLD**:
```python
pid_files = glob.glob("experiment_*.csv")
step_files = glob.glob("step_response_*.csv")
deadband_files = glob.glob("deadband_*.csv")
```

**NEW**:
```python
pid_files = glob.glob(self._get_csv_glob_pattern('pid'))
step_files = glob.glob(self._get_csv_glob_pattern('step'))
deadband_files = glob.glob(self._get_csv_glob_pattern('deadband'))
```

---

## Issue #3: Step Response Needs Restart

### Primary Cause: MQTT Topic Isolation

Step response parameters don't reach ESP32 after first run because dashboard publishes to wrong topics. This is covered in detail in `FIX_PROPOSAL.md`.

**Impact on Step Response**:
1. User sets parameters (amplitude, time, direction)
2. Dashboard publishes to global topics: `trenes/step/amplitude`
3. ESP32 listens to train-specific topics: `trenes/trainA/step/amplitude`
4. Parameters never reach ESP32
5. Dashboard validation blocks experiment start (line 2810-2813)

### Secondary Cause: Parameter Validation Blocks Restart

**Location**: Line 2810-2813

```python
confirmed = self.mqtt_sync.step_confirmed_params
if not confirmed.get('amplitude') or not confirmed.get('time'):
    return html.Div(self.t('configure_step_first'), ...)
```

After stopping experiment, if MQTT parameters aren't persisted or ESP32 doesn't respond, this check fails.

### Solution: MQTT Topic Isolation

See `FIX_PROPOSAL.md` for complete MQTT fixes. Summary:
- Replace all `MQTT_TOPICS['key']` with `self.get_topic('key')`
- Update `MQTTParameterSync` to use train-specific topics
- Ensures parameters reach correct ESP32

---

## Combined Implementation Plan

### Phase 1: Add CSV Glob Helper Method (Quick Win)

**Add after line 1467** (after `setup_callbacks()`):

```python
def _get_csv_glob_pattern(self, experiment_type='pid'):
    """
    Get CSV glob pattern based on train_id and experiment type.

    Supports both single-train and multi-train modes:
    - Single-train: returns "experiment_*.csv"
    - Multi-train (trainA): returns "trainA_experiment_*.csv"

    Args:
        experiment_type: 'pid', 'step', or 'deadband'

    Returns:
        str: Glob pattern for finding CSV files
    """
    patterns = {
        'pid': 'experiment_*.csv',
        'step': 'step_response_*.csv',
        'deadband': 'deadband_*.csv'
    }

    base_pattern = patterns.get(experiment_type, 'experiment_*.csv')

    # Try multiple sources for train_id (multi-train mode detection)
    train_id = None

    # Source 1: train_config (set by multi_train_wrapper)
    if hasattr(self, 'train_config') and self.train_config:
        train_id = self.train_config.id
    # Source 2: data_manager.train_id
    elif hasattr(self, 'data_manager') and hasattr(self.data_manager, 'train_id') and self.data_manager.train_id:
        train_id = self.data_manager.train_id

    # Return train-prefixed pattern or plain pattern
    if train_id:
        return f"{train_id}_{base_pattern}"
    else:
        return base_pattern
```

### Phase 2: Update Graph Callbacks (3 changes)

**Change 1**: Line 1524
```python
# OLD:
csv_files = glob.glob("experiment_*.csv")

# NEW:
csv_files = glob.glob(self._get_csv_glob_pattern('pid'))
```

**Change 2**: Line 3273
```python
# OLD:
csv_files = glob.glob("step_response_*.csv")

# NEW:
csv_files = glob.glob(self._get_csv_glob_pattern('step'))
```

**Change 3**: Find deadband graph code (search for `deadband_*.csv`) and apply same fix

### Phase 3: Update Download Callbacks

Search for download callbacks and update:

```bash
grep -n 'glob.glob.*experiment\|glob.glob.*step_response\|glob.glob.*deadband' train_control_platform.py
```

Replace all found occurrences with train-aware patterns.

### Phase 4: Implement MQTT Topic Isolation

Follow the complete plan in `FIX_PROPOSAL.md`:
1. Add `get_topic()` helper method
2. Update `MQTTParameterSync` class
3. Replace 50+ `MQTT_TOPICS[...]` references

---

## Testing Checklist

### Test 1: Single-Train Mode (Backward Compatibility)

```bash
python train_control_platform.py
```

- [ ] PID experiment starts
- [ ] PID graph shows data in real-time
- [ ] Step response experiment starts
- [ ] Step response graph shows data
- [ ] Can stop and restart step response without application restart
- [ ] CSV files named: `experiment_*.csv`, `step_response_*.csv`

### Test 2: Multi-Train Mode (Train A)

```bash
python multi_train_wrapper.py
# Access: http://127.0.0.1:8050/train/trainA
```

- [ ] PID experiment starts
- [ ] PID graph shows data (from `trainA_experiment_*.csv`)
- [ ] Step response experiment starts
- [ ] Step response graph shows data (from `trainA_step_response_*.csv`)
- [ ] Can stop and restart step response multiple times
- [ ] Parameters update immediately (200-500ms)
- [ ] ESP32 confirmed parameters display with ✓

### Test 3: Multi-Train Isolation (Train A + Train B)

```bash
# Terminal 1: Monitor MQTT
mosquitto_sub -h 192.168.137.1 -t "trenes/#" -v

# Terminal 2: Access Train A
# http://127.0.0.1:8050/train/trainA

# Terminal 3: Access Train B
# http://127.0.0.1:8050/train/trainB
```

- [ ] Train A plots show only Train A data
- [ ] Train B plots show only Train B data
- [ ] Train A experiment doesn't affect Train B graphs
- [ ] MQTT traffic shows train-specific topics (trainA/*, trainB/*)
- [ ] No cross-train interference

### Test 4: CSV File Naming

```bash
# After running experiments, check files:
ls -la *.csv
```

**Expected files**:
- Single-train mode: `experiment_20251110_143052.csv`
- Multi-train (Train A): `trainA_experiment_20251110_143052.csv`
- Multi-train (Train B): `trainB_experiment_20251110_143052.csv`

---

## Implementation Script

### Quick Fix Script (Phases 1-3 only)

```python
#!/usr/bin/env python3
"""
Quick fix for CSV glob patterns in multi-train mode.
This script adds the _get_csv_glob_pattern() method and updates graph callbacks.
"""

import re

def apply_csv_glob_fixes(file_path='train_control_platform.py'):
    with open(file_path, 'r') as f:
        content = f.read()

    # Find insertion point (after setup_callbacks call)
    insertion_point = content.find('self.setup_callbacks()')
    if insertion_point == -1:
        print("ERROR: Could not find setup_callbacks() call")
        return False

    # Find end of line
    next_newline = content.find('\n', insertion_point)

    # Helper method code
    helper_method = '''

    def _get_csv_glob_pattern(self, experiment_type='pid'):
        """
        Get CSV glob pattern based on train_id and experiment type.

        Supports both single-train and multi-train modes:
        - Single-train: returns "experiment_*.csv"
        - Multi-train (trainA): returns "trainA_experiment_*.csv"

        Args:
            experiment_type: 'pid', 'step', or 'deadband'

        Returns:
            str: Glob pattern for finding CSV files
        """
        patterns = {
            'pid': 'experiment_*.csv',
            'step': 'step_response_*.csv',
            'deadband': 'deadband_*.csv'
        }

        base_pattern = patterns.get(experiment_type, 'experiment_*.csv')

        # Try multiple sources for train_id (multi-train mode detection)
        train_id = None

        # Source 1: train_config (set by multi_train_wrapper)
        if hasattr(self, 'train_config') and self.train_config:
            train_id = self.train_config.id
        # Source 2: data_manager.train_id
        elif hasattr(self, 'data_manager') and hasattr(self.data_manager, 'train_id') and self.data_manager.train_id:
            train_id = self.data_manager.train_id

        # Return train-prefixed pattern or plain pattern
        if train_id:
            return f"{train_id}_{base_pattern}"
        else:
            return base_pattern
'''

    # Insert helper method
    new_content = content[:next_newline] + helper_method + content[next_newline:]

    # Replace glob patterns
    replacements = [
        (r'glob\.glob\("experiment_\*\.csv"\)', 'glob.glob(self._get_csv_glob_pattern(\'pid\'))'),
        (r'glob\.glob\("step_response_\*\.csv"\)', 'glob.glob(self._get_csv_glob_pattern(\'step\'))'),
        (r'glob\.glob\("deadband_\*\.csv"\)', 'glob.glob(self._get_csv_glob_pattern(\'deadband\'))'),
    ]

    count = 0
    for pattern, replacement in replacements:
        matches = len(re.findall(pattern, new_content))
        new_content = re.sub(pattern, replacement, new_content)
        count += matches
        print(f"Replaced {matches} occurrences of {pattern}")

    # Write back
    with open(file_path, 'w') as f:
        f.write(new_content)

    print(f"\nTotal replacements: {count}")
    print("✓ CSV glob pattern fixes applied successfully")
    return True

if __name__ == '__main__':
    apply_csv_glob_fixes()
```

**Usage**:
```bash
python fix_csv_globs.py
```

---

## Expected Results

### Before Fixes

**PID Experiment**:
```
Console: [PID START] Created new CSV: trainA_experiment_20251110_143052.csv
Graph: "Experiment files not found"  ❌ Can't find trainA_experiment_*.csv
```

**Step Response**:
```
Console: [STEP START] Created new CSV: trainA_step_response_20251110_143052.csv
Graph: "No step data found"  ❌ Can't find trainA_step_response_*.csv
Second run: "Configure step parameters first"  ❌ MQTT topics wrong, params not confirmed
```

### After Fixes

**PID Experiment**:
```
Console: [PID START] Created new CSV: trainA_experiment_20251110_143052.csv
Graph: Shows real-time distance plot with 45 points  ✅ Found trainA_experiment_*.csv
```

**Step Response** (First Run):
```
Console: [STEP START] Created new CSV: trainA_step_response_20251110_143052.csv
Graph: Shows distance response with 120 points  ✅ Found trainA_step_response_*.csv
ESP32 Params: Amplitude=5.0, Time=10.0, Direction=Forward ✓  ✅ MQTT topics correct
```

**Step Response** (Second Run):
```
Console: [STEP START] Creating new CSV: trainA_step_response_20251110_143125.csv
Graph: Shows new experiment data  ✅ Restart works without application restart
ESP32 Params: Still confirmed ✓  ✅ Parameters persist between runs
```

---

## Priority Ranking

### Critical (Implement First)
1. ✅ Add `_get_csv_glob_pattern()` helper method
2. ✅ Fix PID graph glob (line 1524)
3. ✅ Fix Step response graph glob (line 3273)

**Estimated Time**: 15 minutes
**Impact**: PID and Step Response plots will immediately work

### High Priority (Implement Second)
4. ✅ Update download callbacks glob patterns
5. ✅ Fix deadband graph globs (if any)

**Estimated Time**: 10 minutes
**Impact**: CSV download buttons work, deadband plots work

### Essential (Implement Third)
6. ✅ MQTT topic isolation fixes (see `FIX_PROPOSAL.md`)

**Estimated Time**: 45 minutes
**Impact**: Step response restart issue fully resolved, multi-train isolation working

---

## Files to Modify

1. **train_control_platform.py**:
   - Add `_get_csv_glob_pattern()` method (1 new method)
   - Update graph callbacks (3-5 glob.glob replacements)
   - Update download callbacks (3-5 glob.glob replacements)
   - Add `get_topic()` method (1 new method)
   - Update `MQTTParameterSync` (3 method modifications)
   - Replace MQTT_TOPICS references (50+ replacements)

2. **No changes needed to**:
   - `multi_train_wrapper.py` (already correct)
   - `trains_config.json` (already correct)
   - ESP32 firmware (already correct)

---

## Rollback Plan

```bash
# Before starting, create backup
cp train_control_platform.py train_control_platform_backup_$(date +%Y%m%d_%H%M%S).py

# If issues occur, restore
cp train_control_platform_backup_YYYYMMDD_HHMMSS.py train_control_platform.py

# Or use git
git checkout train_control_platform.py
```

---

## Success Criteria

- [x] All issues analyzed and documented
- [ ] CSV glob helper method added
- [ ] PID plots show data in multi-train mode
- [ ] Step response plots show data in multi-train mode
- [ ] Step response can be stopped and restarted without app restart
- [ ] MQTT parameters confirmed immediately (200-500ms)
- [ ] Multi-train isolation working (no cross-interference)
- [ ] Single-train mode still works (backward compatible)
- [ ] All tests pass

---

**Status**: Analysis complete, ready for implementation
**Next**: Run quick fix script to resolve plotting issues, then implement MQTT fixes
