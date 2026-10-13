export interface Track {
  id: string;
  title: string;
  mood: string;
  bpm: number;
  duration: number;
  prompt: string;
  url: string;
  created_at: number;
  play_count: number;
  last_played: number | null;
  favorite: boolean;
  disliked: boolean;
}
export interface Settings {
  mood: string;
  generation_enabled: boolean;
  buffer_minutes: number;
  track_seconds: number;
  cache_limit_mb: number;
  volume: number;
}
export interface Status {
  settings: Settings;
  provider: string;
  generating: boolean;
  buffered_seconds: number;
  queued_tracks: number;
  total_tracks: number;
  last_error: string | null;
}
export interface Preset {
  name: string;
  bpm: number[];
  description: string;
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}
function post<T>(path: string, body: object): Promise<T> {
  return json<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
export const api = {
  status: () => json<Status>("/api/status"),
  presets: () => json<Record<string, Preset>>("/api/presets"),
  history: (favorites = false) => json<Track[]>("/api/tracks?limit=30&favorites=" + favorites),
  settings: (changes: Partial<Settings>) => post<Settings>("/api/settings", changes),
  played: (id: string) => post<{ok: boolean}>("/api/tracks/" + id + "/played", {}),
  feedback: (id: string, changes: {favorite?: boolean; disliked?: boolean}) =>
    post<{ok: boolean}>("/api/tracks/" + id + "/feedback", changes),
  async next(exclude?: string): Promise<Track | null> {
    const path = "/api/tracks/next" + (exclude ? "?exclude=" + encodeURIComponent(exclude) : "");
    const response = await fetch(path);
    if (response.status === 404) return null;
    if (!response.ok) throw new Error(await response.text());
    return response.json() as Promise<Track>;
  },
};
