from subprocess import call
import sys, datetime, shlex


dt = datetime.datetime(2018, 1, 1, 18, 00, 00)
end = datetime.datetime(2018, 3, 29 ,6, 00, 00)

step = datetime.timedelta(hours=12)
indexfile = '/gemsoft/var/data/gea/data/data/mcs/master_index'
channel = 'mc:azCurrentVel'
outpath = '/export/home/software/tgagg/data/cp/mcs/azCurrentVel/txt'
site = 'cp'

if (len(sys.argv) < 5):
    print  "Usage: python archiveExport.py <system> <channel name> <begin date> <end date> [hd]"
    print  "	    example: $python archiveExport.py mcs mc:azCurrentVel 2018-03-28 2018-03-29"
    sys.exit()

system = sys.argv[1]
channel = sys.argv[2]
dt = datetime.datetime.strptime(sys.argv[3]+' 18:00','%Y-%m-%d %H:%M') 
end = datetime.datetime.strptime(sys.argv[4]+' 6:00','%Y-%m-%d %H:%M') 
dayStr = ''
if (len(sys.argv)>5 and 'd' in sys.argv[5]):
    print 'Gathering daytime data'
    dayStr = 'day_'
    dt = dt.replace(hour=6)
    end = end.replace(hour=18)

outpath = '/archive/tcsmcs/data/'+site+'/'+system+'/'+channel[channel.find(':')+1:].replace(':', '_')+'/txt'
indexfile = '/gemsoft/var/data/gea/data/data/'+system+'/master_index'

call(shlex.split('mkdir -p '+outpath))

while dt < end:
    daystart = dt.strftime('%m/%d/%Y %H:%M:%S')
    outname = "%s/%s_%s_%s_%sexport.txt" % (outpath, dt.strftime('%Y-%m-%d'), site, channel.replace(":","-"), dayStr)
    dt += step
    dayend = dt.strftime('%m/%d/%Y %H:%M:%S')
    command = "ArchiveExport %s -m \"%s\" -s \"%s\" -e \"%s\" -o %s" % (indexfile, channel, daystart, dayend, outname)
    if (len(sys.argv)>5 and 'h' in sys.argv[5]):
        command += ' -precision 20'
    else:
        print "Not using high precision add \'h\' as the last argument to use higher precision."
    dt += step
    args = shlex.split(command)
    print "Processing %s ..." % (outname)
    print args	
    call(args)

print "done"
    

