
import React from 'react';
import PropTypes from 'prop-types';

import { format } from 'd3-format';
import { timeFormat } from 'd3-time-format';

import { ChartCanvas, Chart } from 'react-stockcharts';
import {
  LineSeries,
  ScatterSeries,
  CircleMarker
} from 'react-stockcharts/lib/series';
import { XAxis, YAxis } from 'react-stockcharts/lib/axes';
import {
  CrossHairCursor,
  MouseCoordinateX,
  MouseCoordinateY,
} from 'react-stockcharts/lib/coordinates';

import { discontinuousTimeScaleProvider } from 'react-stockcharts/lib/scale';
import {
  OHLCTooltip,
} from 'react-stockcharts/lib/tooltip';
import { fitWidth } from 'react-stockcharts/lib/helper';
import { last } from 'react-stockcharts/lib/utils';

import { LabelAnnotation, Label, Annotate } from 'react-stockcharts/lib/annotation';

class ValueChart extends React.Component {
  render() {
    const { data: initialData, type, width, ratio } = this.props;
    //console.log('initialData', JSON.stringify(initialData));
    const xScaleProvider = discontinuousTimeScaleProvider
      .inputDateAccessor(d => d.date);
    const {
      data,
      xScale,
      xAccessor,
      displayXAccessor,
    } = xScaleProvider(initialData);
    const xExtents = [
      xAccessor(data[data.length-1]),
      xAccessor(data[data.length - 20])
    ];
    const margin = { left: 70, right: 140, top: 80, bottom: 30 };
    const height = 400;
    console.log('xExtents', xExtents);

    const [yAxisLabelX, yAxisLabelY] = [
      width - margin.left - 60,
      (height - margin.top - margin.bottom) / 2
    ];

    //console.log('data', JSON.stringify(data));
    return React.createElement(ChartCanvas, {
        ratio, 
        width,
        height,
        margin,
        type,
        pointsPerPxThreshold: 1,
        seriesName: 'MSFT',
        data,
        xAccessor,
        displayXAccessor,
        xScale,
      },
      React.createElement(Label, {
          x: (width - margin.left - margin.right) / 2,
          y: - margin.top / 2,
          fontSize: '20',
          text: 'Market Cap & Valuation Graph'
        }
      ),
      React.createElement(Chart, {
          id: 1,
          //yExtents: d => [d.marketCap, d.valuation]
          yExtents: d => [
            d.marketCap + 5 * Math.pow(10, Math.log10(d.marketCap) - 3), 
            d.valuation - 5 * Math.pow(10, Math.log10(d.valuation) - 3)
          ]
        },
        React.createElement(XAxis, {
          axisAt: 'bottom',
          orient: 'bottom',
        }),
        React.createElement(YAxis, {
          axisAt: 'right',
          orient: 'right',
          tickFormat: format(',.3f'),
          ticks: 10
        }),
        React.createElement(Label, {
            x: yAxisLabelX,
            y: yAxisLabelY,
            rotate: -90,
            fontSize: '12',
            text: 'Tokens * Price in ETH'
          }
        ),
        React.createElement(MouseCoordinateX, {
          at: 'bottom',
          orient: 'bottom',
          rectWidth: 130,
          displayFormat: timeFormat('%B %d, %X')
        }),
        React.createElement(MouseCoordinateY, {
          at: 'right',
          orient: 'right',
          rectWidth: 130,
          displayFormat: format(',.3f') 
        }),
        React.createElement(CrossHairCursor),
        React.createElement(LineSeries, {
          yAccessor: d => d.marketCap,
          strokeDasharray: 'Solid' 
        }),
        React.createElement(LineSeries, {
          yAccessor: d => d.valuation,
          stroke: '#D78050',
          strokeDasharray: 'Solid' 
        })
      )
    )
  }
}

ValueChart = fitWidth(ValueChart);

export default ValueChart;
