from litp.migration import BaseMigration
from litp.migration.operations import RemoveProperty


class Migration(BaseMigration):
    version = '1.0.2'
    operations = [
        # remove a property that doesn't exist in the code;
        # will fail but litpd will start fine
        RemoveProperty('migrations-node-config', 'surname', 'foo')
    ]
