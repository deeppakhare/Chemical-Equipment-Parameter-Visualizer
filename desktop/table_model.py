# desktop/table_model.py
from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant

class DataFrameModel(QAbstractTableModel):
    """
    Minimal QAbstractTableModel to display a pandas DataFrame in QTableView.
    """
    def __init__(self, df=None, parent=None):
        super().__init__(parent)
        self._df = df

    def setDataFrame(self, df):
        self.beginResetModel()
        self._df = df
        self.endResetModel()

    def rowCount(self, parent=None):
        return 0 if self._df is None else len(self._df.index)

    def columnCount(self, parent=None):
        return 0 if self._df is None else len(self._df.columns)

    def data(self, index, role=Qt.DisplayRole):
        if self._df is None or not index.isValid():
            return QVariant()
        value = self._df.iat[index.row(), index.column()]
        if role == Qt.DisplayRole:
            # Convert NaN to empty string for nicer display
            if value is None:
                return ""
            try:
                return str(value)
            except Exception:
                return repr(value)
        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if self._df is None:
            return QVariant()
        if role != Qt.DisplayRole:
            return QVariant()
        if orientation == Qt.Horizontal:
            return str(self._df.columns[section])
        else:
            return str(self._df.index[section])
