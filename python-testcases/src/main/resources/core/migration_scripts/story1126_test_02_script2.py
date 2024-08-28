from litp.migration import BaseMigration
from litp.migration.operations import AddProperty
from litp.migration.operations import RenameProperty
from litp.migration.operations import RemoveProperty

class Migration_Wrong(BaseMigration):
    version = '1.1.2'
    operations = [ 
        AddProperty('ip-range', 'prop1', 'value_1'),
    ]
