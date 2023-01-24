import hashlib
import json
import os.path

from PySide6 import QtCore

from mapclientplugins.convertcoordinatefieldstep.model.converter import Converter


NOT_FIELD_TYPES_LIST = ["Name", "CoordinateSystemType", "IsManaged", "IsTypeCoordinate"]


def _field_type(field_info):
    keys = field_info.keys()
    for key in keys:
        if key not in NOT_FIELD_TYPES_LIST:
            return key

    return "<unkonwn>"


def _conversion_possibilities(field_info):
    return list(set(([f["Name"] for f in field_info])))


class CoordinateFieldsModel(QtCore.QAbstractTableModel):

    def __init__(self, field_info, field_conversions=None, parent=None):
        super(CoordinateFieldsModel, self).__init__(parent)
        self._headers = ['Source Field', 'Field Type', 'Re-evaluate In']
        self._field_info = field_info
        self._potential_conversions = _conversion_possibilities(field_info)
        self._field_conversions = [None] * len(field_info) if field_conversions is None else field_conversions
        self._row_count = len(field_info)

    def potential_conversions(self):
        return self._potential_conversions

    def _info_for(self, field_name):
        info_list = [info for info in self._field_info if info["Name"] == field_name]
        return info_list[0]

    def field_conversions(self):
        return self._field_conversions

    def conversions(self):
        conversions = []
        for index, info in enumerate(self._field_info):
            conversion = self._field_conversions[index]
            if conversion is not None:
                conversions.append({
                    "from": info,
                    "to": self._info_for(conversion),
                })

        return conversions

    def columnCount(self, parent) -> int:
        return 3

    def rowCount(self, parent) -> int:
        return self._row_count

    def data(self, index, role):
        if not index.isValid():
            return None

        if role == QtCore.Qt.DisplayRole:
            row = index.row()
            if index.column() == 0:
                return self._field_info[row]["Name"]
            elif index.column() == 1:
                return _field_type(self._field_info[row])
            elif index.column() == 2:
                return self._field_conversions[row]

            return "--"

        return None

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self._headers[section]

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if index.isValid():
            if role == QtCore.Qt.EditRole:
                self._field_conversions[index.row()] = value
                self.dataChanged.emit(index, index)
                return True

        return False

    def flags(self, index):
        if index.isValid():
            if index.column() == 2:
                return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

            return QtCore.Qt.ItemIsEnabled

        return QtCore.Qt.NoItemFlags


class ConvertCoordinateFieldsModel(object):

    def __init__(self, settings):
        self._input_file = settings["input_file"]
        self._location = settings["location"]
        self._identifier = settings["identifier"]
        self._group_field = None

        settings_dir = os.path.join(self._location, self._identifier + "-settings")
        if not os.path.isdir(settings_dir):
            os.mkdir(settings_dir)

        filename_parts = os.path.splitext(os.path.basename(self._input_file))
        self._output_file = os.path.join(settings_dir, filename_parts[0] + "_converted.exf")

        self._converter = Converter()
        self._converter.load(self._input_file)

        field_info = self._converter.fetch_field_information()

        text = json.dumps(field_info)
        hex_value = hashlib.sha1(text.encode("utf-8")).hexdigest()

        self._settings_file = os.path.join(settings_dir, f'settings-{hex_value}.json')
        self._group_field, field_conversions = self._load_settings()

        self._coordinate_field_model = CoordinateFieldsModel(field_info, field_conversions)

    def _load_settings(self):
        model_settings = None
        if os.path.isfile(self._settings_file):
            with open(self._settings_file) as f:
                model_settings = json.load(f)

        field_conversions = None
        group_field = None
        if model_settings is not None:
            group_field = model_settings["group_field"]
            field_conversions = model_settings["field_conversions"]

        return group_field, field_conversions

    def _save_settings(self):
        model_settings = {
            "group_field": self._group_field,
            "field_conversions": self._coordinate_field_model.field_conversions()
        }
        with open(self._settings_file, "w") as f:
            json.dump(model_settings, f)

    def get_coordinate_field_model(self):
        return self._coordinate_field_model

    def get_converted_data_file(self):
        return self._output_file

    def get_group_field(self):
        return self._group_field

    def set_group_field(self, group_field):
        self._group_field = group_field

    def get_group_fields(self):
        return self._converter.fetch_group_field_information()

    def done(self):
        self._save_settings()
        data = self._coordinate_field_model.conversions()
        self._converter.convert_fields(data, self._group_field)
        self._converter.get_output_region().writeFile(self._output_file)
