#!/usr/bin/env python3
"""
Script to systematically update component IDs in train_control_platform.py
to use self._make_id() for multi-train support.

This script handles:
1. Component IDs in layout methods (id='...' and id="...")
2. Callback Input/Output/State declarations
"""

import re
import sys

def update_component_ids(file_path):
    """Update all component IDs to use self._make_id()"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    changes_count = 0

    # List of all component IDs found in the file (extracted manually for accuracy)
    component_ids = [
        # Network tab
        'interface-dropdown', 'interface-status', 'esp32-ip-display',
        'udp-port-input', 'mqtt-port-input', 'apply-config-btn',
        'test-connection-btn', 'refresh-interfaces-btn', 'network-status',

        # Control tab (PID)
        'kp-input', 'kp-send-btn', 'kp-slider',
        'ki-input', 'ki-send-btn', 'ki-slider',
        'kd-input', 'kd-send-btn', 'kd-slider',
        'ref-input', 'ref-send-btn', 'reference-slider',
        'connection-status-indicator', 'data-status',
        'download-csv-btn-control', 'download-csv-btn',
        'start-experiment-btn', 'stop-experiment-btn',
        'pid-status-display', 'realtime-graph', 'relayoutData',
        'detailed-connection-status', 'csv-file-path',

        # Step response tab
        'step-amplitude-input', 'step-duration-input', 'step-direction-radio',
        'start-step-btn', 'stop-step-btn', 'step-status-display',
        'step-pwm-graph', 'step-distance-graph', 'step-combined-graph',
        'download-csv-btn-step', 'step-amplitude-status', 'step-duration-status',
        'step-direction-status', 'step-response-graph', 'step-esp32-status',
        'amplitude-input', 'amplitude-send-btn', 'amplitude-slider',
        'duration-input', 'duration-send-btn', 'duration-slider',
        'direction-radio', 'vbatt-slider',

        # Deadband tab
        'deadband-direction-radio', 'deadband-threshold-input',
        'start-deadband-btn', 'stop-deadband-btn', 'deadband-status-display',
        'deadband-result-display', 'apply-deadband-btn',
        'deadband-pwm-graph', 'deadband-distance-graph', 'deadband-calibration-graph',
        'download-csv-btn-deadband', 'deadband-direction-status', 'deadband-threshold-status',
        'deadband-start-btn', 'deadband-stop-btn', 'deadband-status',
        'deadband-result', 'deadband-curve-graph', 'deadband-apply-btn',

        # Data/Historical tab
        'historical-graph', 'historical-data-stats',

        # Main layout
        'main-tabs', 'tab-content', 'language-dropdown', 'language-store',
        'app-title', 'app-subtitle', 'mode-indicator', 'language-label',
        'top-experiment-controls', 'experiment-status-top',

        # Intervals and stores
        'mqtt-status-refresh', 'data-refresh', 'fast-data-check',
        'ws-message-store', 'zoom-store',
        'network-config-store', 'mqtt-params-store', 'experiment-mode-store',
        'fast-update-check', 'data-refresh-interval', 'page-load-trigger',
        'graph-update-interval',

        # Download components
        'download-csv-control', 'download-csv-step', 'download-csv-deadband',
        'download-csv-file', 'download-csv-file-control', 'download-csv-file-step',
        'download-csv-file-deadband',
    ]

    print(f"Found {len(component_ids)} unique component IDs to update")

    # Pattern 1: Update layout component IDs (id='component-id' or id="component-id")
    for component_id in component_ids:
        # Single quotes: id='component-id'
        pattern1 = f"id='{component_id}'"
        replacement1 = f"id=self._make_id('{component_id}')"

        count1 = content.count(pattern1)
        if count1 > 0:
            content = content.replace(pattern1, replacement1)
            changes_count += count1
            print(f"  Updated {count1} occurrence(s) of id='{component_id}'")

        # Double quotes: id="component-id"
        pattern2 = f'id="{component_id}"'
        replacement2 = f'id=self._make_id("{component_id}")'

        count2 = content.count(pattern2)
        if count2 > 0:
            content = content.replace(pattern2, replacement2)
            changes_count += count2
            print(f"  Updated {count2} occurrence(s) of id=\"{component_id}\"")

    # Pattern 2: Update callback declarations (Input, Output, State)
    # These have format: Input('component-id', 'property')
    for component_id in component_ids:
        # Input with single quotes
        for prefix in ['Input', 'Output', 'State']:
            pattern = f"{prefix}('{component_id}'"
            replacement = f"{prefix}(self._make_id('{component_id}')"

            count = content.count(pattern)
            if count > 0:
                content = content.replace(pattern, replacement)
                changes_count += count
                print(f"  Updated {count} occurrence(s) of {prefix}('{component_id}'")

            # Double quotes version
            pattern = f'{prefix}("{component_id}"'
            replacement = f'{prefix}(self._make_id("{component_id}")'

            count = content.count(pattern)
            if count > 0:
                content = content.replace(pattern, replacement)
                changes_count += count
                print(f"  Updated {count} occurrence(s) of {prefix}(\"{component_id}\"")

    if changes_count == 0:
        print("\nNo changes made - all component IDs may already be updated")
        return False

    # Write updated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\n✅ Successfully updated {changes_count} component ID references")
    print(f"   File: {file_path}")

    return True

if __name__ == '__main__':
    file_path = '/home/user/train_control/train_control_platform.py'

    print("=" * 70)
    print("Multi-Train Component ID Updater")
    print("=" * 70)
    print(f"\nProcessing: {file_path}\n")

    try:
        success = update_component_ids(file_path)

        if success:
            print("\n" + "=" * 70)
            print("✅ Update complete!")
            print("=" * 70)
            print("\nNext steps:")
            print("1. Review changes: git diff train_control_platform.py")
            print("2. Test single-train mode: python train_control_platform.py")
            print("3. Test multi-train mode: python multi_train_wrapper.py")
            print("4. Commit changes if tests pass")
        else:
            print("\n⚠️  No changes were needed")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
