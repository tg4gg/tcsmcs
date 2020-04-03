# vim: ai:sw=4:sts=4:expandtab

###########################################################
#
#  Author:        Ricardo Cardenes <rcardenes@gemini.edu>
#
#  2018-05-01 (rjc):
#      Started a GEA export module
###########################################################

import os
import subprocess
import xmlrpclib
from datetime import datetime, timedelta
from itertools import izip, takewhile
import numpy as np
from time import gmtime
from collections import namedtuple
import tempfile
import json

json.encoder.FLOAT_REPR = lambda o: format(o, '.9f')

ARCHIVE_MAX_XMLRPC_SAMPLES = 10000
ARCHIVE_EXPORTER = '/gemsoft/opt/epics/extensions/bin/linux-x86_64/ArchiveExport'
ARCHIVE_EXPORT_DATA_PATH = '/gemsoft/var/data/gea/data/data/{source}/master_index'
ARCHIVE_SITE_URL = {
        'MK': 'http://geanorth.hi.gemini.edu/run/ArchiveDataServer.cgi',
        'CP': 'http://geasouth.cl.gemini.edu/run/ArchiveDataServer.cgi',
        }

ARCHIVE_MAPPING = {
    'cal': 'cal',
    'ref': 'cal',
    'ag': 'ag',
    'cr': 'crcs',
    'ec': 'ecs',
    'gis': 'gis',
    'gm': 'gmos',
    'ws': 'gws',
    'mc': 'mcs',
    'niri': 'niri',
    'm1': 'pcs',
    'm2': 'scs',
    'ao': 'tcs',
    'oiwfs': 'tcs',
    'pwfs1': 'tcs',
    'pwfs2': 'tcs',
    'tcs': 'tcs',
    'las': 'laser',
    'lhx': 'laser',
    'lis': 'laser',
    'ltcss': 'laser',
    'bto': 'bto',
    'nifs': 'nifs',
    'gc': 'gcal',
    'gnirsgate': 'gnirs',
    'nirs': 'gnirs',
    'tc': 'gnirs',
    'bfo': 'pr',
    'fps': 'pr',
    'hbs': 'pr',
    'pr': 'pr',
    'ta': 'sbflab',
    'mc1': 'sbflab',
    'tc1': 'sbflab',
}

def _format_value(value):
    if isinstance(value, float):
        if value > 900000000: # Likely a timestamp
            return '{0:.9f}'.format(value)
        else:
            return str(value)
    elif isinstance(value, datetime):
        return datetime.strftime(value, '%m/%d/%Y %H:%M:%S.%f')
    return str(value)

class ArchiveFileExporter(object):
    def __init__(self, source, bin_exec=ARCHIVE_EXPORTER):
        self.site = 'local'
        self.source = ARCHIVE_EXPORT_DATA_PATH.format(source=source)
        self.bin_exec = bin_exec

    def cmd_line_builder(self, channel, start, end, output=None):
        args = [channel, '-format', 'decimal',
                         '-start', "'{0}'".format(_format_value(start)),
                         '-end', "'{0}'".format(_format_value(end))]

        if output is not None:
            args.extend(['-output', output])

        return [self.bin_exec, self.source] + args

    def retrieve(self, source, channel, start, end):
        raise NotImplementedError("This functionality hasn't been implemented")

def split_timestamp_to_dt(sample):
    return np.datetime64(datetime.utcfromtimestamp(sample['secs'])) + np.timedelta64(sample['nano'], 'ns')

def addtotimestamp(dt, delta):
    if isinstance(dt, datetime):
        return dt + delta
    else:
        return np.datetime64(dt.astype(int) + int(delta.total_seconds() * 1000000), 'ns')

class ArchiveXmlRpcExporter(object):
    def __init__(self, site):
        self.site = site
        self._keys = None
        self.server = xmlrpclib.Server(ARCHIVE_SITE_URL[site])

    def get_key(self, source):
        if self._keys is None:
            self._keys = dict((x['name'], x['key']) for x in self.server.archiver.archives())
        return self._keys[source]

    def _partial_retrieve(self, source, channel, start, end):
        sstart, send = tosecondstimestamp(start), tosecondstimestamp(end)
        ret = self.server.archiver.values(self.get_key(source), [channel],
                                          int(sstart), int(sstart - int(sstart))*1000000000,
                                          int(send), int(send - int(send))*1000000000,
                                          ARCHIVE_MAX_XMLRPC_SAMPLES, 0)[0]['values']
        if len(ret) > 0:
            return [(split_timestamp_to_dt(sample),) + tuple(sample['value']) for sample in ret]
        else:
            return []

    def retrieve(self, source, channel, start, end):
        t1 = tosecondstimestamp(start)
        t2 = tosecondstimestamp(end)
        done = False
        latest_timestamp = None
        while not done:
            samples = self._partial_retrieve(source, channel, t1, t2)
            for sample in samples:
                if latest_timestamp and sample[0] <= latest_timestamp:
                    continue
                yield sample
            if len(samples) < ARCHIVE_MAX_XMLRPC_SAMPLES or tosecondstimestamp(samples[-1][0]) >= t2:
                done = True
            else:
                latest_timestamp = samples[-1][0]
                t1 = addtotimestamp(latest_timestamp, timedelta(microseconds=10))

export_header = """\
# Generated by SWG Export Tools v0.1
# Method: Raw Data

# Data for channel {channel} at {site} follows:
"""

# If site is not None, a remote connection is assumed
def archive_export(system, channel, output, start=None, end=None, site=None, overwrite=False):
    if not overwrite and os.path.exists(output):
        return True

    if site is None:
        cmd = ArchiveFileExporter(system).cmd_line_builder(channel, start=start, end=end, output=output)
        return subprocess.call(cmd) == 0
    else:
        with open(output, 'w+') as outfile:
            exporter = ArchiveXmlRpcExporter(site)
            outfile.write(export_header.format(channel=channel, site=site))
            for sample in exporter.retrieve(system, channel, start, end):
                outfile.write('\t'.join(tuple(_format_value(x) for x in sample)) + '\n')
        return True

def isoformat(dt):
    return dt.isoformat() if isinstance(dt, datetime) else str(dt)

def tosecondstimestamp(dt):
    if isinstance(dt, datetime):
        return (dt - datetime.utcfromtimestamp(0)).total_seconds()
    elif isinstance(dt, np.datetime64):
        return dt.astype(int) / 1000000000.
    return dt

def todatetime64(dt):
    if isinstance(dt, datetime):
        return np.datetime64(dt, 'ns')
    elif isinstance(dt, float):
        nt = int(dt)
        fr = int(round((dt - nt) * 1000000000))
        return np.datetime64((nt * 1000000000) + fr, 'ns')
    elif isinstance(dt, int):
        return np.datetime64(int(dt * 1000000000), 'ns')
    # NOTE: Assume that we got a datetime64 instance...
    return dt

class CacheFile(object):
    def __init__(self, cache_manager):
        self._cm = cache_manager
        self._file = None
        self._group = None
        self._first = None
        self._last = None

    def _close_file(self):
        if self._file is not None:
            self._file.close()
            if self._first is not None:
                self._cm.add_file(self._file.name, self._first, self._last, to_group=self._group)
            else:
                os.remove(self._file.name)

    def _reset_file(self):
        self._file = self._cm.create_temp_file()
        self._group = None
        self._first = None
        self._last = None

    def __enter__(self):
        try:
            self._reset_file()
            return self
        except (OSError, IOError):
            # Re-raise usual exceptions
            raise

    def __exit__(self, type_, value, traceback):
        if type_ is None:
            self._close_file()

    def write(self, stamp, items):
        # TODO:
        # This algorithm is not too thorough. It will detect when a new set of entries overlap with
        # existing interval groups with start <= of the current stamp, and will include the resulting
        # new file inside said existing group, but it won't fuse two high level groups if the new
        # data stream spans both. This would need additional support on the cache manager class
        group = self._cm.get_interval_for_stamp(stamp)
        if group is None:
            self._file.write('\t'.join([isoformat(stamp)] + ["{0:.9f}".format(i) for i in items]) + '\n')
            if self._first is None:
                self._first = stamp
            self._last = stamp
        elif self._group != group:
            if self._group is not None:
                self._close_file()
                self._reset_file()
            self._group = group

class CacheJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.datetime64):
            return tosecondstimestamp(obj)

IntervalIndexEntry = namedtuple('IntervalIndexEntry', 'start end files')
RawIndexEntry = namedtuple('RawIndexEntry', 'start end name')

class RawCacheManager(object):
    def __init__(self, root_dir, site, db, pvname):
        self.root = root_dir
        self.site = site
        self.db = db
        self.pvname = pvname
        self.cache_dir = os.path.join(root_dir, site, db, pvname, 'raw')
        self._intervals = None

    def __contains__(self, stamp):
        return self.get_interval_for_stamp(stamp) is not None

    @property
    def cache_file(self):
        return os.path.join(self.cache_dir, 'index.txt')

    def dump_index(self, intervals):
        if intervals is not None:
            json.dump(
                    fp=open(self.cache_file, 'w'),
                    cls=CacheJsonEncoder,
                    indent=2,
                    obj=[{"_comment": "Data {0} - {1}".format(isoformat(g.start), isoformat(g.end)),
                          "start": g.start,
                          "end": g.end,
                          "files": [{"name": os.path.basename(i.name),
                                     "start": i.start,
                                     "end": i.end}
                                    for i in g.files]}
                         for g in intervals]
                    )

    def load_index(self):
        try:
            result = []
            for group in json.load(open(self.cache_file)):
                result.append(
                        IntervalIndexEntry(
                            start=todatetime64(group['start']),
                            end  =todatetime64(group['end']),
                            files=tuple(
                                RawIndexEntry(
                                    name =r['name'],
                                    start=todatetime64(r['start']),
                                    end  =todatetime64(r['end']))
                                for r in group['files'])))
            return result
        except (IOError, OSError):
            return []

    def get_intervals(self, refresh):
        if self._intervals is None or refresh:
            try:
                self._intervals = self.load_index()
            except (IOError, OSError):
                # Possibly, no cache file
                pass
        return self._intervals or []

    def get_interval_for_stamp(self, stamp, raw=False):
        for group in self.get_intervals(refresh=False):
            if group.start <= stamp <= group.end:
                return group

    def get_intersection(self, start, end, refresh=False):
        result = []
        # Intervals are non-overlapping and sorted by (start, end) points, so the
        # condition for takewhile should work
        for interval in takewhile(lambda x: (x.start <= end and x.end >= start), self.get_intervals(refresh)):
            c1 = interval.start <= start <= interval.end
            c2 = interval.start <= end <= interval.end
            c3 = start <= interval.start and interval.end <= end
            if c1 or c2 or c3:
                result.append(interval)

        return result

    def get_difference(self, start, end, refresh=False):
        intersec = self.get_intersection(start, end, refresh)
        if not intersec:
            return [(start, end)]
        else:
            result = []
            if start < intersec[0].start:
                result.append((start, intersec[0].start))
            start = intersec[0].end
            interval = None
            for interval in intersec[1:]:
                if interval.start > end:
                    result.append((start, end))
                    break
                if interval.start != start:
                    result.append((start, interval.start))
                start = interval.end
            else:
                if interval is None:
                    if end > intersec[0].end:
                        result.append((intersec[0].end, end))
                elif end > interval.end:
                    result.append((interval.end, end))
            return result

    def get_file_name(self, start, end, full_path=False):
        fname = "{0}_{1}".format(isoformat(start), isoformat(end))
        if full_path:
            return os.path.join(self.cache_dir, fname)
        else:
            return fname

    def new_file(self):
        return CacheFile(self)

    def create_temp_file(self):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        return tempfile.NamedTemporaryFile(dir=self.cache_dir, delete=False)

    def add_to_index(self, path, start, end, to_group=None):
        # TODO: This function should make sure that the intervals do not overlap
        #       but we're going to assume it so far.
        new_entry = RawIndexEntry(name=path, start=start, end=end)
        interval_set = set(self.get_intervals(refresh=False))

        if to_group is None:
            new_group = IntervalIndexEntry(start=start, end=end, files=(new_entry,))
        else:
            new_files = files=tuple(sorted(to_group.files + (new_entry,)))
            new_group = IntervalIndexEntry(start=min(f.start for f in new_files),
                                           end=max(f.end for f in new_files),
                                           files=tuple(sorted(to_group.files + (new_entry,))))
            interval_set.remove(to_group)
        interval_set.add(new_group)
        self._intervals = sorted(interval_set)
        self.dump_index(self._intervals)

    def add_file(self, path, start, end, is_temp=True, to_group=None):
        if is_temp:
            newfn = self.get_file_name(start, end, full_path=True)
            os.rename(path, newfn)
            path = newfn
        self.add_to_index(path, start, end, to_group=to_group)

    def iterate_index(self, index_entry):
        if not isinstance(index_entry, IntervalIndexEntry):
            raise TypeError("Not an IntervalIndexEntry")
        for raw_entry in index_entry.files:
            with open(os.path.join(self.cache_dir, raw_entry.name)) as source:
                for line in source:
                    entry = line.strip().split()
                    yield (np.datetime64(entry[0], 'ns'),) + tuple(float(x) for x in entry[1:])

def map_pv_to_db(pvname):
    key = (pvname.split(':') if ':' in pvname else pvname.split('.'))[0]
    return ARCHIVE_MAPPING[key]

def sorted_zip(*args):
    candidates = []
    for arg in args:
        it = iter(arg)
        try:
            candidates.append((it.next(), it))
        except StopIteration:
            pass

    while candidates:
        candidates = list(reversed(candidates))
        next_item, it = candidates.pop()
        yield next_item
        try:
            candidates.append((it.next(), it))
        except StopIteration:
            pass


class DataManager(object):
    def __init__(self, exporter, root_dir=None):
        self.exp = exporter
        self.root = root_dir if root_dir is not None else os.getcwd()

    def getData(self, pvname, start, end, db=None, cache_data=True, cache_query=False):
        """
        `pvname`: The channel access descriptor to the desired Process Variable
        `start`:  `datetime` compatible object with the first timestamp for the query
        `end`:    `datetime` compatible object with the last timestamp for the query
        `db`:     The name for the database which stores the data. A number of common
                  prefixes will be automatically mapped to databases, but some of them
                  are not 1-to-1, and thus `db` can be explicitly named.
        `cache_data`:
                  Whether to cache the downloaded raw data for this particular query,
                  or not. By default this is `True`. Queries overlapping with cached data
                  won't need to be downloaded again in full.
        `cache_query`:
                  Whether to cache the current query for reuse. A separate binary cache
                  is created for this specific query. Beware, unlike the data downloaded,
                  affected by `cache_data`, overlapping queries are stored separately,
                  in full. By default, this argument is `False`.
        """
        if db is None:
            db = map_pv_to_db(pvname)

        start = todatetime64(start)
        end = todatetime64(end)

        rcm = RawCacheManager(self.root, self.exp.site, db, pvname)
        # Gather missing intervals
        overlap = rcm.get_intersection(start, end)
        difference = rcm.get_difference(start, end)
        for interval in sorted_zip(overlap, difference):
            if isinstance(interval, IntervalIndexEntry):
                for entry in rcm.iterate_index(interval):
                    if start <= entry[0] <= end:
                        yield entry
            else:
                istart, iend = interval
                with rcm.new_file() as dest:
                    for entry in self.exp.retrieve(db, pvname, istart, iend):
                        dest.write(entry[0], entry[1:])
                        yield entry

def get_exporter(source):
    """
    If `source` is one of `'MK'` or `'CP'`, an instance of `ArchiveXmlRpcExporter` will
    be returned. Otherwise, an instance of `ArchiveFileExporter` initialized with `source`
    as the database name.
    """
    if source in ARCHIVE_SITE_URL:
        return ArchiveXmlRpcExporter(source)
    else:
        return ArchiveFileExporter(source)

if __name__ == '__main__':
    # TEST CODE
    dm = DataManager(get_exporter('CP'), root_dir='/tmp/rcm')
    data = list(dm.getData('mc:azDemandPos', start=datetime(2018, 5, 4), end=datetime(2018, 5, 4, 6)))      # Initial bulk download
    data = list(dm.getData('mc:azDemandPos', start=datetime(2018, 5, 4), end=datetime(2018, 5, 4, 6, 10)))  # Incremental download
    data = list(dm.getData('mc:azDemandPos', start=datetime(2018, 5, 5), end=datetime(2018, 5, 4, 6, 30)))  # No download (start > end)
    data = dm.getData('mc:azDemandPos', start=datetime(2018, 5, 4, 6, 5), end=datetime(2018, 5, 4, 6, 35))
    for val in data:
        print val
