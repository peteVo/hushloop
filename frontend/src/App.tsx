import { useEffect, useState } from "react";
import {
  ArrowUpRight, AudioLines, BookOpen, Check, Clock3, CloudRain,
  Code2, Coffee, Disc3, Heart, Headphones, History, Leaf,
  Pause, Play, Settings2, SkipForward, SlidersHorizontal,
  Sparkles, Volume2, VolumeX, Waves
} from "lucide-react";
import { api, type Track } from "./api";
import { useRadio } from "./useRadio";
import "./styles.css";

const MOODS = [
  { id: "rainy", title: "Rainy Café", subtitle: "Warm & nostalgic", icon: Coffee },
  { id: "coding", title: "Midnight Coding", subtitle: "Quiet momentum", icon: Code2 },
  { id: "jazzhop", title: "Jazzhop", subtitle: "Easygoing rhythms", icon: Disc3 },
  { id: "ambient", title: "Ambient Focus", subtitle: "Drift into flow", icon: Leaf },
];
const FOCUS_LENGTHS = [25, 45, 60];

function formatTime(seconds: number) {
  return Math.floor(seconds / 60).toString().padStart(2, "0") +
    ":" + Math.floor(seconds % 60).toString().padStart(2, "0");
}

export default function App() {
  const radio = useRadio();
  const [panel, setPanel] = useState<"library" | "settings">("library");
  const [history, setHistory] = useState<Track[]>([]);
  const [timerSeconds, setTimerSeconds] = useState(25 * 60);
  const [timerRunning, setTimerRunning] = useState(false);
  const [focusLength, setFocusLength] = useState(25);

  useEffect(() => {
    const fetchHistory = () => { void api.history().then(setHistory).catch(() => {}); };
    fetchHistory();
    const poll = window.setInterval(fetchHistory, 5000);
    return () => clearInterval(poll);
  }, []);

  useEffect(() => {
    if (!timerRunning) return;
    const timer = window.setInterval(() => {
      setTimerSeconds(current => {
        if (current <= 1) { setTimerRunning(false); return 0; }
        return current - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [timerRunning]);

  const settings = radio.status?.settings;
  const mood = MOODS.find(item => item.id === settings?.mood) ?? MOODS[0];
  const busy = radio.status?.generating ?? false;
  const queuedMinutes = Math.round((radio.status?.buffered_seconds ?? 0) / 60);
  const isMock = radio.status?.provider.toLowerCase().includes("demo");
  const resetTimer = (minutes: number) => {
    setTimerRunning(false);
    setFocusLength(minutes);
    setTimerSeconds(minutes * 60);
  };

  return (
    <div className={"app mood-" + mood.id}>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-symbol"><AudioLines size={20} strokeWidth={2.2} /></div>
          <div><div className="brand-name">hushloop<span className="brand-dot">.</span></div><div className="brand-small">YOUR PRIVATE RADIO</div></div>
        </div>
        <div className="side-label">YOUR SPACE</div>
        <button className={"nav-button " + (panel === "library" ? "chosen" : "")} onClick={() => setPanel("library")}>
          <Headphones size={17} /> Now listening <span className="nav-key">01</span>
        </button>
        <button className={"nav-button " + (panel === "settings" ? "chosen" : "")} onClick={() => setPanel("settings")}>
          <Settings2 size={17} /> Radio settings <span className="nav-key">02</span>
        </button>
        <div className="side-label moods-label">SELECT AN ATMOSPHERE</div>
        <div className="moods">
          {MOODS.map(item => {
            const Icon = item.icon;
            return (
              <button key={item.id}
                className={"mood-button " + (settings?.mood === item.id ? "active" : "")}
                onClick={() => void radio.selectMood(item.id)}>
                <span className="mood-icon"><Icon size={19} strokeWidth={1.8} /></span>
                <span className="mood-copy"><strong>{item.title}</strong><small>{item.subtitle}</small></span>
                {settings?.mood === item.id && <span className="mood-active-dot" />}
              </button>
            );
          })}
        </div>
        <div className="sidebar-bottom">
          <div className="sidebar-art">
            <CloudRain size={19} /><span>A softer kind of focus.</span>
          </div>
          <div className="sidebar-note">Thoughtfully generated.<br />Made to stay out of your way.</div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="breadcrumb">YOUR RADIO <span>/</span> {panel === "settings" ? "SETTINGS" : "LISTENING ROOM"}</div>
          <div className="status-line"><span className={"live-dot " + (busy ? "busy" : "")} />{busy ? "Composing in the background" : (radio.status?.settings.generation_enabled ? "Ready to create" : "Generation paused")}</div>
        </header>

        {panel === "library" ? (
          <>
            <section className="scene">
              <div className="scene-glow" />
              <div className="scene-window">
                <div className="scene-moon" />
                <div className="scene-rain rain-one" />
                <div className="scene-rain rain-two" />
                <div className="scene-sill" />
              </div>
              <div className="scene-stars" />
              <div className="scene-text">
                <div className="eyebrow"><span className="eyebrow-line" /> AN OPEN-ENDED LISTENING EXPERIENCE</div>
                <h1>Find your<br /><em>quiet place.</em></h1>
                <p>Uninterrupted instrumentals, made for the moments when everything else can wait.</p>
                <div className="scene-meta"><span><Waves size={15} /> {mood.title}</span><span className="meta-divider" /><span>INFINITE RADIO</span></div>
              </div>
              <div className="scene-number">NO. 01 / ∞</div>
            </section>

            <section className="player">
              <div className="player-cover">
                <div className={"record " + (radio.playing ? "spinning" : "")}>
                  <div className="record-ridge ridge-one" />
                  <div className="record-ridge ridge-two" />
                  <div className="record-label"><span>h.</span><span className="center-hole" /></div>
                </div>
              </div>
              <div className="playing-info">
                <div className="tiny-heading">ON AIR <span className="dot-separator">•</span> {radio.track ? "GENERATED FOR YOU" : "AWAITING YOUR FIRST TRACK"}</div>
                <h2>{radio.track?.title ?? "A little room to breathe"}</h2>
                <div className="track-sub">{radio.track ? radio.track.bpm + " BPM · Instrumental · " + mood.title : "Select an atmosphere and press play"}</div>
                <div className="track-actions">
                  <button title={radio.playing ? "Pause" : "Play"} className="main-play"
                    onClick={() => radio.playing || radio.loading ? radio.pause() : void radio.start()}>
                    {radio.loading ? <span className="loader" /> : radio.playing ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" />}
                  </button>
                  <button className="icon-btn" title="Next track" onClick={radio.skip} disabled={!radio.track}><SkipForward size={20} /></button>
                  <button className={"icon-btn " + (radio.track?.favorite ? "is-favorite" : "")}
                    title="Favorite track" disabled={!radio.track} onClick={() => void radio.favorite()}>
                    <Heart size={19} fill={radio.track?.favorite ? "currentColor" : "none"} />
                  </button>
                  <div className="volume"><VolumeX size={15} /><input type="range" min="0" max="1" step="0.01" aria-label="Volume"
                    value={radio.volume} onChange={event => radio.setVolume(Number(event.target.value))} /><Volume2 size={16} /></div>
                </div>
                {(radio.loading || radio.error) && <p className={"player-alert " + (radio.error ? "error" : "")}>
                  {radio.error ?? "Preparing your first track. The initial generation can take a few minutes."}
                </p>}
              </div>
            </section>
            <section className="below">
              <div className="section-heading"><div><div className="eyebrow small">THE LITTLE THINGS</div><h3>Keep the moment going.</h3></div></div>
              <div className="utility-grid">
                <article className="utility-card">
                  <div className="card-head"><span className="utility-icon"><Clock3 size={18} /></span><span className="card-kicker">FOCUS TIMER</span></div>
                  <div className="timer-time">{formatTime(timerSeconds)}</div>
                  <div className="timer-actions">
                    <div className="pills">{FOCUS_LENGTHS.map(minutes => <button key={minutes}
                      className={focusLength === minutes ? "selected" : ""} onClick={() => resetTimer(minutes)}>{minutes}m</button>)}</div>
                    <button className="timer-toggle" onClick={() => timerSeconds === 0 ? resetTimer(focusLength) : setTimerRunning(!timerRunning)}>
                      {timerSeconds === 0 ? "Reset" : timerRunning ? "Pause" : "Start"} <ArrowUpRight size={15} />
                    </button>
                  </div>
                </article>
                <article className="utility-card buffer-card">
                  <div className="card-head"><span className="utility-icon"><Sparkles size={18} /></span><span className="card-kicker">YOUR SOUND RESERVE</span></div>
                  <div className="buffer-line"><strong>{queuedMinutes}<span> min</span></strong><span className="buffer-sub">already waiting for you</span></div>
                  <div className="buffer-meter"><span style={{ width: Math.min(100, (radio.status?.buffered_seconds ?? 0) / ((settings?.buffer_minutes || 5) * 60) * 100) + "%" }} /></div>
                  <div className="buffer-foot"><span>{radio.status?.queued_tracks ?? 0} new tracks buffered</span><span>{busy ? "Composing…" : "Ready"}</span></div>
                </article>
              </div>
              {history.length > 0 && <div className="history"><div className="history-title"><History size={17} /> Your recent soundscapes</div>
                {history.slice(0, 5).map(item => <div className="history-row" key={item.id}>
                  <div className="history-icon"><AudioLines size={16} /></div><span>{item.title}</span><small>{Math.round(item.duration / 60)} min</small>{item.favorite && <Heart size={13} fill="currentColor" />}</div>)}
              </div>}
              <div className="fineprint">MADE FOR YOUR DESK, NOT THE CLOUD. <span>HUSHLOOP 0.1</span></div>
            </section>
          </>
        ) : (
          <section className="settings-panel">
            <div className="eyebrow"><span className="eyebrow-line" /> THE ENGINE ROOM</div>
            <h1>Make it<br /><em>your own.</em></h1>
            <p className="settings-intro">Your music stays on this computer. Adjust how much music gets generated, then let Hushloop handle the rest.</p>
            <div className="settings-box">
              <div className="setting-row"><div><h3><SlidersHorizontal size={18} /> Automatic generation</h3><p>Fill the queue while this is on. Turning it off never stops currently playing music.</p></div><button className={"switch " + (settings?.generation_enabled ? "on" : "")}
                role="switch" aria-checked={!!settings?.generation_enabled} onClick={() => void radio.setGenerationEnabled(!settings?.generation_enabled)}><span /></button></div>
              <div className="setting-row"><div><h3><Clock3 size={18} /> Reserve size</h3><p>Minimum buffered minutes before Hushloop generates more.</p></div><select aria-label="Reserve size" value={settings?.buffer_minutes ?? 5}
                onChange={event => void api.settings({buffer_minutes: Number(event.target.value)}).then(() => radio.refresh())}>
                  {[2, 5, 10, 15, 20, 30].map(mins => <option value={mins} key={mins}>{mins} min</option>)}
                </select></div>
              <div className="setting-row"><div><h3><Disc3 size={18} /> Track length</h3><p>How long each new composition should last.</p></div><select aria-label="Track length" value={settings?.track_seconds ?? 90}
                onChange={event => void api.settings({track_seconds: Number(event.target.value)}).then(() => radio.refresh())}>
                  {[30, 60, 90, 120, 180, 300].map(seconds => <option value={seconds} key={seconds}>{seconds} sec</option>)}
                </select></div>
              <div className="setting-row"><div><h3><BookOpen size={18} /> Audio cache limit</h3><p>Older played tracks are removed automatically when safe.</p></div><select aria-label="Cache size" value={settings?.cache_limit_mb ?? 2048}
                onChange={event => void api.settings({cache_limit_mb: Number(event.target.value)}).then(() => radio.refresh())}>
                  {[512, 1024, 2048, 4096, 8192].map(mb => <option value={mb} key={mb}>{mb} MB</option>)}
                </select></div>
            </div>
            <div className="runtime-note"><span><Check size={16} /> LOCAL-FIRST</span>
              <span>Engine: {radio.status?.provider ?? "Offline"}</span><span>{isMock ? "DEMO AUDIO ONLY" : "ACE-STEP GENERATION"}</span></div>
            {radio.status?.last_error && <p className="settings-error">{radio.status.last_error}</p>}
          </section>
        )}
      </main>
    </div>
  );
}
