"""
Launch script for Blender with MCP addon.
Run with: xvfb-run blender --python start_blender_mcp.py
This keeps Blender running with the socket server on port 9876.
"""
import bpy
import sys
import os

# Add project root to path so the addon can be found
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load and register the addon
exec(open(os.path.join(project_root, "blender_addon.py")).read())
register()

print("=" * 60)
print("Blender MCP server starting on port 9876...")
print("Blender will stay running. Kill this process to stop.")
print("=" * 60)
