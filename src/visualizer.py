"""
Visualizer für den Lollipop-CSP-Solver.

Zeigt in einem eigenen Fenster (Tkinter-Canvas) zuerst die Startkonfiguration
des Gitters und danach den kompletten "Denkpfad" einer Suche:
jede Belegung, jeden verworfenen Wert, jeden Backtracking-Schritt und
(bei Forward Checking / AC-3) die verbleibenden Domänen jeder Zelle.

Wichtig: csp_builder.py und csp_solver.py werden NICHT verändert.
  - Aus csp_solver.py werden nur Imports, Funktionen und Klassen geladen
    (der Code auf Modulebene, der sofort ein Puzzle löst, wird übersprungen).
  - Alle Funktionen aus csp_solver.py werden in einen protokollierenden
    Wrapper gepackt. Ein rekursiver Aufruf einer Suchfunktion = ein Knoten
    im Suchbaum, ein fehlgeschlagener Rückgabewert (None/False) = Backtracking.
  - gitter.consistent() wird nur für dieses eine Gitter-Objekt ersetzt, damit
    auch verworfene Werte sichtbar werden.
  Dadurch funktioniert der Visualizer mit jeder Suchfunktion, egal ob sie
  Kopien der Belegung macht oder sie in-place ändert, welche
  Belegungsreihenfolge (Heuristik) sie nutzt und ob sie Domänen beschneidet.

Welche Suche visualisiert wird:
  - Standard ist die Variable `search_variant` unten.
  - Überschreibbar per Kommandozeile:  --search backtracking_search
  - Im Fenster per Auswahlliste + "Suche starten".
  - Unterstützt jede Funktion in csp_solver.py mit "search" im Namen, z.B.
    backtracking_search(gitter, assignment) oder
    complete_search(gitter, assignment, domains) – Parameter mit "domain" im
    Namen bekommen automatisch dict_copy(gitter.domains).

Gittergröße:
  - Wird automatisch aus den Vorgaben in build_puzzle() erkannt
    (größte Zeile/Spalte + 1, z.B. (24, 17) → 25×25).
  - Erzwingen mit --size 15 oder im Fenster "auto" abwählen.

Ablauf:
  - Das Fenster öffnet sofort, die Suche läuft im Hintergrund und wird live
    angezeigt ("Abbrechen" beendet sie). Danach kann man jeden Schritt abspielen.
  - Zeitlimit: standardmäßig keins (TIME_LIMIT unten). Mit --time-limit 60 wird
    nach 60 s echter Uhrzeit (inkl. Aufzeichnung) abgebrochen.
  - "Abbrechen" im Fenster beendet die Suche jederzeit; das bis dahin
    Aufgezeichnete kann man trotzdem abspielen.

Start (im Ordner, in dem auch csp_builder.py und csp_solver.py liegen):
    python visualizer.py
    python visualizer.py --search backtracking_search --time-limit 60
    python visualizer.py --list                 # verfügbare Suchfunktionen
    python visualizer.py --no-gui               # nur Konsolenausgabe

Bedienung im Fenster:
    Leertaste      Abspielen / Pause
    ← / →          einen Schritt zurück / vor
    Pos1 / Ende    zum Start / zum letzten Schritt
    B              zum nächsten Backtracking-Schritt springen
    D              Domänen ein-/ausblenden
"""

import argparse
import ast
import inspect
import math
import sys
import threading
import time
import traceback
from pathlib import Path

# ==========================================================================
# Welche Suchfunktion aus csp_solver.py standardmäßig visualisiert wird.
# Muss der Name einer Funktion in csp_solver.py sein.
# ==========================================================================
search_variant = "forward_checking_search_with_heuristic"

# Zeitlimit der Suche in Sekunden. None = kein Zeitlimit.
TIME_LIMIT = None
#TIME_LIMIT = 60

# Maximale Anzahl aufgezeichneter Schritte (schützt den Arbeitsspeicher bei sehr
# langen Suchen). None = unbegrenzt.
MAX_STEPS = 2_000_000

# Gittergröße für make_puzzle(size, difficulty) aus csp_solver.py.
# None = automatisch aus den Vorgaben in build_puzzle() erkennen.
DEFAULT_SIZE = None
DEFAULT_DIFFICULTY = "HARD"

# Ordner dieser Datei in den Suchpfad aufnehmen, damit csp_builder gefunden wird
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import csp_builder as csp  # noqa: E402

# Tiefe Rekursion bei großen Gittern (jede Ebene = mehrere Python-Frames)
sys.setrecursionlimit(100_000)
try:
    threading.stack_size(256 * 1024 * 1024)
except (ValueError, RuntimeError):
    pass


# --------------------------------------------------------------------------
# 1) Solver laden, ohne den Code auf Modulebene auszuführen
# --------------------------------------------------------------------------
def load_solver_functions(path: Path = HERE / "csp_solver.py") -> dict:
    """Lädt nur Imports, Funktionen und Klassen aus csp_solver.py.

    Ein normales `import csp_solver` würde sofort das Puzzle auf Modulebene
    lösen und ausgeben. Deshalb wird die Datei per ast eingelesen und nur die
    Definitionen werden ausgeführt. Jeder Aufruf liefert einen frischen
    Namensraum (wichtig, weil die Funktionen darin für die Aufzeichnung
    ersetzt werden).
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    keep = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)
    tree.body = [node for node in tree.body if isinstance(node, keep)]
    namespace = {"__name__": "csp_solver_visual", "__file__": str(path)}
    exec(compile(tree, str(path), "exec"), namespace)
    return namespace


def detect_size(path: Path = HERE / "csp_solver.py", fallback: int = 10) -> int:
    """Liest die Gittergröße aus dem Code auf Modulebene von csp_solver.py,
    z.B. `gitter = csp.LollipopGitter(15)`. Wird nichts gefunden: fallback."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return fallback
    size = None
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.ClassDef)):
            continue
        for node in ast.walk(stmt):
            if (isinstance(node, ast.Call) and node.args
                    and getattr(node.func, "attr", getattr(node.func, "id", None)) == "LollipopGitter"
                    and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, int)):
                size = node.args[0].value
    return size or fallback


def detect_puzzle_size(namespace: dict, difficulty) -> int:
    """Erkennt die Gittergröße aus dem Puzzle selbst.

    build_puzzle() trägt die Vorgaben mit festen Koordinaten ein, z.B. (24, 17).
    Die größte vorkommende Zeile/Spalte + 1 ist die Gittergröße. Das Gitter wird
    dazu einmal probeweise gebaut (mit der Größe, die unten in csp_solver.py
    steht, z.B. LollipopGitter(15)).
    Steht in csp_solver.py eine Größe, die höchstens 1 größer ist als die
    erkannte (z.B. weil in der letzten Zeile und Spalte keine Vorgabe liegt),
    wird diese genommen.
    """
    declared = detect_size(fallback=0)
    try:
        _gitter, givens = build_puzzle(namespace, max(declared, 1), difficulty)
    except Exception:            # noqa: BLE001 – dann eben die angegebene Größe
        return declared or 10
    if not givens:
        return declared or 10
    needed = max(max(r, c) for r, c in givens) + 1
    if declared and needed <= declared <= needed + 1:
        return declared
    return needed


def call_search(namespace: dict, func, gitter, assignment):
    """Ruft die Suchfunktion mit (gitter, assignment) auf und füllt weitere
    Pflicht-Parameter, deren Name 'domain' enthält, mit einer Kopie von
    gitter.domains (über dict_copy aus csp_solver.py, falls vorhanden) –
    genau wie z.B. `forward_checking_search(gitter, assignment, dict_copy(gitter.domains))`."""
    params = list(inspect.signature(func).parameters.values())
    extra = []
    for p in params[2:]:
        if p.default is not inspect.Parameter.empty or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            break
        if "domain" in p.name.lower():
            if "dict_copy" in namespace:
                extra.append(namespace["dict_copy"](gitter.domains))
            else:
                extra.append({cell: list(values) for cell, values in gitter.domains.items()})
        else:
            raise TypeError(f"Weiß nicht, was ich für den Parameter '{p.name}' von "
                            f"{func.__name__}() übergeben soll.")
    return func(gitter, assignment, *extra)


def available_searches(namespace: dict) -> list:
    """Alle Funktionen aus csp_solver.py, deren Name 'search' enthält."""
    return [name for name, obj in namespace.items()
            if inspect.isfunction(obj) and obj.__globals__ is namespace and "search" in name]


def build_puzzle(namespace: dict, size: int, difficulty):
    """Baut das Puzzle möglichst genauso wie csp_solver.py (make_puzzle)."""
    if "make_puzzle" in namespace:
        return namespace["make_puzzle"](size, difficulty)
    gitter = csp.LollipopGitter(size)
    return gitter, gitter.build_puzzle(difficulty)


# --------------------------------------------------------------------------
# 2) Aufzeichnung der Suche
# --------------------------------------------------------------------------
class SearchAborted(Exception):
    """Wird geworfen, wenn Schritt- oder Zeitlimit erreicht ist."""


# Ereignis-Arten
START, ASSIGN, REJECT, PRUNED, BACKTRACK, SOLUTION = (
    "start", "assign", "reject", "pruned", "backtrack", "solution")


def is_assignment(obj) -> bool:
    """dict {Zelle: Domain} (auch leer)."""
    if not isinstance(obj, dict):
        return False
    if not obj:
        return True
    return isinstance(next(iter(obj.values())), csp.Domain)


def is_domains(obj) -> bool:
    """dict {Zelle: Liste/Menge von Domain-Werten}."""
    if not isinstance(obj, dict) or not obj:
        return False
    key, value = next(iter(obj.items()))
    return isinstance(key, tuple) and isinstance(value, (list, set, frozenset, tuple))


def domain_snapshot(domains: dict) -> dict:
    # Tupel statt frozenset: Enum-Werte zu hashen ist in Python langsam,
    # Tupel lassen sich ohne Hashing vergleichen (Identitätsvergleich der Elemente).
    return {cell: tuple(values) for cell, values in domains.items()}


_MISSING = object()


def dict_diff(old: dict, new: dict) -> tuple:
    """Änderungen von old nach new als ((key, neuer Wert oder None), ...).
    Vergleicht nur Werte (kein Hashing der Enum-Werte → schnell auch bei 25×25)."""
    out = [(key, value) for key, value in new.items()
           if (prev := old.get(key, _MISSING)) is not value and prev != value]
    if not old.keys() <= new.keys():          # Einträge, die weggefallen sind
        out.extend((key, None) for key in old.keys() - new.keys())
    return tuple(out)


class _Frame:
    """Ein aktiver Aufruf einer (gewrappten) Solver-Funktion."""
    __slots__ = ("name", "is_node", "a_obj", "d_obj", "a_snap", "d_snap")

    def __init__(self, name, a_obj, d_obj):
        self.name = name
        self.is_node = False
        self.a_obj = a_obj
        self.d_obj = d_obj
        self.a_snap = dict(a_obj)     # Belegung beim Betreten dieses Knotens
        self.d_snap = None            # Domänen beim Betreten (nur für Knoten)


class SearchRecorder:
    """Zeichnet eine beliebige Suchfunktion aus csp_solver.py auf.

    Ereignisse (je ein Tupel):
        (art, fokus_zellen, overlay_wert, belegungs_diff, domänen_diff, tiefe)
    Aus den Diffs kann der Trace jeden Zwischenzustand rekonstruieren.
    """

    def __init__(self, namespace, search_name, gitter, start, max_steps, time_limit):
        self.ns = namespace
        self.search_name = search_name
        self.gitter = gitter
        self.max_steps = max_steps if max_steps else float("inf")
        self.time_limit = time_limit if time_limit else None   # None/0 = kein Zeitlimit

        cells = set(gitter.variables)
        self.init_a = {c: v for c, v in start.items() if c in cells}
        self.outside = len(start) - len(self.init_a)   # Vorgaben, die nicht ins Gitter passen
        self.init_d = domain_snapshot(gitter.domains)
        self.prev_a = dict(self.init_a)
        self.prev_d = dict(self.init_d)

        self.events = []
        self.stack = []               # aktive Aufrufe (_Frame)
        self.recursive = set()        # Funktionen, die sich selbst rekursiv aufrufen
        self.node_depth = 0
        self.started = False
        self.pending = None           # (Zelle, Wert): hat consistent() bestanden, noch offen
        self.consistent_calls = 0
        self.domain_checks = 0
        self.overhead = 0.0
        self._t0 = None
        self.cancelled = False        # wird vom Fenster gesetzt ("Abbrechen")
        self._dom_src = None          # zuletzt fotografiertes Domänen-Objekt …
        self._dom_fp = None           # … dessen Gesamtlänge …
        self._dom_last = None         # … und der Schnappschuss davon
        self.finished = False
        # laufende Zähler (für die Live-Anzeige während der Suche)
        self.n_assign = self.n_reject = self.n_backtrack = 0

    # ---------- Ereignisse ----------
    def _dom_snap(self, domains):
        """Schnappschuss der Domänen. Ist es dasselbe Objekt wie beim letzten Mal und hat
        sich die Gesamtzahl der Werte nicht geändert (z.B. backtracking_search, das
        gitter.domains nie ändert), wird der alte Schnappschuss wiederverwendet."""
        fp = sum(map(len, domains.values()))
        if domains is self._dom_src and fp == self._dom_fp:
            return self._dom_last
        self._dom_src, self._dom_fp = domains, fp   # Referenz halten → id bleibt eindeutig
        self._dom_last = domain_snapshot(domains)
        return self._dom_last

    def _flush_pending(self):
        """Ein Wert hat consistent() bestanden, führte aber zu keinem Kindknoten
        (z.B. Forward Checking hat eine Nachbardomäne geleert) → als verworfen zeigen."""
        if self.pending is not None:
            var, value = self.pending
            self.pending = None
            self._record(PRUNED, (var,), value, None, None)

    def _record(self, kind, focus, overlay, new_a, new_d, a_diff=None):
        if a_diff is None:
            a_diff = dict_diff(self.prev_a, new_a) if new_a is not None else ()
        d_diff = dict_diff(self.prev_d, new_d) if new_d is not None and new_d is not self.prev_d else ()
        if new_a is not None:
            self.prev_a = new_a
        if new_d is not None:
            self.prev_d = new_d
        if focus is None:   # Fokus = Zellen, deren Belegung sich geändert hat
            focus = tuple(cell for cell, _ in a_diff)
        self.events.append((kind, focus, overlay, a_diff, d_diff, self.node_depth))
        if kind == ASSIGN:
            self.n_assign += 1
        elif kind in (REJECT, PRUNED):
            self.n_reject += 1
        elif kind == BACKTRACK:
            self.n_backtrack += 1
        if len(self.events) >= self.max_steps:
            raise SearchAborted("Schrittlimit erreicht")
        if len(self.events) % 64 == 0:
            self._check_limits()

    def _check_limits(self):
        if self.cancelled:
            raise SearchAborted("durch Benutzer")
        # Zeitlimit = echte Uhrzeit inkl. Aufzeichnung, damit "60 s" auch 60 s sind
        if self.time_limit is not None and time.perf_counter() - self._t0 > self.time_limit:
            raise SearchAborted(f"Zeitlimit {self.time_limit:g} s erreicht")

    def _enter(self, frame, check_pending=True):
        """Ein neuer Knoten im Suchbaum (= eine konsistente Belegung)."""
        frame.is_node = True
        self.node_depth += 1
        frame.d_snap = self._dom_snap(frame.d_obj)
        if check_pending and self.pending is not None:
            var, value = self.pending
            if frame.a_snap.get(var) == value:
                self.pending = None       # der geprüfte Wert wurde tatsächlich belegt
            else:
                self._flush_pending()
        a_diff = dict_diff(self.prev_a, frame.a_snap)
        if not self.started:
            self.started = True
            self._record(START, None, None, frame.a_snap, frame.d_snap, a_diff)
        elif any(value is not None for _, value in a_diff):
            self._record(ASSIGN, None, None, frame.a_snap, frame.d_snap, a_diff)
        # sonst: Knoten ohne neue Belegung (z.B. Hilfsfunktion) → kein eigener Schritt

    def _backtrack(self):
        """Knoten ist gescheitert: zurück zum Zustand des Elternknotens."""
        parent = next((f for f in reversed(self.stack) if f.is_node), None)
        self._flush_pending()
        if parent is None:
            return            # Wurzel gescheitert → Suche endet ohne Lösung
        # Belegung wie beim Betreten des Elternknotens; Domänen so, wie der Elternknoten
        # sie jetzt benutzt (z.B. nach seiner eigenen Constraint-Propagierung)
        self._record(BACKTRACK, None, None, parent.a_snap, self._dom_snap(parent.d_obj))

    # ---------- Wrapper ----------
    def _find_args(self, args, kwargs):
        a_obj = d_obj = g = None
        for obj in list(args) + list(kwargs.values()):
            if a_obj is None and is_assignment(obj):
                a_obj = obj
            elif d_obj is None and is_domains(obj):
                d_obj = obj
            elif g is None and hasattr(obj, "variables") and hasattr(obj, "domains"):
                g = obj
        if d_obj is None:
            d_obj = (g or self.gitter).domains
        return a_obj, d_obj

    def _wrap(self, name, func):
        recorder = self

        def wrapper(*args, **kwargs):
            t = time.perf_counter()
            a_obj, d_obj = recorder._find_args(args, kwargs)
            if a_obj is None:                 # keine Belegung als Argument → kein Suchknoten
                recorder.overhead += time.perf_counter() - t
                return func(*args, **kwargs)

            frame = _Frame(name, a_obj, d_obj)
            # Ruft sich eine Funktion selbst auf, ist sie eine rekursive Suchfunktion.
            # Frühere (äußere) Aufrufe derselben Funktion werden nachträglich zu Knoten.
            if any(f.name == name for f in recorder.stack):
                recorder.recursive.add(name)
                for f in recorder.stack:
                    if f.name == name and not f.is_node:
                        recorder._enter(f, check_pending=False)
            if name == recorder.search_name or name in recorder.recursive:
                recorder._enter(frame)
            recorder.stack.append(frame)
            recorder.overhead += time.perf_counter() - t

            try:
                result = func(*args, **kwargs)
            finally:
                recorder.stack.pop()
                if frame.is_node:
                    recorder.node_depth -= 1

            if frame.is_node and (result is None or result is False):
                t = time.perf_counter()
                recorder._backtrack()
                recorder.overhead += time.perf_counter() - t
            return result

        wrapper.__wrapped__ = func
        return wrapper

    def _install(self):
        # Alle Funktionen aus csp_solver.py wrappen (rekursive Aufrufe gehen über
        # den globalen Namen und landen damit ebenfalls im Wrapper).
        for name, obj in list(self.ns.items()):
            if inspect.isfunction(obj) and obj.__globals__ is self.ns:
                self.ns[name] = self._wrap(name, obj)

        original = self.gitter.consistent

        def recording_consistent(variable, assignment):
            ok = original(variable, assignment)
            t = time.perf_counter()
            self.consistent_calls += 1
            if self.consistent_calls % 512 == 0 and self._t0 is not None:
                self._check_limits()   # auch prüfen, wenn lange kein Schritt entsteht
            # Nur Aufrufe direkt aus einer Suchfunktion sind Belegungsversuche.
            # Aufrufe über gitter.possible() / forward_check() usw. sind Prüfungen
            # beim Beschneiden von Domänen; deren Ergebnis sieht man an den Domänen.
            caller = sys._getframe(1).f_code.co_name
            direct = caller == self.search_name or caller in self.recursive
            if not direct:
                self.domain_checks += 1
            if direct and self.node_depth > 0:
                value = assignment.get(variable)
                same_var = self.pending is not None and self.pending[0] == variable
                if same_var:
                    # nächster Wert derselben Variable → der vorige hat nicht geklappt
                    self._flush_pending()
                if not ok:
                    # Verworfener Wert: Basiszustand bleibt, Wert wird nur rot eingeblendet
                    self._record(REJECT, (variable,), value, None, None)
                elif self.pending is None:
                    # Wert besteht den Test; ob er wirklich belegt wird, zeigt der nächste
                    # Knoten. (Weitere ok-Aufrufe für andere Zellen = Prüfungen von Nachbarn.)
                    self.pending = (variable, value)
            self.overhead += time.perf_counter() - t
            return ok

        self.gitter.consistent = recording_consistent

    def run(self):
        """Führt die Suche aus. Rückgabe: (Ergebnis, Status, Dauer in s)."""
        self._install()
        func = self.ns[self.search_name]
        self._t0 = time.perf_counter()
        result = None
        try:
            result = call_search(self.ns, func, self.gitter, dict(self.init_a))
            if is_assignment(result) and result:  # noqa: SIM114
                status = "gelöst"
            elif result is None or result is False:
                status = "keine Lösung"
            else:
                status = "beendet"
        except SearchAborted as e:
            status = f"abgebrochen ({e})"
        except RecursionError:
            status = "Fehler: Rekursion zu tief"
        except Exception as e:   # Fehler im Solver: anzeigen, was bis dahin passiert ist
            traceback.print_exc()
            status = f"Fehler: {type(e).__name__}: {e}"
        finally:
            self.gitter.__dict__.pop("consistent", None)
        self.wall_time = time.perf_counter() - self._t0
        duration = max(0.0, self.wall_time - self.overhead)

        if self.outside:
            status += f" – Achtung: {self.outside} Vorgaben liegen außerhalb des Gitters"
        if status.startswith("gelöst"):
            cells = set(self.gitter.variables)
            self.max_steps = float("inf")
            self._record(SOLUTION, None, None,
                         {c: v for c, v in result.items() if c in cells}, None)
        self.finished = True
        return result, status, duration


# --------------------------------------------------------------------------
# 3) Trace: rekonstruiert jeden Zwischenzustand der Suche
# --------------------------------------------------------------------------
class Trace:
    CHECKPOINT_EVERY = 400

    def __init__(self, gitter, recorder, status, duration, search_name):
        self.rows = max(r for r, _ in gitter.variables) + 1
        self.cols = max(c for _, c in gitter.variables) + 1
        self.size = max(self.rows, self.cols)
        self.given = dict(recorder.init_a)
        self.init_d = dict(recorder.init_d)
        self.n_free = len(gitter.variables) - len(self.given)
        self.events = recorder.events
        self.status = status
        self.duration = duration
        self.search_name = search_name
        self.consistent_calls = recorder.consistent_calls
        self.domain_checks = recorder.domain_checks
        self.wall_time = recorder.wall_time

        # Kumulierte Kennzahlen pro Schritt
        n = len(self.events)
        self.assigns_cum = [0] * (n + 1)
        self.rejects_cum = [0] * (n + 1)
        self.backtracks_cum = [0] * (n + 1)
        a = r = b = 0
        self.domains_change = False
        for i, ev in enumerate(self.events):
            kind = ev[0]
            if kind == ASSIGN:
                a += 1
            elif kind in (REJECT, PRUNED):
                r += 1
            elif kind == BACKTRACK:
                b += 1
            if ev[4]:
                self.domains_change = True
            self.assigns_cum[i + 1] = a
            self.rejects_cum[i + 1] = r
            self.backtracks_cum[i + 1] = b

        # Checkpoints für schnelles Springen auf der Zeitleiste
        self.checkpoints = []
        cur_a, cur_d = dict(self.given), dict(self.init_d)
        for i in range(n + 1):
            if i % self.CHECKPOINT_EVERY == 0:
                self.checkpoints.append((dict(cur_a), dict(cur_d)))
            if i < n:
                self._apply(cur_a, cur_d, self.events[i])

        self._cache_step = 0
        self._cache_a = dict(self.given)
        self._cache_d = dict(self.init_d)

    @staticmethod
    def _apply(cur_a, cur_d, event):
        for cell, value in event[3]:
            if value is None:
                cur_a.pop(cell, None)
            else:
                cur_a[cell] = value
        for cell, values in event[4]:
            if values is None:
                cur_d.pop(cell, None)
            else:
                cur_d[cell] = values

    def state(self, step):
        """(Belegung, Domänen) nach `step` Ereignissen (0 = Start)."""
        if step < self._cache_step or step - self._cache_step > self.CHECKPOINT_EVERY:
            cp = step // self.CHECKPOINT_EVERY
            a, d = self.checkpoints[cp]
            self._cache_a, self._cache_d = dict(a), dict(d)
            self._cache_step = cp * self.CHECKPOINT_EVERY
        while self._cache_step < step:
            self._apply(self._cache_a, self._cache_d, self.events[self._cache_step])
            self._cache_step += 1
        return self._cache_a, self._cache_d

    def assignment_at(self, step):
        return dict(self.state(step)[0])


def record_search(search_name, size, difficulty, max_steps, time_limit, on_recorder=None):
    """Baut das Puzzle, zeichnet die gewählte Suche auf und liefert (gitter, Trace, Ergebnis).

    size:        Gittergröße oder None = automatisch aus den Vorgaben von build_puzzle()
    on_recorder: optionaler Callback, bekommt den Recorder sofort (für die Live-Anzeige).
    """
    namespace = load_solver_functions()
    if search_name not in namespace or not callable(namespace[search_name]):
        raise SystemExit(f"Suchfunktion '{search_name}' gibt es in csp_solver.py nicht. "
                         f"Verfügbar: {', '.join(available_searches(namespace))}")
    if size is None:
        size = detect_puzzle_size(namespace, difficulty)
    gitter, start = build_puzzle(namespace, size, difficulty)
    recorder = SearchRecorder(namespace, search_name, gitter, start, max_steps, time_limit)
    if on_recorder:
        on_recorder(recorder)
    result, status, duration = recorder.run()
    return gitter, Trace(gitter, recorder, status, duration, search_name), result


class LiveView:
    """Wie ein Trace, zeigt aber den aktuellen Zustand einer noch laufenden Suche."""

    def __init__(self, recorder, search_name):
        g = recorder.gitter
        self.recorder = recorder
        self.rows = max(r for r, _ in g.variables) + 1
        self.cols = max(c for _, c in g.variables) + 1
        self.size = max(self.rows, self.cols)
        self.given = dict(recorder.init_a)
        self.n_free = len(g.variables) - len(self.given)
        self.search_name = search_name
        self.events = []
        self.assigns_cum = self.rejects_cum = self.backtracks_cum = [0]
        self.domains_change = True

    def state(self, _step):
        # prev_a / prev_d werden vom Such-Thread nur ersetzt, nie verändert → sicher lesbar
        return self.recorder.prev_a, self.recorder.prev_d


def print_summary(trace):
    print("\nStartkonfiguration:")
    print(format_grid(trace.rows, trace.cols, trace.given))
    print(f"\nSuche:                 {trace.search_name}")
    print(f"Ergebnis:              {trace.status}")
    print(f"Dauer der Suche:       ca. {trace.duration:.3f} s "
          f"(gesamt mit Aufzeichnung {trace.wall_time:.1f} s)")
    print(f"Variablenbelegungen:   {trace.assigns_cum[-1]}")
    print(f"verworfene Werte:      {trace.rejects_cum[-1]}")
    print(f"Backtracking-Schritte: {trace.backtracks_cum[-1]}")
    title = "Lösung" if trace.status.startswith("gelöst") else "Letzter Zustand der Suche"
    print(f"\n{title}:")
    print(format_grid(trace.rows, trace.cols, trace.assignment_at(len(trace.events))))


def limit_text(time_limit) -> str:
    return f"Zeitlimit {time_limit:g} s" if time_limit else "kein Zeitlimit"


def run_in_thread(func):
    """Führt func in einem Thread mit großem Stack aus (tiefe Rekursion)."""
    box = {}

    def target():
        try:
            box["value"] = func()
        except BaseException as e:   # noqa: BLE001 – wird im Aufrufer weitergereicht
            box["error"] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    return thread, box


def format_grid(rows, cols, assignment) -> str:
    """Konsolenausgabe des Gitters, auch für mehrstellige Zeilen-/Spaltennummern."""
    symbols = {csp.Domain.EMPTY: " ", csp.Domain.HORIZONTAL_LINE: "━",
               csp.Domain.VERTICAL_LINE: "┃", csp.Domain.CIRCLE: "o"}
    w = len(str(max(rows, cols) - 1))
    head = " " * (w + 1) + "".join(f"{c:>{w}} " for c in range(cols))
    sep = " " * (w + 1) + ("─" * w + "┼") * cols
    lines = [head, sep]
    for r in range(rows):
        cells = "".join(f"{symbols.get(assignment.get((r, c)), '·'):>{w}}│" for c in range(cols))
        lines.append(f"{r:>{w}}│" + cells)
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 4) GUI
# --------------------------------------------------------------------------
COLORS = {
    "bg": "#1b1d24",
    "panel": "#242731",
    "panel2": "#2d313d",
    "text": "#e6e8ee",
    "muted": "#8b91a3",
    "mark": "#5f667a",
    "grid": "#3a3f4d",
    "unassigned": "#23262f",
    "assigned": "#2f3442",
    "wipeout": "#4a2329",
    "given_bg": "#3d3a2a",
    "given": "#f2c14e",
    "piece": "#7cc4ff",
    "ok": "#4cd585",
    "bad": "#ff5c6c",
    "bt": "#ffa94d",
    "solution": "#f2c14e",
}

NAMES = {
    csp.Domain.EMPTY: "EMPTY",
    csp.Domain.HORIZONTAL_LINE: "HORIZONTAL",
    csp.Domain.VERTICAL_LINE: "VERTICAL",
    csp.Domain.CIRCLE: "CIRCLE",
}
SHORT = {
    csp.Domain.EMPTY: "leer",
    csp.Domain.HORIZONTAL_LINE: "━",
    csp.Domain.VERTICAL_LINE: "┃",
    csp.Domain.CIRCLE: "o",
}
# Position der Domänen-Markierungen (2×2) in einer unbelegten Zelle
MARK_POS = {
    csp.Domain.EMPTY: (0, 0),
    csp.Domain.HORIZONTAL_LINE: (1, 0),
    csp.Domain.VERTICAL_LINE: (0, 1),
    csp.Domain.CIRCLE: (1, 1),
}


def fmt(n) -> str:
    return f"{n:,}".replace(",", ".")


def cells_text(cells, limit=4) -> str:
    text = ", ".join(f"({r},{c})" for r, c in list(cells)[:limit])
    return text + (" …" if len(cells) > limit else "")


def describe(trace: Trace, i: int):
    """Kurzbeschreibung von Ereignis i → (Text, Farb-Tag)."""
    kind, focus, overlay, a_diff, d_diff, _depth = trace.events[i]
    dom = f"  · {len(d_diff)} Domänen geändert" if d_diff else ""
    if kind == START:
        return "Start der Suche" + dom, "muted"
    if kind == ASSIGN:
        parts = [f"({r},{c})←{SHORT[v]}" for (r, c), v in a_diff if v is not None][:3]
        return " ".join(parts) + " ✓" + dom, "ok"
    if kind == REJECT:
        r, c = focus[0]
        return f"({r},{c}) {SHORT.get(overlay, '?')} ✗ Konflikt, verworfen", "bad"
    if kind == PRUNED:
        r, c = focus[0]
        return f"({r},{c}) {SHORT.get(overlay, '?')} ✗ verworfen (Folgeprüfung)", "bad"
    if kind == BACKTRACK:
        return f"↶ zurück, gelöscht: {cells_text(focus, 2)}" + dom, "bt"
    return "★ Lösung gefunden", "solution"


def run_gui(args, searches):
    import tkinter as tk
    from tkinter import ttk

    class App:
        def __init__(self, root):
            self.root = root
            self.step = 0
            self.playing = False
            self._updating_scale = False
            self.sigs = {}                       # zuletzt gezeichneter Zustand pro Zelle
            self.trace = None
            self.total = 0
            self.recorder = None                 # Recorder der gerade laufenden Suche
            self.cell = 40
            self.margin = 30

            root.title("Lollipop – Such-Visualisierung")
            root.configure(bg=COLORS["bg"])

            # Fenstergröße an den Bildschirm anpassen (ca. 92 % × 88 %, zentriert)
            screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
            win_w = int(min(screen_w * 0.92, 1700))
            win_h = int(min(screen_h * 0.88, 1200))
            root.geometry(f"{win_w}x{win_h}+{(screen_w - win_w) // 2}+{max(0, (screen_h - win_h) // 3)}")
            root.minsize(min(820, screen_w), min(520, screen_h))
            compact = screen_h < 850           # kleiner Bildschirm (z.B. Laptop)
            self._redraw_job = None

            style = ttk.Style(root)
            try:
                style.theme_use("clam")
            except tk.TclError:
                pass
            style.configure("TScale", background=COLORS["bg"])
            style.configure("TCombobox", fieldbackground=COLORS["panel2"],
                            background=COLORS["panel2"], foreground=COLORS["text"])

            # ---- Spielfeld-Canvas (passt sich an Fenster- und Gittergröße an) ----
            # Startgröße des Canvas: was neben der Seitenleiste (~390 px) übrig bleibt
            board_w = max(250, win_w - 390 - 40)
            board_h = max(250, win_h - 80)
            self.canvas = tk.Canvas(root, width=board_w, height=board_h,
                                    bg=COLORS["bg"], highlightthickness=0)
            self.canvas.grid(row=0, column=0, padx=(16, 8), pady=16, sticky="nsew")
            root.columnconfigure(0, weight=1)
            root.rowconfigure(0, weight=1)
            # Beim Ziehen am Fenster nicht bei jedem Pixel neu zeichnen
            self.canvas.bind("<Configure>", lambda e: self.schedule_redraw())

            # ---- Seitenleiste ----
            side = tk.Frame(root, bg=COLORS["panel"], padx=14, pady=12)
            side.grid(row=0, column=1, padx=(8, 16), pady=16, sticky="ns")

            def label(parent, text="", size=10, color="text", bold=False, **kw):
                font = ("Helvetica", size, "bold" if bold else "normal")
                return tk.Label(parent, text=text, font=font, fg=COLORS[color],
                                bg=parent["bg"], anchor="w", justify="left", **kw)
            self._label = label

            label(side, "Such-Visualisierung", 15, bold=True).pack(fill="x")

            # Auswahl der Suchfunktion
            pick = tk.Frame(side, bg=COLORS["panel"])
            pick.pack(fill="x", pady=(6, 2))
            self.search_var = tk.StringVar(value=args.search)
            ttk.Combobox(pick, textvariable=self.search_var, values=searches,
                         state="readonly", width=30).pack(side="left", fill="x", expand=True)
            pick2 = tk.Frame(side, bg=COLORS["panel"])
            pick2.pack(fill="x", pady=(2, 2))
            label(pick2, "Größe", 10, "muted").pack(side="left")
            self.size_var = tk.IntVar(value=args.size or 0)
            self.auto_size = tk.BooleanVar(value=args.size is None)
            self.size_box = tk.Spinbox(pick2, from_=2, to=100, textvariable=self.size_var, width=4,
                       bg=COLORS["panel2"], fg=COLORS["text"], buttonbackground=COLORS["panel2"],
                       insertbackground=COLORS["text"], relief="flat")
            self.size_box.pack(side="left", padx=(4, 2))
            tk.Checkbutton(pick2, text="auto", variable=self.auto_size, command=self.update_size_box,
                           bg=COLORS["panel"], fg=COLORS["text"], selectcolor=COLORS["panel2"],
                           activebackground=COLORS["panel"], activeforeground=COLORS["text"],
                           highlightthickness=0).pack(side="left", padx=(0, 8))
            self.update_size_box()
            label(pick2, "Schwierigkeit", 10, "muted").pack(side="left")
            self.diff_var = tk.StringVar(value=args.difficulty.name)
            ttk.Combobox(pick2, textvariable=self.diff_var, state="readonly", width=8,
                         values=[d.name for d in csp.Difficulty]).pack(side="left", padx=(4, 0))
            self.btn_run = tk.Button(pick2, text="Suche starten", command=self.rerun,
                                     bg=COLORS["panel2"], fg=COLORS["text"], relief="flat",
                                     activebackground=COLORS["grid"], bd=0, padx=8, pady=3)
            self.btn_run.pack(side="right")


            self.lbl_info = label(side, "", 9, "muted", wraplength=330)
            self.lbl_info.pack(fill="x", pady=(2, 10))

            self.lbl_step = label(side, "", 12, bold=True)
            self.lbl_step.pack(fill="x")
            self.lbl_action = label(side, "", 11, wraplength=330)
            self.lbl_action.pack(fill="x", pady=(4, 8))

            # Kennzahlen
            stats = tk.Frame(side, bg=COLORS["panel2"], padx=10, pady=8)
            stats.pack(fill="x", pady=(0, 8))
            self.stat_labels = {}
            for key, title in [("assign", "Variablenbelegungen"),
                               ("reject", "verworfene Werte"),
                               ("bt", "Backtracking-Schritte"),
                               ("depth", "Suchtiefe")]:
                row = tk.Frame(stats, bg=COLORS["panel2"])
                row.pack(fill="x")
                label(row, title, 10, "muted").pack(side="left")
                self.stat_labels[key] = label(row, "", 10, bold=True)
                self.stat_labels[key].pack(side="right")

            self.depth_bar = tk.Canvas(side, height=10, width=330, bg=COLORS["panel2"],
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
            speed_row.pack(fill="x", pady=(4, 4))
            label(speed_row, "Tempo", 10, "muted").pack(side="left")
            self.speed_var = tk.DoubleVar(value=35)
            ttk.Scale(speed_row, from_=0, to=100, variable=self.speed_var,
                      command=lambda _v: self.update_speed_label()).pack(side="left", fill="x",
                                                                         expand=True, padx=6)
            self.lbl_speed = label(speed_row, "", 9, "muted", width=8)
            self.lbl_speed.pack(side="right")
            self.update_speed_label()

            # Optionen
            self.show_domains = tk.BooleanVar(value=True)
            tk.Checkbutton(side, text="Domänen (Restwerte) anzeigen", variable=self.show_domains,
                           command=self.full_redraw, bg=COLORS["panel"], fg=COLORS["text"],
                           selectcolor=COLORS["panel2"], activebackground=COLORS["panel"],
                           activeforeground=COLORS["text"], anchor="w",
                           highlightthickness=0).pack(fill="x", pady=(0, 6))

            # Verlauf
            label(side, "Verlauf", 10, "muted").pack(fill="x")
            self.log = tk.Text(side, height=6 if compact else 13, width=44, bg=COLORS["panel2"],
                               fg=COLORS["text"], relief="flat", font=("Courier", 9),
                               padx=6, pady=4, state="disabled", cursor="arrow", wrap="none")
            self.log.pack(fill="both", expand=True)
            self.log_lines = 5 if compact else 11
            for tag in ("ok", "bad", "bt", "muted", "solution"):
                self.log.tag_configure(tag, foreground=COLORS[tag])
            self.log.tag_configure("cur", background=COLORS["grid"])

            # Legende
            legend = tk.Frame(side, bg=COLORS["panel"])
            legend.pack(fill="x", pady=(8, 0))
            entries = [("given", "Vorgabe"), ("piece", "von Suche belegt"),
                       ("ok", "gerade belegt"), ("bad", "verworfener Wert"),
                       ("bt", "zurückgenommen"), ("wipeout", "leere Domäne")]
            for i, (color, text) in enumerate(entries):
                row = tk.Frame(legend, bg=COLORS["panel"])
                row.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 12))
                tk.Label(row, text="■", fg=COLORS[color], bg=COLORS["panel"]).pack(side="left")
                label(row, text, 9, "muted").pack(side="left")

            # ---- Zeitleiste ----
            bottom = tk.Frame(root, bg=COLORS["bg"])
            bottom.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 14))
            label(bottom, "Zeitleiste", 9, "muted").pack(side="left")
            self.scale_var = tk.DoubleVar(value=0)
            self.scale = ttk.Scale(bottom, from_=0, to=1, variable=self.scale_var,
                                   command=self.on_scale)
            self.scale.pack(side="left", fill="x", expand=True, padx=8)

            # Tastatur
            root.bind("<space>", lambda e: self.toggle_play())
            root.bind("<Left>", lambda e: self.goto(self.step - 1))
            root.bind("<Right>", lambda e: self.goto(self.step + 1))
            root.bind("<Home>", lambda e: self.goto(0))
            root.bind("<End>", lambda e: self.goto(self.total))
            root.bind("b", lambda e: self.next_backtrack())
            root.bind("d", lambda e: (self.show_domains.set(not self.show_domains.get()),
                                      self.full_redraw()))

            # Suche sofort starten, sobald das Fenster steht
            self.root.after(50, self.rerun)

        # ---------- Größe ----------
        def update_size_box(self):
            # "auto": Größe wird bei jedem Start aus build_puzzle() erkannt
            self.size_box.config(state="disabled" if self.auto_size.get() else "normal")

        # ---------- Trace wechseln / neu aufzeichnen ----------
        def set_trace(self, new_trace):
            self.trace = new_trace
            self.show_domains.set(new_trace.domains_change)
            self.total = len(new_trace.events)
            self.step = 0
            self.scale.configure(to=max(self.total, 1))
            t = new_trace
            self.lbl_info.config(
                text=f"{t.search_name}  ·  {t.rows}×{t.cols}  ·  Ergebnis: {t.status}\n"
                     f"Dauer ca. {t.duration:.2f} s  ·  {fmt(self.total)} Schritte  ·  "
                     f"{fmt(t.consistent_calls)} consistent()-Aufrufe"
                     + (f", davon {fmt(t.domain_checks)} Domänen-Prüfungen" if t.domain_checks else "")
                     + (f"\nGesamtzeit mit Aufzeichnung {t.wall_time:.1f} s" if t.wall_time > t.duration + 1 else ""))
            self.full_redraw()

        def rerun(self):
            # Läuft schon eine Suche, wirkt der Knopf als "Abbrechen"
            if self.recorder is not None and not self.recorder.finished:
                self.recorder.cancelled = True
                self.btn_run.config(text="breche ab …", state="disabled")
                return
            if self.playing:
                self.toggle_play()
            name = self.search_var.get()
            size = None
            if not self.auto_size.get():
                try:
                    size = int(self.size_var.get())
                except (ValueError, tk.TclError):
                    size = None
            difficulty = csp.Difficulty[self.diff_var.get()]
            self.btn_run.config(text="Abbrechen", state="normal")
            self.lbl_action.config(text="Baue Puzzle …", fg=COLORS["muted"])
            rec_box = {}
            started = time.perf_counter()
            thread, box = run_in_thread(lambda: record_search(
                name, size, difficulty, args.max_steps, args.time_limit,
                lambda r: rec_box.setdefault("r", r)))

            def poll():
                rec = rec_box.get("r")
                if rec is not None:
                    self.recorder = rec
                if thread.is_alive():
                    if rec is not None:
                        self.show_live(rec, name, time.perf_counter() - started)
                    self.root.after(150, poll)
                    return
                self.btn_run.config(state="normal", text="Suche starten")
                if "error" in box:
                    err = box["error"]
                    msg = err.code if isinstance(err, SystemExit) else f"{type(err).__name__}: {err}"
                    self.lbl_action.config(text=f"Fehler: {msg}", fg=COLORS["bad"])
                    print(f"Fehler: {msg}")
                    return
                _gitter, new_trace, _result = box["value"]
                print_summary(new_trace)
                self.set_trace(new_trace)
            poll()

        def show_live(self, rec, name, elapsed):
            """Zeigt während der Suche den aktuellen Zustand (alle ~150 ms)."""
            if not isinstance(self.trace, LiveView) or self.trace.recorder is not rec:
                self.trace = LiveView(rec, name)
                self.total = 0
                self.step = 0
                self.scale.configure(to=1)
                self.lbl_info.config(text=f"{name}  ·  {self.trace.rows}×{self.trace.cols}  ·  "
                                          f"{limit_text(args.time_limit)}")
                if self.auto_size.get():
                    self.size_var.set(self.trace.rows)   # erkannte Größe anzeigen
                self.full_redraw()
            else:
                self.render()
            self.lbl_step.config(text=f"Suche läuft … {elapsed:.0f} s")
            self.lbl_action.config(text=f"{fmt(len(rec.events))} Schritte aufgezeichnet.\n"
                                        f"Danach kannst du sie Schritt für Schritt abspielen.",
                                   fg=COLORS["muted"])
            self.stat_labels["assign"].config(text=fmt(rec.n_assign))
            self.stat_labels["reject"].config(text=fmt(rec.n_reject))
            self.stat_labels["bt"].config(text=fmt(rec.n_backtrack))
            self.stat_labels["depth"].config(text=f"{rec.node_depth} / {self.trace.n_free}")

        # ---------- Steuerung ----------
        def speed(self):
            return 10 ** (self.speed_var.get() / 100 * math.log10(5000))

        def update_speed_label(self):
            self.lbl_speed.config(text=f"{self.speed():.0f} /s")

        def goto(self, step):
            if isinstance(self.trace, LiveView) or self.trace is None:
                return            # während die Suche läuft, gibt es noch nichts abzuspielen
            self.step = max(0, min(self.total, int(step)))
            self.render()

        def on_scale(self, value):
            if not self._updating_scale:
                self.goto(float(value))

        def next_backtrack(self):
            for i in range(self.step, self.total):
                if self.trace.events[i][0] == BACKTRACK:
                    self.goto(i + 1)
                    return
            self.goto(self.total)

        def toggle_play(self):
            if isinstance(self.trace, LiveView) or self.trace is None:
                return
            if not self.playing and self.step >= self.total:
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

        # ---------- Geometrie ----------
        @staticmethod
        def _margin_for(cell, size):
            digits = len(str(max(size - 1, 0)))
            return max(18, int(cell * 0.35) + 6 * digits + 8)

        def update_geometry(self):
            t = self.trace
            w = max(self.canvas.winfo_width(), 100)
            h = max(self.canvas.winfo_height(), 100)
            cell = 56
            for _ in range(3):   # Rand hängt von der Zellgröße ab → kurz iterieren
                margin = self._margin_for(cell, t.size)
                cell = max(6, min(80, int(min((w - margin - 8) / t.cols,
                                              (h - margin - 8) / t.rows))))
            self.cell, self.margin = cell, self._margin_for(cell, t.size)

        def cell_box(self, r, c):
            x0 = self.margin + c * self.cell
            y0 = self.margin + r * self.cell
            return x0, y0, x0 + self.cell, y0 + self.cell

        # ---------- Zeichnen ----------
        def schedule_redraw(self):
            if self._redraw_job is not None:
                self.root.after_cancel(self._redraw_job)
            self._redraw_job = self.root.after(60, self.full_redraw)

        def full_redraw(self):
            self._redraw_job = None
            if self.trace is None:
                return
            self.update_geometry()
            cv = self.canvas
            cv.delete("all")
            self.sigs = {}
            t = self.trace
            font = ("Helvetica", max(7, min(11, self.cell // 4)))
            # Bei sehr vielen Spalten nur jede zweite/fünfte Nummer beschriften
            every = 1 if self.cell >= 18 else (2 if self.cell >= 11 else 5)
            for c in range(0, t.cols, every):
                x0, _, x1, _ = self.cell_box(0, c)
                cv.create_text((x0 + x1) / 2, self.margin / 2, text=str(c),
                               fill=COLORS["muted"], font=font)
            for r in range(0, t.rows, every):
                _, y0, _, y1 = self.cell_box(r, 0)
                cv.create_text(self.margin / 2, (y0 + y1) / 2, text=str(r),
                               fill=COLORS["muted"], font=font)
            self.render()

        def draw_piece(self, tag, x0, y0, x1, y1, value, color):
            cv = self.canvas
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            s = x1 - x0
            w = max(2, s * 0.16)
            if value == csp.Domain.CIRCLE:
                rad = s * 0.30
                cv.create_oval(cx - rad, cy - rad, cx + rad, cy + rad,
                               fill=color, outline="", tags=tag)
            elif value == csp.Domain.HORIZONTAL_LINE:
                cv.create_line(x0 + 1, cy, x1 - 1, cy, fill=color, width=w,
                               capstyle="butt", tags=tag)
            elif value == csp.Domain.VERTICAL_LINE:
                cv.create_line(cx, y0 + 1, cx, y1 - 1, fill=color, width=w,
                               capstyle="butt", tags=tag)
            elif value == csp.Domain.EMPTY:
                rad = max(1, s * 0.05)
                cv.create_oval(cx - rad, cy - rad, cx + rad, cy + rad,
                               fill=COLORS["muted"], outline="", tags=tag)

        def draw_marks(self, tag, x0, y0, s, values):
            """Kleine 2×2-Markierungen für die noch möglichen Werte einer Zelle."""
            cv = self.canvas
            q = s / 2
            for value in values:
                px, py = MARK_POS[value]
                cx, cy = x0 + q * px + q / 2, y0 + q * py + q / 2
                k = q * 0.28
                if value == csp.Domain.CIRCLE:
                    cv.create_oval(cx - k, cy - k, cx + k, cy + k, outline=COLORS["mark"],
                                   width=1, tags=tag)
                elif value == csp.Domain.HORIZONTAL_LINE:
                    cv.create_line(cx - k, cy, cx + k, cy, fill=COLORS["mark"], width=2, tags=tag)
                elif value == csp.Domain.VERTICAL_LINE:
                    cv.create_line(cx, cy - k, cx, cy + k, fill=COLORS["mark"], width=2, tags=tag)
                else:
                    cv.create_rectangle(cx - 1, cy - 1, cx + 1, cy + 1, fill=COLORS["mark"],
                                        outline="", tags=tag)

        def render(self):
            t = self.trace
            if t is None:
                return
            cv = self.canvas
            assignment, domains = t.state(self.step)
            ev = t.events[self.step - 1] if self.step > 0 else None
            kind = ev[0] if ev else None

            # Hervorgehobene Zellen des aktuellen Schritts
            highlight = {}
            if ev:
                color = {START: "ok", ASSIGN: "ok", REJECT: "bad", PRUNED: "bad",
                         BACKTRACK: "bt", SOLUTION: "solution"}[kind]
                for cell in ev[1]:
                    highlight[cell] = COLORS[color]
            show_marks = self.show_domains.get() and self.cell >= 20

            # Nur Zellen neu zeichnen, deren Darstellung sich geändert hat
            for r in range(t.rows):
                for c in range(t.cols):
                    cell = (r, c)
                    value = assignment.get(cell)
                    outline = highlight.get(cell)
                    marks = None
                    if cell in t.given:
                        bg, color = COLORS["given_bg"], COLORS["given"]
                    elif kind in (REJECT, PRUNED) and cell == ev[1][0]:
                        bg, color, value = COLORS["assigned"], COLORS["bad"], ev[2]
                    elif value is not None:
                        bg = COLORS["assigned"]
                        color = COLORS["ok"] if outline and kind in (ASSIGN, START) else COLORS["piece"]
                    else:
                        color = None
                        dom = domains.get(cell)
                        if dom is not None and len(dom) == 0:
                            bg = COLORS["wipeout"]
                        else:
                            bg = COLORS["unassigned"]
                            if show_marks and dom is not None:
                                marks = tuple(sorted(dom, key=lambda d: d.value))
                    sig = (bg, value, color, marks, outline)
                    if self.sigs.get(cell) == sig:
                        continue
                    self.sigs[cell] = sig
                    tag = f"c{r}_{c}"
                    cv.delete(tag)
                    x0, y0, x1, y1 = self.cell_box(r, c)
                    cv.create_rectangle(x0, y0, x1, y1, fill=bg, outline=COLORS["grid"],
                                        width=1, tags=tag)
                    if value is not None:
                        self.draw_piece(tag, x0, y0, x1, y1, value, color)
                    elif marks:
                        self.draw_marks(tag, x0, y0, self.cell, marks)
                    if outline:
                        bw = max(2, self.cell // 14)
                        cv.create_rectangle(x0 + bw / 2 + 1, y0 + bw / 2 + 1,
                                            x1 - bw / 2 - 1, y1 - bw / 2 - 1,
                                            width=bw, outline=outline, tags=tag)

            # Infotexte
            self.lbl_step.config(text=f"Schritt {fmt(self.step)} / {fmt(self.total)}")
            if ev is None:
                self.lbl_action.config(text="Startkonfiguration – Vorgaben in Gelb.\n"
                                            "▶ drücken, um die Suche abzuspielen.",
                                       fg=COLORS["text"])
            else:
                text, tag = describe(t, self.step - 1)
                self.lbl_action.config(text=text, fg=COLORS[tag])

            depth = ev[5] if ev else 0
            self.stat_labels["assign"].config(text=fmt(t.assigns_cum[self.step]))
            self.stat_labels["reject"].config(text=fmt(t.rejects_cum[self.step]))
            self.stat_labels["bt"].config(text=fmt(t.backtracks_cum[self.step]))
            self.stat_labels["depth"].config(text=f"{depth} / {t.n_free}")

            bw = self.depth_bar.winfo_width() or 330
            self.depth_bar.delete("all")
            if t.n_free:
                self.depth_bar.create_rectangle(0, 0, bw * min(depth, t.n_free) / t.n_free, 10,
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
            n = self.log_lines
            lo = max(0, self.step - n)
            hi = min(self.total, self.step + 2)
            if self.step <= n:
                log.insert("end", "     0 Startkonfiguration\n",
                           ("muted",) + (("cur",) if self.step == 0 else ()))
            for i in range(lo, hi):
                text, tag = describe(t, i)
                tags = (tag,) + (("cur",) if i + 1 == self.step else ())
                log.insert("end", f"{i + 1:>6} {text}\n", tags)
            log.config(state="disabled")
            log.see("end")

    root = tk.Tk()
    app = App(root)

    def on_close():
        if app.recorder is not None:
            app.recorder.cancelled = True   # laufende Suche beenden
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


# --------------------------------------------------------------------------
# 5) Einstieg
# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Visualisiert die Suche des Lollipop-Solvers.")
    parser.add_argument("--search", default=search_variant,
                        help=f"Name der Suchfunktion in csp_solver.py (Standard: {search_variant})")
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE,
                        help="Gittergröße erzwingen (Standard: automatisch aus den "
                             "Vorgaben in build_puzzle erkannt)")
    parser.add_argument("--difficulty", default=DEFAULT_DIFFICULTY,
                        choices=[d.name for d in csp.Difficulty] + [d.name.lower() for d in csp.Difficulty],
                        help=f"Schwierigkeit (Standard: {DEFAULT_DIFFICULTY})")
    parser.add_argument("--max-steps", type=int, default=MAX_STEPS,
                        help=f"maximale Anzahl aufgezeichneter Schritte, 0 = unbegrenzt "
                             f"(Standard: {MAX_STEPS})")
    parser.add_argument("--time-limit", type=float, default=TIME_LIMIT,
                        help="Zeitlimit der Suche in Sekunden, 0 = keins (Standard: keins)")
    parser.add_argument("--list", action="store_true", help="verfügbare Suchfunktionen anzeigen")
    parser.add_argument("--no-gui", action="store_true", help="nur Konsolenausgabe, kein Fenster")
    args = parser.parse_args()
    args.difficulty = csp.Difficulty[args.difficulty.upper()]

    searches = available_searches(load_solver_functions())
    if args.list:
        print("Suchfunktionen in csp_solver.py:\n  " + "\n  ".join(searches))
        return

    if not args.no_gui:
        # Fenster sofort öffnen, die Suche läuft im Hintergrund und wird live gezeigt
        run_gui(args, searches)
        return

    print(f"Zeichne '{args.search}' auf ({limit_text(args.time_limit)}) …")
    rec_box = {}
    thread, box = run_in_thread(lambda: record_search(
        args.search, args.size, args.difficulty, args.max_steps, args.time_limit,
        lambda r: rec_box.setdefault("r", r)))
    shown = False
    while thread.is_alive():
        thread.join(2.0)
        if not shown and rec_box.get("r") is not None:
            shown = True
            g = rec_box["r"].gitter
            print(f"Puzzle: {g.size}×{g.size}, {len(rec_box['r'].init_a)} Vorgaben")
        rec = rec_box.get("r")
        if thread.is_alive() and rec is not None:
            print(f"  … {fmt(len(rec.events))} Schritte, {fmt(rec.n_assign)} Belegungen, "
                  f"{fmt(rec.n_backtrack)} Backtracks, Tiefe {rec.node_depth}", flush=True)
    if "error" in box:
        raise box["error"]
    print_summary(box["value"][1])


if __name__ == "__main__":
    main()