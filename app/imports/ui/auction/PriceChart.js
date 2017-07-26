import React, { Component } from 'react';
import d3 from 'd3';

/*import { ChartCanvas, Chart, series, scale, coordinates, tooltip, axes, helper } from 'react-stockcharts';


const { LineSeries, ScatterSeries, CircleMarker, SquareMarker, TriangleMarker } = series;
const { discontinuousTimeScaleProvider } = scale;

const { CrossHairCursor, MouseCoordinateX, MouseCoordinateY } = coordinates;

//const { OHLCTooltip } = tooltip;
const { OHLCTooltip, MovingAverageTooltip, HoverTooltip } = tooltip;
const { XAxis, YAxis } = axes;
const { fitWidth, TypeChooser } = helper;
*/

import { ChartCanvas, Chart } from "react-stockcharts";
import {
  ScatterSeries,
  LineSeries,
  CircleMarker
} from "react-stockcharts/lib/series";
import { XAxis, YAxis } from "react-stockcharts/lib/axes";

import { discontinuousTimeScaleProvider } from "react-stockcharts/lib/scale";
import {
  HoverTooltip,
} from "react-stockcharts/lib/tooltip";
//import { ema } from "react-stockcharts/lib/indicator";
import { fitWidth } from "react-stockcharts/lib/helper";
import { last } from "react-stockcharts/lib/utils";

import {
  CrossHairCursor,
  MouseCoordinateX,
  MouseCoordinateY,
} from "react-stockcharts/lib/coordinates";

import { scaleTime } from "d3-scale";
import { format } from "d3-format";
import { timeFormat } from "d3-time-format";


mockData = [{"auctionPrice":10085363,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10085363,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10085363,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10085363,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10085363,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10084551,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10084551,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10084551,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10084551,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10084551,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10084551,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10083333,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10083333,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10083333,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10083333,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10083333,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10083283,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10083283,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10083283,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10083283,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10083283,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10083283,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645},{"auctionPrice":10082319,"mintSale":7810249683,"mintPurchase":4405124838,"supply":454016645}]

class PriceChart extends Component {
  constructor(props) {
    super(props);
    this.state = {};
  }

  removeRandomValues(data) {
    return data.map((item) => {
      const numberOfDeletion = Math.floor(Math.random() * keyValues.length) + 1;
      for (let i = 0; i < numberOfDeletion; i += 1){
        const randomKey = keyValues[Math.floor(Math.random() * keyValues.length)];
        item[randomKey] = undefined;
      }
      return item;
    });
  }

  render() {
    let { data: initialData, width, ratio, type, startTimestamp, endTimestamp } = this.props;
    console.log('PriceChart data', JSON.stringify(data))
    //data = mockData;

    /*if(!data || !data[0]) {
      return null;
    }*/


    if(!initialData || !initialData[0] || !initialData[1]) {
      return null;
    }
    
    //let last = data[data.length - 1];

    // remove some of the data to be able to see
    // the tooltip resize
    //data = this.removeRandomValues(data);

    //const xAccessor = d => new Date(d.timestamp);
    //const start = xAccessor(last(data));
    //const end = xAccessor(data[Math.max(0, data.length - 150)]);
    //const xExtents = [start, end];

    const xScaleProvider = discontinuousTimeScaleProvider
      .inputDateAccessor(d => new Date(d.timestamp));
    const {
      data,
      xScale,
      xAccessor,
      displayXAccessor,
    } = xScaleProvider(initialData);

    /*let len = data.length;
    const xExtents = [
      xAccessor(last(data)),
      xAccessor(data[len - (len > 20 ? 20 : 1)])
    ];*/

    const xExtents = [startTimestamp, endTimestamp];

    //console.log('xExtents', xExtents)

    //console.log('PriceChart data2', JSON.stringify(data))
    return React.createElement(ChartCanvas, {
        ratio, 
        width,
        height: 400,
        margin: { left: 70, right: 100, top: 20, bottom: 30 },
        type,
        pointsPerPxThreshold: 1,
        seriesName: 'MSFT',
        data,
        //xAccessor: d => new Date(d.timestamp),
        //xScaleProvider: discontinuousTimeScaleProvider,
        //xScale: d3.scaleTime(),
        //xExtents: [startTimestamp, endTimestamp],
        //xExtents: [0, last.supply + 100]

        //xScale: scaleTime(),

        xAccessor,
        //xExtents,
        displayXAccessor,
        xScale
      },
      React.createElement(Chart, {
          id: 1,
          yExtents: d => [d.auctionPrice, d.mintSale, d.mintPurchase]
          //yExtents: d => [d.price]
        },
        React.createElement(XAxis, {
          axisAt: 'bottom',
          orient: 'bottom',
        }),
        React.createElement(YAxis, {
          axisAt: 'right',
          orient: 'right',
          // tickInterval: {5}
          // tickValues: {[40, 60]}
          ticks: 5
        }),

        // Auction price
        //React.createElement(CrossHairCursor),
        React.createElement(MouseCoordinateX, {
            at: "bottom",
            orient: "bottom",
            displayFormat: d3.timeFormat("%Y-%m-%d")
          }
        ),
        React.createElement(MouseCoordinateY, {
            at: "right",
            orient: "right",
            displayFormat: d3.format(".2f")
          }
        ),
        /*React.createElement(HoverTooltip, {
            chartId: 1,
            yAccessor: d => d.auctionPrice,
            tooltipContent: tooltipContent(),
            fontSize: 15
            //bgwidth: 50,
            //bgheight: 50
          }
        ),*/

        React.createElement(LineSeries, {
          yAccessor: d => d.auctionPrice,
          //strokeDasharray: 'LongDash' 
        }),
        React.createElement(ScatterSeries, {
          yAccessor: d => d.auctionPrice,
          marker: CircleMarker,
          markerProps: { r: 3 }
        }),

        // Mint sale price
        React.createElement(LineSeries, {
          yAccessor: d => d.mintSale,
          //strokeDasharray: 'LongDash',
          stroke: "#ff7f0e"
        }),
        React.createElement(ScatterSeries, {
          yAccessor: d => d.mintSale,
          marker: CircleMarker,
          markerProps: { r: 3 }
        }),

        // Mint purchase price
        React.createElement(LineSeries, {
          yAccessor: d => d.mintPurchase,
          //strokeDasharray: 'LongDash',
          stroke: "#2ca02c"
        }),
        React.createElement(ScatterSeries, {
          yAccessor: d => d.mintPurchase,
          marker: CircleMarker,
          markerProps: { r: 3 }
        })
      )
    )
  }
}


var dateFormat = d3.timeFormat("%Y-%m-%d");
var numberFormat = d3.format(".2f");
const keyValues = ["auctionPrice", "mintSale", "mintPurchase"];

function tooltipContent(calculators) {
  return ({ currentItem, xAccessor }) => {
    return {
      x: dateFormat(xAccessor(currentItem)),
      y: [
        { label: "Auction Price", value: currentItem.auctionPrice && numberFormat(currentItem.auctionPrice) },
        { label: "Sale Price", value: currentItem.mintSale && numberFormat(currentItem.mintSale) },
        { label: "Purchase Price", value: currentItem.mintPurchase && numberFormat(currentItem.mintPurchase) }
      ]
      .filter(line => line.value)
    };
  };
}


class PriceSupplyChart extends Component {
  constructor(props) {
    super(props);
    this.state = {};
  }

  render() {
    let { data, width, ratio, type, startTimestamp, endTimestamp } = this.props;
    console.log('PriceChart data', JSON.stringify(data))
    //data = mockData;

    if(!data || !data[0]) {
      return null;
    }
    
    let last = data[data.length - 1];

    return React.createElement(ChartCanvas, {
        ratio, 
        width,
        height: 400,
        margin: { left: 70, right: 70, top: 20, bottom: 30 },
        type,
        pointsPerPxThreshold: 1,
        seriesName: 'MSFT',
        data,
        xAccessor: d => new Date(d.timestamp),
        //xScaleProvider: discontinuousTimeScaleProvider,
        xScale: d3.scaleTime(),
        xExtents: [startTimestamp, endTimestamp],
        //xExtents: [0, last.supply + 100]
      },
      React.createElement(Chart, {
          id: 1,
          //yExtents: d => [d.high, d.low, d.AAPLClose, d.GEClose]
          //yExtents: d => [d.auctionPrice, d.mintSale, d.mintPurchase]
          yExtents: d => [d.price]
        },
        React.createElement(XAxis, {
          axisAt: 'bottom',
          orient: 'bottom',
        }),
        React.createElement(YAxis, {
          axisAt: 'right',
          orient: 'right',
          // tickInterval: {5}
          // tickValues: {[40, 60]}
          ticks: 5
        }),
        React.createElement(CrossHairCursor),
        React.createElement(LineSeries, {
          yAccessor: d => d.mintSale,
          strokeDasharray: 'LongDash' 
        }),
        React.createElement(ScatterSeries, {
          yAccessor: d => d.mintSale,
          marker: CircleMarker,
          markerProps: { r: 3 }
        })
      )
    )
  }
}

export { PriceChart, PriceSupplyChart };
                    