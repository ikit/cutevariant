from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


from .plugin import QueryPluginWidget
from cutevariant.core import Query
from cutevariant.core import sql
from cutevariant.gui.ficon import FIcon


#=================== SELECTION MODEL ===========================
class SelectionQueryModel(QAbstractTableModel):
    """
    This model store all selection from sqlite table selection . 

    Usage: 

        model = SelectionQueryModel()
        model.query = query 
        model.load() 

    """
    def __init__(self):
        super().__init__()
        self._query = None
        self.records = []

    def rowCount(self, parent = QModelIndex()):
        """ overloaded from QAbstractTableModel """
        return len(self.records) 

    def columnCount(self, parent = QModelIndex()):
        """ overloaded from QAbstractTableModel """
        return 2 # value and count 


    def data(self, index: QModelIndex(), role = Qt.DisplayRole):
        """ overloaded from QAbstractTableModel """

        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return self.records[index.row()]["name"]
        
            if index.column() == 1:
                return self.records[index.row()]["count"]

        return None

    def headerData(self, section, orientation, role = Qt.DisplayRole):
        """ overloaded from QAbstractTableModel """

        if not self.records:
            return 

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return "selection"
            if section == 1:
                return "count"

        if orientation == Qt.Vertical and role == Qt.DisplayRole and section > 0:
            return self.records[section]["id"] # For debug purpose . displayed in vertical header


    def record(self, index: QModelIndex()):
        """
        Return Selection records ny index 
        """
        if not index.isValid():
            return None 
        return self.records[index.row()]

    def find_record(self, name: str):
        """
        Find a record by name
        @see: view.selectionModel()
        """ 
        for idx, record in enumerate(self.records):
            if record["name"] == name:
                return idx
        return None

    def remove_record(self, index: QModelIndex()):

            self.beginRemoveRows(QModelIndex(), index.row(), index.row())
            record = self.records.pop(index.row())
            sql.delete_selection(self.query.conn, record["id"])
            self.endRemoveRows()

    def edit_record(self, index, record : dict):
        sql.edit_selection(self.query.conn, record)
        self.dataChanged.emit(index,index)


    @property
    def query(self):
        return self._query

    @query.setter
    def query(self, query: Query):
        self._query = query

    def load(self):
        """
        Load selections into the model
        """
        self.beginResetModel()
        self.records.clear()
        self.records.append({"name":"all", "count": "   "}) # TODO => Must be inside the selection table 
        self.records += list(sql.get_selections(self._query.conn))
        self.endResetModel()

    def save_current_query(self, name):
        """
        Save current query as a new selection and reload the model
        """
        self.query.create_selection(name)
        self.load()

#=================== SELECTION VIEW ===========================

class SelectionQueryWidget(QueryPluginWidget):
    """
    This widget display the list of avaible selection. 
    User can select one of them to update Query::selection 

    """
    def __init__(self):
        super().__init__()

        self.setWindowTitle(self.tr("Selections"))

        self.model = SelectionQueryModel()
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.horizontalHeader().hide()
        #self.view.horizontalHeader().setStretchLastSection(True)

        self.view.verticalHeader().show()
        self.view.verticalHeader().setDefaultSectionSize(26)
        self.view.setShowGrid(False)
        self.view.setAlternatingRowColors(True)

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.setLayout(layout)

        # call on_current_row_changed when item selection changed 
        self.view.selectionModel().currentRowChanged.connect(self.on_current_row_changed)


    def load(self):
        """ Load selection model and update the view """ 
        self.view.selectionModel().blockSignals(True)
        self.model.load()
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch )
        self.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents )

        # Select record according query.selection 
        row = self.model.find_record(self.query.selection)
        if row is not None:
            self.view.selectRow(row)


        self.view.selectionModel().blockSignals(False)



    def on_change_query(self):
        """ 
        Method override from AbstractQueryWidget
        """
        self.load()


    def on_init_query(self):
        """ 
        Method override from AbstractQueryWidget
        """
        self.model.query = self.query


    def on_current_row_changed(self, index):
        
        self.query.selection = self.model.record(index)["name"]
        self.query_changed.emit()



    def save_current_query(self):

        name, success = QInputDialog.getText(
            self, "type a name for selection", "Selection name:", QLineEdit.Normal
        )

        if success:
            self.model.save_current_query(name)


    def contextMenuEvent(self, event: QContextMenuEvent):
        """
        Overrided
        """

        current_index = self.view.currentIndex()
        record = self.model.record(current_index)

        menu = QMenu()

        menu.addAction(FIcon(0xf8ff),"Edit", self.edit_selection)

        menu.addMenu(self._create_set_operation_menu(FIcon(0xf55d),"Intersect with ..."))
        menu.addMenu(self._create_set_operation_menu(FIcon(0xf55b),"Difference with ..."))
        menu.addMenu(self._create_set_operation_menu(FIcon(0xf564),"Union with ..."))
        

        menu.addSeparator()
        menu.addAction(FIcon(0xf413),"Remove", self.remove_selection)
        
        menu.exec_(event.globalPos())




    def _create_set_operation_menu(self,icon, menu_name):
        menu = QMenu(menu_name)
        menu.setIcon(icon)

        current_index = self.view.selectionModel().currentIndex()

        for selection in sql.get_selections(self.query.conn):
            if self.model.record(current_index)["name"] != selection["name"]:
                action = menu.addAction(selection["name"])


        return menu


    def _make_set_operation(self):
        action = self.sender()

        #current_selection = self.model.record(self.view.selectionModel().currentIndex())[0]




    def remove_selection(self):
        
        msg = QMessageBox()
        msg.setText(self.tr("Are you sure you want to remove this selection ? "))
        msg.setStandardButtons(QMessageBox.Yes|QMessageBox.No)

        if msg.exec_() == QMessageBox.Yes:
            for index in self.view.selectionModel().selectedRows():
                self.model.remove_record(index)


    def edit_selection(self):

        current_index = self.view.selectionModel().currentIndex()
        new_name = QInputDialog.getText(self,"get new name", "name")
        if new_name[1] and current_index:
            old_record = self.model.record(current_index)
            old_record["name"] = new_name[0]
            print("old record", old_record)
            self.model.edit_record(current_index,old_record)