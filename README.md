# Splunk Cloud App Exporter

Export apps from Splunk Cloud Victoria Experience using the Admin Config Service (ACS) API.

## Features

✅ **Export single apps or all apps**
✅ **Directory selection**: local/, default/, users/
✅ **Local-only exports** (custom configurations only)
✅ **Environment variable authentication**
✅ **Bulk operations with progress tracking**
✅ **Automatic Splunkbase app filtering**

## Quick Start

```bash
# Set your JWT token (get from Splunk Cloud Settings > Tokens)
export SPLUNK_ACS_TOKEN="your-jwt-token-here"

# Export all apps (local configs only) - RECOMMENDED
python3 export_splunk_app.py --stack gw --export-all --local-only

# Export a single app
python3 export_splunk_app.py --stack gw --app AAA_search

# List all available apps
python3 export_splunk_app.py --stack gw --list-apps
```

## Command Line Options

```bash
python3 export_splunk_app.py --help
```

### Core Options
- `--stack STACK` - Your Splunk Cloud stack name (required)
- `--token TOKEN` - JWT token (or set SPLUNK_ACS_TOKEN env var)
- `--app APP` - Single app name to export
- `--output-dir DIR` - Output directory (default: current directory)

### Bulk Operations
- `--export-all` - Export all apps
- `--list-apps` - List all available apps
- `--include-splunkbase` - Include Splunkbase apps in bulk export

### Directory Selection
- `--local-only` - Export only local/ directory (custom configs)
- `--include-default` - Include default/ directory (enabled by default)
- `--include-users` - Include users/ directory

## Common Use Cases

### 1. Backup All Custom Configurations (Recommended)

Export just the `local/` directories from all apps - this contains your custom configurations without the bloat of default files:

```bash
export SPLUNK_ACS_TOKEN="your-token"
python3 export_splunk_app.py --stack gw --export-all --local-only --output-dir ./local_configs
```

**Benefits:**
- ✅ Faster downloads (smaller files)
- ✅ Only your customizations
- ✅ Perfect for configuration backup
- ✅ Excludes Splunkbase apps automatically

### 2. Full App Backup

Export complete apps including default configurations:

```bash
export SPLUNK_ACS_TOKEN="your-token"
python3 export_splunk_app.py --stack gw --export-all --output-dir ./full_apps
```

### 3. Single App Export

Export a specific app:

```bash
export SPLUNK_ACS_TOKEN="your-token"

# Local configs only
python3 export_splunk_app.py --stack gw --app AAA_search --local-only

# Full app
python3 export_splunk_app.py --stack gw --app AAA_search
```

### 4. Migration/Development Workflow

```bash
export SPLUNK_ACS_TOKEN="your-token"

# 1. List apps to see what's available
python3 export_splunk_app.py --stack gw --list-apps

# 2. Export specific development apps (local configs only)
python3 export_splunk_app.py --stack gw --app my_custom_app --local-only --output-dir ./dev_exports

# 3. Export all for full backup
python3 export_splunk_app.py --stack gw --export-all --local-only --output-dir ./backup_$(date +%Y%m%d)
```

## Output

The script downloads `.spl` files (standard Splunk app packages) that can be:
- ✅ Installed on other Splunk instances
- ✅ Unpacked with `tar -xzf app.spl`
- ✅ Validated with `splunk-appinspect`
- ✅ Version controlled

## Error Handling

The script handles common issues:
- ✅ **Invalid tokens** - Clear error messages
- ✅ **Missing apps** - Skips and continues
- ✅ **Network issues** - Retry suggestions
- ✅ **Bulk failures** - Summary at end

Some apps may fail export due to:
- Empty local/ directories (when using --local-only)
- Permission restrictions
- App-specific limitations

## Security Notes

- 🔒 **Never commit tokens to version control**
- 🔄 **Rotate JWT tokens regularly**
- 🎯 **Use least-privilege tokens** (only required ACS permissions)
- 📁 **Store exports securely** (they contain your configurations)

## Requirements

- Python 3.6+
- `requests` library: `pip install requests`
- Valid Splunk Cloud Victoria Experience deployment
- JWT token with ACS app export permissions

## Creating JWT Tokens

1. Log in to your Splunk Cloud deployment
2. Go to **Settings > Tokens**
3. Create new token with **ACS** permissions
4. Copy the token value
5. Set as `SPLUNK_ACS_TOKEN` environment variable

## Troubleshooting

### "operation only supported for splunk stack on Classic Experience"
- ✅ **Fixed in this version** - Uses correct Victoria Experience endpoints

### "Authentication failed: Invalid or expired JWT token"
- 🔄 Create a new token in Splunk Cloud
- ✅ Verify token has ACS permissions

### Apps failing to export with 400 errors
- ℹ️ Normal for apps with empty local/ directories when using `--local-only`
- ✅ Check export summary for successful vs failed apps

---

**Happy Splunking!** 🚀
