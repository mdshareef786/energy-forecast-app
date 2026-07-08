import io
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.asset import Device
from app.models.reading import EnergyReading
from app.models.ml_results import Forecast, Anomaly, Recommendation
from app.models.user import User
from app.core.security import get_current_user

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/device/{device_id}/csv")
def export_device_csv(device_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    readings = (
        db.query(EnergyReading)
        .filter(EnergyReading.device_id == device_id)
        .order_by(EnergyReading.timestamp)
        .all()
    )
    if not readings:
        raise HTTPException(status_code=400, detail="No readings available to export for this device")

    df = pd.DataFrame([
        {"timestamp": r.timestamp.isoformat(), "energy_kwh": r.energy_kwh, "temperature_c": r.temperature_c}
        for r in readings
    ])

    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)

    filename = f"{device.name.replace(' ', '_')}_energy_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/device/{device_id}/pdf")
def export_device_pdf(device_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    readings = (
        db.query(EnergyReading)
        .filter(EnergyReading.device_id == device_id)
        .order_by(EnergyReading.timestamp)
        .all()
    )
    latest_forecast = (
        db.query(Forecast).filter(Forecast.device_id == device_id).order_by(Forecast.generated_at.desc()).first()
    )
    recent_anomalies = (
        db.query(Anomaly).filter(Anomaly.device_id == device_id).order_by(Anomaly.timestamp.desc()).limit(10).all()
    )
    recommendations = (
        db.query(Recommendation).filter(Recommendation.device_id == device_id)
        .order_by(Recommendation.created_at.desc()).limit(10).all()
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], fontSize=18, spaceAfter=4)
    section_style = ParagraphStyle("SectionCustom", parent=styles["Heading2"], spaceBefore=16, spaceAfter=6)

    story = [
        Paragraph("Energy Consumption Report", title_style),
        Paragraph(f"{device.name} — generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]),
        Spacer(1, 12),
    ]

    # Summary
    total_kwh = sum(r.energy_kwh for r in readings) if readings else 0
    story.append(Paragraph("Summary", section_style))
    summary_data = [
        ["Total readings", str(len(readings))],
        ["Total consumption (kWh)", f"{total_kwh:.1f}"],
        ["Anomalies logged", str(len(recent_anomalies))],
        ["Recommendations generated", str(len(recommendations))],
    ]
    summary_table = Table(summary_data, colWidths=[220, 220])
    summary_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(summary_table)

    # Forecast accuracy
    if latest_forecast:
        story.append(Paragraph("Latest Forecast", section_style))
        forecast_data = [
            ["Model", str(latest_forecast.model_type.value if hasattr(latest_forecast.model_type, "value") else latest_forecast.model_type)],
            ["Horizon", str(latest_forecast.horizon.value if hasattr(latest_forecast.horizon, "value") else latest_forecast.horizon)],
            ["MAE", f"{latest_forecast.mae:.2f}" if latest_forecast.mae is not None else "—"],
            ["RMSE", f"{latest_forecast.rmse:.2f}" if latest_forecast.rmse is not None else "—"],
            ["MAPE", f"{latest_forecast.mape:.1f}%" if latest_forecast.mape is not None else "—"],
        ]
        forecast_table = Table(forecast_data, colWidths=[220, 220])
        forecast_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(forecast_table)

    # Anomalies
    story.append(Paragraph("Recent Anomalies", section_style))
    if recent_anomalies:
        anomaly_rows = [["Timestamp", "Energy (kWh)", "Severity", "Reason"]]
        for a in recent_anomalies:
            anomaly_rows.append([
                a.timestamp.strftime("%Y-%m-%d %H:%M"),
                f"{a.energy_kwh:.1f}",
                str(a.severity.value if hasattr(a.severity, "value") else a.severity),
                (a.reason or "")[:60],
            ])
        anomaly_table = Table(anomaly_rows, colWidths=[110, 90, 70, 190])
        anomaly_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))
        story.append(anomaly_table)
    else:
        story.append(Paragraph("No anomalies detected.", styles["Normal"]))

    # Recommendations
    story.append(Paragraph("Optimization Recommendations", section_style))
    if recommendations:
        for r in recommendations:
            story.append(Paragraph(f"• [{r.priority.upper()}] {r.message}", styles["Normal"]))
    else:
        story.append(Paragraph("No recommendations generated yet.", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)

    filename = f"{device.name.replace(' ', '_')}_report_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
