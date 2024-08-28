from litp.migration import BaseMigration
from litp.migration.operations import AddProperty
from litp.migration.operations import RemoveProperty
from litp.migration.operations import RenameProperty

class Migration(BaseMigration):
    version = '1.1.2'
    operations = [
        #Add dulicate property
        AddProperty('os-profile', 'name', 'os-profile-1'),
        #Remove non-existant property
        RemoveProperty('os-profile', 'prop_1', 'value_1'),
        #Rename non-existant property
        RemoveProperty('os-profile', 'prop_2', 'value_2'),
    ]
