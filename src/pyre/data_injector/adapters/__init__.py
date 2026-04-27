# src/pyre/data_injector/adapters/__init__.py
# Import all adapters so their @AdapterRegistry.register decorators execute on package load.
from .csv_adapter import CSVAdapter as CSVAdapter
from .db_adapter import DBAdapter as DBAdapter
from .dict_adapter import DictAdapter as DictAdapter
from .excel_adapter import ExcelAdapter as ExcelAdapter
from .json_adapter import JSONAdapter as JSONAdapter
from .yaml_adapter import YAMLAdapter as YAMLAdapter
