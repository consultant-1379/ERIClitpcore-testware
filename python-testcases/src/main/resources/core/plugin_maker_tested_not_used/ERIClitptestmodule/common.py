##############################################################################
# COPYRIGHT Ericsson AB 2014
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

from litp.core.task import RemoteExecutionTask


def get_name(model_item):
    """@todo"""

    if model_item.item_type != 'test-module':
        return ''

    return '{0}_{1}_{2}_{3}'.format(
        model_item.tc_story,
        model_item.tc_name,
        model_item.tc_type,
        model_item.tc_description
    )


def get_states(codes):
    """@todo"""

    _STATES = {
        '0': 'Initial',
        '1': 'Updated',
        '2': 'Applied',
        '3': 'ForRemoval',
        '4': 'Removed'
    }

    return [_STATES[str(code)] for code in codes]


def get_rpc_task(nodes, model_item, agent, action, description, **kwargs):
    """return a remote execution task"""

    return RemoteExecutionTask(
        nodes=nodes,
        model_item=model_item,
        description=description,
        agent=agent,
        action=action,
        kwargs=kwargs
    )


def get_nodes(plugin_api_context, return_only=None, include_ms=False,
            hostnames=None):
    """get nodes from the model"""

    nodes = list()
    nodes.extend(plugin_api_context.query('node'))
    if include_ms:
        nodes.extend(plugin_api_context.query('ms'))
    if return_only:
        if return_only == len(nodes):
            return nodes
        else:
            return nodes[0:return_only]
    if hostnames:
        per_host = list()
        for hostname in hostnames:
            per_host.extend(
                [node for node in nodes if node.hostname == hostname]
            )
        nodes[:] = [node for node in nodes if node in per_host]

    return nodes


def get_cluster(plugin_api_context, cluster_type):
    """@todo"""

    return plugin_api_context.query(cluster_type)
