# Multi-Train Refactoring - Quick Start Guide

## TL;DR - What You Need to Do

This is a comprehensive refactoring to support multiple trains with URL routing. Here's the fastest path to implementation.

---

## Quick Implementation (30-Minute Version)

### Step 1: Create Configuration (2 minutes)

Create `trains_config.json`:

```json
{
  "trains": {
    "trainA": {
      "name": "Train A",
      "udp_port": 5555,
      "mqtt_prefix": "trenes/trainA",
      "pid_limits": {
        "kp_max": 250,
        "ki_max": 150,
        "kd_max": 150,
        "reference_min": 1,
        "reference_max": 100
      },
      "enabled": true
    }
  },
  "admin_password": "admin123",
  "dashboard_host": "127.0.0.1",
  "dashboard_port": 8050
}
```

### Step 2: Backup Current Version (1 minute)

```bash
cp train_control_platform.py train_control_platform_backup_$(date +%Y%m%d).py
```

### Step 3: Add MultiTrainApp Class (5 minutes)

Open `train_control_platform.py` and insert this BEFORE the `TrainControlDashboard` class (around line 1044):

```python
# =============================================================================
# Multi-Train Application Wrapper
# =============================================================================

class MultiTrainApp:
    """Multi-train application wrapper with URL routing"""

    def __init__(self):
        self.config_manager = TrainConfigManager()
        self.app = dash.Dash(__name__, suppress_callback_exceptions=True)
        self.train_dashboards = {}
        self.udp_receivers = {}
        self._initialize_trains()
        self._setup_routing()

    def _initialize_trains(self):
        enabled_trains = self.config_manager.get_enabled_trains()
        for train_id, train_config in enabled_trains.items():
            network_manager = NetworkManager()
            data_manager = DataManager(train_id=train_id)
            udp_receiver = UDPReceiver(data_manager, port=train_config.udp_port)

            dashboard = TrainControlDashboard(
                train_config=train_config,
                network_manager=network_manager,
                data_manager=data_manager,
                udp_receiver=udp_receiver,
                app=self.app
            )

            self.train_dashboards[train_id] = dashboard
            self.udp_receivers[train_id] = udp_receiver

    def _setup_routing(self):
        self.app.layout = html.Div([
            dcc.Location(id='url', refresh=False),
            html.Div(id='page-content')
        ])

        @self.app.callback(
            Output('page-content', 'children'),
            [Input('url', 'pathname')]
        )
        def display_page(pathname):
            if pathname == '/' or pathname is None:
                return self._create_landing_page()
            elif pathname and pathname.startswith('/train/'):
                train_id = pathname.split('/')[-1]
                if train_id in self.train_dashboards:
                    return self.train_dashboards[train_id].get_layout()
            return html.Div("404 - Page not found")

    def _create_landing_page(self):
        trains = self.config_manager.get_enabled_trains()
        cards = [
            html.Div([
                html.H3(cfg.name),
                html.A(html.Button("Access"), href=f'/train/{tid}')
            ]) for tid, cfg in trains.items()
        ]
        return html.Div([
            html.H1("Train Control Platform"),
            html.Div(cards)
        ])

    def run(self, host='127.0.0.1', port=8050, debug=False, use_reloader=False):
        self.app.run(host=host, port=port, debug=debug, use_reloader=use_reloader)
```

### Step 4: Update TrainControlDashboard __init__ (10 minutes)

**Find the __init__ method** (around line 1048) and change:

```python
# BEFORE:
def __init__(self, network_manager, data_manager, udp_receiver):

# AFTER:
def __init__(self, train_config: TrainConfig, network_manager, data_manager, udp_receiver, app=None):
    self.train_config = train_config
    self.train_id = train_config.id
    # ... rest of init

    # Generate train-specific MQTT topics
    self.mqtt_topics = self._generate_train_topics()

    # Use provided app or create new one
    if app is None:
        self.app = dash.Dash(__name__, suppress_callback_exceptions=True)
        self.standalone = True
    else:
        self.app = app
        self.standalone = False
```

**Add these two helper methods to TrainControlDashboard:**

```python
def _generate_train_topics(self):
    """Generate train-specific MQTT topics"""
    train_topics = {}
    for key, base_topic in MQTT_TOPICS.items():
        train_topics[key] = self.train_config.get_topic(base_topic)
    return train_topics

def _id(self, component_id):
    """Generate train-specific component ID"""
    return f"{self.train_id}-{component_id}"

def get_layout(self):
    """Get the dashboard layout (for multi-train routing)"""
    return self.app.layout
```

### Step 5: Update MQTT References (5 minutes)

**In MQTTParameterSync class __init__** (around line 258):

```python
# BEFORE:
def __init__(self):

# AFTER:
def __init__(self, mqtt_topics=None):
    # ... existing code ...
    self.topics = mqtt_topics if mqtt_topics is not None else MQTT_TOPICS
```

**Find and replace in MQTTParameterSync methods:**
- `MQTT_TOPICS[` → `self.topics[`

**In TrainControlDashboard __init__, update MQTT initialization:**

```python
# BEFORE:
self.mqtt_sync = MQTTParameterSync()

# AFTER:
self.mqtt_sync = MQTTParameterSync(mqtt_topics=self.mqtt_topics)
```

**Find and replace in TrainControlDashboard methods:**
- `MQTT_TOPICS[` → `self.mqtt_topics[`

### Step 6: Update Main Entry Point (5 minutes)

**Replace the bottom of the file** (lines 3737-end):

```python
# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == '__main__':
    config_manager = TrainConfigManager()
    enabled_trains = config_manager.get_enabled_trains()

    if len(enabled_trains) >= 1:
        # Multi-train or single-train mode
        print(f"Starting with {len(enabled_trains)} train(s)")

        if len(enabled_trains) == 1:
            # Single train - backward compatibility
            train_id = list(enabled_trains.keys())[0]
            train_config = enabled_trains[train_id]

            network_manager = NetworkManager()
            data_manager = DataManager(train_id=train_id)
            udp_receiver = UDPReceiver(data_manager, port=train_config.udp_port)

            dashboard = TrainControlDashboard(
                train_config=train_config,
                network_manager=network_manager,
                data_manager=data_manager,
                udp_receiver=udp_receiver
            )

            dashboard.run(debug=False, use_reloader=False)
        else:
            # Multi-train mode
            multi_app = MultiTrainApp()
            multi_app.run(debug=False, use_reloader=False)
    else:
        print("ERROR: No trains configured in trains_config.json")
```

### Step 7: Test (5 minutes)

```bash
python train_control_platform.py
```

- Should see: "Starting with 1 train(s)"
- Dashboard loads at http://127.0.0.1:8050
- Everything works as before

---

## Testing Multi-Train (Add Second Train)

### Add trainB to trains_config.json:

```json
{
  "trains": {
    "trainA": {
      "name": "Train A",
      "udp_port": 5555,
      "mqtt_prefix": "trenes/trainA",
      "pid_limits": {...},
      "enabled": true
    },
    "trainB": {
      "name": "Train B",
      "udp_port": 5556,
      "mqtt_prefix": "trenes/trainB",
      "pid_limits": {...},
      "enabled": true
    }
  },
  "admin_password": "admin123",
  "dashboard_host": "127.0.0.1",
  "dashboard_port": 8050
}
```

### Restart:

```bash
python train_control_platform.py
```

- Should see: "Starting with 2 trains"
- Landing page shows at http://127.0.0.1:8050/
- Click "Train A" → /train/trainA
- Click "Train B" → /train/trainB

---

## Critical Notes

### What You MUST Update (Minimum Viable Implementation)

1. **MultiTrainApp class** - Add to file
2. **TrainControlDashboard.__init__** - Accept train_config parameter
3. **_generate_train_topics()** - Add method
4. **_id()** - Add helper method
5. **MQTTParameterSync.__init__** - Accept mqtt_topics parameter
6. **Main entry point** - Support multi-train detection

### What You CAN Skip (For Now)

1. **Component ID prefixing** - Will work but may have issues with 2+ trains in same browser
2. **Landing page styling** - Basic version is functional
3. **Admin panel** - Not critical for functionality
4. **Full MQTT_TOPICS replacement** - Do it incrementally

### What Will Break Without Updates

1. **MQTT communication** - Won't work if topics aren't train-specific
2. **UDP reception** - Won't work if ports conflict
3. **Component IDs** - Will have collisions with 2+ trains

---

## Debugging

### If dashboard doesn't start:

```python
# Check configuration loading
config_manager = TrainConfigManager()
print(config_manager.trains)
print(config_manager.get_enabled_trains())
```

### If MQTT doesn't work:

```python
# Add to _generate_train_topics
def _generate_train_topics(self):
    train_topics = {}
    for key, base_topic in MQTT_TOPICS.items():
        train_topics[key] = self.train_config.get_topic(base_topic)
    print(f"[{self.train_id}] MQTT Topics:")
    print(f"  kp: {train_topics['kp']}")
    print(f"  sync: {train_topics['sync']}")
    return train_topics
```

### If routing doesn't work:

```python
# Add to _setup_routing callback
def display_page(pathname):
    print(f"Routing: {pathname}")
    print(f"Available trains: {list(self.train_dashboards.keys())}")
    # ... rest of callback
```

---

## Complete Implementation

For the **full implementation** with all features:

1. Read **IMPLEMENTATION_SUMMARY_MULTITRAIN.md** for complete checklist
2. Follow **MQTT_TOPICS_REPLACEMENT_GUIDE.md** for all MQTT updates
3. Follow **CALLBACK_ID_UPDATE_GUIDE.md** for all component ID updates
4. See **MULTI_TRAIN_REFACTORING.md** for detailed code sections

---

## Rollback Plan

If something breaks:

```bash
# Restore backup
cp train_control_platform_backup_YYYYMMDD.py train_control_platform.py

# Or use git
git checkout train_control_platform.py
```

---

## Support

**Issue:** "No module named 'TrainConfig'"
**Fix:** TrainConfig should already be defined around line 115

**Issue:** "get_topic not found"
**Fix:** TrainConfig.get_topic() should exist around line 124

**Issue:** "DataManager doesn't accept train_id"
**Fix:** This should already be updated per your context

**Issue:** Dashboard crashes with 2+ trains
**Fix:** Need to complete component ID prefixing (Step 7 in full guide)

---

## Success Checklist

- [ ] trains_config.json created
- [ ] Backup made
- [ ] MultiTrainApp class added
- [ ] TrainControlDashboard.__init__ updated
- [ ] Helper methods added (_generate_train_topics, _id, get_layout)
- [ ] MQTTParameterSync accepts mqtt_topics
- [ ] Main entry point updated
- [ ] Single train tested
- [ ] Multi-train tested (if applicable)

---

## Estimated Time

- **Minimum implementation:** 30-45 minutes
- **Full implementation:** 4-6 hours
- **Testing:** 1-2 hours

Start with minimum implementation, test, then gradually add features.

Good luck! 🚂
