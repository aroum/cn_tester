import os
import shutil
import subprocess
import sys
import tempfile

import serial.tools.list_ports


def find_serial_port():
    """Find an available COM port and return its device string (e.g., 'COM5')."""
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        raise Exception("No COM ports found")
    return ports[0].device  # Return the first detected port


def _resolve_nrfutil_base_cmd():
    """Prefer native CLI if available; avoid `sys.executable -m` when frozen.

    In a Nuitka onefile build, calling the bundled interpreter with `-m adafruit_nrfutil`
    causes self-execution errors. We therefore prefer:
      1) `adafruit-nrfutil` or `nrfutil` found on PATH;
      2) Windows `py -m adafruit_nrfutil` launcher;
      3) A `python*` executable on PATH with `-m adafruit_nrfutil`;
      4) Only in non-frozen mode: current interpreter with `-m`.
    """
    # 1) Try CLI wrappers on PATH
    for name in ("adafruit-nrfutil", "nrfutil"):
        path = shutil.which(name)
        if path:
            return [path]

    # 2) On Windows, use Python launcher to avoid calling the bundled exe
    if os.name == "nt" and shutil.which("py"):
        return ["py", "-m", "adafruit_nrfutil"]

    # 3) Try common python executables on PATH
    for py in ("python", "python3", "python3.13", "python3.12", "python3.11", "python3.10"):
        if shutil.which(py):
            return [py, "-m", "adafruit_nrfutil"]

    # 4) Only when not frozen, use current interpreter
    if not getattr(sys, "_MEIPASS", False) and not getattr(sys, "frozen", False):
        return [sys.executable, "-m", "adafruit_nrfutil"]

    # 5) No viable launcher found
    raise RuntimeError(
        "Cannot locate 'adafruit-nrfutil' or Python launcher. Install with 'pip install adafruit-nrfutil' or ensure 'py'/'python' is in PATH."
    )

def flash_firmware(hex_file, port=None, baudrate=115200):

    if not os.path.exists(hex_file):
        raise Exception(f"Firmware file not found: {hex_file}")

    # Search for hex_file in the compiled application
    if getattr(sys, '_MEIPASS', False):
        hex_file = os.path.join(sys._MEIPASS, 'mcu_firmware', os.path.basename(hex_file))

    hex_file = os.path.abspath(hex_file) # Ensure absolute path

    base_cmd = _resolve_nrfutil_base_cmd()

    # If port not provided, try to auto-detect
    if port is None:
        port = find_serial_port()

    # Create dfu_file in a temporary directory
    dfu_file = os.path.join(tempfile.gettempdir(), os.path.splitext(os.path.basename(hex_file))[0] + ".zip")
    dfu_file = os.path.abspath(dfu_file) # Ensure absolute path
    try:
        if os.path.exists(dfu_file):
            os.remove(dfu_file)
    except Exception:
        pass

    print(f"Attempting to create DFU package: {dfu_file}")
    # Generate DFU zip (first attempt without sd-req)
    try:
        genpkg_cmd = base_cmd + [
            "dfu", "genpkg",
            "--dev-type", "0x0052",
            "--application", hex_file,
            dfu_file,
        ]
        print(f"Running DFU package generation command: {' '.join(genpkg_cmd)}")
        res_gen = subprocess.run(genpkg_cmd, capture_output=True, text=True)
        print(f"DFU package generation result (first attempt):\nReturn Code: {res_gen.returncode}\nStdout: {res_gen.stdout}\nStderr: {res_gen.stderr}")
        if res_gen.returncode != 0:
            # Some bootloader versions require specifying sd-req=0x00
            genpkg_cmd2 = base_cmd + [
                "dfu", "genpkg",
                "--dev-type", "0x0052",
                "--application", hex_file,
                "--sd-req", "0x00",
                dfu_file,
            ]
            print(f"Running DFU package generation command (second attempt): {' '.join(genpkg_cmd2)}")
            res_gen2 = subprocess.run(genpkg_cmd2, capture_output=True, text=True)
            print(f"DFU package generation result (second attempt):\nReturn Code: {res_gen2.returncode}\nStdout: {res_gen2.stdout}\nStderr: {res_gen2.stderr}")
            if res_gen2.returncode != 0:
                raise Exception(f"DFU package creation failed:\n{res_gen.stderr or res_gen.stdout}\n{res_gen2.stderr or res_gen2.stdout}")
    except Exception as e:
        raise Exception(f"Failed to create DFU package: {e}")

    # Flash DFU package over serial
    try:
        flash_cmd = base_cmd + [
            "dfu", "serial",
            "--package", dfu_file,
            "-p", str(port),
            "-b", str(baudrate),
            "--singlebank",
        ]
        res_flash = subprocess.run(flash_cmd, capture_output=True, text=True)
        if res_flash.returncode != 0:
            raise Exception(f"Firmware upload error: {res_flash.stderr or res_flash.stdout}")
    except Exception as e:
        raise Exception(f"Failed to upload firmware: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python flash_nrf.py <hex_file_path> [COM-port] [baudrate]")
        sys.exit(1)

    hex_file = sys.argv[1]
    port = sys.argv[2] if len(sys.argv) > 2 else None
    baudrate = int(sys.argv[3]) if len(sys.argv) > 3 else 115200

    flash_firmware(hex_file, port, baudrate)