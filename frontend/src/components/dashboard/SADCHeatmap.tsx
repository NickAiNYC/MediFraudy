import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { Card, CardContent, Typography, Box } from '@mui/material';

interface SADCHeatmapProps {
  data: Array<{
    claim_date: string;
    provider_id: number;
    value: number;
  }>;
}

export const SADCHeatmap: React.FC<SADCHeatmapProps> = ({ data }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!data || !Array.isArray(data) || data.length === 0 || !svgRef.current) return;

    // Clear previous
    d3.select(svgRef.current).selectAll("*").remove();

    const margin = { top: 30, right: 30, bottom: 30, left: 30 };
    const width = 800 - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current)
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Parse dates
    const parseDate = d3.timeParse("%Y-%m-%d");
    const formattedData = data.map(d => ({
      ...d,
      date: parseDate(d.claim_date) as Date
    })).filter(d => d.date);

    // Group by date
    const dailyCounts = d3.rollups(formattedData, v => d3.sum(v, d => d.value), d => d.date);
    
    // Create scales
    const x = d3.scaleTime()
      .domain(d3.extent(formattedData, d => d.date) as [Date, Date])
      .range([0, width]);

    const y = d3.scaleLinear()
      .domain([0, d3.max(dailyCounts, d => d[1]) as number])
      .range([height, 0]);

    // Draw axes
    svg.append("g")
      .attr("transform", `translate(0,${height})`)
      .call(d3.axisBottom(x));

    svg.append("g")
      .call(d3.axisLeft(y));

    // Draw line
    const line = d3.line<[Date, number]>()
      .x(d => x(d[0]))
      .y(d => y(d[1]));

    svg.append("path")
      .datum(dailyCounts)
      .attr("fill", "none")
      .attr("stroke", "#ff5722")
      .attr("stroke-width", 2)
      .attr("d", line);

    // Highlight spikes
    const threshold = d3.mean(dailyCounts, d => d[1])! + (2 * d3.deviation(dailyCounts, d => d[1])!);
    
    svg.selectAll("circle")
      .data(dailyCounts.filter(d => d[1] > threshold))
      .enter()
      .append("circle")
      .attr("cx", d => x(d[0]))
      .attr("cy", d => y(d[1]))
      .attr("r", 5)
      .attr("fill", "red")
      .append("title")
      .text(d => `Spike: ${d[1]} attendees on ${d3.timeFormat("%Y-%m-%d")(d[0])}`);

  }, [data]);

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          SADC "Payday" Patterns
        </Typography>
        <Typography variant="body2" color="textSecondary" gutterBottom>
          Total daily attendance across all flagged SADC centers.
        </Typography>
        <Box sx={{ overflowX: 'auto' }}>
            <svg ref={svgRef}></svg>
        </Box>
      </CardContent>
    </Card>
  );
};
