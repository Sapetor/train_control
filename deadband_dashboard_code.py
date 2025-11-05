# =============================================================================
# Deadband Dashboard Integration Code
# This file contains all the code needed to integrate deadband calibration
# into train_control_platform.py
# =============================================================================

# ==========================
# 1. TRANSLATION KEYS TO ADD
# ==========================
# Add these after the step response translations (around line 1048)

SPANISH_TRANSLATIONS = {
    # Deadband Calibration
    'deadband_tab': '🔧 Calibración Deadband',
    'deadband_title': 'Calibración de Zona Muerta',
    'deadband_config': 'Configuración de Calibración',
    'start_calibration': 'Iniciar Calibración',
    'stop_calibration': 'Detener Calibración',
    'motion_threshold': 'Umbral de Movimiento (cm)',
    'deadband_direction': 'Dirección',
    'calibration_result': 'Resultado de Calibración',
    'apply_to_pid': 'Aplicar a PID',
    'deadband_value': 'Valor Deadband',
    'calibration_in_progress': '🔄 Calibración en progreso...',
    'calibration_complete': '✓ Calibración completa',
    'deadband_pwm_graph': 'PWM vs Tiempo',
    'deadband_distance_graph': 'Distancia vs Tiempo',
    'deadband_curve_graph': 'Curva de Calibración (PWM vs Distancia)',
    'pwm_value': 'PWM',
    'initial_distance': 'Distancia Inicial',
    'motion_detected': 'Movimiento Detectado',
    'calibrating': 'Calibrando...',
    'deadband_applied': '✓ Deadband aplicado al modo PID',
}

ENGLISH_TRANSLATIONS = {
    # Deadband Calibration
    'deadband_tab': '🔧 Deadband Calibration',
    'deadband_title': 'Deadband Calibration',
    'deadband_config': 'Calibration Configuration',
    'start_calibration': 'Start Calibration',
    'stop_calibration': 'Stop Calibration',
    'motion_threshold': 'Motion Threshold (cm)',
    'deadband_direction': 'Direction',
    'calibration_result': 'Calibration Result',
    'apply_to_pid': 'Apply to PID',
    'deadband_value': 'Deadband Value',
    'calibration_in_progress': '🔄 Calibration in progress...',
    'calibration_complete': '✓ Calibration complete',
    'deadband_pwm_graph': 'PWM vs Time',
    'deadband_distance_graph': 'Distance vs Time',
    'deadband_curve_graph': 'Calibration Curve (PWM vs Distance)',
    'pwm_value': 'PWM',
    'initial_distance': 'Initial Distance',
    'motion_detected': 'Motion Detected',
    'calibrating': 'Calibrating...',
    'deadband_applied': '✓ Deadband applied to PID mode',
}

# ==========================
# 2. ADD TAB TO TABS LIST
# ==========================
# In create_layout() method, modify the dcc.Tabs around line 1677:
#
# OLD:
#     dcc.Tabs(id='main-tabs', value='control-tab', children=[
#         dcc.Tab(label=self.t('network_tab'), value='network-tab'),
#         dcc.Tab(label=self.t('control_tab'), value='control-tab'),
#         dcc.Tab(label=self.t('step_response_tab'), value='step-response-tab'),
#         dcc.Tab(label=self.t('data_tab'), value='data-tab')
#     ]),
#
# NEW:
#     dcc.Tabs(id='main-tabs', value='control-tab', children=[
#         dcc.Tab(label=self.t('network_tab'), value='network-tab'),
#         dcc.Tab(label=self.t('control_tab'), value='control-tab'),
#         dcc.Tab(label=self.t('step_response_tab'), value='step-response-tab'),
#         dcc.Tab(label=self.t('deadband_tab'), value='deadband-tab'),
#         dcc.Tab(label=self.t('data_tab'), value='data-tab')
#     ]),

# ==========================
# 3. ADD TAB RENDERING CASE
# ==========================
# In render_tab_content callback (around line 2180), add:
#
#     elif active_tab == 'deadband-tab':
#         return self.create_deadband_tab()

# ==========================
# 4. CREATE_DEADBAND_TAB METHOD
# ==========================
# Add this method to TrainControlDashboard class (after create_step_response_tab, around line 2045):

def create_deadband_tab(self):
    """Create deadband calibration tab"""
    return html.Div([
        html.H3(self.t('deadband_title'), style={'color': self.colors['text'], 'marginBottom': '20px'}),

        html.Div([
            # Left column - Configuration Panel
            html.Div([
                html.Div([
                    html.H4(self.t('deadband_config'),
                           style={'color': self.colors['primary'], 'marginBottom': '15px', 'fontSize': '16px'}),

                    # Direction
                    html.Div([
                        html.Label(f"{self.t('deadband_direction')}:",
                                 style={'fontWeight': '500', 'fontSize': '13px', 'marginBottom': '8px',
                                       'display': 'block'}),
                        dcc.RadioItems(
                            id='deadband-direction-radio',
                            options=[
                                {'label': f"  {self.t('forward')}", 'value': 1},
                                {'label': f"  {self.t('reverse')}", 'value': 0}
                            ],
                            value=1,
                            inline=True,
                            style={'fontSize': '13px'},
                            labelStyle={'marginRight': '20px', 'cursor': 'pointer'}
                        )
                    ], style={'marginBottom': '15px', 'padding': '10px', 'backgroundColor': '#f8f9fa',
                             'borderRadius': '6px'}),

                    # Motion Threshold
                    html.Div([
                        html.Label(f"{self.t('motion_threshold')}:",
                                 style={'fontWeight': '500', 'fontSize': '13px', 'marginBottom': '8px',
                                       'display': 'block'}),
                        dcc.Input(id='deadband-threshold-input', type='number',
                                value=0.08, min=0.01, max=1.0, step=0.01,
                                style={'width': '80px', 'height': '28px', 'fontSize': '12px',
                                      'padding': '4px'})
                    ], style={'marginBottom': '15px', 'padding': '10px', 'backgroundColor': '#f8f9fa',
                             'borderRadius': '6px'}),

                    # Start/Stop Buttons
                    html.Div([
                        html.Button(self.t('start_calibration'), id='deadband-start-btn', n_clicks=0,
                                  style={'backgroundColor': '#28A745', 'color': 'white', 'padding': '10px 20px',
                                        'border': 'none', 'borderRadius': '6px', 'fontSize': '14px',
                                        'cursor': 'pointer', 'marginRight': '10px'}),
                        html.Button(self.t('stop_calibration'), id='deadband-stop-btn', n_clicks=0,
                                  style={'backgroundColor': '#DC3545', 'color': 'white', 'padding': '10px 20px',
                                        'border': 'none', 'borderRadius': '6px', 'fontSize': '14px',
                                        'cursor': 'pointer'})
                    ], style={'marginBottom': '20px'}),

                    # Status Display
                    html.Div(id='deadband-status',
                           style={'fontSize': '13px', 'padding': '12px', 'backgroundColor': '#f8f9fa',
                                 'borderRadius': '6px', 'marginBottom': '15px', 'minHeight': '60px'}),

                    # Result Display
                    html.Div([
                        html.H5(self.t('calibration_result'),
                               style={'fontSize': '14px', 'marginBottom': '10px', 'color': self.colors['text']}),
                        html.Div(id='deadband-result',
                               style={'fontSize': '32px', 'fontWeight': 'bold', 'color': '#28A745',
                                     'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#f8f9fa',
                                     'borderRadius': '6px', 'marginBottom': '15px'}),
                        html.Button(self.t('apply_to_pid'), id='deadband-apply-btn', n_clicks=0,
                                  disabled=True,
                                  style={'width': '100%', 'padding': '10px', 'backgroundColor': '#007BFF',
                                        'color': 'white', 'border': 'none', 'borderRadius': '6px',
                                        'fontSize': '14px', 'cursor': 'pointer'})
                    ])

                ], style={'background': 'white', 'padding': '15px', 'borderRadius': '8px',
                         'boxShadow': '0 1px 4px rgba(0,0,0,0.1)'})
            ], style={'width': '35%', 'paddingRight': '20px'}),

            # Right column - Graphs
            html.Div([
                # PWM vs Time
                html.Div([
                    html.H4(self.t('deadband_pwm_graph'),
                           style={'textAlign': 'center', 'color': self.colors['primary'],
                                 'marginBottom': '8px', 'fontSize': '14px'}),
                    dcc.Graph(id='deadband-pwm-graph',
                             figure=px.line(),
                             style={'height': '250px'})
                ], style={'background': 'white', 'padding': '12px', 'borderRadius': '8px',
                         'boxShadow': '0 1px 4px rgba(0,0,0,0.1)', 'marginBottom': '15px'}),

                # Distance vs Time
                html.Div([
                    html.H4(self.t('deadband_distance_graph'),
                           style={'textAlign': 'center', 'color': self.colors['primary'],
                                 'marginBottom': '8px', 'fontSize': '14px'}),
                    dcc.Graph(id='deadband-distance-graph',
                             figure=px.line(),
                             style={'height': '250px'})
                ], style={'background': 'white', 'padding': '12px', 'borderRadius': '8px',
                         'boxShadow': '0 1px 4px rgba(0,0,0,0.1)', 'marginBottom': '15px'}),

                # Calibration Curve
                html.Div([
                    html.H4(self.t('deadband_curve_graph'),
                           style={'textAlign': 'center', 'color': self.colors['primary'],
                                 'marginBottom': '8px', 'fontSize': '14px'}),
                    dcc.Graph(id='deadband-curve-graph',
                             figure=px.line(),
                             style={'height': '300px'})
                ], style={'background': 'white', 'padding': '12px', 'borderRadius': '8px',
                         'boxShadow': '0 1px 4px rgba(0,0,0,0.1)'})

            ], style={'width': '65%'})

        ], style={'display': 'flex', 'gap': '20px'})
    ])
