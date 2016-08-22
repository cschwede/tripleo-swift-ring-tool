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

4) You need the following patch on your undercloud instance:

    https://review.openstack.org/358643/

5) Install the `tripleo-swift-ring-tool` to create rings based on the
   disks gathered from introspection data:

    git clone git://github.com/cschwede/tripleo-swift-ring-tool.git
    cd tripleo-swift-ring-tool
    sudo python setup.py install
    cd ~/

6) Run the `tripleo-swift-ring-tool` and upload the created ring- and
   builderfiles to the undercloud Swift. The `upload-swift-artifacts` tool will
   create a template in `~/.tripleo/environments/deployment-artifacts.yaml`
   that includes a temporary url that will be used during the deployment. The
   `tripleo-swift-ring-tool` will create a template in
   `~/.tripleo/environments/swift_disks.yaml` with a per-node list of disks to
   prepare for Swift.

    tripleo-swift-ring-tool overcloud-rings
    OS_AUTH_URL=`echo "$OS_AUTH_URL" | sed -e 's/v2.0/v3/g'`OS_IDENTITY_API_VERSION=3 ./upload-swift-artifacts -f overcloud-rings/rings.tar.gz

   Note: you need the [tripleo-common/scripts/upload-swift-artifacts][3] tool for this.

7) Deploy the overcloud:

    openstack overcloud deploy --templates

   This will deploy an overcloud and
   - disable the default ring building in TripleO
   - fetch the rings created by tripleo-swift-ring-tool
   - create XFS filesystems on all found blockdevices (except hda/sda/vda)
   - add system uuid hostname aliases

[1]: https://github.com/openstack/tripleo-quickstart
[2]: http://docs.openstack.org/developer/tripleo-docs/advanced_deployment/node_placement.html
[3]: https://raw.githubusercontent.com/openstack/tripleo-common/master/scripts/upload-swift-artifacts
