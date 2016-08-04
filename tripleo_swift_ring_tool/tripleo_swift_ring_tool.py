#!/usr/bin/python
# -*- coding: utf-8 -*-
import argparse
import logging
import os
import sys
import tarfile

import ironic_inspector_client
import ironicclient
from keystoneauth1 import loading as ksloading
from swift.common.ring import RingBuilder


def main(argv=sys.argv):
    parser = argparse.ArgumentParser(
        description='Swift ring helper for TripleO')

    parser.add_argument('ringdir',
                        default='swift-rings',
                        help='Directory for Swift ring builder files')

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

    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')

    args = parser.parse_args(argv[1:])

    log_format = "%(levelname)s %(message)s"
    log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG
    logging.basicConfig(format=log_format, level=log_level)
    logging.getLogger('requests').setLevel(logging.WARNING)

    if not os.path.isdir(args.ringdir):
        os.makedirs(args.ringdir)

    tar = tarfile.open("%s/rings.tar.gz" % args.ringdir, "w:gz")
    for ring in ['account', 'container', 'object']:
        fname = "%s/%s.builder" % (args.ringdir, ring)
        builder_file, ring_file = write_ring(args, fname)
        tar.add(builder_file, "etc/swift/%s" % os.path.basename(builder_file))
        tar.add(ring_file, "etc/swift/%s" % os.path.basename(ring_file))
    tar.close()


def write_ring(args, builderfile):
    # Make an educated guess about the used port. These are the defaults for
    # TripleO-based deployments in Mitaka
    builder_fname = os.path.basename(builderfile)
    if 'account' in builder_fname:
        port = 6002
    elif 'container' in builder_fname:
        port = 6001
    elif 'object' in builder_fname:
        port = 6000
    else:
        port = 6000

    logging.debug('Set port for new devices to %d' % port)

    if not os.path.isfile(builderfile):
        logging.info(
            '%s not found, creating new builder file', builderfile)
        rb = RingBuilder(args.part_power, args.replicas, args.min_part_hours)
    else:
        logging.info('Using existing builder file %s', builderfile)
        rb = RingBuilder.load(builderfile)

    devices = get_disks(args)

    # Add all missing devices
    for dev in devices:
        _dev = rb.search_devs(dev)
        if not _dev:
            dev['weight'] = float(dev.get('size')) / 10**9
            dev['region'] = 1
            dev['zone'] = 1
            dev['port'] = port
            dev['meta'] = dev['node_uuid']
            # Could be improved; it's the storage network by default
            dev['replication_ip'] = dev['ip']
            dev['replication_port'] = dev['port']
            rb.add_dev(dev)
            logging.info('Added device %s / %s', dev['ip'], dev['device'])
        else:
            logging.info(
                'Ignoring existing device %s / %s', dev['ip'], dev['device'])
    rb.rebalance()
    rb.save(builderfile)
    ring_file = os.path.splitext(builderfile)[0] + '.ring.gz'
    ring_data = rb.get_ring()
    ring_data.save(ring_file)
    return [builderfile, ring_file]


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
                         'size': disk.get('size', 0),
                         'node_uuid': node.uuid}
                all_disks.append(entry)

    return all_disks


if __name__ == "__main__":
    sys.exit(main())
