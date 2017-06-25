# Learn about API authentication here: https://plot.ly/python/getting-started
# Find your api_key here: https://plot.ly/settings/api

import plotly.plotly as py
import plotly.graph_objs as go
from plotly import tools


def draw(ticks):

    if False:  # remove most of initial auction
        ticks_r = [t for t in ticks if t['CT_Reserve'] > 0]
        ticks = ticks[-int(len(ticks_r) * 1.1):]

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
    chart('CT_Virtual_Supply', traces3)
    chart('CT_Virtual_Supply_Auction', traces3)
    chart('CT_Skipped_Supply', traces3)
    chart('CT_Reserve_Based_Supply', traces3)

    # Changes
    for key in ['CT_Supply', 'CT_Sale_Price', 'CT_Purchase_Price', 'CT_Spread',
                'MktCap', 'Valuation', 'CT_Reserve', 'Market_Price']:
        chart('Change_' + key, traces4)

    fig = tools.make_subplots(rows=4, cols=1,
                              subplot_titles=('Prices', 'Valuation', 'Supply', 'Changes'))

    for t in traces1:
        fig.append_trace(t, 1, 1)
    for t in traces2:
        fig.append_trace(t, 2, 1)
    for t in traces3:
        fig.append_trace(t, 3, 1)
    for t in traces4:
        fig.append_trace(t, 4, 1)

    fig['layout'].update(title='Continuous Token Auction')
    # fig['layout'].update(yaxis=dict(title='price'))
    # fig['layout'].update(yaxis2=dict(title='value'))
    plot_url = py.plot(fig, filename='continuoustoken')
