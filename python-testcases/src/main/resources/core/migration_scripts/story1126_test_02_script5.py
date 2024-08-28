from litp.migration import BaseMigration
from litp.migration.operations import AddProperty
from litp.migration.operations import RenameProperty
from litp.migration.operations import RemoveProperty

class Migration(BaseMigration):
    version = '1.1.2'
    operations = [ 
        # RemoveProperty_nonexistent
        RemoveProperty('ip-range', 'prop1', 'val1'),
        # RemoveProperty_Mandatory_nodefault
        RemoveProperty('os-profile', 'path', '/profiles/node-iso/'),
        # RemoveProperty_Mandatory_default
        RenameProperty('os-profile', 'arch', 'x86_64')
    ]
