#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

import mock

from osc_lib.tests import utils

from tripleoclient import exceptions
from tripleoclient.v1 import overcloud_plan


class TestOvercloudPlanList(utils.TestCommand):

    def setUp(self):
        super(TestOvercloudPlanList, self).setUp()

        self.cmd = overcloud_plan.ListPlans(self.app, None)
        self.app.client_manager.workflow_engine = mock.Mock()
        self.workflow = self.app.client_manager.workflow_engine

    def test_list_empty(self):
        self.workflow.action_executions.create.return_value = (
            mock.Mock(output='{"result": []}'))

        result = self.cmd.take_action(None)
        self.workflow.action_executions.create.assert_called_once_with(
            'tripleo.plan.list')

        self.assertEqual(0, len(result[1]))

    def test_list(self):
        self.workflow.action_executions.create.return_value = (
            mock.Mock(output='{"result": ["test-plan-1", "test-plan-2"]}'))

        result = self.cmd.take_action(None)
        self.workflow.action_executions.create.assert_called_once_with(
            'tripleo.plan.list')

        self.assertEqual(1, len(result[0]))
        self.assertEqual([('test-plan-1',), ('test-plan-2',)], result[1])


class TestOvercloudDeletePlan(utils.TestCommand):

    def setUp(self):
        super(TestOvercloudDeletePlan, self).setUp()

        self.cmd = overcloud_plan.DeletePlan(self.app, None)
        self.app.client_manager.workflow_engine = mock.Mock()
        self.workflow = self.app.client_manager.workflow_engine

    @mock.patch(
        'tripleoclient.workflows.plan_management.delete_deployment_plan',
        autospec=True)
    def test_delete_plan(self, delete_deployment_plan_mock):
        parsed_args = self.check_parser(self.cmd, ['test-plan'],
                                        [('plans', ['test-plan'])])

        self.cmd.take_action(parsed_args)

        delete_deployment_plan_mock.assert_called_once_with(
            self.workflow,
            container='test-plan')

    @mock.patch(
        'tripleoclient.workflows.plan_management.delete_deployment_plan',
        autospec=True)
    def test_delete_multiple_plans(self, delete_deployment_plan_mock):
        argslist = ['test-plan1', 'test-plan2']
        verifylist = [('plans', ['test-plan1', 'test-plan2'])]
        parsed_args = self.check_parser(self.cmd, argslist, verifylist)

        self.cmd.take_action(parsed_args)

        expected = [
            mock.call(self.workflow, container='test-plan1'),
            mock.call(self.workflow, container='test-plan2'),
        ]
        self.assertEqual(delete_deployment_plan_mock.call_args_list,
                         expected)


class TestOvercloudCreatePlan(utils.TestCommand):

    def setUp(self):
        super(TestOvercloudCreatePlan, self).setUp()

        self.cmd = overcloud_plan.CreatePlan(self.app, None)
        self.app.client_manager.workflow_engine = mock.Mock()
        self.tripleoclient = mock.Mock()

        self.websocket = mock.Mock()
        self.websocket.__enter__ = lambda s: self.websocket
        self.websocket.__exit__ = lambda s, *exc: None
        self.tripleoclient = mock.Mock()
        self.tripleoclient.messaging_websocket.return_value = self.websocket
        self.app.client_manager.tripleoclient = self.tripleoclient

        self.workflow = self.app.client_manager.workflow_engine
        self.swift = self.app.client_manager.tripleoclient.object_store

        # Mock UUID4 generation for every test
        uuid4_patcher = mock.patch('uuid.uuid4', return_value="UUID4")
        self.mock_uuid4 = uuid4_patcher.start()
        self.addCleanup(self.mock_uuid4.stop)

    def test_create_default_plan(self):

        # Setup
        arglist = ['overcast']
        verifylist = [
            ('name', 'overcast'),
            ('templates', None)
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.websocket.wait_for_messages.return_value = iter([{
            "execution": {"id": "IDID"},
            "status": "SUCCESS"
        }])

        # Run
        self.cmd.take_action(parsed_args)

        # Verify
        self.workflow.executions.create.assert_called_once_with(
            'tripleo.plan_management.v1.create_deployment_plan',
            workflow_input={
                'container': 'overcast',
                'queue_name': 'UUID4',
                'generate_passwords': True,
                'use_default_templates': True,
                'source_url': None
            })

    def test_create_default_plan_failed(self):

        # Setup
        arglist = ['overcast']
        verifylist = [
            ('name', 'overcast'),
            ('templates', None)
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.websocket.wait_for_messages.return_value = iter([{
            "execution": {"id": "IDID"},
            "status": "ERROR", "message": "failed"
        }])

        # Run
        self.assertRaises(exceptions.WorkflowServiceError,
                          self.cmd.take_action, parsed_args)

        # Verify
        self.workflow.executions.create.assert_called_once_with(
            'tripleo.plan_management.v1.create_deployment_plan',
            workflow_input={
                'container': 'overcast',
                'queue_name': 'UUID4',
                'generate_passwords': True,
                'use_default_templates': True,
                'source_url': None
            })

    @mock.patch("tripleoclient.workflows.plan_management.tarball")
    def test_create_custom_plan(self, mock_tarball):

        # Setup
        arglist = ['overcast', '--templates', '/fake/path']
        verifylist = [
            ('name', 'overcast'),
            ('templates', '/fake/path')
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.websocket.wait_for_messages.return_value = iter([{
            "execution": {"id": "IDID"},
            "status": "SUCCESS"
        }])
        mock_result = mock.Mock(output='{"result": null}')
        self.workflow.action_executions.create.return_value = mock_result

        # Run
        self.cmd.take_action(parsed_args)

        # Verify
        self.workflow.action_executions.create.assert_called_once_with(
            'tripleo.plan.create_container', {"container": "overcast"},
            run_sync=True, save_result=True
        )

        self.workflow.executions.create.assert_called_once_with(
            'tripleo.plan_management.v1.create_deployment_plan',
            workflow_input={
                'container': 'overcast',
                'queue_name': 'UUID4',
                'generate_passwords': True
            })

    @mock.patch("tripleoclient.workflows.plan_management.tarball")
    def test_create_custom_plan_failed(self, mock_tarball):

        # Setup
        arglist = ['overcast', '--templates', '/fake/path']
        verifylist = [
            ('name', 'overcast'),
            ('templates', '/fake/path')
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.websocket.wait_for_messages.return_value = iter([{
            "execution": {"id": "IDID"},
            "status": "ERROR", "message": "failed"
        }])
        mock_result = mock.Mock(output='{"result": null}')
        self.workflow.action_executions.create.return_value = mock_result

        self.swift.get_account.return_value = (
            {u'accept-ranges': u'bytes'},
            [{u'bytes': 1719440, u'count': 482, u'name': u'overcast'},
             {u'bytes': 1719440, u'count': 482, u'name': u'overcloud'}]
        )

        self.swift.get_container.return_value = (
            {u'x-container-meta-usage-tripleo': u'plan'},
            [{u'hash': u'2df2606ed8b866806b162ab3fa9a77ea',
              u'last_modified': u'2016-12-09T21:18:16.172610', u'bytes': 808,
              u'name': u'all-nodes-validation.yaml',
              u'content_type': u'application/octet-stream'},
             {u'hash': u'0f1043e65e95ec24054a4ea63cdb3984',
              u'last_modified': u'2016-12-09T21:18:19.612600', u'bytes': 583,
              u'name': u'bootstrap-config.yaml',
              u'content_type': u'application/octet-stream'},
             {u'hash': u'f9415b93617acd6b151582543a77c689',
              u'last_modified': u'2016-12-09T21:18:16.486870', u'bytes': 20903,
              u'name': u'capabilities-map.yaml',
              u'content_type': u'application/octet-stream'}]
        )

        # Run
        self.assertRaises(exceptions.WorkflowServiceError,
                          self.cmd.take_action, parsed_args)

        # Verify
        self.workflow.action_executions.create.assert_called_once_with(
            'tripleo.plan.create_container', {"container": "overcast"},
            run_sync=True, save_result=True
        )

        self.workflow.executions.create.assert_called_once_with(
            'tripleo.plan_management.v1.create_deployment_plan',
            workflow_input={
                'container': 'overcast',
                'queue_name': 'UUID4',
                'generate_passwords': True
            })

        self.swift.get_account.assert_called_once()
        self.swift.get_container.assert_called_once_with('overcast')
        self.swift.delete_object.assert_has_calls([
            mock.call('overcast', u'capabilities-map.yaml'),
            mock.call('overcast', u'bootstrap-config.yaml'),
            mock.call('overcast', u'all-nodes-validation.yaml'),
        ], any_order=True)

    @mock.patch("tripleoclient.workflows.plan_management.tarball")
    def test_create_custom_plan_plan_environment_file(self,
                                                      mock_tarball):
        # Setup
        arglist = ['overcast', '--templates', '/fake/path',
                   '-p', 'the_plan_environment.yaml']
        verifylist = [
            ('name', 'overcast'),
            ('templates', '/fake/path'),
            ('plan_environment_file', 'the_plan_environment.yaml')
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.websocket.wait_for_messages.return_value = iter([{
            "execution": {"id": "IDID"},
            "status": "SUCCESS"
        }])
        mock_result = mock.Mock(output='{"result": null}')
        self.workflow.action_executions.create.return_value = mock_result

        mock_open_context = mock.mock_open()
        with mock.patch('six.moves.builtins.open', mock_open_context):
            self.cmd.take_action(parsed_args)

        # Verify
        self.workflow.action_executions.create.assert_called_once_with(
            'tripleo.plan.create_container', {"container": "overcast"},
            run_sync=True, save_result=True
        )

        self.workflow.executions.create.assert_called_once_with(
            'tripleo.plan_management.v1.create_deployment_plan',
            workflow_input={
                'container': 'overcast',
                'queue_name': 'UUID4',
                'generate_passwords': True
            })

        mock_open_context.assert_has_calls(
            [mock.call('the_plan_environment.yaml')])

        self.tripleoclient.object_store.put_object.assert_called_once_with(
            'overcast', 'plan-environment.yaml', mock_open_context())

    def test_create_default_plan_with_password_gen_disabled(self):

        # Setup
        arglist = ['overcast', '--disable-password-generation']
        verifylist = [
            ('name', 'overcast'),
            ('templates', None),
            ('disable_password_generation', True)
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self.websocket.wait_for_messages.return_value = iter([{
            "execution": {"id": "IDID"},
            "status": "SUCCESS"
        }])

        # Run
        self.cmd.take_action(parsed_args)

        # Verify
        self.workflow.executions.create.assert_called_once_with(
            'tripleo.plan_management.v1.create_deployment_plan',
            workflow_input={
                'container': 'overcast',
                'queue_name': 'UUID4',
                'use_default_templates': True,
                'generate_passwords': False,
                'source_url': None
            })


class TestOvercloudDeployPlan(utils.TestCommand):

    def setUp(self):
        super(TestOvercloudDeployPlan, self).setUp()

        app_args = mock.Mock()
        app_args.verbose_level = 1
        self.cmd = overcloud_plan.DeployPlan(self.app, app_args)

        self.workflow = self.app.client_manager.workflow_engine = mock.Mock()
        self.orch = self.app.client_manager.orchestration = mock.Mock()

        self.websocket = mock.Mock()
        self.websocket.__enter__ = lambda s: self.websocket
        self.websocket.__exit__ = lambda s, *exc: None
        self.tripleoclient = mock.Mock()
        self.tripleoclient.messaging_websocket.return_value = self.websocket
        self.app.client_manager.tripleoclient = self.tripleoclient

        # Mock UUID4 generation for every test
        uuid4_patcher = mock.patch('uuid.uuid4', return_value="UUID4")
        self.mock_uuid4 = uuid4_patcher.start()
        self.addCleanup(self.mock_uuid4.stop)

        sleep_patch = mock.patch('time.sleep')
        self.addCleanup(sleep_patch.stop)
        sleep_patch.start()

    @mock.patch('tripleoclient.utils.wait_for_stack_ready', autospec=True)
    def test_overcloud_deploy_plan(self, mock_for_stack_ready):

        # Setup
        arglist = ['--run-validations', 'overcast']
        verifylist = [
            ('name', 'overcast'),
            ('run_validations', True),
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        # No existing stack, this is a new deploy.
        self.orch.stacks.get.return_value = None

        self.websocket.wait_for_messages.return_value = iter([{
            'execution': {'id': 'IDID'},
            'status': 'SUCCESS'
        }])

        mock_for_stack_ready.return_value = True

        # Run
        self.cmd.take_action(parsed_args)

        # Verify
        self.workflow.executions.create.assert_called_once_with(
            'tripleo.deployment.v1.deploy_plan',
            workflow_input={
                'container': 'overcast',
                'run_validations': True,
                'queue_name': 'UUID4',
                'skip_deploy_identifier': False
            }
        )


class TestOvercloudExportPlan(utils.TestCommand):

    def setUp(self):
        super(TestOvercloudExportPlan, self).setUp()
        self.cmd = overcloud_plan.ExportPlan(self.app, None)
        self.app.client_manager = mock.Mock()
        self.clients = self.app.client_manager

        # Mock UUID4 generation for every test
        uuid4_patcher = mock.patch('uuid.uuid4', return_value="UUID4")
        self.mock_uuid4 = uuid4_patcher.start()
        self.addCleanup(self.mock_uuid4.stop)

        # Mock urlopen
        f = mock.Mock()
        f.read.return_value = 'tarball contents'
        urlopen_patcher = mock.patch('six.moves.urllib.request.urlopen',
                                     return_value=f)
        self.mock_urlopen = urlopen_patcher.start()
        self.addCleanup(self.mock_urlopen.stop)

    @mock.patch(
        'tripleoclient.workflows.plan_management.export_deployment_plan',
        autospec=True)
    def test_export_plan(self, export_deployment_plan_mock):
        parsed_args = self.check_parser(self.cmd, ['test-plan'],
                                        [('plan', 'test-plan')])

        export_deployment_plan_mock.return_value = 'http://fake-url.com'

        with mock.patch('six.moves.builtins.open', mock.mock_open()):
            self.cmd.take_action(parsed_args)

        export_deployment_plan_mock.assert_called_once_with(
            self.clients, plan='test-plan', queue_name='UUID4')

    @mock.patch('os.path.exists')
    def test_export_plan_outfile_exists(self, exists_mock):
        parsed_args = self.check_parser(self.cmd, ['test-plan'],
                                        [('plan', 'test-plan')])

        exists_mock.return_value = True

        self.assertRaises(exceptions.PlanExportError,
                          self.cmd.take_action, parsed_args)

    @mock.patch(
        'tripleoclient.workflows.plan_management.export_deployment_plan',
        autospec=True)
    @mock.patch('os.path.exists')
    def test_export_plan_outfile_exists_with_overwrite(
            self, exists_mock, export_deployment_plan_mock):
        arglist = ['-f', 'test-plan']
        verifylist = [
            ('plan', 'test-plan'),
            ('force_overwrite', True)
        ]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        exists_mock.return_value = True
        export_deployment_plan_mock.return_value = 'http://fake-url.com'

        with mock.patch('six.moves.builtins.open', mock.mock_open()):
            self.cmd.take_action(parsed_args)

        export_deployment_plan_mock.assert_called_once_with(
            self.clients, plan='test-plan', queue_name='UUID4')
