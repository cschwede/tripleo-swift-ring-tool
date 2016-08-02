#!/usr/bin/python
# -*- coding: utf-8 -*-
import argparse
import logging
import os
import sys

import ironic_inspector_client
import ironicclient
from keystoneauth1 import loading as ksloading
from swift.common.ring import RingBuilder
import swiftclient


def main(argv=sys.argv):
    parser = argparse.ArgumentParser(
        description='Swift ring helper for TripleO')

    parser.add_argument('builderfile',
                        help='Swift ring builder filename')

    parser.add_argument('--part_power',
                        default=14, type=int,
                        help='Partition power for new rings. Default: 14')

    parser.add_argument('--replicas',
                        default=3, type=int,
                        help='Replias for new rings. Default: 3')

    parser.add_argument('--min_part_hours',
                        default=1, type=int,
                        help='min_part_hours for new rings. Default: 1')

    parser.add_argument('--port',
                        help='IP Port for new devices')

    parser.add_argument('--os-username',
                        default=os.environ.get('OS_USERNAME'),
                        help='Defaults to env[OS_USERNAME]')

    parser.add_argument('--os-password',
                        default=os.environ.get('OS_PASSWORD'),
                        help='Defaults to env[OS_PASSWORD]')

    parser.add_argument('--os-tenant-name',
                        default=os.environ.get('OS_TENANT_NAME'),
                        help='Defaults to env[OS_TENANT_NAME]')

    parser.add_argument('--os-auth-url',
                        default=os.environ.get('OS_AUTH_URL'),
                        help='Defaults to env[OS_AUTH_URL]')

    parser.add_argument('--ironic-inspector-password',
                        default=os.environ.get('IRONIC_INSPECTOR_PASSWORD'),
                        help='Defaults to env[IRONIC_INSPECTOR_PASSWORD]')

    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')

    args = parser.parse_args(argv[1:])

    log_format = "%(levelname)s %(message)s"
    log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG
    logging.basicConfig(format=log_format, level=log_level)
    logging.getLogger('requests').setLevel(logging.WARNING)

    builder_file, ring_file = write_ring(args)
    if args.ironic_inspector_password:
        upload_file(args, [builder_file, ring_file])
    else:
        logging.info('Skipping ring upload - inspector password not set')


def write_ring(args):
    # Make an educated guess about the used port. These are the defaults for
    # TripleO-based deployments in Mitaka
    builder_fname = os.path.basename(args.builderfile)
    if 'account' in builder_fname:
        port = 6002
    elif 'container' in builder_fname:
        port = 6001
    elif 'object' in builder_fname:
        port = 6000
    else:
        port = 6000

    logging.debug('Set port for new devices to %d' % port)

    if not os.path.isfile(args.builderfile):
        logging.info(
            '%s not found, creating new builder file', args.builderfile)
        rb = RingBuilder(args.part_power, args.replicas, args.min_part_hours)
    else:
        logging.info('Using existing builder file %s', args.builderfile)
        rb = RingBuilder.load(args.builderfile)

    devices = get_disks(args)

    # Add all missing devices
    for dev in devices:
        _dev = rb.search_devs(dev)
        if not _dev:
            dev['weight'] = float(dev.get('size')) / 10**9
            dev['region'] = 1
            dev['zone'] = 1
            dev['port'] = port
            # Could be improved; it's the storage network by default
            dev['replication_ip'] = dev['ip']
            dev['replication_port'] = dev['port']
            rb.add_dev(dev)
            logging.info('Added device %s / %s', dev['ip'], dev['device'])
        else:
            logging.info(
                'Ignoring existing device %s / %s', dev['ip'], dev['device'])
    rb.rebalance()
    rb.save(args.builderfile)
    ring_file = os.path.splitext(args.builderfile)[0] + '.ring.gz'
    ring_data = rb.get_ring()
    ring_data.save(ring_file)
    return [args.builderfile, ring_file]


def get_disks(args):
    ironic = ironicclient.client.get_client(
        1,
        os_username=args.os_username,
        os_password=args.os_password,
        os_auth_url=args.os_auth_url,
        os_tenant_name=args.os_tenant_name)

    loader = ksloading.get_plugin_loader('password')

    auth_plugin = loader.load_from_options(
        username=args.os_username,
        password=args.os_password,
        auth_url=args.os_auth_url,
        tenant_name=args.os_tenant_name)

    keystone_session = ksloading.session.Session().load_from_options(
        auth=auth_plugin)

    insp_client = ironic_inspector_client.ClientV1(session=keystone_session)
    all_disks = []
    for node in ironic.node.list():
        details = ironic.node.get(node.uuid)
        display_name = details.instance_info.get('display_name')
        if not display_name:
            # Instance is not yet started, so we need to do an educated guess
            # about the hostname
            _capabilities = details.properties.get('capabilities')
            capabilities = dict(
                [entry.split(':') for entry in _capabilities.split(',')])
            cap_node = capabilities.get('node')
            if not cap_node:
                # Node is not tagged, skip it
                continue
            display_name = "overcloud-%s" % cap_node
        data = insp_client.get_data(node.uuid)
        root_disk = data.get('root_disk')
        disks = data.get('inventory', {}).get('disks', [])
        for disk in disks:
            if root_disk.get('name') != disk.get('name'):
                entry = {'ip': "%s-storage" % display_name,
                         'device': os.path.basename(disk.get('name')),
                         'size': disk.get('size', 0)}
                all_disks.append(entry)

    return all_disks


def upload_file(args, filenames):
    swift = swiftclient.client.Connection(
        authurl=args.os_auth_url,
        tenant_name='service',
        user='ironic',
        key=args.ironic_inspector_password,
        auth_version=2)
    storage_url, _ = swift.get_auth()
    logging.info('Storage URL to use in the environment: %s', storage_url)
    # Ensure container exists and is public readable
    headers = {'X-Container-Read': '.r:*,.rlistings',
               'X-Container-Meta-Web-Listings': 'true'}
    swift.put_container('overcloud-swift-rings', headers)
    swift.post_container('overcloud-swift-rings', headers)

    for filename in filenames:
        objname = os.path.basename(filename)
        with open(filename) as inf:
            contents = inf.read()
            swift.put_object('overcloud-swift-rings', objname, contents)
            logging.info('Uploaded %s to undercloud Swift', filename)


if __name__ == "__main__":
    sys.exit(main())
