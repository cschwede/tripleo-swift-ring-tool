tripleo-swift-ring-tool
=======================

A small tool to simplify ring management for TripleO-based Swift installations.


POC using tripleo-quickstart
----------------------------

1) Deploy a [TripleO quickstart][1] undercloud.

2) Add some blockdevices to the nodes, using libvirsh on the $VIRTHOST node.
   Make sure you have at least 3 additional devices (to use 3 replicas).
   For example:

    ssh $VIRTHOST
    su - stack
    dd if=/dev/zero of=control_0_vdb.img bs=1k count=100k
    dd if=/dev/zero of=control_0_vdc.img bs=1k count=100k
    dd if=/dev/zero of=control_0_vdd.img bs=1k count=100k
    virsh attach-disk --config control_0 ~/control_0_vdb.img vdb
    virsh attach-disk --config control_0 ~/control_0_vdc.img vdc
    virsh attach-disk --config control_0 ~/control_0_vdd.img vdd

3) Run the introspection on the undercloud:

    source stackrc
    openstack baremetal introspection bulk start

4) The hostnames are not yet known, but they are required to create the rings.
   Therefore we need to ensure the hosts are placed in a specific order, and we
   use the node capabilities to do so (see also [the docs][2]). If you just
   used the default devmode in `tripleo-quickstart`, do the following:

    ironic node-update compute-0 replace \
        properties/capabilities='node:novacompute-0,profile:compute,cpu_hugepages:true,boot_option:local,cpu_vt:true'

    ironic node-update control-0 replace \
        properties/capabilities='node:controller-0,profile:control,cpu_hugepages:true,boot_option:local,cpu_vt:true'

   Note: make sure you use 'controller-%index', 'objectstorage-%index' or
   'novacompute-%index'.  Otherwise the hostnames won't match with the rings
   built by `tripleo-swift-ring-tool`.

5) Install the `tripleo-swift-ring-tool` to create rings based on the
   disks gathered from introspection data:

    git clone git://github.com/cschwede/tripleo-swift-ring-tool.git
    cd tripleo-swift-ring-tool
    sudo python setup.py install
    cd ~/

6) Run the `tripleo-swift-ring-tool` and upload the created ring- and
   builderfiles to the undercloud Swift. The `upload-swift-artifacts` tool will
   create a template in `~/.tripleo/environments/deployment-artifacts.yaml`
   that includes a temporary url that will be used during the deployment.

    tripleo-swift-ring-tool overcloud-rings
    upload-swift-artifacts -f overcloud-rings/rings.tar.gz

   Note: you need the [tripleo-common/scripts/upload-swift-artifacts][3] tool for this.

7) Deploy the overcloud using the following templates from this repo:

    openstack overcloud deploy --templates \
        -e templates/swift_env.yaml \
        -e ~/.tripleo/environments/deployment-artifacts.yaml

   This will disable the default ring building in TripleO, fetch the rings
   created by tripleo-swift-ring-tool, and create XFS filesystems on all found
   blockdevices (except hda/sda/vda).  There is another template named
   `templates/storage_policy.yaml`; you can modify this if you need more than
   one storage policy, for example to use erasure coding.

[1]: https://github.com/openstack/tripleo-quickstart
[2]: http://docs.openstack.org/developer/tripleo-docs/advanced_deployment/node_placement.html
[3]: https://raw.githubusercontent.com/openstack/tripleo-common/master/scripts/upload-swift-artifacts
