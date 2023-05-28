class AstWalker:
    def walk(self, node, attributes, nodes):
        if isinstance(attributes, dict):
            self._walk_with_attrs(node, attributes, nodes)
        else:
            self._walk_with_list_of_attrs(node, attributes, nodes)

    def _walk_with_attrs(self, node, attributes, nodes):
        if self._check_attributes(node, attributes):
            nodes.append(node)
        else:
            if "children" in node and node["children"]:
                for child in node["children"]:
                    self._walk_with_attrs(child, attributes, nodes)

    def _walk_with_list_of_attrs(self, node, list_of_attributes, nodes):
        if self._check_list_of_attributes(node, list_of_attributes):
            nodes.append(node)
        else:
            if "children" in node and node["children"]:
                for child in node["children"]:
                    self._walk_with_list_of_attrs(child, list_of_attributes, nodes)

    def _check_attributes(self, node, attributes):
        for name in attributes:
            if name == "attributes":
                if "attributes" not in node or not self._check_attributes(node["attributes"], attributes["attributes"]):
                    return False
            else:
                if name not in node or node[name] != attributes[name]:
                    return False
        return True

    def _check_list_of_attributes(self, node, list_of_attributes):
        for attrs in list_of_attributes:
            if self._check_attributes(node, attrs):
                return True
        return False

 # Design a new AstWalker to suit with the new AST Form of Solidity 0.8 verison

class AstWalker_Sup_high:  
    def walk(self, node, attributes, nodes):
        if isinstance(attributes, dict):
            self._walk_with_attrs(node, attributes, nodes)
        else:
            self._walk_with_list_of_attrs(node, attributes, nodes)


    def _walk_with_attrs(self, node, attributes, nodes):
        if self._check_attributes(node, attributes):
            nodes.append(node)
        else:
            for name in node:
                if isinstance(node[name], list):
                    for child in node[name]:
                        if isinstance(child, dict):
                            self._walk_with_attrs(child, attributes, nodes)
                elif isinstance(node[name], dict):
                    self._walk_with_attrs(node[name], attributes, nodes)

    def _walk_with_list_of_attrs(self, node, list_of_attributes, nodes):
        if self._check_list_of_attributes(node, list_of_attributes):
            nodes.append(node)
        else:
            for name in node:
                if isinstance(node[name], list):
                    for child in node[name]:
                        if isinstance(child, dict):
                            self._walk_with_list_of_attrs(child, list_of_attributes, nodes)
                elif isinstance(node[name], dict):
                    self._walk_with_list_of_attrs(node[name], list_of_attributes, nodes)

    def _check_attributes(self, node, attributes):
        for name in attributes:
            if name not in node or node[name] != attributes[name]:
                return False
        return True

    def _check_list_of_attributes(self, node, list_of_attributes):
        for attrs in list_of_attributes:
            if self._check_attributes(node, attrs):
                return True
        return False