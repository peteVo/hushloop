import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Status, type Track } from "./api";
import { crossfadeCurves } from "./crossfade.js";

type Slot = { audio: HTMLAudioElement; gain: GainNode; track: Track };

export function useRadio() {
  const [status, setStatus] = useState<Status | null>(null);
  const [track, setTrack] = useState<Track | null>(null);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [volume, setVolume] = useState(0.65);

  const context = useRef<AudioContext | null>(null);
  const master = useRef<GainNode | null>(null);
  const current = useRef<Slot | null>(null);
  const pending = useRef<Slot | null>(null);
  const fading = useRef<Slot | null>(null);
  const prefetching = useRef(false);
  const transitioning = useRef(false);
  const playingRef = useRef(false);
  const startTicket = useRef(0);
  const fadeTimeout = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const state = await api.status();
      setStatus(state);
      return state;
    } catch {
      setError("Local radio server is not reachable. Start the Python backend.");
      return null;
    }
  }, []);

  useEffect(() => {
    void (async () => {
      const s = await refresh();
      if (s) setVolume(s.settings.volume);
    })();
    const timer = window.setInterval(() => { void refresh(); }, 3000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    if (master.current) master.current.gain.value = volume;
    const timer = window.setTimeout(() => { void api.settings({ volume }).catch(() => {}); }, 500);
    return () => window.clearTimeout(timer);
  }, [volume]);

  function getContext(): AudioContext {
    if (!context.current) {
      const ctx = new AudioContext();
      const masterNode = ctx.createGain();
      masterNode.gain.value = volume;
      masterNode.connect(ctx.destination);
      context.current = ctx;
      master.current = masterNode;
    }
    return context.current;
  }

  function createSlot(item: Track): Slot {
    const ctx = getContext();
    const audio = new Audio(item.url);
    audio.preload = "auto";
    const gain = ctx.createGain();
    gain.gain.value = 0;
    ctx.createMediaElementSource(audio).connect(gain);
    gain.connect(master.current!);
    const slot: Slot = { audio, gain, track: item };
    audio.addEventListener("ended", () => {
      if (current.current === slot && !transitioning.current && playingRef.current) {
        void advance();
      }
    });
    audio.load();
    return slot;
  }

  function dispose(slot: Slot | null) {
    if (!slot) return;
    slot.audio.pause();
    slot.audio.removeAttribute("src");
    slot.audio.load();
    slot.gain.disconnect();
  }

  async function prefetch() {
    if (!current.current || pending.current || prefetching.current) return;
    prefetching.current = true;
    try {
      const item = await api.next(current.current.track.id);
      if (item && current.current && !pending.current) {
        pending.current = createSlot(item);
      }
    } catch {
      // Retry on the next interval; music that already exists keeps playing.
    } finally {
      prefetching.current = false;
    }
  }

  async function advance(fadeSeconds = 4) {
    if (transitioning.current || !current.current) return;
    if (!pending.current) await prefetch();
    const next = pending.current;
    const old = current.current;
    if (!next || !old) return;
    transitioning.current = true;
    pending.current = null;
    try {
      const ctx = getContext();
      await ctx.resume();
      await next.audio.play();
      const seconds = Math.max(0, Math.min(fadeSeconds, old.audio.duration - old.audio.currentTime || 0));
      if (seconds === 0) {
        next.gain.gain.value = 1;
        old.gain.gain.value = 0;
      } else {
        const { fadeIn, fadeOut } = crossfadeCurves();
        next.gain.gain.setValueCurveAtTime(fadeIn, ctx.currentTime, seconds);
        old.gain.gain.setValueCurveAtTime(fadeOut, ctx.currentTime, seconds);
      }
      current.current = next;
      fading.current = old;
      setTrack(next.track);
      void api.played(next.track.id);
      fadeTimeout.current = window.setTimeout(() => {
        dispose(old);
        if (fading.current === old) fading.current = null;
        transitioning.current = false;
        fadeTimeout.current = null;
        void prefetch();
      }, seconds * 1000 + 80);
    } catch (e) {
      dispose(next);
      transitioning.current = false;
      setError(e instanceof Error ? e.message : "Playback transition failed");
    }
  }

  const start = useCallback(async () => {
    if (loading) return;
    const ticket = ++startTicket.current;
    setLoading(true);
    setError(null);
    try {
      const ctx = getContext();
      await ctx.resume();
      if (!current.current) await api.settings({ generation_enabled: true });
      if (current.current) {
        await Promise.all([current.current, fading.current].filter((s): s is Slot => !!s).map(s => s.audio.play()));
        playingRef.current = true;
        setPlaying(true);
        return;
      }
      // Initial buffer may require substantial GPU inference time.
      while (ticket === startTicket.current) {
        const candidate = await api.next();
        if (candidate) {
          const slot = createSlot(candidate);
          slot.gain.gain.value = 1;
          await slot.audio.play();
          if (ticket !== startTicket.current) { dispose(slot); return; }
          current.current = slot;
          playingRef.current = true;
          setTrack(candidate);
          setPlaying(true);
          void api.played(candidate.id);
          void prefetch();
          break;
        }
        await new Promise(resolve => window.setTimeout(resolve, 2200));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to start player");
    } finally {
      if (ticket === startTicket.current) setLoading(false);
    }
  }, [loading]);

  const pause = useCallback(() => {
    ++startTicket.current;
    current.current?.audio.pause();
    fading.current?.audio.pause();
    void context.current?.suspend();
    playingRef.current = false;
    setPlaying(false);
    setLoading(false);
  }, []);

  const skip = useCallback(() => { void advance(0.9); }, []);

  const selectMood = useCallback(async (mood: string) => {
    if (pending.current) { dispose(pending.current); pending.current = null; }
    try {
      await api.settings({ mood });
      await refresh();
      void prefetch();
    } catch {
      setError("Could not change the mood");
    }
  }, [refresh]);

  const setGenerationEnabled = useCallback(async (enabled: boolean) => {
    try {
      await api.settings({ generation_enabled: enabled });
      await refresh();
    } catch {
      setError("Could not update generation settings");
    }
  }, [refresh]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (!playingRef.current || !current.current) return;
      if (!pending.current && !transitioning.current) void prefetch();
      const slot = current.current;
      const duration = slot.audio.duration || slot.track.duration;
      if (pending.current && !transitioning.current &&
          duration - slot.audio.currentTime <= 5) {
        void advance(4);
      }
    }, 750);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => () => {
    ++startTicket.current;
    if (fadeTimeout.current !== null) clearTimeout(fadeTimeout.current);
    dispose(current.current);
    dispose(pending.current);
    dispose(fading.current);
    void context.current?.close();
  }, []);

  const favorite = useCallback(async () => {
    if (!track) return;
    const value = !track.favorite;
    await api.feedback(track.id, { favorite: value });
    setTrack({ ...track, favorite: value });
  }, [track]);

  return {
    status, track, playing, loading, error, volume, setVolume,
    start, pause, skip, selectMood, setGenerationEnabled, favorite, refresh,
  };
}
