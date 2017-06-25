# Learn about API authentication here: https://plot.ly/python/getting-started
# Find your api_key here: https://plot.ly/settings/api
import collections
import plotly.plotly as py
import plotly.graph_objs as go
from plotly import tools


def draw(ticks):

    if True:  # remove most of initial auction
        ticks_r = [t for t in ticks if t['CT_Reserve'] > 0]
        ticks = ticks[-int(len(ticks_r) * 1.2):]

    MARKETSIM = bool([t for t in ticks if 'Market_Price' in t])

    def tdata(key):
        return [(t['time'], t[key]) for t in ticks if key in t]

    traces1 = []
    traces2 = []
    traces3 = []
    traces4 = []

    def chart(key, t=traces1):
        d = tdata(key)
        assert d
        name = key.replace('_', ' ')
        s = go.Scatter(x=[_[0] for _ in d], y=[_[1] for _ in d], name=name)
        t.append(s)

    def chart2(key):
        chart(key, traces2)

    # PRICES
    chart('CT_Sale_Price')
    if MARKETSIM:
        chart('Market_Price')
    chart('CT_Simulated_Price')
    chart('CT_Purchase_Price')
    chart('CT_Reserve_Based_Price')

    # Valuations
    chart2('MktCap')
    chart2('CT_Reserve')
    chart2('Max_Valuation')
    chart2('Valuation')

    # Supplies
    chart('CT_Supply', traces3)
    chart('CT_Notional_Supply', traces3)
    chart('CT_Simulated_Supply', traces3)
    chart('CT_Skipped_Supply', traces3)
    chart('CT_Arithmetic_Supply', traces3)

    # Changes
    if MARKETSIM:
        for key in ['CT_Supply', 'CT_Sale_Price', 'CT_Purchase_Price', 'CT_Spread',
                    'MktCap', 'Valuation', 'CT_Reserve', 'Market_Price']:
            chart('Change_' + key, traces4)

    ######
    SHOW = collections.OrderedDict(
        Prices=traces1,
        # Valuation=traces2,
        # Supply=traces3,
        # Changes=traces4
    )

    fig = tools.make_subplots(rows=len(SHOW), cols=1,
                              subplot_titles=SHOW.keys())

    for i, traces in enumerate(SHOW.values()):
        for t in traces:
            fig.append_trace(t, i + 1, 1)

    fig['layout'].update(title='Continuous Token')
    plot_url = py.plot(fig, filename='continuoustoken')
