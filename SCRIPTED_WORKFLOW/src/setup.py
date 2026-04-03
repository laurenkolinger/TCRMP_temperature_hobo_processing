#!/usr/bin/env python3
"""
Automated Setup Script for Temperature Monitoring Framework
==========================================================

Creates virtual environment, installs dependencies, and generates directory structure.
Run: python src/setup.py
"""

import os
import sys
import subprocess
import json
import shutil
from datetime import datetime
from pathlib import Path

# Import config from current directory
try:
    from config import CONFIG, MONITORING_TYPE_CONFIGS, get_directory_structure, resolve_path
except ImportError:
    print("Error: Cannot import config.py from src directory")
    sys.exit(1)

class FrameworkSetup:
    def __init__(self):
        self.config = CONFIG
        self.base_dir = Path(self.config['BASE_DIRECTORY'])
        self.requirements_file = Path(__file__).parent / self.config['REQUIREMENTS_FILE']
        
    def create_virtual_environment(self):
        #venv_path = self.base_dir / self.config['VENV_NAME']
        # CHANGE TO PUT THE TEMP ENV IN SCRIPTED WORKFLOW INSTEAD OF SCRIPTED OUTPUTS TBA
        venv_path = Path(self.config['WORKFLOW_DIRECTORY']) / self.config['VENV_NAME']
        
        print(f"Creating virtual environment: {venv_path}")
        
        # Remove existing venv if it exists
        if venv_path.exists():
            shutil.rmtree(venv_path)
        
        # Create new virtual environment
        subprocess.run([sys.executable, '-m', 'venv', str(venv_path)], check=True)
        
        # Determine paths
        if sys.platform == "win32":
            pip_path = venv_path / "Scripts" / "pip"
            python_path = venv_path / "Scripts" / "python"
        else:
            pip_path = venv_path / "bin" / "pip"
            python_path = venv_path / "bin" / "python"
        
        # Install requirements
        print("Installing dependencies...")
        subprocess.run([str(pip_path), 'install', '-r', str(self.requirements_file)], check=True)
        
        return True
    
    def create_directory_structure(self):
        print("Creating directory structure...")
        
        #dp = self.base_dir / self.config['YEARS'] / self.config['MONITORING_TYPES']
        #print(dp)
        #os.makedirs(dp, exist_ok=True) #create the directory for the year and monitoring type

        structure = get_directory_structure()
        
        for dir_path in structure.keys():
            
            os.makedirs(dir_path, exist_ok=True)
            
            # Create README for HOBO_OUT directories
            if '01_HOBO_OUT' in dir_path:
                readme_path = Path(dir_path) / 'README.md'
                with open(readme_path, 'w') as f:
                    f.write("# HOBO Data Files\n\n")
                    f.write("Place original HOBO export files here:\n")
                    f.write("- .csv files (temperature data)\n")
                    f.write("- .hobo files (binary HOBO files)\n")
                    f.write("- _Details.txt files (deployment metadata)\n")
        
        print(f"Created {len(structure)} directories")
        return True
    
    def create_config_snapshot(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        config_snapshot = {
            'setup_info': {
                'timestamp': datetime.now().isoformat(),
                'framework_version': self.config['FRAMEWORK_VERSION'],
                'created_by': self.config['CREATED_BY']
            },
            'directory_structure': {
                'years': self.config['YEARS'],
                'monitoring_types': self.config['MONITORING_TYPES'],
                'subdirectories': self.config['AUTO_SUBDIRECTORIES'],
                'base_directory': str(self.base_dir)
            }
        }
        
        # Write config snapshot to each year/monitoring_type config_snapshots directory
        json_files = []
        for year in self.config['YEARS']:
            for monitoring_type in self.config['MONITORING_TYPES']:
                snapshot_dir = self.base_dir / str(year) / monitoring_type / 'config_snapshots'
                json_file = snapshot_dir / f'config_snapshot_{timestamp}.json'
                
                with open(json_file, 'w') as f:
                    json.dump(config_snapshot, f, indent=2)
                json_files.append(json_file)

        # Also export config snapshot to metadata export folder (perRun)
        export_metadata_path = resolve_path(self.config.get('EXPORT_METADATA_PATH', ''))
        if export_metadata_path and os.path.exists(export_metadata_path):
            perrun_dir = os.path.join(export_metadata_path, "perRun")
            os.makedirs(perrun_dir, exist_ok=True)
            export_file = os.path.join(perrun_dir, f'config_snapshot_{timestamp}.json')
            with open(export_file, 'w') as f:
                json.dump(config_snapshot, f, indent=2)
            json_files.append(export_file)
            print(f"Config snapshot exported to: {export_file}")

        return json_files
    
    def run_setup(self):
        print("Temperature Monitoring Framework - Setup")
        print("=" * 40)
        
        # Create virtual environment
        self.create_virtual_environment()
        
        # Create directory structure
        self.create_directory_structure()
        
        # Create config snapshot
        self.create_config_snapshot()
        
        # Final instructions
        #venv_path = self.base_dir / self.config['VENV_NAME'] HAVE TO ALSO CHANGE THIS SO THAT TEMP ENV IS ONLY IN SCRIPTED WORKFLOW TBA
        venv_path = Path(self.config['WORKFLOW_DIRECTORY']) / self.config['VENV_NAME']
        
        print("\nSETUP COMPLETE")
        print(f"Framework Location: {self.base_dir}")
        print(f"Virtual Environment: {venv_path}")
        
        print("\nTo activate:")
        if sys.platform == "win32":
            print(f"  {venv_path}\\Scripts\\activate")
        else:
            print(f"  source {venv_path}/bin/activate")
        
        print("\nNext Steps:")
        print("1. Activate virtual environment")
        print("2. Place HOBO files in year/monitoring_type/01_HOBO_OUT/")
        print("3. Run processing scripts")
        
        return True

def main():
    setup = FrameworkSetup()
    setup.run_setup()

if __name__ == "__main__":
    main() 