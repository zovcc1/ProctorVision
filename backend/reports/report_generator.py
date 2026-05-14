import os
import cv2
import csv
import time
from pathlib import Path
from typing import Dict, Any, List
from backend.config.config_manager import config
from backend.session.session_manager import Session

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, Image, HRFlowable,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False


# Human-readable event labels and severity
EVENT_META = {
    'gaze_outside':   {'label': 'Looked Away From Screen',       'severity': 'Medium'},
    'phone_detected': {'label': 'Mobile Phone Detected',          'severity': 'High'},
    'extra_person':   {'label': 'Additional Person in Frame',     'severity': 'High'},
    'mouth_covered':  {'label': 'Mouth Covered (possible whispering)', 'severity': 'Medium'},
    'focus_loss':     {'label': 'Tab/Window Focus Lost (Terminated)', 'severity': 'High'},
    'attempted_focus_loss': {'label': 'Brief Focus Loss Attempt', 'severity': 'Medium'},
    'window_closed':  {'label': 'Browser Window Closed',          'severity': 'High'},
}

SEVERITY_COLOR = {
    'High':   colors.HexColor('#c0392b'),
    'Medium': colors.HexColor('#e67e22'),
    'Low':    colors.HexColor('#27ae60'),
}


class ReportGenerator:
    def __init__(self):
        base_dir = Path(__file__).resolve().parent.parent.parent
        reports_dir = config.get('output.reports_dir', 'reports_output')
        if not Path(reports_dir).is_absolute():
            self._reports_dir = base_dir / reports_dir
        else:
            self._reports_dir = Path(reports_dir)
        self._reports_dir.mkdir(parents=True, exist_ok=True)
        self._snapshots_dir = self._reports_dir / 'snapshots'
        self._snapshots_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_event_frame(self, session: Session, event_type: str, frame) -> None:
        """Save a JPEG snapshot when an event starts. Called from app.py."""
        try:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f"Snapshot_{timestamp}_{event_type}_{session.id[:8]}.jpg"
            path = self._snapshots_dir / filename
            cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            session.captured_frames.append({
                'event':     event_type,
                'timestamp': time.time(),
                'path':      str(path),
            })
        except Exception as e:
            print(f"Frame capture error: {e}")

    def generate_csv(self, session: Session, timestamp: str = None) -> str:
        if not timestamp:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f"ProctorReport_{timestamp}_{session.id[:8]}.csv"
        filepath = self._reports_dir / filename
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'attention_state', 'gaze_direction',
                'yaw', 'pitch', 'roll', 'mouth_ratio',
                'persons_count', 'phone_detected', 'hand_near_face', 'mouth_covered',
            ])
            for rec in session.records:
                writer.writerow([
                    rec.get('timestamp', ''),
                    rec.get('attention_state', ''),
                    rec.get('gaze_direction', ''),
                    round(rec.get('yaw', 0.0), 2),
                    round(rec.get('pitch', 0.0), 2),
                    round(rec.get('roll', 0.0), 2),
                    round(rec.get('mouth_ratio', 0.0), 3),
                    rec.get('persons_count', 0),
                    'Yes' if rec.get('phone_detected') else 'No',
                    'Yes' if rec.get('hand_near_face') else 'No',
                    'Yes' if rec.get('mouth_covered') else 'No',
                ])
        return str(filepath)

    def generate_pdf(self, session: Session, timestamp: str = None) -> str:
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("reportlab not installed. Run: pip install reportlab")

        if not timestamp:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f"ProctorReport_{timestamp}_{session.id[:8]}.pdf"
        filepath = self._reports_dir / filename
        doc = SimpleDocTemplate(
            str(filepath), pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm,
        )
        styles = getSampleStyleSheet()
        story = []

        # ── Title ──────────────────────────────────────────────────────
        story.append(Paragraph("<b>ProctorVision - Session Report</b>", styles['Title']))
        story.append(Spacer(1, 0.3*cm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        story.append(Spacer(1, 0.3*cm))

        # ── Session summary ────────────────────────────────────────────
        stats = self._compute_stats(session)
        summary_data = [
            ['Session ID',     session.id],
            ['Start Time',     time.ctime(session.start_time)],
            ['End Time',       time.ctime(session.end_time) if session.end_time else 'N/A'],
            ['Duration',       f"{session.duration()} seconds"],
            ['Total Records',  str(len(session.records))],
            ['Attentive',      f"{stats.get('attentive_pct', 0)}%"],
            ['Distracted',     f"{stats.get('distracted_pct', 0)}%"],
            ['Warning',        f"{stats.get('warning_pct', 0)}%"],
        ]
        summary_table = Table(summary_data, colWidths=[5*cm, 11*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND',  (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('GRID',        (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME',    (0, 0), (0, -1), 'Helvetica-Bold'),
            ('TOPPADDING',  (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.5*cm))

        # ── Risk summary ───────────────────────────────────────────────
        story.append(self._build_risk_summary(session, stats, styles))
        story.append(Spacer(1, 0.5*cm))

        # ── Timeline chart ─────────────────────────────────────────────
        chart_path = None
        if MATPLOTLIB_AVAILABLE and session.records:
            chart_path = self._generate_timeline_chart(session)
            if chart_path:
                story.append(Paragraph("<b>Attention Timeline</b>", styles['Heading2']))
                story.append(Image(chart_path, width=16*cm, height=5*cm))
                story.append(Spacer(1, 0.5*cm))

        # ── Detected events ────────────────────────────────────────────
        # Combine session events and external events
        all_events = []
        for ev in session.events:
            all_events.append({
                'type': ev.get('type'),
                'start': ev.get('start'),
                'end': ev.get('end'),
                'duration': ev.get('duration'),
                'source': 'vision'
            })
        for ev in session.external_events:
            all_events.append({
                'type': ev.get('type'),
                'start': ev.get('timestamp'),
                'end': ev.get('timestamp'),
                'duration': 0,
                'source': 'external'
            })

        # Sort by start time
        all_events.sort(key=lambda x: x['start'])

        if all_events:
            story.append(Paragraph("<b>Detected Events</b>", styles['Heading2']))
            story.append(Spacer(1, 0.2*cm))

            # Build frame lookup: event_type → list of paths
            frame_lookup: Dict[str, List[str]] = {}
            for cf in session.captured_frames:
                frame_lookup.setdefault(cf['event'], []).append(cf['path'])
            frame_used: Dict[str, int] = {}  # track index per event type

            for ev in all_events:
                etype = ev.get('type', '')
                meta = EVENT_META.get(etype, {'label': etype, 'severity': 'Low'})
                sev_color = SEVERITY_COLOR.get(meta['severity'], colors.grey)

                # Event header row
                header_data = [[
                    Paragraph(f"<b>{meta['label']}</b>", styles['Normal']),
                    Paragraph(f"<b>Severity: {meta['severity']}</b>", styles['Normal']),
                    Paragraph(f"<b>Duration: {ev.get('duration', 0)}s</b>", styles['Normal']),
                ]]
                header_table = Table(header_data, colWidths=[8*cm, 4*cm, 4*cm])
                header_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), sev_color),
                    ('TEXTCOLOR',  (0, 0), (-1, -1), colors.white),
                    ('TOPPADDING',    (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING',   (0, 0), (-1, -1), 8),
                ]))
                story.append(header_table)

                # Event detail row
                detail_data = [[
                    f"Start: {time.ctime(ev.get('start', 0))}",
                    f"End:   {time.ctime(ev.get('end', 0))}",
                    '',
                ]]
                detail_table = Table(detail_data, colWidths=[8*cm, 4*cm, 4*cm])
                detail_table.setStyle(TableStyle([
                    ('GRID',       (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ('FONTSIZE',   (0, 0), (-1, -1), 8),
                    ('TOPPADDING',    (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING',   (0, 0), (-1, -1), 8),
                ]))
                story.append(detail_table)

                # Embedded snapshot if available
                idx = frame_used.get(etype, 0)
                paths = frame_lookup.get(etype, [])
                if idx < len(paths) and Path(paths[idx]).exists():
                    story.append(Spacer(1, 0.2*cm))
                    story.append(
                        Image(paths[idx], width=7*cm, height=5*cm, kind='proportional')
                    )
                    frame_used[etype] = idx + 1

                story.append(Spacer(1, 0.4*cm))

        doc.build(story)

        # ── Cleanup ────────────────────────────────────────────────────
        # Remove chart if it exists
        if chart_path and Path(chart_path).exists():
            try:
                Path(chart_path).unlink()
            except Exception as e:
                print(f"Chart cleanup error: {e}")

        # Remove snapshots
        for cf in session.captured_frames:
            try:
                p = Path(cf['path'])
                if p.exists():
                    p.unlink()
            except Exception as e:
                print(f"Snapshot cleanup error: {e}")

        return str(filepath)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_risk_summary(self, session: Session, stats: Dict, styles) -> Table:
        total_suspicious_s = round(
            session.duration() * (1 - stats.get('attentive_pct', 100) / 100), 1
        )

        vision_high = [
            e for e in session.events
            if EVENT_META.get(e.get('type', ''), {}).get('severity') == 'High'
        ]
        external_high = [
            e for e in session.external_events
            if EVENT_META.get(e.get('type', ''), {}).get('severity') == 'High'
        ]
        high_severity_count = len(vision_high) + len(external_high)

        verdict = 'LOW RISK'
        verdict_color = colors.HexColor('#27ae60')
        total_events_count = len(session.events) + len(session.external_events)

        if total_events_count >= 5 or total_suspicious_s > 30 or high_severity_count > 0:
            verdict = 'HIGH RISK — Review Required'
            verdict_color = colors.HexColor('#c0392b')
        elif total_events_count >= 2 or total_suspicious_s > 10:
            verdict = 'MEDIUM RISK'
            verdict_color = colors.HexColor('#e67e22')

        lines = [
            f"Total suspicious time: {total_suspicious_s}s "
            f"({round(100 - stats.get('attentive_pct', 100), 1)}% of session)",
            f"Total incidents: {total_events_count}",
            f"High-severity incidents: {high_severity_count}",
        ]
        body = '\n'.join(lines)

        data = [
            [Paragraph(f"<b>Risk Assessment: {verdict}</b>", styles['Normal'])],
            [Paragraph(body.replace('\n', '<br/>'), styles['Normal'])],
        ]
        t = Table(data, colWidths=[16*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), verdict_color),
            ('TEXTCOLOR',     (0, 0), (-1, 0), colors.white),
            ('BACKGROUND',    (0, 1), (-1, -1), colors.HexColor('#fdfefe')),
            ('GRID',          (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING',   (0, 0), (-1, -1), 10),
        ]))
        return t

    def _compute_stats(self, session: Session) -> Dict[str, Any]:
        total = len(session.records)
        if total == 0:
            return {}
        counts = {'Attentive': 0, 'Distracted': 0, 'Warning': 0}
        for r in session.records:
            st = r.get('attention_state', 'Attentive')
            counts[st] = counts.get(st, 0) + 1
        return {
            'attentive_pct':  round(counts['Attentive']  / total * 100, 1),
            'distracted_pct': round(counts['Distracted'] / total * 100, 1),
            'warning_pct':    round(counts['Warning']    / total * 100, 1),
        }

    def _generate_timeline_chart(self, session: Session) -> str:
        try:
            records = session.records
            t0 = records[0].get('timestamp', 0)
            ts = [r.get('timestamp', 0) - t0 for r in records]
            states = [r.get('attention_state', 'Attentive') for r in records]
            color_map = {'Attentive': 'green', 'Distracted': 'orange', 'Warning': 'red'}
            colors_list = [color_map.get(s, 'grey') for s in states]

            fig, ax = plt.subplots(figsize=(10, 2.5))
            ax.scatter(ts, [1] * len(ts), c=colors_list, s=60, marker='s')
            ax.set_yticks([])
            ax.set_xlabel('Time (seconds)')
            ax.set_title('Attention State Timeline')
            legend_elements = [
                Patch(facecolor='green',  label='Attentive'),
                Patch(facecolor='orange', label='Distracted'),
                Patch(facecolor='red',    label='Warning'),
            ]
            ax.legend(handles=legend_elements, loc='upper right')
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            chart_path = self._reports_dir / f"chart_{timestamp}_{session.id[:8]}.png"
            plt.tight_layout()
            plt.savefig(str(chart_path), dpi=100)
            plt.close(fig)
            return str(chart_path)
        except Exception as e:
            print(f"Chart generation error: {e}")
            return None