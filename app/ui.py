import os
import re
import threading
import time
from collections import deque

from PySide6.QtCore import Qt, QRectF, QThread, Signal, QTimer, QSettings
from PySide6.QtGui import QColor, QBrush, QPen, QPainter, QFont, QIcon
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QWidget,
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QStackedWidget,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsSimpleTextItem,
    QLabel,
    QPushButton,
    QComboBox,
    QGroupBox,
    QSizePolicy,
    QPlainTextEdit, )

# Flexible import of helper functions for COM ports
# Ensures this module loads both as part of the 'app' package
# and as a standalone module.
try:
    from .com_ports import (
        refresh_ports_for,
        attach_auto_refresh,
        send_command_to_port_item,
        parse_device_from_item,
    )
except Exception:
    try:
        from app.com_ports import (
            refresh_ports_for,
            attach_auto_refresh,
            send_command_to_port_item,
            parse_device_from_item,
        )
    except Exception:
        from com_ports import (
            refresh_ports_for,
            attach_auto_refresh,
            send_command_to_port_item,
            parse_device_from_item,
        )


PIN_ROWS = [
    ("GND", "B+"),
    ("D1  P0.06", "B+"),
    ("D0  P0.08", "GND"),
    ("GND", "RESET"),
    ("GND", "VCC"),
    ("D2  P0.17", "P0.31 D21"),
    ("D3  P0.20", "P0.29 D20"),
    ("D4  P0.22", "P0.02 D19"),
    ("D5  P0.24", "P1.15 D18"),
    ("D6  P0.10", "P1.13 D15"),
    ("D7  P0.09", "P1.11 D14"),
    ("D8  P0.11", "P0.10 D16"),
    ("D9  P1.06", "P0.09 D10"),
]


class PinoutView(QGraphicsView):
    log_square_clicked = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(self.renderHints() | QPainter.RenderHint.Antialiasing)
        self.left_circles = []  # list of tuples (item, text)
        self.right_circles = [] # list of tuples (item, text)
        self.usb_square = None
        self._draw_pinout()

    def _draw_pin_row(self, y, left_text, right_text, rect_left, rect_width):
        scene = self.scene()

        # Geometry
        padding = 5
        circle_radius = 8
        label_gap = 8

        # Left column: circle then left-aligned label
        left_circle_x = rect_left + padding
        circle_item = QGraphicsEllipseItem(
            QRectF(left_circle_x - circle_radius, y - circle_radius, circle_radius * 2, circle_radius * 2)
        )
        # Non-tested: GND, B+ — dark gray; others white initially

        palette = QApplication.palette()
        btn_color = palette.color(QPalette.Button)
        alt_base_color = palette.color(QPalette.AlternateBase)

        if any(x in left_text for x in ("GND", "B+")):
            circle_item.setBrush(QBrush(QColor(20, 20, 20)))  # dark gray
        else:
            circle_item.setBrush(QBrush(btn_color))
        circle_item.setPen(QPen(alt_base_color))
        scene.addItem(circle_item)
        self.left_circles.append((circle_item, left_text))

        left_label_x = left_circle_x + circle_radius + label_gap
        left_label = QGraphicsSimpleTextItem(left_text)
        left_label.setBrush(QApplication.palette().color(QPalette.Text))
        bold_font = QFont()
        bold_font.setBold(True)
        left_label.setFont(bold_font)
        left_label_height = left_label.boundingRect().height()
        left_label.setPos(left_label_x, y - (left_label_height / 2))
        scene.addItem(left_label)

        # Right column: right-aligned label then circle
        right_circle_x = rect_left + rect_width - padding
        right_label = QGraphicsSimpleTextItem(right_text)
        right_label.setBrush(QApplication.palette().color(QPalette.Text))
        right_label.setFont(bold_font)
        # Position label so its right edge is label_gap away from the circle
        right_label_width = right_label.boundingRect().width()
        right_label_height = right_label.boundingRect().height()
        right_label_x = right_circle_x - circle_radius - label_gap - right_label_width
        right_label.setPos(right_label_x, y - (right_label_height / 2))
        scene.addItem(right_label)

        right_circle_item = QGraphicsEllipseItem(
            QRectF(right_circle_x - circle_radius, y - circle_radius, circle_radius * 2, circle_radius * 2)
        )
        if any(x in right_text for x in ("GND", "B+")):
            right_circle_item.setBrush(QBrush(QColor(20, 20, 20)))  # dark gray
        else:
            right_circle_item.setBrush(QBrush(btn_color))
        right_circle_item.setPen(QPen(alt_base_color))
        scene.addItem(right_circle_item)
        self.right_circles.append((right_circle_item, right_text))

    def _draw_pinout(self):
        scene = self.scene()
        scene.clear()

        # Base rectangle (light gray)
        rect_width = 290
        rect_height = 400
        rect_left = 5
        rect_top = 5
        base_rect = QGraphicsRectItem(rect_left, rect_top, rect_width, rect_height)
        palette = QApplication.palette()
        btn_color = palette.color(QPalette.Button)
        usb_color = palette.color(QPalette.AlternateBase)
        alt_base_color = palette.color(QPalette.AlternateBase)
        base_rect.setBrush(QBrush(btn_color))
        base_rect.setPen(QPen(alt_base_color))
        scene.addItem(base_rect)

        # Dark square at the top center, top edge aligned with rectangle's top, descending ~3 rows
        row_height = 31
        usb_square_size = row_height * 2.7
        usb_square_left = rect_left + (rect_width - usb_square_size) / 2
        self.usb_square = QGraphicsRectItem(usb_square_left, rect_top, usb_square_size, usb_square_size)
        self.usb_square.setBrush(QBrush(usb_color))  # dark gray
        self.usb_square.setPen(QPen(alt_base_color))  # dark gray
        scene.addItem(self.usb_square)

        # Draw pin rows inside the base rectangle
        start_y = rect_top  + 15
        for i, (left_text, right_text) in enumerate(PIN_ROWS):
            y = start_y + i * row_height
            self._draw_pin_row(y, left_text, right_text, rect_left + 10, rect_width - 20)

        # Fit the view
        scene.setSceneRect(0, 0, rect_left + rect_width + 5, rect_top + rect_height + 5)
        self.setFixedSize(305, 415)

    # Helpers for coloring circles
    @staticmethod
    def _canonical_pins_from_text(text: str):
        pins = []
        for m in re.finditer(r"P([01])[._](\d{2})", text):
            pins.append(f"P{m.group(1)}_{m.group(2)}")
        return pins

    def _is_test_circle(self, text: str) -> bool:
        return not any(x in text for x in ("GND", "B+"))

    def set_all_test_circles(self, color: QColor):
        for item, text in self.left_circles + self.right_circles:
            if self._is_test_circle(text):
                item.setBrush(QBrush(color))

    def set_circles_idle(self):
        palette = QApplication.palette()
        btn_color = palette.color(QPalette.ToolTipText)
        alt_base_color = palette.color(QPalette.AlternateBase)
        for item, text in self.left_circles + self.right_circles:
            if self._is_test_circle(text):
                item.setBrush(QBrush(alt_base_color))
                item.setPen(QPen(btn_color))

    def set_circles_testing(self):
        palette = QApplication.palette()
        highlight_color = palette.color(QPalette.Highlight)
        self.set_all_test_circles(highlight_color)

    def set_circles_success(self, problem_pins: set[str] | None = None):
        green = QColor(0, 200, 0)  # green
        red = QColor(255, 0, 0)  # red
        pset = problem_pins or set()
        for item, text in self.left_circles + self.right_circles:
            if not self._is_test_circle(text):
                continue
            pins = set(self._canonical_pins_from_text(text))
            item.setBrush(QBrush(red if pins & pset else green))  # red or green

    def set_circles_failure(self, problem_pins: set[str]):
        green = QColor(0, 200, 0)  # green
        red = QColor(255, 0, 0)  # red
        for item, text in self.left_circles + self.right_circles:
            if not self._is_test_circle(text):
                continue
            pins = set(self._canonical_pins_from_text(text))
            item.setBrush(QBrush(red if pins & problem_pins else green))  # red or green

    # Click handling for dark square to open logs page
    def mousePressEvent(self, event):
        try:
            if self.usb_square is not None:
                scene_pos = self.mapToScene(event.position().toPoint())
                item_pos = self.usb_square.mapFromScene(scene_pos)
                if self.usb_square.rect().contains(item_pos):
                    self.log_square_clicked.emit()
                    return
        except Exception:
            pass
        super().mousePressEvent(event)


class SerialReader(QThread):
    line_received = Signal(str, str)  # role, line

    def __init__(self, device: str, role: str, baud: int = 115200):
        super().__init__(None)
        self.device = device
        self.role = role
        self.baud = baud
        self._stop = False
        self._ser = None
        self._out_queue = deque()
        self._queue_lock = threading.Lock()

    def run(self):
        try:
            import serial  # type: ignore
        except Exception:
            return
        while not self._stop:
            # Ensure port is opened; if failed, retry until available
            if self._ser is None:
                try:
                    self._ser = serial.Serial(self.device, baudrate=self.baud, timeout=0.1)
                except Exception:
                    self._ser = None
                    QThread.msleep(500)
                    continue
            # Read line; if error (e.g., port disappeared), close and retry
            try:
                data = self._ser.readline()
            except Exception:
                try:
                    if self._ser:
                        self._ser.close()
                except Exception:
                    pass
                self._ser = None
                QThread.msleep(300)
                continue
            if not data:
                # Try sending queued commands even if there is no incoming data
                try:
                    while True:
                        cmd = None
                        with self._queue_lock:
                            if self._out_queue:
                                cmd = self._out_queue.popleft()
                            else:
                                break
                        if cmd is None:
                            break
                        if self._ser is None:
                            # port is gone — return the command to the queue and exit
                            with self._queue_lock:
                                self._out_queue.appendleft(cmd)
                            break
                        try:
                            if not cmd.endswith("\n"):
                                cmd = cmd + "\n"
                            self._ser.write(cmd.encode('utf-8'))
                            self._ser.flush()
                        except Exception:
                            # not successful — return the command and reopen the port later
                            with self._queue_lock:
                                self._out_queue.appendleft(cmd)
                            try:
                                if self._ser:
                                    self._ser.close()
                            except Exception:
                                pass
                            self._ser = None
                            break
                except Exception:
                    pass
                QThread.msleep(10)
                continue
            try:
                line = data.decode('utf-8', errors='ignore').strip()
            except Exception:
                continue
            if line:
                self.line_received.emit(self.role, line)
            # After reading a line, try sending queued commands
            try:
                while True:
                    cmd = None
                    with self._queue_lock:
                        if self._out_queue:
                            cmd = self._out_queue.popleft()
                        else:
                            break
                    if cmd is None:
                        break
                    if self._ser is None:
                        with self._queue_lock:
                            self._out_queue.appendleft(cmd)
                        break
                    try:
                        if not cmd.endswith("\n"):
                            cmd = cmd + "\n"
                        self._ser.write(cmd.encode('utf-8'))
                        self._ser.flush()
                    except Exception:
                        with self._queue_lock:
                            self._out_queue.appendleft(cmd)
                        try:
                            if self._ser:
                                self._ser.close()
                        except Exception:
                            pass
                        self._ser = None
                        break
            except Exception:
                pass
        # Cleanup
        try:
            if self._ser:
                self._ser.close()
        except Exception:
            pass

    def stop(self):
        self._stop = True

    def send_line(self, line: str) -> bool:
        """Queue a line to be sent via the open Serial port."""
        if self._stop:
            return False
        try:
            with self._queue_lock:
                self._out_queue.append(line)
            return True
        except Exception:
            return False

class FlashWorker(QThread):
    """Background worker that waits for DFU port, flashes firmware, then detects new Target COM.

    Signals:
      - progress(str): textual progress messages for logs
      - done(str dfu_port, str new_target): DFU port and new Target port (empty string if not found)
      - failed(str): error message
    """
    progress = Signal(str)
    done = Signal(str, str)
    failed = Signal(str)

    def __init__(self, hex_path: str, baudrate: int = 115200, timeout_s: float = 12.0, before_ports: set[str] | None = None):
        super().__init__(None)
        self.hex_path = hex_path
        self.baudrate = baudrate
        self.timeout_s = timeout_s
        self.before_ports = before_ports or set()
        self._stop = False

    def stop(self):
        self._stop = True

    def _list_ports_local(self) -> set[str]:
        try:
            from serial.tools import list_ports
            return {p.device for p in list_ports.comports()}
        except Exception:
            return set()

    def _wait_for_new_port_local(self, exclude: set[str], timeout_s: float) -> str | None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if self._stop:
                return None
            now = self._list_ports_local()
            candidates = [d for d in now if d not in exclude]
            if candidates:
                return candidates[0]
            time.sleep(0.2)
        return None

    def run(self):
        try:
            if self._stop:
                self.failed.emit("Cancelled")
                return
            # Step 1: wait for DFU port
            self.progress.emit("Flash: waiting for DFU port")
            dfu_port = self._wait_for_new_port_local(self.before_ports, self.timeout_s)
            if self._stop:
                self.failed.emit("Cancelled")
                return
            if dfu_port:
                self.progress.emit(f"Flash: DFU port detected: {dfu_port}")
            else:
                self.progress.emit("Flash: DFU port not detected, will rely on auto-detection")

            # Step 2: flash firmware (blocking in this thread)
            try:
                try:
                    from .flash_nrf import flash_firmware as do_flash
                except Exception:
                    try:
                        from app.flash_nrf import flash_firmware as do_flash
                    except Exception:
                        from flash_nrf import flash_firmware as do_flash
                if self._stop:
                    self.failed.emit("Cancelled")
                    return
                if dfu_port:
                    do_flash(self.hex_path, dfu_port, self.baudrate)
                else:
                    do_flash(self.hex_path)
            except Exception as e:
                raise Exception(f"Firmware upload failed: {e}")
            self.progress.emit("Flash: firmware upload finished")

            if self._stop:
                self.failed.emit("Cancelled")
                return
            # Step 3: detect new normal Target COM
            exclude = set(self.before_ports)
            if dfu_port:
                exclude.add(dfu_port)
            new_target = self._wait_for_new_port_local(exclude, self.timeout_s)
            self.done.emit(dfu_port or "", new_target or "")
        except Exception as e:
            self.failed.emit(str(e))


class StatusBox(QWidget):
    def __init__(self, label_text: str, color: QColor, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self.color_label = QLabel()
        self.color_label.setFixedSize(40, 40)
        self.set_color(color)

        self.text_label = QLabel(label_text)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.color_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.text_label)

    def set_color(self, color: QColor):
        self.color_label.setStyleSheet(
            f"background-color: rgb({color.red()},{color.green()},{color.blue()});"
            "border: 1px solid #555;"
        )


class MainWindow(QWidget):
    def __init__(self):
        super().__init__(None)
        self.setWindowTitle("C!N Tester GUI")
        import sys
        if getattr(sys, '_MEIPASS', False):
            icon_path = os.path.join(sys._MEIPASS, 'icon', 'icon.png')
        else:
            icon_path = os.path.join(os.path.dirname(__file__), 'icon', 'icon.png')
        self.setWindowIcon(QIcon(icon_path))

        # self.setWindowIcon(QIcon(QPixmap(icon_path)))
        # Left: Pinout
        self.pinout_view = PinoutView()
        # Do not stretch pinout vertically, only horizontally
        self.pinout_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Right: Controls
        controls = QWidget(None)
        # Fix controls panel vertical size to remove empty space below
        controls.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        controls.setFixedWidth(280)  # explicit width for Right: Controls
        # controls.setFixedHeight(400)
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 10, 0)
        controls_layout.setSpacing(12)

        # Test result group
        test_group = QGroupBox("Test result")
        # Bold group title
        group_font = QFont(); group_font.setBold(True)
        test_group.setFont(group_font)
        test_layout = QHBoxLayout(test_group)
        # Default state: white (idle). Yellow when testing, green on success, red on failure.

        palette = QApplication.palette()
        alt_base_color = palette.color(QPalette.AlternateBase)

        self.box_all_high = StatusBox("All High", alt_base_color)
        self.box_all_low = StatusBox("All Low", alt_base_color)
        self.box_sequence = StatusBox("Sequence", alt_base_color)
        test_layout.addWidget(self.box_all_high)
        test_layout.addWidget(self.box_all_low)
        test_layout.addWidget(self.box_sequence)

        # Ready group
        ready_group = QGroupBox("Ready")
        ready_group.setFont(group_font)
        ready_layout = QHBoxLayout(ready_group)
        self.box_master_ready = StatusBox("Master", QColor(255, 0, 0))  # red
        self.box_target_ready = StatusBox("Target", QColor(255, 0, 0))  # red
        ready_layout.addWidget(self.box_master_ready)
        ready_layout.addWidget(self.box_target_ready)

        # COM ports group
        ports_group = QGroupBox("COM ports")
        ports_group.setFont(group_font)
        ports_layout = QVBoxLayout(ports_group)
        self.target_combo = QComboBox(None)
        self.master_combo = QComboBox(None)
        self.target_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.master_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        ports_layout.addWidget(QLabel("Target:"))
        ports_layout.addWidget(self.target_combo)
        ports_layout.addWidget(QLabel("Master:"))
        ports_layout.addWidget(self.master_combo)

        # Buttons group
        buttons_group = QWidget(None)
        buttons_layout = QHBoxLayout(buttons_group)
        self.btn_flash = QPushButton("Flash")
        self.btn_run = QPushButton("Run Test")
        self.btn_flash_run = QPushButton("Flash&&Run")

        font = QFont()
        font.setBold(True)

        self.btn_flash.setFont(font)
        self.btn_run.setFont(font)
        self.btn_flash_run.setFont(font)
        text_color = QApplication.palette().color(QPalette.ButtonText)
        self.btn_flash.setStyleSheet(f"color: {text_color.name()};")
        self.btn_run.setStyleSheet(f"color: {text_color.name()};")
        self.btn_flash_run.setStyleSheet(f"color: {text_color.name()};")
        # Initially all buttons are white
        try:
            palette = QApplication.palette()
            base_color = palette.color(QPalette.Base)
            self.btn_flash.setStyleSheet(f"QPushButton {{ background-color: {base_color.name()}; }}")
            self.btn_run.setStyleSheet(f"QPushButton {{ background-color: {base_color.name()}; }}")
            self.btn_flash_run.setStyleSheet(f"QPushButton {{ background-color: {base_color.name()}; }}")
        except Exception:
            pass
        buttons_layout.addWidget(self.btn_flash)
        buttons_layout.addWidget(self.btn_run)
        buttons_layout.addWidget(self.btn_flash_run)

        # Assemble controls
        controls_layout.addWidget(test_group)
        controls_layout.addWidget(ready_group)
        controls_layout.addWidget(ports_group)
        controls_layout.addWidget(buttons_group)

        # Main layout switched to stacked with logs page
        self.stack = QStackedWidget(self)
        main_page = QWidget()
        main_layout_inner = QHBoxLayout(main_page)
        main_layout_inner.setContentsMargins(2, 2, 2, 2)
        main_layout_inner.setSpacing(2)
        main_layout_inner.addWidget(self.pinout_view, stretch=3)
        main_layout_inner.addWidget(controls, stretch=0)  # controls panel width is fixed

        # Logs page
        logs_page = QWidget(None)
        logs_layout = QVBoxLayout(logs_page)
        logs_layout.setContentsMargins(6, 6, 6, 6)
        logs_layout.setSpacing(6)

        # Top bar with close button on the right
        top_bar = QWidget(logs_page)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Target log label
        target_label = QLabel("Target")
        top_layout.addWidget(target_label)

        top_layout.addStretch(1)

        # Clear logs button (left of X)
        self.btn_clear = QPushButton("C", top_bar)
        self.btn_clear.setFixedWidth(24)
        self.btn_clear.setToolTip("Clear master and target logs")
        top_layout.addWidget(self.btn_clear)

        self.btn_back = QPushButton("X", top_bar)
        self.btn_back.setFixedWidth(24)
        self.btn_back.setToolTip("Return to the main page")
        top_layout.addWidget(self.btn_back)
        logs_layout.addWidget(top_bar)

        # Target log
        self.target_log = QPlainTextEdit()
        self.target_log.setReadOnly(True)
        self.target_log.setFixedHeight(180)
        self.target_log.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        logs_layout.addWidget(self.target_log, stretch=1)

        # Master log
        master_label = QLabel("Master")
        logs_layout.addWidget(master_label)
        self.master_log = QPlainTextEdit()
        self.master_log.setReadOnly(True)
        self.master_log.setFixedHeight(180)

        self.master_log.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        logs_layout.addWidget(self.master_log, stretch=1)

        # Assemble stack
        self.stack.addWidget(main_page)
        self.stack.addWidget(logs_page)
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self.stack)

        # Navigation wiring
        self.pinout_view.log_square_clicked.connect(self.show_logs_page)
        self.btn_back.clicked.connect(self.show_main_page)
        self.btn_clear.clicked.connect(self.clear_logs)
        # Fix window size to prevent resizing
        self.setFixedSize(self.sizeHint())

        # Populate COM ports initially
        refresh_ports_for(self.master_combo)
        refresh_ports_for(self.target_combo)

        # Load saved COM-port selections, if available
        try:
            self._load_saved_ports()
        except Exception:
            pass

        # Wire up buttons
        self.btn_flash.clicked.connect(self.on_flash)
        self.btn_run.clicked.connect(self.on_run_test)
        self.btn_flash_run.clicked.connect(self.on_flash_and_run)

        # Refresh ports when user opens a dropdown, and reset error style
        attach_auto_refresh(self.master_combo)
        attach_auto_refresh(self.target_combo)

        # Readers for COM ports
        self.master_reader: SerialReader | None = None
        self.target_reader: SerialReader | None = None
        self.problem_pins: set[str] = set()
        # Flags to suppress repeated 'STAGE — IDLE: OK' lines in logs
        self._master_idle_seen: bool = False
        self._target_idle_seen: bool = False
        self._await_target_ready: bool = False

        # Restart readers on selection change
        self.master_combo.currentTextChanged.connect(self.restart_readers)
        self.target_combo.currentTextChanged.connect(self.restart_readers)

        # Initial idle circles and start readers (deferred until event loop starts)
        self.pinout_view.set_circles_idle()
        QTimer.singleShot(0, self.restart_readers)

    def _set_combo_to_device(self, combo: QComboBox, device: str | None):
        if not device:
            return
        try:
            count = combo.count()
            for i in range(count):
                text = combo.itemText(i)
                dev = parse_device_from_item(text) or ""
                if dev == device:
                    combo.setCurrentIndex(i)
                    return
        except Exception:
            pass

    def _load_saved_ports(self):
        settings = QSettings("aroum", "C!N Tester GUI")
        master_dev = settings.value("master_port_device", type=str)
        target_dev = settings.value("target_port_device", type=str)
        self._set_combo_to_device(self.master_combo, master_dev)
        self._set_combo_to_device(self.target_combo, target_dev)

    def _save_ports(self):
        settings = QSettings("aroum", "C!N Tester GUI")
        try:
            m_dev = parse_device_from_item(self.master_combo.currentText()) or ""
            t_dev = parse_device_from_item(self.target_combo.currentText()) or ""
            settings.setValue("master_port_device", m_dev)
            settings.setValue("target_port_device", t_dev)
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            self._save_ports()
        except Exception:
            pass
        # We search for all attributes ending with '_reader' or '_flash_worker'
        worker_suffixes = ("_reader", "_flash_worker")
        worker_attrs = [attr for attr in dir(self) if attr.endswith(worker_suffixes)]

        active_threads = []
        for attr in worker_attrs:
            worker = getattr(self, attr)
            # Check if the object is a descendant of QThread and if it is running.
            if isinstance(worker, QThread) and worker.isRunning():
                active_threads.append(worker)

        if active_threads:
            print("Active threads detected. Initiating safe shutdown....")

            for worker in active_threads:
                # We try to get the role name, otherwise we use the attribute name
                role_name = getattr(worker, 'role', attr)
                worker.stop()  # Setting a stop flag

            # We are waiting for all streams to complete
            for worker in active_threads:
                if worker.isRunning():
                    role_name = getattr(worker, 'role', attr)
                    if not worker.wait(3000):  # Wait up to 3 seconds for the thread to finish
                        print(f"Thread {role_name} did not terminate, force termination...")
                        worker.terminate()  # The last resort

        # After all threads have completed (or are forced to stop), allow the window to close.
        event.accept()
        super().closeEvent(event)

    def show_logs_page(self):
        self.stack.setCurrentIndex(1)

    def show_main_page(self):
        self.stack.setCurrentIndex(0)

    def clear_logs(self):
        try:
            self.master_log.clear()
            self.target_log.clear()
        except Exception:
            pass

    def _list_ports(self) -> set[str]:
        """Return a set of currently available COM devices, e.g. {"COM3", "COM7"}."""
        try:
            from serial.tools import list_ports
            return {p.device for p in list_ports.comports()}
        except Exception:
            return set()

    def _wait_for_new_port(self, exclude: set[str], timeout_s: float = 12.0) -> str | None:
        """Wait until a new COM port appears that is not in `exclude` within `timeout_s` seconds.

        Returns the port name or None if not found in time.
        """
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            now = self._list_ports()
            candidates = [d for d in now if d not in exclude]
            if candidates:
                return candidates[0]
            time.sleep(0.2)
        return None

    # Helper state setters for test result colors
    def set_idle_state(self):
        palette = QApplication.palette()
        base_color = palette.color(QPalette.Base)
        # white = QColor(255, 255, 255)
        self.box_all_high.set_color(base_color)
        self.box_all_low.set_color(base_color)
        self.box_sequence.set_color(base_color)
        self.pinout_view.set_circles_idle()

    def set_testing_state(self):
        # yellow = QColor(255, 255, 0)
        palette = QApplication.palette()
        bright_color = palette.color(QPalette.BrightText)

        self.box_all_high.set_color(bright_color)
        self.box_all_low.set_color(bright_color)
        self.box_sequence.set_color(bright_color)
        self.pinout_view.set_circles_testing()

    def set_success_state(self):
        green = QColor(0, 200, 0)
        self.box_all_high.set_color(green)
        self.box_all_low.set_color(green)
        self.box_sequence.set_color(green)
        self.pinout_view.set_circles_success(self.problem_pins)

    def set_failure_state(self):
        red = QColor(255, 0, 0)
        self.box_all_high.set_color(red)
        self.box_all_low.set_color(red)
        self.box_sequence.set_color(red)
        self.pinout_view.set_circles_failure(self.problem_pins)

    # --- Button styling helpers ---
    def _set_btn_state(self, btn: QPushButton, state: str):
        # Get the default button text color from the application palette
        pal = QApplication.palette()
        default_text_hex = pal.color(QPalette.ButtonText).name()

        # Initialize color variables
        bg_color = None
        text_color = default_text_hex  # Default text color for non-busy states

        if state == "idle":
            # Clear the style sheet to revert to default appearance
            btn.setStyleSheet("")
            return

        if state == "busy":
            bg_color = "rgb(255,255,0)"
            # Set text color to black for better contrast on yellow background
            text_color = "#000000"
        elif state == "success":
            bg_color = "rgb(0,200,0)"
            # Use default text color
        elif state == "error":
            bg_color = "rgb(255,0,0)"
            # Use default text color

        # Apply the determined style sheet using f-string
        if bg_color:
            btn.setStyleSheet(f"QPushButton {{ background-color: {bg_color}; color: {text_color}; }}")

    def on_flash(self):
        """Start flashing Target asynchronously: enter DFU via Master, flash firmware, update UI when done."""
        try:
            # UI state: mark Flash busy (yellow), others default; disable Flash buttons during operation
            try:
                self._last_action = "flash"
                self._await_target_ready = False
                self._set_btn_state(self.btn_flash, "busy")
                self._set_btn_state(self.btn_run, "idle")
                self._set_btn_state(self.btn_flash_run, "idle")
                self.btn_flash.setEnabled(False)
                self.btn_flash_run.setEnabled(False)
            except Exception:
                pass

            # Snapshot ports and enter DFU via Master
            before = self._list_ports()
            self._log_info("Flash: sending FLASH to Master (DFU enter)")
            self._send_master_flash()

            # Resolve firmware path
            try:
                import os
                hex_path = os.path.join(os.path.dirname(__file__), 'mcu_firmware', 'firmware_target.hex')
            except Exception:
                hex_path = 'app/mcu_firmware/firmware_target.hex'

            # Start background worker
            self._flash_worker = FlashWorker(hex_path, 115200, 12.0, before)
            self._flash_worker.progress.connect(self._log_info)
            self._flash_worker.done.connect(self._on_flash_worker_done)
            self._flash_worker.failed.connect(self._on_flash_worker_failed)
            self._flash_worker.start()
        except Exception as e:
            try:
                self._log_info(f"Flash: error — {e}")
            except Exception:
                pass

    def on_run_test(self):
        self.problem_pins.clear()
        self.set_testing_state()
        # Clear logs when starting a new test from UI
        self.clear_logs()
        # Button colors per spec: Run is yellow during test

        try:
            # Preserve flash_run context if active; otherwise mark standalone run
            if getattr(self, "_last_action", "") != "flash_run":
                self._last_action = "run"
            self._set_btn_state(self.btn_run, "busy")
            if getattr(self, "_last_action", "") == "flash_run":
                # In combined flow keep Flash&&Run yellow; leave Flash as is (reflecting flash result)
                self._set_btn_state(self.btn_flash_run, "busy")
            else:
                # Standalone run: other buttons are default
                self._set_btn_state(self.btn_flash, "idle")
                self._set_btn_state(self.btn_flash_run, "idle")
        except Exception:
            pass
        # Send START command to the selected Master port
        ok = False
        try:
            if self.master_reader:
                ok = self.master_reader.send_line("START")
        except Exception:
            ok = False
        if not ok:
            ok = send_command_to_port_item(self.master_combo.currentText(), "START\n")
            if not ok:
                self.mark_combo_error(self.master_combo)

    def on_flash_and_run(self):
        """Flash Target asynchronously, refresh Target COM, then auto-start the test when ready."""
        try:
            # UI state per spec: Flash&Run yellow while the whole process; flash reflects stage color
            try:
                self._last_action = "flash_run"
                self._set_btn_state(self.btn_flash_run, "busy")
                self._set_btn_state(self.btn_flash, "busy")  # flashing stage starts
                self._set_btn_state(self.btn_run, "idle")
                self.btn_flash.setEnabled(False)
                self.btn_flash_run.setEnabled(False)
            except Exception:
                pass

            before = self._list_ports()
            self._log_info("Flash&Run: sending FLASH to Master (DFU enter)")
            self._send_master_flash()

            # Resolve firmware path
            try:
                import os
                hex_path = os.path.join(os.path.dirname(__file__), 'mcu_firmware', 'firmware_target.hex')
            except Exception:
                hex_path = 'app/mcu_firmware/firmware_target.hex'

            # Start background worker
            self._flash_worker = FlashWorker(hex_path, 115200, 12.0, before)
            self._flash_worker.progress.connect(self._log_info)
            self._flash_worker.done.connect(self._on_flash_worker_done)
            self._flash_worker.failed.connect(self._on_flash_worker_failed)
            self._flash_worker.start()
        except Exception as e:
            try:
                self._log_info(f"Flash&Run: error — {e}")
            except Exception:
                pass

    def _send_master_flash(self) -> bool:
        ok = False
        try:
            if self.master_reader:
                ok = self.master_reader.send_line("FLASH")
        except Exception:
            ok = False
        if not ok:
            ok = send_command_to_port_item(self.master_combo.currentText(), "FLASH\n")
            if not ok:
                self.mark_combo_error(self.master_combo)
        return ok

    def _log_info(self, text: str):
        # Log to both panes for visibility
        try:
            self.master_log.appendPlainText(text)
            self.target_log.appendPlainText(text)
        except Exception:
            pass

    # --- COM readers and parsing ---
    def mark_combo_error(self, combo: QComboBox):
        try:
            combo.setStyleSheet("QComboBox { border: 2px solid red; }")
        except Exception:
            pass

    def restart_readers(self):
        # stop existing
        for role in ("master", "target"):
            reader = getattr(self, f"{role}_reader")
            if reader:
                try:
                    reader.line_received.disconnect(self.on_serial_line)
                except Exception:
                    pass
                reader.stop()
                reader.wait(500)
                setattr(self, f"{role}_reader", None)

        # start new
        self.start_reader("master", self.master_combo)
        self.start_reader("target", self.target_combo)

        # equal port check
        dev_m = parse_device_from_item(self.master_combo.currentText())
        dev_t = parse_device_from_item(self.target_combo.currentText())
        if dev_m and dev_t and not dev_m.startswith("<") and dev_m == dev_t:
            self.mark_combo_error(self.master_combo)
            self.mark_combo_error(self.target_combo)

    def start_reader(self, role: str, combo: QComboBox):
        dev = parse_device_from_item(combo.currentText())
        if not dev or dev.startswith("<"):
            return
        reader = SerialReader(dev, role)
        reader.line_received.connect(self.on_serial_line)
        reader.start()
        setattr(self, f"{role}_reader", reader)

    def _extract_pins_from_message(self, line: str) -> set[str]:
        pins = set()
        # capture P0_06, P0.06, P1_07(VCC)
        for m in re.finditer(r"P([01])[._](\d{2})", line):
            pins.add(f"P{m.group(1)}_{m.group(2)}")
        return pins

    def on_serial_line(self, role: str, line: str):
        # Validate message source
        if role == "master":
            if not line.startswith("Master"):
                self.mark_combo_error(self.master_combo)
                return
        elif role == "target":
            if not line.startswith("Target"):
                self.mark_combo_error(self.target_combo)
                return
            # Auto-start the test when target speaks after flashing
            if getattr(self, "_await_target_ready", False):
                try:
                    self._await_target_ready = False
                    self.on_run_test()
                except Exception:
                    pass
        else:
            return

        uline = line.upper()

        # READY indicator and logging with suppression of repeated 'STAGE — IDLE: OK'
        try:
            is_idle_ok = ("STAGE" in uline) and ("IDLE: OK" in uline)
            if role == "master":
                self.box_master_ready.set_color(QColor(0, 200, 0))  # green
                if is_idle_ok:
                    if not getattr(self, "_master_idle_seen", False):
                        self.master_log.appendPlainText(line)
                        self._master_idle_seen = True
                else:
                    self.master_log.appendPlainText(line)
                    self._master_idle_seen = False
            else:  # target
                self.box_target_ready.set_color(QColor(0, 200, 0))  # green
                if is_idle_ok:
                    if not getattr(self, "_target_idle_seen", False):
                        self.target_log.appendPlainText(line)
                        self._target_idle_seen = True
                else:
                    self.target_log.appendPlainText(line)
                    self._target_idle_seen = False
        except Exception:
            pass

        # Only the master controls test states
        if role != "master":
            return

        if "START" in uline:
            # Only react if test was initiated from UI (Run / Flash&&Run)
            if getattr(self, "_last_action", "") not in ("run", "flash_run"):
                return
            self.problem_pins.clear()
            self.set_testing_state()
            self.pinout_view.set_circles_testing()
            # Clear logs when the test actually begins
            self.clear_logs()
            return
        palette = QApplication.palette()
        base_color = palette.color(QPalette.Base)
        text_default_color = palette.color(QPalette.WindowText)
        text_highlight_color = palette.color(QPalette.WindowText)
        # stage updates
        if "ALL_HIGH" in uline:
            if "BEGIN" in uline:
                self.box_all_high.set_color(QColor(255, 255, 0))
            elif "OK" in uline:
                self.box_all_high.set_color(QColor(0, 200, 0))
            elif "ERROR" in uline:
                self.box_all_high.set_color(QColor(255, 0, 0))
                self.problem_pins |= self._extract_pins_from_message(line)
                # Buttons per spec on test error

                if getattr(self, "_last_action", "") == "run":
                    try:
                        self._set_btn_state(self.btn_run, "error")
                    except Exception:
                        pass
                elif getattr(self, "_last_action", "") == "flash_run":
                    try:
                        self._set_btn_state(self.btn_run, "error")
                        self._set_btn_state(self.btn_flash_run, "error")
                    except Exception:
                        pass
            return

        if "ALL_LOW" in uline:
            if "BEGIN" in uline:
                self.box_all_low.set_color(QColor(255, 255, 0))
            elif "OK" in uline:
                self.box_all_low.set_color(QColor(0, 200, 0))
            elif "ERROR" in uline:
                self.box_all_low.set_color(QColor(255, 0, 0))
                self.problem_pins |= self._extract_pins_from_message(line)
                # Buttons per spec on test error
                if getattr(self, "_last_action", "") == "run":
                    try:
                        self._set_btn_state(self.btn_run, "error")
                    except Exception:
                        pass
                elif getattr(self, "_last_action", "") == "flash_run":
                    try:
                        self._set_btn_state(self.btn_run, "error")
                        self._set_btn_state(self.btn_flash_run, "error")
                    except Exception:
                        pass
            return

        if "SEQUENCE" in uline:
            if "BEGIN" in uline:
                self.box_sequence.set_color(QColor(255, 255, 0))
            elif "ALL OK" in uline or ("OK" in uline and "ALL" in uline):
                self.box_sequence.set_color(QColor(0, 200, 0))
            elif "ERROR" in uline:
                self.box_sequence.set_color(QColor(255, 0, 0))
                self.problem_pins |= self._extract_pins_from_message(line)
                # Buttons per spec on test error
                if getattr(self, "_last_action", "") == "run":
                    try:
                        self._set_btn_state(self.btn_run, "error")
                    except Exception:
                        pass
                elif getattr(self, "_last_action", "") == "flash_run":
                    try:
                        self._set_btn_state(self.btn_run, "error")
                        self._set_btn_state(self.btn_flash_run, "error")
                    except Exception:
                        pass
            return

        if "SUCCESS" in uline:
            self.set_success_state()
            self.pinout_view.set_circles_success(self.problem_pins)
            try:
                # On test success, return all buttons to default per spec
                self._set_btn_state(self.btn_run, "idle")
                self._set_btn_state(self.btn_flash, "idle")
                self._set_btn_state(self.btn_flash_run, "idle")
            except Exception:
                pass
            try:
                self._last_action = None
            except Exception:
                pass
            return

        if "FAIL" in uline or "ERROR" in uline:
            self.set_failure_state()
            self.pinout_view.set_circles_failure(self.problem_pins)
            # Buttons per spec on failure
            try:
                if getattr(self, "_last_action", None) == "run":
                    self._set_btn_state(self.btn_run, "error")
                elif getattr(self, "_last_action", None) == "flash_run":
                    self._set_btn_state(self.btn_run, "error")
                    self._set_btn_state(self.btn_flash_run, "error")
            except Exception:
                pass

    def _on_flash_worker_done(self, dfu_port: str, new_target: str):
        """Handle completion of FlashWorker.

        Updates button color, optionally refreshes Target COM and starts the test for Flash&&Run.
        """
        try:
            # Re-enable buttons
            self.btn_flash.setEnabled(True)
            self.btn_flash_run.setEnabled(True)
        except Exception:
            pass

        if getattr(self, "_last_action", "") == "flash_run":
            # Flash&&Run: mark flash success (btn_flash green) and keep Flash&&Run yellow until test completes
            try:
                self._set_btn_state(self.btn_flash, "success")  # green
                self._set_btn_state(self.btn_flash_run, "busy")  # yellow
            except Exception:
                pass
            if new_target:
                self._log_info(f"Flash&Run: new Target COM detected: {new_target}")
                refresh_ports_for(self.target_combo)
                self._set_combo_to_device(self.target_combo, new_target)
                try:
                    self._save_ports()
                except Exception:
                    pass
                self.restart_readers()
            else:
                self._log_info("Flash&Run: new Target COM not detected, keeping previous selection")
            # Await Target readiness message to start tests (no timer fallback)
            self._await_target_ready = True
        else:
            # Plain Flash: set button green
            try:
                self._set_btn_state(self.btn_flash, "success")  # green
            except Exception:
                pass
            # Update Target COM selection if detected
            if new_target:
                self._log_info(f"Flash: new Target COM detected: {new_target}")
                refresh_ports_for(self.target_combo)
                self._set_combo_to_device(self.target_combo, new_target)
                try:
                    self._save_ports()
                except Exception:
                    pass
                self.restart_readers()

        # Clear worker reference
        self._flash_worker = None

    # Removed: Flash&&Run starts tests on Target readiness message, not by timer

    def _on_flash_worker_failed(self, message: str):
        """Handle FlashWorker failure by logging and updating button color."""
        try:
            self.btn_flash.setEnabled(True)
            self.btn_flash_run.setEnabled(True)
        except Exception:
            pass
        self._log_info(f"Flash: error — {message}")
        if getattr(self, "_last_action", "") == "flash_run":
            try:
                self._set_btn_state(self.btn_flash_run, "error")  # red
                self._set_btn_state(self.btn_flash, "error")  # red
            except Exception:
                pass
        else:
            try:
                self._set_btn_state(self.btn_flash, "error")  # red
            except Exception:
                pass
        # Clear worker reference
        self._flash_worker = None