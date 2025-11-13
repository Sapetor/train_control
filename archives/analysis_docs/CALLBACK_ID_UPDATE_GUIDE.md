# Callback ID Update Guide

## Overview
This guide provides a systematic approach to updating all component IDs in TrainControlDashboard to support multi-train architecture.

## Strategy

All component IDs need to be prefixed with the train ID to avoid collisions when multiple trains are loaded in the same Dash app.

### ID Naming Convention

**Single Train (Current):**
```python
id='start-experiment-btn'
```

**Multi-Train (New):**
```python
id=self._id('start-experiment-btn')  # Results in: 'trainA-start-experiment-btn'
```

## Helper Method

Add this method to TrainControlDashboard class:

```python
def _id(self, component_id):
    """
    Generate train-specific component ID

    Args:
        component_id: Base component ID (e.g., 'start-btn')

    Returns:
        Train-specific ID (e.g., 'trainA-start-btn')

    Example:
        >>> self.train_id = 'trainA'
        >>> self._id('start-btn')
        'trainA-start-btn'
    """
    return f"{self.train_id}-{component_id}"
```

## Component Categories

### Category 1: Buttons

**Pattern:**
```python
html.Button(id='button-name', ...)
```

**Update to:**
```python
html.Button(id=self._id('button-name'), ...)
```

**Examples:**

```python
# Start/Stop experiment buttons
html.Button(id=self._id('start-experiment-btn'), ...)
html.Button(id=self._id('stop-experiment-btn'), ...)

# Network configuration
html.Button(id=self._id('refresh-interfaces-btn'), ...)
html.Button(id=self._id('apply-config-btn'), ...)

# Parameter controls
html.Button(id=self._id('send-kp-btn'), ...)
html.Button(id=self._id('send-ki-btn'), ...)
html.Button(id=self._id('send-kd-btn'), ...)
html.Button(id=self._id('send-ref-btn'), ...)

# Step response
html.Button(id=self._id('send-step-params-btn'), ...)

# CSV download
html.Button(id=self._id('download-csv-btn-control'), ...)
html.Button(id=self._id('download-csv-btn-step'), ...)
html.Button(id=self._id('download-csv-btn-deadband'), ...)
```

### Category 2: Dropdowns

```python
# Network interface selection
dcc.Dropdown(id=self._id('network-interface-dropdown'), ...)

# Language selection
dcc.Dropdown(id=self._id('language-dropdown'), ...)
```

### Category 3: Inputs

```python
# Numeric inputs
dcc.Input(id=self._id('udp-port-input'), ...)
dcc.Input(id=self._id('mqtt-port-input'), ...)
dcc.Input(id=self._id('kp-input'), ...)
dcc.Input(id=self._id('ki-input'), ...)
dcc.Input(id=self._id('kd-input'), ...)
dcc.Input(id=self._id('reference-input'), ...)
dcc.Input(id=self._id('step-amplitude-input'), ...)
dcc.Input(id=self._id('step-time-input'), ...)
dcc.Input(id=self._id('deadband-threshold-input'), ...)
```

### Category 4: Graphs

```python
dcc.Graph(id=self._id('realtime-graph'), ...)
dcc.Graph(id=self._id('historical-graph'), ...)
dcc.Graph(id=self._id('step-response-graph'), ...)
dcc.Graph(id=self._id('deadband-pwm-graph'), ...)
dcc.Graph(id=self._id('deadband-distance-graph'), ...)
dcc.Graph(id=self._id('deadband-calibration-graph'), ...)
```

### Category 5: Stores (dcc.Store)

```python
dcc.Store(id=self._id('language-store'), ...)
dcc.Store(id=self._id('network-config-store'), ...)
dcc.Store(id=self._id('mqtt-params-store'), ...)
dcc.Store(id=self._id('ws-message-store'), ...)
dcc.Store(id=self._id('experiment-mode-store'), ...)
```

### Category 6: Intervals

```python
dcc.Interval(id=self._id('data-refresh-interval'), ...)
dcc.Interval(id=self._id('mqtt-status-refresh'), ...)
dcc.Interval(id=self._id('fast-update-check'), ...)
dcc.Interval(id=self._id('page-load-trigger'), ...)
```

### Category 7: Display Components

```python
html.Div(id=self._id('experiment-status-top'), ...)
html.Div(id=self._id('connection-status-display'), ...)
html.Div(id=self._id('parameter-status-display'), ...)
html.Div(id=self._id('step-parameter-status-display'), ...)
html.Div(id=self._id('network-status'), ...)
html.Div(id=self._id('esp32-config-section'), ...)
html.Div(id=self._id('tab-content'), ...)
```

### Category 8: Tabs

```python
dcc.Tabs(id=self._id('main-tabs'), ...)
dcc.Tab(value=self._id('network-tab'), ...)
dcc.Tab(value=self._id('control-tab'), ...)
dcc.Tab(value=self._id('step-response-tab'), ...)
dcc.Tab(value=self._id('deadband-tab'), ...)
dcc.Tab(value=self._id('data-tab'), ...)
```

### Category 9: Radio Items

```python
dcc.RadioItems(id=self._id('step-direction-radio'), ...)
dcc.RadioItems(id=self._id('deadband-direction-radio'), ...)
```

### Category 10: Text Components

```python
html.H1(id=self._id('app-title'), ...)
html.P(id=self._id('app-subtitle'), ...)
html.Label(id=self._id('language-label'), ...)
html.Span(id=self._id('mode-indicator'), ...)
```

### Category 11: Downloads

```python
dcc.Download(id=self._id('download-dataframe-csv'), ...)
```

## Callback Updates

### Pattern for Callbacks

**BEFORE:**
```python
@self.app.callback(
    Output('output-component', 'property'),
    [Input('input-component', 'property')]
)
def my_callback(input_value):
    # ...
```

**AFTER:**
```python
@self.app.callback(
    Output(self._id('output-component'), 'property'),
    [Input(self._id('input-component'), 'property')]
)
def my_callback(input_value):
    # ...
```

### Example: Start Experiment Callback

**BEFORE:**
```python
@self.app.callback(
    [Output('experiment-status-top', 'children'),
     Output('experiment-mode-store', 'data')],
    [Input('start-experiment-btn', 'n_clicks'),
     Input('main-tabs', 'value')],
    [State('experiment-mode-store', 'data')]
)
def start_experiment(n_clicks, active_tab, mode_data):
    # ...
```

**AFTER:**
```python
@self.app.callback(
    [Output(self._id('experiment-status-top'), 'children'),
     Output(self._id('experiment-mode-store'), 'data')],
    [Input(self._id('start-experiment-btn'), 'n_clicks'),
     Input(self._id('main-tabs'), 'value')],
    [State(self._id('experiment-mode-store'), 'data')]
)
def start_experiment(n_clicks, active_tab, mode_data):
    # ...
```

## Complete ID Inventory

Here's a comprehensive list of all component IDs that need updating:

### Network Tab
- `network-interface-dropdown`
- `refresh-interfaces-btn`
- `udp-port-input`
- `mqtt-port-input`
- `apply-config-btn`
- `network-status`
- `esp32-config-section`

### Control Tab (PID)
- `kp-input`
- `ki-input`
- `kd-input`
- `reference-input`
- `send-kp-btn`
- `send-ki-btn`
- `send-kd-btn`
- `send-ref-btn`
- `parameter-status-display`
- `connection-status-display`
- `realtime-graph`
- `download-csv-btn-control`

### Step Response Tab
- `step-amplitude-input`
- `step-time-input`
- `step-direction-radio`
- `send-step-params-btn`
- `step-parameter-status-display`
- `step-response-graph`
- `download-csv-btn-step`

### Deadband Tab
- `deadband-direction-radio`
- `deadband-threshold-input`
- `deadband-start-btn`
- `deadband-stop-btn`
- `deadband-status-display`
- `deadband-result-display`
- `deadband-pwm-graph`
- `deadband-distance-graph`
- `deadband-calibration-graph`
- `download-csv-btn-deadband`

### Data Tab
- `historical-graph`
- `csv-file-path-display`
- `total-packets-display`

### Global Components
- `language-dropdown`
- `language-label`
- `language-store`
- `app-title`
- `app-subtitle`
- `mode-indicator`
- `main-tabs`
- `tab-content`
- `start-experiment-btn`
- `stop-experiment-btn`
- `experiment-status-top`
- `experiment-mode-store`
- `network-config-store`
- `mqtt-params-store`
- `ws-message-store`
- `data-refresh-interval`
- `mqtt-status-refresh`
- `fast-update-check`
- `page-load-trigger`
- `download-dataframe-csv`

## Automated Update Script

```python
import re

def update_component_ids(file_path):
    """
    Automatically update component IDs in TrainControlDashboard class

    Adds self._id() wrapper to all id= parameters
    """

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to match id='...' or id="..." within TrainControlDashboard class
    # Only replace literal string IDs, not function calls

    def replace_id(match):
        """Replace id='component-id' with id=self._id('component-id')"""
        full_match = match.group(0)
        component_id = match.group(1)

        # Skip if already using self._id()
        if 'self._id(' in full_match:
            return full_match

        # Replace with train-specific ID
        return f"id=self._id('{component_id}')"

    # Find TrainControlDashboard class
    class_start = content.find('class TrainControlDashboard:')
    if class_start == -1:
        print("ERROR: TrainControlDashboard class not found")
        return

    # Find next class or end of file
    next_class = content.find('\nclass ', class_start + 1)
    class_end = next_class if next_class != -1 else len(content)

    # Extract class content
    before_class = content[:class_start]
    class_content = content[class_start:class_end]
    after_class = content[class_end:]

    # Replace all id='...' patterns in class content
    updated_class = re.sub(
        r"id=['\"]([a-zA-Z0-9\-_]+)['\"]",
        replace_id,
        class_content
    )

    # Reconstruct file
    updated_content = before_class + updated_class + after_class

    # Save updated file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    print("✓ Component IDs updated successfully")

    # Count replacements
    original_ids = len(re.findall(r"id=['\"]([a-zA-Z0-9\-_]+)['\"]", class_content))
    updated_ids = len(re.findall(r"id=self\._id\(", updated_class))

    print(f"  Updated {updated_ids} component IDs")

# Run the script
update_component_ids('train_control_platform.py')
```

## Manual Verification Steps

After running the automated script, manually verify:

1. **Check for missed IDs:**
   ```bash
   # Search for literal id= in TrainControlDashboard
   grep -n "id=['\"][a-z]" train_control_platform.py
   ```

2. **Check for double-wrapped IDs:**
   ```bash
   # Should not find any
   grep -n "self._id.*self._id" train_control_platform.py
   ```

3. **Verify callback signatures:**
   ```bash
   # All callbacks should use self._id()
   grep -A 5 "@self.app.callback" train_control_platform.py
   ```

## Testing

After updating all IDs:

1. **Single train test:**
   - Configure one train
   - Start dashboard
   - Verify all components work
   - Check browser console for errors

2. **Multi-train test:**
   - Configure two trains
   - Access /train/trainA
   - Access /train/trainB
   - Verify no ID collisions
   - Check that actions on trainA don't affect trainB

3. **ID collision test:**
   - Open browser developer tools
   - Check for "duplicate ID" warnings
   - Should be NONE

## Common Issues

### Issue 1: Callback not triggering
**Cause:** Mismatch between component ID and callback ID
**Solution:** Ensure both use `self._id('same-name')`

### Issue 2: Component not rendering
**Cause:** Tab value mismatch
**Solution:** Ensure tab values also use `self._id()`

### Issue 3: Graph not updating
**Cause:** Graph ID in callback doesn't match layout
**Solution:** Check zoom state dictionary keys also updated

## Zoom State Dictionary Update

Don't forget to update zoom state keys:

**BEFORE:**
```python
self.zoom_state = {
    'realtime-graph': {...},
    'historical-graph': {...}
}
```

**AFTER:**
```python
self.zoom_state = {
    self._id('realtime-graph'): {...},
    self._id('historical-graph'): {...}
}
```

Or reference dynamically in methods:
```python
def _handle_zoom_state(self, graph_id, relayout_data):
    if relayout_data and graph_id in self.zoom_state:
        zoom_state = self.zoom_state[graph_id]
        # ...
```

## Next Steps

After completing callback ID updates:

1. Test single train mode thoroughly
2. Test multi-train mode with 2+ trains
3. Verify MQTT topics are train-specific
4. Check CSV files have train-specific names
5. Test URL routing (/, /train/X, /admin)
