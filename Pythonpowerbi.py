from flask import Flask, render_template_string, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import io
import base64
from datetime import datetime
import socket
import sys
import subprocess

# Auto-install required packages
def install_package(package):
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

install_package('flask')
install_package('PyMuPDF')
install_package('Pillow')

try:
    import fitz  # PyMuPDF
    from PIL import Image
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Get the script directory for reliable paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(SCRIPT_DIR, 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(SCRIPT_DIR, 'outputs')

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

print(f"📁 Upload folder: {app.config['UPLOAD_FOLDER']}")
print(f"📁 Output folder: {app.config['OUTPUT_FOLDER']}")

# Global variables to store current PDF data
current_pdf = None
current_filename = None

def get_local_ip():
    """Get the local IP address of this machine"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Region Extractor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #0F1E36;
            color: white;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .top-frame {
            background-color: #0A192F;
            padding: 10px;
            display: flex;
            align-items: center;
        }
        
        .logo {
            width: 150px;
            height: 50px;
            margin-right: 10px;
            cursor: pointer;
        }
        
        .title {
            font-size: 24px;
            font-weight: bold;
            color: #00BFFF;
            margin-left: 10px;
        }
        
        .toolbar {
            background-color: #0A192F;
            padding: 5px;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .btn {
            background-color: #007ACC;
            color: white;
            border: none;
            padding: 8px 12px;
            font-family: 'Segoe UI', sans-serif;
            font-size: 10px;
            font-weight: bold;
            cursor: pointer;
            border-radius: 3px;
            transition: background-color 0.2s;
        }
        
        .btn:hover {
            background-color: #005A9E;
        }
        
        .btn:active {
            background-color: #005A9E;
        }
        
        .btn:disabled {
            background-color: #444;
            cursor: not-allowed;
        }
        
        .page-label {
            background-color: #0A192F;
            color: white;
            font-family: 'Segoe UI', sans-serif;
            font-size: 10px;
            font-weight: bold;
            margin-left: 10px;
            padding: 8px;
        }
        
        .canvas-container {
            flex: 1;
            background-color: white;
            position: relative;
            overflow: auto;
            cursor: default;
            user-select: none;
            -webkit-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
        }
        
        .canvas-container.selecting {
            cursor: crosshair;
        }
        
        .canvas {
            position: relative;
            display: inline-block;
        }
        
        .pdf-image {
            display: block;
            max-width: none;
            user-select: none;
            -webkit-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
            pointer-events: none;
        }
        
        .selection-box {
            position: absolute;
            border: 3px solid #FF0000;
            background-color: rgba(255, 0, 0, 0.15);
            pointer-events: none;
            display: none;
            box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.8), 
                        0 0 10px rgba(255, 0, 0, 0.5);
            animation: pulse-border 1.5s ease-in-out infinite alternate;
        }
        
        @keyframes pulse-border {
            0% { border-color: #FF0000; box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.8), 0 0 10px rgba(255, 0, 0, 0.5); }
            100% { border-color: #FF3333; box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.9), 0 0 15px rgba(255, 0, 0, 0.8); }
        }
        
        .selection-info {
            background-color: #0F1E36;
            color: white;
            font-family: 'Segoe UI', sans-serif;
            font-size: 10px;
            padding: 5px;
            text-align: center;
        }
        
        .status-bar {
            background-color: #0A192F;
            color: white;
            font-family: 'Segoe UI', sans-serif;
            font-size: 9px;
            padding: 5px;
            border-top: 1px solid #333;
        }
        
        .file-input {
            display: none;
        }
        
        .drag-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 191, 255, 0.2);
            border: 3px dashed #00BFFF;
            display: none;
            justify-content: center;
            align-items: center;
            font-size: 24px;
            font-weight: bold;
            color: #00BFFF;
            z-index: 1000;
        }
        
        .loading {
            text-align: center;
            padding: 20px;
            color: #00BFFF;
        }
    </style>
</head>
<body>
    <div class="drag-overlay" id="dragOverlay">
        Drop PDF file here
    </div>
    
    <div class="top-frame">
        <div class="title">PDF Extractor</div>
    </div>
    
    <div class="toolbar">
        <input type="file" id="fileInput" class="file-input" accept=".pdf">
        <button class="btn" onclick="document.getElementById('fileInput').click()">Load PDF</button>
        <button class="btn" id="prevBtn" onclick="prevPage()" disabled>Prev</button>
        <button class="btn" id="nextBtn" onclick="nextPage()" disabled>Next</button>
        <button class="btn" id="saveBtn" onclick="saveSelection()" disabled>Save Selection as Image</button>
        <button class="btn" id="printBtn" onclick="printImage()" disabled>🖨️ Print Image</button>
        <div class="page-label" id="pageLabel">Page 0/0</div>
    </div>
    
    <div class="canvas-container" id="canvasContainer">
        <div class="canvas" id="canvas">
            <img id="pdfImage" class="pdf-image" style="display: none;">
            <div class="selection-box" id="selectionBox"></div>
        </div>
    </div>
    
    <div class="selection-info" id="selectionInfo">Hold Ctrl and drag to select area</div>
    <div class="status-bar" id="statusBar">Ready - Click 'Load PDF' to begin</div>
    
    <script>
        let currentPdf = null;
        let currentPage = 0;
        let totalPages = 0;
        let isSelecting = false;
        let startX, startY, endX, endY;
        let selectionValid = false;
        let lastExtractedImage = null;
        let ctrlPressed = false;
        
        const fileInput = document.getElementById('fileInput');
        const pdfImage = document.getElementById('pdfImage');
        const selectionBox = document.getElementById('selectionBox');
        const canvasContainer = document.getElementById('canvasContainer');
        const canvas = document.getElementById('canvas');
        
        // File upload handling
        fileInput.addEventListener('change', handleFileUpload);
        
        // Drag and drop
        document.addEventListener('dragover', (e) => {
            e.preventDefault();
            document.getElementById('dragOverlay').style.display = 'flex';
        });
        
        document.addEventListener('dragleave', (e) => {
            if (!e.relatedTarget) {
                document.getElementById('dragOverlay').style.display = 'none';
            }
        });
        
        document.addEventListener('drop', (e) => {
            e.preventDefault();
            document.getElementById('dragOverlay').style.display = 'none';
            
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type === 'application/pdf') {
                fileInput.files = files;
                handleFileUpload();
            }
        });
        
        // Mouse events for selection
        canvas.addEventListener('mousedown', startSelection);
        canvas.addEventListener('mousemove', updateSelection);
        canvas.addEventListener('mouseup', endSelection);
        
        function updateStatus(message) {
            document.getElementById('statusBar').textContent = message;
        }
        
        function handleFileUpload() {
            const file = fileInput.files[0];
            if (!file) return;
            
            updateStatus('Loading PDF...');
            
            const formData = new FormData();
            formData.append('pdf_file', file);
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    currentPdf = data.filename;
                    totalPages = data.total_pages;
                    currentPage = 0;
                    updatePageDisplay();
                    updateStatus(`Loaded: ${file.name} (${totalPages} pages)`);
                    
                    document.getElementById('prevBtn').disabled = false;
                    document.getElementById('nextBtn').disabled = false;
                } else {
                    updateStatus('Error: ' + data.error);
                }
            })
            .catch(error => {
                updateStatus('Error loading PDF: ' + error.message);
            });
        }
        
        function updatePageDisplay() {
            if (!currentPdf) return;
            
            updateStatus('Rendering page...');
            
            fetch(`/get_page/${currentPage}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    pdfImage.src = data.image;
                    pdfImage.style.display = 'block';
                    document.getElementById('pageLabel').textContent = `Page ${currentPage + 1}/${totalPages}`;
                    clearSelection();
                    updateStatus('Ready - Hold Ctrl and drag to select area');
                } else {
                    updateStatus('Error: ' + data.error);
                }
            })
            .catch(error => {
                updateStatus('Error rendering page: ' + error.message);
            });
        }
        
        function prevPage() {
            if (currentPage > 0) {
                currentPage--;
                updatePageDisplay();
            }
        }
        
        function nextPage() {
            if (currentPage < totalPages - 1) {
                currentPage++;
                updatePageDisplay();
            }
        }
        
        function startSelection(e) {
            if (!currentPdf || !ctrlPressed) return;
            
            e.preventDefault();
            
            const rect = canvas.getBoundingClientRect();
            startX = e.clientX - rect.left + canvasContainer.scrollLeft;
            startY = e.clientY - rect.top + canvasContainer.scrollTop;
            
            isSelecting = true;
            selectionBox.style.display = 'block';
            selectionBox.style.left = startX + 'px';
            selectionBox.style.top = startY + 'px';
            selectionBox.style.width = '0px';
            selectionBox.style.height = '0px';
            
            updateStatus('Selecting... Release to finish selection');
        }
        
        function updateSelection(e) {
            if (!isSelecting || !ctrlPressed) return;
            
            e.preventDefault();
            
            const rect = canvas.getBoundingClientRect();
            endX = e.clientX - rect.left + canvasContainer.scrollLeft;
            endY = e.clientY - rect.top + canvasContainer.scrollTop;
            
            const left = Math.min(startX, endX);
            const top = Math.min(startY, endY);
            const width = Math.abs(endX - startX);
            const height = Math.abs(endY - startY);
            
            selectionBox.style.left = left + 'px';
            selectionBox.style.top = top + 'px';
            selectionBox.style.width = width + 'px';
            selectionBox.style.height = height + 'px';
            
            updateStatus(`Selecting: ${Math.round(width)}x${Math.round(height)} pixels`);
        }
        
        function endSelection(e) {
            if (!isSelecting || !ctrlPressed) return;
            
            e.preventDefault();
            isSelecting = false;
            
            const rect = canvas.getBoundingClientRect();
            endX = e.clientX - rect.left + canvasContainer.scrollLeft;
            endY = e.clientY - rect.top + canvasContainer.scrollTop;
            
            const width = Math.abs(endX - startX);
            const height = Math.abs(endY - startY);
            
            if (width > 5 && height > 5) {
                selectionValid = true;
                document.getElementById('selectionInfo').textContent = `Selected area: ${Math.round(width)}x${Math.round(height)} pixels`;
                document.getElementById('saveBtn').disabled = false;
                updateStatus(`Selection ready: ${Math.round(width)}x${Math.round(height)} pixels - Click 'Save Selection as Image'`);
            } else {
                clearSelection();
                updateStatus('Selection too small - Hold Ctrl and drag to select a larger area');
            }
        }
        
        function clearSelection() {
            selectionBox.style.display = 'none';
            selectionValid = false;
            isSelecting = false;
            document.getElementById('selectionInfo').textContent = 'Hold Ctrl and drag to select area';
            document.getElementById('saveBtn').disabled = true;
            if (currentPdf) {
                updateStatus('Ready - Hold Ctrl and drag to select area');
            }
        }
        
        function saveSelection() {
            if (!selectionValid || !currentPdf) return;
            
            updateStatus('Extracting selection...');
            
            const x1 = Math.min(startX, endX);
            const y1 = Math.min(startY, endY);
            const x2 = Math.max(startX, endX);
            const y2 = Math.max(startY, endY);
            
            fetch('/extract_region', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    page_num: currentPage,
                    x1: x1,
                    y1: y1,
                    x2: x2,
                    y2: y2
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    lastExtractedImage = data.filename;
                    updateStatus(`✅ Selection saved as ${data.filename} - Ready to print!`);
                    document.getElementById('printBtn').disabled = false;
                    
                    // Auto-download the file
                    const link = document.createElement('a');
                    link.href = data.download_url;
                    link.download = data.filename;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    
                    // Show success message
                    setTimeout(() => {
                        updateStatus(`📁 File downloaded: ${data.filename} | 🖨️ Click "Print Image" to print`);
                    }, 1000);
                } else {
                    updateStatus('❌ Error: ' + data.error);
                    console.error('Save error:', data.error);
                }
            })
            .catch(error => {
                updateStatus('❌ Error saving selection: ' + error.message);
                console.error('Save error:', error);
            });
        }
        
        function printImage() {
            if (!lastExtractedImage) {
                updateStatus('❌ No image available to print - Save a selection first');
                return;
            }
            
            updateStatus('🖨️ Opening print dialog...');
            
            // Open the print page in a new window
            const printWindow = window.open(`/print/${lastExtractedImage}`, '_blank', 'width=800,height=600');
            
            if (printWindow) {
                printWindow.focus();
                updateStatus(`✅ Print window opened for: ${lastExtractedImage}`);
            } else {
                // Fallback: try direct download if popup blocked
                updateStatus('⚠️ Popup blocked - trying direct download...');
                const link = document.createElement('a');
                link.href = `/download/${lastExtractedImage}`;
                link.download = lastExtractedImage;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                updateStatus(`📁 Downloaded: ${lastExtractedImage} - Open file and print manually`);
            }
        }
        
        // Track Ctrl key state
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Control') {
                ctrlPressed = true;
                canvasContainer.classList.add('selecting');
                updateStatus('Hold Ctrl and drag to select area');
            } else if (e.key === 'ArrowLeft' && currentPage > 0) {
                prevPage();
            } else if (e.key === 'ArrowRight' && currentPage < totalPages - 1) {
                nextPage();
            } else if (e.key === 'Escape') {
                clearSelection();
            }
        });
        
        document.addEventListener('keyup', (e) => {
            if (e.key === 'Control') {
                ctrlPressed = false;
                canvasContainer.classList.remove('selecting');
                if (!selectionValid) {
                    updateStatus('Ready - Hold Ctrl and drag to select area');
                }
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    global current_pdf, current_filename
    
    if 'pdf_file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['pdf_file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and file.filename.lower().endswith('.pdf'):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            current_pdf = fitz.open(filepath)
            current_filename = filename
            total_pages = len(current_pdf)
            
            return jsonify({
                'success': True,
                'filename': filename,
                'total_pages': total_pages
            })
        except Exception as e:
            return jsonify({'error': f'Failed to open PDF: {str(e)}'}), 400
    
    return jsonify({'error': 'Invalid file type. Please upload a PDF file.'}), 400

@app.route('/get_page/<int:page_num>')
def get_page(page_num):
    global current_pdf
    
    if not current_pdf:
        return jsonify({'error': 'No PDF loaded'}), 400
    
    if page_num < 0 or page_num >= len(current_pdf):
        return jsonify({'error': 'Invalid page number'}), 400
    
    try:
        page = current_pdf[page_num]
        # Render page as image with 2x zoom like original
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Convert to base64 for web display
        img_base64 = base64.b64encode(img_data).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image': f'data:image/png;base64,{img_base64}',
            'width': pix.width,
            'height': pix.height
        })
    except Exception as e:
        return jsonify({'error': f'Failed to render page: {str(e)}'}), 400

@app.route('/extract_region', methods=['POST'])
def extract_region():
    global current_pdf
    
    if not current_pdf:
        return jsonify({'error': 'No PDF loaded'}), 400
    
    data = request.json
    page_num = data.get('page_num')
    x1 = data.get('x1')
    y1 = data.get('y1')
    x2 = data.get('x2')
    y2 = data.get('y2')
    
    if None in [page_num, x1, y1, x2, y2]:
        return jsonify({'error': 'Missing selection coordinates'}), 400
    
    try:
        page = current_pdf[page_num]
        
        # Convert coordinates (they come from 2x zoom display, same as original)
        rect = fitz.Rect(x1/2, y1/2, x2/2, y2/2)
        
        # Extract region with 2x quality like original
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)
        
        # Save extracted image with timestamp like original
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"selection_{timestamp}.png"
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, "wb") as f:
            f.write(pix.tobytes("png"))
        
        # Verify file was created
        if not os.path.exists(filepath):
            return jsonify({'error': 'Failed to save file'}), 500
            
        # Also return as base64 for immediate display/print
        img_base64 = base64.b64encode(pix.tobytes("png")).decode('utf-8')
        
        print(f"✅ File saved: {filepath}")
        print(f"📏 File size: {os.path.getsize(filepath)} bytes")
        
        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': filepath,
            'download_url': f'/download/{filename}',
            'print_url': f'/print/{filename}',
            'image_data': f'data:image/png;base64,{img_base64}'
        })
        
    except Exception as e:
        print(f"❌ Extraction error: {str(e)}")
        return jsonify({'error': f'Failed to extract region: {str(e)}'}), 400

@app.route('/download/<filename>')
def download_file(filename):
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        print(f"🔍 Looking for file: {filepath}")
        
        if os.path.exists(filepath):
            print(f"✅ File found, sending: {filepath}")
            return send_file(filepath, as_attachment=True, download_name=filename)
        else:
            print(f"❌ File not found: {filepath}")
            # List all files in output folder for debugging
            if os.path.exists(app.config['OUTPUT_FOLDER']):
                files = os.listdir(app.config['OUTPUT_FOLDER'])
                print(f"📂 Files in output folder: {files}")
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        print(f"❌ Download error: {str(e)}")
        return jsonify({'error': f'Download failed: {str(e)}'}), 400

@app.route('/print/<filename>')
def print_file(filename):
    """Special route for printing - opens image in print-friendly page"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        print(f"🖨️ Print request for: {filepath}")
        
        if os.path.exists(filepath):
            # Read image and convert to base64
            with open(filepath, 'rb') as f:
                img_data = f.read()
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            # Return HTML page optimized for printing
            print_html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Print - {filename}</title>
                <style>
                    @media print {{
                        body {{ margin: 0; padding: 0; }}
                        .no-print {{ display: none; }}
                        img {{ 
                            max-width: 100%; 
                            max-height: 100vh; 
                            object-fit: contain;
                            page-break-inside: avoid;
                        }}
                    }}
                    @media screen {{
                        body {{ 
                            font-family: 'Segoe UI', sans-serif;
                            background: #0F1E36;
                            color: white;
                            text-align: center;
                            padding: 20px;
                        }}
                        img {{ 
                            max-width: 90%;
                            border: 2px solid #007ACC;
                            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
                        }}
                        .print-btn {{
                            background: #007ACC;
                            color: white;
                            border: none;
                            padding: 15px 30px;
                            font-size: 16px;
                            font-weight: bold;
                            cursor: pointer;
                            margin: 20px;
                            border-radius: 5px;
                        }}
                        .print-btn:hover {{ background: #005A9E; }}
                    }}
                </style>
            </head>
            <body>
                <div class="no-print">
                    <h2>📄 {filename}</h2>
                    <button class="print-btn" onclick="window.print()">🖨️ Print Image</button>
                    <button class="print-btn" onclick="window.close()">❌ Close</button>
                </div>
                <img src="data:image/png;base64,{img_base64}" alt="{filename}">
                <script>
                    // Auto-focus for keyboard shortcuts
                    window.focus();
                    
                    // Keyboard shortcuts
                    document.addEventListener('keydown', function(e) {{
                        if (e.ctrlKey && e.key === 'p') {{
                            e.preventDefault();
                            window.print();
                        }} else if (e.key === 'Escape') {{
                            window.close();
                        }}
                    }});
                    
                    // Auto-print option (uncomment if you want auto-print)
                    // window.onload = function() {{ setTimeout(() => window.print(), 500); }};
                </script>
            </body>
            </html>
            '''
            return print_html
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        print(f"❌ Print error: {str(e)}")
        return jsonify({'error': f'Print failed: {str(e)}'}), 400

if __name__ == '__main__':
    local_ip = get_local_ip()
    port = 5000
    
    print("=" * 60)
    print("🌐 PDF Region Extractor - Web Version")
    print("=" * 60)
    print(f"✅ Server starting on: http://{local_ip}:{port}")
    print(f"📱 Local access: http://127.0.0.1:{port}")
    print(f"🌍 Network access: http://{local_ip}:{port}")
    print("=" * 60)
    print("📝 Instructions:")
    print("   1. Anyone on your network can access the URL above")
    print("   2. Your IP may change, but the app will show the new IP when restarted")
    print("   3. Share the network URL with others on your network")
    print("   4. Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print("   Try running as administrator or use a different port")