// server/public/js/histogram.js

function getExecutionTimes(tree) {
  // This helper function is unchanged and correct.
  const times = [];
  function traverse(node) {
    if (!node) return;
    const execTime = (node.exit_time - node.creation_time) / 1e9;
    if (execTime >= 0) {
      times.push(execTime);
    }
    if (node.children) {
      node.children.forEach(traverse);
    }
  }
  traverse(tree);
  return times;
}

/**
 * Renders a responsive, correctly styled histogram of execution times.
 * @param {object} data - The raw process tree data.
 * @param {string} svgSelector - The CSS selector for the SVG element.
 */
function createHistogram(data, svgSelector) {
  const executionTimes = getExecutionTimes(data);
  if (executionTimes.length === 0) {
    return;
  }

  const chartContainer = d3.select(svgSelector);
  const tooltip = d3.select("#gantt-tooltip");

  chartContainer.selectAll("*").remove();
  if (executionTimes.length === 0) return;

  const containerNode = chartContainer.node();
  const containerWidth = containerNode.getBoundingClientRect().width;

  const margin = { top: 20, right: 30, bottom: 50, left: 60 }; // Increased bottom/left margin for labels
  const width = containerWidth - margin.left - margin.right;
  const height = 300 - margin.top - margin.bottom;

  const svg = chartContainer
    .attr("width", containerWidth)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left}, ${margin.top})`)
    .attr("class", "histogram-chart");

  // --- X Scale and Axis ---
  const xMax = d3.max(executionTimes);
  const xScale = d3
    .scaleLinear()
    .domain([0, xMax > 0 ? xMax : 1]) // Handle case where max is 0
    .range([0, width]);

  svg
    .append("g")
    .attr("transform", `translate(0, ${height})`)
    .attr("class", "axis")
    .call(d3.axisBottom(xScale).tickFormat((d) => `${d.toFixed(2)}s`))
    .selectAll("text")
    .style("fill", "#9ca3af"); // Set tick label color

  svg
    .append("text")
    .attr("text-anchor", "middle")
    .attr("x", width / 2)
    .attr("y", height + margin.bottom - 5)
    .style("fill", "#cbd5e1") // Set axis title color
    .text("Execution Time (s)");

  // --- Binning Data ---
  const histogram = d3
    .bin()
    .value((d) => d)
    .domain(xScale.domain())
    .thresholds(xScale.ticks(40)); // Increased ticks for better granularity

  const bins = histogram(executionTimes);

  // --- Y Scale and Axis ---
  const yMax = d3.max(bins, (d) => d.length);
  const yScale = d3
    .scaleLinear()
    .domain([0, yMax > 0 ? yMax : 1]) // Handle case where max is 0
    .range([height, 0]);

  svg
    .append("g")
    .attr("class", "axis")
    .call(d3.axisLeft(yScale))
    .selectAll("text")
    .style("fill", "#9ca3af"); // Set tick label color

  svg
    .append("text")
    .attr("text-anchor", "middle")
    .attr("transform", "rotate(-90)")
    .attr("y", -margin.left + 20)
    .attr("x", -height / 2)
    .style("fill", "#cbd5e1") // Set axis title color
    .text("Frequency (count)");

  // --- Tooltip and Rendering ---
  svg
    .selectAll("rect")
    .data(bins)
    .enter()
    .append("rect")
    .attr("class", "bar")
    .attr("x", (d) => xScale(d.x0) + 1)
    .attr("transform", (d) => `translate(0, ${yScale(d.length)})`)
    .attr("width", (d) => Math.max(0, xScale(d.x1) - xScale(d.x0) - 1))
    .attr("height", (d) => height - yScale(d.length))
    .on("mouseover", function (event, d) {
      tooltip.transition().duration(200).style("opacity", 0.9);
      tooltip
        .html(
          `<strong>Time Range:</strong> ${d.x0.toFixed(3)}s - ${d.x1.toFixed(
            3
          )}s<br/>` + `<strong>Count:</strong> ${d.length}`
        )
        .style("left", event.pageX + 15 + "px")
        .style("top", event.pageY - 28 + "px");
    })
    .on("mouseout", function (d) {
      tooltip.transition().duration(500).style("opacity", 0);
    });
}
