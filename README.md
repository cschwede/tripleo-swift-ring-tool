tripleo-swift-ring-tool
=======================

A small tool to simplify ring management for TripleO-based Swift installations.


POC using tripleo-quickstart
----------------------------

1) Deploy a TripleO quickstart[1] undercloud.

2) Add some blockdevices to the nodes, using libvirsh on the $VIRTHOST node.
   Make sure you have at least 3 additional devices (to use 3 replicas).
   For example:

    ssh $VIRTHOST
    su - stack
    dd if=/dev/zero of=controller_0_vdb.img bs=1k count=100k
    dd if=/dev/zero of=controller_0_vdc.img bs=1k count=100k
    dd if=/dev/zero of=controller_0_vdd.img bs=1k count=100k
    virsh attach-disk --config controller_0 ~/controller_0_vdb.img vdb
    virsh attach-disk --config controller_0 ~/controller_0_vdc.img vdc
    virsh attach-disk --config controller_0 ~/controller_0_vdd.img vdd

3) Run the introspection on the undercloud:

    source stackrc
    openstack baremetal introspection bulk start

4) The hostnames are not yet known, but they are required to create the rings.
   Therefore we need to ensure the hosts are placed in a specific order, and we
   use the node capabilities to do so (see also [2]):

    ironic node-list
    ironic node-update <node uuid> replace properties/capabilities='node:controller-0,profile:control,boot_option:local'

    ironic node-update <node uuid> replace properties/capabilities='node:objectstorage-0,profile:control,boot_option:local'

   Note: make sure you use 'controller-%index' or 'objectstorage-%index',
   otherwise the hostnames won't match with the rings built by `tripleo-swift-ring-tool`.

5) Install and run the `tripleo-swift-ring-tool` to create rings based on the
   disks gathered from introspection data:

    git clone git://github.com/cschwede/tripleo-swift-ring-tool.git
    cd tripleo-swift-ring-tool
    sudo python setup.py install

    export IRONIC_INSPECTOR_PASSWORD=$(grep ironic ~/undercloud-passwords.conf | cut -f 2 -d "=")
    tripleo-swift-ring-tool account.builder
    tripleo-swift-ring-tool container.builder
    tripleo-swift-ring-tool object.builder

   This will also upload the .builder/.ring.gz file to the undercloud Swift,
   and the tool will display a storage url where the rings can be downloaded.
   Note: this is a public accessible URL in this POC.

6) Set the `storage_url` in `templates/swift_env.yaml` using the output from
   previous step.

7) Deploy the overcloud using the following templates from this repo:

    openstack overcloud deploy --control-scale 1 --compute-scale 0 \
        --swift-storage-scale 1 --templates -e templates/swift_env.yaml \

    This will disable the default ring building in TripleO, fetch the rings
    created by tripleo-swift-ring-tool, and create XFS filesystems on all found
    blockdevices (except hda/sda/vda).  There is another template named
    `templates/storage_policy.yaml`; you can modify this if you need more than
    one storage policy, for example to use erasure coding.

[1] https://github.com/openstack/tripleo-quickstart
[2] http://docs.openstack.org/developer/tripleo-docs/advanced_deployment/node_placement.html
