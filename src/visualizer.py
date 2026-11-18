"""
Visualizer für den Lollipop-CSP-Solver.

Zeigt in einem eigenen Fenster (Tkinter-Canvas) zuerst die Startkonfiguration
des Gitters und danach den kompletten "Denkpfad" der Backtracking-Suche:
jede versuchte Belegung, jeden Konflikt und jeden Backtracking-Schritt.

Wichtig: csp_builder.py und csp_solver.py werden NICHT verändert.
  - Aus csp_solver.py werden nur die Funktionsdefinitionen geladen
    (der Code auf Modulebene, der sofort ein Puzzle löst, wird übersprungen).
  - Die Suche wird aufgezeichnet, indem gitter.consistent() für dieses eine
    Gitter-Objekt durch einen Wrapper ersetzt wird, der jeden Aufruf
    protokolliert und dann die Original-Methode aufruft.

Start (im Ordner, in dem auch csp_builder.py und csp_solver.py liegen):
    python visualizer.py
    python visualizer.py --max-steps 500000 --time-limit 60
    python visualizer.py --no-gui          # nur Konsolenausgabe

Bedienung im Fenster:
    Leertaste  Abspielen / Pause
    ← / →      einen Schritt zurück / vor
    Pos1 / Ende   zum Start / zum letzten Schritt
    B          zum nächsten Backtracking-Schritt springen
"""

import argparse
import ast
import math
import sys
import time
from pathlib import Path

# Ordner dieser Datei in den Suchpfad aufnehmen, damit csp_builder gefunden wird
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import csp_builder as csp  # noqa: E402


# --------------------------------------------------------------------------
# 1) Solver-Funktionen laden, ohne den Code auf Modulebene auszuführen
# --------------------------------------------------------------------------
def load_solver_functions(path: Path = HERE / "csp_solver.py") -> dict:
    """Lädt nur Imports, Funktionen und Klassen aus csp_solver.py.

    Ein normales `import csp_solver` würde sofort das Puzzle auf Modulebene
    lösen und ausgeben. Deshalb wird die Datei per ast eingelesen und nur die
    Definitionen werden ausgeführt.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    keep = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)
    tree.body = [node for node in tree.body if isinstance(node, keep)]
    namespace = {"__name__": "csp_solver_visual", "__file__": str(path)}
    exec(compile(tree, str(path), "exec"), namespace)
    return namespace


# --------------------------------------------------------------------------
# 2) Aufzeichnung der Suche
# --------------------------------------------------------------------------
class SearchAborted(Exception):
    """Wird geworfen, wenn Schritt- oder Zeitlimit erreicht ist."""


class SearchRecorder:
    """Ersetzt gitter.consistent durch einen protokollierenden Wrapper.

    Jeder Aufruf von consistent(variable, assignment) entspricht genau einem
    Belegungsversuch der Backtracking-Suche. Gespeichert wird pro Versuch nur
    (Index der Variable in der Belegungsreihenfolge, Wert, konsistent?).
    Daraus lässt sich jeder Zwischenzustand der Suche rekonstruieren, weil die
    Suche die Variablen in fester Reihenfolge belegt.
    """

    def __init__(self, gitter, order, max_steps, time_limit):
        self.gitter = gitter
        self.index_of = {var: k for k, var in enumerate(order)}
        self.max_steps = max_steps
        self.time_limit = time_limit
        self.events = []          # Liste von (k, Domain, ok)
        self._original = gitter.consistent
        self._start = None

    def __enter__(self):
        self._start = time.perf_counter()
        original = self._original

        def recording_consistent(variable, assignment):
            ok = original(variable, assignment)
            self.events.append((self.index_of[variable], assignment[variable], ok))
            if len(self.events) >= self.max_steps:
                raise SearchAborted("Schrittlimit erreicht")
            # Zeit nur ab und zu prüfen (perf_counter ist nicht ganz gratis)
            if len(self.events) % 256 == 0 and time.perf_counter() - self._start > self.time_limit:
                raise SearchAborted("Zeitlimit erreicht")
            return ok

        # Nur dieses Objekt wird gepatcht, die Klasse bleibt unverändert
        self.gitter.consistent = recording_consistent
        return self

    def __exit__(self, *exc):
        # Original-Methode wiederherstellen
        self.gitter.__dict__.pop("consistent", None)
        return False


# --------------------------------------------------------------------------
# 3) Trace: rekonstruiert jeden Zwischenzustand der Suche
# --------------------------------------------------------------------------
class Trace:
    CHECKPOINT_EVERY = 500

    def __init__(self, gitter, start_assignment, order, events, status, duration):
        self.size = gitter.size
        self.given = dict(start_assignment)
        self.order = order                # Belegungsreihenfolge der freien Zellen
        self.n = len(order)
        self.events = events
        self.status = status              # "gelöst" / "keine Lösung" / "abgebrochen: ..."
        self.duration = duration

        # Pro Schritt: kumulierte Belegungen, Backtracks, Backtracks direkt davor
        self.backtracks_cum = [0] * (len(events) + 1)
        self.backtrack_before = [0] * len(events)
        self.ok_cum = [0] * (len(events) + 1)
        prev_k = -1
        bt = 0
        okc = 0
        for i, (k, _value, ok) in enumerate(events):
            # Springt die Suche auf eine frühere (oder dieselbe nach einem Fehlschlag
            # in tieferer Ebene) Variable zurück, wurden (prev_k - k) Ebenen verworfen.
            jump = prev_k - k if prev_k > k else 0
            self.backtrack_before[i] = jump
            bt += jump
            if ok:
                okc += 1
            self.backtracks_cum[i + 1] = bt
            self.ok_cum[i + 1] = okc
            prev_k = k

        # Checkpoints für schnelles Springen auf der Zeitleiste
        self.checkpoints = []
        values = [None] * self.n
        top = -1                          # höchster belegter Index
        for i in range(len(events) + 1):
            if i % self.CHECKPOINT_EVERY == 0:
                self.checkpoints.append((tuple(values), top))
            if i < len(events):
                top = self._apply(values, top, events[i])

        self._cache_step = 0
        self._cache_values = [None] * self.n
        self._cache_top = -1

    @staticmethod
    def _apply(values, top, event):
        k, value, _ok = event
        for j in range(k + 1, top + 1):   # alles hinter k ist (wieder) unbelegt
            values[j] = None
        values[k] = value
        return k

    def state(self, step):
        """Belegung der freien Zellen nach `step` Ereignissen (0 = Start)."""
        if step < self._cache_step or step - self._cache_step > self.CHECKPOINT_EVERY:
            cp = step // self.CHECKPOINT_EVERY
            vals, top = self.checkpoints[cp]
            self._cache_values = list(vals)
            self._cache_top = top
            self._cache_step = cp * self.CHECKPOINT_EVERY
        while self._cache_step < step:
            self._cache_top = self._apply(self._cache_values, self._cache_top,
                                          self.events[self._cache_step])
            self._cache_step += 1
        return self._cache_values

    def assignment_at(self, step):
        """Vollständiges Dict {Zelle: Domain} inkl. Vorgaben."""
        result = dict(self.given)
        for k, value in enumerate(self.state(step)):
            if value is not None:
                result[self.order[k]] = value
        return result


def record_search(max_steps, time_limit, size=10):
    """Baut das Puzzle wie csp_solver.py auf und zeichnet backtracking_search auf."""
    solver = load_solver_functions()
    gitter = csp.LollipopGitter(size)
    start = gitter.build_puzzle(csp.Difficulty.HARD)
    # Gleiche Reihenfolge wie in backtracking_search: erste unbelegte Variable zuerst
    order = [v for v in gitter.variables if v not in start]

    t0 = time.perf_counter()
    with SearchRecorder(gitter, order, max_steps, time_limit) as rec:
        try:
            result = solver["forward_checking_search"](gitter, start)
            status = "gelöst" if result is not None else "keine Lösung"
        except SearchAborted as e:
            result = None
            status = f"abgebrochen ({e})"
    duration = time.perf_counter() - t0
    return gitter, Trace(gitter, start, order, rec.events, status, duration), result


# --------------------------------------------------------------------------
# 4) GUI
# --------------------------------------------------------------------------
COLORS = {
    "bg": "#1b1d24",
    "panel": "#242731",
    "panel2": "#2d313d",
    "text": "#e6e8ee",
    "muted": "#8b91a3",
    "grid": "#3a3f4d",
    "unassigned": "#23262f",
    "assigned": "#2f3442",
    "given_bg": "#3d3a2a",
    "given": "#f2c14e",
    "piece": "#7cc4ff",
    "ok": "#4cd585",
    "bad": "#ff5c6c",
    "bt": "#ffa94d",
}

NAMES = {
    csp.Domain.EMPTY: "EMPTY",
    csp.Domain.HORIZONTAL_LINE: "HORIZONTAL",
    csp.Domain.VERTICAL_LINE: "VERTICAL",
    csp.Domain.CIRCLE: "CIRCLE",
}


def run_gui(trace: Trace):
    import tkinter as tk
    from tkinter import ttk

    class App:
        CELL = 56
        MARGIN = 34

        def __init__(self, root):
            self.root = root
            self.trace = trace
            self.total = len(trace.events)
            self.step = 0
            self.playing = False
            self._updating_scale = False

            root.title("Lollipop – Backtracking-Visualisierung")
            root.configure(bg=COLORS["bg"])

            style = ttk.Style(root)
            try:
                style.theme_use("clam")
            except tk.TclError:
                pass
            style.configure("TScale", background=COLORS["bg"])

            board_px = self.MARGIN + trace.size * self.CELL + 12

            # ---- Spielfeld-Canvas ----
            self.canvas = tk.Canvas(root, width=board_px, height=board_px,
                                    bg=COLORS["bg"], highlightthickness=0)
            self.canvas.grid(row=0, column=0, padx=(16, 8), pady=16, sticky="n")

            # ---- Seitenleiste ----
            side = tk.Frame(root, bg=COLORS["panel"], padx=14, pady=12)
            side.grid(row=0, column=1, padx=(8, 16), pady=16, sticky="ns")

            def label(parent, text="", size=10, color="text", bold=False, **kw):
                font = ("Helvetica", size, "bold" if bold else "normal")
                return tk.Label(parent, text=text, font=font, fg=COLORS[color],
                                bg=parent["bg"], anchor="w", justify="left", **kw)

            label(side, "Backtracking-Suche", 15, bold=True).pack(fill="x")
            label(side, f"Ergebnis: {trace.status}  ·  {trace.duration:.2f} s  ·  "
                        f"{self.total:,} Versuche".replace(",", "."),
                  9, "muted").pack(fill="x", pady=(0, 10))

            self.lbl_step = label(side, "", 12, bold=True)
            self.lbl_step.pack(fill="x")
            self.lbl_action = label(side, "", 11, wraplength=300)
            self.lbl_action.pack(fill="x", pady=(4, 0))
            self.lbl_bt = label(side, "", 10, "bt")
            self.lbl_bt.pack(fill="x", pady=(0, 8))

            # Kennzahlen
            stats = tk.Frame(side, bg=COLORS["panel2"], padx=10, pady=8)
            stats.pack(fill="x", pady=(0, 8))
            self.stat_labels = {}
            for key, title in [("assign", "Variablenbelegungen"),
                               ("ok", "davon konsistent"),
                               ("bt", "Backtracking-Schritte"),
                               ("depth", "Suchtiefe")]:
                row = tk.Frame(stats, bg=COLORS["panel2"])
                row.pack(fill="x")
                label(row, title, 10, "muted").pack(side="left")
                self.stat_labels[key] = label(row, "", 10, bold=True)
                self.stat_labels[key].pack(side="right")

            # Balken für die Suchtiefe
            self.depth_bar = tk.Canvas(side, height=10, width=300, bg=COLORS["panel2"],
                                       highlightthickness=0)
            self.depth_bar.pack(fill="x", pady=(0, 10))

            # Steuerung
            ctrl = tk.Frame(side, bg=COLORS["panel"])
            ctrl.pack(fill="x", pady=(0, 6))
            btn_cfg = dict(bg=COLORS["panel2"], fg=COLORS["text"], relief="flat",
                           activebackground=COLORS["grid"], activeforeground=COLORS["text"],
                           font=("Helvetica", 12), width=3, bd=0, padx=4, pady=4)
            tk.Button(ctrl, text="⏮", command=lambda: self.goto(0), **btn_cfg).pack(side="left", padx=2)
            tk.Button(ctrl, text="◀", command=lambda: self.goto(self.step - 1), **btn_cfg).pack(side="left", padx=2)
            self.btn_play = tk.Button(ctrl, text="▶", command=self.toggle_play, **btn_cfg)
            self.btn_play.pack(side="left", padx=2)
            tk.Button(ctrl, text="▶|", command=lambda: self.goto(self.step + 1), **btn_cfg).pack(side="left", padx=2)
            tk.Button(ctrl, text="⏭", command=lambda: self.goto(self.total), **btn_cfg).pack(side="left", padx=2)
            tk.Button(ctrl, text="↶ BT", command=self.next_backtrack,
                      **{**btn_cfg, "width": 5}).pack(side="left", padx=2)

            # Geschwindigkeit (logarithmisch: 1 … 5000 Schritte/s)
            speed_row = tk.Frame(side, bg=COLORS["panel"])
            speed_row.pack(fill="x", pady=(4, 8))
            label(speed_row, "Tempo", 10, "muted").pack(side="left")
            self.speed_var = tk.DoubleVar(value=35)
            ttk.Scale(speed_row, from_=0, to=100, variable=self.speed_var,
                      command=lambda _v: self.update_speed_label()).pack(side="left", fill="x",
                                                                         expand=True, padx=6)
            self.lbl_speed = label(speed_row, "", 9, "muted", width=10)
            self.lbl_speed.pack(side="right")
            self.update_speed_label()

            # Protokoll der letzten Schritte
            label(side, "Verlauf", 10, "muted").pack(fill="x")
            self.log = tk.Text(side, height=14, width=40, bg=COLORS["panel2"],
                               fg=COLORS["text"], relief="flat", font=("Courier", 9),
                               padx=6, pady=4, state="disabled", cursor="arrow")
            self.log.pack(fill="both", expand=True)
            self.log.tag_configure("ok", foreground=COLORS["ok"])
            self.log.tag_configure("bad", foreground=COLORS["bad"])
            self.log.tag_configure("bt", foreground=COLORS["bt"])
            self.log.tag_configure("cur", background=COLORS["grid"])

            # Legende
            legend = tk.Frame(side, bg=COLORS["panel"])
            legend.pack(fill="x", pady=(8, 0))
            for color, text in [("given", "Vorgabe"), ("piece", "von Suche belegt"),
                                ("ok", "aktuell: konsistent"), ("bad", "aktuell: Konflikt")]:
                row = tk.Frame(legend, bg=COLORS["panel"])
                row.pack(fill="x")
                tk.Label(row, text="■", fg=COLORS[color], bg=COLORS["panel"]).pack(side="left")
                label(row, text, 9, "muted").pack(side="left")

            # ---- Zeitleiste ----
            bottom = tk.Frame(root, bg=COLORS["bg"])
            bottom.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 14))
            root.columnconfigure(0, weight=1)
            label(bottom, "Zeitleiste", 9, "muted").pack(side="left")
            self.scale_var = tk.DoubleVar(value=0)
            ttk.Scale(bottom, from_=0, to=max(self.total, 1), variable=self.scale_var,
                      command=self.on_scale).pack(side="left", fill="x", expand=True, padx=8)

            # Tastatur
            root.bind("<space>", lambda e: self.toggle_play())
            root.bind("<Left>", lambda e: self.goto(self.step - 1))
            root.bind("<Right>", lambda e: self.goto(self.step + 1))
            root.bind("<Home>", lambda e: self.goto(0))
            root.bind("<End>", lambda e: self.goto(self.total))
            root.bind("b", lambda e: self.next_backtrack())

            self.render()

        # ---------- Steuerung ----------
        def speed(self):
            """Schritte pro Sekunde aus der Reglerstellung."""
            return 10 ** (self.speed_var.get() / 100 * math.log10(5000))

        def update_speed_label(self):
            self.lbl_speed.config(text=f"{self.speed():.0f} /s")

        def goto(self, step):
            self.step = max(0, min(self.total, int(step)))
            self.render()

        def on_scale(self, value):
            if not self._updating_scale:
                self.goto(float(value))

        def next_backtrack(self):
            for i in range(self.step, self.total):
                if self.trace.backtrack_before[i]:
                    self.goto(i + 1)
                    return
            self.goto(self.total)

        def toggle_play(self):
            if self.step >= self.total:
                self.step = 0
            self.playing = not self.playing
            self.btn_play.config(text="⏸" if self.playing else "▶")
            if self.playing:
                self._last_tick = time.perf_counter()
                self._carry = 0.0
                self.tick()

        def tick(self):
            if not self.playing:
                return
            now = time.perf_counter()
            self._carry += (now - self._last_tick) * self.speed()
            self._last_tick = now
            n = int(self._carry)
            if n:
                self._carry -= n
                self.goto(self.step + n)
            if self.step >= self.total:
                self.playing = False
                self.btn_play.config(text="▶")
                return
            self.root.after(16, self.tick)

        # ---------- Zeichnen ----------
        def cell_box(self, r, c):
            x0 = self.MARGIN + c * self.CELL
            y0 = self.MARGIN + r * self.CELL
            return x0, y0, x0 + self.CELL, y0 + self.CELL

        def draw_piece(self, r, c, value, color):
            x0, y0, x1, y1 = self.cell_box(r, c)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            w = self.CELL * 0.16
            cv = self.canvas
            if value == csp.Domain.CIRCLE:
                rad = self.CELL * 0.30
                cv.create_oval(cx - rad, cy - rad, cx + rad, cy + rad,
                               fill=color, outline="", tags="dyn")
            elif value == csp.Domain.HORIZONTAL_LINE:
                cv.create_line(x0 + 1, cy, x1 - 1, cy, fill=color, width=w,
                               capstyle="butt", tags="dyn")
            elif value == csp.Domain.VERTICAL_LINE:
                cv.create_line(cx, y0 + 1, cx, y1 - 1, fill=color, width=w,
                               capstyle="butt", tags="dyn")
            elif value == csp.Domain.EMPTY:
                cv.create_text(cx, cy, text="·", fill=COLORS["muted"],
                               font=("Helvetica", 14), tags="dyn")

        def render(self):
            t = self.trace
            cv = self.canvas
            cv.delete("all")
            assignment = t.assignment_at(self.step)
            current = t.events[self.step - 1] if self.step > 0 else None
            cur_cell = t.order[current[0]] if current else None

            # Koordinaten
            for i in range(t.size):
                x0, y0, x1, y1 = self.cell_box(0, i)
                cv.create_text((x0 + x1) / 2, self.MARGIN - 14, text=str(i),
                               fill=COLORS["muted"], font=("Helvetica", 9))
                x0, y0, x1, y1 = self.cell_box(i, 0)
                cv.create_text(self.MARGIN - 14, (y0 + y1) / 2, text=str(i),
                               fill=COLORS["muted"], font=("Helvetica", 9))

            # Zellen
            for r in range(t.size):
                for c in range(t.size):
                    cell = (r, c)
                    if cell in t.given:
                        bg = COLORS["given_bg"]
                    elif cell in assignment:
                        bg = COLORS["assigned"]
                    else:
                        bg = COLORS["unassigned"]
                    cv.create_rectangle(*self.cell_box(r, c), fill=bg,
                                        outline=COLORS["grid"], width=1)

            # Belegungen
            for cell, value in assignment.items():
                r, c = cell
                if not (0 <= r < t.size and 0 <= c < t.size):
                    continue
                if cell in t.given:
                    color = COLORS["given"]
                elif cell == cur_cell:
                    color = COLORS["ok"] if current[2] else COLORS["bad"]
                else:
                    color = COLORS["piece"]
                self.draw_piece(r, c, value, color)

            # Rahmen um die aktuelle Zelle
            if cur_cell:
                x0, y0, x1, y1 = self.cell_box(*cur_cell)
                cv.create_rectangle(x0 + 2, y0 + 2, x1 - 2, y1 - 2, width=3,
                                    outline=COLORS["ok"] if current[2] else COLORS["bad"])

            # Infotexte
            self.lbl_step.config(text=f"Schritt {self.step:,} / {self.total:,}".replace(",", "."))
            if current is None:
                self.lbl_action.config(text="Startkonfiguration – Vorgaben in Gelb.\n"
                                            "▶ drücken, um die Suche abzuspielen.",
                                       fg=COLORS["text"])
                self.lbl_bt.config(text="")
            else:
                k, value, ok = current
                r, c = cur_cell
                text = f"Zelle ({r},{c}) ← {NAMES[value]}   " + ("✓ konsistent" if ok else "✗ Konflikt")
                self.lbl_action.config(text=text, fg=COLORS["ok"] if ok else COLORS["bad"])
                jump = t.backtrack_before[self.step - 1]
                self.lbl_bt.config(text=f"↶ Backtracking: {jump} Ebene(n) zurück" if jump else "")
                if self.step == self.total and t.status == "gelöst":
                    self.lbl_action.config(text=text + "\n★ Lösung gefunden!")

            depth = (current[0] + 1) if current else 0
            tries = self.step
            self.stat_labels["assign"].config(text=f"{tries:,}".replace(",", "."))
            self.stat_labels["ok"].config(text=f"{t.ok_cum[self.step]:,}".replace(",", "."))
            self.stat_labels["bt"].config(text=f"{t.backtracks_cum[self.step]:,}".replace(",", "."))
            self.stat_labels["depth"].config(text=f"{depth} / {t.n}")

            self.depth_bar.update_idletasks()
            bw = self.depth_bar.winfo_width() or 300
            self.depth_bar.delete("all")
            if t.n:
                self.depth_bar.create_rectangle(0, 0, bw * depth / t.n, 10,
                                                fill=COLORS["piece"], outline="")

            self.render_log()

            self._updating_scale = True
            self.scale_var.set(self.step)
            self._updating_scale = False

        def render_log(self):
            t = self.trace
            log = self.log
            log.config(state="normal")
            log.delete("1.0", "end")
            lo = max(0, self.step - 12)
            hi = min(self.total, self.step + 2)
            if lo == 0 and self.step == 0:
                log.insert("end", "      Start\n", "cur")
            for i in range(lo, hi):
                k, value, ok = t.events[i]
                r, c = t.order[k]
                if t.backtrack_before[i]:
                    log.insert("end", f"      ↶ {t.backtrack_before[i]} Ebene(n) zurück\n", "bt")
                line = f"{i + 1:>6} ({r},{c}) {NAMES[value]:<10} {'✓' if ok else '✗'}\n"
                tags = ("ok" if ok else "bad",) + (("cur",) if i + 1 == self.step else ())
                log.insert("end", line, tags)
            log.config(state="disabled")
            log.see("end")

    root = tk.Tk()
    App(root)
    root.mainloop()


# --------------------------------------------------------------------------
# 5) Einstieg
# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Visualisiert die Backtracking-Suche des Lollipop-Solvers.")
    parser.add_argument("--max-steps", type=int, default=300_000,
                        help="maximale Anzahl aufgezeichneter Belegungsversuche (Standard: 300000)")
    parser.add_argument("--time-limit", type=float, default=60.0,
                        help="Zeitlimit der Suche in Sekunden (Standard: 60)")
    parser.add_argument("--no-gui", action="store_true", help="nur Konsolenausgabe, kein Fenster")
    args = parser.parse_args()

    print("Zeichne Backtracking-Suche auf …")
    gitter, trace, result = record_search(args.max_steps, args.time_limit)

    print("\nStartkonfiguration:")
    print(gitter.toString(trace.given))
    print(f"Ergebnis:              {trace.status}")
    print(f"Dauer der Suche:       {trace.duration:.3f} s")
    print(f"Variablenbelegungen:   {len(trace.events)}")
    print(f"Backtracking-Schritte: {trace.backtracks_cum[-1]}")
    if result is not None:
        print("\nLösung:")
        print(gitter.toString(result))
    else:
        print("\nLetzter Zustand der Suche:")
        print(gitter.toString(trace.assignment_at(len(trace.events))))

    if not args.no_gui:
        run_gui(trace)


if __name__ == "__main__":
    main()