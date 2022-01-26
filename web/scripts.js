const colorScaleCreator = () => {
    const colors = [];
    const random = d3.randomInt(256);

    return (count) => {
        if (colors.length < count) {
            colors.push(...d3.range(count - colors.length).map(() => d3.color(`rgb(${random()}, ${random()}, ${random()})`)));
        }
        return d3.scaleOrdinal(d3.range(count), colors.slice(0, count));
    };
};

const createColorScale = colorScaleCreator();

const createLinearScale = (data, getValue, rangeMin, rangeMax) => {
    const valueMin = d3.min(data, getValue);
    const valueMax = d3.max(data, getValue);
    return d3.scaleLinear()
        .domain([valueMin, valueMax])
        .range([rangeMin, rangeMax]);
};

export const draw = (dataSets, options = {}) => {
    const defaults = { stackCharts: false, showLabels: true, normalize: true };
    const { stackCharts, showLabels, normalize } = { ...defaults, ...options };
    const WIDTH = d3.select('svg').node().width.baseVal.value;
    const HEIGHT = d3.select('svg').node().height.baseVal.value;
    const height = HEIGHT / dataSets.length

    const colorScale = createColorScale(dataSets.length);

    const allData = d3.merge(dataSets.map((dataSet, dataSetIndex) => dataSet.data.map(datum => ({...datum, dataSetIndex }))));

    const xScale = createLinearScale(allData, d => d.x, 0, WIDTH);
    const yScales = stackCharts ?
        dataSets.map((dataSet) => createLinearScale(normalize ? dataSet.data : allData, d => d.y, HEIGHT, 0)) :
        dataSets.map((dataSet, index) => createLinearScale(normalize ? dataSet.data : allData, d => d.y, height * (index + 1), height * index));

    const line = (dataSet, index) => {
        return d3.line()
            .x(d => xScale(d.x))
            .y(d => yScales[index](d.y))(dataSet.data);
    };

    const gChartUpdate = d3.select('svg').selectAll('.set').data(dataSets);
    const gChartEnter = gChartUpdate.enter().append('g').attr('class', 'set').style('opacity', 0);
    gChartEnter.transition().style('opacity', 1);
    gChartUpdate.exit().transition().style('opacity', 0).remove();

    gChartEnter.append('text').attr('class', 'label');
    gChartUpdate.merge(gChartEnter).select('.label')
        .text(d => d.label)
        .style('visibility', showLabels ? 'visible' : 'hidden')
        .style('font-weight', 'bold')
        .style('alignment-baseline', 'text-after-edge')
        .style('stroke', (d, i) => colorScale(i).copy({ opacity: 0.8 }))
        .style('fill', (d, i) => colorScale(i).copy({ opacity: 0.2 }));
    gChartEnter.select('.label')
        .attr('font-size', stackCharts ? 32 : d3.min([height * 0.8, 128]))
        .attr('x', 10)
        .attr('y', stackCharts ? (d, i) => yScales[i](d.data[0].y) : (d, i) => (i + 1) * height);
    gChartUpdate.select('.label')
        .transition()
        .attr('font-size', stackCharts ? 32 : d3.min([height * 0.8, 128]))
        .attr('x', 10)
        .attr('y', stackCharts ? (d, i) => yScales[i](d.data[0].y) : (d, i) => (i + 1) * height);

    gChartEnter.append('path').attr('class', 'line');
    gChartUpdate.merge(gChartEnter).select('.line')
        .style('stroke', (d, i) => colorScale(i));
    gChartEnter.select('.line')
        .attr('d', line);
    gChartUpdate.select('.line')
        .transition()
        .attr('d', line);

    const allDataScaled = d3.merge(dataSets.map((dataSet, dataSetIndex) => {
        return dataSet.data.map(({ x, y }) => {
            return [xScale(x), yScales[dataSetIndex](y)];
        })
    }));
    const delaunay = d3.Delaunay.from(allDataScaled);
    const voronoi = delaunay.voronoi([0, 0, WIDTH, HEIGHT]);
    const cellPolygons = [...voronoi.cellPolygons()];

    const gHoverAreaUpdate = d3.select('svg').selectAll('.group').data(cellPolygons);
    const gHoverAreaEnter = gHoverAreaUpdate.enter().append('g').attr('class', 'group');
    gHoverAreaUpdate.exit().remove();

    gHoverAreaEnter.append('circle')
        .attr('class', 'point')
        .attr('r', 4);

    gHoverAreaEnter.append('path')
        .attr('class', 'area');

    gHoverAreaUpdate.merge(gHoverAreaEnter).select('.point')
        .style('stroke', d => colorScale(allData[d.index].dataSetIndex))
        .style('fill', d => colorScale(allData[d.index].dataSetIndex).copy({ opacity: 0.4 }))
        .attr('cx', (d) => xScale(allData[d.index].x))
        .attr('cy', (d) => {
            return yScales[allData[d.index].dataSetIndex](allData[d.index].y);
        });

    gHoverAreaUpdate.merge(gHoverAreaEnter).select('.area')
        .attr('d', (d) => {
            const path = d3.path();
            path.moveTo(...d[0]);
            d.forEach(point => path.lineTo(...point));
            path.closePath();
            return path.toString();
        })
        .on('mouseover', (e, d, i) => {
            d3.select('.tooltip').style('display', 'block');
            d3.select('.tooltip-label').text(dataSets[allData[d.index].dataSetIndex].label);
            d3.select('.tooltip-x').text(d3.timeFormat('%m-%d-%Y')(new Date(allData[d.index].x * 1000)));
            d3.select('.tooltip-y').text(d3.format(',.2f')(allData[d.index].y));
        })
        .on('mouseout', () => {
            d3.select('.tooltip').style('display', 'none');
        })
        .on('mousemove', (e) => {
            d3.select('.tooltip')
                .style('left', `${e.clientX}px`)
                .style('top', `${e.clientY}px`);
            d3.select('.tooltip > div')
                .style('left', e.clientX < window.innerWidth / 2 ? '15px' : 'unset')
                .style('right', e.clientX < window.innerWidth / 2 ? 'unset' : '10px')
                .style('top', e.clientY < window.innerHeight / 2 ? '15px' : 'unset')
                .style('bottom', e.clientY < window.innerHeight / 2 ? 'unset' : '10px');
        })
};
