import time
import numpy
import click
import random


def generate(kwargs):
    total_supply = kwargs['total_supply']
    bins = kwargs['bins']
    duration = kwargs['duration']

    price_start = kwargs['price_start']
    price_exponent = kwargs['price_exponent']
    price_constant = kwargs['price_constant']

    time_now = kwargs['start_time']

    max_bid = 1e10

    timestamped = [(time_now + i) for i in range(0, duration, 3600)]

    price_graph = []
    for i in timestamped:
        t = i - time_now
        price = price_start * ((1 + t) / (1 + t + ((t ** price_exponent) / price_constant)))
        price_graph.append(price)

    # probability density function
    pdf = lambda x, sigma, mu: (numpy.exp(-(numpy.log(x) - mu)**2 / (2 * sigma**2)) /
                                (x * sigma * numpy.sqrt(2 * numpy.pi)))

    bids = []
    token_buys = []
    funding_target = []
    tokens_left = total_supply
    sigma = 1
    mu = 0
    for current_price in price_graph:
        bid = max_bid * pdf(price_graph.index(current_price) / len(price_graph) * 2.5 + 0.01,
                            sigma, mu) * random.random()
        tokens_left -= bid / current_price
        bids.append(bid)
        funding_target.append((tokens_left) * current_price)
        token_buys.append(bid / current_price)
        if total_supply < 0:
            break

    ar, ar_bins = numpy.histogram(timestamped[:len(bids)],
                                  bins=bins,
                                  weights=bids)
    price_ar = numpy.interp(numpy.arange(0, len(price_graph), len(price_graph) / bins),
                            numpy.arange(0, len(price_graph)), price_graph)

    target_ar = numpy.interp(numpy.arange(0, len(funding_target), len(funding_target) / bins),
                             numpy.arange(0, len(funding_target)), funding_target)
    token_buys_ar = numpy.interp(numpy.arange(0, len(token_buys), len(token_buys) / bins),
                                 numpy.arange(0, len(token_buys)), token_buys)
    return {
        'timestamped_bins': [int(x) for x in ar_bins[:-1].tolist()],
        'bin_sum': [int(x) for x in ar.tolist()],
        'bin_cumulative_sum': [int(x) for x in numpy.cumsum(ar).tolist()],
        'funding_target': target_ar.tolist(),
        'token_buys': token_buys_ar.tolist(),
        'price': price_ar.tolist()
    }


def plot(data):
    import matplotlib.pyplot as plt
    import matplotlib.dates as md
    import datetime as dt

    def adjust_xaxis():
        ax = plt.gca()
        xfmt = md.DateFormatter('%Y-%m-%d %H:%M:%S')
        ax.xaxis.set_major_formatter(xfmt)
        plt.subplots_adjust(bottom=0.2)
        plt.xticks(rotation=25)

    def remove_xticks():
        ax = plt.gca()
        ax.set_xticklabels([])
        ax.set_xticks([])
    plt.figure(1)

    # plotting price graph
    plt.subplot(511)
    plt.ylabel('price')
    remove_xticks()
    dates = [dt.datetime.fromtimestamp(ts) for ts in data['timestamped_bins']]
    plt.plot(dates, data['price'], 'r')

    # plotting  sum
    plt.subplot(512)
    remove_xticks()
    plt.ylabel('bids')
    plt.bar(dates, data['bin_sum'], 0.1)

    # plotting cumulative sum
    plt.subplot(513)
    remove_xticks()
    plt.ylabel('token buys')
    plt.bar(dates, data['token_buys'], 0.1)

    # plotting funding target
    plt.subplot(514)
    remove_xticks()
    plt.ylabel('target [Eth]')
    plt.plot(dates, data['funding_target'], 'r')

    # plotting cumulative sum
    plt.subplot(515)
    adjust_xaxis()
    plt.ylabel('bids total')
    plt.plot(dates, data['bin_cumulative_sum'], 'r')
    plt.show()


@click.command()
@click.option(
    '--total-supply',
    default=10000,
    type=int,
    help='total token supply (tokens)'
)
@click.option(
    '--bins',
    default=800,
    type=int,
    help='bins in the output'
)
@click.option(
    '--duration',
    default=14 * 24 * 60 * 60,
    type=int,
    help='duration of the auction (seconds)'
)
@click.option(
    '--price-start',
    default=2e18,
    type=int,
    help='price start (wei)'
)
@click.option(
    '--price-exponent',
    default=3,
    type=float,
    help='price exponent'
)
@click.option(
    '--price-constant',
    default=1574640000,
    type=int,
    help='price constant'
)
@click.option(
    '--start-time',
    default=time.time(),
    type=int,
    help='price constant'
)
@click.option(
    '--plot',
    is_flag=True,
    default=False,
    help='display result (requires matplotlib)'
)
@click.option(
    '--json',
    is_flag=True,
    default=False,
    help='print result as a JSON to stdout'
)
def main(**kwargs):
    data = generate(kwargs)
    if kwargs['plot']:
        plot(data)
    if kwargs['json']:
        import json
        print(json.dumps(data))


if __name__ == "__main__":
    main()
