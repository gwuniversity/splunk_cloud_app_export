#!/usr/bin/env python3
"""
Splunk Cloud Admin Config Service App Exporter

This script uses the Splunk Cloud Admin Config Service to export non-splunkbase apps.
It prompts for an app name and downloads the app package.

Requirements:
- requests library (pip install requests)
- Valid JWT authentication token for Splunk Cloud ACS
- Access to the Admin Config Service

To create a JWT token:
1. Log in to your Splunk Cloud Platform deployment
2. Go to Settings > Tokens
3. Create a new token with appropriate permissions

Authentication:
- Set SPLUNK_ACS_TOKEN environment variable with your JWT token, OR
- Provide token when prompted interactively
"""

import requests
import json
import getpass
import sys
import os
from urllib.parse import urljoin
import argparse

class SplunkCloudAppExporter:
    def __init__(self, stack_name, auth_token=None):
        self.stack_name = stack_name
        self.base_url = f"https://admin.splunk.com/{stack_name}/adminconfig/v2/"
        self.session = requests.Session()
        self.auth_token = auth_token
    
    def authenticate(self):
        """Authenticate with Splunk Cloud Admin Config Service using JWT token"""
        if not self.auth_token:
            # Check for environment variable first
            self.auth_token = os.getenv('SPLUNK_ACS_TOKEN')
            if self.auth_token:
                print("Using JWT token from SPLUNK_ACS_TOKEN environment variable")
            else:
                self.auth_token = getpass.getpass("Enter your ACS JWT authentication token: ")
        
        if not self.auth_token:
            print("✗ No authentication token provided")
            print("  Set SPLUNK_ACS_TOKEN environment variable or provide token when prompted")
            return False
        
        # Set the authorization header with the JWT token
        self.session.headers.update({
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Test authentication by trying to list apps
        try:
            test_url = urljoin(self.base_url, "apps/victoria")
            response = self.session.get(test_url)
            response.raise_for_status()
            
            print("✓ Successfully authenticated with Splunk Cloud ACS")
            return True
                
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 401:
                    print("✗ Authentication failed: Invalid or expired JWT token")
                elif e.response.status_code == 403:
                    print("✗ Authentication failed: Insufficient permissions")
                    try:
                        error_body = e.response.text
                        print(f"Response body: {error_body}")
                    except:
                        pass
                else:
                    print(f"✗ Authentication failed: HTTP {e.response.status_code} - {e}")
                    try:
                        error_body = e.response.text
                        print(f"Response body: {error_body}")
                    except:
                        pass
            else:
                print(f"✗ Authentication failed: {e}")
            return False
    
    def list_apps(self):
        """List all apps in the Splunk Cloud instance (handles pagination)"""
        apps_url = urljoin(self.base_url, "apps/victoria")
        all_apps = []
        offset = 0
        count = 100  # Request 100 apps per page (higher than default 30)
        
        while True:
            params = {
                'count': count,
                'offset': offset
            }
            
            try:
                response = self.session.get(apps_url, params=params)
                response.raise_for_status()
                
                apps_data = response.json()
                apps_batch = apps_data.get('apps', [])
                
                if not apps_batch:
                    # No more apps to retrieve
                    break
                
                all_apps.extend(apps_batch)
                
                # Check if we got fewer apps than requested (indicates last page)
                if len(apps_batch) < count:
                    break
                    
                # Move to next page
                offset += count
                
                # Optional: show progress for large app lists
                if offset > count:  # Don't show for first batch
                    print(f"  Retrieved {len(all_apps)} apps so far...")
                
            except requests.exceptions.RequestException as e:
                print(f"✗ Failed to list apps (offset {offset}): {e}")
                break
        
        print(f"Total apps found: {len(all_apps)}")
        return all_apps
    
    def get_app_info(self, app_name):
        """Get detailed information about a specific app"""
        app_url = urljoin(self.base_url, f"apps/victoria/{app_name}")
        
        try:
            response = self.session.get(app_url)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to get app info for '{app_name}': {e}")
            return None
    
    def export_app(self, app_name, output_dir=".", local_only=False, include_default=True, include_users=False):
        """Export/download a specific app"""
        print(f"Checking if app '{app_name}' exists...")
        
        # First, verify the app exists and get its info
        app_info = self.get_app_info(app_name)
        if not app_info:
            print(f"✗ App '{app_name}' not found or inaccessible")
            return False
        
        # Check if it's a non-splunkbase app
        app_details = app_info.get('app', {})
        is_splunkbase = app_details.get('is_splunkbase_app', False)
        
        if is_splunkbase:
            print(f"⚠ Warning: '{app_name}' appears to be a Splunkbase app")
            proceed = input("Do you want to continue anyway? (y/N): ").lower()
            if proceed != 'y':
                print("Export cancelled")
                return False
        
        # Build query parameters for directory selection
        params = {}
        if local_only:
            params['local'] = 'true'
            params['default'] = 'false'
            params['users'] = 'false'
            print(f"  Exporting local/ directory only")
        else:
            params['local'] = 'true'  # Always include local
            params['default'] = 'true' if include_default else 'false'
            params['users'] = 'true' if include_users else 'false'
            dirs = []
            if params['local'] == 'true':
                dirs.append('local/')
            if params['default'] == 'true':
                dirs.append('default/')
            if params['users'] == 'true':
                dirs.append('users/')
            print(f"  Exporting directories: {', '.join(dirs)}")
        
        # Export the app
        export_url = urljoin(self.base_url, f"apps/victoria/export/download/{app_name}")
        
        try:
            print(f"Downloading app '{app_name}'...")
            response = self.session.get(export_url, params=params, stream=True)
            response.raise_for_status()
            
            # Determine filename
            filename = f"{app_name}.spl"
            if 'content-disposition' in response.headers:
                import re
                cd = response.headers['content-disposition']
                filename_match = re.search(r'filename="?([^"]+)"?', cd)
                if filename_match:
                    filename = filename_match.group(1)
            
            output_path = os.path.join(output_dir, filename)
            
            # Download the file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(output_path)
            print(f"✓ Successfully downloaded '{app_name}' to '{output_path}' ({file_size} bytes)")
            
            # Optionally run app validation if splunk-appinspect is available
            if self.check_appinspect_available():
                validate = input("Would you like to validate the app with splunk-appinspect? (y/N): ").lower()
                if validate == 'y':
                    self.validate_app(output_path)
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to export app '{app_name}': {e}")
            return False
    
    def check_appinspect_available(self):
        """Check if splunk-appinspect is available"""
        try:
            import subprocess
            result = subprocess.run(['splunk-appinspect', '--version'], 
                                 capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def validate_app(self, app_path):
        """Validate the downloaded app using splunk-appinspect"""
        try:
            import subprocess
            print(f"Validating {app_path} with splunk-appinspect...")
            
            cmd = ['splunk-appinspect', 'inspect', app_path, '--mode', 'precert', '--included-tags', 'cloud']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✓ App validation passed")
            else:
                print("⚠ App validation found issues:")
                print(result.stdout)
                if result.stderr:
                    print(result.stderr)
            
        except Exception as e:
            print(f"✗ Failed to validate app: {e}")
    
    def export_all_apps(self, output_dir=".", local_only=False, include_default=True, include_users=False, skip_splunkbase=True):
        """Export all apps from the Splunk Cloud instance"""
        print("Retrieving list of all apps...")
        apps = self.list_apps()
        
        if not apps:
            print("✗ No apps found or unable to retrieve app list")
            return False
        
        # Filter apps if needed
        apps_to_export = []
        skipped_apps = []
        
        for app in apps:
            app_name = app.get('name', 'Unknown')
            is_splunkbase = app.get('is_splunkbase_app', False)
            
            if skip_splunkbase and is_splunkbase:
                skipped_apps.append(f"{app_name} (Splunkbase)")
                continue
                
            apps_to_export.append(app_name)
        
        print(f"Found {len(apps_to_export)} apps to export")
        if skipped_apps:
            print(f"Skipping {len(skipped_apps)} Splunkbase apps: {', '.join(skipped_apps[:5])}{'...' if len(skipped_apps) > 5 else ''}")
        
        if not apps_to_export:
            print("✗ No apps to export after filtering")
            return False
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Export each app
        successful_exports = []
        failed_exports = []
        
        for i, app_name in enumerate(apps_to_export, 1):
            print(f"\n[{i}/{len(apps_to_export)}] Exporting {app_name}...")
            
            success = self.export_app(
                app_name, 
                output_dir, 
                local_only=local_only,
                include_default=include_default,
                include_users=include_users
            )
            
            if success:
                successful_exports.append(app_name)
            else:
                failed_exports.append(app_name)
        
        # Summary
        print(f"\n=== Export Summary ===")
        print(f"✓ Successfully exported: {len(successful_exports)} apps")
        if successful_exports:
            for app in successful_exports[:10]:  # Show first 10
                print(f"  ✓ {app}")
            if len(successful_exports) > 10:
                print(f"  ... and {len(successful_exports) - 10} more")
        
        if failed_exports:
            print(f"✗ Failed to export: {len(failed_exports)} apps")
            for app in failed_exports:
                print(f"  ✗ {app}")
        
        return len(failed_exports) == 0

def main():
    parser = argparse.ArgumentParser(description='Export Splunk Cloud apps using Admin Config Service')
    parser.add_argument('--stack', required=True, help='Splunk Cloud stack name (e.g., your-stack-name)')
    parser.add_argument('--token', help='ACS JWT authentication token')
    parser.add_argument('--app', help='App name to export (will prompt if not provided)')
    parser.add_argument('--output-dir', default='.', help='Output directory for downloaded apps')
    parser.add_argument('--list-apps', action='store_true', help='List all available apps')
    parser.add_argument('--export-all', action='store_true', help='Export all apps (excluding Splunkbase apps by default)')
    
    # Directory selection options
    parser.add_argument('--local-only', action='store_true', help='Export only local/ directory (custom configurations)')
    parser.add_argument('--include-default', action='store_true', default=True, help='Include default/ directory (default: true)')
    parser.add_argument('--include-users', action='store_true', help='Include users/ directory')
    parser.add_argument('--include-splunkbase', action='store_true', help='Include Splunkbase apps when using --export-all')
    
    args = parser.parse_args()
    
    # Create exporter instance
    exporter = SplunkCloudAppExporter(args.stack, args.token)
    
    # Authenticate
    if not exporter.authenticate():
        sys.exit(1)
    
    # List apps if requested
    if args.list_apps:
        print("\nAvailable apps:")
        apps = exporter.list_apps()
        if apps:
            for app in apps:
                name = app.get('name', 'Unknown')
                title = app.get('title', '')
                is_splunkbase = app.get('is_splunkbase_app', False)
                status = "📦 Splunkbase" if is_splunkbase else "🔧 Custom"
                print(f"  {status} {name} - {title}")
        else:
            print("  No apps found or unable to retrieve app list")
        
        if not args.app and not args.export_all:
            sys.exit(0)
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Handle export all apps
    if args.export_all:
        print("\nExporting all apps...")
        if args.local_only:
            print("Using --local-only: exporting only local/ directories")
        
        success = exporter.export_all_apps(
            output_dir=args.output_dir,
            local_only=args.local_only,
            include_default=args.include_default and not args.local_only,
            include_users=args.include_users,
            skip_splunkbase=not args.include_splunkbase
        )
        
        if success:
            print("\n✓ All apps exported successfully!")
        else:
            print("\n⚠ Some apps failed to export (see summary above)")
            sys.exit(1)
        
        sys.exit(0)
    
    # Handle single app export
    app_name = args.app
    if not app_name:
        app_name = input("\nEnter the name of the app to export: ").strip()
        if not app_name:
            print("No app name provided")
            sys.exit(1)
    
    # Export the single app
    success = exporter.export_app(
        app_name, 
        args.output_dir,
        local_only=args.local_only,
        include_default=args.include_default and not args.local_only,
        include_users=args.include_users
    )
    
    if success:
        print(f"\n✓ App '{app_name}' exported successfully!")
    else:
        print(f"\n✗ Failed to export app '{app_name}'")
        sys.exit(1)

if __name__ == "__main__":
    main()