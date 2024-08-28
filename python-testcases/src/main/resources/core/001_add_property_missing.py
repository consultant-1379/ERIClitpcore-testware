from litp.migration import BaseMigration
from litp.migration.operations import AddProperty


class Migration(BaseMigration):
    version = '1.0.2'
    operations = [
        # add property that doesn't exist in the code;
        # will fail and litp will not start
        AddProperty('migrations-node-config', 'surname', 'foo')
    ]
