import base64
from io import BytesIO
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import tempfile
import pdfkit
from html2image import Html2Image
import os

from functions import data as db, func_valor as val, func_summary, viz, utility


def fig_to_base64(fig, kind="plotly"):
    if kind == "plotly":
        if not isinstance(fig, go.Figure):
            raise ValueError("Expected a plotly.graph_objects.Figure, but got a different type.")
        img_bytes = fig.to_image(format="png", width=900, height=400, scale=2)
    elif kind == "matplotlib":
        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches='tight')
        buf.seek(0)
        img_bytes = buf.read()
        plt.close(fig)
    return base64.b64encode(img_bytes).decode("utf-8")


def generate_report_html(selected_name):
    athlete_info = db.AthleteInfoData(athlete=selected_name)
    sprintData = db.swiftSprint(data=db.dfSprint, player_name=selected_name)
    agilityData = db.proAgility(data=db.dfProAgility, player_name=selected_name)
    VerticalData = db.verticalJump(player_name=selected_name)
    BroadJumpData = db.broadJump(player_name=selected_name)
    dfCMJ = db.AthleteCMJ(athlete=selected_name)
    dfMR = db.AthleteMR(athlete=selected_name)
    summary = func_summary.get_athlete_summary(selected_name)

    try:
        token = db.valorToken
        valorAthletes = val.ValorAthletes(token=token)
        athlete_id = valorAthletes[valorAthletes["Name"] == selected_name]["ValorID"].values[0]
        valorSessions = val.ValorSessions(token=token)
        hip_score = shoulder_score = ankle_score = 0

        session_data = valorSessions[valorSessions["Athlete ID"] == athlete_id]
        hip_sessions = session_data[session_data['Session Name'] == "Hip Hinge Test"]
        if not hip_sessions.empty:
            hip_data = val.ValorHipHinge(token=token, key=hip_sessions['s3Key'].values[0])
            hip_score = hip_data["Score"].mean(skipna=True) * 100 if not hip_data.empty else 0
        shoulder_score = 80
        ankle_score = 85
    except:
        hip_score = shoulder_score = ankle_score = 0

    images_html = ""

    def image_block(fig, title):
        encoded = fig_to_base64(fig, kind="plotly")
        return f"<div class='img-block'><h4>{title}</h4><img src='data:image/png;base64,{encoded}' /></div>"

    def score_chart_image(score, label):
        fig = go.Figure(go.Bar(
            x=[label],
            y=[score],
            marker_color="#00A651" if score > 85 else "#FF4B4B" if score < 75 else "#FFC107",
            text=[f"{int(score)}%"],
            textposition="outside"
        ))
        fig.update_layout(yaxis=dict(range=[0, 100]), height=200, margin=dict(t=20, b=20))
        return image_block(fig, label + " Score")

    images_html += score_chart_image(shoulder_score, "Shoulder")
    images_html += score_chart_image(ankle_score, "Ankle")
    images_html += score_chart_image(hip_score, "Hip Hinge")

    if not sprintData.empty and not agilityData.empty:
        fig_speed = viz.plot_reactive_performance(sprintData, agilityData)
        images_html += image_block(fig_speed, "Speed & Agility Performance")

    if not dfCMJ.empty:
        fdData = pd.DataFrame({
            "Comp": ['SLO Combine', 'SLO Combine', 'Elite', 'Elite'],
            "Metric": ['Reactive Strength','Relative Power', 'Reactive Strength', 'Relative Power'],
            "Value": [
                dfCMJ['mRSI SLO Rank'].max().round(0),
                dfCMJ['Peak Rel Power SLO Rank'].max().round(0),
                dfCMJ['mRSI Elite Rank'].max().round(0),
                dfCMJ['Peak Rel Power Elite Rank'].max().round(0)]
        })
        fig_power = viz.plot_power_ranks(fdData, show=False)
        images_html += image_block(fig_power, "Power Ranks")

    def table_html(df, title):
        return f"<div class='table-block'><h4>{title}</h4>{df.to_html(index=False)}</div>"

    tables_html = ""
    if not dfCMJ.empty:
        cmj_df = dfCMJ[['Jump Height (in)', 'mRSI', 'Peak Rel Prop Power (W/kg)', 'Braking Asymmetry']].max().reset_index()
        cmj_df.columns = ['Metric', 'Value']
        tables_html += table_html(cmj_df, "Countermovement Jump Metrics")

    if not dfMR.empty:
        mr_df = dfMR[['Avg Jump Height (in)', 'Peak Jump Height (in)', 'Avg RSI', 'Peak RSI']].max().reset_index()
        mr_df.columns = ['Metric', 'Value']
        tables_html += table_html(mr_df, "Multi-Rebound Jump Metrics")

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial; margin: 20px; color: #111; }}
            h1, h2 {{ color: #ff6b35; }}
            .img-block, .table-block {{ margin-bottom: 20px; }}
            img {{ max-width: 100%; height: auto; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ border: 1px solid #ccc; padding: 6px; text-align: left; }}
        </style>
    </head>
    <body>
        <h1>Code 8 Combine Report</h1>
        <h2>{selected_name}</h2>
        <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>

        {images_html}
        {tables_html}

        {f'<div style="margin-top:20px;"><h4>Coach Summary</h4><div>{summary}</div></div>' if summary else ''}

        <div style="text-align:center; margin-top:40px; font-size:12px;">
            <p>San Luis Obispo County Combine 2025 – Code 8 Performance</p>
        </div>
    </body>
    </html>
    """
    return html


def convert_html_to_pdf(html_str):
    config = pdfkit.configuration(wkhtmltopdf="C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        pdfkit.from_string(html_str, f.name, configuration=config)
        f.seek(0)
        return f.read()


def convert_html_to_png(html_str):
    hti = Html2Image()
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    temp_file.write(html_str.encode())
    temp_file.close()

    temp_dir = tempfile.gettempdir()
    filename = "temp_report.png"
    hti.output_path = temp_dir
    hti.screenshot(html_file=temp_file.name, save_as=filename, size=(1280, 720))

    output_path = os.path.join(temp_dir, filename)
    with open(output_path, "rb") as f:
        img_bytes = BytesIO(f.read())

    os.remove(output_path)
    return img_bytes.read()
