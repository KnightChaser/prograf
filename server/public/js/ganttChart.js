// server/public/js/ganttChart.js

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
function createGanttChart(data, svgSelector) {
  const { flatList, minTimestamp, maxTimestamp } = flattenTree(data);
  const chartContainer = d3.select(svgSelector);

  // Clear previous chart content
  chartContainer.selectAll("*").remove();

  if (flatList.length === 0) return;

  const margin = { top: 20, right: 30, bottom: 40, left: 150 };
  const width = 960 - margin.left - margin.right;
  const barHeight = 20;
  const barPadding = 5;
  const height = flatList.length * (barHeight + barPadding);

  const svg = chartContainer
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left}, ${margin.top})`)
    .attr("class", "gantt-chart");

  // Scales
  const xScale = d3
    .scaleLinear()
    .domain([0, (maxTimestamp - minTimestamp) / 1e6]) // Relative milliseconds
    .range([0, width]);

  const yScale = d3
    .scaleBand()
    .domain(flatList.map((d) => d.pid))
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

  // Data Binding and Rendering
  const groups = svg
    .selectAll("g.bar-group")
    .data(flatList)
    .enter()
    .append("g")
    .attr("class", "bar-group")
    .attr("transform", (d) => `translate(0, ${yScale(d.pid)})`);

  groups
    .append("rect")
    .attr("class", "bar")
    .attr("x", (d) => xScale((d.creation_time - minTimestamp) / 1e6))
    .attr("width", (d) => xScale((d.exit_time - d.creation_time) / 1e6))
    .attr("height", yScale.bandwidth());

  groups
    .append("text")
    .attr("class", "bar-label")
    .attr("x", (d) => d.depth * 20 + 5) // Indentation
    .attr("y", yScale.bandwidth() / 2)
    .attr("dy", "0.35em")
    .text((d) => `${d.comm} (${d.pid})`);
}
