/** Minimalist administrator panel for managing series and sensors (Requirements F3, F4, F8, F12). */

import React, { useEffect, useState } from "react";
import {
  createSeries,
  deleteSeries,
  fetchSensors,
  loginAdministrator,
  logoutAdministrator,
  changePassword,
  registerSensor,
  unregisterSensor,
} from "../services/api";
import type { SensorItem, SeriesItem } from "../types";

interface AdminPanelProperties {
  seriesList: SeriesItem[];
  onSeriesMutated: () => void;
}

export const AdminPanel: React.FC<AdminPanelProperties> = ({
  seriesList,
  onSeriesMutated,
}) => {
  const [bearerToken, setBearerToken] = useState<string>(() => {
    return sessionStorage.getItem("waterdeep_auth_token") || "";
  });
  const [loginUsername, setLoginUsername] = useState<string>("admin");
  const [loginPassword, setLoginPassword] = useState<string>("");
  const [loginErrorMessage, setLoginErrorMessage] = useState<string>("");
  const [actionFeedbackMessage, setActionFeedbackMessage] = useState<string>("");

  // Stan czujników
  const [sensorsList, setSensorsList] = useState<SensorItem[]>([]);
  const [newlyCreatedApiKey, setNewlyCreatedApiKey] = useState<string>("");

  // Stan nowej serii
  const [newSeriesName, setNewSeriesName] = useState<string>("");
  const [newSeriesMinValue, setNewSeriesMinValue] = useState<string>("0.0");
  const [newSeriesMaxValue, setNewSeriesMaxValue] = useState<string>("100.0");
  const [newSeriesColor, setNewSeriesColor] = useState<string>("#2563eb");
  const [newSeriesUnit, setNewSeriesUnit] = useState<string>("%");

  // Stan nowego czujnika
  const [newSensorName, setNewSensorName] = useState<string>("");
  const [newSensorSeriesId, setNewSensorSeriesId] = useState<number>(
    seriesList.length > 0 ? seriesList[0].id : 1
  );

  // Stan zmiany hasła (F8)
  const [currentPasswordValue, setCurrentPasswordValue] = useState<string>("");
  const [newPasswordValue, setNewPasswordValue] = useState<string>("");
  const [confirmPasswordValue, setConfirmPasswordValue] = useState<string>("");


  useEffect(() => {
    if (seriesList.length > 0 && !newSensorSeriesId) {
      setNewSensorSeriesId(seriesList[0].id);
    }
  }, [seriesList, newSensorSeriesId]);

  const refreshSensorsList = async (activeToken: string) => {
    try {
      const loadedSensors = await fetchSensors(activeToken);
      setSensorsList(loadedSensors);
    } catch (loadError) {
      console.error("Błąd pobierania listy czujników:", loadError);
    }
  };

  useEffect(() => {
    if (bearerToken) {
      refreshSensorsList(bearerToken);
    }
  }, [bearerToken]);

  const handlePerformLogin = async (formSubmitEvent: React.FormEvent) => {
    formSubmitEvent.preventDefault();
    setLoginErrorMessage("");
    try {
      const loginResult = await loginAdministrator(loginUsername, loginPassword);
      setBearerToken(loginResult.accessToken);
      sessionStorage.setItem("waterdeep_auth_token", loginResult.accessToken);
      setLoginPassword("");
      setActionFeedbackMessage("Zalogowano pomyślnie jako administrator.");
    } catch (authenticationError) {
      setLoginErrorMessage(
        authenticationError instanceof Error
          ? authenticationError.message
          : "Niepoprawne dane logowania"
      );
    }
  };

  const handlePerformLogout = async () => {
    if (bearerToken) {
      try {
        await logoutAdministrator(bearerToken);
      } catch (logoutError) {
        console.error("Błąd wylogowania:", logoutError);
      }
    }
    setBearerToken("");
    sessionStorage.removeItem("waterdeep_auth_token");
    setSensorsList([]);
    setNewlyCreatedApiKey("");
    setActionFeedbackMessage("Wylogowano pomyślnie.");
  };

  const handleCreateSeriesSubmit = async (formSubmitEvent: React.FormEvent) => {
    formSubmitEvent.preventDefault();
    setActionFeedbackMessage("");

    const parsedMinValue = parseFloat(newSeriesMinValue);
    const parsedMaxValue = parseFloat(newSeriesMaxValue);

    if (isNaN(parsedMinValue) || isNaN(parsedMaxValue)) {
      setActionFeedbackMessage("Błąd: Wartości min i max muszą być liczbami.");
      return;
    }

    if (parsedMinValue >= parsedMaxValue) {
      setActionFeedbackMessage("Błąd (F4): Wartość minimalna musi być ściśle mniejsza od maksymalnej.");
      return;
    }

    try {
      await createSeries(bearerToken, {
        name: newSeriesName.trim(),
        minValue: parsedMinValue,
        maxValue: parsedMaxValue,
        color: newSeriesColor,
        unit: newSeriesUnit.trim() || null,
        icon: null,
      });
      setNewSeriesName("");
      setActionFeedbackMessage(`Pomyślnie utworzono nową serię.`);
      onSeriesMutated();
    } catch (creationError) {
      setActionFeedbackMessage(
        creationError instanceof Error ? creationError.message : "Błąd tworzenia serii"
      );
    }
  };

  const handleDeleteSeriesClick = async (seriesIdentifier: number, seriesDisplayName: string) => {
    const confirmation = window.confirm(
      `Czy na pewno chcesz usunąć serię '${seriesDisplayName}'? Kaskadowo zostaną usunięte jej czujniki i pomiary.`
    );
    if (!confirmation) {
      return;
    }

    try {
      await deleteSeries(bearerToken, seriesIdentifier);
      setActionFeedbackMessage(`Pomyślnie usunięto serię '${seriesDisplayName}'.`);
      onSeriesMutated();
      if (bearerToken) {
        refreshSensorsList(bearerToken);
      }
    } catch (deletionError) {
      setActionFeedbackMessage(
        deletionError instanceof Error ? deletionError.message : "Błąd usuwania serii"
      );
    }
  };

  const handleRegisterSensorSubmit = async (formSubmitEvent: React.FormEvent) => {
    formSubmitEvent.preventDefault();
    setNewlyCreatedApiKey("");
    setActionFeedbackMessage("");

    if (!newSensorName.trim()) {
      setActionFeedbackMessage("Błąd: Podaj nazwę czujnika.");
      return;
    }

    try {
      const createdSensorResponse = await registerSensor(
        bearerToken,
        newSensorName.trim(),
        newSensorSeriesId
      );
      setNewlyCreatedApiKey(createdSensorResponse.apiKey);
      setNewSensorName("");
      setActionFeedbackMessage(`Pomyślnie zarejestrowano czujnik '${createdSensorResponse.name}'.`);
      refreshSensorsList(bearerToken);
    } catch (registrationError) {
      setActionFeedbackMessage(
        registrationError instanceof Error ? registrationError.message : "Błąd rejestracji czujnika"
      );
    }
  };

  const handleChangePasswordSubmit = async (formSubmitEvent: React.FormEvent) => {
    formSubmitEvent.preventDefault();
    setActionFeedbackMessage("");

    if (newPasswordValue !== confirmPasswordValue) {
      setActionFeedbackMessage("Błąd: Nowe hasło i potwierdzenie hasła nie są identyczne.");
      return;
    }

    if (newPasswordValue.length < 8) {
      setActionFeedbackMessage("Błąd: Nowe hasło musi mieć co najmniej 8 znaków.");
      return;
    }

    try {
      await changePassword(bearerToken, currentPasswordValue, newPasswordValue);
      setCurrentPasswordValue("");
      setNewPasswordValue("");
      setConfirmPasswordValue("");
      setActionFeedbackMessage("Hasło administratora zostało pomyślnie zmienione.");
    } catch (passwordChangeError) {
      setActionFeedbackMessage(
        passwordChangeError instanceof Error
          ? passwordChangeError.message
          : "Błąd podczas zmiany hasła"
      );
    }
  };

  const handleUnregisterSensorClick = async (sensorIdentifier: number, sensorDisplayName: string) => {
    const confirmation = window.confirm(
      `Wyrejestrować czujnik '${sensorDisplayName}'? Klucz API przestanie działać, a zebrane wyniki pozostaną.`
    );
    if (!confirmation) {
      return;
    }

    try {
      await unregisterSensor(bearerToken, sensorIdentifier);
      setActionFeedbackMessage(`Wyrejestrowano czujnik '${sensorDisplayName}'.`);
      refreshSensorsList(bearerToken);
    } catch (unregistrationError) {
      setActionFeedbackMessage(
        unregistrationError instanceof Error ? unregistrationError.message : "Błąd wyrejestrowania"
      );
    }
  };

  return (
    <section className="admin-container" aria-label="Panel administratora">
      <h2 className="section-heading">⚙️ Panel Zarządzania (Administrator)</h2>

      {actionFeedbackMessage && (
        <div className="feedback-banner" role="status">
          {actionFeedbackMessage}
        </div>
      )}

      {!bearerToken ? (
        <form onSubmit={handlePerformLogin} className="admin-login-form">
          <p className="login-hint">Zaloguj się kontem administratora, aby zarządzać seriami i sensorami.</p>
          {loginErrorMessage && <p className="error-message" role="alert">{loginErrorMessage}</p>}
          <div className="form-row">
            <label htmlFor="admin-username-input">Użytkownik:</label>
            <input
              id="admin-username-input"
              type="text"
              value={loginUsername}
              onChange={(changeEvent) => setLoginUsername(changeEvent.target.value)}
              required
            />
          </div>
          <div className="form-row">
            <label htmlFor="admin-password-input">Hasło:</label>
            <input
              id="admin-password-input"
              type="password"
              value={loginPassword}
              onChange={(changeEvent) => setLoginPassword(changeEvent.target.value)}
              required
            />
          </div>
          <button type="submit" className="primary-button">Zaloguj się</button>
        </form>
      ) : (
        <div className="admin-authenticated-workspace">
          <div className="workspace-header">
            <span>Zalogowano jako administrator</span>
            <button onClick={handlePerformLogout} className="secondary-button">Wyloguj</button>
          </div>

          {/* Rejestracja czujnika i jednorazowy klucz API */}
          {newlyCreatedApiKey && (
            <div className="one-time-key-alert" role="alert">
              <strong>🔑 Nowo wygenerowany klucz API czujnika:</strong>
              <div className="key-code-display">{newlyCreatedApiKey}</div>
              <p className="key-warning">
                Zapisz ten klucz teraz! Ze względów bezpieczeństwa (SHA-256) klucz nigdy więcej nie zostanie ujawniony.
              </p>
            </div>
          )}

          <div className="admin-grid-sections">
            {/* Formularz nowej serii */}
            <div className="admin-card">
              <h3>Dodaj nową serię</h3>
              <form onSubmit={handleCreateSeriesSubmit}>
                <div className="form-field">
                  <label htmlFor="series-name-input">Nazwa serii:</label>
                  <input
                    id="series-name-input"
                    type="text"
                    value={newSeriesName}
                    onChange={(changeEvent) => setNewSeriesName(changeEvent.target.value)}
                    placeholder="np. Poziom wody w Dokerze"
                    required
                  />
                </div>
                <div className="form-row-dual">
                  <div className="form-field">
                    <label htmlFor="series-min-input">Wartość min:</label>
                    <input
                      id="series-min-input"
                      type="number"
                      step="any"
                      value={newSeriesMinValue}
                      onChange={(changeEvent) => setNewSeriesMinValue(changeEvent.target.value)}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label htmlFor="series-max-input">Wartość max:</label>
                    <input
                      id="series-max-input"
                      type="number"
                      step="any"
                      value={newSeriesMaxValue}
                      onChange={(changeEvent) => setNewSeriesMaxValue(changeEvent.target.value)}
                      required
                    />
                  </div>
                </div>
                <div className="form-row-dual">
                  <div className="form-field">
                    <label htmlFor="series-color-input">Kolor:</label>
                    <input
                      id="series-color-input"
                      type="color"
                      value={newSeriesColor}
                      onChange={(changeEvent) => setNewSeriesColor(changeEvent.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label htmlFor="series-unit-input">Jednostka:</label>
                    <input
                      id="series-unit-input"
                      type="text"
                      value={newSeriesUnit}
                      onChange={(changeEvent) => setNewSeriesUnit(changeEvent.target.value)}
                      placeholder="%"
                    />
                  </div>
                </div>
                <button type="submit" className="primary-button">Utwórz serię</button>
              </form>
            </div>

            {/* Rejestracja czujnika */}
            <div className="admin-card">
              <h3>Zarejestruj czujnik</h3>
              <form onSubmit={handleRegisterSensorSubmit}>
                <div className="form-field">
                  <label htmlFor="sensor-name-input">Nazwa czujnika:</label>
                  <input
                    id="sensor-name-input"
                    type="text"
                    value={newSensorName}
                    onChange={(changeEvent) => setNewSensorName(changeEvent.target.value)}
                    placeholder="np. Czujnik Bramy #2"
                    required
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="sensor-series-select">Przypisana seria:</label>
                  <select
                    id="sensor-series-select"
                    value={newSensorSeriesId}
                    onChange={(changeEvent) => setNewSensorSeriesId(Number(changeEvent.target.value))}
                  >
                    {seriesList.map((seriesEntry) => (
                      <option key={seriesEntry.id} value={seriesEntry.id}>
                        {seriesEntry.name} ({seriesEntry.minValue} - {seriesEntry.maxValue})
                      </option>
                    ))}
                  </select>
                </div>
                <button type="submit" className="primary-button">Zarejestruj i pobierz klucz API</button>
              </form>
            </div>

            {/* Zmiana hasła administratora (F8) */}
            <div className="admin-card">
              <h3>Zmień hasło administratora (F8)</h3>
              <form onSubmit={handleChangePasswordSubmit}>
                <div className="form-field">
                  <label htmlFor="current-password-input">Bieżące hasło:</label>
                  <input
                    id="current-password-input"
                    type="password"
                    value={currentPasswordValue}
                    onChange={(changeEvent) => setCurrentPasswordValue(changeEvent.target.value)}
                    required
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="new-password-input">Nowe hasło:</label>
                  <input
                    id="new-password-input"
                    type="password"
                    value={newPasswordValue}
                    onChange={(changeEvent) => setNewPasswordValue(changeEvent.target.value)}
                    required
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="confirm-password-input">Potwierdź nowe hasło:</label>
                  <input
                    id="confirm-password-input"
                    type="password"
                    value={confirmPasswordValue}
                    onChange={(changeEvent) => setConfirmPasswordValue(changeEvent.target.value)}
                    required
                  />
                </div>
                <button type="submit" className="primary-button">Zaktualizuj hasło</button>
              </form>
            </div>
          </div>

          {/* Lista czujników */}
          <div className="admin-list-section">
            <h3>Zarejestrowane czujniki ({sensorsList.length})</h3>
            {sensorsList.length === 0 ? (
              <p>Brak zarejestrowanych czujników.</p>
            ) : (
              <ul className="sensors-list">
                {sensorsList.map((sensorEntry) => {
                  const matchingSeries = seriesList.find(
                    (candidateSeries) => candidateSeries.id === sensorEntry.seriesId
                  );
                  const lastReadingDisplay = sensorEntry.lastMeasurementAt
                    ? new Date(sensorEntry.lastMeasurementAt).toLocaleString()
                    : "brak odczytów";

                  return (
                    <li key={sensorEntry.id} className="sensor-list-item">
                      <div className="sensor-meta">
                        <strong>{sensorEntry.name}</strong>
                        <span className="sensor-series-name">
                          Seria: {matchingSeries ? matchingSeries.name : `#${sensorEntry.seriesId}`}
                        </span>
                        <span className="sensor-last-reading">Ostatni pomiar: {lastReadingDisplay}</span>
                      </div>
                      <button
                        onClick={() => handleUnregisterSensorClick(sensorEntry.id, sensorEntry.name)}
                        className="danger-button"
                      >
                        Wyrejestruj
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {/* Zarządzanie istniejącymi seriami */}
          <div className="admin-list-section">
            <h3>Zarządzanie seriami pomiarowymi</h3>
            <ul className="series-manage-list">
              {seriesList.map((seriesEntry) => (
                <li key={seriesEntry.id} className="series-manage-item">
                  <span className="series-color-tag" style={{ backgroundColor: seriesEntry.color }} />
                  <strong>{seriesEntry.name}</strong>
                  <span>Zakres: [{seriesEntry.minValue}, {seriesEntry.maxValue}] {seriesEntry.unit || ""}</span>
                  <button
                    onClick={() => handleDeleteSeriesClick(seriesEntry.id, seriesEntry.name)}
                    className="danger-button"
                  >
                    Usuń serię
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </section>
  );
};
