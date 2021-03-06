# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import print_function

from tripleoclient import exceptions
from tripleoclient.workflows import base


def register_or_update(clients, **workflow_input):
    """Node Registration or Update

    Run the tripleo.baremetal.v1.register_or_update Mistral workflow.
    """

    workflow_client = clients.workflow_engine
    tripleoclients = clients.tripleoclient
    queue_name = workflow_input['queue_name']

    with tripleoclients.messaging_websocket(queue_name) as ws:
        execution = base.start_workflow(
            workflow_client,
            'tripleo.baremetal.v1.register_or_update',
            workflow_input=workflow_input
        )

        for payload in base.wait_for_messages(workflow_client, ws, execution):
            if 'message' in payload:
                print(payload['message'])

    if payload['status'] == 'SUCCESS':
        registered_nodes = payload['registered_nodes']
        for nd in registered_nodes:
            print('Successfully registered node UUID %s' % nd['uuid'])
        return registered_nodes
    else:
        raise exceptions.RegisterOrUpdateError(
            'Exception registering nodes: {}'.format(payload['message']))


def _format_provide_errors(payload):
    errors = []
    messages = payload.get('message', [])
    for msg in messages:
        try:
            # With multiple workflows, the error message can become
            # quite large and unreadable as it gets passed from task to
            # task. This attempts to keep only the last, and hopefully
            # useful part.
            errors.append(msg.get('result', '').rstrip('\n').split('\n')[-1])
        except Exception:
            errors.append(msg.get('result', ''))
    return '\n'.join(errors)


def provide(clients, **workflow_input):
    """Provide Baremetal Nodes

    Run the tripleo.baremetal.v1.provide Mistral workflow.
    """

    workflow_client = clients.workflow_engine
    tripleoclients = clients.tripleoclient
    queue_name = workflow_input['queue_name']

    with tripleoclients.messaging_websocket(queue_name) as ws:
        execution = base.start_workflow(
            workflow_client,
            'tripleo.baremetal.v1.provide',
            workflow_input={'node_uuids': workflow_input['node_uuids'],
                            'queue_name': queue_name}
        )

        for payload in base.wait_for_messages(workflow_client, ws, execution):
            if 'message' in payload:
                print(payload['message'])

    if payload['status'] != 'SUCCESS':
        try:
            message = _format_provide_errors(payload)
        except Exception:
            message = 'Failed.'
        raise exceptions.NodeProvideError(
            'Failed to set nodes to available state: {}'.format(message))


def introspect(clients, **workflow_input):
    """Introspect Baremetal Nodes

    Run the tripleo.baremetal.v1.introspect Mistral workflow.
    """

    workflow_client = clients.workflow_engine
    tripleoclients = clients.tripleoclient
    queue_name = workflow_input['queue_name']

    print("Waiting for introspection to finish...")

    with tripleoclients.messaging_websocket(queue_name) as ws:
        execution = base.start_workflow(
            workflow_client,
            'tripleo.baremetal.v1.introspect',
            workflow_input={
                'node_uuids': workflow_input['node_uuids'],
                'run_validations': workflow_input['run_validations'],
                'queue_name': queue_name
            }
        )

        for payload in base.wait_for_messages(workflow_client, ws, execution):
            if 'message' in payload:
                print(payload['message'])

        if payload['status'] == 'SUCCESS':
            print('Successfully introspected all nodes.')
        else:
            raise exceptions.IntrospectionError(
                "Introspection completed with errors:\n%s" % '\n'
                .join(msg for msg in payload['message'] if msg))

    print("Introspection completed.")


def introspect_manageable_nodes(clients, **workflow_input):
    """Introspect all manageable nodes

    Run the tripleo.baremetal.v1.introspect_manageable_nodes Mistral workflow.
    """

    workflow_client = clients.workflow_engine
    tripleoclients = clients.tripleoclient
    queue_name = workflow_input['queue_name']

    print("Waiting for introspection to finish...")

    errors = []

    with tripleoclients.messaging_websocket(queue_name) as ws:
        execution = base.start_workflow(
            workflow_client,
            'tripleo.baremetal.v1.introspect_manageable_nodes',
            workflow_input={
                'run_validations': workflow_input['run_validations'],
                'queue_name': queue_name,
            }
        )

        for payload in base.wait_for_messages(workflow_client, ws, execution):
            if 'message' in payload:
                print(payload['message'])

    if payload['status'] == 'SUCCESS':
        introspected_nodes = payload['introspected_nodes'] or {}
        for node_uuid, status in introspected_nodes.items():
            if status['error'] is not None:
                errors.append("%s: %s" % (node_uuid, status['error']))
    else:
        raise exceptions.IntrospectionError(
            'Exception introspecting nodes: {}'.format(payload['message']))

    if errors:
        raise exceptions.IntrospectionError(
            "Introspection completed with errors:\n%s" % '\n'
            .join(errors))

    print("Introspection completed.")


def provide_manageable_nodes(clients, **workflow_input):
    """Provide all manageable Nodes

    Run the tripleo.baremetal.v1.provide_manageable_nodes Mistral workflow.
    """

    workflow_client = clients.workflow_engine
    tripleoclients = clients.tripleoclient
    queue_name = workflow_input['queue_name']

    with tripleoclients.messaging_websocket(queue_name) as ws:
        execution = base.start_workflow(
            workflow_client,
            'tripleo.baremetal.v1.provide_manageable_nodes',
            workflow_input={"queue_name": queue_name, }
        )

        for payload in base.wait_for_messages(workflow_client, ws, execution):
            if 'message' in payload:
                print(payload['message'])

    if payload['status'] != 'SUCCESS':
        raise exceptions.NodeProvideError(
            'Exception providing nodes:{}'.format(payload['message']))

    print(payload['message'])


def configure(clients, **workflow_input):
    """Configure Node boot options.

    Run the tripleo.baremetal.v1.configure Mistral workflow.
    """

    workflow_client = clients.workflow_engine
    ooo_client = clients.tripleoclient
    queue_name = workflow_input['queue_name']

    with ooo_client.messaging_websocket(queue_name) as ws:
        execution = base.start_workflow(
            workflow_client,
            'tripleo.baremetal.v1.configure',
            workflow_input=workflow_input
        )

        for payload in base.wait_for_messages(workflow_client, ws, execution):
            if 'message' in payload:
                print(payload['message'])

    if payload['status'] != 'SUCCESS':
        raise exceptions.NodeConfigurationError(
            'Failed to configure nodes: {}'.format(payload['message']))


def configure_manageable_nodes(clients, **workflow_input):
    """Configure all manageable Nodes.

    Run the tripleo.baremetal.v1.configure_manageable_nodes Mistral workflow.
    """

    workflow_client = clients.workflow_engine
    ooo_client = clients.tripleoclient
    queue_name = workflow_input['queue_name']

    with ooo_client.messaging_websocket(queue_name) as ws:
        execution = base.start_workflow(
            workflow_client,
            'tripleo.baremetal.v1.configure_manageable_nodes',
            workflow_input=workflow_input
        )

        for payload in base.wait_for_messages(workflow_client, ws, execution):
            if 'message' in payload:
                print(payload['message'])

    if payload['status'] != 'SUCCESS':
        raise exceptions.NodeConfigurationError(
            'Exception configuring nodes: {}'.format(payload['message']))

    print(payload['message'])


def create_raid_configuration(clients, **workflow_input):
    """Create RAID configuration on nodes.

    Run the tripleo.baremetal.v1.create_raid_configuration Mistral workflow.
    """

    workflow_client = clients.workflow_engine
    ooo_client = clients.tripleoclient
    queue_name = workflow_input['queue_name']

    print('Creating RAID configuration for given nodes, this may take time')

    with ooo_client.messaging_websocket(queue_name) as ws:
        execution = base.start_workflow(
            workflow_client,
            'tripleo.baremetal.v1.create_raid_configuration',
            workflow_input=workflow_input
        )

        for payload in base.wait_for_messages(workflow_client, ws, execution):
            if 'message' in payload:
                print(payload['message'])

    if payload['status'] == 'SUCCESS':
        print('Success')
    else:
        raise RuntimeError(
            'Failed to create RAID: {}'.format(payload['message']))


def discover_and_enroll(clients, **workflow_input):
    """Discover nodes.

    Run the tripleo.baremetal.v1.discover_and_enroll_nodes Mistral workflow.
    """

    workflow_client = clients.workflow_engine
    tripleoclients = clients.tripleoclient
    queue_name = workflow_input['queue_name']

    with tripleoclients.messaging_websocket(queue_name) as ws:
        execution = base.start_workflow(
            workflow_client,
            'tripleo.baremetal.v1.discover_and_enroll_nodes',
            workflow_input=workflow_input
        )

        for payload in base.wait_for_messages(workflow_client, ws, execution):
            if payload.get('message'):
                print(payload['message'])

    if payload['status'] == 'SUCCESS':
        registered_nodes = payload['registered_nodes']
        for nd in registered_nodes:
            print('Successfully registered node UUID %s' % nd['uuid'])
        return registered_nodes
    else:
        raise exceptions.RegisterOrUpdateError(
            'Exception discovering nodes: {}'.format(payload['message']))
