/** Synchronized data table component for telemetry measurements (Requirements F2, F6). */

import React, { useEffect, useRef } from "react";
import type { MeasurementItem, SeriesItem } from "../types";

interface TelemetryTableProperties {
  seriesList: SeriesItem[];
  measurementsList: MeasurementItem[];
  selectedMeasurementIdentifier: number | null;
  onSelectMeasurement: (measurementIdentifier: number) => void;
}

export const TelemetryTable: React.FC<TelemetryTableProperties> = ({
  seriesList,
  measurementsList,
  selectedMeasurementIdentifier,
  onSelectMeasurement,
}) => {
  const selectedRowReference = useRef<HTMLTableRowElement | null>(null);

  useEffect(() => {
    if (selectedMeasurementIdentifier !== null && selectedRowReference.current) {
      selectedRowReference.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
  }, [selectedMeasurementIdentifier]);

  const seriesLookupById: { [seriesId: number]: SeriesItem } = {};
  for (const seriesEntry of seriesList) {
    seriesLookupById[seriesEntry.id] = seriesEntry;
  }

  if (measurementsList.length === 0) {
    return (
      <section className="table-container empty-state" aria-label="Tabela wyników pomiarów">
        <p>Brak pomiarów do wyświetlenia w tabeli.</p>
      </section>
    );
  }

  return (
    <section className="table-container" aria-label="Tabela wyników pomiarów">
      <div className="table-scroll-wrapper">
        <table className="telemetry-data-table">
          <thead>
            <tr>
              <th scope="col">ID</th>
              <th scope="col">Seria</th>
              <th scope="col">Wartość</th>
              <th scope="col">Data i czas (UTC)</th>
            </tr>
          </thead>
          <tbody>
            {measurementsList.map((singleMeasurement) => {
              const matchingSeries = seriesLookupById[singleMeasurement.seriesId];
              const isRowSelected = singleMeasurement.id === selectedMeasurementIdentifier;
              const formattedDate = new Date(singleMeasurement.timestamp).toLocaleString();
              const seriesDisplayName = matchingSeries ? matchingSeries.name : `Seria #${singleMeasurement.seriesId}`;
              const measurementUnit = matchingSeries?.unit ? ` ${matchingSeries.unit}` : "";

              return (
                <tr
                  key={singleMeasurement.id}
                  ref={isRowSelected ? selectedRowReference : null}
                  className={`table-row ${isRowSelected ? "selected-row" : ""}`}
                  tabIndex={0}
                  role="button"
                  aria-pressed={isRowSelected}
                  onClick={() => onSelectMeasurement(singleMeasurement.id)}
                  onKeyDown={(keyboardEvent: React.KeyboardEvent) => {
                    if (keyboardEvent.key === "Enter" || keyboardEvent.key === " ") {
                      keyboardEvent.preventDefault();
                      onSelectMeasurement(singleMeasurement.id);
                    }
                  }}
                >
                  <td className="cell-id">{singleMeasurement.id}</td>
                  <td className="cell-series">
                    {matchingSeries && (
                      <span
                        className="series-indicator"
                        style={{ backgroundColor: matchingSeries.color }}
                        aria-hidden="true"
                      />
                    )}
                    <span>{seriesDisplayName}</span>
                  </td>
                  <td className="cell-value">
                    <strong>{singleMeasurement.value.toFixed(2)}</strong>
                    <span className="unit-label">{measurementUnit}</span>
                  </td>
                  <td className="cell-timestamp">{formattedDate}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
};
