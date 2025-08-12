import dash
from dash import dcc, html, dash_table, ctx, Input, Output, State, callback
import plotly.express as px
import plotly.io as pio
pio.templates.default = 'plotly_white'
COLORWAY = [
    '#2563EB', '#E11D48', '#059669', '#7C3AED', '#F59E0B', '#10B981',
    '#EF4444', '#3B82F6', '#8B5CF6', '#F97316', '#14B8A6', '#84CC16', '#EC4899'
]
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from sqlalchemy import create_engine, text
import urllib.parse
import logging
import datetime
import pyodbc
import json
from datetime import timedelta
import numpy as np
import base64
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Enhanced Blue Color Palette
BLUE_COLORS = {
    'dark_primary': '#0A1628',
    'primary': '#1E3A8A',
    'secondary': '#3B82F6',
    'light_blue': '#60A5FA',
    'very_light': '#DBEAFE',
    'accent': '#1D4ED8',
    'gradient_dark': '#0F172A',
    'gradient_light': '#1E40AF',
    'text_primary': '#F8FAFC',
    'text_secondary': '#CBD5E1',
    'background_dark': '#0F1419',
    'background_card': '#1E293B',
    'border': '#334155',
    'success': '#2563EB',
    'warning': '#3B82F6',
    'danger': '#1E40AF',
    'dropdown_bg': '#1E293B',
    'dropdown_text': '#F8FAFC',
    'dropdown_hover': '#334155',
    'plasman_blue': '#009FE3'  # Plasman brand blue
}

# Chart color palettes
CHART_PALETTES = {
    'main': ['#1E3A8A', '#3B82F6', '#60A5FA', '#93C5FD', '#DBEAFE', '#1D4ED8', '#2563EB', '#3730A3'],
    'customer': {
        'Volvo Cars': '#1E3A8A',
        'Volvo Trucks': '#3B82F6',
        'IPG': '#60A5FA',
        'BMW': '#93C5FD',
        'Ford': '#DBEAFE',
        'Mercedes': '#1D4ED8',
        'Audi': '#2563EB',
        'Toyota': '#3730A3',
        'Volkswagen': '#1E40AF',
        'Peugeot': '#2D3748',
        'Renault': '#4A5568',
        'Opel': '#2B6CB0'
    }
}

# Database connection
db_user = "sr-cm4dPython"
db_password = "eiBQMY7VZ!Dg1cZYlKo398tac"

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER=SEGO01SQL01\\CM4DINSTANCE;"
    f"DATABASE=Plastal-CM4D;"
    f"UID={db_user};"
    f"PWD={db_password};"
)

# Test connection
try:
    test_conn = pyodbc.connect(conn_str, timeout=10)
    test_cursor = test_conn.cursor()
    test_cursor.execute("SELECT USER_NAME() as [user_name], DB_NAME() as [db_name]")
    result = test_cursor.fetchone()
    logging.info(f"Connected as user: {result[0]}, Database: {result[1]}")
    test_conn.close()
except Exception as e:
    logging.error(f"Connection test failed: {e}")
    print(f"Connection failed: {e}")
    exit(1)

params_conn = urllib.parse.quote_plus(conn_str)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params_conn}")

FACILITIES = ["PASI", "PAGE", "PAGO"]

# Create Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# Enhanced CSS styling with Plasman branding
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>PLASMAN AB - Customer Dashboard</title>
        {%favicon%}
        {%css%}
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Inter', sans-serif;
            }
            
            body {
                background: linear-gradient(135deg, #0F1419 0%, #1E293B 50%, #0A1628 100%);
                background-attachment: fixed;
                color: #F8FAFC;
                overflow-x: hidden;
            }
            
            .main-container {
                background: linear-gradient(135deg, #0F1419 0%, #1E293B 100%);
                min-height: 100vh;
                position: relative;
            }
            
            /* Plasman Logo Styling */
            .plasman-logo {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 30px;
                margin-bottom: 20px;
                padding: 30px;
                background: linear-gradient(135deg, rgba(0, 159, 227, 0.1), rgba(30, 58, 138, 0.1));
                border-radius: 20px;
                border: 2px solid rgba(0, 159, 227, 0.3);
                box-shadow: 0 8px 32px rgba(0, 159, 227, 0.2);
            }
            
            .plasman-logo-container {
                display: flex;
                align-items: center;
                gap: 25px;
            }
            
            .logo-shapes {
                position: relative;
                width: 180px;
                height: 70px;
                margin-right: 20px;
            }
            
            .logo-shape-top {
                position: absolute;
                top: 5px;
                left: 0;
                width: 160px;
                height: 25px;
                background: linear-gradient(135deg, #2E4A6B, #3A5B7A);
                border-radius: 50px 30px 20px 50px;
                box-shadow: 0 4px 12px rgba(46, 74, 107, 0.4);
                transform: skewX(-5deg);
            }
            
            .logo-shape-bottom {
                position: absolute;
                top: 25px;
                left: 0;
                width: 160px;
                height: 25px;
                background: linear-gradient(135deg, #009FE3, #00B8E6);
                border-radius: 20px 50px 50px 30px;
                box-shadow: 0 4px 12px rgba(0, 159, 227, 0.4);
                transform: skewX(-5deg);
            }
            
            .logo-text-container {
                display: flex;
                flex-direction: column;
                align-items: flex-start;
                gap: 5px;
            }
            
            .plasman-brand-text {
                color: #009FE3;
                font-size: 3.2rem;
                font-weight: 900;
                margin: 0;
                text-shadow: 0 4px 8px rgba(0, 159, 227, 0.3);
                letter-spacing: 2px;
                background: linear-gradient(135deg, #009FE3, #0077B6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .plasman-subtitle {
                color: #60A5FA;
                font-size: 1.1rem;
                font-weight: 600;
                margin: 0;
                text-transform: uppercase;
                letter-spacing: 1px;
                opacity: 0.9;
            }
            
            /* Dashboard Builder Button */
            .dashboard-builder-btn {
                background: linear-gradient(135deg, #009FE3, #0077B6);
                border: none;
                color: white;
                padding: 16px 32px;
                border-radius: 16px;
                font-size: 16px;
                font-weight: 700;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 8px 24px rgba(0, 159, 227, 0.3);
                text-transform: uppercase;
                letter-spacing: 1px;
                display: flex;
                align-items: center;
                gap: 12px;
                margin: 20px auto;
                position: relative;
                overflow: hidden;
            }
            
            .dashboard-builder-btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 12px 32px rgba(0, 159, 227, 0.4);
                background: linear-gradient(135deg, #0077B6, #005577);
            }
            
            .dashboard-builder-btn:active {
                transform: translateY(-1px);
            }
            
            .dashboard-builder-btn::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
                transition: left 0.5s;
            }
            
            .dashboard-builder-btn:hover::before {
                left: 100%;
            }
            
            /* Modal Styling */
            .modal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                backdrop-filter: blur(10px);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                animation: fadeIn 0.3s ease-out;
            }
            
            .modal-content {
                background: linear-gradient(135deg, #1E293B, #0F172A);
                border: 2px solid #009FE3;
                border-radius: 24px;
                padding: 40px;
                max-width: 800px;
                width: 90%;
                max-height: 90vh;
                overflow-y: auto;
                box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5);
                position: relative;
                animation: slideIn 0.3s ease-out;
            }
            
            .modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid rgba(0, 159, 227, 0.3);
            }
            
            .modal-title {
                color: #009FE3;
                font-size: 1.8rem;
                font-weight: 800;
                margin: 0;
            }
            
            .close-btn {
                background: none;
                border: none;
                color: #009FE3;
                font-size: 24px;
                cursor: pointer;
                padding: 8px;
                border-radius: 8px;
                transition: all 0.3s ease;
            }
            
            .close-btn:hover {
                background: rgba(0, 159, 227, 0.2);
                transform: rotate(90deg);
            }
            
            .builder-section {
                margin-bottom: 30px;
                padding: 24px;
                background: rgba(30, 41, 59, 0.6);
                border: 1px solid rgba(0, 159, 227, 0.3);
                border-radius: 16px;
            }
            
            .builder-section-title {
                color: #60A5FA;
                font-size: 1.2rem;
                font-weight: 700;
                margin-bottom: 16px;
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .builder-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-top: 16px;
            }
            
            .builder-field {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            
            .builder-label {
                color: #CBD5E1;
                font-weight: 600;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .builder-input, .builder-select {
                background: rgba(30, 41, 59, 0.8);
                border: 2px solid rgba(0, 159, 227, 0.3);
                border-radius: 12px;
                padding: 12px 16px;
                color: #F8FAFC;
                font-size: 14px;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            
            .builder-input:focus, .builder-select:focus {
                outline: none;
                border-color: #009FE3;
                box-shadow: 0 0 0 3px rgba(0, 159, 227, 0.2);
            }
            
            .apply-config-btn {
                background: linear-gradient(135deg, #22C55E, #16A34A);
                border: none;
                color: white;
                padding: 16px 32px;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 700;
                cursor: pointer;
                transition: all 0.3s ease;
                width: 100%;
                margin-top: 20px;
            }
            
            .apply-config-btn:hover {
                background: linear-gradient(135deg, #16A34A, #15803D);
                transform: translateY(-2px);
                box-shadow: 0 8px 24px rgba(34, 197, 94, 0.3);
            }
            
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            @keyframes slideIn {
                from { transform: translateY(-50px) scale(0.95); opacity: 0; }
                to { transform: translateY(0) scale(1); opacity: 1; }
            }
            
            /* Enhanced Dropdown Styling */
            .Select-control {
                background-color: #1E293B !important;
                border: 2px solid #3B82F6 !important;
                border-radius: 12px !important;
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2) !important;
                backdrop-filter: blur(10px) !important;
            }
            
            .Select-control:hover {
                border-color: #60A5FA !important;
                box-shadow: 0 6px 20px rgba(96, 165, 250, 0.3) !important;
            }
            
            .Select-value-label {
                color: #F8FAFC !important;
                font-weight: 600 !important;
                font-size: 14px !important;
            }
            
            .Select-placeholder {
                color: #CBD5E1 !important;
                font-weight: 500 !important;
            }
            
            .Select-arrow {
                border-color: #60A5FA transparent transparent !important;
            }
            
            .Select-menu-outer {
                background-color: #1E293B !important;
                border: 2px solid #3B82F6 !important;
                border-radius: 12px !important;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4) !important;
                backdrop-filter: blur(20px) !important;
                z-index: 9999 !important;
            }
            
            .VirtualizedSelectOption,
            .Select-option {
                background-color: #1E293B !important;
                color: #F8FAFC !important;
                padding: 12px 16px !important;
                font-weight: 500 !important;
                border-bottom: 1px solid rgba(59, 130, 246, 0.1) !important;
            }
            
            .VirtualizedSelectOption:hover,
            .VirtualizedSelectFocusedOption,
            .Select-option:hover,
            .Select-option.is-focused {
                background-color: #334155 !important;
                color: #60A5FA !important;
                font-weight: 600 !important;
            }
            
            .Select-option.is-selected {
                background-color: #3B82F6 !important;
                color: #F8FAFC !important;
                font-weight: 700 !important;
            }
            
            .premium-card {
                background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
                backdrop-filter: blur(25px);
                border: 1px solid rgba(59, 130, 246, 0.3);
                border-radius: 24px;
                padding: 32px;
                transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                position: relative;
                overflow: hidden;
                box-shadow: 0 25px 50px rgba(0, 0, 0, 0.4);
                margin-bottom: 32px;
            }
            
            .header-gradient {
                background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 50%, #60A5FA 100%);
                position: relative;
                overflow: hidden;
            }
            
            .facility-header {
                font-size: 3rem;
                font-weight: 900;
                color: #F8FAFC;
                text-shadow: 0 4px 8px rgba(0,0,0,0.3);
                margin: 0;
                text-align: center;
                padding: 20px 0;
                background: linear-gradient(135deg, #60A5FA, #93C5FD);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .section-title {
                font-size: 1.5rem;
                font-weight: 800;
                color: #60A5FA;
                margin-bottom: 24px;
                display: flex;
                align-items: center;
                gap: 16px;
            }
            
            .chart-container {
                background: rgba(30, 41, 59, 0.4);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(59, 130, 246, 0.2);
                border-radius: 20px;
                padding: 24px;
                margin: 16px 0;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
                position: relative;
            }
            
            .control-panel {
                background: rgba(30, 41, 59, 0.8);
                backdrop-filter: blur(15px);
                border: 1px solid rgba(59, 130, 246, 0.3);
                border-radius: 16px;
                padding: 24px;
                margin-bottom: 32px;
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
                align-items: center;
                justify-content: space-between;
            }
            
            .control-group {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            
            .control-label {
                font-weight: 600;
                color: #CBD5E1;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .export-btn {
                background: linear-gradient(135deg, rgba(30, 58, 138, 0.8), rgba(59, 130, 246, 0.8));
                border: 1px solid rgba(96, 165, 250, 0.3);
                color: #F8FAFC;
                padding: 12px 24px;
                border-radius: 12px;
                font-size: 14px;
                cursor: pointer;
                transition: all 0.3s ease;
                backdrop-filter: blur(10px);
                margin: 8px;
                font-weight: 600;
            }
            
            .export-btn:hover {
                background: linear-gradient(135deg, rgba(59, 130, 246, 0.9), rgba(96, 165, 250, 0.9));
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(30, 58, 138, 0.4);
            }
            
            /* IMPROVED DATA TABLE STYLING WITH SCROLLING */
            .data-table {
                background: rgba(30, 41, 59, 0.6);
                backdrop-filter: blur(15px);
                border-radius: 16px;
                overflow: hidden;
                border: 1px solid rgba(59, 130, 246, 0.3);
                max-height: 600px;
                overflow-y: auto;
            }
            
            .data-table::-webkit-scrollbar {
                width: 12px;
            }
            
            .data-table::-webkit-scrollbar-track {
                background: rgba(30, 41, 59, 0.3);
                border-radius: 10px;
            }
            
            .data-table::-webkit-scrollbar-thumb {
                background: linear-gradient(135deg, #3B82F6, #60A5FA);
                border-radius: 10px;
                border: 2px solid rgba(30, 41, 59, 0.3);
            }
            
            .data-table::-webkit-scrollbar-thumb:hover {
                background: linear-gradient(135deg, #60A5FA, #93C5FD);
            }
            
            .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner table {
                border-collapse: separate !important;
                border-spacing: 0 2px !important;
            }
            
            .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td {
                border: none !important;
                padding: 16px 20px !important;
                transition: all 0.3s ease !important;
            }
            
            .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner tr:hover td {
                background-color: rgba(59, 130, 246, 0.2) !important;
                transform: scale(1.01);
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
            }
            
            .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th {
                position: sticky !important;
                top: 0 !important;
                z-index: 10 !important;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2) !important;
            }
            
            .fade-in {
                animation: fadeIn 0.8s ease-in-out;
            }
            
            .export-section {
                text-align: center;
                margin: 20px 0;
                padding: 20px;
                background: rgba(30, 41, 59, 0.5);
                border-radius: 12px;
                border: 1px solid rgba(59, 130, 246, 0.2);
            }
            
            .download-success {
                background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(16, 185, 129, 0.2));
                border: 1px solid rgba(34, 197, 94, 0.4);
                color: #10B981;
                padding: 16px;
                border-radius: 12px;
                margin-top: 12px;
                font-weight: 600;
            }
            
            .data-range-info {
                background: rgba(59, 130, 246, 0.1);
                border: 1px solid rgba(59, 130, 246, 0.3);
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 20px;
                color: #60A5FA;
                font-weight: 600;
                text-align: center;
            }
            
            /* Hide modal by default */
            .modal-hidden {
                display: none !important;
            }
        </style>
    </head>
    <body>
        <div class="main-container">
            {%app_entry%}
        </div>
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Enhanced layout with Plasman logo and dashboard builder
app.layout = html.Div([
    # Plasman Logo Section
    html.Div([
        # Custom Plasman Logo using HTML/CSS
        html.Div([
            # Logo shapes using CSS
            html.Div([
                html.Div(className="logo-shape-top"),
                html.Div(className="logo-shape-bottom")
            ], className="logo-shapes"),
            # Plasman text
            html.Div([
                html.H1("PLASMAN", className="plasman-brand-text"),
                html.P("Advanced Manufacturing Analytics", className="plasman-subtitle")
            ], className="logo-text-container")
        ], className="plasman-logo-container")
    ], className="plasman-logo"),
    
    # Dashboard Builder Button
    html.Button([
        html.I(className="fas fa-cogs"),
        "Dashboard Builder"
    ], id="dashboard-builder-btn", className="dashboard-builder-btn"),
    
    # Dashboard Builder Modal
    html.Div([
        html.Div([
            html.Div([
                html.H2([
                    html.I(className="fas fa-tools", style={'marginRight': '12px'}),
                    "Dashboard Configuration"
                ], className="modal-title"),
                html.Button("×", id="close-modal-btn", className="close-btn")
            ], className="modal-header"),
            
            # Refresh Settings
            html.Div([
                html.H3([
                    html.I(className="fas fa-sync-alt", style={'marginRight': '8px'}),
                    "Auto-Refresh Settings"
                ], className="builder-section-title"),
                html.Div([
                    html.Div([
                        html.Label("Refresh Interval:", className="builder-label"),
                        dcc.Dropdown(
                            id="refresh-interval-select",
                            options=[
                                {'label': '10 seconds', 'value': 10000},
                                {'label': '30 seconds', 'value': 30000},
                                {'label': '1 minute', 'value': 60000},
                                {'label': '5 minutes', 'value': 300000},
                                {'label': '10 minutes', 'value': 600000},
                                {'label': 'Disabled', 'value': 0}
                            ],
                            value=30000,
                            className="builder-select",
                            style={'backgroundColor': 'rgba(30, 41, 59, 0.8)'}
                        )
                    ], className="builder-field"),
                    html.Div([
                        html.Label("Enable Auto-Refresh:", className="builder-label"),
                        dcc.Checklist(
                            id="auto-refresh-enable",
                            options=[{'label': 'Enable', 'value': 'enabled'}],
                            value=['enabled'],
                            style={'color': '#F8FAFC', 'marginTop': '8px'}
                        )
                    ], className="builder-field")
                ], className="builder-grid")
            ], className="builder-section"),
            
            # Display Settings
            html.Div([
                html.H3([
                    html.I(className="fas fa-chart-bar", style={'marginRight': '8px'}),
                    "Display Configuration"
                ], className="builder-section-title"),
                html.Div([
                    html.Div([
                        html.Label("Default Facility:", className="builder-label"),
                        dcc.Dropdown(
                            id="default-facility-select",
                            options=[{'label': 'All Facilities', 'value': 'ALL'}] + [{'label': f, 'value': f} for f in FACILITIES],
                            value='ALL',
                            className="builder-select"
                        )
                    ], className="builder-field"),
                    html.Div([
                        html.Label("Default Time Range:", className="builder-label"),
                        dcc.Dropdown(
                            id="default-timerange-select",
                            options=[
                                {'label': 'Last 7 days', 'value': 7},
                                {'label': 'Last 30 days', 'value': 30},
                                {'label': 'Last 90 days', 'value': 90},
                                {'label': 'Last 6 months', 'value': 180},
                                {'label': 'Last year', 'value': 365}
                            ],
                            value=30,
                            className="builder-select"
                        )
                    ], className="builder-field"),
                    html.Div([
                        html.Label("Chart Animation:", className="builder-label"),
                        dcc.Checklist(
                            id="chart-animation-enable",
                            options=[{'label': 'Enable Animations', 'value': 'enabled'}],
                            value=['enabled'],
                            style={'color': '#F8FAFC', 'marginTop': '8px'}
                        )
                    ], className="builder-field")
                ], className="builder-grid")
            ], className="builder-section"),
            
            # Data Settings
            html.Div([
                html.H3([
                    html.I(className="fas fa-database", style={'marginRight': '8px'}),
                    "Data Configuration"
                ], className="builder-section-title"),
                html.Div([
                    html.Div([
                        html.Label("Records Per Page:", className="builder-label"),
                        dcc.Dropdown(
                            id="records-per-page-select",
                            options=[
                                {'label': '10 records', 'value': 10},
                                {'label': '25 records', 'value': 25},
                                {'label': '50 records', 'value': 50},
                                {'label': '100 records', 'value': 100}
                            ],
                            value=25,
                            className="builder-select"
                        )
                    ], className="builder-field"),
                    html.Div([
                        html.Label("Max Customers in Charts:", className="builder-label"),
                        dcc.Dropdown(
                            id="max-customers-select",
                            options=[
                                {'label': '10 customers', 'value': 10},
                                {'label': '15 customers', 'value': 15},
                                {'label': '20 customers', 'value': 20},
                                {'label': 'All customers', 'value': 999}
                            ],
                            value=15,
                            className="builder-select"
                        )
                    ], className="builder-field")
                ], className="builder-grid")
            ], className="builder-section"),
            
            # Apply Configuration Button
            html.Button([
                html.I(className="fas fa-check", style={'marginRight': '8px'}),
                "Apply Configuration"
            ], id="apply-config-btn", className="apply-config-btn")
            
        ], className="modal-content")
    ], id="dashboard-modal", className="modal-overlay modal-hidden"),
    
    # Dynamic facility header
    html.Div(id='facility-header-container'),
    
    # Control Panel
    html.Div([
        html.Div([
            html.Div([
                html.Label("Facility:", className='control-label'),
                dcc.Dropdown(
                    id='facility-selector',
                    options=[{'label': 'All Facilities', 'value': 'ALL'}] + [{'label': f, 'value': f} for f in FACILITIES],
                    value='ALL',
                    style={'width': '180px'},
                    className='enhanced-dropdown'
                )
            ], className='control-group'),
            
            html.Div([
                html.Label("Time Range:", className='control-label'),
                dcc.Dropdown(
                    id='timerange-selector',
                    options=[
                        {'label': 'Last 7 days', 'value': 7},
                        {'label': 'Last 30 days', 'value': 30},
                        {'label': 'Last 90 days', 'value': 90},
                        {'label': 'Last 6 months', 'value': 180},
                        {'label': 'Last year', 'value': 365}
                    ],
                    value=30,
                    style={'width': '180px'},
                    className='enhanced-dropdown'
                )
            ], className='control-group'),
            
            html.Div([
                html.Label("Auto Refresh:", className='control-label'),
                dcc.Interval(id='main-interval', interval=30000, n_intervals=0),
                html.Div([
                    html.I(className='fas fa-sync-alt', style={'color': '#60A5FA', 'marginRight': '8px'}),
                    html.Span(id='refresh-status', children="30s", style={'color': '#CBD5E1', 'fontWeight': '600'})
                ])
            ], className='control-group')
        ])
    ], className='control-panel'),
    
    # Customer Analysis Section
    html.Div([
        html.H2([
            html.I(className='fas fa-users', style={'marginRight': '16px'}),
            "Customer Analytics"
        ], className='section-title'),
        
        # Data range information
        html.Div(id='data-range-info'),
        
        # Export buttons section
        html.Div([
            html.H4("📊 Export Options", style={'color': '#60A5FA', 'marginBottom': '16px'}),
            html.Button([
                html.I(className='fas fa-file-pdf', style={'marginRight': '8px'}),
                "Download PDF Report"
            ], id='download-pdf-btn', className='export-btn'),
            html.Button([
                html.I(className='fas fa-file-excel', style={'marginRight': '8px'}),
                "Download Excel Data"
            ], id='download-excel-btn', className='export-btn'),
            
            # Download components (invisible but functional)
            dcc.Download(id="download-pdf"),
            dcc.Download(id="download-excel"),
            
            # Status messages
            html.Div(id='download-status', style={'marginTop': '12px'})
        ], className='export-section'),
        
        # Charts
        html.Div([
            html.Div([
                dcc.Graph(id='customer-bar-chart')
            ], className='chart-container', style={'width': '48%', 'display': 'inline-block', 'margin': '1%'}),
            
            html.Div([
                dcc.Graph(id='customer-pie-chart')
            ], className='chart-container', style={'width': '48%', 'display': 'inline-block', 'margin': '1%'})
        ]),
        
        # Trends Chart
        html.Div([
            dcc.Graph(id='trends-chart')
        ], className='chart-container')
    ], className='premium-card'),
# --- Daily measurements by factory (grouped columns) ---
html.Div([
    html.Div([
        html.I(className='fas fa-chart-bar', style={'marginRight': '8px'}),
        html.Span('Daily measurements by factory', style={'fontWeight': '600'})
    ], className='card-title'),
    dcc.Graph(id='daily-by-factory-chart', config={'displaylogo': False})
], className='premium-card'),

    
    # Data Table Section
    html.Div([
        html.H2([
            html.I(className='fas fa-table', style={'marginRight': '16px'}),
            "Customer Data"
        ], className='section-title'),
        
        html.Div([
            dash_table.DataTable(
                id='customer-table',
                columns=[],
                data=[],
                style_cell={
                    'textAlign': 'left',
                    'padding': '16px 20px',
                    'backgroundColor': 'rgba(30, 41, 59, 0.6)',
                    'color': '#F8FAFC',
                    'border': '1px solid rgba(59, 130, 246, 0.3)',
                    'fontFamily': 'Inter',
                    'fontSize': '14px',
                    'fontWeight': '500'
                },
                style_header={
                    'backgroundColor': 'rgba(30, 58, 138, 0.8)',
                    'color': '#F8FAFC',
                    'fontWeight': 'bold',
                    'fontSize': '16px',
                    'border': '1px solid rgba(96, 165, 250, 0.4)',
                    'textAlign': 'center',
                    'padding': '20px 16px'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgba(30, 41, 59, 0.4)'
                    },
                    {
                        'if': {'row_index': 'even'},
                        'backgroundColor': 'rgba(30, 41, 59, 0.6)'
                    }
                ],
                page_size=25,
                sort_action="native",
                filter_action="native",
                fixed_rows={'headers': True},
                style_table={
                    'maxHeight': '600px',
                    'overflowY': 'auto',
                    'border': '1px solid rgba(59, 130, 246, 0.3)',
                    'borderRadius': '12px'
                }
            )
        ], className='data-table')
    ], className='premium-card'),
    
    # Data stores
    dcc.Store(id='dashboard-data', data={}),
    dcc.Store(id='dashboard-config', data={
        'refresh_interval': 30000,
        'auto_refresh_enabled': True,
        'default_facility': 'ALL',
        'default_timerange': 30,
        'chart_animation': True,
        'records_per_page': 25,
        'max_customers': 15
    }),
    
], style={'padding': '0', 'margin': '0', 'minHeight': '100vh'}, className='fade-in')

# Modal show/hide callbacks
@app.callback(
    Output('dashboard-modal', 'className'),
    [Input('dashboard-builder-btn', 'n_clicks'),
     Input('close-modal-btn', 'n_clicks'),
     Input('apply-config-btn', 'n_clicks')],
    prevent_initial_call=True
)
def toggle_modal(builder_clicks, close_clicks, apply_clicks):
    triggered = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if triggered == 'dashboard-builder-btn':
        return 'modal-overlay'
    elif triggered in ['close-modal-btn', 'apply-config-btn']:
        return 'modal-overlay modal-hidden'
    
    return 'modal-overlay modal-hidden'

# Configuration update callback
@app.callback(
    [Output('dashboard-config', 'data'),
     Output('main-interval', 'interval'),
     Output('main-interval', 'disabled'),
     Output('facility-selector', 'value'),
     Output('timerange-selector', 'value'),
     Output('customer-table', 'page_size'),
     Output('refresh-status', 'children')],
    Input('apply-config-btn', 'n_clicks'),
    [State('refresh-interval-select', 'value'),
     State('auto-refresh-enable', 'value'),
     State('default-facility-select', 'value'),
     State('default-timerange-select', 'value'),
     State('chart-animation-enable', 'value'),
     State('records-per-page-select', 'value'),
     State('max-customers-select', 'value')],
    prevent_initial_call=True
)
def update_dashboard_config(n_clicks, refresh_interval, auto_refresh, default_facility, 
                          default_timerange, chart_animation, records_per_page, max_customers):
    if n_clicks:
        auto_refresh_enabled = 'enabled' in (auto_refresh or [])
        chart_animation_enabled = 'enabled' in (chart_animation or [])
        
        config = {
            'refresh_interval': refresh_interval,
            'auto_refresh_enabled': auto_refresh_enabled,
            'default_facility': default_facility,
            'default_timerange': default_timerange,
            'chart_animation': chart_animation_enabled,
            'records_per_page': records_per_page,
            'max_customers': max_customers
        }
        
        # Format refresh status
        if refresh_interval == 0 or not auto_refresh_enabled:
            refresh_status = "Disabled"
            interval_disabled = True
        else:
            if refresh_interval < 60000:
                refresh_status = f"{refresh_interval//1000}s"
            else:
                refresh_status = f"{refresh_interval//60000}m"
            interval_disabled = False
        
        return (config, refresh_interval, interval_disabled, default_facility, 
                default_timerange, records_per_page, refresh_status)
    
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

# Dynamic facility header
@app.callback(
    Output('facility-header-container', 'children'),
    Input('facility-selector', 'value')
)
def update_facility_header(selected_facility):
    if selected_facility == 'ALL':
        header_text = "PLASMAN AB - Customer Dashboard"
        subtitle = "All Facilities Customer Analysis"
    else:
        header_text = f"PLASMAN AB - {selected_facility}"
        subtitle = f"Facility {selected_facility} Customer Analysis"
    
    return html.Div([
        html.Div([
            html.I(className='fas fa-industry', style={'fontSize': '32px', 'marginRight': '16px', 'color': '#F8FAFC'}),
            html.Div([
                html.H1(header_text, className='facility-header'),
                html.P(subtitle, style={
                    'fontSize': '1.1rem', 
                    'margin': '0', 
                    'color': 'rgba(248, 250, 252, 0.8)',
                    'fontWeight': '500',
                    'textAlign': 'center'
                })
            ])
        ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'})
    ], className='header-gradient', style={'padding': '24px 32px', 'marginBottom': '32px'})

# Main dashboard callback with configuration support
@app.callback([
    Output('customer-bar-chart', 'figure'),
    Output('customer-pie-chart', 'figure'),
    Output('trends-chart', 'figure'),
    Output('daily-by-factory-chart', 'figure'),
     Output('customer-table', 'columns'),
     Output('customer-table', 'data'),
     Output('dashboard-data', 'data'),
     Output('data-range-info', 'children')],
    [Input('main-interval', 'n_intervals'),
     Input('facility-selector', 'value'),
     Input('timerange-selector', 'value')],
    State('dashboard-config', 'data')
)
def update_dashboard(n_intervals, selected_facility, timerange, config):
    try:
        # Get configuration values
        max_customers = config.get('max_customers', 15)
        chart_animation = config.get('chart_animation', True)
        
        # Calculate date range
        end_date = datetime.date.today()
        start_date = end_date - timedelta(days=timerange)
        
        # Build facility filter
        if selected_facility == 'ALL':
            facility_filter = "r.R_FilterA IN ('PASI', 'PAGE', 'PAGO')"
            facility_params = {}
        else:
            facility_filter = "r.R_FilterA = :facility"
            facility_params = {'facility': selected_facility}
        
        # Main query for customer data with better date handling
        main_query = text(f"""
        SELECT 
            r.R_FilterB AS Customer,
            r.R_FilterA AS Facility,
            CAST(s.S_CreateDate AS DATE) as measurement_date,
            COUNT(DISTINCT s.S_ID) AS measurement_count,
            MAX(s.S_CreateDate) as latest_measurement,
            MIN(s.S_CreateDate) as earliest_measurement,
            COUNT(DISTINCT r.R_ID) as routine_count
        FROM Routine r
        JOIN Sample s ON s.S_R_ID = r.R_ID
        WHERE {facility_filter}
          AND s.S_CreateDate >= :start_date
          AND s.S_CreateDate <= :end_date
          AND r.R_FilterB IS NOT NULL 
          AND r.R_FilterB <> ''
        GROUP BY r.R_FilterB, r.R_FilterA, CAST(s.S_CreateDate AS DATE)
        ORDER BY measurement_date DESC, Customer, Facility
        """)
        
        params = {
            'start_date': start_date.strftime("%Y-%m-%d"),
            'end_date': end_date.strftime("%Y-%m-%d"),
            **facility_params
        }
        
        df = pd.read_sql_query(main_query, engine, params=params)
        
        # Create data range info
        facility_text = selected_facility if selected_facility != 'ALL' else 'All Facilities'
        data_range_info = html.Div([
            html.I(className='fas fa-calendar-alt', style={'marginRight': '8px'}),
            f"📅 Data Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} | ",
            html.I(className='fas fa-building', style={'marginLeft': '16px', 'marginRight': '8px'}),
            f"🏭 Facility: {facility_text} | ",
            html.I(className='fas fa-clock', style={'marginLeft': '16px', 'marginRight': '8px'}),
            f"⏱️ Period: {timerange} days"
        ], className='data-range-info')
        
        if not df.empty:
            # Customer Bar Chart
            customer_data = df.groupby('Customer')['measurement_count'].sum().reset_index()
            # Apply max customers limit from configuration
            customer_data = customer_data.sort_values('measurement_count', ascending=False).head(max_customers)
            
            colors = [CHART_PALETTES['customer'].get(customer, CHART_PALETTES['main'][i % len(CHART_PALETTES['main'])]) 
                     for i, customer in enumerate(customer_data['Customer'])]
            
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                x=customer_data['Customer'],
                y=customer_data['measurement_count'],
                marker=dict(color=colors, line=dict(color='rgba(96, 165, 250, 0.8)', width=2)),
                text=customer_data['measurement_count'],
                textposition='outside',
                textfont=dict(size=14, color='#F8FAFC', family='Inter'),
                hovertemplate='<b>%{x}</b><br>Measurements: %{y:,}<br><extra></extra>'
            ))
            
            fig_bar.update_layout(colorway=COLORWAY, 
                title=dict(text=f'<b>Top {max_customers} Customer Measurements</b> ({timerange}d)', x=0.5, 
                          font=dict(size=18, color='#60A5FA', family='Inter')),
                xaxis=dict(title='Customer', color='#CBD5E1', tickangle=45, 
                          tickfont=dict(size=11, color='#F8FAFC')),
                yaxis=dict(title='Measurements', color='#CBD5E1', 
                          tickfont=dict(size=12, color='#F8FAFC')),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#F8FAFC', family='Inter'),
                margin=dict(t=80, b=100, l=60, r=40),
                height=450,
                transition=dict(duration=500 if chart_animation else 0)
            )
            
            # Customer Pie Chart
            pie_data = customer_data.head(10)
            fig_pie = go.Figure()
            fig_pie.add_trace(go.Pie(
                labels=pie_data['Customer'],
                values=pie_data['measurement_count'],
                hole=0.5,
                marker=dict(colors=colors[:len(pie_data)], 
                           line=dict(color='rgba(248, 250, 252, 0.8)', width=3)),
                textinfo='label+percent',
                textposition='outside',
                textfont=dict(size=12, color='#F8FAFC', family='Inter'),
                hovertemplate='<b>%{label}</b><br>Count: %{value:,}<br>Share: %{percent}<extra></extra>'
            ))
            
            fig_pie.update_layout(colorway=COLORWAY, 
                title=dict(text=f'<b>Customer Distribution</b> ({timerange}d)', x=0.5,
                          font=dict(size=18, color='#60A5FA', family='Inter')),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#F8FAFC', family='Inter'),
                margin=dict(t=80, b=40, l=40, r=40),
                height=450,
                transition=dict(duration=500 if chart_animation else 0)
            )
            
            # Trends Chart - Enhanced for better visibility of all dates
            daily_trend = df.groupby('measurement_date').agg({
                'measurement_count': 'sum',
                'Customer': 'nunique'
            }).reset_index()
            daily_trend = daily_trend.sort_values('measurement_date')
            
            # Convert measurement_date to datetime if it isn't already
            daily_trend['measurement_date'] = pd.to_datetime(daily_trend['measurement_date'])
            
            # Fill in missing dates to show complete timeline
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            date_df = pd.DataFrame({'measurement_date': date_range})
            daily_trend = date_df.merge(daily_trend, on='measurement_date', how='left').fillna(0)
            
            fig_trend = make_subplots(specs=[[{"secondary_y": True}]])
            
            fig_trend.add_trace(
                go.Scatter(
                    x=daily_trend['measurement_date'],
                    y=daily_trend['measurement_count'],
                    mode='lines+markers',
                    name='Daily Measurements',
                    line=dict(color='#60A5FA', width=4),
                    marker=dict(color='#93C5FD', size=8),
                    fill='tonexty',
                    fillcolor='rgba(96, 165, 250, 0.2)',
                    hovertemplate='<b>Date:</b> %{x}<br><b>Measurements:</b> %{y:,}<extra></extra>'
                ),
                secondary_y=False
            )
            
            fig_trend.add_trace(
                go.Scatter(
                    x=daily_trend['measurement_date'],
                    y=daily_trend['Customer'],
                    mode='lines+markers',
                    name='Unique Customers',
                    line=dict(color='#DBEAFE', width=3, dash='dot'),
                    marker=dict(color='#1D4ED8', size=6),
                    hovertemplate='<b>Date:</b> %{x}<br><b>Customers:</b> %{y}<extra></extra>'
                ),
                secondary_y=True
            )
            
            fig_trend.update_layout(colorway=COLORWAY, 
                title=dict(text=f'<b>Customer Activity Trends</b> ({timerange}d)', x=0.5,
                          font=dict(size=18, color='#60A5FA', family='Inter')),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#F8FAFC', family='Inter'),
                margin=dict(t=80, b=60, l=60, r=60),
                height=400,
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    bgcolor='rgba(30, 41, 59, 0.8)',
                    bordercolor='rgba(59, 130, 246, 0.3)',
                    borderwidth=1
                ),
                transition=dict(duration=500 if chart_animation else 0)
            )
            
            fig_trend.update_xaxes(
                title_text="Date", 
                color='#CBD5E1',
                showgrid=True,
                gridcolor='rgba(59, 130, 246, 0.2)'
            )
            fig_trend.update_yaxes(
                title_text="Daily Measurements", 
                color='#CBD5E1',
                secondary_y=False,
                showgrid=True,
                gridcolor='rgba(59, 130, 246, 0.1)'
            )
            fig_trend.update_yaxes(
                title_text="Unique Customers", 
                color='#CBD5E1', 
                secondary_y=True
            )
            
            # Enhanced Table data with better organization
            table_data = df.groupby(['Facility', 'Customer', 'measurement_date']).agg({
                'measurement_count': 'sum',
                'routine_count': 'sum',
                'latest_measurement': 'max'
            }).reset_index()
            
            # Add summary row for each customer
            customer_summary = df.groupby(['Facility', 'Customer']).agg({
                'measurement_count': 'sum',
                'routine_count': 'sum',
                'latest_measurement': 'max',
                'measurement_date': 'count'  # Number of active days
            }).reset_index()
            
            customer_summary = customer_summary.rename(columns={'measurement_date': 'active_days'})
            customer_summary['measurement_date'] = 'TOTAL'
            customer_summary = customer_summary.sort_values('measurement_count', ascending=False)
            
            # Format the latest measurement datetime
            table_data['latest_measurement'] = table_data['latest_measurement'].dt.strftime('%Y-%m-%d %H:%M')
            customer_summary['latest_measurement'] = customer_summary['latest_measurement'].dt.strftime('%Y-%m-%d %H:%M')
            
            # Combine detailed and summary data
            table_data['measurement_date'] = table_data['measurement_date'].astype(str)
            table_data['active_days'] = 1  # Each row represents one active day
            
            # Reorder columns for better display
            detailed_data = table_data[['Facility', 'Customer', 'measurement_date', 'measurement_count', 'routine_count', 'latest_measurement']].copy()
            summary_data = customer_summary[['Facility', 'Customer', 'measurement_date', 'measurement_count', 'routine_count', 'latest_measurement']].copy()
            
            # Combine and sort
            combined_data = pd.concat([summary_data, detailed_data], ignore_index=True)
            combined_data = combined_data.sort_values(['Customer', 'measurement_date'])
            
            columns = [
                {'name': 'Facility', 'id': 'Facility'},
                {'name': 'Customer', 'id': 'Customer'},
                {'name': 'Date', 'id': 'measurement_date'},
                {'name': 'Measurements', 'id': 'measurement_count', 'type': 'numeric'},
                {'name': 'Routines', 'id': 'routine_count', 'type': 'numeric'},
                {'name': 'Latest Activity', 'id': 'latest_measurement'}
            ]
            
            data = combined_data.to_dict('records')
            
            # Store data for exports
            dashboard_data = {
                'raw_data': df.to_dict('records'),
                'customer_summary': customer_data.to_dict('records'),
                'daily_trends': daily_trend.to_dict('records'),
                'table_data': combined_data.to_dict('records'),
                'timerange': timerange,
                'facility': selected_facility,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'total_records': len(df),
                'unique_customers': df['Customer'].nunique(),
                'last_update': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        else:
            # Empty figures
            fig_bar = go.Figure()
            fig_bar.update_layout(
                title="No Data Available for Selected Period", 
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#F8FAFC', family='Inter')
            )
            
            fig_pie = go.Figure()
            fig_pie.update_layout(
                title="No Data Available for Selected Period", 
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#F8FAFC', family='Inter')
            )
            
            fig_trend = go.Figure()
            fig_trend.update_layout(
                title="No Data Available for Selected Period", 
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#F8FAFC', family='Inter')
            )
            
            columns = []
            data = []
            dashboard_data = {
                'timerange': timerange,
                'facility': selected_facility,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'total_records': 0,
                'unique_customers': 0
            }
            
            # Update data range info for no data
            data_range_info = html.Div([
                html.I(className='fas fa-exclamation-triangle', style={'marginRight': '8px', 'color': '#FFA500'}),
                f"⚠️ No data found for period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} | ",
                html.I(className='fas fa-building', style={'marginLeft': '16px', 'marginRight': '8px'}),
                f"🏭 Facility: {facility_text}"
            ], className='data-range-info', style={'backgroundColor': 'rgba(255, 165, 0, 0.1)', 'borderColor': 'rgba(255, 165, 0, 0.3)', 'color': '#FFA500'})
        

        # ---- Build daily-by-factory chart from aggregated df ----
        try:
            if not df.empty:
                df_daily = df.groupby(['measurement_date','Facility'], as_index=False)['measurement_count'].sum()
                df_daily = df_daily.sort_values('measurement_date')
                daily_by_factory_fig = px.bar(
                    df_daily, x='measurement_date', y='measurement_count',
                    color='Facility', barmode='group', title='Daily measurements by factory'
                )
                daily_by_factory_fig.update_layout(colorway=COLORWAY, legend_title_text='Facility')
            else:
                daily_by_factory_fig = go.Figure()
                daily_by_factory_fig.add_annotation(text='No data in selected range', showarrow=False, y=0.5)
        except Exception as _e_daily:
            daily_by_factory_fig = go.Figure()
            daily_by_factory_fig.add_annotation(text=f'Error building daily chart: {_e_daily}', showarrow=False, y=0.5)

        return fig_bar, fig_pie, fig_trend, daily_by_factory_fig, columns, data, dashboard_data, data_range_info
        
    except Exception as e:
        logging.error(f"Error updating dashboard: {e}")
        
        # Error figures
        error_fig = go.Figure()
        error_fig.update_layout(
            title=f"Database Error: {str(e)[:50]}...",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#F8FAFC')
        )
        
        error_info = html.Div([
            html.I(className='fas fa-exclamation-circle', style={'marginRight': '8px', 'color': '#EF4444'}),
            f"❌ Database Error: {str(e)[:100]}..."
        ], className='data-range-info', style={'backgroundColor': 'rgba(239, 68, 68, 0.1)', 'borderColor': 'rgba(239, 68, 68, 0.3)', 'color': '#EF4444'})
        
        return error_fig, error_fig, error_fig, error_fig, [], [], {}, error_info

# PDF Report Generation
def generate_pdf_report(dashboard_data, facility, timerange):
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1E3A8A'),
            alignment=1  # Center alignment
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.HexColor('#3B82F6')
        )
        
        # Title
        story.append(Paragraph("PLASMAN AB - Customer Analysis Report", title_style))
        story.append(Spacer(1, 12))
        
        # Report info
        facility_text = facility if facility != 'ALL' else 'All Facilities'
        story.append(Paragraph(f"<b>Facility:</b> {facility_text}", styles['Normal']))
        story.append(Paragraph(f"<b>Time Period:</b> Last {timerange} days", styles['Normal']))
        story.append(Paragraph(f"<b>Date Range:</b> {dashboard_data.get('start_date', 'N/A')} to {dashboard_data.get('end_date', 'N/A')}", styles['Normal']))
        story.append(Paragraph(f"<b>Generated:</b> {dashboard_data.get('last_update', 'N/A')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Customer Summary
        if dashboard_data.get('customer_summary'):
            story.append(Paragraph("Customer Measurement Summary", heading_style))
            
            # Create table data
            table_data = [['Customer', 'Total Measurements']]
            for customer in dashboard_data['customer_summary'][:10]:
                table_data.append([customer['Customer'], str(customer['measurement_count'])])
            
            # Create table
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#3B82F6'))
            ]))
            
            story.append(table)
            story.append(Spacer(1, 20))
        
        # Summary statistics
        story.append(Paragraph("Key Metrics", heading_style))
        story.append(Paragraph(f"<b>Total Records:</b> {dashboard_data.get('total_records', 0):,}", styles['Normal']))
        story.append(Paragraph(f"<b>Unique Customers:</b> {dashboard_data.get('unique_customers', 0)}", styles['Normal']))
        story.append(Paragraph(f"<b>Analysis Period:</b> {timerange} days", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer.getvalue()
        
    except Exception as e:
        logging.error(f"Error generating PDF: {e}")
        return None

# Excel Report Generation
def generate_excel_report(dashboard_data):
    try:
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Customer summary sheet
            if dashboard_data.get('customer_summary'):
                customer_df = pd.DataFrame(dashboard_data['customer_summary'])
                customer_df.to_excel(writer, sheet_name='Customer_Summary', index=False)
            
            # Daily trends sheet
            if dashboard_data.get('daily_trends'):
                trends_df = pd.DataFrame(dashboard_data['daily_trends'])
                trends_df.to_excel(writer, sheet_name='Daily_Trends', index=False)
            
            # Detailed data sheet
            if dashboard_data.get('table_data'):
                table_df = pd.DataFrame(dashboard_data['table_data'])
                table_df.to_excel(writer, sheet_name='Detailed_Data', index=False)
            
            # Raw data sheet
            if dashboard_data.get('raw_data'):
                raw_df = pd.DataFrame(dashboard_data['raw_data'])
                raw_df.to_excel(writer, sheet_name='Raw_Data', index=False)
        
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        logging.error(f"Error generating Excel: {e}")
        return None

# PDF Download Callback
@app.callback(
    [Output("download-pdf", "data"),
     Output("download-status", "children")],
    Input("download-pdf-btn", "n_clicks"),
    [State('dashboard-data', 'data'),
     State('facility-selector', 'value'),
     State('timerange-selector', 'value')],
    prevent_initial_call=True
)
def download_pdf_report(n_clicks, dashboard_data, facility, timerange):
    if not dashboard_data:
        return dash.no_update, html.Div(
            "❌ No data available for export", 
            className='download-success',
            style={'backgroundColor': 'rgba(239, 68, 68, 0.2)', 'borderColor': 'rgba(239, 68, 68, 0.4)', 'color': '#EF4444'}
        )
    
    try:
        pdf_data = generate_pdf_report(dashboard_data, facility, timerange)
        if pdf_data:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"plasman_report_{facility}_{timestamp}.pdf"
            
            return dcc.send_bytes(pdf_data, filename), html.Div([
                html.I(className='fas fa-check-circle', style={'marginRight': '8px'}),
                f"✅ PDF Report downloaded successfully!"
            ], className='download-success')
        else:
            return dash.no_update, html.Div(
                "❌ Error generating PDF report", 
                className='download-success',
                style={'backgroundColor': 'rgba(239, 68, 68, 0.2)', 'borderColor': 'rgba(239, 68, 68, 0.4)', 'color': '#EF4444'}
            )
    except Exception as e:
        logging.error(f"PDF download error: {e}")
        return dash.no_update, html.Div(
            f"❌ Error: {str(e)[:50]}...", 
            className='download-success',
            style={'backgroundColor': 'rgba(239, 68, 68, 0.2)', 'borderColor': 'rgba(239, 68, 68, 0.4)', 'color': '#EF4444'}
        )

# Excel Download Callback
@app.callback(
    [Output("download-excel", "data"),
     Output("download-status", "children", allow_duplicate=True)],
    Input("download-excel-btn", "n_clicks"),
    State('dashboard-data', 'data'),
    State('facility-selector', 'value'),
    prevent_initial_call=True
)
def download_excel_report(n_clicks, dashboard_data, facility):
    if not dashboard_data:
        return dash.no_update, html.Div(
            "❌ No data available for export", 
            className='download-success',
            style={'backgroundColor': 'rgba(239, 68, 68, 0.2)', 'borderColor': 'rgba(239, 68, 68, 0.4)', 'color': '#EF4444'}
        )
    
    try:
        excel_data = generate_excel_report(dashboard_data)
        if excel_data:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"plasman_data_{facility}_{timestamp}.xlsx"
            
            return dcc.send_bytes(excel_data, filename), html.Div([
                html.I(className='fas fa-check-circle', style={'marginRight': '8px'}),
                "✅ Excel file downloaded successfully!"
            ], className='download-success')
        else:
            return dash.no_update, html.Div(
                "❌ Error generating Excel file", 
                className='download-success',
                style={'backgroundColor': 'rgba(239, 68, 68, 0.2)', 'borderColor': 'rgba(239, 68, 68, 0.4)', 'color': '#EF4444'}
            )
    except Exception as e:
        logging.error(f"Excel download error: {e}")
        return dash.no_update, html.Div(
            f"❌ Error: {str(e)[:50]}...", 
            className='download-success',
            style={'backgroundColor': 'rgba(239, 68, 68, 0.2)', 'borderColor': 'rgba(239, 68, 68, 0.4)', 'color': '#EF4444'}
        )

if __name__ == '__main__':
     print("🚀 Starting ENHANCED PLASMAN AB Customer Dashboard...") 
    port = int(os.environ.get('PORT', 8050))  # Use PORT from environment, fallback to 8050
    print(f"🌐 Access at: http://0.0.0.0:{port}")
    # ... your other print statements ...

    app.run(debug=False, host='0.0.0.0', port=port)