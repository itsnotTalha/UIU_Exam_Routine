import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';

const PANEL_CACHE = GLib.build_filenamev([
    GLib.get_home_dir(), '.local', 'share', 'uiu-exam-widget', 'panel-cache.json',
]);

const APP_LAUNCHER = GLib.build_filenamev([
    GLib.get_home_dir(), '.local', 'bin', 'uiu-exam-widget',
]);

function durationText(milliseconds) {
    const totalMinutes = Math.max(0, Math.floor(milliseconds / 60000));
    const days = Math.floor(totalMinutes / 1440);
    const hours = Math.floor((totalMinutes % 1440) / 60);
    const minutes = totalMinutes % 60;

    if (days > 0)
        return `${days}d ${hours}h`;
    if (hours > 0)
        return `${hours}h ${minutes}m`;
    if (minutes > 0)
        return `${minutes}m`;
    return '<1m';
}

function parseDate(value) {
    if (!value)
        return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
}

function readPanelCache() {
    try {
        const file = Gio.File.new_for_path(PANEL_CACHE);
        const [, contents] = file.load_contents(null);
        const text = new TextDecoder().decode(contents);
        const data = JSON.parse(text);
        return Array.isArray(data.exams) ? data.exams : [];
    } catch (e) {
        return [];
    }
}

function nextState(exams) {
    const now = new Date();
    const normalized = exams
        .map(exam => ({
            ...exam,
            startDate: parseDate(exam.start),
            endDate: parseDate(exam.end),
        }))
        .filter(exam => exam.startDate !== null);

    const live = normalized
        .filter(exam => exam.startDate <= now && (!exam.endDate || now <= exam.endDate))
        .sort((a, b) => a.startDate - b.startDate);

    if (live.length > 0)
        return {kind: 'live', exam: live[0], now};

    const upcoming = normalized
        .filter(exam => exam.startDate > now)
        .sort((a, b) => a.startDate - b.startDate);

    if (upcoming.length > 0)
        return {kind: 'upcoming', exam: upcoming[0], now};

    if (normalized.length > 0)
        return {kind: 'done', exam: null, now};

    return {kind: 'empty', exam: null, now};
}

const ExamIndicator = GObject.registerClass(
class ExamIndicator extends PanelMenu.Button {
    _init(extension) {
        super._init(0.0, 'UIU Exam Indicator', false);
        this._extension = extension;

        this._box = new St.BoxLayout({
            style_class: 'uiu-exam-panel-box',
            y_align: Clutter.ActorAlign.CENTER,
        });

        this._icon = new St.Icon({
            icon_name: 'x-office-calendar-symbolic',
            style_class: 'system-status-icon uiu-exam-panel-icon',
            y_align: Clutter.ActorAlign.CENTER,
        });

        this._label = new St.Label({
            text: 'UIU · Loading…',
            style_class: 'uiu-exam-panel-label uiu-exam-empty',
            y_align: Clutter.ActorAlign.CENTER,
        });

        this._box.add_child(this._icon);
        this._box.add_child(this._label);
        this.add_child(this._box);

        this.connect('button-press-event', () => {
            this._extension.launchApp();
            return Clutter.EVENT_STOP;
        });
    }

    setStatus(text, urgencyClass) {
        this._label.text = text;
        this._label.style_class = `uiu-exam-panel-label ${urgencyClass}`;
        this.accessible_name = text;
    }
});

export default class UIUExamIndicatorExtension extends Extension {
    enable() {
        this._indicator = new ExamIndicator(this);

        // GNOME's date menu/clock lives in the center box. Position 0 inserts this
        // indicator on its left, which keeps it immediately before the clock on a
        // standard Ubuntu/GNOME panel.
        Main.panel.addToStatusArea(this.uuid, this._indicator, 0, 'center');

        this._refresh();

        this._timerId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 30, () => {
            this._refresh();
            return GLib.SOURCE_CONTINUE;
        });

        try {
            const file = Gio.File.new_for_path(PANEL_CACHE);
            const parent = file.get_parent();
            if (parent) {
                this._monitor = parent.monitor_directory(Gio.FileMonitorFlags.NONE, null);
                this._monitorId = this._monitor.connect('changed', (_monitor, changedFile) => {
                    if (changedFile && changedFile.get_basename() === 'panel-cache.json')
                        this._refresh();
                });
            }
        } catch (e) {
            this._monitor = null;
            this._monitorId = null;
        }
    }

    _refresh() {
        if (!this._indicator)
            return;

        const state = nextState(readPanelCache());

        if (state.kind === 'empty') {
            this._indicator.setStatus('UIU · Fetch routine', 'uiu-exam-empty');
            return;
        }

        if (state.kind === 'done') {
            this._indicator.setStatus("✓ You're good now", 'uiu-exam-good');
            return;
        }

        const exam = state.exam;
        const code = exam.course_code || 'Exam';
        const room = exam.room && exam.room !== '—' ? `R${exam.room}` : 'Room —';

        if (state.kind === 'live') {
            const remaining = exam.endDate ? durationText(exam.endDate - state.now) : 'now';
            this._indicator.setStatus(`${code} · LIVE ${remaining} · ${room}`, 'uiu-exam-live');
            return;
        }

        const remainingMs = exam.startDate - state.now;
        const remaining = durationText(remainingMs);
        let urgency = 'uiu-exam-normal';

        if (remainingMs <= 60 * 60 * 1000)
            urgency = 'uiu-exam-critical';
        else if (remainingMs <= 6 * 60 * 60 * 1000)
            urgency = 'uiu-exam-critical';
        else if (remainingMs <= 24 * 60 * 60 * 1000)
            urgency = 'uiu-exam-urgent';
        else if (remainingMs <= 3 * 24 * 60 * 60 * 1000)
            urgency = 'uiu-exam-soon';

        this._indicator.setStatus(`${code} · ${remaining} · ${room}`, urgency);
    }

    launchApp() {
        try {
            Gio.Subprocess.new([APP_LAUNCHER], Gio.SubprocessFlags.NONE);
        } catch (e) {
            Main.notify('UIU Exam Widget', 'Could not open the app. Run install-topbar.sh again.');
        }
    }

    disable() {
        if (this._timerId) {
            GLib.Source.remove(this._timerId);
            this._timerId = null;
        }

        if (this._monitor && this._monitorId) {
            this._monitor.disconnect(this._monitorId);
            this._monitorId = null;
        }
        this._monitor?.cancel();
        this._monitor = null;

        this._indicator?.destroy();
        this._indicator = null;
    }
}
