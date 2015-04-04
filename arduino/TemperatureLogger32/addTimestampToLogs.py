from os import listdir
from os.path import isfile, join
import datetime
import calendar

path = '.'

filenames = sorted([ f for f in listdir(path) \
            if isfile(join(path,f)) and f.lower().endswith('.log')])

for filename in filenames:

    infile = open(filename, "r")
    outfile = open("c_"+filename, "w")

    for line in infile:
        fields = line.split(',')
        date = fields[0]
        time = fields[1]

        da = date.split("/")
        ta = time.split(":")
        dt = datetime.datetime(int(da[0]), int(da[1]), int(da[2]), int(ta[0]), int(ta[1]), int(ta[2]))
        timestamp = calendar.timegm(dt.utctimetuple())

        outfile.write("%s,%s"%(timestamp,line))
    
    outfile.close()
    infile.close()

