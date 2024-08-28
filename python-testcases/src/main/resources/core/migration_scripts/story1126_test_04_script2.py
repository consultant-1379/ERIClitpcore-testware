from litp.migration import BaseMigration
from litp.migration.operations import AddProperty
from litp.migration.operations import RemoveProperty
from litp.migration.operations import RenameProperty

class Migration(BaseMigration):
    version = '1.1.2'
    operations = [ 
        #Remove mandatory property with default
        RemoveProperty('os-profile', 'arch', 'value_3'),
        #Rename mandatory property with default
        RenameProperty('os-profile', 'breed', 'new_breed'),
    ]
