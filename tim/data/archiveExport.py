from subprocess import call
import sys, datetime, shlex


dt = datetime.datetime(2018, 3, 11, 18, 00, 00)
end = datetime.datetime(2018, 3, 18, 6, 00, 00)

step = datetime.timedelta(hours=12)
indexfile = '/gemsoft/var/data/gea/data/data/mcs/master_index'
#indexfile = '/gemsoft/var/data/gea/data/data/crcs/master_index'
channel = 'mc:azPmacPosError'
#channel = 'mc:azDemandPos'
#channel = 'cr:crDemandPos'
outpath = '/export/home/software/tgagg/mcs'
#outpath = '/export/home/software/mrippa/crcs'
site = 'CPO'

while dt < end:
    daystart = dt.strftime('%m/%d/%Y %H:%M:%S')
    outname = "%s/%s_%sexport.txt" % (outpath, dt.strftime('%Y-%m-%d'), site)
    dt += step
    dayend = dt.strftime('%m/%d/%Y %H:%M:%S')
    command = "ArchiveExport %s -m \"%s\" -s \"%s\" -e \"%s\" -o %s" % (indexfile, channel, daystart, dayend, outname)
    dt += step
    args = shlex.split(command)
    print "Processing %s ..." % (outname)
    print args	
    call(args)

print "done"
    

