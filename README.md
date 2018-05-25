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

## Plotting tool

This tools goal is to offer a straightforward way to identify anomalies in the TCS tracking. It is a merge of several scripts that sprouted at the very initial stage of this analysis effort. It makes use of the features of swglib. 

Here the areas of interest for plotting are explained: [Data processing and analysis](https://docs.google.com/document/d/1cZ4VJncNP1fW5Nk8Uf9sKKBAjShs3a1wL9Vg5DxGrYs/edit#heading=h.ccazbon1vexl)

And here the instructions to use the new tool are shown: [Single Tracking Plot tool](https://docs.google.com/document/d/1wCf2ctd0chd1QXGVKq35qSoBzgNS0QFkFRKSl6h7aKg/edit?usp=sharing])

This two docs should be merged together for better readability. Here is an execution example:

```
python plotTrackingArray.py -axis el -mode vel -date 2018-05-07 -day
python plotTrackingArray.py -h
usage: plotTrackingArray.py [-h] [-sys SYSTEM] [-date DATE] [-day]
                            [-scale SCALE] [-cols COLS] [-axis AXIS]
                            [-time TIME_RNG] [-mode MODE]

This script allows analyzing different aspects of the TCS tracking performance
and behaviour.

optional arguments:
  -h, --help            show this help message and exit
  -sys SYSTEM, --system SYSTEM
                        System to be analyzed: tcs, mcs or both
  -date DATE, --date DATE
                        Date - format YYYY-MM-DD
  -day, --eng_mode      If used daytime will be analyzed 6am-6pm
  -scale SCALE, --scale SCALE
                        Scale to be applied to data
  -cols COLS, --columns COLS
                        Columns to be plotted
  -axis AXIS, --axis AXIS
                        Axis to be plotted, can be az or el
  -time TIME_RNG, --time_range TIME_RNG
                        Specific time range format: HHMM-HHMM
  -mode MODE, --plot_mode MODE
                        Different ways of representing the data, could be:
                        execTime, posDiff, vel or period
```



