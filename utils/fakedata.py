import random
import math
import time
import numpy
import json
#import matplotlib
#matplotlib.use('Qt5Agg')
#import matplotlib.pyplot as plt



total_supply = 10000
bins = 800
duration = 14*24*60*60

price_start = 2e18
price_exponent = 3
price_constant = 1574640000

time_now = time.time()

timestamped = [ (time_now + i) for i in range(0, duration, 60)]
#price= price_start * (1+elapsed_seconds) / (1+elapsed_seconds + elapsed_seconds^price_exponent / price_constant)`

price_graph = []
for i in timestamped:
    price= price_start * (1+i) / (1+i + i**price_exponent / price_constant)
    price_graph.append(price)


max_bid = 1e2

bids = []
token_buys = []
funding_target = []
for current_price in price_graph:
    bid = max_bid * numpy.random.lognormal(0, 0.5)
    total_supply -= bid / current_price
    bids.append(bid)
    funding_target.append(price_start - (bid * current_price))
    token_buys.append(bid/current_price)
    if total_supply < 0:
        break

target, target_bins = numpy.histogram(timestamped[:len(bids)],
                              bins=bins,
                              weights=price_graph)
ar, ar_bins = numpy.histogram(timestamped[:len(bids)],
                              bins=bins,
                              weights=bids)

price, price_bins = numpy.histogram(timestamped[:len(bids)],
                              bins=bins,
                              weights=price_graph)

#plt.figure(1)
#plt.plot(ar_bins[:-1], price, 'r')
#plt.plot(ar_bins[:-1], numpy.cumsum(ar).tolist(), 'g')
#plt.plot(ar_bins[:-1], target, 'b')
#plt.show()
ret = {
    'timestamped_bins': [int(x) for x in ar_bins[:-1].tolist()],
    'bin_sum': [int(x) for x in ar.tolist()],
    'bin_cumulative_sum': [int(x) for x in numpy.cumsum(ar).tolist()],
    'funding_target': [int(x) for x in target.tolist()],
    'price': [int(x) for x in price.tolist()],
}
print json.dumps(ret)
