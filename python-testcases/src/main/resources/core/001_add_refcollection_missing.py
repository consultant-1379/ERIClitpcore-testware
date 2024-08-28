from litp.migration import BaseMigration
from litp.migration.operations import AddRefCollection


class Migration(BaseMigration):
    version = '1.0.2'
    operations = [
        # add a refcollection that doesn't exist in the code;
        # will fail but litpd will start fine
        AddRefCollection(
            'migrations-node-config', 'collection_items_missing',
            'software-item'
        )
    ]
