/** Domain data types and schemas for Waterdeep Watchtower application. */

export interface SeriesItem {
  id: number;
  name: string;
  minValue: number;
  maxValue: number;
  color: string;
  icon?: string | null;
  unit?: string | null;
}

export interface MeasurementItem {
  id: number;
  seriesId: number;
  sensorId?: number | null;
  value: number;
  timestamp: string;
}

export interface SensorItem {
  id: number;
  name: string;
  seriesId: number;
  createdAt: string;
  lastMeasurementAt?: string | null;
}

export interface SensorCreatedResponse extends SensorItem {
  apiKey: string;
}

export interface LoginResponse {
  accessToken: string;
  tokenType: string;
  expiresIn: number;
}

export interface ProblemDetailsError {
  type?: string;
  title: string;
  status: number;
  detail: string;
  instance?: string;
}

export interface TelemetryFilterCriteria {
  selectedSeriesIdentifiers: number[];
  rangeFromTimestamp?: string;
  rangeToTimestamp?: string;
  maximumResultsLimit: number;
  sortDirection: "asc" | "desc";
}
