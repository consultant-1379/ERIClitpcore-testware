##############################################################################
# COPYRIGHT Ericsson AB 2014
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

import src.testmodule_plugin.common as common

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


def _get_config(modelitem, context_api):
    """@todo"""

    tasks = list()
    log.trace.info(
        "create_configuration for {0}_{1}_{2}_{2}".format(
            common.get_name(modelitem)
        )
    )
    nodes = common.get_nodes(context_api)
    if modelitem.get_state() in common.get_states([0, 1, 3]):
        for node in nodes:
            tasks.append(
                common.get_rpc_task(
                    [node],
                    modelitem,
                    'service',
                    'status',
                    'Execute a remote procedure call on node \'{0}\''.format(
                        node.hostname
                    ),
                    service='httpd'
                )
            )

    return tasks


def cfg_tc_03_p_no_lock_unlock(modelitem, context_api):
    """@todo"""

    return _get_config(modelitem, context_api)


def lck_tc_03_p_no_lock_unlock(modelitem, context_api, node):
    """@todo"""

    name = common.get_name(modelitem)
    log.trace.info(
        "create_lock_tasks for '{0}'".format(name)
    )
    if modelitem.get_state() in common.get_states([0, 1, 3]):
        log.trace.info(
            "No lock/unlock tasks required for '{0}'".format(name)
        )
        log.trace.debug(
            "No use for '{0}' or '{1}'".format(context_api, node)
        )

    return []


def cfg_tc_04_n_lock_no_unlock(modelitem, context_api):
    """@todo"""

    return _get_config(modelitem, context_api)


def lck_tc_04_n_lock_no_unlock(modelitem, context_api, node):
    """@todo"""

    name = common.get_name(modelitem)
    log.trace.info(
        "create_lock_tasks for '{0}'".format(name)
    )
    log.trace.debug(
        "No use for '{0}'".format(context_api)
    )
    if modelitem.get_state() in common.get_states([0, 1, 3]):
        return [
            common.get_rpc_task(
                node,
                modelitem,
                'lock_unlock',
                'lock',
                'Lock task on node \'{0}\' for test \'{1}\''.format(
                    node.hostname,
                    modelitem.description
                )
            )
        ]

    return []


def cfg_tc_05_n_unlock_no_lock(modelitem, context_api):
    """@todo"""

    return _get_config(modelitem, context_api)


def lck_tc_05_n_unlock_no_lock(modelitem, context_api, node):
    """@todo"""

    name = common.get_name(modelitem)
    log.trace.info(
        "create_lock_tasks for '{0}'".format(name)
    )
    log.trace.debug(
        "No use for '{0}'".format(context_api)
    )
    if modelitem.get_state() in common.get_states([0, 1, 3]):
        return [
            common.get_rpc_task(
                node,
                modelitem,
                'lock_unlock',
                'unlock',
                'Lock task on node \'{0}\' for test \'{1}\''.format(
                    node.hostname,
                    modelitem.description
                )
            )
        ]

    return []


def cfg_tc_06_n_multi_lock_unlock(modelitem, context_api):
    """@todo"""

    return _get_config(modelitem, context_api)


def lck_tc_06_n_multi_lock_unlock(modelitem, context_api, node):
    """@todo"""

    tasks = list()
    name = common.get_name(modelitem)
    log.trace.info(
        "create_lock_tasks for '{0}'".format(name)
    )
    tasks.extend(
        lck_tc_04_n_lock_no_unlock(modelitem, context_api, node)
    )
    tasks.extend(
        lck_tc_05_n_unlock_no_lock(modelitem, context_api, node)
    )

    return tasks


def cfg_tc_07_n_no_ha_mngr(modelitem, context_api):
    """@todo"""

    return  _get_config(modelitem, context_api)


def lck_tc_07_n_no_ha_mngr(modelitem, context_api, node):
    """@todo"""

    no_exist_ha = 'INVALID_DOES_NOT_EXIST'
    tasks = list()
    name = common.get_name(modelitem)
    log.trace.info(
        "create_lock_tasks for '{0}'".format(name)
    )
    if modelitem.get_state() in common.get_states([0, 1, 3]):
        hamngr = [
            cluster.ha_manager \
            for cluster in common.get_cluster(context_api, 'vcs-cluster')
        ][0]
        if hamngr == no_exist_ha:
            tasks.extend(
                lck_tc_04_n_lock_no_unlock(modelitem, context_api, node)
            )
            tasks.extend(
                lck_tc_05_n_unlock_no_lock(modelitem, context_api, node)
            )

    return tasks


def cfg_tc_10_n_cluster_lock_unlock(modelitem, context_api):
    """@todo"""

    return  _get_config(modelitem, context_api)


def lck_tc_10_n_cluster_lock_unlock(modelitem, context_api, node):
    """@todo"""

    return lck_tc_06_n_multi_lock_unlock(modelitem, context_api, node)
