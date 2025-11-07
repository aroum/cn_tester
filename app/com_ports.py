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