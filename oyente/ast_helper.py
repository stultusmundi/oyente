from utils import run_command
from ast_walker import AstWalker, AstWalker_Sup_high
import json

class AstHelper:
    def __init__(self, filename, input_type, remap, allow_paths="", high_ver=0):
        self.input_type = input_type
        self.allow_paths = allow_paths
        self.high_ver = high_ver
        if input_type == "solidity":
            self.remap = remap
            self.source_list = self.get_source_list(filename)
        elif input_type == "standard json":
            self.source_list = self.get_source_list_standard_json(filename)
        else:
            raise Exception("There is no such type of input")
        self.contracts = self.extract_contract_definitions(self.source_list)
        

    def get_source_list_standard_json(self, filename):
        with open('standard_json_output', 'r') as f:
            out = f.read()
        out = json.loads(out)
        return out["sources"]

    def get_source_list(self, filename):
        if self.allow_paths:
            cmd = "solc --combined-json ast %s %s --allow-paths %s" % (self.remap, filename, self.allow_paths)
        else:
            cmd = "solc --combined-json ast %s %s" % (self.remap, filename)
        out = run_command(cmd)
        out = json.loads(out)
        return out["sources"]

    def extract_contract_definitions(self, sourcesList):
        ret = {
            "contractsById": {},
            "contractsByName": {},
            "sourcesByContract": {}
        }
        if self.high_ver:
            walker = AstWalker_Sup_high()
        else:
            walker = AstWalker()
        for k in sourcesList:
            if self.input_type == "solidity":
                ast = sourcesList[k]["AST"]
                
            else:
                ast = sourcesList[k]["legacyAST"]
            nodes = []
            if self.high_ver:
                walker.walk(ast, {"nodeType": "ContractDefinition"}, nodes)#    0.8
            else:
                walker.walk(ast, {"name": "ContractDefinition"}, nodes) #0.7
            for node in nodes:
                ret["contractsById"][node["id"]] = node
                ret["sourcesByContract"][node["id"]] = k
                if self.high_ver:
                    ret["contractsByName"][k + ':' + node["name"]] = node # 0.8
                else:
                    ret["contractsByName"][k + ':' + node["attributes"]["name"]] = node # 0.7

        return ret

    def get_linearized_base_contracts(self, id, contractsById):
        if self.high_ver:
            return map(lambda id: contractsById[id], contractsById[id]["linearizedBaseContracts"])  #0.8
        else:
            return map(lambda id: contractsById[id], contractsById[id]["attributes"]["linearizedBaseContracts"])    #0.7

    def extract_state_definitions(self, c_name):
        node = self.contracts["contractsByName"][c_name]
        state_vars = []
        if node:
            base_contracts = self.get_linearized_base_contracts(node["id"], self.contracts["contractsById"])
            base_contracts = list(base_contracts)
            base_contracts = list(reversed(base_contracts))
            for contract in base_contracts:
                if "children" in contract:
                    for item in contract["children"]:
                        if item["name"] == "VariableDeclaration":
                            state_vars.append(item)
                if "nodes" in contract:
                    for item in contract["nodes"]:
                        if item["nodeType"] == "VariableDeclaration":
                            state_vars.append(item)
        return state_vars

    def extract_states_definitions(self):
        ret = {}
        for contract in self.contracts["contractsById"]:
            if self.high_ver:
                name = self.contracts["contractsById"][contract]["name"]#0.8
            else:
                name = self.contracts["contractsById"][contract]["attributes"]["name"]  #0.7
            source = self.contracts["sourcesByContract"][contract]
            full_name = source + ":" + name
            ret[full_name] = self.extract_state_definitions(full_name)
        return ret

    def extract_func_call_definitions(self, c_name):
        node = self.contracts["contractsByName"][c_name]
        if self.high_ver:
            walker = AstWalker_Sup_high()
        else:
            walker = AstWalker()
        nodes = []
        if node:
            if self.high_ver:
                walker.walk(node, {"nodeType":  "FunctionCall"}, nodes)
            else:
                walker.walk(node, {"name":  "FunctionCall"}, nodes)
        return nodes

    def extract_func_calls_definitions(self):
        ret = {}
        for contract in self.contracts["contractsById"]:
            if self.high_ver:
                name = self.contracts["contractsById"][contract]["name"]#0.8
            else:
                name = self.contracts["contractsById"][contract]["attributes"]["name"]  #0.7
            source = self.contracts["sourcesByContract"][contract]
            full_name = source + ":" + name
            ret[full_name] = self.extract_func_call_definitions(full_name)
        return ret

    def extract_state_variable_names(self, c_name):
        state_variables = self.extract_states_definitions()[c_name]
        var_names = []
        for var_name in state_variables:
            if self.high_ver:
                var_names.append(var_name["name"])#0.8
            else:
                var_names.append(var_name["attributes"]["name"])  #0.7
        return var_names

    def extract_func_call_srcs(self, c_name):
        func_calls = self.extract_func_calls_definitions()[c_name]
        func_call_srcs = []
        for func_call in func_calls:
            func_call_srcs.append(func_call["src"])
        return func_call_srcs

    def get_callee_src_pairs(self, c_name):
        node = self.contracts["contractsByName"][c_name]
        if self.high_ver:
            walker = AstWalker_Sup_high()
        else:
            walker = AstWalker()
        nodes = []
        if node:
            if self.high_ver:           # Probable bug to fix
                list_of_attributes = [
                    {"memberName": "delegatecall"},
                    {"memberName": "call"},
                    {"memberName": "callcode"}
                ]
            else:
                list_of_attributes = [
                    {"attributes": {"member_name": "delegatecall"}},
                    {"attributes": {"member_name": "call"}},
                    {"attributes": {"member_name": "callcode"}}
                ]
            walker.walk(node, list_of_attributes, nodes)
        callee_src_pairs = []
        for node in nodes:
            if self.high_ver:
                type_of_first_child = node["typeDescriptions"]["typeString"]
                if type_of_first_child.split(" ")[0] == "contract":
                    contract = type_of_first_child.split(" ")[1]
                    contract_path = self._find_contract_path(self.contracts["contractsByName"].keys(), contract)
                    callee_src_pairs.append((contract_path, node["src"]))
            else:
                if "children" in node and node["children"]:
                    type_of_first_child = node["children"][0]["attributes"]["type"]
                    if type_of_first_child.split(" ")[0] == "contract":
                        contract = type_of_first_child.split(" ")[1]
                        contract_path = self._find_contract_path(self.contracts["contractsByName"].keys(), contract)
                        callee_src_pairs.append((contract_path, node["src"]))
        return callee_src_pairs

    def get_func_name_to_params(self, c_name):
        node = self.contracts['contractsByName'][c_name]
        if self.high_ver:
            walker = AstWalker_Sup_high()
        else:
            walker = AstWalker()
        func_def_nodes = []
        if node:
            if self.high_ver:
                walker.walk(node, {'nodeType': 'FunctionDefinition'}, func_def_nodes)
            else:
                walker.walk(node, {'name': 'FunctionDefinition'}, func_def_nodes)
        func_name_to_params = {}
        for func_def_node in func_def_nodes:
            if self.high_ver:
                func_name = func_def_node['name']
                params_nodes = []
                walker.walk(func_def_node, {'nodeType': 'ParameterList'}, params_nodes)

                params_node = params_nodes[0]
                param_nodes = []
                walker.walk(params_node, {'nodeType': 'VariableDeclaration'}, param_nodes)
                for param_node in param_nodes:
                    var_name = param_node['name']
                    type_name = param_node["typeName"]["nodeType"]
                    if type_name == 'ArrayTypeName':
                        literal_nodes = []
                        walker.walk(param_node, {'nodeType': 'Literal'}, literal_nodes)
                        if literal_nodes:
                            array_size = int(literal_nodes[0]['value'])
                        else:
                            array_size = 1
                        param = {'name': var_name, 'type': type_name, 'value': array_size}
                    elif type_name == 'ElementaryTypeName':
                        param = {'name': var_name, 'type': type_name}
                    else:
                        param = {'name': var_name, 'type': type_name}

                    if func_name not in func_name_to_params:
                        func_name_to_params[func_name] = [param]
                    else:
                        func_name_to_params[func_name].append(param)
            else:
                func_name = func_def_node['attributes']['name']
                params_nodes = []
                walker.walk(func_def_node, {'name': 'ParameterList'}, params_nodes)

                params_node = params_nodes[0]
                param_nodes = []
                walker.walk(params_node, {'name': 'VariableDeclaration'}, param_nodes)
                for param_node in param_nodes:
                    var_name = param_node['attributes']['name']
                    type_name = param_node['children'][0]['name']
                    if type_name == 'ArrayTypeName':
                        literal_nodes = []
                        walker.walk(param_node, {'name': 'Literal'}, literal_nodes)
                        if literal_nodes:
                            array_size = int(literal_nodes[0]['attributes']['value'])
                        else:
                            array_size = 1
                        param = {'name': var_name, 'type': type_name, 'value': array_size}
                    elif type_name == 'ElementaryTypeName':
                        param = {'name': var_name, 'type': type_name}
                    else:
                        param = {'name': var_name, 'type': type_name}

                    if func_name not in func_name_to_params:
                        func_name_to_params[func_name] = [param]
                    else:
                        func_name_to_params[func_name].append(param)
        return func_name_to_params

    def _find_contract_path(self, contract_paths, contract):
        for path in contract_paths:
            cname = path.split(":")[-1]
            if contract == cname:
                return path
        return ""
