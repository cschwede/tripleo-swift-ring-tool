import mock
import unittest

from tripleo_swift_ring_tool import tripleo_swift_ring_tool


class DummyArgs(object):
    def __init__(self):
        self.os_username = 'username'
        self.os_password = 'password'
        self.os_auth_url = 'http://localhost/'
        self.os_tenant_name = 'tenant'


class DummyNode(object):
    def __init__(self):
        self.uuid = 'uuid'


class DummyDetails(object):
    def __init__(self, display_name=None):
        self.instance_info = {'display_name': display_name}
        self.properties = {'capabilities': 'node:node-0,other:value'}


class TestRingUtil(unittest.TestCase):
    @mock.patch('ironicclient.client')
    @mock.patch('ironic_inspector_client.ClientV1')
    @mock.patch('keystoneauth1.loading')
    def test_get_disks(self, mock_keystone, mock_inspector, mock_ironicclient):
        args = DummyArgs()
        # Two nodes found. One down (no displayname yet), one with a node
        # capability set
        mock_ironicclient.get_client().node.list.return_value = [
            DummyNode(), DummyNode()]
        mock_ironicclient.get_client().node.get.side_effect = [
            DummyDetails('overcloud-some-0'), DummyDetails()]

        # Both nodes have one root disk and another storage disk with a
        # whopping size of 1000 bytes
        mock_inspector().get_data.return_value = {
            'root_disk': {'name': '/dev/vda'},
            'inventory': {'disks': [
                {'name': '/dev/vda'},
                {'name': '/dev/vdb', 'size': 1000},
            ]}}

        expected = [
            {'device': 'vdb', 'ip': 'overcloud-some-0-storage', 'size': 1000},
            {'device': 'vdb', 'ip': 'overcloud-node-0-storage', 'size': 1000}]

        self.assertEqual(expected, tripleo_swift_ring_tool.get_disks(args))
