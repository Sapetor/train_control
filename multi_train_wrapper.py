"""
Multi-Train Wrapper for Train Control Platform
===============================================
This module wraps the existing TrainControlDashboard to support multiple trains
with URL-based routing and independent control.

Usage:
    python multi_train_wrapper.py

Features:
- Landing page at / with train selection
- Train-specific dashboards at /train/{trainId}
- Admin panel at /admin
- Independent UDP receivers and MQTT clients per train
"""

import dash
from dash import dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate
import os
import sys

# Import from existing platform
from train_control_platform import (
    TrainControlDashboard,
    NetworkManager,
    DataManager,
    StepResponseDataManager,
    DeadbandDataManager,
    UDPReceiver,
    MQTTParameterSync,
    TrainConfigManager,
    TrainConfig
)


class MultiTrainApp:
    """
    Wrapper application that manages multiple train dashboard instances
    with URL-based routing
    """

    def __init__(self):
        # Load train configurations
        self.config_manager = TrainConfigManager()

        # Create Dash app with suppressed callback exceptions for routing
        self.app = dash.Dash(
            __name__,
            suppress_callback_exceptions=True,
            title="Multi-Train Control Platform"
        )

        # Shared network manager (uses same broker for all trains)
        self.network_manager = NetworkManager()

        # Storage for train-specific components
        self.train_dashboards = {}
        self.udp_receivers = {}
        self.data_managers = {}

        # Initialize train dashboard instances
        self._initialize_train_dashboards()

        # Setup main app layout and routing
        self._setup_layout()
        self._setup_routing()

        print(f"[MULTI-TRAIN] Initialized with {len(self.train_dashboards)} trains")

    def _initialize_train_dashboards(self):
        """Create dashboard instances for each enabled train"""
        enabled_trains = self.config_manager.get_enabled_trains()

        for train_id, train_config in enabled_trains.items():
            try:
                # Create train-specific data managers
                data_manager = DataManager(train_id=train_config.id)
                step_data_manager = StepResponseDataManager(train_id=train_config.id)
                deadband_data_manager = DeadbandDataManager(train_id=train_config.id)

                # Create UDP receiver for this train
                # Note: UDPReceiver only accepts one data_manager, switches modes via set_data_manager()
                udp_receiver = UDPReceiver(
                    data_manager=data_manager,
                    port=train_config.udp_port
                )

                # Store components
                self.udp_receivers[train_id] = udp_receiver
                self.data_managers[train_id] = {
                    'pid': data_manager,
                    'step': step_data_manager,
                    'deadband': deadband_data_manager
                }

                # Create dashboard instance for this train
                # CRITICAL: Pass skip_setup=True to prevent layout creation until config is set
                dashboard = TrainControlDashboard(
                    network_manager=self.network_manager,
                    data_manager=data_manager,
                    udp_receiver=udp_receiver,
                    app=self.app,  # Share the wrapper's app instance
                    skip_setup=True  # Don't create layout yet
                )

                # Override data managers with train-specific ones
                dashboard.step_data_manager = step_data_manager
                dashboard.deadband_data_manager = deadband_data_manager

                # Store train config for MQTT topic generation
                dashboard.train_config = train_config

                # Generate and store train-specific MQTT topics
                dashboard.mqtt_topics = self._generate_train_topics(train_config.mqtt_prefix)

                # NOW create the layout after all configuration is set
                dashboard.setup_layout()
                dashboard.setup_callbacks()

                self.train_dashboards[train_id] = dashboard

                print(f"[MULTI-TRAIN] Initialized {train_config.name} (UDP: {train_config.udp_port}, MQTT: {train_config.mqtt_prefix})")

            except Exception as e:
                print(f"[MULTI-TRAIN ERROR] Failed to initialize {train_id}: {e}")

    def _generate_train_topics(self, mqtt_prefix):
        """Generate train-specific MQTT topics"""
        from train_control_platform import MQTT_TOPICS

        train_topics = {}
        for key, topic in MQTT_TOPICS.items():
            # Replace 'trenes/' with train-specific prefix
            if topic.startswith('trenes/'):
                train_topics[key] = topic.replace('trenes/', f'{mqtt_prefix}/', 1)
            else:
                train_topics[key] = f'{mqtt_prefix}/{topic}'

        return train_topics

    def _setup_layout(self):
        """Setup main app layout with URL routing"""
        self.app.layout = html.Div([
            dcc.Location(id='url', refresh=False),
            html.Div(id='page-content', style={'minHeight': '100vh'})
        ])

    def _setup_routing(self):
        """Setup URL routing callback"""
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
                    return self._create_train_page(train_id)
                else:
                    return self._create_not_found_page(train_id)
            elif pathname == '/admin':
                return self._create_admin_page()
            else:
                return self._create_404_page()

    def _create_landing_page(self):
        """Create landing page with train selection grid"""
        enabled_trains = self.config_manager.get_enabled_trains()

        # Page header
        header = html.Div([
            html.H1("🚂 Train Control Platform", style={
                'textAlign': 'center',
                'color': '#2c3e50',
                'marginBottom': '10px'
            }),
            html.P("Select a train to begin", style={
                'textAlign': 'center',
                'color': '#7f8c8d',
                'fontSize': '18px'
            })
        ], style={'padding': '40px 20px 20px'})

        # Train selection grid
        train_cards = []
        for train_id, train_config in enabled_trains.items():
            card = html.Div([
                html.Div([
                    html.H3(train_config.name, style={
                        'margin': '0 0 10px 0',
                        'color': '#2c3e50'
                    }),
                    html.P(f"ID: {train_config.id}", style={
                        'margin': '0 0 5px 0',
                        'color': '#7f8c8d',
                        'fontSize': '14px'
                    }),
                    html.P(f"UDP Port: {train_config.udp_port}", style={
                        'margin': '0 0 15px 0',
                        'color': '#95a5a6',
                        'fontSize': '12px'
                    }),
                    html.A(
                        html.Button("Access Dashboard →", style={
                            'width': '100%',
                            'padding': '12px',
                            'backgroundColor': '#3498db',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '6px',
                            'cursor': 'pointer',
                            'fontSize': '16px',
                            'fontWeight': 'bold'
                        }),
                        href=f'/train/{train_config.id}'
                    )
                ], style={
                    'padding': '20px',
                })
            ], style={
                'backgroundColor': 'white',
                'borderRadius': '12px',
                'boxShadow': '0 4px 6px rgba(0,0,0,0.1)',
                'transition': 'transform 0.2s',
                'minWidth': '280px'
            })
            train_cards.append(card)

        train_grid = html.Div(train_cards, style={
            'display': 'grid',
            'gridTemplateColumns': 'repeat(auto-fit, minmax(280px, 1fr))',
            'gap': '20px',
            'padding': '20px',
            'maxWidth': '1200px',
            'margin': '0 auto'
        })

        # Admin link
        footer = html.Div([
            html.Hr(style={'margin': '40px 0 20px 0'}),
            html.A("⚙️ Admin Panel", href='/admin', style={
                'color': '#3498db',
                'textDecoration': 'none',
                'fontSize': '16px'
            })
        ], style={
            'textAlign': 'center',
            'padding': '20px'
        })

        return html.Div([header, train_grid, footer], style={
            'backgroundColor': '#ecf0f1',
            'minHeight': '100vh'
        })

    def _create_train_page(self, train_id):
        """Create page for specific train dashboard"""
        dashboard = self.train_dashboards[train_id]
        train_config = self.config_manager.trains[train_id]

        if not hasattr(dashboard, 'layout'):
            return html.Div([
                html.H1("Error: Dashboard layout not found", style={'color': 'red'}),
                html.P(f"Train {train_id} dashboard not properly initialized.")
            ])

        # Add back button at top
        back_button = html.Div([
            html.A("← Back to Train Selection", href='/', style={
                'color': '#3498db',
                'textDecoration': 'none',
                'fontSize': '14px',
                'display': 'inline-block',
                'padding': '10px 20px',
                'backgroundColor': '#ecf0f1',
                'borderRadius': '6px'
            })
        ], style={'padding': '10px 20px'})

        # Train identifier badge
        train_badge = html.Div([
            html.Span(f"🚂 {train_config.name}", style={
                'backgroundColor': '#3498db',
                'color': 'white',
                'padding': '8px 16px',
                'borderRadius': '20px',
                'fontSize': '14px',
                'fontWeight': 'bold',
                'display': 'inline-block'
            })
        ], style={'padding': '0 20px 10px'})

        # Get dashboard layout from instance variable (not app.layout)
        # Each dashboard stores its layout separately in multi-train mode
        dashboard_content = dashboard.layout

        return html.Div([back_button, train_badge, dashboard_content])

    def _create_not_found_page(self, train_id):
        """Create page for non-existent train"""
        return html.Div([
            html.H1("🚫 Train Not Found", style={'textAlign': 'center', 'color': '#e74c3c'}),
            html.P(f"Train '{train_id}' does not exist or is disabled.", style={
                'textAlign': 'center',
                'fontSize': '18px',
                'color': '#7f8c8d'
            }),
            html.Div([
                html.A("← Back to Train Selection", href='/', style={
                    'color': '#3498db',
                    'textDecoration': 'none',
                    'fontSize': '16px'
                })
            ], style={'textAlign': 'center', 'marginTop': '20px'})
        ], style={
            'padding': '100px 20px',
            'backgroundColor': '#ecf0f1',
            'minHeight': '100vh'
        })

    def _create_404_page(self):
        """Create 404 error page"""
        return html.Div([
            html.H1("404", style={'textAlign': 'center', 'color': '#e74c3c', 'fontSize': '72px'}),
            html.P("Page not found", style={
                'textAlign': 'center',
                'fontSize': '24px',
                'color': '#7f8c8d'
            }),
            html.Div([
                html.A("← Back to Home", href='/', style={
                    'color': '#3498db',
                    'textDecoration': 'none',
                    'fontSize': '16px'
                })
            ], style={'textAlign': 'center', 'marginTop': '20px'})
        ], style={
            'padding': '100px 20px',
            'backgroundColor': '#ecf0f1',
            'minHeight': '100vh'
        })

    def _create_admin_page(self):
        """Create admin configuration page"""
        trains = self.config_manager.trains

        # Header
        header = html.Div([
            html.H1("⚙️ Admin Panel", style={'color': '#2c3e50'}),
            html.A("← Back to Home", href='/', style={
                'color': '#3498db',
                'textDecoration': 'none'
            })
        ], style={'padding': '20px', 'borderBottom': '2px solid #ecf0f1'})

        # Train list
        train_rows = []
        for train_id, train_config in trains.items():
            status_badge = html.Span(
                "✓ Enabled" if train_config.enabled else "✗ Disabled",
                style={
                    'backgroundColor': '#2ecc71' if train_config.enabled else '#e74c3c',
                    'color': 'white',
                    'padding': '4px 12px',
                    'borderRadius': '12px',
                    'fontSize': '12px'
                }
            )

            row = html.Tr([
                html.Td(train_config.name, style={'padding': '12px'}),
                html.Td(train_config.id, style={'padding': '12px', 'color': '#7f8c8d'}),
                html.Td(str(train_config.udp_port), style={'padding': '12px'}),
                html.Td(train_config.mqtt_prefix, style={'padding': '12px', 'fontFamily': 'monospace'}),
                html.Td(status_badge, style={'padding': '12px'}),
                html.Td([
                    html.A("View", href=f'/train/{train_config.id}', style={
                        'color': '#3498db',
                        'textDecoration': 'none',
                        'marginRight': '10px'
                    })
                ], style={'padding': '12px'})
            ])
            train_rows.append(row)

        train_table = html.Table([
            html.Thead(html.Tr([
                html.Th("Name", style={'padding': '12px', 'textAlign': 'left', 'borderBottom': '2px solid #ecf0f1'}),
                html.Th("ID", style={'padding': '12px', 'textAlign': 'left', 'borderBottom': '2px solid #ecf0f1'}),
                html.Th("UDP Port", style={'padding': '12px', 'textAlign': 'left', 'borderBottom': '2px solid #ecf0f1'}),
                html.Th("MQTT Prefix", style={'padding': '12px', 'textAlign': 'left', 'borderBottom': '2px solid #ecf0f1'}),
                html.Th("Status", style={'padding': '12px', 'textAlign': 'left', 'borderBottom': '2px solid #ecf0f1'}),
                html.Th("Actions", style={'padding': '12px', 'textAlign': 'left', 'borderBottom': '2px solid #ecf0f1'})
            ])),
            html.Tbody(train_rows)
        ], style={
            'width': '100%',
            'backgroundColor': 'white',
            'borderRadius': '8px',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
        })

        # Configuration info
        config_info = html.Div([
            html.H3("Configuration", style={'color': '#2c3e50', 'marginTop': '30px'}),
            html.P(f"Config File: trains_config.json"),
            html.P(f"Dashboard Host: {self.config_manager.dashboard_host}:{self.config_manager.dashboard_port}"),
            html.P(f"Total Trains: {len(trains)} ({len(self.config_manager.get_enabled_trains())} enabled)")
        ], style={
            'padding': '20px',
            'backgroundColor': 'white',
            'borderRadius': '8px',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
            'marginTop': '20px'
        })

        return html.Div([header, html.Div([train_table, config_info], style={'padding': '20px'})], style={
            'backgroundColor': '#ecf0f1',
            'minHeight': '100vh'
        })

    def start_udp_receivers(self):
        """Start all UDP receivers"""
        for train_id, receiver in self.udp_receivers.items():
            receiver.start()
            print(f"[UDP] Started receiver for {train_id} on port {receiver.port}")

    def run(self, host=None, port=None, debug=False):
        """Run the multi-train dashboard application"""
        # Start all UDP receivers
        self.start_udp_receivers()

        # Use config values if not overridden
        if host is None:
            host = self.config_manager.dashboard_host
        if port is None:
            port = self.config_manager.dashboard_port

        print(f"\n[MULTI-TRAIN] Starting dashboard on http://{host}:{port}")
        print(f"[MULTI-TRAIN] Landing page: http://{host}:{port}/")
        print(f"[MULTI-TRAIN] Admin panel: http://{host}:{port}/admin")
        print("[MULTI-TRAIN] Train dashboards:")
        for train_id in self.train_dashboards.keys():
            print(f"  - http://{host}:{port}/train/{train_id}")

        self.app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == '__main__':
    # Create and run multi-train app
    app = MultiTrainApp()
    app.run()
