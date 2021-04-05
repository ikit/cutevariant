# Standard imports
import typing
import glob
import json
import os

# Qt imports
from PySide2.QtCore import Qt, QAbstractTableModel, QDateTime, QSettings, QDir, QUrl
from PySide2.QtWidgets import (
    QToolBar,
    QVBoxLayout,
    QApplication,
    QFileDialog,
    QMessageBox,
    QTableView,
)

from PySide2.QtGui import QDesktopServices

# Custom imports
from cutevariant.gui import style, plugin, FIcon, MainWindow
from cutevariant.core.querybuilder import build_vql_query
from cutevariant.commons import logger

from cutevariant.core import sql


LOGGER = logger()


class HistoryModel(QAbstractTableModel):

    HEADERS = ["time", "count", "query", "tags"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.records = []

    def rowCount(self, parent: QModelIndex) -> int:
        """ override """
        return len(self.records)

    def columnCount(self, parent: QModelIndex) -> int:
        """ override """
        return 4

    def data(self, index: QModelIndex, role):
        """ override """

        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            if index.column() == 0:
                # The time for the query
                return self.records[index.row()][0].toString("hh:mm:ss")
            if index.column() == 1:
                # The number of variants for this query
                return str(self.records[index.row()][1])
            if index.column() == 2:
                # The query itself
                return self.records[index.row()][2]
            if index.column() == 3:
                # The tags for this query
                return self.records[index.row()][3]

        if role == Qt.EditRole:
            if index.column() == 3:
                return self.records[index.row()][3]

        if role == Qt.ToolTipRole:
            return self.records[index.row()][3]

        return None

    def setData(self, index, value, role=Qt.EditRole):
        if index.column() == 3:
            self.records[index.row()][3] = value
            return True
        else:
            return False

    def flags(self, index):
        base_flags = super().flags(index)
        if index.column() == 3:
            return base_flags | Qt.ItemIsEditable
        else:
            return base_flags

    def headerData(self, section: int, orientation: Qt.Orientation, role):
        """ override """

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return HistoryModel.HEADERS[section]

        return None

    def add_record(
        self, query: str, count: int, time: QDateTime = None, tags: str = None
    ):
        """Add a record into the model

        Args:
            query (str): A VQL query
            count (int): the total count of variant returns by the VQL query
            time (QDateTime): the date and time of the query, leave it to None if you want it set automatically
            tags (str): the tags associated with this query
        """

        if not time:
            time = QDateTime.currentDateTime()

        if not tags:
            tags = ""

        self.beginInsertRows(QModelIndex(), 0, 0)
        self.records.insert(0, [time, count, query, tags])
        self.endInsertRows()

    def load_from_csv(self, file_name):

        with open(file_name) as device:
            lines = device.readlines()

            # Will append the lines from the file to the existing ones
            prev_row_count = self.rowCount(QModelIndex())

            self.beginInsertRows(
                QModelIndex(), prev_row_count, prev_row_count + len(lines) - 1
            )

            for line in lines:
                # So we don't get empty lines in our CSV !
                line = line.strip()
                # \t is the perfect separator: one cannot accidentally create a tag with a tabulation in it (at least not from a tableview)
                time, count, query, *_ = line.split("\t")

                # Avoid type error when trying to sort counts between loaded counts and actual counts...
                count = int(count)

                # Just a hack to allow tag (last column) to be optional. Store it in the _ python garbage-like variable
                tag = _[0] if _ else ""

                if time.isnumeric():
                    time = QDateTime.fromSecsSinceEpoch(int(time))
                else:
                    time = QDateTime.currentDateTime()
                self.records.append([time, count, query, tag])

            # TODO Call sort on the model after insertion (to sort by date)
            self.endInsertRows()

    def load_from_json(self, file_name):
        QMessageBox.information(
            self,
            self.tr("Easter egg..."),
            self.tr("A JSON file ? Fine, as you wish... You're the user after all..."),
        )
        with open(file_name) as device:
            records = json.load(device)

            self.beginInsertRows(
                QModelIndex(), prev_row_count, prev_row_count + len(lines)
            )

            # records is a python array from a JSON one. Each record in it has the four keys of the four columns of our model
            for record in records:
                # Get the time of query from this record (defaults to current time)
                time = record.get("time", QDateTime().currentDateTime())
                if isinstance(time, str):
                    if time.isnumeric():
                        time = QDateTime.fromSecsSinceEpoch(int(time))
                count = record.get("count", 0)
                query = records.get("query", "")
                tag = records.get("tags", "")
                self.records.append([time, count, query, tag])

            self.endInsertRows()

    def save_to_csv(self, file_name):
        print("Saving CSV to ", file_name)
        with open(file_name, "w+") as device:
            for record in self.records:
                time, count, query, tags = record

                # In self.records, time (first column) is a QDateTime. So we need to convert it to a string to store it
                time = str(time.toSecsSinceEpoch())
                device.write("\t".join([time, str(count), query, tags]) + "\n")

    def save_to_json(self, file_name):
        root = []
        for record in self.records:
            time, count, query, tags = record

            # In self.records, time (first column) is a QDateTime. So we need to convert it to a string to store it
            time = str(time.toSecsSinceEpoch())
            root.append({"time": time, "count": count, "query": query, "tags": tags})

        with open(file_name, "w+") as device:
            json.dump(root, device)

    def clear_records(self):
        """Clear records from models"""
        self.beginResetModel()
        self.records.clear()
        self.endResetModel()

    def get_record(self, index: QModelIndex):
        """ Return record corresponding to the model index """
        return self.records[index.row()]

    def sort(self, column, order=Qt.AscendingOrder):
        """
        Only sort on columns 0 (request time) and 1 (variants count returned by the request)
        """

        if column <= 1:
            self.beginResetModel()
            self.records.sort(
                key=lambda record: record[column], reverse=(order == Qt.AscendingOrder)
            )
            self.endResetModel()
        else:
            return


class VqlHistoryWidget(plugin.PluginWidget):
    """Exposed class to manage VQL/SQL queries from the mainwindow"""

    LOCATION = plugin.FOOTER_LOCATION
    ENABLE = True
    REFRESH_ONLY_VISIBLE = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("VQL Editor"))

        # Create model / view
        self.view = QTableView()
        self.model = HistoryModel()
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.verticalHeader().hide()
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setSortingEnabled(True)

        self.project_dir = ""

        self.view.doubleClicked.connect(self.on_double_clicked)
        #  Create toolbar
        self.toolbar = QToolBar()
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.toolbar.addAction(
            FIcon(0xF0413), self.tr("Clear"), self.model.clear_records
        )

        self.toolbar.addAction(
            FIcon(0xF02FA),
            self.tr("Load history from file (will append)"),
            self.on_load_logs_pressed,
        )

        self.toolbar.addAction(
            FIcon(0xF0256),
            self.tr("Open project directory"),
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.project_dir))
            if self.project_dir
            else QMessageBox.information(
                self, self.tr("Info"), self.tr("No project opened")
            ),
        )

        # Create layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.view)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(main_layout)

    def on_register(self, mainwindow: MainWindow):
        mainwindow.variants_count_loaded.connect(self.on_variant_count)

    def on_variant_count(self, count: int):
        vql_query = build_vql_query(
            self.mainwindow.state.fields,
            self.mainwindow.state.source,
            self.mainwindow.state.filters,
            self.mainwindow.state.group_by,
            self.mainwindow.state.having,
        )

        self.model.add_record(vql_query, count)

    def on_open_project(self, conn):
        """ override """
        self.conn = conn
        full_path = sql.get_database_file_name(conn)

        # Get the project absolute directory
        self.project_dir = os.path.dirname(full_path)

        # Get the project name without the extension
        project_name = os.path.basename(full_path).split(".")[0]

        # Look for logs in the project directory, with name starting with log and containing the project name
        history_logs = glob.glob(f"{self.project_dir}/log*{project_name}*.*")
        for log in history_logs:
            print(log)
            try:
                if log.endswith("csv"):
                    self.model.load_from_csv(log)
                if log.endswith("json"):
                    self.model.load_from_json(log)
            except Exception as e:
                QMessageBox.warning(
                    self,
                    self.tr("Warning"),
                    self.tr(f"Could not open VQL history ! Full exception below\n{e}"),
                )
                continue

    def on_close(self):
        """ override """

        full_path = sql.get_database_file_name(self.conn)

        # Get the project absolute directory
        project_dir = os.path.dirname(full_path)

        # Get the project name without the extension
        project_name = os.path.basename(full_path).split(".")[0]

        log_file_name = f"{project_dir}/log_{project_name}.csv"
        self.model.save_to_csv(log_file_name)

        super().on_close()

    def on_refresh(self):
        """"""
        pass

    def on_double_clicked(self, index: QModelIndex):
        """triggered when history record is clicked

        Args:
            index (QModelIndex): index
        """
        _, _, query, _ = self.model.get_record(index)
        parsed_query = next(vql.parse_vql(query))
        print(parsed_query)

        self.mainwindow.state.fields = parsed_query["fields"]
        self.mainwindow.state.source = parsed_query["source"]
        self.mainwindow.state.filters = parsed_query["filters"]
        self.mainwindow.state.group_by = parsed_query["group_by"]
        self.mainwindow.state.having = parsed_query["having"]

        self.mainwindow.refresh_plugins(sender=self)

    def on_load_logs_pressed(self):
        """
        Called whenever you'd like the user to load a log file into the query history.
        This feature can be useful if you'd like to share your queries with other users
        """
        settings = QSettings()

        # When asking for a log file to load, try to remember where it was last time
        log_dir = settings.value(
            f"{self.mainwindow.state.project_file_name}/latest_log_dir", QDir.homePath()
        )

        # Ask for a file name to load the log from
        file_name = QFileDialog.getOpenFileName(
            self,
            self.tr("Please select the file you want to load the log from"),
            log_dir,
            self.tr("Log file (*.csv *.json)"),
        )[0]

        # Load the file into the model, according to the extension
        if file_name.endswith("csv"):
            self.model.load_from_csv(file_name)
        if file_name.endswith("json"):
            self.model.load_from_json(file_name)

        # Remember where we just loaded from last time
        settings.setValue(
            f"{self.mainwindow.state.project_file_name}/latest_log_dir",
            os.path.dirname(file_name),
        )


if __name__ == "__main__":

    import sys
    import sqlite3

    app = QApplication(sys.argv)

    conn = sqlite3.connect("/home/sacha/Dev/cutevariant/examples/test.db")

    view = VqlHistoryWidget()
    view.show()

    app.exec_()
