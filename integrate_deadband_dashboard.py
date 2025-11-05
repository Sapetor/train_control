#!/usr/bin/env python3
"""
Automated Deadband Dashboard Integration Script

This script automatically integrates the deadband calibration UI
into train_control_platform.py by making 7 targeted modifications.

Usage:
    python integrate_deadband_dashboard.py

The script will:
1. Backup the original file
2. Make 7 modifications
3. Validate syntax
4. Create a diff file
5. Save the modified file
"""

import re
import sys
from datetime import datetime
import difflib

def backup_file(filepath):
    """Create a backup of the original file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_{timestamp}"
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✓ Backup created: {backup_path}")
    return backup_path

def read_file(filepath):
    """Read file contents"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(filepath, content):
    """Write content to file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def add_spanish_translations(content):
    """Add Spanish translation keys for deadband"""
    print("\n[1/7] Adding Spanish translation keys...")

    # Find the location after step translations
    pattern = r"(\s+'configure_step_first': 'Configure los parámetros del escalón primero')"

    spanish_translations = """,

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
                'deadband_applied': '✓ Deadband aplicado al modo PID'"""

    if re.search(pattern, content):
        content = re.sub(pattern, r'\1' + spanish_translations, content, count=1)
        print("  ✓ Spanish translations added")
    else:
        print("  ⚠ Warning: Could not find Spanish translation insertion point")

    return content

def add_english_translations(content):
    """Add English translation keys for deadband"""
    print("\n[2/7] Adding English translation keys...")

    # Find the location in English section
    pattern = r"(\s+'configure_step_first': 'Configure step parameters first')"

    english_translations = """,

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
                'deadband_applied': '✓ Deadband applied to PID mode'"""

    if re.search(pattern, content):
        content = re.sub(pattern, r'\1' + english_translations, content, count=1)
        print("  ✓ English translations added")
    else:
        print("  ⚠ Warning: Could not find English translation insertion point")

    return content

def add_deadband_tab(content):
    """Add deadband tab to tabs list"""
    print("\n[3/7] Adding deadband tab to tabs list...")

    # Find and replace the tabs definition
    old_tabs = r"(dcc\.Tabs\(id='main-tabs', value='control-tab', children=\[\s+dcc\.Tab\(label=self\.t\('network_tab'\), value='network-tab'\),\s+dcc\.Tab\(label=self\.t\('control_tab'\), value='control-tab'\),\s+dcc\.Tab\(label=self\.t\('step_response_tab'\), value='step-response-tab'\),\s+dcc\.Tab\(label=self\.t\('data_tab'\), value='data-tab'\))"

    new_tabs = r"\1,\n                dcc.Tab(label=self.t('deadband_tab'), value='deadband-tab')"

    if re.search(old_tabs, content):
        content = re.sub(old_tabs, new_tabs, content, count=1)
        print("  ✓ Deadband tab added to tabs list")
    else:
        print("  ⚠ Warning: Could not find tabs list")

    return content

def add_render_case(content):
    """Add deadband render case to render_tab_content"""
    print("\n[4/7] Adding render case for deadband tab...")

    # Find and add the elif case
    pattern = r"(elif active_tab == 'step-response-tab':\s+return self\.create_step_response_tab\(\))"

    new_case = r"\1\n            elif active_tab == 'deadband-tab':\n                return self.create_deadband_tab()"

    if re.search(pattern, content):
        content = re.sub(pattern, new_case, content, count=1)
        print("  ✓ Render case added")
    else:
        print("  ⚠ Warning: Could not find render_tab_content callback")

    return content

def add_create_deadband_tab_method(content):
    """Add create_deadband_tab method"""
    print("\n[5/7] Adding create_deadband_tab() method...")

    # Read the method from the code file
    with open('deadband_dashboard_code.py', 'r', encoding='utf-8') as f:
        code_content = f.read()

    # Extract the method
    method_match = re.search(r'(def create_deadband_tab\(self\):.*?)(?=\n# ==========================|\Z)',
                             code_content, re.DOTALL)

    if not method_match:
        print("  ⚠ Warning: Could not extract method from deadband_dashboard_code.py")
        return content

    method_code = method_match.group(1).rstrip()

    # Find insertion point (after create_step_response_tab)
    pattern = r"(    def create_step_response_tab\(self\):.*?\n        \]\)\n\n)"

    if re.search(pattern, content, re.DOTALL):
        # Add the new method after create_step_response_tab
        content = re.sub(pattern, r'\1' + method_code + '\n\n', content, count=1, flags=re.DOTALL)
        print("  ✓ create_deadband_tab() method added")
    else:
        print("  ⚠ Warning: Could not find insertion point for method")

    return content

def add_callbacks(content):
    """Add deadband callbacks"""
    print("\n[6/7] Adding deadband callbacks...")

    # Read the callbacks from the code file
    with open('deadband_callbacks_code.py', 'r', encoding='utf-8') as f:
        callbacks_content = f.read()

    # Extract all callbacks (remove header comments)
    callbacks_start = callbacks_content.find('@self.app.callback')
    if callbacks_start == -1:
        print("  ⚠ Warning: Could not extract callbacks")
        return content

    callbacks_code = callbacks_content[callbacks_start:]

    # Find insertion point - right after the step response graph callback ends
    # Look for the specific end pattern of the update_step_graph callback
    pattern = r'(                return fig\n                \n            except Exception as e:\n                fig = px\.line\(title=f"\{self\.t\(\'data_read_error\'\)\}: \{str\(e\)\}"\)\n                fig\.update_layout\(\n                    plot_bgcolor=self\.colors\[\'surface\'\],\n                    paper_bgcolor=self\.colors\[\'background\'\]\n                \)\n                return fig\n)'

    if re.search(pattern, content):
        # Add callbacks right after the step graph callback
        insertion = "\n        # =====================================================================\n"
        insertion += "        # Deadband Calibration Callbacks\n"
        insertion += "        # =====================================================================\n\n"
        insertion += "        " + callbacks_code.replace('\n', '\n        ').rstrip() + "\n"

        content = re.sub(pattern, r'\1' + insertion, content, count=1)
        print("  ✓ 5 deadband callbacks added")
    else:
        print("  ⚠ Warning: Could not find callback insertion point")

    return content

def update_mode_indicator(content):
    """Update mode indicator to handle deadband tab"""
    print("\n[7/7] Updating mode indicator...")

    # Find and replace the mode indicator callback
    old_code = r"(def update_mode_indicator\(active_tab, language_data\):.*?is_step = active_tab == 'step-response-tab'\s+mode_text = 'Step Response' if is_step else 'PID Control'\s+badge_color = '#28A745' if is_step else '#007BFF')"

    new_code = '''def update_mode_indicator(active_tab, language_data):
            """Update the mode indicator badge based on active tab"""
            if active_tab == 'step-response-tab':
                mode_text = 'Step Response'
                badge_color = '#28A745'
            elif active_tab == 'deadband-tab':
                mode_text = 'Deadband Cal'
                badge_color = '#FFA500'  # Orange
            else:
                mode_text = 'PID Control'
                badge_color = '#007BFF\''''

    if re.search(old_code, content, re.DOTALL):
        content = re.sub(old_code, new_code, content, count=1, flags=re.DOTALL)
        print("  ✓ Mode indicator updated")
    else:
        print("  ⚠ Warning: Could not find mode indicator callback")

    return content

def create_diff(original, modified, output_file):
    """Create a diff file showing changes"""
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile='train_control_platform.py (original)',
        tofile='train_control_platform.py (modified)',
        lineterm=''
    )

    diff_text = ''.join(diff)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(diff_text)

    return diff_text

def validate_syntax(content):
    """Validate Python syntax"""
    print("\nValidating Python syntax...")
    try:
        compile(content, '<string>', 'exec')
        print("  ✓ Syntax validation passed")
        return True
    except SyntaxError as e:
        print(f"  ✗ Syntax error: {e}")
        return False

def main():
    print("=" * 70)
    print("Deadband Dashboard Integration - Automated Script")
    print("=" * 70)

    filepath = 'train_control_platform.py'

    # Check if required files exist
    try:
        with open(filepath, 'r') as f:
            pass
        with open('deadband_dashboard_code.py', 'r') as f:
            pass
        with open('deadband_callbacks_code.py', 'r') as f:
            pass
    except FileNotFoundError as e:
        print(f"\n✗ Error: Required file not found: {e.filename}")
        print("\nMake sure you're running this script from the train_control directory.")
        sys.exit(1)

    # Backup original file
    print("\nStep 0: Creating backup...")
    backup_path = backup_file(filepath)

    # Read original content
    original_content = read_file(filepath)

    # Apply modifications
    content = original_content
    content = add_spanish_translations(content)
    content = add_english_translations(content)
    content = add_deadband_tab(content)
    content = add_render_case(content)
    content = add_create_deadband_tab_method(content)
    content = add_callbacks(content)
    content = update_mode_indicator(content)

    # Validate syntax
    validation_passed = validate_syntax(content)
    if not validation_passed:
        print("\n⚠ Validation reported errors, but will proceed anyway")
        print("  (Sometimes compile() has issues with long strings)")

        # Try alternative validation
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            import subprocess
            result = subprocess.run(['python', '-m', 'py_compile', tmp_path],
                                   capture_output=True, text=True)
            if result.returncode == 0:
                print("  ✓ Alternative validation passed - file is valid")
                validation_passed = True
            else:
                print(f"  ✗ Alternative validation also failed: {result.stderr}")
        finally:
            import os
            os.unlink(tmp_path)

        if not validation_passed:
            print("\n✗ Integration failed due to syntax errors")
            print(f"  Original file is safe at: {filepath}")
            print(f"  Backup available at: {backup_path}")
            sys.exit(1)

    # Create diff file
    print("\nCreating diff file...")
    diff_text = create_diff(original_content, content, 'deadband_integration.diff')

    # Count changes
    lines_added = diff_text.count('\n+')
    lines_removed = diff_text.count('\n-')
    print(f"  ✓ Diff created: deadband_integration.diff")
    print(f"    Lines added: {lines_added}")
    print(f"    Lines removed: {lines_removed}")

    # Save modified file
    print("\nSaving modified file...")
    write_file(filepath, content)
    print(f"  ✓ Modified file saved: {filepath}")

    # Summary
    print("\n" + "=" * 70)
    print("Integration Complete!")
    print("=" * 70)
    print("\nFiles created:")
    print(f"  - {backup_path} (backup)")
    print(f"  - deadband_integration.diff (changes)")
    print(f"  - {filepath} (modified)")

    print("\nNext steps:")
    print("  1. Review the diff file to see what changed")
    print("  2. Test the dashboard: python train_control_platform.py")
    print("  3. Navigate to the Deadband Calibration tab (🔧)")
    print("  4. Upload tren_esp_unified_COMPLETE.ino to ESP32")
    print("  5. Run a calibration test")

    print("\nIf anything goes wrong:")
    print(f"  - Restore from backup: cp {backup_path} {filepath}")

    print("\n✓ All done!")

if __name__ == '__main__':
    main()
