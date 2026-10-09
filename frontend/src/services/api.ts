/** API client for Waterdeep Watchtower REST API. */

import type {
  LoginResponse,
  MeasurementItem,
  ProblemDetailsError,
  SensorCreatedResponse,
  SensorItem,
  SeriesItem,
  TelemetryFilterCriteria,
} from "../types";

const apiBaseUrl = "";

async function parseJsonResponseOrThrow<ResultType>(responseObject: Response): Promise<ResultType> {
  if (responseObject.status === 204) {
    return {} as ResultType;
  }

  const responseText = await responseObject.text();
  let parsedJsonPayload: unknown;
  try {
    parsedJsonPayload = responseText ? JSON.parse(responseText) : {};
  } catch {
    throw new Error(`Błąd parsowania odpowiedzi serwera (kod ${responseObject.status})`);
  }

  if (!responseObject.ok) {
    const problemError = parsedJsonPayload as ProblemDetailsError;
    const errorMessage =
      problemError.detail || problemError.title || `Błąd serwera (status ${responseObject.status})`;
    throw new Error(errorMessage);
  }

  return parsedJsonPayload as ResultType;
}

export async function fetchAllSeries(): Promise<SeriesItem[]> {
  const requestResponse = await fetch(`${apiBaseUrl}/api/series`, {
    headers: { Accept: "application/json" },
  });
  return parseJsonResponseOrThrow<SeriesItem[]>(requestResponse);
}

export async function fetchMeasurements(
  filterCriteria: TelemetryFilterCriteria
): Promise<MeasurementItem[]> {
  const queryParameters = new URLSearchParams();

  if (filterCriteria.selectedSeriesIdentifiers.length > 0) {
    queryParameters.set("series", filterCriteria.selectedSeriesIdentifiers.join(","));
  }
  if (filterCriteria.rangeFromTimestamp) {
    queryParameters.set("from", filterCriteria.rangeFromTimestamp);
  }
  if (filterCriteria.rangeToTimestamp) {
    queryParameters.set("to", filterCriteria.rangeToTimestamp);
  }
  if (filterCriteria.sortDirection === "desc") {
    queryParameters.set("sort", "-timestamp");
  } else {
    queryParameters.set("sort", "timestamp");
  }
  queryParameters.set("limit", String(filterCriteria.maximumResultsLimit));

  const requestUrl = `${apiBaseUrl}/api/measurements?${queryParameters.toString()}`;
  const requestResponse = await fetch(requestUrl, {
    headers: { Accept: "application/json" },
  });
  return parseJsonResponseOrThrow<MeasurementItem[]>(requestResponse);
}

export async function loginAdministrator(
  accountUsername: string,
  accountPassword: string
): Promise<LoginResponse> {
  const requestResponse = await fetch(`${apiBaseUrl}/api/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      username: accountUsername,
      password: accountPassword,
    }),
  });
  return parseJsonResponseOrThrow<LoginResponse>(requestResponse);
}

export async function logoutAdministrator(bearerToken: string): Promise<void> {
  const requestResponse = await fetch(`${apiBaseUrl}/api/auth/logout`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${bearerToken}`,
    },
  });
  await parseJsonResponseOrThrow<void>(requestResponse);
}

export async function fetchSensors(bearerToken: string): Promise<SensorItem[]> {
  const requestResponse = await fetch(`${apiBaseUrl}/api/sensors`, {
    headers: {
      Authorization: `Bearer ${bearerToken}`,
      Accept: "application/json",
    },
  });
  return parseJsonResponseOrThrow<SensorItem[]>(requestResponse);
}

export async function createSeries(
  bearerToken: string,
  seriesPayload: Omit<SeriesItem, "id">
): Promise<SeriesItem> {
  const requestResponse = await fetch(`${apiBaseUrl}/api/series`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${bearerToken}`,
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(seriesPayload),
  });
  return parseJsonResponseOrThrow<SeriesItem>(requestResponse);
}

export async function updateSeries(
  bearerToken: string,
  seriesIdentifier: number,
  seriesPayload: Omit<SeriesItem, "id">
): Promise<SeriesItem> {
  const requestResponse = await fetch(`${apiBaseUrl}/api/series/${seriesIdentifier}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${bearerToken}`,
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(seriesPayload),
  });
  return parseJsonResponseOrThrow<SeriesItem>(requestResponse);
}

export async function deleteSeries(
  bearerToken: string,
  seriesIdentifier: number
): Promise<void> {
  const requestResponse = await fetch(`${apiBaseUrl}/api/series/${seriesIdentifier}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${bearerToken}`,
    },
  });
  await parseJsonResponseOrThrow<void>(requestResponse);
}

export async function registerSensor(
  bearerToken: string,
  sensorName: string,
  targetSeriesIdentifier: number
): Promise<SensorCreatedResponse> {
  const requestResponse = await fetch(`${apiBaseUrl}/api/sensors`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${bearerToken}`,
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      name: sensorName,
      seriesId: targetSeriesIdentifier,
    }),
  });
  return parseJsonResponseOrThrow<SensorCreatedResponse>(requestResponse);
}

export async function unregisterSensor(
  bearerToken: string,
  sensorIdentifier: number
): Promise<void> {
  const requestResponse = await fetch(`${apiBaseUrl}/api/sensors/${sensorIdentifier}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${bearerToken}`,
    },
  });
  await parseJsonResponseOrThrow<void>(requestResponse);
}

export async function changePassword(
  bearerToken: string,
  currentPasswordValue: string,
  newPasswordValue: string
): Promise<void> {
  const requestResponse = await fetch(`${apiBaseUrl}/api/auth/password`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${bearerToken}`,
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      currentPassword: currentPasswordValue,
      newPassword: newPasswordValue,
    }),
  });
  await parseJsonResponseOrThrow<void>(requestResponse);
}
