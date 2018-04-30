import math
import numpy as np
#    /* tick = floor ( traw * TICKHZ + 1.0 ) / TICKHZ; */

"""
traw = 1123456700.3 #Timestamp
print "Input traw=",traw
for TICKHZ in range(10, 100, 10):
	tick = math.floor( traw * TICKHZ + 1.0 ) / TICKHZ

	print "multiply={0}, floor={1}, div={2}".format(traw * TICKHZ + 1.0, math.floor( traw * TICKHZ + 1.0 ), tick)
	print "traw={0} TICKHZ={1} --> tick={2} diff={3}".format(traw, TICKHZ, tick, tick-traw)


TICKHZ = 20
for traw in np.arange(10000000.05, 10000002.0, 0.1):
	tick = math.floor( traw * TICKHZ + 1.0 ) / TICKHZ
	print "traw={0} TICKHZ={1}, MULTIPLY={3} FLOOR={4} --> tick={2} diff={3:10.5f}ms".format(traw, TICKHZ, tick, (tick-traw)*1000.0, (traw * TICKHZ + 1.0) , math.floor( traw * TICKHZ + 1.0 ))
"""

def calculate(traw):
	TICKHZ = 20.0
	tick = math.floor( traw * TICKHZ + 1.0 ) / TICKHZ
	print "traw={0} MULTIPLY={1} FLOOR={2} --> tick={3} diff={4:10.5f}ms".format(\
		traw, (traw * TICKHZ + 1.0), math.floor( traw * TICKHZ + 1.0 ), tick, (tick-traw)*1000.0)


calculate(1524043293.1864778996)
calculate(1524043293.3868739605)