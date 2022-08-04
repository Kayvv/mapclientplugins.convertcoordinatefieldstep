import webbrowser

from PySide2 import QtWidgets, QtCore

from mapclientplugins.convertcoordinatefieldstep.view.ui_convertcoordinatefields import Ui_ConvertCoordinateFieldWidget


class ConvertCoordinateFieldsView(QtWidgets.QWidget):

    def __init__(self, model, parent=None):
        super(ConvertCoordinateFieldsView, self).__init__(parent)
        self._ui = Ui_ConvertCoordinateFieldWidget()
        self._ui.setupUi(self)
        self._done_callback = None

        self._model = model

        self._ui.comboBoxFilterFields.addItems(self._model.get_group_fields())
        group_field = self._model.get_group_field()
        if group_field is not None:
            self._ui.comboBoxFilterFields.setCurrentText(group_field)
        self._ui.tableViewCoordinateFields.setModel(self._model.get_coordinate_field_model())
        self._ui.tableViewCoordinateFields.setItemDelegateForColumn(2, ComboBoxDelegate())
        self._make_connections()

    def _make_connections(self):
        self._ui.pushButtonDocumentation.clicked.connect(self._documentationButtonClicked)
        self._ui.pushButtonDone.clicked.connect(self._done_button_clicked)
        self._ui.comboBoxFilterFields.activated.connect(self._filter_field_changed)

    def _filter_field_changed(self, current_index):
        current_text = self._ui.comboBoxFilterFields.currentText()
        self._model.set_group_field(current_text)

    def _documentationButtonClicked(self):
        webbrowser.open("https://abi-mapping-tools.readthedocs.io/en/latest/mapclientplugins.convertcoordinatefieldstep/docs/index.html")

    def _done_button_clicked(self):
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self._model.done()
        QtWidgets.QApplication.restoreOverrideCursor()
        self._done_callback()

    def register_done_execution(self, callback):
        self._done_callback = callback


class ComboBoxDelegate(QtWidgets.QStyledItemDelegate):

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)
        editor.setFrame(False)
        editor.addItems(index.model().potential_conversions())

        return editor

    # def setEditorData(self, editor, index):
    #     data = index.model().data()
    #     if data is not None:
    #         editor.clear()
    #         editor.insertItems(0, data)
    #         cell_data = index.model().data(index, QtCore.Qt.DisplayRole)
    #         editor.setCurrentText(cell_data)

    # def setModelData(self, editor, model, index):
    #     value = editor.currentText()
    #     model.setData(index, value, QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

