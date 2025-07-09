from PyQt5.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QListWidget, QPushButton,
    QListWidgetItem, QFileDialog, QMenu, QLabel, QGraphicsOpacityEffect,
    QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation
from PyQt5.QtGui import QPixmap
import sys, os



# ### SplashScreen
# A frameless, translucent splash screen that displays a given image with a fade-in animation.
# Intended to simulate a professional application launch screen.
# Closes automatically after the specified duration.
class SplashScreen(QDialog):
    def __init__(self, image_path, duration=4000): # duration: 4 seconds
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Layout & Bild
        layout = QVBoxLayout()
        label = QLabel()
        pixmap = QPixmap(image_path)
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.setLayout(layout)
        self.resize(pixmap.size())

        # Opacity + Fade-in
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.anim = QPropertyAnimation(self.effect, b"opacity")
        self.anim.setDuration(duration)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

        # Automatisch schließen
        QTimer.singleShot(duration, self.close)


# ### DragDropWidget
# A custom QWidget that enables drag-and-drop functionality for file input.
# Dropped files are displayed in a QListWidget, and users can remove them via a right-click context menu.
# Checked items can be retrieved using `get_file_paths()` to determine which files are selected for further processing.

class DragDropWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setAcceptDrops(True)
        self.file_list = QListWidget()
        self.layout.addWidget(self.file_list)
        self.setLayout(self.layout)
        self.file_paths = []

        self.file_list.setSelectionMode(QListWidget.SingleSelection)
        self.file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self.show_context_menu)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                self.file_paths.append(path)
                item = QListWidgetItem(os.path.basename(path))
                item.setToolTip(path)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.file_list.addItem(item)

    def get_file_paths(self):
        return [
            item.toolTip()
            for i in range(self.file_list.count())
            if (item := self.file_list.item(i)).checkState() == Qt.Checked
        ]

    def show_context_menu(self, pos):
        menu = QMenu(self)
        remove_action = menu.addAction("Remove selected")
        action = menu.exec_(self.file_list.mapToGlobal(pos))
        if action == remove_action:
            for item in self.file_list.selectedItems():
                self.file_paths.remove(item.toolTip())
                self.file_list.takeItem(self.file_list.row(item))

class LabeledDropArea(QWidget):
    def __init__(self, label_text):
        super().__init__()
        self.layout = QVBoxLayout()
        self.label = QLabel(label_text)
        self.drop_area = DragDropWidget()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.drop_area)
        self.setLayout(self.layout)

    def get_file_paths(self):
        return self.drop_area.get_file_paths()



# ### MultiFileInputGUI
# A QWidget that provides a user-friendly interface for selecting multiple input files and an output directory.
# Users can drag and drop files into labeled drop areas for brightfield and signal images.
# The "Run Analysis" button is only enabled once both image types and an output folder have been provided.
# Intended to simplify file selection for non-programming users in image analysis workflows.

class MultiFileInputGUI(QDialog):
    def __init__(self):
        super().__init__()
        self.selected_paths = None
        self.setWindowTitle("Multi File Input GUI")
        self.resize(500, 600)
        self.layout = QVBoxLayout()

        self.brightfield_input = LabeledDropArea("Drop Brightfield Image:")
        self.signal_input = LabeledDropArea("Drop Signal Image:")

        self.output_label = QLabel("Output to: Not selected")
        self.output_path = None

        self.output_button = QPushButton("Select Output Directory")
        self.run_button = QPushButton("Run Analysis")

        self.output_button.clicked.connect(self.select_output_folder)
        self.run_button.clicked.connect(self.run_analysis)

        self.layout.addWidget(self.brightfield_input)
        self.layout.addWidget(self.signal_input)
        self.layout.addWidget(self.output_button)
        self.layout.addWidget(self.output_label)
        self.layout.addWidget(self.run_button)

        self.setLayout(self.layout)

        # Disable run button initially
        self.run_button.setEnabled(False)

        # Connect signals to monitor input state
        self.brightfield_input.drop_area.file_list.itemChanged.connect(self.check_ready)
        self.signal_input.drop_area.file_list.itemChanged.connect(self.check_ready)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_path = folder
            self.output_label.setText(f"Output to: {folder}")
        self.check_ready()

    def run_analysis(self):
        bright_paths = self.brightfield_input.get_file_paths()
        signal_paths = self.signal_input.get_file_paths()
        out_dir = self.output_path

        if not bright_paths or not signal_paths or not out_dir:
            QMessageBox.warning(self, "Missing Inputs",
                                "Please drop both Brightfield and Signal images and select an output folder.")
            return

        bf = bright_paths[0]
        sig = signal_paths[0]
        # store selected paths and close
        self.selected_paths = (bf, sig, out_dir)
        self.accept()

    def check_ready(self):
        brightfield_ready = len(self.brightfield_input.get_file_paths()) > 0
        signal_ready = len(self.signal_input.get_file_paths()) > 0
        output_ready = self.output_path is not None
        self.run_button.setEnabled(brightfield_ready and signal_ready and output_ready)


def pick_file_paths():
    """
    Show the drag-and-drop file-picker as a QDialog; return (path to brightfield, path to signal, output path) tuple.
    """
    dialog = MultiFileInputGUI()
    result = dialog.exec_()
    if result == QDialog.Accepted:
        return dialog.selected_paths
    return None


# to generate correct paths withing code distribution
def resource_path(relative_path):
    # when bundled with PyInstaller this will be something like /.../_MEIPASS
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        # two levels up: scripts/ → project root
        helper_dir = os.path.dirname(os.path.abspath(__file__))
        base = os.path.dirname(helper_dir)
    return os.path.join(base, relative_path)