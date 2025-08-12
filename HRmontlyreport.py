from flask import Flask, render_template_string, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import sys
import subprocess
from datetime import datetime
import json
import socket
import tempfile
import shutil
import logging

# Configure logging for Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Auto-install required packages
def install_package(package):
    try:
        __import__(package.split('==')[0] if '==' in package else package)
        logger.info(f"Package {package} already installed")
    except ImportError:
        try:
            logger.info(f"Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '--no-cache-dir'])
            logger.info(f"Successfully installed {package}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install {package}: {e}")

# Install required packages
packages = [
    'flask',
    'pandas',
    'openpyxl', 
    'reportlab',
    'matplotlib',
    'numpy'
]

logger.info("Installing required packages...")
for package in packages:
    install_package(package)

try:
    import pandas as pd
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')  # Use non-GUI backend for Render
    import matplotlib.pyplot as plt
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    import io
    logger.info("All modules imported successfully")
except ImportError as e:
    logger.error(f"Error importing required modules: {e}")
    sys.exit(1)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB for Render

# Use /tmp for Render (ephemeral storage)
TEMP_BASE = '/tmp'

# Create directories
UPLOAD_DIR = os.path.join(TEMP_BASE, 'uploads')
OUTPUT_DIR = os.path.join(TEMP_BASE, 'output')
CHART_DIR = os.path.join(TEMP_BASE, 'charts')

# Ensure directories exist
for directory in [UPLOAD_DIR, OUTPUT_DIR, CHART_DIR]:
    try:
        os.makedirs(directory, mode=0o755, exist_ok=True)
        logger.info(f"Directory {directory} created")
    except Exception as e:
        logger.error(f"Failed to create {directory}: {e}")

app.config['UPLOAD_FOLDER'] = UPLOAD_DIR
app.config['OUTPUT_FOLDER'] = OUTPUT_DIR
app.config['TEMP_FOLDER'] = CHART_DIR

# Global variables
uploaded_files = []
report_data = {}

def detect_column_type(series, column_name):
    """Simple column type detection"""
    try:
        clean_series = series.dropna()
        if len(clean_series) == 0:
            return 'empty'
        
        column_name_lower = str(column_name).lower().strip()
        
        # Check for date columns
        if any(keyword in column_name_lower for keyword in ['date', 'time', 'birth', 'hire']):
            try:
                pd.to_datetime(clean_series.head(5), errors='raise')
                return 'date'
            except:
                pass
        
        # Check if numeric
        if pd.api.types.is_numeric_dtype(clean_series):
            return 'numeric'
        
        # Check for categorical data
        unique_values = len(clean_series.unique())
        total_values = len(clean_series)
        
        if unique_values <= 15 or (unique_values / total_values) < 0.5:
            return 'categorical'
        
        return 'text'
    except Exception:
        return 'text'

def analyze_excel_data(dataframes):
    """Analyze Excel data with error handling"""
    analysis = {
        'summary': {},
        'data_overview': [],
        'charts_data': {
            'numeric': {},
            'categorical': {},
            'dates': {}
        },
        'insights': []
    }
    
    try:
        total_rows = 0
        total_files = len(dataframes)
        
        for filename, sheets in dataframes.items():
            file_summary = {
                'filename': filename,
                'sheets': {},
                'total_rows': 0,
                'total_columns': 0
            }
            
            for sheet_name, df in sheets.items():
                if df.empty:
                    continue
                
                rows, cols = df.shape
                total_rows += rows
                file_summary['sheets'][sheet_name] = {
                    'rows': rows,
                    'columns': cols,
                    'column_names': list(df.columns)
                }
                file_summary['total_rows'] += rows
                file_summary['total_columns'] = max(file_summary['total_columns'], cols)
                
                # Analyze columns (limit to first 10 for performance)
                for col in list(df.columns)[:10]:
                    try:
                        col_clean = str(col).strip()
                        col_type = detect_column_type(df[col], col)
                        
                        if col_type == 'numeric':
                            numeric_data = pd.to_numeric(df[col], errors='coerce').dropna()
                            if len(numeric_data) > 0:
                                if col_clean not in analysis['charts_data']['numeric']:
                                    analysis['charts_data']['numeric'][col_clean] = []
                                analysis['charts_data']['numeric'][col_clean].extend(numeric_data.head(1000).tolist())
                        
                        elif col_type == 'categorical':
                            value_counts = df[col].value_counts().head(10)  # Limit categories
                            if col_clean not in analysis['charts_data']['categorical']:
                                analysis['charts_data']['categorical'][col_clean] = {}
                            
                            for value, count in value_counts.items():
                                if pd.notna(value):
                                    key = str(value).strip()
                                    analysis['charts_data']['categorical'][col_clean][key] = \
                                        analysis['charts_data']['categorical'][col_clean].get(key, 0) + count
                    except Exception as e:
                        logger.warning(f"Error analyzing column {col}: {e}")
                        continue
            
            analysis['data_overview'].append(file_summary)
        
        # Generate summary
        analysis['summary'] = {
            'total_files': total_files,
            'total_rows': total_rows,
            'total_columns': sum(len(f['sheets']) for f in analysis['data_overview']),
            'numeric_columns': len(analysis['charts_data']['numeric']),
            'categorical_columns': len(analysis['charts_data']['categorical']),
            'date_columns': 0
        }
        
        # Generate insights
        insights = [
            f"📊 Analyzed {total_files} Excel files with {total_rows:,} records",
            f"📈 Found {len(analysis['charts_data']['numeric'])} numeric columns",
            f"📋 Found {len(analysis['charts_data']['categorical'])} categorical columns"
        ]
        
        analysis['insights'] = insights
        return analysis
    
    except Exception as e:
        logger.error(f"Error in analyze_excel_data: {e}")
        return {
            'summary': {'total_files': 0, 'total_rows': 0, 'total_columns': 0, 'numeric_columns': 0, 'categorical_columns': 0, 'date_columns': 0},
            'data_overview': [],
            'charts_data': {'numeric': {}, 'categorical': {}, 'dates': {}},
            'insights': ["Error occurred during analysis"]
        }

def create_simple_chart(chart_type, data, title, filename, column_name=""):
    """Create simple charts for Render"""
    try:
        plt.close('all')
        plt.style.use('default')
        
        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor('white')
        
        if chart_type == 'categorical_bar' and isinstance(data, dict):
            # Limit to top 8 categories
            sorted_data = dict(sorted(data.items(), key=lambda x: x[1], reverse=True)[:8])
            
            bars = ax.bar(range(len(sorted_data)), sorted_data.values(), color='#1976D2', alpha=0.7)
            ax.set_xticks(range(len(sorted_data)))
            ax.set_xticklabels(sorted_data.keys(), rotation=45, ha='right')
            ax.set_ylabel('Count')
            ax.set_title(title)
            
        elif chart_type == 'numeric_histogram' and isinstance(data, list):
            # Limit data size
            if len(data) > 5000:
                data = data[:5000]
            
            ax.hist(data, bins=15, color='#1976D2', alpha=0.7, edgecolor='white')
            ax.set_xlabel(column_name)
            ax.set_ylabel('Frequency')
            ax.set_title(title)
        
        plt.tight_layout()
        
        chart_path = os.path.join(app.config['TEMP_FOLDER'], filename)
        plt.savefig(chart_path, dpi=100, bbox_inches='tight', facecolor='white')
        plt.close()
        
        if os.path.exists(chart_path):
            logger.info(f"Chart created: {chart_path}")
            return chart_path
        else:
            logger.warning(f"Chart file not created: {chart_path}")
            return None
            
    except Exception as e:
        logger.error(f"Error creating chart {filename}: {e}")
        plt.close('all')
        return None

def generate_pdf_report(analysis, report_title, company_name):
    """Generate PDF report with error handling"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"HR_Report_{timestamp}.pdf"
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        
        logger.info(f"Creating PDF at: {filepath}")
        
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        story = []
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1565C0'),
            spaceAfter=20,
            alignment=1
        )
        
        # Title
        story.append(Paragraph(company_name, title_style))
        story.append(Paragraph(report_title, title_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        
        # Summary table
        summary_data = [
            ["Metric", "Value"],
            ["Files Analyzed", str(analysis['summary']['total_files'])],
            ["Total Records", f"{analysis['summary']['total_rows']:,}"],
            ["Numeric Columns", str(analysis['summary']['numeric_columns'])],
            ["Categorical Columns", str(analysis['summary']['categorical_columns'])]
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1565C0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        
        # Insights
        story.append(Paragraph("Key Insights", styles['Heading2']))
        for insight in analysis['insights']:
            story.append(Paragraph(f"• {insight}", styles['Normal']))
        
        # Add charts (limit to 3 for performance)
        chart_count = 0
        
        # Categorical charts
        for col_name, cat_data in list(analysis['charts_data']['categorical'].items())[:2]:
            if chart_count >= 3:
                break
            try:
                chart_path = create_simple_chart(
                    'categorical_bar',
                    cat_data,
                    f'{col_name} Distribution',
                    f'cat_{chart_count}.png',
                    col_name
                )
                
                if chart_path and os.path.exists(chart_path):
                    story.append(PageBreak())
                    story.append(Paragraph(f"{col_name} Analysis", styles['Heading2']))
                    story.append(Image(chart_path, width=5*inch, height=3*inch))
                    chart_count += 1
            except Exception as e:
                logger.error(f"Error adding categorical chart: {e}")
        
        # Numeric charts
        for col_name, num_data in list(analysis['charts_data']['numeric'].items())[:1]:
            if chart_count >= 3:
                break
            try:
                chart_path = create_simple_chart(
                    'numeric_histogram',
                    num_data,
                    f'{col_name} Distribution',
                    f'num_{chart_count}.png',
                    col_name
                )
                
                if chart_path and os.path.exists(chart_path):
                    story.append(PageBreak())
                    story.append(Paragraph(f"{col_name} Analysis", styles['Heading2']))
                    story.append(Image(chart_path, width=5*inch, height=3*inch))
                    chart_count += 1
            except Exception as e:
                logger.error(f"Error adding numeric chart: {e}")
        
        # Build PDF
        doc.build(story)
        
        # Clean up chart files
        try:
            for file in os.listdir(app.config['TEMP_FOLDER']):
                if file.endswith('.png'):
                    os.remove(os.path.join(app.config['TEMP_FOLDER'], file))
        except:
            pass
        
        if os.path.exists(filepath):
            logger.info(f"PDF report created successfully: {filepath}")
            return filename
        else:
            raise Exception("PDF file was not created")
            
    except Exception as e:
        logger.error(f"Error generating PDF report: {e}")
        import traceback
        traceback.print_exc()
        raise e

# HTML Template (simplified)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HR Report Generator</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #1976D2, #1565C0); color: white; min-height: 100vh; }
        .container { max-width: 1000px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .card { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 20px; margin-bottom: 20px; backdrop-filter: blur(10px); }
        .btn { background: #1976D2; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px; }
        .btn:hover { background: #1565C0; }
        .btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .form-input { width: 100%; padding: 10px; border: none; border-radius: 5px; margin-bottom: 10px; }
        .file-item { background: rgba(255,255,255,0.1); padding: 10px; margin: 10px 0; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; }
        .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
        .status-success { background: rgba(76,175,80,0.3); border: 1px solid #4CAF50; }
        .status-error { background: rgba(244,67,54,0.3); border: 1px solid #f44336; }
        .status-info { background: rgba(33,150,243,0.3); border: 1px solid #2196F3; }
        .loading { display: none; text-align: center; padding: 30px; }
        .spinner { width: 30px; height: 30px; border: 3px solid rgba(255,255,255,0.3); border-top: 3px solid white; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 10px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .upload-area { border: 2px dashed rgba(255,255,255,0.5); padding: 40px; text-align: center; border-radius: 10px; }
        .upload-area:hover { border-color: #42A5F5; background: rgba(66,165,245,0.1); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin: 15px 0; }
        .stat-card { background: rgba(30,136,229,0.2); padding: 10px; border-radius: 5px; text-align: center; }
        .stat-value { font-size: 1.2rem; font-weight: bold; color: #42A5F5; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 HR Report Generator</h1>
            <p>Upload Excel files to generate HR reports</p>
        </div>
        
        <div class="card upload-area" id="uploadArea">
            <h3>📁 Upload Excel Files</h3>
            <p>Select .xlsx or .xls files</p>
            <input type="file" id="fileInput" multiple accept=".xlsx,.xls" style="display: none;">
            <button class="btn" onclick="document.getElementById('fileInput').click()">Browse Files</button>
            <div id="filesList"></div>
        </div>
        
        <div class="card" id="configSection" style="display: none;">
            <h3>⚙️ Report Configuration</h3>
            <div class="stats-grid" id="statsGrid"></div>
            <input type="text" id="reportTitle" class="form-input" placeholder="Report Title" value="HR Monthly Report">
            <input type="text" id="companyName" class="form-input" placeholder="Company Name" value="Company Analytics">
            <button class="btn" id="generateBtn" onclick="generateReport()" disabled>📊 Generate Report</button>
            <button class="btn" onclick="clearFiles()">🗑️ Clear Files</button>
        </div>
        
        <div class="loading" id="loadingSection">
            <div class="spinner"></div>
            <p>Generating report...</p>
        </div>
        
        <div id="statusMessages"></div>
    </div>
    
    <script>
        let uploadedFiles = [];
        
        document.getElementById('fileInput').addEventListener('change', handleFileUpload);
        
        function handleFileUpload() {
            const files = Array.from(document.getElementById('fileInput').files);
            if (files.length === 0) return;
            
            showStatus('Uploading files...', 'info');
            
            const formData = new FormData();
            files.forEach(file => formData.append('excel_files', file));
            
            fetch('/upload_excel', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    uploadedFiles = data.files;
                    updateFilesList();
                    updateStatsGrid(data.summary);
                    document.getElementById('configSection').style.display = 'block';
                    document.getElementById('generateBtn').disabled = false;
                    showStatus(`Successfully uploaded ${files.length} files`, 'success');
                } else {
                    showStatus(`Error: ${data.error}`, 'error');
                }
            })
            .catch(error => {
                showStatus(`Upload failed: ${error.message}`, 'error');
            });
        }
        
        function updateStatsGrid(summary) {
            const stats = [
                { label: 'Files', value: summary.total_files },
                { label: 'Records', value: summary.total_rows.toLocaleString() },
                { label: 'Columns', value: summary.total_columns },
                { label: 'Numeric', value: summary.numeric_columns },
                { label: 'Categories', value: summary.categorical_columns }
            ];
            
            document.getElementById('statsGrid').innerHTML = stats.map(stat => `
                <div class="stat-card">
                    <div class="stat-value">${stat.value}</div>
                    <div>${stat.label}</div>
                </div>
            `).join('');
        }
        
        function updateFilesList() {
            const filesList = document.getElementById('filesList');
            filesList.innerHTML = uploadedFiles.map((file, index) => `
                <div class="file-item">
                    <div>
                        <strong>${file.filename}</strong><br>
                        <small>Sheets: ${file.sheets.join(', ')} | ${file.size}</small>
                    </div>
                    <button class="btn" onclick="removeFile(${index})">Remove</button>
                </div>
            `).join('');
        }
        
        function removeFile(index) {
            uploadedFiles.splice(index, 1);
            if (uploadedFiles.length === 0) {
                document.getElementById('configSection').style.display = 'none';
                document.getElementById('generateBtn').disabled = true;
            }
            updateFilesList();
        }
        
        function clearFiles() {
            uploadedFiles = [];
            document.getElementById('filesList').innerHTML = '';
            document.getElementById('configSection').style.display = 'none';
            document.getElementById('generateBtn').disabled = true;
            document.getElementById('fileInput').value = '';
            showStatus('Files cleared', 'info');
        }
        
        function generateReport() {
            const reportTitle = document.getElementById('reportTitle').value || 'HR Monthly Report';
            const companyName = document.getElementById('companyName').value || 'Company';
            
            document.getElementById('loadingSection').style.display = 'block';
            document.getElementById('generateBtn').disabled = true;
            
            fetch('/generate_reports', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ report_title: reportTitle, company_name: companyName })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('loadingSection').style.display = 'none';
                document.getElementById('generateBtn').disabled = false;
                
                if (data.success) {
                    showStatus('Report generated successfully!', 'success');
                    const downloadDiv = document.createElement('div');
                    downloadDiv.className = 'status status-success';
                    downloadDiv.innerHTML = `
                        <h4>📊 Report Ready</h4>
                        <a href="${data.pdf_url}" class="btn" download style="text-decoration: none;">📄 Download PDF</a>
                    `;
                    document.getElementById('statusMessages').appendChild(downloadDiv);
                } else {
                    showStatus(`Error: ${data.error}`, 'error');
                }
            })
            .catch(error => {
                document.getElementById('loadingSection').style.display = 'none';
                document.getElementById('generateBtn').disabled = false;
                showStatus(`Error: ${error.message}`, 'error');
            });
        }
        
        function showStatus(message, type) {
            const statusDiv = document.createElement('div');
            statusDiv.className = `status status-${type}`;
            statusDiv.innerHTML = message;
            document.getElementById('statusMessages').appendChild(statusDiv);
            setTimeout(() => statusDiv.remove(), 5000);
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    global uploaded_files, report_data
    
    try:
        if 'excel_files' not in request.files:
            return jsonify({'error': 'No files selected'}), 400
        
        files = request.files.getlist('excel_files')
        if not files:
            return jsonify({'error': 'No files provided'}), 400
        
        uploaded_files = []
        dataframes = {}
        
        for file in files:
            if file.filename == '' or not (file.filename.lower().endswith('.xlsx') or file.filename.lower().endswith('.xls')):
                continue
                
            try:
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                
                file.save(filepath)
                logger.info(f"File saved: {filepath}")
                
                # Read Excel file
                excel_file = pd.ExcelFile(filepath)
                sheets = {}
                sheet_names = []
                
                for sheet_name in excel_file.sheet_names:
                    try:
                        df = pd.read_excel(filepath, sheet_name=sheet_name)
                        df.columns = df.columns.astype(str).str.strip()
                        df = df.dropna(how='all').dropna(axis=1, how='all')
                        
                        if not df.empty:
                            sheets[sheet_name] = df
                            sheet_names.append(sheet_name)
                            logger.info(f"Read sheet {sheet_name}: {len(df)} rows")
                    except Exception as e:
                        logger.warning(f"Could not read sheet {sheet_name}: {e}")
                
                if sheets:
                    dataframes[file.filename] = sheets
                    file_size = os.path.getsize(filepath)
                    uploaded_files.append({
                        'filename': file.filename,
                        'filepath': filepath,
                        'sheets': sheet_names,
                        'size': f"{file_size/1024:.1f} KB" if file_size < 1024*1024 else f"{file_size/(1024*1024):.1f} MB"
                    })
                    
            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {e}")
                continue
        
        if not uploaded_files:
            return jsonify({'error': 'No valid Excel files processed'}), 400
        
        # Analyze data
        report_data = analyze_excel_data(dataframes)
        logger.info("Data analysis completed")
        
        return jsonify({
            'success': True,
            'files': uploaded_files,
            'summary': report_data['summary']
        })
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/generate_reports', methods=['POST'])
def generate_reports():
    global report_data
    
    try:
        if not report_data:
            return jsonify({'error': 'No data available. Upload files first.'}), 400
        
        data = request.json
        report_title = data.get('report_title', 'HR Monthly Report')
        company_name = data.get('company_name', 'Company')
        
        logger.info(f"Generating report: {report_title}")
        
        # Generate PDF
        pdf_filename = generate_pdf_report(report_data, report_title, company_name)
        
        return jsonify({
            'success': True,
            'pdf_filename': pdf_filename,
            'pdf_url': f'/download/{pdf_filename}'
        })
        
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Report generation failed: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        filename = secure_filename(filename)
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=filename)
        else:
            return jsonify({'error': 'File not found'}), 404
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting HR Report Generator on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
