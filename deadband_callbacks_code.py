# =============================================================================
# Deadband Calibration Callbacks
# Add these callbacks to the setup_callbacks() method in TrainControlDashboard
# =============================================================================

# ==========================
# CALLBACK 1: Start/Stop Calibration
# ==========================
# Add this after step response callbacks (around line 2700):

@self.app.callback(
    [Output('deadband-status', 'children'),
     Output('deadband-result', 'children'),
     Output('deadband-apply-btn', 'disabled')],
    [Input('deadband-start-btn', 'n_clicks'),
     Input('deadband-stop-btn', 'n_clicks'),
     Input('graph-update-interval', 'n_intervals')],
    [State('deadband-direction-radio', 'value'),
     State('deadband-threshold-input', 'value')],
    prevent_initial_call=True
)
def handle_deadband_calibration(start_clicks, stop_clicks, n_intervals,
                                direction, threshold):
    """Handle deadband calibration start/stop and status updates"""
    ctx = callback_context

    if not ctx.triggered:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Check network configuration
    if not self.network_manager.selected_ip:
        return (html.Div(self.t('configure_network_warning'),
                        style={'color': '#DC3545'}),
                "", True)

    # Start calibration
    if trigger_id == 'deadband-start-btn' and start_clicks > 0:
        try:
            # Switch to deadband data manager
            self.experiment_mode = 'deadband'
            self.udp_receiver.set_data_manager(self.deadband_data_manager)

            # Clear previous calibration data
            self.deadband_data_manager.clear_history()

            # Create new CSV file
            csv_path = self.deadband_data_manager.create_deadband_csv()
            print(f"Deadband calibration CSV: {csv_path}")

            # Send configuration via MQTT
            self.mqtt_sync.publish(MQTT_TOPICS['deadband_direction'], str(direction))
            time.sleep(0.05)
            self.mqtt_sync.publish(MQTT_TOPICS['deadband_threshold'], str(threshold))
            time.sleep(0.05)

            # Start calibration
            self.mqtt_sync.publish(MQTT_TOPICS['deadband_sync'], "True")

            return (html.Div(self.t('calibration_in_progress'),
                            style={'color': '#FFA500'}),
                    "", True)

        except Exception as e:
            return (html.Div(f"Error: {str(e)}", style={'color': '#DC3545'}),
                    "", True)

    # Stop calibration
    elif trigger_id == 'deadband-stop-btn' and stop_clicks > 0:
        try:
            self.mqtt_sync.publish(MQTT_TOPICS['deadband_sync'], "False")

            return (html.Div(self.t('calibration_complete'),
                            style={'color': '#28A745'}),
                    f"{self.deadband_data_manager.calibrated_deadband} PWM",
                    False if self.deadband_data_manager.calibrated_deadband > 0 else True)

        except Exception as e:
            return (html.Div(f"Error: {str(e)}", style={'color': '#DC3545'}),
                    "", True)

    # Status updates (check for calibration result)
    elif trigger_id == 'graph-update-interval':
        # Check if calibration has completed
        if self.deadband_data_manager.calibrated_deadband > 0:
            return (html.Div(self.t('calibration_complete'),
                            style={'color': '#28A745'}),
                    f"{self.deadband_data_manager.calibrated_deadband} PWM",
                    False)
        elif len(self.deadband_data_manager.deadband_history['pwm']) > 0:
            # Calibration in progress
            current_pwm = self.deadband_data_manager.deadband_history['pwm'][-1]
            return (html.Div(f"{self.t('calibrating')} PWM: {current_pwm}",
                            style={'color': '#FFA500'}),
                    "", True)

    raise PreventUpdate


# ==========================
# CALLBACK 2: Apply Deadband to PID
# ==========================

@self.app.callback(
    Output('deadband-status', 'children', allow_duplicate=True),
    Input('deadband-apply-btn', 'n_clicks'),
    State('deadband-result', 'children'),
    prevent_initial_call=True
)
def apply_deadband_to_pid(n_clicks, result_text):
    """Apply calibrated deadband value to PID mode"""
    if n_clicks > 0 and result_text:
        try:
            # Send apply command via MQTT
            self.mqtt_sync.publish(MQTT_TOPICS['deadband_apply'], "True")

            return html.Div(self.t('deadband_applied'),
                           style={'color': '#28A745', 'fontWeight': 'bold'})

        except Exception as e:
            return html.Div(f"Error applying deadband: {str(e)}",
                           style={'color': '#DC3545'})

    raise PreventUpdate


# ==========================
# CALLBACK 3: Update PWM vs Time Graph
# ==========================

@self.app.callback(
    Output('deadband-pwm-graph', 'figure'),
    Input('graph-update-interval', 'n_intervals')
)
def update_deadband_pwm_graph(n):
    """Update PWM vs Time graph"""
    try:
        data = self.deadband_data_manager.deadband_history

        if len(data['time']) == 0:
            # No data yet
            fig = px.line()
            fig.update_layout(
                title=self.t('deadband_pwm_graph'),
                xaxis_title=self.t('time') + ' (ms)',
                yaxis_title='PWM',
                template='plotly_white'
            )
            return fig

        fig = go.Figure()

        # PWM trace
        fig.add_trace(go.Scatter(
            x=data['time'],
            y=data['pwm'],
            mode='lines',
            name='PWM',
            line=dict(color='blue', width=2)
        ))

        # Mark motion detection point
        if 1 in data['motion_detected']:
            idx = data['motion_detected'].index(1)
            fig.add_trace(go.Scatter(
                x=[data['time'][idx]],
                y=[data['pwm'][idx]],
                mode='markers+text',
                name=self.t('motion_detected'),
                marker=dict(color='red', size=15, symbol='star'),
                text=[f"PWM={data['pwm'][idx]}"],
                textposition='top center'
            ))

        fig.update_layout(
            title=self.t('deadband_pwm_graph'),
            xaxis_title=self.t('time') + ' (ms)',
            yaxis_title='PWM',
            hovermode='x unified',
            template='plotly_white',
            showlegend=True
        )

        return fig

    except Exception as e:
        print(f"Error updating PWM graph: {e}")
        return px.line()


# ==========================
# CALLBACK 4: Update Distance vs Time Graph
# ==========================

@self.app.callback(
    Output('deadband-distance-graph', 'figure'),
    Input('graph-update-interval', 'n_intervals')
)
def update_deadband_distance_graph(n):
    """Update Distance vs Time graph"""
    try:
        data = self.deadband_data_manager.deadband_history

        if len(data['time']) == 0:
            fig = px.line()
            fig.update_layout(
                title=self.t('deadband_distance_graph'),
                xaxis_title=self.t('time') + ' (ms)',
                yaxis_title=self.t('distance_cm'),
                template='plotly_white'
            )
            return fig

        fig = go.Figure()

        # Distance trace
        fig.add_trace(go.Scatter(
            x=data['time'],
            y=data['distance'],
            mode='lines',
            name=self.t('distance_cm'),
            line=dict(color='green', width=2)
        ))

        # Initial distance reference line
        if len(data['initial_distance']) > 0:
            fig.add_trace(go.Scatter(
                x=data['time'],
                y=data['initial_distance'],
                mode='lines',
                name=self.t('initial_distance'),
                line=dict(color='gray', width=1, dash='dash')
            ))

            # Motion threshold bands
            threshold = 0.08  # Get from UI state if needed
            initial = data['initial_distance'][0]
            fig.add_hrect(
                y0=initial - threshold,
                y1=initial + threshold,
                fillcolor="yellow",
                opacity=0.2,
                line_width=0,
                annotation_text=self.t('motion_threshold')
            )

        # Mark motion detection point
        if 1 in data['motion_detected']:
            idx = data['motion_detected'].index(1)
            fig.add_trace(go.Scatter(
                x=[data['time'][idx]],
                y=[data['distance'][idx]],
                mode='markers',
                name=self.t('motion_detected'),
                marker=dict(color='red', size=12, symbol='star')
            ))

        fig.update_layout(
            title=self.t('deadband_distance_graph'),
            xaxis_title=self.t('time') + ' (ms)',
            yaxis_title=self.t('distance_cm'),
            hovermode='x unified',
            template='plotly_white',
            showlegend=True
        )

        return fig

    except Exception as e:
        print(f"Error updating distance graph: {e}")
        return px.line()


# ==========================
# CALLBACK 5: Update Calibration Curve (PWM vs Distance)
# ==========================

@self.app.callback(
    Output('deadband-curve-graph', 'figure'),
    Input('graph-update-interval', 'n_intervals')
)
def update_deadband_curve_graph(n):
    """Update PWM vs Distance calibration curve"""
    try:
        data = self.deadband_data_manager.deadband_history

        if len(data['pwm']) == 0:
            fig = px.line()
            fig.update_layout(
                title=self.t('deadband_curve_graph'),
                xaxis_title='PWM',
                yaxis_title=self.t('distance_cm'),
                template='plotly_white'
            )
            return fig

        fig = go.Figure()

        # Main calibration curve
        fig.add_trace(go.Scatter(
            x=data['pwm'],
            y=data['distance'],
            mode='lines+markers',
            name=self.t('calibration_result'),
            line=dict(color='purple', width=2),
            marker=dict(size=4)
        ))

        # Mark deadband point
        if 1 in data['motion_detected']:
            idx = data['motion_detected'].index(1)
            deadband_pwm = data['pwm'][idx]
            deadband_distance = data['distance'][idx]

            fig.add_trace(go.Scatter(
                x=[deadband_pwm],
                y=[deadband_distance],
                mode='markers+text',
                name=f'Deadband = {deadband_pwm}',
                marker=dict(color='red', size=15, symbol='star'),
                text=[f'{deadband_pwm}'],
                textposition='top center'
            ))

            # Vertical line at deadband
            fig.add_vline(
                x=deadband_pwm,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Deadband: {deadband_pwm} PWM",
                annotation_position="top"
            )

        fig.update_layout(
            title=self.t('deadband_curve_graph'),
            xaxis_title='PWM',
            yaxis_title=self.t('distance_cm'),
            hovermode='closest',
            template='plotly_white',
            showlegend=True
        )

        return fig

    except Exception as e:
        print(f"Error updating curve graph: {e}")
        return px.line()
