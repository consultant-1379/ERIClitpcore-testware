from litp.migration import BaseMigration
from litp.migration.operations import AddProperty
from litp.migration.operations import RemoveProperty

class Migration(BaseMigration):
    version = '1.1.2'
    operations = [ 
        AddProperty('storage-profile', 'prop1', 'storage1'),
        RemoveProperty('storage-profile', 'storage_profile_name', 'sp1'),
    ]
