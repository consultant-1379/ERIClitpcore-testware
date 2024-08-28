from litp.migration import BaseMigration
from litp.migration.operations import AddProperty
from litp.migration.operations import RenameProperty

class Migration(BaseMigration):
    version = '1.1.2'
    operations = [ 
        AddProperty('network-profile', 'prop4', 'ghi'),
        RenameProperty('network-profile', 'management_network', 'mgmt_network'),
    ]
