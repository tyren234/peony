/** Minimalist accessible SVG chart component distinguishing series by color and shape (Requirements F2, WCAG 2.2 AA). */

import React from "react";
import type { MeasurementItem, SeriesItem } from "../types";

interface TelemetryChartProperties {
  seriesList: SeriesItem[];
  measurementsList: MeasurementItem[];
  selectedMeasurementIdentifier: number | null;
  onSelectMeasurement: (measurementIdentifier: number) => void;
}

const SERIES_POINT_SHAPES = ["circle", "square", "triangle", "diamond", "cross", "star"] as const;

export const TelemetryChart: React.FC<TelemetryChartProperties> = ({
  seriesList,
  measurementsList,
  selectedMeasurementIdentifier,
  onSelectMeasurement,
}) => {
  if (measurementsList.length === 0) {
    return (
      <section className="chart-container empty-state" aria-label="Wykres pomiarów telemetrycznych">
        <p>Brak pomiarów dla wybranych kryteriów filtrowania.</p>
      </section>
    );
  }

  const svgChartWidth = 800;
  const svgChartHeight = 360;
  const marginPadding = { top: 20, right: 30, bottom: 40, left: 60 };

  const usableChartWidth = svgChartWidth - marginPadding.left - marginPadding.right;
  const usableChartHeight = svgChartHeight - marginPadding.top - marginPadding.bottom;

  // Obliczenie granic czasowych i wartości
  const measurementTimestamps = measurementsList.map((measurementEntry) =>
    new Date(measurementEntry.timestamp).getTime()
  );
  const minimumTimestamp = Math.min(...measurementTimestamps);
  const maximumTimestamp = Math.max(...measurementTimestamps);
  const timestampSpan = Math.max(1, maximumTimestamp - minimumTimestamp);

  const measurementValues = measurementsList.map((measurementEntry) => measurementEntry.value);
  const rawMinimumValue = Math.min(...measurementValues);
  const rawMaximumValue = Math.max(...measurementValues);
  const valuePadding = Math.max(1, (rawMaximumValue - rawMinimumValue) * 0.1);
  const chartMinimumValue = rawMinimumValue - valuePadding;
  const chartMaximumValue = rawMaximumValue + valuePadding;
  const chartValueSpan = Math.max(1, chartMaximumValue - chartMinimumValue);

  // Funkcje mapujące na współrzędne SVG
  const calculateCoordinateX = (timestampIsoString: string): number => {
    const timestampMilliseconds = new Date(timestampIsoString).getTime();
    const progressRatio = (timestampMilliseconds - minimumTimestamp) / timestampSpan;
    return marginPadding.left + progressRatio * usableChartWidth;
  };

  const calculateCoordinateY = (numericValue: number): number => {
    const progressRatio = (numericValue - chartMinimumValue) / chartValueSpan;
    return marginPadding.top + (1 - progressRatio) * usableChartHeight;
  };

  // Grupowanie pomiarów według serii
  const measurementsGroupedBySeries: { [seriesId: number]: MeasurementItem[] } = {};
  for (const singleMeasurement of measurementsList) {
    if (!measurementsGroupedBySeries[singleMeasurement.seriesId]) {
      measurementsGroupedBySeries[singleMeasurement.seriesId] = [];
    }
    measurementsGroupedBySeries[singleMeasurement.seriesId].push(singleMeasurement);
  }

  // Rysowanie symbolu kształtu dla serii
  const renderPointShape = (
    shapeType: string,
    centerCoordinateX: number,
    centerCoordinateY: number,
    pointColor: string,
    isPointSelected: boolean,
    pointMeasurementIdentifier: number,
    accessibleDescription: string
  ) => {
    const pointRadius = isPointSelected ? 7 : 4.5;
    const commonProperties = {
      fill: isPointSelected ? "#ffffff" : pointColor,
      stroke: pointColor,
      strokeWidth: isPointSelected ? 3 : 1.5,
      className: `chart-point ${isPointSelected ? "selected-point" : ""}`,
      tabIndex: 0,
      role: "button" as const,
      "aria-label": accessibleDescription,
      onClick: () => onSelectMeasurement(pointMeasurementIdentifier),
      onKeyDown: (keyboardEvent: React.KeyboardEvent) => {
        if (keyboardEvent.key === "Enter" || keyboardEvent.key === " ") {
          keyboardEvent.preventDefault();
          onSelectMeasurement(pointMeasurementIdentifier);
        }
      },
    };

    if (shapeType === "square") {
      const squareSize = pointRadius * 2;
      return (
        <rect
          key={pointMeasurementIdentifier}
          x={centerCoordinateX - pointRadius}
          y={centerCoordinateY - pointRadius}
          width={squareSize}
          height={squareSize}
          {...commonProperties}
        />
      );
    }

    if (shapeType === "triangle") {
      const trianglePoints = `${centerCoordinateX},${centerCoordinateY - pointRadius * 1.3} ${
        centerCoordinateX - pointRadius
      },${centerCoordinateY + pointRadius} ${centerCoordinateX + pointRadius},${
        centerCoordinateY + pointRadius
      }`;
      return <polygon key={pointMeasurementIdentifier} points={trianglePoints} {...commonProperties} />;
    }

    if (shapeType === "diamond") {
      const diamondPoints = `${centerCoordinateX},${centerCoordinateY - pointRadius * 1.3} ${
        centerCoordinateX + pointRadius * 1.2
      },${centerCoordinateY} ${centerCoordinateX},${centerCoordinateY + pointRadius * 1.3} ${
        centerCoordinateX - pointRadius * 1.2
      },${centerCoordinateY}`;
      return <polygon key={pointMeasurementIdentifier} points={diamondPoints} {...commonProperties} />;
    }

    // Domyślnie circle
    return (
      <circle
        key={pointMeasurementIdentifier}
        cx={centerCoordinateX}
        cy={centerCoordinateY}
        r={pointRadius}
        {...commonProperties}
      />
    );
  };

  return (
    <section className="chart-container" aria-label="Wykres pomiarów telemetrycznych">
      <div className="chart-legend" role="list" aria-label="Legenda serii pomiarowych">
        {seriesList.map((seriesEntry, seriesIndex) => {
          const seriesShape = SERIES_POINT_SHAPES[seriesIndex % SERIES_POINT_SHAPES.length];
          return (
            <div key={seriesEntry.id} className="legend-item" role="listitem">
              <span
                className="legend-color-box"
                style={{ backgroundColor: seriesEntry.color }}
                aria-hidden="true"
              />
              <span className="legend-shape-label" aria-hidden="true">
                [{seriesShape}]
              </span>
              <span className="legend-name">{seriesEntry.name}</span>
            </div>
          );
        })}
      </div>

      <svg
        viewBox={`0 0 ${svgChartWidth} ${svgChartHeight}`}
        className="telemetry-svg-chart"
        role="img"
        aria-label="Interaktywny wykres liniowy pomiarów"
      >
        {/* Siatka pozioma i etykiety osi Y */}
        {[0, 0.25, 0.5, 0.75, 1.0].map((gridRatioIndex) => {
          const gridLevelValue = chartMinimumValue + gridRatioIndex * chartValueSpan;
          const gridCoordinateY = calculateCoordinateY(gridLevelValue);
          return (
            <g key={gridRatioIndex} className="grid-horizontal-line">
              <line
                x1={marginPadding.left}
                y1={gridCoordinateY}
                x2={svgChartWidth - marginPadding.right}
                y2={gridCoordinateY}
                stroke="#e2e8f0"
                strokeDasharray="4 4"
              />
              <text
                x={marginPadding.left - 8}
                y={gridCoordinateY + 4}
                textAnchor="end"
                className="axis-label"
                fill="#64748b"
                fontSize="11"
              >
                {gridLevelValue.toFixed(1)}
              </text>
            </g>
          );
        })}

        {/* Osie główne */}
        <line
          x1={marginPadding.left}
          y1={marginPadding.top}
          x2={marginPadding.left}
          y2={svgChartHeight - marginPadding.bottom}
          stroke="#475569"
          strokeWidth="1.5"
        />
        <line
          x1={marginPadding.left}
          y1={svgChartHeight - marginPadding.bottom}
          x2={svgChartWidth - marginPadding.right}
          y2={svgChartHeight - marginPadding.bottom}
          stroke="#475569"
          strokeWidth="1.5"
        />

        {/* Linie i punkty serii */}
        {seriesList.map((seriesEntry, seriesIndex) => {
          const seriesPoints = measurementsGroupedBySeries[seriesEntry.id] || [];
          if (seriesPoints.length === 0) {
            return null;
          }

          const sortedPoints = [...seriesPoints].sort(
            (firstPoint, secondPoint) =>
              new Date(firstPoint.timestamp).getTime() - new Date(secondPoint.timestamp).getTime()
          );

          const polylineCoordinates = sortedPoints
            .map((singlePoint) => {
              const coordinateX = calculateCoordinateX(singlePoint.timestamp);
              const coordinateY = calculateCoordinateY(singlePoint.value);
              return `${coordinateX.toFixed(1)},${coordinateY.toFixed(1)}`;
            })
            .join(" ");

          const seriesShape = SERIES_POINT_SHAPES[seriesIndex % SERIES_POINT_SHAPES.length];

          return (
            <g key={seriesEntry.id} className="series-chart-group">
              <polyline
                fill="none"
                stroke={seriesEntry.color}
                strokeWidth="2.5"
                points={polylineCoordinates}
              />
              {sortedPoints.map((singlePoint) => {
                const coordinateX = calculateCoordinateX(singlePoint.timestamp);
                const coordinateY = calculateCoordinateY(singlePoint.value);
                const isSelected = singlePoint.id === selectedMeasurementIdentifier;
                const formattedTime = new Date(singlePoint.timestamp).toLocaleTimeString();
                const accessibleDescription = `${seriesEntry.name}: ${singlePoint.value} (${formattedTime})`;

                return renderPointShape(
                  seriesShape,
                  coordinateX,
                  coordinateY,
                  seriesEntry.color,
                  isSelected,
                  singlePoint.id,
                  accessibleDescription
                );
              })}
            </g>
          );
        })}
      </svg>
    </section>
  );
};
