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
    QComboBox, QProgressBar, QCheckBox, QFrame, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal, QSize

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
SAMPLE_CSV_PATH = PROJECT_ROOT / "samples" / "sample_equipment_data.csv"
SAMPLE_SUMMARY_JSON = PROJECT_ROOT / "samples" / "sample_summary_api_payload.json"
SAMPLE_PDF = PROJECT_ROOT / "samples" / "sample_report.pdf"

# -----------------------
# Worker & threading helpers (same robust approach)
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
    thread = QThread()
    worker = Worker(fn, *args, **kwargs)
    worker.moveToThread(thread)

    def _finished_slot(result):
        if on_done:
            try:
                on_done(result)
            except Exception as e:
                print("Error in on_done callback:", e)
        try:
            thread.quit()
        except Exception:
            pass

    def _error_slot(exc):
        if on_error:
            try:
                on_error(exc)
            except Exception as e:
                print("Error in on_error callback:", e)
        try:
            thread.quit()
        except Exception:
            pass

    def _cleanup():
        try:
            worker.deleteLater()
        except Exception:
            pass
        try:
            thread.deleteLater()
        except Exception:
            pass

    worker.signals.finished.connect(_finished_slot)
    worker.signals.error.connect(_error_slot)
    thread.started.connect(worker.run)
    thread.finished.connect(_cleanup)

    thread.start()
    return thread

def _read_csv_sync(path):
    import pandas as pd
    df = pd.read_csv(path)
    return df

# -----------------------
# Login widget (unchanged logic)
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
        self.threads = []
        self.user = user
        self.token = user.get("token")
        set_token(self.token)
        self.setWindowTitle(f"Equipment Visualizer — Desktop — {user.get('user')}")
        self.resize(1100, 720)
        self.current_df = None
        self.current_summary = None
        self._create_ui()
        self.apply_styles()

    def apply_styles(self):
        # Basic theme matching web: soft cards, rounded buttons, readable font
        qss = """
        QWidget {
          background: #f8fafc;
          font-family: Inter, Arial, sans-serif;
          color: #0f172a;
          font-size: 13px;
        }
        QFrame#card {
          background: white;
          border-radius: 10px;
          border: 1px solid #e6eef8;
          padding: 10px;
        }
        QPushButton {
          background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #5b8def, stop:1 #3f6ef5);
          color: white;
          padding: 8px 12px;
          border-radius: 8px;
          border: none;
          min-height: 28px;
        }
        QPushButton[secondary="true"] {
          background: transparent;
          color: #1f2937;
          border: 1px solid #d1d5db;
        }
        QPushButton:disabled { opacity: 0.6; }
        QLabel#muted { color: #6b7280; font-size:12px; }
        QTableView {
          background: white;
          gridline-color: #f3f4f6;
        }
        QProgressBar { height: 10px; border-radius: 5px; }
        """
        self.setStyleSheet(qss)

    def _create_ui(self):
        root = QVBoxLayout()

        # Top action row
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)
        self.lbl_file = QLabel("No file loaded")
        self.lbl_file.setObjectName("muted")
        btn_choose = QPushButton("Choose CSV")
        btn_choose.setProperty("secondary", True)
        btn_choose.clicked.connect(self.choose_file)
        btn_load_sample = QPushButton("Load sample CSV")
        btn_load_sample.setProperty("secondary", True)
        btn_load_sample.clicked.connect(self.load_sample_csv)
        btn_upload = QPushButton("Upload")
        btn_upload.clicked.connect(self.upload_current_file)
        btn_report = QPushButton("Generate / Open Report")
        btn_report.clicked.connect(self.generate_report)
        top_bar.addWidget(self.lbl_file, stretch=1)
        top_bar.addWidget(btn_choose)
        top_bar.addWidget(btn_load_sample)
        top_bar.addWidget(btn_upload)
        top_bar.addWidget(btn_report)
        root.addLayout(top_bar)

        # KPI / info row (card)
        kpi_card = QFrame()
        kpi_card.setObjectName("card")
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(24)

        # KPI widgets
        self.kpi_dataset = QLabel("Dataset: —")
        self.kpi_rows = QLabel("Rows: —")
        self.kpi_cols = QLabel("Columns: —")
        self.kpi_numeric = QLabel("Numeric: —")
        for lbl in (self.kpi_dataset, self.kpi_rows, self.kpi_cols, self.kpi_numeric):
            lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            lbl.setMinimumWidth(120)
            # subtle muted label under value would be nicer but keep simple
            kpi_layout.addWidget(lbl)

        kpi_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        kpi_card.setLayout(kpi_layout)
        root.addWidget(kpi_card)

        # progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        # main content split: left preview & upload, right history & actions
        main_h = QHBoxLayout()
        left_col = QVBoxLayout()
        right_col = QVBoxLayout()
        left_col.setSpacing(12)
        right_col.setSpacing(12)

        # Upload + preview card
        upload_card = QFrame()
        upload_card.setObjectName("card")
        upload_layout = QVBoxLayout()
        upload_layout.setSpacing(8)
        # File chooser + preview component are separate; reuse your Upload logic visually
        self.table_view = QTableView()
        self.table_model = DataFrameModel()
        self.table_view.setModel(self.table_model)
        upload_layout.addWidget(QLabel("<b>Data Preview</b>"))
        upload_layout.addWidget(self.table_view)
        upload_card.setLayout(upload_layout)
        left_col.addWidget(upload_card, stretch=1)

        # Chart card
        chart_card = QFrame()
        chart_card.setObjectName("card")
        chart_layout = QVBoxLayout()
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Y column:"))
        self.combo_y = QComboBox()
        controls.addWidget(self.combo_y)
        btn_plot = QPushButton("Plot")
        btn_plot.clicked.connect(self.plot_selected_column)
        controls.addWidget(btn_plot)
        chart_layout.addLayout(controls)
        self.figure = Figure(figsize=(6, 3))
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)
        chart_card.setLayout(chart_layout)
        left_col.addWidget(chart_card, stretch=0)

        # History & actions card on right
        history_card = QFrame()
        history_card.setObjectName("card")
        history_layout = QVBoxLayout()
        history_layout.addWidget(QLabel("<b>History</b>"))
        self.history_label = QLabel("Loading history...")
        history_layout.addWidget(self.history_label)
        self.history_container = QVBoxLayout()
        history_layout.addLayout(self.history_container)
        history_card.setLayout(history_layout)
        right_col.addWidget(history_card)

        # action card (download, KPIs)
        action_card = QFrame()
        action_card.setObjectName("card")
        action_layout = QVBoxLayout()
        action_layout.addWidget(QLabel("<b>Actions</b>"))
        # reuse report button as well
        btn_report2 = QPushButton("Generate / Download Report")
        btn_report2.clicked.connect(self.generate_report)
        action_layout.addWidget(btn_report2)
        action_card.setLayout(action_layout)
        right_col.addWidget(action_card)

        # assemble columns
        main_h.addLayout(left_col, stretch=3)
        main_h.addLayout(right_col, stretch=1)

        root.addLayout(main_h)
        self.setLayout(root)

        # initialize: load history and set current empty preview
        self._init_after_ui()

    def _init_after_ui(self):
        # If sample exists, pre-populate small preview (but don't auto-login)
        if SAMPLE_CSV_PATH.exists():
            # do not block — load later on demand
            pass
        self.load_history()

    # helper to start threads and track refs
    def _start_thread(self, fn, on_done=None, on_error=None, *args):
        th = run_in_thread(fn, on_done, on_error, *args)
        self.threads.append(th)
        try:
            th.finished.connect(lambda: self._try_remove_thread(th))
        except Exception:
            pass
        return th

    def _try_remove_thread(self, th):
        try:
            if th in self.threads:
                self.threads.remove(th)
        except Exception:
            pass

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
            btn_load.setProperty("secondary", True)
            btn_load.clicked.connect(lambda checked, e=entry: self.load_history_entry(e))
            hbox.addWidget(lbl)
            hbox.addWidget(btn_load)
            self.history_container.addLayout(hbox)

    def load_history_entry(self, entry):
        self.progress.setVisible(True)
        self.progress.setValue(10)

        def _on_done(summary):
            self.progress.setValue(100)
            self.apply_summary(summary)
            self.progress.setVisible(False)

        def _on_err(exc):
            self.progress.setVisible(False)
            QMessageBox.critical(self, "Summary error", f"{str(exc)}\n\n{getattr(exc,'_traceback','')}")

        ds = entry.get("dataset_id") or entry.get("id") or entry.get("original_filename")
        if not ds or ds == "unknown":
            QMessageBox.warning(self, "Cannot load", "This history entry does not contain a usable dataset id.")
            self.progress.setVisible(False)
            return

        self._start_thread(get_summary, _on_done, _on_err, ds)

    # -----------------
    # File handling
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
        self._start_thread(_read_csv_sync, self._on_csv_read_done, self._on_csv_read_err, str(SAMPLE_CSV_PATH))

    def load_csv_preview(self, path):
        if not os.path.exists(path):
            QMessageBox.warning(self, "File missing", f"File not found: {path}")
            return
        self.lbl_file.setText(path)
        self._start_thread(_read_csv_sync, self._on_csv_read_done, self._on_csv_read_err, path)

    def _on_csv_read_done(self, df):
        try:
            preview = df.head(200).copy()
            self.current_df = preview
            self.table_model.setDataFrame(preview)
            numeric_cols = preview.select_dtypes(include="number").columns.tolist()
            self.combo_y.clear()
            self.combo_y.addItems(numeric_cols)
            self.current_summary = None
            # update KPI
            self.update_kpis(dataset_label=os.path.basename(self.lbl_file.text()), rows=len(df), cols=len(df.columns), numeric=numeric_cols)
        except Exception as e:
            QMessageBox.critical(self, "CSV load error", str(e))

    def _on_csv_read_err(self, exc):
        tb = getattr(exc, "_traceback", "")
        QMessageBox.critical(self, "CSV read failed", f"{str(exc)}\n\n{tb}")

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
    # Apply summary + update KPI
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
        self.tabs.setCurrentWidget(self.tab_preview) if hasattr(self, "tabs") else None

        # update KPI card
        ds_label = summary.get("original_filename") or str(summary.get("dataset_id") or "—")
        total_rows = summary.get("rows") or (len(self.current_df) if self.current_df is not None else 0)
        total_cols = len(summary.get("columns") or (list(self.current_df.columns) if self.current_df is not None else []))
        numeric_list = numeric or []
        self.update_kpis(dataset_label=ds_label, rows=total_rows, cols=total_cols, numeric=numeric_list)

        QMessageBox.information(self, "Summary loaded", f"Loaded summary for {summary.get('dataset_id')}")

    def update_kpis(self, dataset_label="—", rows=0, cols=0, numeric=None):
        self.kpi_dataset.setText(f"<b>Dataset:</b> {dataset_label}")
        self.kpi_rows.setText(f"<b>Rows:</b> {rows}")
        self.kpi_cols.setText(f"<b>Columns:</b> {cols}")
        numeric = numeric or []
        ntext = ", ".join(numeric[:5]) + (", ..." if len(numeric) > 5 else "") if numeric else "—"
        self.kpi_numeric.setText(f"<b>Numeric:</b> {ntext}")

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
            self.canvas.draw_idle()
        except Exception:
            try:
                self.canvas.draw()
            except Exception as e:
                print("Plot draw error:", e)

    # -----------------
    # Report download (keeps your robust resolver & auto-upload fallback)
    # -----------------
    def generate_report(self):
        if not self.current_summary:
            QMessageBox.warning(self, "No dataset", "Load a dataset summary first.")
            return

        self.progress.setVisible(True)
        self.progress.setValue(5)

        import re
        def try_extract_id_from_url(url):
            if not url or not isinstance(url, str):
                return None
            m = re.search(r"/api/datasets/(\d+)[/|$]", url)
            if m:
                return int(m.group(1))
            m2 = re.search(r"/datasets/(\d+)[/|$]", url)
            if m2:
                return int(m2.group(1))
            return None

        def resolve_dataset_id(summary):
            did = summary.get("id")
            if isinstance(did, int):
                return did
            dsid = summary.get("dataset_id")
            if isinstance(dsid, str) and dsid.isdigit():
                return int(dsid)
            for key in ("file", "file_url", "url", "summary_url"):
                val = summary.get(key)
                if val:
                    ext = try_extract_id_from_url(val)
                    if ext:
                        return ext
            rv = summary.get("raw_preview")
            if isinstance(rv, list) and rv:
                row0 = rv[0]
                for k in ("file", "file_url", "url"):
                    if k in row0:
                        ext = try_extract_id_from_url(row0[k])
                        if ext:
                            return ext
            try:
                hist = get_history()
                if isinstance(hist, list):
                    for entry in hist:
                        if not entry:
                            continue
                        if entry.get("id") and (entry.get("original_filename") == summary.get("original_filename") or entry.get("original_filename") == summary.get("dataset_id")):
                            return entry.get("id")
                        if summary.get("original_filename") and entry.get("original_filename") == summary.get("original_filename"):
                            return entry.get("id")
                        fname = summary.get("dataset_id") or summary.get("original_filename")
                        if fname and entry.get("file") and entry["file"].endswith(fname):
                            return entry.get("id")
                        if entry.get("dataset_id") and entry.get("dataset_id") == summary.get("dataset_id"):
                            return entry.get("id")
            except Exception:
                pass
            return None

        dataset_id = resolve_dataset_id(self.current_summary)

        if not dataset_id:
            local_path = None
            try:
                local_path = self.lbl_file.text()
                if local_path and os.path.exists(local_path):
                    self.progress.setValue(15)
                    def _after_upload(res):
                        self.progress.setValue(60)
                        new_id = None
                        if isinstance(res, dict):
                            new_id = res.get("dataset_id") or res.get("id")
                            if isinstance(new_id, str) and new_id.isdigit():
                                new_id = int(new_id)
                        if new_id:
                            def _done_report(p):
                                self.progress.setVisible(False)
                                if not p or not os.path.exists(p):
                                    QMessageBox.warning(self, "Report", "Failed to download report after upload.")
                                    return
                                try:
                                    webbrowser.open_new(f"file://{p}")
                                    QMessageBox.information(self, "Report", f"Opened report: {p}")
                                except Exception as e:
                                    QMessageBox.information(self, "Report saved", f"Report saved at {p}\n{e}")

                            def _err_report(exc):
                                self.progress.setVisible(False)
                                QMessageBox.critical(self, "Report error", f"{str(exc)}\n\n{getattr(exc,'_traceback','')}")

                            self._start_thread(download_report, _done_report, _err_report, new_id)
                        else:
                            self.progress.setVisible(False)
                            QMessageBox.warning(self, "Report", "Auto-upload succeeded but backend did not return dataset id.")
                    self._start_thread(upload_file, _after_upload, lambda e: (self.progress.setVisible(False), QMessageBox.critical(self, "Upload error", str(e))), local_path)
                    return
            except Exception:
                pass

        if not dataset_id:
            self.progress.setVisible(False)
            debug_msg = "Could not determine dataset id for report.\n\n"
            debug_msg += "Summary keys: " + ", ".join(list(self.current_summary.keys())) + "\n"
            debug_msg += "Try: load dataset from History or Upload the CSV first.\n"
            QMessageBox.critical(self, "Report", debug_msg)
            return

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

        self._start_thread(download_report, _on_done, _on_err, dataset_id)

    # -----------------
    # Safe cleanup on close
    # -----------------
    def closeEvent(self, event):
        try:
            for th in list(self.threads):
                try:
                    running = False
                    try:
                        running = th.isRunning()
                    except Exception:
                        running = False
                    if running:
                        try:
                            th.quit()
                        except Exception:
                            pass
                        try:
                            th.wait(2000)
                        except Exception:
                            pass
                    else:
                        try:
                            th.quit()
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

        try:
            if hasattr(self, "canvas") and self.canvas is not None:
                try:
                    self.canvas.close()
                except Exception:
                    pass
        except Exception:
            pass

        super().closeEvent(event)
