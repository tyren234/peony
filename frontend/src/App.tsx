/** Minimalist single-page application entry point for Waterdeep Watchtower. */

import React, { useEffect, useState } from "react";
import { AdminPanel } from "./components/AdminPanel";
import { TelemetryChart } from "./components/TelemetryChart";
import { TelemetryTable } from "./components/TelemetryTable";
import { fetchAllSeries, fetchMeasurements } from "./services/api";
import type { MeasurementItem, SeriesItem, TelemetryFilterCriteria } from "./types";

export const App: React.FC = () => {
  const [seriesList, setSeriesList] = useState<SeriesItem[]>([]);
  const [measurementsList, setMeasurementsList] = useState<MeasurementItem[]>([]);
  const [selectedSeriesIdentifiers, setSelectedSeriesIdentifiers] = useState<number[]>([]);
  const [rangeFromTimestamp, setRangeFromTimestamp] = useState<string>("");
  const [rangeToTimestamp, setRangeToTimestamp] = useState<string>("");
  const [selectedMeasurementIdentifier, setSelectedMeasurementIdentifier] = useState<number | null>(null);
  const [isLoadingData, setIsLoadingData] = useState<boolean>(true);
  const [applicationErrorMessage, setApplicationErrorMessage] = useState<string>("");

  const loadSeriesData = async () => {
    try {
      const loadedSeries = await fetchAllSeries();
      setSeriesList(loadedSeries);
      if (selectedSeriesIdentifiers.length === 0) {
        setSelectedSeriesIdentifiers(loadedSeries.map((seriesEntry) => seriesEntry.id));
      }
    } catch (loadError) {
      setApplicationErrorMessage(
        loadError instanceof Error ? loadError.message : "Błąd pobierania serii"
      );
    }
  };

  const loadMeasurementsData = async () => {
    setIsLoadingData(true);
    setApplicationErrorMessage("");
    try {
      const filterCriteria: TelemetryFilterCriteria = {
        selectedSeriesIdentifiers: selectedSeriesIdentifiers,
        rangeFromTimestamp: rangeFromTimestamp ? new Date(rangeFromTimestamp).toISOString() : undefined,
        rangeToTimestamp: rangeToTimestamp ? new Date(rangeToTimestamp).toISOString() : undefined,
        maximumResultsLimit: 500,
        sortDirection: "asc",
      };
      const loadedMeasurements = await fetchMeasurements(filterCriteria);
      setMeasurementsList(loadedMeasurements);
    } catch (loadError) {
      setApplicationErrorMessage(
        loadError instanceof Error ? loadError.message : "Błąd pobierania pomiarów"
      );
    } finally {
      setIsLoadingData(false);
    }
  };

  useEffect(() => {
    loadSeriesData();
  }, []);

  useEffect(() => {
    if (seriesList.length > 0) {
      loadMeasurementsData();
    }
  }, [seriesList, selectedSeriesIdentifiers, rangeFromTimestamp, rangeToTimestamp]);

  const handleToggleSeriesSelection = (seriesIdentifier: number) => {
    setSelectedSeriesIdentifiers((previousSelectedIdentifiers) => {
      if (previousSelectedIdentifiers.includes(seriesIdentifier)) {
        if (previousSelectedIdentifiers.length === 1) {
          return previousSelectedIdentifiers; // Zostaw przynajmniej jedną serię
        }
        return previousSelectedIdentifiers.filter(
          (candidateIdentifier) => candidateIdentifier !== seriesIdentifier
        );
      }
      return [...previousSelectedIdentifiers, seriesIdentifier];
    });
  };

  const handleSetQuickRangeAll = () => {
    setRangeFromTimestamp("");
    setRangeToTimestamp("");
  };

  const handleSetQuickRangeLastHour = () => {
    const oneHourAgoMoment = new Date(Date.now() - 60 * 60 * 1000);
    setRangeFromTimestamp(oneHourAgoMoment.toISOString().slice(0, 16));
    setRangeToTimestamp("");
  };

  const handleSetQuickRangeLastDay = () => {
    const oneDayAgoMoment = new Date(Date.now() - 24 * 60 * 60 * 1000);
    setRangeFromTimestamp(oneDayAgoMoment.toISOString().slice(0, 16));
    setRangeToTimestamp("");
  };

  return (
    <div className="watchtower-application-root">
      <header className="application-header">
        <div className="header-title-container">
          <h1 className="header-main-title">🏰 Waterdeep Watchtower</h1>
          <p className="header-subtitle">
            Punkt Dowodzenia Straży Miejskiej Waterdeep i Wieży Blackstaffa
          </p>
        </div>
        <div className="header-meta-actions no-print">
          <button
            onClick={() => window.print()}
            className="secondary-button"
            title="Drukuj raport pomiarów"
            aria-label="Drukuj raport pomiarów"
          >
            🖨️ Drukuj raport
          </button>
        </div>
      </header>

      {applicationErrorMessage && (
        <div className="feedback-banner error-banner" role="alert">
          {applicationErrorMessage}
        </div>
      )}

      <main className="application-main-content">
        {/* Panel filtrów */}
        <section className="filter-controls no-print" aria-label="Filtry pomiarów">
          <div className="series-filter-group">
            <span className="filter-group-label">Serie do wyświetlenia:</span>
            <div className="series-checkboxes-list">
              {seriesList.map((seriesEntry) => {
                const isSeriesChecked = selectedSeriesIdentifiers.includes(seriesEntry.id);
                return (
                  <label key={seriesEntry.id} className="series-checkbox-label">
                    <input
                      type="checkbox"
                      checked={isSeriesChecked}
                      onChange={() => handleToggleSeriesSelection(seriesEntry.id)}
                    />
                    <span
                      className="series-indicator-dot"
                      style={{ backgroundColor: seriesEntry.color }}
                      aria-hidden="true"
                    />
                    <span>{seriesEntry.name}</span>
                  </label>
                );
              })}
            </div>
          </div>

          <div className="time-filter-group">
            <div className="datetime-input-wrapper">
              <label htmlFor="filter-from-datetime">Od (from):</label>
              <input
                id="filter-from-datetime"
                type="datetime-local"
                value={rangeFromTimestamp}
                onChange={(changeEvent) => setRangeFromTimestamp(changeEvent.target.value)}
              />
            </div>
            <div className="datetime-input-wrapper">
              <label htmlFor="filter-to-datetime">Do (to):</label>
              <input
                id="filter-to-datetime"
                type="datetime-local"
                value={rangeToTimestamp}
                onChange={(changeEvent) => setRangeToTimestamp(changeEvent.target.value)}
              />
            </div>
            <div className="quick-ranges-bar">
              <button onClick={handleSetQuickRangeAll} className="quick-filter-button">Wszystko</button>
              <button onClick={handleSetQuickRangeLastHour} className="quick-filter-button">Ostatnia 1h</button>
              <button onClick={handleSetQuickRangeLastDay} className="quick-filter-button">Ostatnie 24h</button>
              <button onClick={loadMeasurementsData} className="primary-button">Odśwież</button>
            </div>
          </div>
        </section>

        {/* Informacja o ładowaniu */}
        {isLoadingData && (
          <div className="loading-indicator" role="status">
            Pobieranie aktualnych odczytów telemetrii...
          </div>
        )}

        {/* Interaktywny wykres (F2, WCAG 2.2 AA) */}
        <TelemetryChart
          seriesList={seriesList.filter((candidateSeries) =>
            selectedSeriesIdentifiers.includes(candidateSeries.id)
          )}
          measurementsList={measurementsList}
          selectedMeasurementIdentifier={selectedMeasurementIdentifier}
          onSelectMeasurement={setSelectedMeasurementIdentifier}
        />

        {/* Zsynchronizowana tabela danych (F6) */}
        <TelemetryTable
          seriesList={seriesList}
          measurementsList={measurementsList}
          selectedMeasurementIdentifier={selectedMeasurementIdentifier}
          onSelectMeasurement={setSelectedMeasurementIdentifier}
        />

        {/* Panel administratora (F3, F8, F12) */}
        <div className="no-print">
          <AdminPanel
            seriesList={seriesList}
            onSeriesMutated={() => {
              loadSeriesData();
              loadMeasurementsData();
            }}
          />
        </div>
      </main>

      <footer className="application-footer no-print">
        <p>Straż Miejska Waterdeep &copy; 2026. Projekt Zaawansowane Aplikacje Internetowe (ZAI 26Z).</p>
      </footer>
    </div>
  );
};

export default App;
