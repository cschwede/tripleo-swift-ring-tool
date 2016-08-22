import mock
import unittest

import tripleo_swift_ring_tool


class DummyArgs(object):
    def __init__(self):
        self.os_username = 'username'
        self.os_password = 'password'
        self.os_auth_url = 'http://localhost/'
        self.os_tenant_name = 'tenant'


class DummyNode(object):
    def __init__(self):
        self.uuid = 'uuid'


class TestRingUtil(unittest.TestCase):
    @mock.patch('ironicclient.client')
    @mock.patch('ironic_inspector_client.ClientV1')
    @mock.patch('keystoneauth1.loading')
    def test_get_disks(self, mock_keystone, mock_inspector, mock_ironicclient):
        args = DummyArgs()
        mock_ironicclient.get_client().node.list.return_value = [
            DummyNode()]

        # Both nodes have one root disk and another storage disk with a
        # whopping size of 1000 bytes
        mock_inspector().get_data.return_value = {
            'root_disk': {'name': '/dev/vda'},
            'inventory': {'disks': [
                {'name': '/dev/vda'},
                {'name': '/dev/vdb', 'size': 1000},
            ]},
            'extra': {'system': {'product': {
                'uuid': 'A72CF094-8D2C-49D8-B76A-79C531CFBB23'}}}}

        expected_disks = [
            {'device': 'vdb',
             'ip': 'A72CF094-8D2C-49D8-B76A-79C531CFBB23',
             'machine_uuid': 'A72CF094-8D2C-49D8-B76A-79C531CFBB23',
             'size': 1000}]
        expected_node_data_json = {'A72CF094-8D2C-49D8-B76A-79C531CFBB23':
             {'swift::storage::disks::args': {'vdb': {}}}}

        all_disks, node_data_json = tripleo_swift_ring_tool.get_disks(args)
        self.assertEqual(expected_disks, all_disks)
        self.assertEqual(expected_node_data_json, node_data_json)
