/**
 * Simple line chart component for macro data visualization using canvas
 * Provides fallback visualization when charting libraries aren't available
 */

import React, { useEffect, useRef } from 'react'

type MiniLineChartDataPoint = {
  date: string
  value: number
}

type MiniLineChartProps = {
  data: MiniLineChartDataPoint[]
  title?: string
  width?: number
  height?: number
  color?: string
  showTooltip?: boolean
}

const MiniLineChart: React.FC<MiniLineChartProps> = ({
  data,
  title,
  width = 400,
  height = 200,
  color = '#4a9eff',
  showTooltip = true
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)

  const horizontalLines = 5  // Define this constant

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !data || data.length === 0) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Clear canvas
    ctx.clearRect(0, 0, width, height)

    // Set dimensions
    canvas.width = width
    canvas.height = height

    // Parse dates and find min/max for scaling
    const parsedData = data.map(d => ({
      date: new Date(d.date),
      value: parseFloat(String(d.value))
    })).filter(d => !isNaN(d.date.getTime()) && !isNaN(d.value))

    if (parsedData.length === 0) return

    const minDate = Math.min(...parsedData.map(d => d.date.getTime()))
    const maxDate = Math.max(...parsedData.map(d => d.date.getTime()))
    const minValue = Math.min(...parsedData.map(d => d.value))
    const maxValue = Math.max(...parsedData.map(d => d.value))

    // Add some padding to the scale
    const valueRange = maxValue - minValue
    const padding = valueRange > 0 ? valueRange * 0.05 : 0.1
    const paddedMinValue = minValue - padding
    const paddedMaxValue = maxValue + padding

    // Draw grid lines (horizontal)
    ctx.strokeStyle = '#eee'
    ctx.lineWidth = 0.5
    const horizontalLines = 5
    for (let i = 0; i <= horizontalLines; i++) {
      const y = height - (i / horizontalLines) * (height - 30) - 15  // Leave some bottom margin
      ctx.beginPath()
      ctx.moveTo(30, y)  // Leave some left margin for labels
      ctx.lineTo(width - 15, y)
      ctx.stroke()
    }

    // Draw the line chart
    ctx.strokeStyle = color
    ctx.lineWidth = 2
    ctx.beginPath()

    parsedData.forEach((point, index) => {
      // Scale date to x position (with left margin)
      const x = 30 + ((point.date.getTime() - minDate) / (maxDate - minDate)) * (width - 45)
      // Scale value to y position (inverted, with top/bottom margins)
      const y = height - 15 - ((point.value - paddedMinValue) / (paddedMaxValue - paddedMinValue)) * (height - 30)

      if (index === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    })

    ctx.stroke()

    // Draw points
    ctx.fillStyle = color
    parsedData.forEach((point, index) => {
      if (index % Math.ceil(parsedData.length / 8) === 0 || index === 0 || index === parsedData.length - 1) { // Show ~8 points max
        const x = 30 + ((point.date.getTime() - minDate) / (maxDate - minDate)) * (width - 45)
        const y = height - 15 - ((point.value - paddedMinValue) / (paddedMaxValue - paddedMinValue)) * (height - 30)
        
        ctx.beginPath()
        ctx.arc(x, y, 3, 0, 2 * Math.PI)
        ctx.fill()
      }
    })

    // Draw axis labels
    ctx.fillStyle = '#666'
    ctx.font = '10px Arial'
    ctx.textAlign = 'center'

    // X-axis labels (dates)
    const labelIndices = [0, Math.floor(parsedData.length / 4), Math.floor(parsedData.length / 2), Math.floor(3 * parsedData.length / 4), parsedData.length - 1]
    labelIndices.forEach(index => {
      if (index >= 0 && index < parsedData.length) {
        const x = 30 + ((parsedData[index].date.getTime() - minDate) / (maxDate - minDate)) * (width - 45)
        const dateStr = parsedData[index].date.toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' })
        ctx.fillText(dateStr, x, height - 5)
      }
    })

    // Y-axis labels (values)
    ctx.textAlign = 'right'
    for (let i = 0; i <= horizontalLines; i++) {
      const value = paddedMinValue + (i / horizontalLines) * (paddedMaxValue - paddedMinValue)
      const y = height - 15 - (i / horizontalLines) * (height - 30)
      ctx.fillText(value.toFixed(2), 25, y + 4)
    }
  }, [data, width, height, color])

  // Handle mouse movement for tooltip
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!showTooltip || !tooltipRef.current || !canvasRef.current) return

    const canvas = canvasRef.current
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    const container = containerRef.current
    if (!container) return

    // Show tooltip near mouse with value and date info
    const tooltip = tooltipRef.current
    tooltip.style.display = 'block'
    tooltip.style.left = `${e.clientX}px`
    tooltip.style.top = `${e.clientY - 30}px`

    // Find nearest data point to mouse position
    if (data && data.length > 0) {
      // Normalize times and compute X positions in a clearer multi-step way to avoid parsing issues
      const times = data.map(d => new Date(d.date).getTime()).filter(t => !isNaN(t));
      const minTime = times.length ? Math.min(...times) : 0;
      const maxTime = times.length ? Math.max(...times) : 0;

      const parsedData = data
        .map(d => {
          const date = new Date(d.date);
          const value = parseFloat(String(d.value));
          const x = (minTime !== maxTime)
            ? 30 + ((date.getTime() - minTime) / (maxTime - minTime)) * (width! - 45)
            : 30;
          return { date, value, x };
        })
        .filter(d => !isNaN(d.date.getTime()) && !isNaN(d.value));

      let nearest = parsedData[0]
      let minDist = Math.abs(x - nearest.x)

      for (let i = 1; i < parsedData.length; i++) {
        const dist = Math.abs(x - parsedData[i].x)
        if (dist < minDist) {
          minDist = dist
          nearest = parsedData[i]
        }
      }

      if (nearest) {
        tooltip.innerHTML = `
          <div style="padding: 8px; background: rgba(0,0,0,0.8); color: white; border-radius: 4px; font-size: 12px; pointer-events: none;">
            <div>Date: ${nearest.date.toLocaleDateString('fr-FR')}</div>
            <div>Valeur: ${nearest.value.toFixed(2)}</div>
          </div>
        `
      } else {
        tooltip.style.display = 'none'
      }
    } else {
      tooltip.style.display = 'none'
    }
  }

  const handleMouseLeave = () => {
    if (tooltipRef.current) {
      tooltipRef.current.style.display = 'none'
    }
  }

  return (
    <div ref={containerRef} style={{ position: 'relative', display: 'inline-block' }}>
      {title && <h3 style={{ marginBottom: 8, fontSize: 16, fontWeight: 600 }}>{title}</h3>}
      <canvas
        ref={canvasRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{ 
          border: '1px solid #ddd', 
          borderRadius: '4px',
          width: width,
          height: height
        }}
      />
      {showTooltip && (
        <div
          ref={tooltipRef}
          style={{
            position: 'fixed',
            display: 'none',
            zIndex: 1000,
            pointerEvents: 'none',
            transform: 'translate(-50%, -100%)',
          }}
        />
      )}
    </div>
  )
}

export default MiniLineChart