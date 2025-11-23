# desktop/main_window.py
from pathlib import Path
import os
import tempfile
import webbrowser
import traceback
import json
import matplotlib

# set backend early (before importing FigureCanvas on some systems)
matplotlib.use("Qt5Agg")

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QTabWidget, QLineEdit, QMessageBox, QTableView,
    QComboBox, QProgressBar, QCheckBox
)
from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal

import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from table_model import DataFrameModel
from api import (
    login_user, upload_file, get_summary, get_history, download_report,
    set_token
)
from auth import load_cached_token, save_token, clear_cached_token

# Project sample locations (relative to repo root)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
# default sample (the file you uploaded earlier)
SAMPLE_CSV_PATH = Path("../samples/sample_equipment_data.csv")
SAMPLE_SUMMARY_JSON = PROJECT_ROOT / "samples" / "sample_summary_api_payload.json"
SAMPLE_PDF = PROJECT_ROOT / "samples" / "sample_report.pdf"

# -----------------------
# Worker & threading helpers
# -----------------------
class WorkerSignals(QObject):
    finished = pyqtSignal(object)   # result
    error = pyqtSignal(Exception)   # exception instance

class Worker(QObject):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception as e:
            e._traceback = traceback.format_exc()
            self.signals.error.emit(e)

def run_in_thread(fn, on_done=None, on_error=None, *args, **kwargs):
    """
    Run fn in a QThread non-blockingly.
    - on_done(result) and on_error(exc) are called on the main thread.
    - Returns the QThread instance (caller should keep a reference).
    """
    thread = QThread()
    worker = Worker(fn, *args, **kwargs)
    worker.moveToThread(thread)

    def handle_done(result):
        if on_done:
            try:
                on_done(result)
            except Exception as e:
                print("Error in on_done callback:", e)
        try:
            thread.quit()  # request thread to stop; do NOT wait here
        except Exception:
            pass

    def handle_error(exc):
        if on_error:
            try:
                on_error(exc)
            except Exception as e:
                print("Error in on_error callback:", e)
        try:
            thread.quit()
        except Exception:
            pass

    def cleanup():
        # executed when thread finishes (non-blocking)
        try:
            worker.deleteLater()
        except Exception:
            pass
        try:
            thread.deleteLater()
        except Exception:
            pass

    worker.signals.finished.connect(handle_done)
    worker.signals.error.connect(handle_error)
    thread.started.connect(worker.run)
    thread.finished.connect(cleanup)

    thread.start()
    return thread

# -----------------------
# CSV reading helper to run inside worker
# -----------------------
def _read_csv_sync(path):
    # This runs inside a background thread
    import pandas as pd
    # Use a simple read_csv; caller will .head() for preview
    df = pd.read_csv(path)
    return df

# -----------------------
# Login widget
# -----------------------
class LoginWidget(QWidget):
    def __init__(self, on_login):
        super().__init__()
        self.on_login = on_login
        self._login_thread = None
        self.init_ui()
        self.setWindowTitle("Login — Equipment Visualizer (Desktop)")

        cached = load_cached_token()
        if cached:
            self.username.setText(cached.get("username", ""))
            self.remember_chk.setChecked(True)

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>Login</b>"))

        self.username = QLineEdit()
        self.username.setPlaceholderText("username")
        self.password = QLineEdit()
        self.password.setPlaceholderText("password")
        self.password.setEchoMode(QLineEdit.Password)

        self.remember_chk = QCheckBox("Remember me (store token locally)")
        btn = QPushButton("Sign in")
        btn.clicked.connect(self.do_login)

        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addWidget(self.remember_chk)
        layout.addWidget(btn)
        self.setLayout(layout)

    def do_login(self):
        username = self.username.text().strip()
        password = self.password.text().strip()
        remember = self.remember_chk.isChecked()
        if not username or not password:
            QMessageBox.warning(self, "Missing", "Enter username and password")
            return

        def _on_done(res):
            token = res.get("token") or res.get("key") or res.get("auth_token")
            if not token:
                QMessageBox.critical(self, "Login failed", f"No token returned: {res}")
                return
            set_token(token)
            if remember:
                save_token(username, token)
            self.on_login({"user": username, "token": token})

        def _on_err(exc):
            tb = getattr(exc, "_traceback", "")
            QMessageBox.critical(self, "Login error", f"{str(exc)}\n\n{tb}")

        self._login_thread = run_in_thread(login_user, _on_done, _on_err, username, password, remember)

# -----------------------
# Main window
# -----------------------
class MainWindow(QWidget):
    def __init__(self, user):
        super().__init__()
        # keep references to threads so they are not GC'd
        self.threads = []
        self.user = user
        self.token = user.get("token")
        set_token(self.token)
        self.setWindowTitle(f"Equipment Visualizer — Desktop — {user.get('user')}")
        self.resize(1000, 700)
        self.current_df = None
        self.current_summary = None
        self._create_ui()

    def _create_ui(self):
        layout = QVBoxLayout()

        # top actions
        top_bar = QHBoxLayout()
        self.lbl_file = QLabel("No file loaded")
        btn_choose = QPushButton("Choose CSV")
        btn_choose.clicked.connect(self.choose_file)
        btn_load_sample = QPushButton("Load sample CSV")
        btn_load_sample.clicked.connect(self.load_sample_csv)
        btn_upload = QPushButton("Upload (to backend)")
        btn_upload.clicked.connect(self.upload_current_file)
        btn_report = QPushButton("Generate / Open Report")
        btn_report.clicked.connect(self.generate_report)
        top_bar.addWidget(self.lbl_file)
        top_bar.addWidget(btn_choose)
        top_bar.addWidget(btn_load_sample)
        top_bar.addWidget(btn_upload)
        top_bar.addWidget(btn_report)
        layout.addLayout(top_bar)

        # progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # tabs
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
        self.setLayout(layout)

    # preview tab
    def _init_preview_tab(self):
        v = QVBoxLayout()
        self.table_view = QTableView()
        self.table_model = DataFrameModel()
        self.table_view.setModel(self.table_model)
        v.addWidget(self.table_view)
        self.tab_preview.setLayout(v)

    # chart tab
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

        # Matplotlib canvas: give parent and keep on main thread
        self.figure = Figure(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setParent(self)
        v.addWidget(self.canvas)
        self.tab_chart.setLayout(v)

    # history tab
    def _init_history_tab(self):
        v = QVBoxLayout()
        self.history_label = QLabel("Loading history...")
        v.addWidget(self.history_label)
        self.history_container = QVBoxLayout()
        v.addLayout(self.history_container)
        self.tab_history.setLayout(v)
        self.load_history()

    # helper to start threads and keep references; remove on finished
    def _start_thread(self, fn, on_done=None, on_error=None, *args):
        th = run_in_thread(fn, on_done, on_error, *args)
        self.threads.append(th)
        # remove reference on finished so it can be GC'd later
        def _try_remove():
            try:
                if th in self.threads:
                    self.threads.remove(th)
            except Exception:
                pass
        # connect removal to finished signal (thread may not have attribute 'finished' publicly,
        # but QThread has finished signal we can connect)
        try:
            th.finished.connect(_try_remove)
        except Exception:
            # if connection fails, ignore (we still keep the reference for safety)
            pass
        return th

    # -----------------
    # History
    # -----------------
    def load_history(self):
        self.history_label.setText("Loading history...")
        self._clear_history_children()

        def _on_done(res):
            self.history_label.setText("")
            self._render_history(res)

        def _on_err(exc):
            self.history_label.setText("Failed to load history")
            QMessageBox.warning(self, "History error", f"{str(exc)}\n\n{getattr(exc, '_traceback', '')}")

        self._start_thread(get_history, _on_done, _on_err)

    def _clear_history_children(self):
        while self.history_container.count():
            child = self.history_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _render_history(self, entries):
        for entry in entries:
            hbox = QHBoxLayout()
            lbl = QLabel(f"{entry.get('dataset_id')}  ({entry.get('rows')} rows)")
            btn_load = QPushButton("Load")
            btn_load.clicked.connect(lambda checked, e=entry: self.load_history_entry(e))
            hbox.addWidget(lbl)
            hbox.addWidget(btn_load)
            self.history_container.addLayout(hbox)

    def load_history_entry(self, entry):
        """
        Safely load a history entry's summary. Normalizes fallback keys and prevents
        calling the API with None.
        """
        self.progress.setVisible(True)
        self.progress.setValue(10)

        def _on_done(summary):
            self.progress.setValue(100)
            self.apply_summary(summary)
            self.progress.setVisible(False)

        def _on_err(exc):
            self.progress.setVisible(False)
            QMessageBox.critical(self, "Summary error", f"{str(exc)}\n\n{getattr(exc,'_traceback','')}")

        # prefer numeric id if exists
        ds = entry.get("dataset_id") or entry.get("id") or entry.get("original_filename") or entry.get("filename")

        # if ds is 'unknown' or None, show message and abort
        if not ds or ds == "unknown":
            QMessageBox.warning(self, "Cannot load", "This history entry does not contain a usable dataset id.")
            self.progress.setVisible(False)
            return

        # If ds looks like a filename (ends with .csv) we might instead attempt to fetch via a static path:
        if isinstance(ds, str) and ds.lower().endswith(".csv"):
            # First try backend summary endpoint using filename as identifier (some backends support this)
            # Fallback: try to fetch a public sample JSON path if present in samples folder
            try:
                # Try numeric id first if ds is numeric-like
                if str(ds).isdigit():
                    self._start_thread(get_summary, _on_done, _on_err, int(ds))
                else:
                    # try as string id (some backends accept filenames)
                    self._start_thread(get_summary, _on_done, _on_err, ds)
            except Exception as e:
                self.progress.setVisible(False)
                QMessageBox.critical(self, "Error", str(e))
            return

        # otherwise call summary using ds
        self._start_thread(get_summary, _on_done, _on_err, ds)

    # -----------------
    # File handling (CSV load in background)
    # -----------------
    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV", ".", "CSV Files (*.csv)")
        if not path:
            return
        self.lbl_file.setText(path)
        self.load_csv_preview(path)

    def load_sample_csv(self):
        if not SAMPLE_CSV_PATH.exists():
            QMessageBox.warning(self, "Sample missing", f"Sample CSV not found at {SAMPLE_CSV_PATH}")
            return
        self.lbl_file.setText(str(SAMPLE_CSV_PATH))
        # load CSV in a background thread (avoids blocking GUI/painting)
        def _on_done(df):
            try:
                preview = df.head(200).copy()
                self.current_df = preview
                self.table_model.setDataFrame(preview)
                numeric_cols = preview.select_dtypes(include="number").columns.tolist()
                self.combo_y.clear()
                self.combo_y.addItems(numeric_cols)
                self.current_summary = None
            except Exception as e:
                QMessageBox.critical(self, "CSV load error", str(e))

        def _on_err(exc):
            tb = getattr(exc, "_traceback", "")
            QMessageBox.critical(self, "CSV read failed", f"{str(exc)}\n\n{tb}")

        self._start_thread(_read_csv_sync, _on_done, _on_err, str(SAMPLE_CSV_PATH))

    def load_csv_preview(self, path):
        if not os.path.exists(path):
            QMessageBox.warning(self, "File missing", f"File not found: {path}")
            return
        self.lbl_file.setText(path)

        def _on_done(df):
            try:
                preview = df.head(200).copy()
                self.current_df = preview
                self.table_model.setDataFrame(preview)
                numeric_cols = preview.select_dtypes(include="number").columns.tolist()
                self.combo_y.clear()
                self.combo_y.addItems(numeric_cols)
                self.current_summary = None
            except Exception as e:
                QMessageBox.critical(self, "CSV load error", str(e))

        def _on_err(exc):
            tb = getattr(exc, "_traceback", "")
            QMessageBox.critical(self, "CSV read failed", f"{str(exc)}\n\n{tb}")

        self._start_thread(_read_csv_sync, _on_done, _on_err, path)

    # -----------------
    # Upload
    # -----------------
    def upload_current_file(self):
        path = self.lbl_file.text()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "No file", "Choose or load a CSV file first.")
            return

        self.progress.setVisible(True)
        self.progress.setValue(5)

        def _on_done(res):
            self.progress.setValue(50)
            try:
                dataset_id = res.get("dataset_id") or res.get("id") or None
                summary_url = res.get("summary_url")
                if summary_url:
                    self._start_thread(get_summary,
                                       lambda s: (self.apply_summary(s), self.progress.setValue(100), self.progress.setVisible(False)),
                                       lambda e: (QMessageBox.critical(self, "Summary load failed", str(e)), self.progress.setVisible(False)),
                                       summary_url)
                elif dataset_id:
                    self._start_thread(get_summary,
                                       lambda s: (self.apply_summary(s), self.progress.setValue(100), self.progress.setVisible(False)),
                                       lambda e: (QMessageBox.critical(self, "Summary load failed", str(e)), self.progress.setVisible(False)),
                                       dataset_id)
                else:
                    if isinstance(res, dict) and res.get("summary"):
                        self.apply_summary(res)
                        self.progress.setValue(100)
                        self.progress.setVisible(False)
                    else:
                        QMessageBox.information(self, "Upload", f"Upload completed: {res}")
                        self.progress.setVisible(False)
            except Exception as e:
                self.progress.setVisible(False)
                QMessageBox.critical(self, "Upload result error", str(e))

        def _on_err(exc):
            self.progress.setVisible(False)
            QMessageBox.critical(self, "Upload failed", f"{str(exc)}\n\n{getattr(exc,'_traceback','')}")

        self._start_thread(upload_file, _on_done, _on_err, path)
        self.progress.setValue(20)

    # -----------------
    # Apply summary
    # -----------------
    def apply_summary(self, summary):
        self.current_summary = summary
        rows = summary.get("raw_preview")
        if rows:
            try:
                df = pd.DataFrame(rows)
                self.current_df = df
                self.table_model.setDataFrame(df)
            except Exception:
                pass
        numeric = summary.get("numeric_columns", [])
        if not numeric and self.current_df is not None:
            numeric = self.current_df.select_dtypes(include="number").columns.tolist()
        self.combo_y.clear()
        self.combo_y.addItems(numeric)
        self.tabs.setCurrentWidget(self.tab_preview)
        QMessageBox.information(self, "Summary loaded", f"Loaded summary for {summary.get('dataset_id')}")

    # -----------------
    # Plotting
    # -----------------
    def plot_selected_column(self):
        ycol = self.combo_y.currentText()
        if not ycol:
            QMessageBox.warning(self, "No column", "Select a numeric column to plot.")
            return
        if self.current_df is not None and ycol in self.current_df.columns:
            series = pd.to_numeric(self.current_df[ycol], errors="coerce").fillna(method="ffill").tolist()
            x = list(range(1, len(series) + 1))
            y = series
        elif self.current_summary:
            rows = self.current_summary.get("rows", 10) or 10
            mean_val = self.current_summary.get("summary", {}).get(ycol, {}).get("mean", 0)
            x = list(range(1, rows + 1))
            y = [mean_val] * rows
        else:
            QMessageBox.warning(self, "No data", "No data available to plot.")
            return

        self.figure.clf()
        ax = self.figure.add_subplot(111)
        ax.plot(x, y, marker="o", linestyle="-")
        ax.set_title(ycol)
        ax.set_xlabel("Index")
        ax.set_ylabel(ycol)
        try:
            # use draw_idle to let Qt schedule paint safely
            self.canvas.draw_idle()
        except Exception:
            try:
                self.canvas.draw()
            except Exception as e:
                print("Plot draw error:", e)

    # -----------------
    # Report download
    # -----------------
    def generate_report(self):
        if not self.current_summary:
            QMessageBox.warning(self, "No dataset", "Load a dataset summary first.")
            return

        self.progress.setVisible(True)
        self.progress.setValue(5)

        def _on_done(out_path):
            self.progress.setVisible(False)
            if not out_path or not os.path.exists(out_path):
                QMessageBox.warning(self, "Report", "Failed to download report.")
                return
            try:
                webbrowser.open_new(f"file://{out_path}")
                QMessageBox.information(self, "Report", f"Opened report: {out_path}")
            except Exception as e:
                QMessageBox.information(self, "Report saved", f"Report saved at {out_path}\n{e}")

        def _on_err(exc):
            self.progress.setVisible(False)
            QMessageBox.critical(self, "Report error", f"{str(exc)}\n\n{getattr(exc,'_traceback','')}")

        dataset_id = self.current_summary.get("dataset_id")
        self._start_thread(download_report, _on_done, _on_err, dataset_id)

    # -----------------
    # Safe cleanup on close
    # -----------------
    def closeEvent(self, event):
        # Request threads to quit but do not block (cleanup happens in thread.finished)
        try:
            for th in list(self.threads):
                try:
                    th.quit()
                except Exception:
                    pass
        except Exception:
            pass

        # close Matplotlib canvas safely
        try:
            if hasattr(self, "canvas") and self.canvas is not None:
                try:
                    self.canvas.close()
                except Exception:
                    pass
        except Exception:
            pass

        super().closeEvent(event)
