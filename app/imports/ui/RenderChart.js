import React, { Component } from 'react';
import d3 from 'd3';
import LineAndScatterChart from '/imports/ui/Graph';

export default class RenderChart extends Component {
    constructor(props) {
        super(props);
        this.state = {};
    }

    componentWillMount() {
        let self = this;
        d3["tsv"]("http://rrag.github.io/react-stockcharts/data/MSFT.tsv", (err, data) => {
        	data.forEach((d, i) => {
        		d.date = new Date(d3.timeParse("%Y-%m-%d")(d.date).getTime());
        		d.open = +d.open;
        		d.high = +d.high;
        		d.low = +d.low;
        		d.close = +d.close;
        		d.volume = +d.volume;
        	});
            //console.log('data', data)
            self.data = data;
            self.dataInd = 600
            let newdata = data.slice(0, self.dataInd);
            console.log('newdata', newdata)
            self.setState({ data: newdata });
        });
    }

    componentDidMount() {
        let self = this;
        self.intervalID = window.setInterval(updateData, 2000);
        if(!data) return;
        let len = data.length;

        function updateData() {
            //console.log('--updateData--')
            let data = self.state.data;
            self.dataInd += 3

            data = self.data.slice(0, self.dataInd)
            self.setState({ data })
        }
    }

    componentWillUnmount() {
        if(this.intervalID)
            clearInterval(this.intervalID)
    }

    render() {
        //console.log('render RenderChart')
        data = this.state.data;
        return (
            React.createElement('div', {},
                data ? React.createElement(LineAndScatterChart, {type: 'hybrid', data: data, width: 600, ratio: 1}) : null
            )
        )
    }
}
