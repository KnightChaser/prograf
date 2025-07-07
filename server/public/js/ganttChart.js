// server/public/js/ganttChart.js

const MAX_INITIAL_NODES = 20; // Max nodes to show before needing to expand

/**
 * Flattens the hierarchical tree data and calculates time bounds.
 * @param {object} tree - The root node of the process tree.
 * @returns {object} An object containing the flattened list and time info.
 */
function flattenTree(tree) {
  const flatList = [];
  let minTimestamp = Infinity;
  let maxTimestamp = 0;

  // traverse the tree recursively, collecting nodes and their depth
  function traverse(node, depth) {
    if (node.creation_time < minTimestamp) minTimestamp = node.creation_time;
    if (node.exit_time > maxTimestamp) maxTimestamp = node.exit_time;

    flatList.push({ ...node, depth });
    node.children.forEach((child) => traverse(child, depth + 1));
  }
  traverse(tree, 0);

  return { flatList, minTimestamp, maxTimestamp };
}

/**
 * Renders the Gantt chart inside a given SVG element using D3.
 * @param {object} data - The raw process tree data.
 * @param {string} svgSelector - The CSS selector for the SVG element (e.g., "#gantt-chart").
 */
function createGanttChart(data, svgSelector, forceFull = false) {
  const { flatList, minTimestamp, maxTimestamp } = flattenTree(data);
  const chartContainer = d3.select(svgSelector);
  const tooltip = d3.select("#gantt-tooltip");
  const expandBtn = d3.select("#expand-chart-btn");

  chartContainer.selectAll("*").remove();

  if (flatList.length === 0) {
    expandBtn.classed("hidden", true);
    return;
  }

  // *** FIX: Use a mutable variable for the list to be rendered ***
  let renderList = flatList;

  // Expand/collapse logic
  if (flatList.length > MAX_INITIAL_NODES && !forceFull) {
    renderList = flatList.slice(0, MAX_INITIAL_NODES);
    expandBtn
      .classed("hidden", false)
      .text(`Show Full Chart (${flatList.length} nodes)`)
      .on("click", () => {
        // On click, re-render with the full data by setting forceFull to true
        createGanttChart(data, svgSelector, true);
      });
  } else {
    expandBtn.classed("hidden", true);
  }

  const nodeMap = new Map(flatList.map((node) => [node.pid, node]));
  const margin = { top: 20, right: 30, bottom: 40, left: 150 };
  const width = 960 - margin.left - margin.right;
  const barHeight = 20;
  const barPadding = 5;
  const height = renderList.length * (barHeight + barPadding); // Use renderList's length

  const svg = chartContainer
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left}, ${margin.top})`)
    .attr("class", "gantt-chart");

  // Scales
  const xScale = d3
    .scaleLinear()
    .domain([0, (maxTimestamp - minTimestamp) / 1e6])
    .range([0, width]);

  const yScale = d3
    .scaleBand()
    .domain(renderList.map((d) => d.pid)) // Use renderList for the y-domain
    .range([0, height])
    .padding(0.1);

  // Axes
  const xAxis = d3
    .axisBottom(xScale)
    .ticks(10, ".2s")
    .tickFormat((d) => (d / 1000).toFixed(2) + "s");
  svg
    .append("g")
    .attr("transform", `translate(0, ${height})`)
    .attr("class", "axis")
    .call(xAxis);

  // Data Binding
  const groups = svg
    .selectAll("g.bar-group")
    .data(renderList) // Use renderList for data binding
    .enter()
    .append("g")
    .attr("class", "bar-group")
    .attr("transform", (d) => `translate(0, ${yScale(d.pid)})`)
    .on("mouseover", function (event, d) {
      tooltip.transition().duration(200).style("opacity", 0.9);
      const parentNode = nodeMap.get(d.ppid);
      const parentInfo = parentNode
        ? `${parentNode.comm} (${parentNode.pid})`
        : "N/A";
      const startTimeS = ((d.creation_time - minTimestamp) / 1e9).toFixed(6);
      const endTimeS = ((d.exit_time - minTimestamp) / 1e9).toFixed(6);
      const execTimeS = ((d.exit_time - d.creation_time) / 1e9).toFixed(6);
      tooltip
        .html(
          `<strong>Name:</strong> ${d.comm}<br/>` +
            `<strong>PID:</strong> ${d.pid}<br/>` +
            `<strong>PPID:</strong> ${parentInfo}<br/>` +
            `<strong>Start Time:</strong> ${startTimeS}s (relative)<br/>` +
            `<strong>End Time:</strong> ${endTimeS}s (relative)<br/>` +
            `<strong>Execution Time:</strong> ${execTimeS}s`
        )
        .style("left", event.pageX + 15 + "px")
        .style("top", event.pageY - 28 + "px");
    })
    .on("mouseout", function (d) {
      tooltip.transition().duration(500).style("opacity", 0);
    });

  groups
    .append("rect")
    .attr("class", "bar")
    .attr("x", (d) => xScale((d.creation_time - minTimestamp) / 1e6))
    .attr("width", (d) => xScale((d.exit_time - d.creation_time) / 1e6))
    .attr("height", yScale.bandwidth());
  groups
    .append("text")
    .attr("class", "bar-label")
    .attr("x", (d) => d.depth * 20 + 5)
    .attr("y", yScale.bandwidth() / 2)
    .attr("dy", "0.35em")
    .text((d) => `${d.comm} (${d.pid})`);
}
