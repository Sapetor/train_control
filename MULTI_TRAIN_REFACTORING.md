# Multi-Train Architecture Refactoring Guide

## Overview
This document contains the complete refactored code to transform the Train Control Platform from single-train to multi-train architecture with URL routing.

## Key Changes

### 1. MultiTrainApp Wrapper Class
- Manages multiple train dashboard instances
- Handles URL routing (/, /train/{trainId}, /admin)
- Creates separate UDP receivers and MQTT clients per train

### 2. TrainControlDashboard Modifications
- Accepts `train_config` parameter
- Uses train-specific MQTT topics via `self.mqtt_topics`
- All callback IDs prefixed with `{train_id}-`
- DataManager instances are train-specific

### 3. URL Routing
- Landing page shows train selection grid
- Admin page for train configuration
- Individual train dashboards at `/train/{trainId}`

## File Modifications Required

### File: train_control_platform.py

---

## SECTION 1: New MultiTrainApp Class (Insert BEFORE TrainControlDashboard class, around line 1044)

```python
# =============================================================================
# Multi-Train Application Wrapper
# =============================================================================

class MultiTrainApp:
    """
    Multi-train application wrapper with URL routing

    Manages multiple train dashboard instances, each with independent:
    - UDP receiver
    - MQTT client
    - Data managers
    - Network configuration

    Routes:
    - / : Landing page with train selection grid
    - /train/{trainId} : Individual train dashboard
    - /admin : Admin panel for train configuration
    """

    def __init__(self):
        """Initialize multi-train application"""
        print("\n" + "="*70)
        print("Initializing Multi-Train Control Platform")
        print("="*70 + "\n")

        # Load train configurations
        self.config_manager = TrainConfigManager()

        # Create main Dash app with URL routing support
        self.app = dash.Dash(
            __name__,
            suppress_callback_exceptions=True,  # Required for dynamic routing
            title="Train Control Platform"
        )

        # Storage for train-specific instances
        self.train_dashboards = {}      # TrainControlDashboard instances
        self.udp_receivers = {}         # UDPReceiver instances
        self.network_managers = {}      # NetworkManager instances
        self.data_managers = {}         # DataManager instances

        # Initialize all enabled trains
        self._initialize_trains()

        # Setup URL routing
        self._setup_routing()

        print("\nMulti-Train Platform initialized successfully")
        print(f"Enabled trains: {list(self.train_dashboards.keys())}")

    def _initialize_trains(self):
        """Initialize dashboard instances for each enabled train"""
        enabled_trains = self.config_manager.get_enabled_trains()

        if not enabled_trains:
            print("⚠️  WARNING: No enabled trains found in configuration!")
            print("    Please configure trains in the admin panel")
            return

        for train_id, train_config in enabled_trains.items():
            print(f"\nInitializing train: {train_config.name} (ID: {train_id})")

            # Create train-specific network manager
            network_manager = NetworkManager()
            self.network_managers[train_id] = network_manager

            # Create train-specific data managers
            data_manager = DataManager(train_id=train_id)
            step_data_manager = StepResponseDataManager(train_id=train_id)
            deadband_data_manager = DeadbandDataManager(train_id=train_id)

            self.data_managers[train_id] = {
                'pid': data_manager,
                'step': step_data_manager,
                'deadband': deadband_data_manager
            }

            # Create train-specific UDP receiver
            udp_receiver = UDPReceiver(
                data_manager=data_manager,
                ip='0.0.0.0',  # Listen on all interfaces
                port=train_config.udp_port
            )
            self.udp_receivers[train_id] = udp_receiver

            # Create train-specific dashboard
            dashboard = TrainControlDashboard(
                train_config=train_config,
                network_manager=network_manager,
                data_manager=data_manager,
                udp_receiver=udp_receiver,
                app=self.app  # Share the main app instance
            )

            # Set step and deadband data managers
            dashboard.step_data_manager = step_data_manager
            dashboard.deadband_data_manager = deadband_data_manager

            self.train_dashboards[train_id] = dashboard

            print(f"  ✓ UDP receiver on port {train_config.udp_port}")
            print(f"  ✓ MQTT prefix: {train_config.mqtt_prefix}")
            print(f"  ✓ Dashboard instance created")

    def _setup_routing(self):
        """Setup URL routing for multi-train application"""

        # Main layout with URL location and page content
        self.app.layout = html.Div([
            dcc.Location(id='url', refresh=False),
            html.Div(id='page-content')
        ])

        # Routing callback
        @self.app.callback(
            Output('page-content', 'children'),
            [Input('url', 'pathname')]
        )
        def display_page(pathname):
            """Route to appropriate page based on URL path"""

            # Root path - Landing page
            if pathname == '/' or pathname is None:
                return self._create_landing_page()

            # Train-specific dashboard
            elif pathname and pathname.startswith('/train/'):
                train_id = pathname.split('/')[-1]
                if train_id in self.train_dashboards:
                    return self.train_dashboards[train_id].get_layout()
                else:
                    return self._create_404_page(f"Train '{train_id}' not found")

            # Admin panel
            elif pathname == '/admin':
                return self._create_admin_page()

            # 404 - Page not found
            else:
                return self._create_404_page()

    def _create_landing_page(self):
        """Create landing page with train selection grid"""
        enabled_trains = self.config_manager.get_enabled_trains()

        # Create train cards
        train_cards = []
        for train_id, train_config in enabled_trains.items():
            train_cards.append(
                html.Div([
                    # Train card header
                    html.Div([
                        html.H3(train_config.name, style={
                            'color': '#1f2937',
                            'margin': '0 0 8px 0',
                            'fontSize': '24px',
                            'fontWeight': '600'
                        }),
                        html.P(f"ID: {train_config.id}", style={
                            'color': '#6b7280',
                            'margin': '0 0 4px 0',
                            'fontSize': '14px'
                        }),
                        html.P(f"UDP Port: {train_config.udp_port}", style={
                            'color': '#6b7280',
                            'margin': '0 0 4px 0',
                            'fontSize': '14px'
                        }),
                        html.P(f"MQTT: {train_config.mqtt_prefix}", style={
                            'color': '#6b7280',
                            'margin': '0',
                            'fontSize': '14px'
                        })
                    ], style={'marginBottom': '20px'}),

                    # Access button
                    html.A(
                        html.Button("Access Dashboard →", style={
                            'backgroundColor': '#3b82f6',
                            'color': 'white',
                            'border': 'none',
                            'padding': '12px 24px',
                            'borderRadius': '8px',
                            'fontSize': '16px',
                            'fontWeight': '500',
                            'cursor': 'pointer',
                            'transition': 'all 0.2s ease',
                            'width': '100%'
                        }),
                        href=f'/train/{train_id}'
                    )
                ], style={
                    'backgroundColor': 'white',
                    'padding': '24px',
                    'borderRadius': '12px',
                    'boxShadow': '0 4px 6px rgba(0,0,0,0.1)',
                    'transition': 'all 0.2s ease',
                    'minWidth': '280px'
                }, className='train-card')
            )

        # No trains configured message
        if not train_cards:
            train_cards = [
                html.Div([
                    html.H3("No Trains Configured", style={'color': '#6b7280'}),
                    html.P("Please configure trains in the admin panel.", style={'color': '#9ca3af'}),
                    html.A(
                        html.Button("Go to Admin Panel", style={
                            'backgroundColor': '#3b82f6',
                            'color': 'white',
                            'border': 'none',
                            'padding': '12px 24px',
                            'borderRadius': '8px',
                            'fontSize': '16px',
                            'cursor': 'pointer'
                        }),
                        href='/admin'
                    )
                ], style={
                    'backgroundColor': 'white',
                    'padding': '40px',
                    'borderRadius': '12px',
                    'textAlign': 'center'
                })
            ]

        return html.Div([
            # Header
            html.Div([
                html.H1("🚂 Train Control Platform", style={
                    'color': 'white',
                    'margin': '0',
                    'fontSize': '32px',
                    'fontWeight': '700'
                }),
                html.P("Multi-Train ESP32 PID Control System", style={
                    'color': 'rgba(255,255,255,0.9)',
                    'margin': '8px 0 0 0',
                    'fontSize': '16px'
                })
            ], style={
                'background': 'linear-gradient(135deg, #dc2626 0%, #1e40af 100%)',
                'color': 'white',
                'padding': '40px 24px',
                'borderRadius': '12px',
                'marginBottom': '32px',
                'textAlign': 'center'
            }),

            # Train selection grid
            html.Div(train_cards, style={
                'display': 'grid',
                'gridTemplateColumns': 'repeat(auto-fill, minmax(280px, 1fr))',
                'gap': '24px',
                'marginBottom': '32px'
            }),

            # Admin panel link
            html.Div([
                html.A(
                    html.Button("⚙️ Admin Panel", style={
                        'backgroundColor': '#6b7280',
                        'color': 'white',
                        'border': 'none',
                        'padding': '12px 24px',
                        'borderRadius': '8px',
                        'fontSize': '16px',
                        'fontWeight': '500',
                        'cursor': 'pointer'
                    }),
                    href='/admin'
                )
            ], style={'textAlign': 'center'})

        ], style={
            'backgroundColor': '#f8fafc',
            'minHeight': '100vh',
            'padding': '24px',
            'maxWidth': '1200px',
            'margin': '0 auto'
        })

    def _create_admin_page(self):
        """Create admin page for train configuration"""
        trains = self.config_manager.trains

        # Create train list with enable/disable controls
        train_list = []
        for train_id, train_config in trains.items():
            status_color = '#10b981' if train_config.enabled else '#ef4444'
            status_text = 'Enabled' if train_config.enabled else 'Disabled'

            train_list.append(
                html.Div([
                    html.Div([
                        html.H4(train_config.name, style={
                            'margin': '0 0 8px 0',
                            'color': '#1f2937'
                        }),
                        html.P(f"ID: {train_id}", style={
                            'margin': '0 0 4px 0',
                            'fontSize': '14px',
                            'color': '#6b7280'
                        }),
                        html.P(f"UDP Port: {train_config.udp_port} | MQTT: {train_config.mqtt_prefix}", style={
                            'margin': '0',
                            'fontSize': '14px',
                            'color': '#6b7280'
                        })
                    ], style={'flex': '1'}),

                    html.Div([
                        html.Span(status_text, style={
                            'backgroundColor': status_color,
                            'color': 'white',
                            'padding': '6px 12px',
                            'borderRadius': '6px',
                            'fontSize': '14px',
                            'fontWeight': '500'
                        })
                    ])
                ], style={
                    'backgroundColor': 'white',
                    'padding': '20px',
                    'borderRadius': '8px',
                    'marginBottom': '16px',
                    'display': 'flex',
                    'alignItems': 'center',
                    'justifyContent': 'space-between',
                    'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
                })
            )

        return html.Div([
            # Header
            html.Div([
                html.Div([
                    html.H1("⚙️ Admin Panel", style={
                        'color': 'white',
                        'margin': '0',
                        'fontSize': '28px'
                    }),
                    html.P("Manage train configurations", style={
                        'color': 'rgba(255,255,255,0.9)',
                        'margin': '8px 0 0 0'
                    })
                ], style={'flex': '1'}),

                html.A(
                    html.Button("← Back to Landing", style={
                        'backgroundColor': 'rgba(255,255,255,0.2)',
                        'color': 'white',
                        'border': '1px solid white',
                        'padding': '10px 20px',
                        'borderRadius': '6px',
                        'cursor': 'pointer'
                    }),
                    href='/'
                )
            ], style={
                'background': 'linear-gradient(135deg, #1f2937 0%, #3b82f6 100%)',
                'color': 'white',
                'padding': '32px 24px',
                'borderRadius': '12px',
                'marginBottom': '24px',
                'display': 'flex',
                'alignItems': 'center',
                'justifyContent': 'space-between'
            }),

            # Train list
            html.Div([
                html.H3("Configured Trains", style={
                    'color': '#1f2937',
                    'marginBottom': '20px'
                }),
                html.Div(train_list if train_list else [
                    html.P("No trains configured", style={'color': '#6b7280'})
                ])
            ], style={
                'backgroundColor': 'white',
                'padding': '24px',
                'borderRadius': '12px',
                'marginBottom': '24px',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
            }),

            # Configuration info
            html.Div([
                html.H3("Configuration File", style={
                    'color': '#1f2937',
                    'marginBottom': '12px'
                }),
                html.P(f"File: {self.config_manager.config_file}", style={
                    'color': '#6b7280',
                    'marginBottom': '8px'
                }),
                html.P("To modify train configurations, edit the trains_config.json file and restart the application.", style={
                    'color': '#6b7280',
                    'fontSize': '14px'
                })
            ], style={
                'backgroundColor': '#f8fafc',
                'padding': '20px',
                'borderRadius': '8px',
                'border': '1px solid #e5e7eb'
            })

        ], style={
            'backgroundColor': '#f8fafc',
            'minHeight': '100vh',
            'padding': '24px',
            'maxWidth': '1000px',
            'margin': '0 auto'
        })

    def _create_404_page(self, message="Page not found"):
        """Create 404 error page"""
        return html.Div([
            html.Div([
                html.H1("404", style={
                    'fontSize': '72px',
                    'margin': '0',
                    'color': '#dc2626'
                }),
                html.H2(message, style={
                    'fontSize': '24px',
                    'margin': '16px 0',
                    'color': '#1f2937'
                }),
                html.P("The page you're looking for doesn't exist.", style={
                    'color': '#6b7280',
                    'marginBottom': '24px'
                }),
                html.A(
                    html.Button("← Back to Home", style={
                        'backgroundColor': '#3b82f6',
                        'color': 'white',
                        'border': 'none',
                        'padding': '12px 24px',
                        'borderRadius': '8px',
                        'fontSize': '16px',
                        'cursor': 'pointer'
                    }),
                    href='/'
                )
            ], style={
                'backgroundColor': 'white',
                'padding': '60px',
                'borderRadius': '12px',
                'textAlign': 'center',
                'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
            })
        ], style={
            'backgroundColor': '#f8fafc',
            'minHeight': '100vh',
            'padding': '24px',
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'center'
        })

    def run(self, host='127.0.0.1', port=8050, debug=False, use_reloader=False):
        """Run the multi-train dashboard application"""
        print(f"\n{'='*70}")
        print(f"Starting Multi-Train Dashboard at http://{host}:{port}")
        print(f"{'='*70}\n")
        print("Available routes:")
        print(f"  - / (Landing page with train selection)")
        print(f"  - /train/{{trainId}} (Individual train dashboards)")
        print(f"  - /admin (Admin panel)")
        print()

        # Disable Flask request logging to reduce terminal spam
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        self.app.run(host=host, port=port, debug=debug, use_reloader=use_reloader)

    def stop(self):
        """Stop all UDP receivers gracefully"""
        print("\nShutting down all train receivers...")
        for train_id, receiver in self.udp_receivers.items():
            print(f"  Stopping {train_id}...")
            receiver.stop()
        print("All receivers stopped")
```

---

## SECTION 2: Refactored TrainControlDashboard Constructor

Replace the __init__ method of TrainControlDashboard (around line 1048) with:

```python
def __init__(self, train_config: TrainConfig, network_manager, data_manager, udp_receiver, app=None):
    """
    Initialize Train Control Dashboard

    Args:
        train_config: TrainConfig instance with train-specific settings
        network_manager: NetworkManager instance for this train
        data_manager: DataManager instance for this train
        udp_receiver: UDPReceiver instance for this train
        app: Optional existing Dash app instance (for multi-train setup)
    """
    self.train_config = train_config
    self.train_id = train_config.id
    self.network_manager = network_manager
    self.data_manager = data_manager
    self.udp_receiver = udp_receiver

    # Track which experiment mode is active ('pid', 'step', or 'deadband')
    self.experiment_mode = 'pid'

    # Create step response data manager (will be set by MultiTrainApp if using multi-train)
    self.step_data_manager = StepResponseDataManager(train_id=train_config.id)

    # Create deadband calibration data manager
    self.deadband_data_manager = DeadbandDataManager(train_id=train_config.id)

    # Initialize current language from network manager
    self.current_language = self.network_manager.language

    # Generate train-specific MQTT topics
    self.mqtt_topics = self._generate_train_topics()

    # Initialize MQTT parameter sync with train-specific topics
    self.mqtt_sync = MQTTParameterSync(mqtt_topics=self.mqtt_topics)
    self.confirmed_params = {
        'kp': 0.0,
        'ki': 0.0,
        'kd': 0.0,
        'reference': 10.0
    }

    # Set up callback for when parameters are confirmed by Arduino
    self.mqtt_sync.on_params_updated = self._on_params_confirmed

    # Store zoom state to preserve user zoom when data updates
    self.zoom_state = {
        f'{self.train_id}-realtime-graph': {
            'xaxis.range[0]': None,
            'xaxis.range[1]': None,
            'yaxis.range[0]': None,
            'yaxis.range[1]': None,
            'user_has_zoomed': False
        },
        f'{self.train_id}-historical-graph': {
            'xaxis.range[0]': None,
            'xaxis.range[1]': None,
            'yaxis.range[0]': None,
            'yaxis.range[1]': None,
            'user_has_zoomed': False
        }
    }

    # Language dictionaries (keep existing translations)
    self.translations = {
        # ... (keep all existing translations)
    }

    # Use provided app or create new one
    if app is None:
        # Single train mode - create own app
        external_stylesheets = [
            'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
        ]
        self.app = dash.Dash(__name__, external_stylesheets=external_stylesheets,
                            suppress_callback_exceptions=True)
        self.standalone = True
    else:
        # Multi-train mode - use shared app
        self.app = app
        self.standalone = False

    # Setup message queue for push notifications
    self.websocket_messages = queue.Queue(maxsize=100)

    # Connect callback to data sources
    self.data_manager.websocket_callback = self._push_websocket_message
    self.mqtt_sync.websocket_callback = self._push_websocket_message
    self.step_data_manager.websocket_callback = self._push_websocket_message

    # Modern color scheme (keep existing colors)
    self.colors = {
        'primary': '#1f2937',
        'secondary': '#3b82f6',
        'accent': '#10b981',
        'background': '#f8fafc',
        'surface': '#ffffff',
        'text': '#1f2937',
        'text_light': '#6b7280',
        'success': '#10b981',
        'warning': '#f59e0b',
        'danger': '#ef4444',
        'train_primary': '#dc2626',
        'train_secondary': '#1e40af'
    }

    # Only setup layout and callbacks if standalone mode
    if self.standalone:
        self.setup_layout()
        self.setup_callbacks()
    else:
        # Multi-train mode - callbacks will be set up later
        self.setup_callbacks()

def _generate_train_topics(self):
    """
    Generate train-specific MQTT topics

    Replaces 'trenes/' prefix with train-specific MQTT prefix
    """
    train_topics = {}
    for key, base_topic in MQTT_TOPICS.items():
        # Use TrainConfig's get_topic method to convert base topic
        train_topics[key] = self.train_config.get_topic(base_topic)

    print(f"\n[Train {self.train_id}] MQTT Topics:")
    print(f"  Base: trenes/* → Train: {self.train_config.mqtt_prefix}/*")
    print(f"  Example: {MQTT_TOPICS['kp']} → {train_topics['kp']}")

    return train_topics

def get_layout(self):
    """
    Get the dashboard layout for this train

    Used by MultiTrainApp for URL routing
    """
    # This will return the same layout created by setup_layout()
    # but allows MultiTrainApp to retrieve it for routing

    # Re-create layout to ensure fresh state
    return html.Div([
        dcc.Store(id=f'{self.train_id}-language-store', data={'language': 'es'}),
        dcc.Store(id=f'{self.train_id}-network-config-store', data={}),
        dcc.Store(id=f'{self.train_id}-mqtt-params-store', data={'last_update': 0}),

        # ... rest of layout with train_id prefixes ...
        # (Full implementation in next section)
    ])
```

---

## SECTION 3: Update MQTTParameterSync to Accept Custom Topics

Modify the MQTTParameterSync class __init__ (around line 258):

```python
class MQTTParameterSync:
    """Handles MQTT communication for PID parameter synchronization"""

    def __init__(self, mqtt_topics=None):
        """
        Initialize MQTT parameter sync

        Args:
            mqtt_topics: Optional dict of train-specific MQTT topics
                        If None, uses global MQTT_TOPICS
        """
        self.mqtt_client = mqtt.Client(client_id=f"train_dashboard_{uuid.uuid4().hex[:8]}")
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.connected = False
        self.broker_ip = None

        # Use provided topics or default global topics
        self.topics = mqtt_topics if mqtt_topics is not None else MQTT_TOPICS

        # Callback for when parameters are confirmed
        self.on_params_updated = None

        # Callback for websocket push notifications
        self.websocket_callback = None

        # Store confirmed parameter values
        self.confirmed_params = {
            'kp': 0.0,
            'ki': 0.0,
            'kd': 0.0,
            'reference': 10.0,
            'step_amplitude': 0.0,
            'step_time': 0.0,
            'step_direction': 1,
            'step_vbatt': 0.0
        }
```

Then update all references to `MQTT_TOPICS` within MQTTParameterSync to use `self.topics`:

```python
def _on_connect(self, client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        print("Connected to MQTT broker")
        self.connected = True

        # Subscribe to status topics for PID parameters
        client.subscribe([
            (self.topics['kp_status'], 0),
            (self.topics['ki_status'], 0),
            (self.topics['kd_status'], 0),
            (self.topics['ref_status'], 0)
        ])

        # Subscribe to status topics for step response parameters
        client.subscribe([
            (self.topics['step_amplitude_status'], 0),
            (self.topics['step_time_status'], 0),
            (self.topics['step_direction_status'], 0),
            (self.topics['step_vbatt_status'], 0)
        ])

        # Request current parameters from ESP32
        client.publish(self.topics['request_params'], "1")
        client.publish(self.topics['step_request_params'], "1")
    # ... rest of method
```

---

## SECTION 4: Update Callback ID Prefixing

All callback IDs in TrainControlDashboard need to be prefixed with `{train_id}-`.

Key method to add to TrainControlDashboard:

```python
def _id(self, component_id):
    """
    Generate train-specific component ID

    Args:
        component_id: Base component ID

    Returns:
        Prefixed ID: {train_id}-{component_id}
    """
    return f"{self.train_id}-{component_id}"
```

Then update ALL component IDs in layout creation and callbacks:

**BEFORE:**
```python
html.Button(id='start-experiment-btn', ...)
```

**AFTER:**
```python
html.Button(id=self._id('start-experiment-btn'), ...)
```

---

## SECTION 5: Update Main Entry Point

Replace the global instances and main entry point (lines 3737-3792) with:

```python
# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("Train Control Platform")
    print("VERSION: 2025-11-09 Multi-Train Architecture")
    print("="*70 + "\n")

    # Check if multi-train mode
    config_manager = TrainConfigManager()
    enabled_trains = config_manager.get_enabled_trains()

    if len(enabled_trains) > 1:
        # Multi-train mode
        print(f"Multi-train mode: {len(enabled_trains)} trains configured")
        multi_app = MultiTrainApp()

        try:
            multi_app.run(
                host=config_manager.dashboard_host,
                port=config_manager.dashboard_port,
                debug=False,
                use_reloader=False
            )
        except KeyboardInterrupt:
            print("\nShutting down...")
            multi_app.stop()

    elif len(enabled_trains) == 1:
        # Single-train mode (backward compatibility)
        print("Single-train mode")
        train_id = list(enabled_trains.keys())[0]
        train_config = enabled_trains[train_id]

        # Create instances
        network_manager = NetworkManager()
        data_manager = DataManager(train_id=train_id)
        udp_receiver = UDPReceiver(data_manager, port=train_config.udp_port)

        # Create dashboard
        dashboard = TrainControlDashboard(
            train_config=train_config,
            network_manager=network_manager,
            data_manager=data_manager,
            udp_receiver=udp_receiver
        )

        print(f"\nStarting dashboard at http://127.0.0.1:8050")

        # Disable Flask request logging
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        try:
            dashboard.run(debug=False, use_reloader=False)
        except KeyboardInterrupt:
            print("\nShutting down...")
            udp_receiver.stop()

    else:
        print("ERROR: No trains configured!")
        print("Please create a trains_config.json file with train configurations")
        print("\nExample configuration:")
        print("""
{
  "trains": {
    "trainA": {
      "name": "Train A",
      "udp_port": 5555,
      "mqtt_prefix": "trenes",
      "pid_limits": {
        "kp_max": 250,
        "ki_max": 150,
        "kd_max": 150
      },
      "enabled": true
    }
  },
  "admin_password": "admin123",
  "dashboard_host": "127.0.0.1",
  "dashboard_port": 8050
}
        """)
```

---

## Implementation Steps

1. **Backup current file**
   ```bash
   cp train_control_platform.py train_control_platform_before_multitr ain.py
   ```

2. **Add MultiTrainApp class** (Section 1)
   - Insert before TrainControlDashboard class

3. **Update TrainControlDashboard.__init__** (Section 2)
   - Add train_config parameter
   - Generate train-specific MQTT topics
   - Add _id() helper method

4. **Update MQTTParameterSync** (Section 3)
   - Accept custom mqtt_topics parameter
   - Replace MQTT_TOPICS with self.topics

5. **Update all component IDs** (Section 4)
   - Add self._id() calls throughout layout creation
   - Update all callbacks to use prefixed IDs

6. **Update main entry point** (Section 5)
   - Add multi-train detection
   - Create MultiTrainApp or single TrainControlDashboard

7. **Test configuration**
   - Create trains_config.json with test trains
   - Start application
   - Verify landing page appears
   - Access individual train dashboards
   - Check MQTT topic prefixes in logs

---

## Next Steps

After implementing these changes:

1. **Update DataManager classes** to fully support train_id in file naming
2. **Update CSV file naming** to include train_id prefix
3. **Test MQTT communication** with train-specific topics
4. **Add admin panel functionality** for live train enable/disable
5. **Implement train configuration editor** in admin panel

---

## Compatibility Notes

- **Backward compatible**: Single train configuration still works
- **Gradual migration**: Can run single train first, then add more
- **File structure**: Existing CSV files remain compatible
- **Network config**: Each train has independent network configuration

