from litp.migration import BaseMigration
from litp.migration.operations import AddProperty
from litp.migration.operations import RemoveProperty

class Migration(BaseMigration):
    version = '1.1.2'
    operations = [ 
        AddProperty('os-profile', 'prop1', 'os-profile-1'),
        RemoveProperty('os-profile', 'arch', 'x86_64'),
        RemoveProperty('os-profile', 'path', '/profiles/node-iso/'),
    ]
