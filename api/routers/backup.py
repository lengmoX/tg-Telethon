"""
Backup API Router
"""

import shutil
import zipfile
import json
import os
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from api.deps import get_api_config, get_current_user
from tgf.data.config import Config

router = APIRouter()

@router.get("/export", response_class=FileResponse)
async def export_backup(
    background_tasks: BackgroundTasks,
    config: Config = Depends(get_api_config),
    _: str = Depends(get_current_user)
):
    """
    Export all data to a zip file.
    Includes: database, session files, and .env
    """
    # Create temp file for zip
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tgf_backup_{date_str}.zip"
    temp_zip = config.data_dir / f"temp_{filename}"
    
    metadata = {
        "version": 2,
        "created_at": datetime.now().isoformat(),
        "tool": "tgf-web",
        "namespace": config.namespace,
        "contents": []
    }
    
    try:
        with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 1. Export database
            if config.db_path.exists():
                # On Windows, we might need to copy it first if it's locked?
                # Usually reading/copying an open SQLite file is "okay" but might be inconsistent.
                # For safety, we could try to verify integrity or use sqlite3 backup API, 
                # but for now we follow the CLI approach.
                try:
                    zf.write(config.db_path, "tgf.db")
                    metadata["contents"].append("database")
                except PermissionError:
                    # Fallback: try to read bytes if possible or skip
                    pass

            # 2. Export session files
            if config.sessions_dir.exists():
                for session_file in config.sessions_dir.glob("*.session"):
                    zf.write(session_file, f"sessions/{session_file.name}")
                
                # Also include journal files
                for journal_file in config.sessions_dir.glob("*.session-journal"):
                    zf.write(journal_file, f"sessions/{journal_file.name}")
                
                metadata["contents"].append("sessions")

            # 3. Export .env file
            env_file = config.data_dir / ".env"
            if env_file.exists():
                zf.write(env_file, ".env")
                metadata["contents"].append("env")

            # 4. Write metadata
            zf.writestr('metadata.json', json.dumps(metadata, ensure_ascii=False, indent=2))
        
        # Cleanup temp file after sending
        background_tasks.add_task(os.remove, temp_zip)
        
        return FileResponse(
            path=temp_zip,
            filename=filename,
            media_type='application/zip'
        )
        
    except Exception as e:
        if temp_zip.exists():
            os.remove(temp_zip)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/import")
async def import_backup(
    file: UploadFile = File(...),
    config: Config = Depends(get_api_config),
    _: str = Depends(get_current_user)
):
    """
    Import data from a backup zip file.
    WARNING: This will overwrite existing data.
    """
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a .zip archive")
    
    # Save uploaded file to temp
    temp_zip = config.data_dir / f"temp_upload_{file.filename}"
    try:
        with open(temp_zip, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        restored_items = []
        
        with zipfile.ZipFile(temp_zip, 'r') as zf:
            # Validate metadata (optional)
            try:
                meta = json.loads(zf.read('metadata.json'))
            except:
                pass # Legacy or missing metadata is ok
            
            # 1. Restore Database
            # Note: Restoring DB while running might fail on Windows due to locking.
            # We will attempt it.
            if 'tgf.db' in zf.namelist():
                try:
                    # Create a backup of current DB just in case
                    if config.db_path.exists():
                        shutil.copy(config.db_path, config.db_path.with_suffix('.bak'))
                    
                    # Extract to temp then replace
                    zf.extract('tgf.db', config.data_dir / "temp_restore")
                    temp_db = config.data_dir / "temp_restore" / "tgf.db"
                    
                    # Move to actual location
                    # On Windows, this is the critical step
                    shutil.move(str(temp_db), str(config.db_path))
                    shutil.rmtree(config.data_dir / "temp_restore", ignore_errors=True)
                    restored_items.append("Database")
                except PermissionError:
                    raise HTTPException(
                        status_code=409, 
                        detail="无法恢复数据库: 文件正被使用。请先停止服务再手动恢复，或仅恢复配置和会话。"
                    )
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Database restore failed: {str(e)}")

            # 2. Restore Sessions
            session_files = [f for f in zf.namelist() if f.startswith('sessions/') and not f.endswith('/')]
            if session_files:
                config.sessions_dir.mkdir(parents=True, exist_ok=True)
                for sf in session_files:
                    target_name = Path(sf).name
                    zf.extract(sf, config.data_dir) # Extracts to data_dir/sessions/name
                    # No need to move if structure matches, but zip structure might vary
                    # CLI creates "sessions/filename", so extraction puts it in data_dir/sessions/
                restored_items.append(f"Sessions ({len(session_files)})")

            # 3. Restore .env
            if '.env' in zf.namelist():
                zf.extract('.env', config.data_dir)
                restored_items.append("Config (.env)")
                
        return {
            "success": True, 
            "message": f"Restored: {', '.join(restored_items)}",
            "details": restored_items
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    finally:
        if temp_zip.exists():
            os.remove(temp_zip)
