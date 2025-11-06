from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from titiler.core.factory import TilerFactory
from starlette.middleware.cors import CORSMiddleware
from pathlib import Path
import yaml
import os
import tempfile
import shutil
import subprocess

# Load configuration
config_file = Path("config.yaml")
if config_file.exists():
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
else:
    # Default configuration if config.yaml doesn't exist
    config = {
        'server': {'host': '0.0.0.0', 'port': 8000, 'reload': True},
        'data': {'directory': 'data', 'pattern': '*cog*.tif', 'include_extensions': ['.tif', '.tiff']},
        'cors': {'enabled': True, 'origins': ['*'], 'allow_credentials': True, 'allow_methods': ['*'], 'allow_headers': ['*']},
        'viewer': {'title': 'Orthomosaic Viewer', 'default_opacity': 1.0, 'max_zoom': 2000},
        'titiler': {'tile_size': 256, 'max_threads': 10}
    }

app = FastAPI(title=config['viewer']['title'])

# Add CORS middleware if enabled
if config['cors']['enabled']:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config['cors']['origins'],
        allow_credentials=config['cors']['allow_credentials'],
        allow_methods=config['cors']['allow_methods'],
        allow_headers=config['cors']['allow_headers'],
    )

# Create a TilerFactory for Cloud-Optimized GeoTIFFs
cog = TilerFactory()

# Register all the COG endpoints automatically
app.include_router(cog.router, tags=["Cloud Optimized GeoTIFF"])

# Mount static files (for any CSS, JS, images, etc.)
# This allows serving files from the data directory
data_directory = config['data']['directory']
app.mount("/static", StaticFiles(directory=data_directory), name="static")

# API endpoint to list available COG files in the data directory
@app.get("/api/cog-files")
def list_cog_files():
    data_dir = Path(config['data']['directory'])
    if not data_dir.exists():
        return {"files": []}
    
    # Find all files matching the configured extensions
    cog_files = []
    extensions = config['data']['include_extensions']
    pattern_keyword = "cog"  # Look for 'cog' in filename
    
    for ext in extensions:
        for file in data_dir.glob(f"*{ext}"):
            if pattern_keyword in file.name.lower():
                cog_files.append(str(file.name))
    
    return {"files": sorted(cog_files)}

# API endpoint to get configuration
@app.get("/api/config")
def get_config():
    """Return viewer configuration for client"""
    return {
        "viewer": config['viewer'],
        "data_directory": config['data']['directory']
    }

# Serve the landing page at root
@app.get("/", response_class=HTMLResponse)
def read_index():
    index_file = Path("web/index.html")
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return "<h1>Welcome to SfM Orthomosaic Viewer</h1>"

# Serve the viewer page
@app.get("/viewer", response_class=HTMLResponse)
def read_viewer():
    viewer_file = Path("web/viewer.html")
    if viewer_file.exists():
        return viewer_file.read_text(encoding="utf-8")
    return "<h1>Viewer not found</h1>"

# Serve the converter page
@app.get("/converter", response_class=HTMLResponse)
def read_converter():
    converter_file = Path("web/converter.html")
    if converter_file.exists():
        return converter_file.read_text(encoding="utf-8")
    return "<h1>Converter not found</h1>"

# API endpoint for COG conversion
@app.post("/api/convert")
async def convert_to_cog(
    file: UploadFile = File(...),
    resampling: str = Form("bilinear"),
    compression: str = Form("auto"),
    output_name: str = Form(None),
    nodata: str = Form(None)
):
    """Convert uploaded GeoTIFF to COG format"""
    
    # Validate file type
    if not file.filename.lower().endswith(('.tif', '.tiff')):
        raise HTTPException(status_code=400, detail="Only .tif and .tiff files are supported")
    
    # Create temp directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        # Save uploaded file
        input_path = temp_dir_path / file.filename
        with open(input_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        # Generate output filename
        if output_name:
            if not output_name.lower().endswith(('.tif', '.tiff')):
                output_name += '.tif'
        else:
            # Auto-generate with _cog suffix
            stem = Path(file.filename).stem
            output_name = f"{stem}_cog.tif"
        
        # Ensure output goes to data directory
        output_dir = Path(config['data']['directory'])
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_name
        
        # Build conversion command
        cmd = [
            'python', 'scripts/make_cog.py',
            '--src', str(input_path),
            '--dst', str(output_path),
            '--resampling', resampling
        ]
        
        # Add compression if not auto
        if compression != 'auto':
            cmd.extend(['--profile', compression])
        
        # Add nodata value if provided (for DEMs)
        if nodata:
            try:
                cmd.extend(['--nodata', str(float(nodata))])
            except ValueError:
                pass  # Invalid nodata value, skip it
        
        try:
            # Run conversion
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"Conversion failed: {result.stderr}"
                )
            
            # Check if output file was created
            if not output_path.exists():
                raise HTTPException(
                    status_code=500,
                    detail="Conversion completed but output file not found"
                )
            
            return JSONResponse({
                "success": True,
                "output_file": output_name,
                "message": "Conversion successful",
                "size_mb": round(output_path.stat().st_size / (1024 * 1024), 2)
            })
            
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Conversion timeout (file too large)")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Conversion error: {str(e)}")