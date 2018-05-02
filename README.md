# SWGLib

An attempt to rationalize and organize the Python that we've been using to
make sense of the TCS/MCS problem, in the hopes that we can use it at a
later point as a standard tool.

## Data Harvesting

```
>>> from swglib.export import archive_export
>>> system = 'mcs'
>>> channel = 'mc:followA.J'
>>> outfile = '/tmp/{}.sample'.format(channel)
>>> archive_export(system, channel, output=outfile, site='CP', start=datetime(2018, 5, 1), end=datetime(2018, 5, 1, 0, 1))
```

The code above will connect to geasouth.cl.gemini.edu and query the required data over XML-RPC,
dumping the result to the file specified as the `output` argument. It won't clobber existing
data (pass `overwrite=True` to override this behavior).

If `site` is not specified, the code will assume that it is being run on a GEA machine, and use
`ArchiveExport` locally, instead.
