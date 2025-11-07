from PySide6.QtWidgets import QApplication, QWidget, QLabel, QGridLayout, QVBoxLayout
from PySide6.QtGui import QPalette
from PySide6.QtCore import Qt
import sys


class PaletteDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QPalette Colors Demo (System Theme)")

        self.main_layout = QVBoxLayout(self)
        self.grid_layout = QGridLayout()
        self.main_layout.addLayout(self.grid_layout)
        self.show_palette()

    def show_palette(self):
        # Clearing old widgets (if any)
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        palette = QApplication.palette()

        roles = [
            (QPalette.Window, "Window"),
            (QPalette.WindowText, "WindowText"),
            (QPalette.Base, "Base"),
            (QPalette.AlternateBase, "AlternateBase"),
            (QPalette.ToolTipBase, "ToolTipBase"),
            (QPalette.ToolTipText, "ToolTipText"),
            (QPalette.Text, "Text"),
            (QPalette.Button, "Button"),
            (QPalette.ButtonText, "ButtonText"),
            (QPalette.BrightText, "BrightText"),
            (QPalette.Highlight, "Highlight"),
            (QPalette.HighlightedText, "HighlightedText"),
            (QPalette.Disabled, QPalette.Text, "Disabled Text"),
            (QPalette.Disabled, QPalette.ButtonText, "Disabled ButtonText"),
            (QPalette.Disabled, QPalette.Highlight, "Disabled Highlight"),
        ]

        row = 0
        col = 0

        for role_data in roles:
            role_name = ""
            color = None

            if len(role_data) == 2:
                # Standard role for QPalette.Active
                role, role_name = role_data
                color = palette.color(QPalette.Active, role)
            elif len(role_data) == 3:
                # Role for a specific group (e.g., Disabled)
                group, role, role_name = role_data
                color = palette.color(group, role)

            if not color or not color.isValid():
                continue

            label = QLabel(role_name)
            label.setAlignment(Qt.AlignCenter)

            # Determine text color for contrast
            text_color = "white" if color.lightness() < 128 else "black"

            label.setStyleSheet(
                f"""
                QLabel {{
                    background-color: {color.name()}; 
                    color: {text_color}; 
                    padding: 8px; 
                    border: 1px solid gray;
                    border-radius: 4px; /* Let's round the corners a bit */
                }}
                """
            )
            label.setMinimumHeight(40)  # For better readability

            self.grid_layout.addWidget(label, row, col)

            col += 1
            if col > 2:
                col = 0
                row += 1


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PaletteDemo()
    window.resize(500, 400)
    window.show()
    sys.exit(app.exec())

