# desktop/client.py
import sys
import os
import json
import tempfile
import webbrowser
from pathlib import Path

import pandas as pd
import requests  # used when switching to real backend
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTabWidget, QLineEdit, QMessageBox,
    QTableView, QComboBox, QProgressBar
)
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from table_model import DataFrameModel

# ----------------------
# Local sample files (you uploaded these earlier)
# ----------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # desktop -> project root
SAMPLE_CSV_PATH = PROJECT_ROOT / "samples" / "sample_equipment_data.csv"
SAMPLE_SUMMARY_JSON = PROJECT_ROOT / "samples" / "sample_summary_api_payload.json"  # e.g. "/mnt/data/sample_report.pdf" or place PDF in desktop/ and set path

# ----------------------
# Mock API layer (for frontend dev). Replace with real requests calls later.
# ----------------------
def login_mock(username, password):
    # very simple mock login that always returns a token
    if username and password:
        return {"token": "fake-desktop-token", "user": username}
    raise ValueError("Invalid username/password (mock)")

def upload_mock(file_path):
    """
    Mock upload: simulate "upload" and return dataset_id and summary path (local)
    We use SAMPLE_SUMMARY_JSON as the backend's summary response.
    """
    # In a real backend you would do:
    # with open(file_path, "rb") as f:
    #     r = requests.post(f"{API_BASE_URL}/api/datasets/upload/", files={"file": f}, headers=...)
    #     return r.json()
    # For mock, return local sample summary path
    return {
        "dataset_id": Path(file_path).name,
        "summary_url": SAMPLE_SUMMARY_JSON,  # we will read JSON directly from file
        "history_url": None
    }

def get_summary_mock(dataset_id_or_url):
    # dataset_id_or_url might be a path or URL; if it's the sample path, read file
    path = dataset_id_or_url
    if path is None:
        path = SAMPLE_SUMMARY_JSON
    # If looks like path, read
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    # Otherwise return a simple summary stub
    return {
        "dataset_id": str(dataset_id_or_url),
        "rows": 0,
        "columns": [],
        "numeric_columns": [],
        "summary": {},
        "raw_preview": []
    }

def get_history_mock():
    return [
        {
            "dataset_id": Path(SAMPLE_CSV_PATH).name,
            "uploaded_at": "2025-11-17T12:00:00Z",
            "rows": 15,
            "columns": ["ID","Flowrate","Pressure","Temperature","Note"]
        }
    ]

def download_report_mock(dataset_id):
    """
    Mock: if SAMPLE_PDF is provided and exists, open it; otherwise create a small temporary PDF file.
    """
    if SAMPLE_PDF and os.path.exists(SAMPLE_PDF):
        return SAMPLE_PDF

    # create a small placeholder PDF via a minimal PDF header (not a full report)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp_path = tmp.name
    tmp.close()
    # create a very small valid PDF using a basic template
    pdf_bytes = b"%PDF-1.1\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R >> endobj\n4 0 obj << /Length 44 >> stream\nBT /F1 24 Tf 20 180 Td (Sample Report) Tj ET\nendstream endobj\nxref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000061 00000 n \n0000000112 00000 n \n0000000213 00000 n \ntrailer << /Root 1 0 R >>\nstartxref\n310\n%%EOF"
    with open(tmp_path, "wb") as f:
        f.write(pdf_bytes)
    return tmp_path

# ----------------------
# GUI: Login dialog (simple)
# ----------------------
class LoginWidget(QWidget):
    def __init__(self, on_login):
        super().__init__()
        self.on_login = on_login
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>Login (mock)</b>"))
        self.username = QLineEdit()
        self.username.setPlaceholderText("username")
        self.password = QLineEdit()
        self.password.setPlaceholderText("password")
        self.password.setEchoMode(QLineEdit.Password)
        btn = QPushButton("Sign in")
        btn.clicked.connect(self.do_login)
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addWidget(btn)
        self.setLayout(layout)

    def do_login(self):
        try:
            res = login_mock(self.username.text().strip(), self.password.text().strip())
            self.on_login(res)
        except Exception as e:
            QMessageBox.warning(self, "Login failed", str(e))

# ----------------------
# GUI: Main Window
# ----------------------
class MainWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.token = user.get("token")
        self.setWindowTitle(f"Equipment Visualizer — Desktop — {user.get('user')}")
        self.resize(1000, 700)
        self.current_df = None  # pandas DataFrame for preview/raw rows
        self.current_summary = None
        self._create_ui()

    def _create_ui(self):
        container = QWidget()
        layout = QVBoxLayout()

        # top actions
        top_bar = QHBoxLayout()
        self.lbl_file = QLabel("No file loaded")
        btn_choose = QPushButton("Choose CSV")
        btn_choose.clicked.connect(self.choose_file)
        btn_load_sample = QPushButton("Load sample CSV")
        btn_load_sample.clicked.connect(self.load_sample_csv)
        btn_upload = QPushButton("Upload (mock)")
        btn_upload.clicked.connect(self.upload_current_file)
        btn_report = QPushButton("Generate / Open Report (mock)")
        btn_report.clicked.connect(self.generate_report)
        top_bar.addWidget(self.lbl_file)
        top_bar.addWidget(btn_choose)
        top_bar.addWidget(btn_load_sample)
        top_bar.addWidget(btn_upload)
        top_bar.addWidget(btn_report)
        layout.addLayout(top_bar)

        # progress bar for upload (mock)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # tabs: Preview, Chart, History
        self.tabs = QTabWidget()
        self.tab_preview = QWidget()
        self.tab_chart = QWidget()
        self.tab_history = QWidget()

        self._init_preview_tab()
        self._init_chart_tab()
        self._init_history_tab()

        self.tabs.addTab(self.tab_preview, "Preview")
        self.tabs.addTab(self.tab_chart, "Chart")
        self.tabs.addTab(self.tab_history, "History")

        layout.addWidget(self.tabs)
        container.setLayout(layout)
        self.setCentralWidget(container)

    # -----------------
    # Preview tab
    # -----------------
    def _init_preview_tab(self):
        v = QVBoxLayout()
        self.table_view = QTableView()
        self.table_model = DataFrameModel()
        self.table_view.setModel(self.table_model)
        v.addWidget(self.table_view)
        self.tab_preview.setLayout(v)

    # -----------------
    # Chart tab
    # -----------------
    def _init_chart_tab(self):
        v = QVBoxLayout()
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Y column:"))
        self.combo_y = QComboBox()
        controls.addWidget(self.combo_y)
        btn_plot = QPushButton("Plot")
        btn_plot.clicked.connect(self.plot_selected_column)
        controls.addWidget(btn_plot)
        v.addLayout(controls)

        # Matplotlib canvas
        self.figure = Figure(figsize=(6,4))
        self.canvas = FigureCanvas(self.figure)
        v.addWidget(self.canvas)
        self.tab_chart.setLayout(v)

    # -----------------
    # History tab
    # -----------------
    def _init_history_tab(self):
        v = QVBoxLayout()
        self.history_label = QLabel("Loading history...")
        v.addWidget(self.history_label)
        self.history_container = QVBoxLayout()
        v.addLayout(self.history_container)
        self.tab_history.setLayout(v)
        self.load_history()

    def load_history(self):
        hist = get_history_mock()
        self.history_label.setText("")
        # clear existing children
        while self.history_container.count():
            child = self.history_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        for entry in hist:
            hbox = QHBoxLayout()
            lbl = QLabel(f"{entry['dataset_id']}  ({entry['rows']} rows)")
            btn_load = QPushButton("Load")
            btn_load.clicked.connect(lambda checked, e=entry: self.load_history_entry(e))
            hbox.addWidget(lbl)
            hbox.addWidget(btn_load)
            self.history_container.addLayout(hbox)

    def load_history_entry(self, entry):
        summary = get_summary_mock(entry.get("dataset_id"))
        self.apply_summary(summary)

    # -----------------
    # File handling & upload
    # -----------------
    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV", ".", "CSV Files (*.csv)")
        if not path:
            return
        self.lbl_file.setText(path)
        self.load_csv_preview(path)

    def load_sample_csv(self):
        if not os.path.exists(SAMPLE_CSV_PATH):
            QMessageBox.warning(self, "Sample missing", f"Sample CSV not found at {SAMPLE_CSV_PATH}")
            return
        self.lbl_file.setText(SAMPLE_CSV_PATH)
        self.load_csv_preview(SAMPLE_CSV_PATH)

    def load_csv_preview(self, path):
        try:
            df = pd.read_csv(path)
        except Exception as e:
            QMessageBox.critical(self, "Error reading CSV", str(e))
            return
        # keep only first 200 rows for UI
        preview = df.head(200).copy()
        self.current_df = preview
        self.table_model.setDataFrame(preview)
        # populate chart column dropdown with numeric columns
        numeric_cols = preview.select_dtypes(include="number").columns.tolist()
        self.combo_y.clear()
        self.combo_y.addItems(numeric_cols)
        # also clear current summary
        self.current_summary = None

    def upload_current_file(self):
        path = self.lbl_file.text()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "No file", "Choose or load a CSV file first.")
            return
        # show progress bar (mock)
        self.progress.setVisible(True)
        self.progress.setValue(10)
        # mock upload
        try:
            res = upload_mock(path)
            self.progress.setValue(50)
            summary = get_summary_mock(res.get("summary_url"))
            self.progress.setValue(90)
            self.apply_summary(summary)
            self.progress.setValue(100)
        except Exception as e:
            QMessageBox.critical(self, "Upload failed", str(e))
        finally:
            self.progress.setVisible(False)

    def apply_summary(self, summary):
        """
        summary: expected dict with keys:
          - dataset_id
          - rows
          - columns
          - numeric_columns
          - summary (per-column stats)
          - raw_preview (optional list of row dicts)
        """
        self.current_summary = summary
        # if raw_preview exists, load into DataFrame model
        rows = summary.get("raw_preview")
        if rows:
            try:
                df = pd.DataFrame(rows)
                self.current_df = df
                self.table_model.setDataFrame(df)
            except Exception:
                pass
        # populate numeric dropdown
        numeric = summary.get("numeric_columns", [])
        # If table has numeric types but summary doesn't list, take from df
        if not numeric and self.current_df is not None:
            numeric = self.current_df.select_dtypes(include="number").columns.tolist()
        self.combo_y.clear()
        self.combo_y.addItems(numeric)
        # switch to preview tab so user sees result
        self.tabs.setCurrentWidget(self.tab_preview)
        QMessageBox.information(self, "Summary loaded", f"Loaded summary for {summary.get('dataset_id')}")

    # -----------------
    # Chart plotting
    # -----------------
    def plot_selected_column(self):
        ycol = self.combo_y.currentText()
        if not ycol:
            QMessageBox.warning(self, "No column", "Select a numeric column to plot.")
            return
        # prepare x and y values
        if self.current_df is not None and ycol in self.current_df.columns:
            # prefer raw preview values
            series = self.current_df[ycol].astype(float, errors='ignore').fillna(method='ffill').to_list()
            x = list(range(1, len(series)+1))
            y = series
        elif self.current_summary:
            # fallback: use mean repeated across 'rows' count
            rows = self.current_summary.get("rows", 10) or 10
            mean_val = self.current_summary.get("summary", {}).get(ycol, {}).get("mean", 0)
            x = list(range(1, rows+1))
            y = [mean_val] * rows
        else:
            QMessageBox.warning(self, "No data", "No data available to plot.")
            return

        # draw
        self.figure.clf()
        ax = self.figure.add_subplot(111)
        ax.plot(x, y, marker='o', linestyle='-')
        ax.set_title(ycol)
        ax.set_xlabel("Index")
        ax.set_ylabel(ycol)
        self.canvas.draw()

    # -----------------
    # Generate / download report (mock)
    # -----------------
    def generate_report(self):
        if not self.current_summary:
            QMessageBox.warning(self, "No dataset", "Load a dataset summary first.")
            return
        # mock download
        pdf_path = download_report_mock(self.current_summary.get("dataset_id"))
        if not pdf_path or not os.path.exists(pdf_path):
            QMessageBox.warning(self, "Report", "Failed to generate/open report.")
            return
        # Try to open using default system viewer
        try:
            webbrowser.open_new(f"file://{pdf_path}")
            QMessageBox.information(self, "Report", f"Opened report: {pdf_path}")
        except Exception as e:
            QMessageBox.information(self, "Report saved", f"Report saved at {pdf_path}\n{e}")

# ----------------------
# Startup
# ----------------------
def main():
    app = QApplication(sys.argv)

    # Show login first
    def on_login(user):
        login_widget.close()
        mw = MainWindow(user)
        mw.show()
        app.exec_()

    login_widget = LoginWidget(on_login)
    login_widget.setWindowTitle("Login — Equipment Visualizer (Desktop)")
    login_widget.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

