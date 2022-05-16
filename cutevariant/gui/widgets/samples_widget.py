import sqlite3
from PySide6.QtWidgets import (
    QTabWidget,
    QTableView,
    QWidget,
    QDialog,
    QApplication,
    QLineEdit,
    QAbstractItemView,
    QSizePolicy,
    QVBoxLayout,
    QToolBar,
    QSplitter,
    QDialogButtonBox,
)
from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    Signal,
    Slot,
    QStringListModel,
    Qt,
    QSize,
)
from PySide6.QtGui import QAction, QIcon, QFont

from cutevariant.core import sql
from cutevariant.gui.widgets import ChoiceWidget, create_widget_action
from cutevariant.gui.style import (
    SAMPLE_CLASSIFICATION,
)

from cutevariant.config import Config
from cutevariant.gui.ficon import FIcon


class SamplesModel(QAbstractTableModel):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self._data = []
        self._headers = ["name", "family", "Statut", "Tags"]
        self.name_filter = ""
        self.fam_filter = []
        self.tag_filter = []
        self.valid_filter = []

        self.conn = conn

    def rowCount(self, parent=QModelIndex()):
        """override"""
        if parent == QModelIndex():
            return len(self._data)
        return 0

    def columnCount(self, parent=QModelIndex()):
        """override"""
        if parent == QModelIndex():
            return len(self._headers)

        return 0

    def data(self, index: QModelIndex, role: Qt.ItemDataRole):

        if not index.isValid():
            return
        if role == Qt.DisplayRole:
            sample = self._data[index.row()]
            if index.column() == 0:
                return sample["name"]

            if index.column() == 1:
                return sample["family_id"]

            if index.column() == 2:
                return SAMPLE_CLASSIFICATION.get(sample["classification"])["name"]

            if index.column() == 3:
                return sample["tags"]

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]

    def load(self):
        if self.conn:
            self.beginResetModel()
            self._data = list(
                sql.search_samples(
                    self.conn,
                    self.name_filter,
                    families=self.fam_filter,
                    tags=self.tag_filter,
                    classifications=self.valid_filter,
                )
            )
            self.endResetModel()

    def get_sample(self, row: int):
        return self._data[row]


## Second Tab
class SelectionDialog(QDialog):

    selection_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__()

        self.toolbar = QToolBar()
        self.model = QStringListModel()
        self.view = QTableView()
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.horizontalHeader().hide()
        self.view.setShowGrid(False)
        self.view.verticalHeader().hide()
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.setModel(self.model)
        v_layout = QVBoxLayout(self)
        v_layout.addWidget(self.toolbar)

        v_layout.addWidget(self.view)
        self._setup_actions()

        self.setWindowTitle(self.tr("Selected sample(s)"))

    def _setup_actions(self):
        sep = QWidget()
        sep.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.toolbar.addAction(QIcon(), "Remove selection(s)", self._on_remove)
        self.toolbar.addWidget(sep)
        self.toolbar.addAction(QIcon(), "Clear all", self._on_clear)

    def set_samples(self, samples):
        previous = set(self.model.stringList())

        samples = set(samples).union(previous)

        self.model.setStringList(samples)
        self.selection_changed.emit(self.model.rowCount())

    def get_samples(self):
        return self.model.stringList()

    def _on_remove(self):
        names = self.model.stringList()

        for index in self.view.selectionModel().selectedRows():
            del names[index.row()]

        self.model.setStringList(names)
        self.selection_changed.emit(self.model.rowCount())

    def _on_clear(self):
        self.model.setStringList([])
        self.selection_changed.emit(self.model.rowCount())


class SamplesWidget(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__()

        self.toolbar = QToolBar()
        self.line = QLineEdit()
        self.line.setPlaceholderText("Search sample ...")
        self.line.textChanged.connect(self._on_search)

        self.model = SamplesModel(conn)

        self.selection_dialog = SelectionDialog()
        self.selection_dialog.selection_changed.connect(self._update_count)

        self.view = QTableView()
        self.view.verticalHeader().hide()
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.view.setModel(self.model)

        # Filters
        self.family_choice = ChoiceWidget()
        self.family_choice.accepted.connect(self._on_search)
        self.statut_choice = ChoiceWidget()
        self.statut_choice.accepted.connect(self._on_search)
        self.tag_choice = ChoiceWidget()
        self.tag_choice.accepted.connect(self._on_search)

        v_layout = QVBoxLayout(self)
        v_layout.addWidget(self.toolbar)
        v_layout.addWidget(self.line)
        v_layout.addWidget(self.view)

        self._setup_actions()

        self.view.doubleClicked.connect(self._on_add_selection)

        self.conn = None

    def get_selected_samples(self):
        return self.selection_dialog.get_samples()

    def set_selected_samples(self, samples: list):
        self.selection_dialog.set_samples(samples)

    def _setup_actions(self):

        family_action = create_widget_action(self.toolbar, self.family_choice)
        family_action.setText("Family")
        statut_action = create_widget_action(self.toolbar, self.statut_choice)
        statut_action.setText("Statut")
        tag_action = create_widget_action(self.toolbar, self.tag_choice)
        tag_action.setText("Tags")
        self.toolbar.addSeparator()
        clear_action = self.toolbar.addAction(QIcon(), "Clear filters", self.clear_filters)

        # separator
        sep = QWidget()
        sep.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(sep)
        self.add_button = self.toolbar.addAction("Add To Selection")
        self.add_button.setIcon(FIcon(0xF0415))
        self.add_button.setToolTip(self.tr("Add selections to basket"))
        self.add_button.triggered.connect(self._on_add_selection)
        self.basket_button = self.toolbar.addAction("Selected samples")
        self.basket_button.setToolTip(self.tr("Show selected samples"))
        self.basket_button.setIcon(FIcon(0xF0076))
        self.basket_button.triggered.connect(self._on_basket_clicked)
        # self.toolbar.widgetForAction(self.basket_button).setAutoRaise(False)

        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

    def _load_filters(self):
        if self.conn:
            # Load family
            self.family_choice.clear()
            for fam in sql.get_samples_family(self.conn):
                self.family_choice.add_item(QIcon(), fam, data=fam)

            # Load Status
            self.statut_choice.clear()
            for key, value in SAMPLE_CLASSIFICATION.items():
                self.statut_choice.add_item(QIcon(), value["name"], data=key)

            # Load Tags
            self.tag_choice.clear()
            config = Config("samples")
            tags = config.get("tags", [])
            for tag in tags:
                self.tag_choice.add_item(QIcon(), tag["name"], data=tag["name"])

    def clear_filters(self):
        self.tag_choice.uncheck_all()
        self.family_choice.uncheck_all()
        self.statut_choice.uncheck_all()
        self._on_search()

    def _on_search(self):
        """Start a search query"""
        self.model.name_filter = self.line.text()

        tags = [i["data"] for i in self.tag_choice.selected_items()]
        fam = [i["data"] for i in self.family_choice.selected_items()]
        val = [i["data"] for i in self.statut_choice.selected_items()]

        self.model.tag_filter = tags
        self.model.fam_filter = fam
        self.model.valid_filter = val

        self.model.load()

    def _on_add_selection(self):

        samples = [
            self.model.get_sample(i.row())["name"]
            for i in self.view.selectionModel().selectedRows()
        ]

        self.selection_dialog.set_samples(samples)

    def _update_count(self):
        count = len(self.selection_dialog.get_samples())
        self.basket_button.setText(f"{count} Selected sample(s)")
        # font = QFont()
        # font.setBold(count > 0)
        # self.basket_button.setFont(font)

    @property
    def conn(self):
        return self.model.conn

    @conn.setter
    def conn(self, conn):
        self.model.conn = conn
        self.model.load()
        self._load_filters()

    def _on_basket_clicked(self):

        self.selection_dialog.exec()


class SamplesDialog(QDialog):
    def __init__(self, conn, parent=None):
        super().__init__(parent)

        self.w = SamplesWidget(conn)
        self.w.conn = conn

        self.btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)

        self.btn_box.buttons()[0].setFlat(False)

        v_layout = QVBoxLayout(self)
        v_layout.addWidget(self.w)
        v_layout.addWidget(self.btn_box)
        self.resize(800, 400)

        self.setWindowTitle(self.tr("Select sample(s)"))

    def set_samples(self, samples: list):
        self.w.set_selected_samples(samples)

    def get_samples(self):
        return self.w.get_selected_samples()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection("/home/sacha/test.db")

    w = SamplesDialog(conn)
    w.set_samples(["Sample1"])
    w.exec()

    print(w.get_samples())

    app.exec()
