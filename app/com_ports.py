import time
from PySide6.QtWidgets import QComboBox

try:
    from serial.tools import list_ports as serial_list_ports
except Exception:
    serial_list_ports = None


def get_ports_list():
    """Return a list of combo items like 'COM5 (desc)' for detected ports.
    Falls back to placeholders when pyserial is missing or no ports are found.
    """
    ports = []
    try:
        if serial_list_ports:
            ports_info = serial_list_ports.comports()
            ports = [
                f"{p.device} ({p.description})" if getattr(p, "description", None) else p.device
                for p in ports_info
            ]
        else:
            ports = ["<pyserial not installed>"]
    except Exception:
        ports = []
    if not ports:
        ports = ["<no ports detected>"]
    return ports



def refresh_ports_for(combo: QComboBox):
    """Refresh the given combo box with the current list of COM ports."""
    items = get_ports_list()
    combo.clear()
    combo.addItems(items)


def attach_auto_refresh(combo: QComboBox):
    """Attach auto-refresh behavior when the combo popup opens.
    Also clears any error highlight on user interaction.
    """
    def _show_popup():
        # Reset error highlight on user interaction
        try:
            combo.setStyleSheet("")
        except Exception:
            pass
        refresh_ports_for(combo)
        QComboBox.showPopup(combo)
    combo.showPopup = _show_popup


# --- Sending commands over serial ---
def _extract_device(selected_text: str) -> str | None:
    """Extract device name like 'COM5' from combo item 'COM5 (desc)'."""
    if not selected_text:
        return None
    # If item contains description in parentheses, strip it
    try:
        if " (" in selected_text:
            return selected_text.split(" (", 1)[0].strip()
        return selected_text.strip()
    except Exception:
        return None


def send_command_to_port_item(item_text: str, command: str, baud: int = 115200, timeout: float = 1.0) -> bool:
    """
    Open a serial port derived from a combo item text and send a line command.
    Returns True on success, False otherwise. Safe if pyserial is missing.
    """
    try:
        import serial  # type: ignore
    except Exception:
        return False

    dev = _extract_device(item_text)
    print(dev)
    if not dev or dev.startswith("<"):
        return False

    try:
        with serial.Serial(dev, baudrate=baud, timeout=timeout) as ser:
            data = command.encode("utf-8")
            ser.write(data)
            ser.flush()
        return True
    except Exception:
        return False


def parse_device_from_item(selected_text: str) -> str | None:
    """Public helper to get device like 'COM5' from combo item text."""
    return _extract_device(selected_text)


def discover_mcu_ports(baud: int = 115200, timeout: float = 0.5):
    """
    Scan all available COM ports and look for "Hello! I am Master!"
    or "Hello! I am Target!" messages.
    Returns a dict: {"master": port_path or None, "target": port_path or None}
    """
    results = {"master": None, "target": None}
    try:
        import serial
        from serial.tools import list_ports
    except Exception:
        return results

    ports_info = list_ports.comports()
    for p in ports_info:
        dev = p.device
        if results["master"] and results["target"]:
            break
        
        try:
            # We use a short timeout for discovery
            with serial.Serial(dev, baudrate=baud, timeout=timeout) as ser:
                # Read for a bit to see if we get the hello message
                # We might need to wait a bit or read multiple times
                start_time = time.time()
                while time.time() - start_time < 1.0: # give it 1 second per port max
                    if ser.in_waiting:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if "Hello! I am Master!" in line:
                            results["master"] = dev
                            break
                        if "Hello! I am Target!" in line:
                            results["target"] = dev
                            break
                    time.sleep(0.1)
        except Exception:
            continue
            
    return results