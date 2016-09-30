tripleo-swift-ring-tool
=======================

A small tool to simplify ring management for TripleO-based Swift installations.


POC using tripleo-quickstart
----------------------------

1) Deploy a [TripleO quickstart][1] undercloud including Gerrit review
   [#358643][2] (tripleo-heat-templates)
   and one ore more objectstorage nodes:

    ./quickstart.sh --release master-tripleo-ci -e @swift.yaml <VIRTHOST>

   The required `swift.yaml` could look like this:

    overcloud_nodes:
      - name: objectstorage_0
        flavor: objectstorage
      - name: objectstorage_1
        flavor: objectstorage

      - name: control_0
        flavor: control

    overcloud_templates_repo: "https://git.openstack.org/openstack/tripleo-heat-templates"
    overcloud_templates_path: "tripleo-heat-templates"
    overcloud_templates_refspec: "refs/changes/43/358643/4"

    extra_args: --control-scale 1 --compute-scale 0 --swift-storage-scale 2

2) SSH into the undercloud and install the [tripleo-swift-ring-tool.py][3] tool:

    ssh -F /home/vagrant/.quickstart/ssh.config.ansible undercloud
    curl -O "https://raw.githubusercontent.com/cschwede/tripleo-swift-ring-tool/master/tripleo_swift_ring_tool.py"

3) Run the `tripleo-swift-ring-tool` and upload the created ring- and
   builderfiles to the undercloud Swift:

    source stackrc
    python tripleo_swift_ring_tool.py overcloud-rings
    upload-swift-artifacts -f overcloud-rings/rings.tar.gz

   The `upload-swift-artifacts` tool will
   create a template in `~/.tripleo/environments/deployment-artifacts.yaml`
   that includes a temporary url that will be used during the deployment. The
   `tripleo-swift-ring-tool` will create a template in
   `~/.tripleo/environments/swift_disks.yaml` with a per-node list of disks to
   prepare for Swift, disabling default ringbuilding and re-enabling the
   mount check.

4) Deploy the overcloud:

    ~/overcloud-deploy.sh

   This will deploy an overcloud and
   - disable the default ring building in TripleO
   - fetch the rings created by tripleo-swift-ring-tool
   - create XFS filesystems on all found blockdevices (except hda/sda/vda)
   - add system uuid hostname aliases

[1]: https://github.com/openstack/tripleo-quickstart
[2]: https://review.openstack.org/358643/
[3]: https://raw.githubusercontent.com/cschwede/tripleo-swift-ring-tool/master/tripleo_swift_ring_tool.py
