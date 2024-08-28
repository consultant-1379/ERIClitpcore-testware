from litp.migration import BaseMigration
from litp.migration.operations import AddProperty
from litp.migration.operations import RemoveProperty
from litp.migration.operations import RenameProperty

class Migration(BaseMigration):
    version = '1.1.2'
    operations = [ 
        #Add property with no value given
        AddProperty('os-profile', 'prop1'),
        #Remove property with no value given
        RemoveProperty('os-profile', 'name'),
    ]
