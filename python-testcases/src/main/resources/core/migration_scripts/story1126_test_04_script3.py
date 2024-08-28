from litp.migration import BaseMigration
from litp.migration.operations import AddProperty
from litp.migration.operations import RemoveProperty
from litp.migration.operations import RenameProperty

class Migration(BaseMigration):
    version = '1.110.13'
    operations = [
        #Add dulicate property
        AddProperty('os-profile', 'name', 'sample-profile'),
        #Remove non-existant property
        RemoveProperty('os-profile', 'prop_1', 'value_1'),
        #Rename non-existant property
        RemoveProperty('os-profile', 'prop_2', 'value_2'),
        RemoveProperty('os-profile', 'new_breed'),
        AddProperty('os-profile', 'arch', 'x86_64'),
    ]
