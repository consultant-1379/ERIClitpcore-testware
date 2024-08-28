from litp.migration import BaseMigration
from litp.migration.operations import AddProperty
 
class Migration(BaseMigration):
    version = '1.1.2'
    operations = [
        AddProperty('os-profile', 'prop1', 'ghi'),
        AddProperty('physical-device', 'prop4', 'prp'),
    ]
