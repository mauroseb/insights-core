"""
fstab - file ``/etc/fstab``
===========================

Parse the ``/etc/fstab`` file into a list of lines.  Each line is a dictionary
of fields, named according to their definitions in ``man fstab``:

* ``fs_spec`` - the device to mount
* ``fs_file`` - the mount point
* ``fs_vfstype`` - the type of file system
* ``fs_mntops`` - any mount options
* ``fs_freq`` - the dump frequency - not used
* ``fs_passno`` - check the filesystem on reboot in this pass number

``fs_freq`` and ``fs_passno`` are recorded as integers if found, and zero if
not present.

The ``fs_mntops`` mount options are converted to a dictionary, so that each
option's value set to True so it can be conveniently searched.

This data, as above, is available in the ``data`` property.  The class also
presents the ``rows`` property, which is the same rows converted to
objects:

* Each column becomes a property with the same name.
* The mount options are a special object with properties corresponding to the
  common mount options: ``rw``, ``ro``, ``relatime``, ``seclabel``,
  ``attr2``, ``inode61``, and ``noquota``, as well as the ``rq``, ``sw``, and
  ``xx`` options which are not documented in ``man mount``.

The data for each mount point is also available via the ``mounted_on``
property; the data is the same as that stored in the ``rows`` list.

Typical content of the ``fstab`` looks like::

    #
    # /etc/fstab
    # Created by anaconda on Fri May  6 19:51:54 2016
    #
    /dev/mapper/rhel_hadoop--test--1-root /                       xfs     defaults        0 0
    UUID=2c839365-37c7-4bd5-ac47-040fba761735 /boot               xfs     defaults        0 0
    /dev/mapper/rhel_hadoop--test--1-home /home                   xfs     defaults        0 0
    /dev/mapper/rhel_hadoop--test--1-swap swap                    swap    defaults        0 0

    /dev/sdb1 /hdfs/data1 xfs rw,relatime,seclabel,attr2,inode64,noquota 0 0
    /dev/sdc1 /hdfs/data2 xfs rw,relatime,seclabel,attr2,inode64,noquota 0 0
    /dev/sdd1 /hdfs/data3 xfs rw,relatime,seclabel,attr2,inode64,noquota 0 0

    localhost:/ /mnt/hdfs nfs rw,vers=3,proto=tcp,nolock,timeo=600 0 0

    nfs_hostname.redhat.com:/nfs_share/data     /srv/rdu/cases/000  nfs     ro,defaults,hard,intr,bg,noatime,nodev,nosuid,nfsvers=3,tcp,rsize=32768,wsize=32768     0

Examples:

    >>> fstab = shared[FSTab]
    >>> len(fstab)
    9
    >>> fstab.data[0]['fs_spec'] # Note that data is a list not a dict here
    '/dev/mapper/rhel_hadoop--test--1-root'
    >>> fstab.data[0]['fs_mntops']
    'defaults'
    >>> fstab.rows[0].fs_spec
    '/dev/mapper/rhel_hadoop--test--1-root'
    >>> fstab.rows[0].fs_mntops.defaults
    True
    >>> fstab.rows[0].fs_mntops.relatime
    False
    >>> fstab.mounted_on['/hdfs/data3'].fs_spec
    '/dev/sdd1'

"""

from collections import namedtuple

from .. import Mapper, mapper, get_active_lines, parse_table
from ..mappers import optlist_to_dict

FS_HEADINGS = "fs_spec                               fs_file                 fs_vfstype fs_mntops    fs_freq fs_passno"

type_info = namedtuple('type_info', field_names=['type', 'default'])


class MountOpts(object):
    """
    An object representing the mount options found in the ``fs_mntops``
    field of the fstab entry.  Each option in the comma-separated list is
    a key, and 'key=value' pairs such as 'gid=5' are split so that e.g. the
    key is 'gid' and the value is '5'.  Otherwise, the key is the option
    name and its value is 'True'.

    In addition, the properties ``rw``, ``rq``, ``ro``, ``sw``, ``xx``,
    ``relatime``, ``seclabel``, ``attr2``, ``inode64`` and ``noquota`` will
    always be available and are False if not defined in the options list.
    """
    type_infos = {
        'rw': type_info(bool, False),
        'rq': type_info(bool, False),
        'ro': type_info(bool, False),
        'sw': type_info(bool, False),
        'xx': type_info(bool, False),
        'relatime': type_info(bool, False),
        'seclabel': type_info(bool, False),
        'attr2': type_info(bool, False),
        'inode64': type_info(bool, False),
        'noquota': type_info(bool, False)
    }

    def __init__(self, data):
        self.data = data
        for k, v in MountOpts.type_infos.iteritems():
            if k not in data:
                data[k] = v.default

        for k, v in data.iteritems():
            setattr(self, k, v)


class FSTabEntry(object):
    """
    An object representing an entry in ``/etc/fstab``.  The fields are
    stored as attributes.  ``fs_mntops`` is a MountOpts object.
    """
    def __init__(self, data):
        for k, v in data.iteritems():
            v = v if k != 'fs_mntops' else MountOpts(v)
            setattr(self, k, v)


@mapper("fstab")
class FSTab(Mapper):
    """
    Parse the content of ``/etc/fstab``.

    This object provides the '__len__' and '__iter__' methods to allow it to
    be used as a list to iterate over the ``rows`` data, e.g.::

        >>> if len(fstab) > 0:
        >>>     for fs in fstab:
        >>>         print fs.fs_file

    Attributes:
        data (list): a list of parsed fstab entries as dictionaries.
        rows (list): a list of parsed fstab entries as FSTabEntry objects.
        mounted_on (dict): a dictionary of FSTabEntry objects keyed on mount
            point.
    """
    def __len__(self):
        return len(self.rows)

    def __iter__(self):
        for row in self.rows:
            yield row

    def parse_content(self, content):
        """
        Parse each line in the file ``/etc/fstab``.
        """
        fstab_output = parse_table([FS_HEADINGS] + get_active_lines(content))
        for line in fstab_output:
            line['fs_freq'] = int(line['fs_freq']) if 'fs_freq' in line else 0
            line['fs_passno'] = int(line['fs_passno']) if 'fs_passno' in line else 0
            # optlist_to_dict converts 'key=value' to key: value and
            # 'key' to key: True
            line['fs_mntops'] = optlist_to_dict(line['fs_mntops'])
        self.data = fstab_output
        self.rows = [FSTabEntry(datum) for datum in self.data]
        # assert: all mount points of valid entries are unique by definition
        self.mounted_on = {row.fs_file: row for row in self.rows}
