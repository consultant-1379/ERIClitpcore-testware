from litp.migration import BaseMigration
from litp.migration.operations import AddProperty
from litp.migration.operations import RenameProperty
from litp.migration.operations import RemoveProperty
from litp.migration.operations import AddCollection
from litp.migration.operations import AddRefCollection
from litp.migration.operations import UpdateCollectionType
from litp.migration.operations import RenameItemType


class Migration(BaseMigration):
    version = '1.0.2'
    operations = [
        RenameItemType('migrations-node-config', 'migrated-node-config'),
        AddCollection(
            'migrated-node-config', 'migration_collection_added',
            'migration-config'
        ),
        AddRefCollection(
            'migrated-node-config', 'migration_refcollection_added',
            'migration-config'
        ),
        AddProperty('migrated-node-config', 'surname', 'bar'),
        RenameProperty('migrated-node-config', 'name', 'renamed'),
        RemoveProperty('migrated-node-config', 'toberemoved'),
        UpdateCollectionType(
            'migrated-node-config', 'migration_items_collection',
            'migration-config', 'node-config'
        )
    ]
