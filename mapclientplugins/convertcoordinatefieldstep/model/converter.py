import json

from cmlibs.utils.zinc.field import find_or_create_field_group
from cmlibs.zinc.context import Context
from cmlibs.zinc.field import Field
from cmlibs.zinc.status import OK as ZINC_OK


class ConverterFileReadFailed(Exception):
    pass


class Converter(object):

    def __init__(self):
        self._context = Context("converter")
        self._output_node_set_group = None

    def _load_file(self, region_name, filename):
        root_region = self._context.getDefaultRegion()
        region = root_region.createChild(region_name)
        result = region.readFile(filename)
        if result != ZINC_OK:
            raise ConverterFileReadFailed(f"Failed to read file '{filename}'")

        return region

    def _input_region(self):
        root_region = self._context.getDefaultRegion()
        return root_region.findChildByName("original")

    def _output_region(self):
        root_region = self._context.getDefaultRegion()
        region = root_region.findChildByName("converted")
        if not (region and region.isValid()):
            region = root_region.createChild("converted")

        return region

    def get_output_region(self):
        return self._output_region()

    def load(self, filename):
        self._load_file("original", filename)

    def fetch_group_field_information(self):
        region = self._input_region()
        field_module = region.getFieldmodule()

        field_iter = field_module.createFielditerator()
        field = field_iter.next()
        group_fields = ["nodes", "datapoints"]
        while field.isValid():
            markerGroup = field.castGroup()
            if markerGroup.isValid():
                group_fields.append(markerGroup.getName())
            field = field_iter.next()

        return group_fields

    def fetch_field_information(self):
        field_info = []
        region = self._input_region()

        info = json.loads(region.getFieldmodule().writeDescription())
        if "Fields" in info:
            return info["Fields"]

        return field_info

    def convert_fields(self, field_info, group_field_name):
        region = self._input_region()
        field_module = region.getFieldmodule()
        output_region = self._output_region()
        output_field_module = output_region.getFieldmodule()
        output_node_set = output_field_module.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        output_node_template = output_node_set.createNodetemplate()
        self._output_node_set_group = _create_node_group(output_field_module, output_node_set, group_field_name)

        group_field = field_module.findFieldByName(group_field_name)

        if group_field:
            group_field = group_field.castGroup()
            if group_field and group_field.isValid():
                # print(group_field.getSize())
                node_set = field_module.findNodesetByName("nodes")
                node_template = node_set.createNodetemplate()
                node_group = group_field.getFieldNodeGroup(node_set)
                group = node_group.getNodesetGroup()
                data_iter = group.createNodeiterator()
                data_item = data_iter.next()
                output_field_module.readDescription(field_module.writeDescription())
                fields_with_times = {}
                for info in field_info:
                    from_field_name = info["from"]["Name"]
                    field = field_module.findFieldByName(from_field_name)
                    node_template.defineFieldFromNode(field, data_item)
                    time_sequence = node_template.getTimesequence(field)
                    to_field_name = info["to"]["Name"]
                    output_field = output_field_module.findFieldByName(to_field_name)
                    output_node_template.defineField(output_field)
                    if time_sequence and time_sequence.isValid():
                        fields_with_times[to_field_name] = time_sequence
                        output_node_template.setTimesequence(output_field, time_sequence)

                field_cache = field_module.createFieldcache()
                output_field_cache = output_field_module.createFieldcache()
                while data_item.isValid():
                    new_datapoint = output_node_set.createNode(-1, output_node_template)
                    self._output_node_set_group.addNode(new_datapoint)
                    field_cache.setNode(data_item)
                    output_field_cache.setNode(new_datapoint)
                    for info in field_info:
                        # from_field_name = info["from"]["Name"]
                        to_field_name = info["to"]["Name"]
                        from_field = field_module.findFieldByName(to_field_name)
                        to_field = output_field_module.findFieldByName(to_field_name)
                        if "FieldStoredString" in info["from"]:
                            value = from_field.evaluateString(field_cache)
                            if value:
                                to_field.assignString(output_field_cache, value)
                        elif "FieldFiniteElement" in info["from"]:
                            component_count = from_field.getNumberOfComponents()
                            if to_field_name in fields_with_times:
                                time_sequence = fields_with_times[to_field_name]
                                for i in range(time_sequence.getNumberOfTimes()):
                                    time = time_sequence.getTime(i + 1)
                                    field_cache.setTime(time)
                                    output_field_cache.setTime(time)
                                    result, values = from_field.evaluateReal(field_cache, component_count)
                                    to_field.assignReal(output_field_cache, values)
                            else:
                                result, values = from_field.evaluateReal(field_cache, component_count)
                                if result == ZINC_OK:
                                    to_field.assignReal(output_field_cache, values)
                        elif "FieldStoredMeshLocation" in info["from"] and "FieldFiniteElement" in info["to"] and info["to"]["FieldFiniteElement"]["NumberOfComponents"] == 3:
                            component_count = from_field.getNumberOfComponents()
                            from_field_name = info["from"]["Name"]
                            original_field = field_module.findFieldByName(from_field_name)
                            host_coordinates = field_module.createFieldEmbedded(from_field, original_field)
                            result, values = host_coordinates.evaluateReal(field_cache, component_count)
                            if result == ZINC_OK:
                                to_field.assignReal(output_field_cache, values)

                    data_item = data_iter.next()

        field = output_field_module.findFieldByName("coordinates")
        field.setName("data_coordinates")


def _create_node_group(field_module, node_set, group_field_name):
    field_group = find_or_create_field_group(field_module, group_field_name)
    node_group_field = field_group.getFieldNodeGroup(node_set)
    if not node_group_field.isValid():
        node_group_field = field_group.createFieldNodeGroup(node_set)

    return node_group_field.getNodesetGroup()
