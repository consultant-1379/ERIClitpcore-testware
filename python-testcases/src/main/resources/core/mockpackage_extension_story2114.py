from litp.core.extension import ModelExtension
from litp.core.model_type import ItemType
from litp.core.model_type import Property

#
#  THIS FILE IS PROVIDED AS A REFERENCE/EXAMPLE OF HOW TO CREATE A NEW MODEL
#  ITEM TYPE
#


class MockPackageExtension(ModelExtension):

    def define_item_types(self):

        return [ItemType("mock-package",
                         extend_item="software-item",
                         item_description="Software package to install.",
                         name=Property("basic_string",
                                        prop_description="Package name to "
                                                         "install/remove.",
                                       required=True,
                                       ),
                         version=Property("any_string",
                                        prop_description="Package version "
                                                        "to install/remove.",
                                           ),
                         release=Property("any_string",
                                          prop_description="Package release "
                                                         "to install/remove.",
                                            ),
                         arch=Property("any_string",
                                       prop_description="Package arch to "
                                                        "install/remove.",
                                        ),
                         ensure=Property("any_string",
                                    prop_description="Constraint for package "
                                                     "enforcement.",
                                    default="installed",
                                   ),
                         config=Property("any_string",
                                    prop_description="Constraint for "
                                                    "configuration retention.",
                                    ),
                         repository=Property("any_string",
                                    prop_description="Name of repository "
                                                         "to get Package.",
                                        ),
                    )
                ]
