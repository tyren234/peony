/** Accessible composite 24-hour datetime picker component (Requirement F5, WCAG 2.2 AA). */

import React, { useEffect, useState } from "react";

interface DateTime24InputProperties {
  inputIdentifier: string;
  fieldLabel: string;
  currentIsoValue: string;
  onValueChange: (updatedIsoValue: string) => void;
  defaultTimeValue?: string;
}

const TWENTY_FOUR_HOUR_TIME_REGEX = /^([01]\d|2[0-3]):[0-5]\d$/;

export const DateTime24Input: React.FC<DateTime24InputProperties> = ({
  inputIdentifier,
  fieldLabel,
  currentIsoValue,
  onValueChange,
  defaultTimeValue = "00:00",
}) => {
  const [localDateString, setLocalDateString] = useState<string>("");
  const [localTimeString, setLocalTimeString] = useState<string>("");

  // Synchronizacja stanu lokalnego przy zmianie wartosci z zewnatrz (np. szybkie filtry lub reset)
  useEffect(() => {
    if (currentIsoValue && currentIsoValue.includes("T")) {
      const [extractedDatePart, extractedTimePart] = currentIsoValue.split("T");
      setLocalDateString(extractedDatePart);
      setLocalTimeString(extractedTimePart ? extractedTimePart.slice(0, 5) : defaultTimeValue);
    } else {
      setLocalDateString("");
      setLocalTimeString("");
    }
  }, [currentIsoValue, defaultTimeValue]);

  const handleDatePartChange = (changeEvent: React.ChangeEvent<HTMLInputElement>) => {
    const updatedDate = changeEvent.target.value;
    setLocalDateString(updatedDate);

    if (!updatedDate) {
      setLocalTimeString("");
      onValueChange("");
      return;
    }

    const effectiveTime =
      localTimeString && TWENTY_FOUR_HOUR_TIME_REGEX.test(localTimeString)
        ? localTimeString
        : defaultTimeValue;

    if (!localTimeString || !TWENTY_FOUR_HOUR_TIME_REGEX.test(localTimeString)) {
      setLocalTimeString(effectiveTime);
    }

    onValueChange(`${updatedDate}T${effectiveTime}`);
  };

  const handleTimePartChange = (changeEvent: React.ChangeEvent<HTMLInputElement>) => {
    let sanitizedTimeValue = changeEvent.target.value.replace(/[^0-9:]/g, "");

    // Automatyczne dodawanie dwukropka po wpisaniu dwoch cyfr godziny
    if (
      sanitizedTimeValue.length === 2 &&
      !sanitizedTimeValue.includes(":") &&
      !changeEvent.target.value.endsWith(":")
    ) {
      const parsedHours = parseInt(sanitizedTimeValue, 10);
      if (parsedHours >= 0 && parsedHours <= 23) {
        sanitizedTimeValue = `${sanitizedTimeValue}:`;
      }
    }

    if (sanitizedTimeValue.length > 5) {
      sanitizedTimeValue = sanitizedTimeValue.slice(0, 5);
    }

    setLocalTimeString(sanitizedTimeValue);

    if (TWENTY_FOUR_HOUR_TIME_REGEX.test(sanitizedTimeValue) && localDateString) {
      onValueChange(`${localDateString}T${sanitizedTimeValue}`);
    }
  };

  const handleTimeKeyDown = (keyboardEvent: React.KeyboardEvent<HTMLInputElement>) => {
    if (keyboardEvent.key === "ArrowUp" || keyboardEvent.key === "ArrowDown") {
      keyboardEvent.preventDefault();
      const currentHoursMinutes = localTimeString && TWENTY_FOUR_HOUR_TIME_REGEX.test(localTimeString)
        ? localTimeString
        : defaultTimeValue;

      const [currentHourText, currentMinuteText] = currentHoursMinutes.split(":");
      let currentHourNumber = parseInt(currentHourText, 10);

      if (keyboardEvent.key === "ArrowUp") {
        currentHourNumber = (currentHourNumber + 1) % 24;
      } else {
        currentHourNumber = (currentHourNumber - 1 + 24) % 24;
      }

      const formattedHour = String(currentHourNumber).padStart(2, "0");
      const updatedTime = `${formattedHour}:${currentMinuteText}`;
      setLocalTimeString(updatedTime);

      if (localDateString) {
        onValueChange(`${localDateString}T${updatedTime}`);
      }
    }
  };

  return (
    <div className="datetime-input-wrapper">
      <label htmlFor={`${inputIdentifier}-date`} className="datetime-control-label">
        {fieldLabel}
      </label>
      <div className="datetime-24-composite-control">
        <input
          type="date"
          id={`${inputIdentifier}-date`}
          value={localDateString}
          onChange={handleDatePartChange}
          className="datetime-date-picker-input"
          aria-label={`${fieldLabel} - data kalendarzowa`}
        />
        <div className="time-24-subcontrol-wrapper">
          <input
            type="text"
            id={`${inputIdentifier}-time`}
            value={localTimeString}
            onChange={handleTimePartChange}
            onKeyDown={handleTimeKeyDown}
            placeholder="14:00"
            maxLength={5}
            inputMode="numeric"
            className="datetime-time-24-input"
            aria-label={`${fieldLabel} - godzina w formacie 24-godzinnym GG:MM`}
            title="Format 24-godzinny (GG:MM, np. 14:30). Uzyj strzalek w gore/dol, aby zmienic godzine."
          />
          <span className="time-format-hint-badge" aria-hidden="true">
            24h
          </span>
        </div>
      </div>
    </div>
  );
};
