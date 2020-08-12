from PySide2.QtCore import (
    Qt,
    QAbstractTableModel,
    QAbstractItemModel,
    QModelIndex,
    Property,
)

from PySide2.QtWidgets import (
    QTableView,
    QItemDelegate,
    QWidget,
    QStyleOptionViewItem,
    QComboBox,
)

import tempfile


class PedModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()

        self.samples_data = []
        self.headers = (
            "Family",
            "Sample",
            "Father_id",
            "Mother_id",
            "Sexe",
            "Phenotype",
        )

        self.sex_map = {"1": "Male", "2": "Female", "0": ""}

        self.phenotype_map = {"1": "Unaffected", "2": "Affected", "0": ""}

    def rowCount(self, index=QModelIndex()):
        """ override """
        return len(self.samples_data)

    def columnCount(self, index=QModelIndex()):
        """ override """
        if index == QModelIndex():
            return len(self.headers)

        return 0

    def get_data_list(self, column: int):
        return list(set([i[column] for i in self.samples_data]))

    def clear(self):
        self.beginResetModel()
        self.samples_data.clear()
        self.endResetModel()

    def from_pedfile(self, filename: str):
        samples = []
        self.beginResetModel()
        self.samples_data.clear()
        with open(filename, "r") as file:
            for line in file:
                row = line.strip().split("\t")
                self.samples_data.append(row)

        self.endResetModel()

    def to_pedfile(self, filename: str):

        with open(filename, "w") as file:
            for sample in self.samples_data:
                file.write("\t".join(sample) + "\n")

    def set_samples(self, samples: list):
        """ fill model """
        self.beginResetModel()
        self.samples_data.clear()
        for sample in samples:
            self.samples_data.append(sample)
        self.endResetModel()

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        """ overrided """
        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.EditRole:
            value = self.samples_data[index.row()][index.column()]

            if index.column() == 3 or index.column() == 2:  # parent
                return value if value != "0" else ""

            if index.column() == 4:  # Sexe
                return self.sex_map.get(value, "")

            if index.column() == 5:  # Phenotype
                return self.phenotype_map.get(value, "")

            return value

        return None

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        """ overrided """

        if not index.isValid():
            return None

        if role == Qt.EditRole:
            self.samples_data[index.row()][index.column()] = value
            return True

        return False

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: Qt.DisplayRole
    ):
        """ overrided """
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self.headers[section]

        return None

    def flags(self, index: QModelIndex):
        """ overrided """
        if not index.isValid():
            return None

        if index.column() > 0:
            return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled

        return Qt.ItemIsSelectable | Qt.ItemIsEnabled


class PedDelegate(QItemDelegate):
    def createEditor(
        self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ):

        # index.model refer to SampleModel

        if index.column() < 2:
            return super().createEditor(parent, option, index)

        widget = QComboBox(parent)
        if index.column() == 2 or index.column() == 3:  # father_id or mother_id
            widget.addItems(
                [""] + index.model().get_data_list(0)
            )  #  Fill with sample name
            return widget

        if index.column() == 4:  #  sexe
            widget.addItem("Male", "1")
            widget.addItem("Female", "2")
            widget.addItem("", "0")
            return widget

        if index.column() == 5:
            widget.addItem("Unaffected", "1")
            widget.addItem("Affected", "2")
            widget.addItem("", "0")
            return widget

        return super().createEditor(parent, option, index)

    def setModelData(
        self, editor: QWidget, model: QAbstractItemModel, index: QModelIndex
    ):

        if type(editor) == QComboBox:
            model.setData(index, editor.currentData())
            return

        return super().setModelData(editor, model, index)


class PedView(QTableView):
    def __init__(self):
        super().__init__()
        self.model = PedModel()
        self.delegate = PedDelegate()
        self.setModel(self.model)
        self.horizontalHeader().setStretchLastSection(True)
        self.setAlternatingRowColors(True)
        self.verticalHeader().hide()
        self.setItemDelegate(self.delegate)

    def clear(self):
        self.model.clear()

    def set_samples(self, data):
        self.model.set_samples(data)

    def get_samples(self):
        return self.model.samples_data

    def get_pedfile(self):
        outfile = tempfile.mkstemp(suffix=".ped", text=True)[1]
        self.model.to_pedfile(outfile)
        return outfile

    # Create property binding for QWizardPage.registerFields
    samples = Property(list, get_samples, set_samples)
    pedfile = Property(str, get_pedfile)
