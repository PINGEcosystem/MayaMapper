'''
Copyright (c) 2025 Cameron S. Bodine
'''

#########
# Imports
import os, sys


def _preload_windows_torch_backend():
    if os.name != 'nt':
        return

    _prepare_windows_torch_runtime()

    try:
        import torch  # noqa: F401
    except (ImportError, OSError):
        # seg_torch.py raises a more actionable error message if torch is required later.
        pass


def _prepare_windows_torch_runtime():
    if os.name != 'nt':
        return

    os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')

    torch_lib_dir = os.path.join(sys.prefix, 'Lib', 'site-packages', 'torch', 'lib')
    if os.path.isdir(torch_lib_dir):
        os.environ['PATH'] = torch_lib_dir + os.pathsep + os.environ.get('PATH', '')
        try:
            os.add_dll_directory(torch_lib_dir)
        except Exception:
            pass


def _prepare_windows_geo_runtime():
    if os.name != 'nt':
        return

    share_dir = os.path.join(sys.prefix, 'Library', 'share')
    gdal_data_dir = os.path.join(share_dir, 'gdal')
    proj_data_dir = os.path.join(share_dir, 'proj')

    if os.path.isdir(gdal_data_dir):
        os.environ.setdefault('GDAL_DATA', gdal_data_dir)

    if os.path.isdir(proj_data_dir):
        os.environ.setdefault('PROJ_LIB', proj_data_dir)


_prepare_windows_torch_runtime()
_preload_windows_torch_backend()
_prepare_windows_geo_runtime()

from osgeo import gdal
gdal.PushErrorHandler('CPLQuietErrorHandler')

# Add the package root to the path, may not need after pypi package...
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.append(PACKAGE_DIR)

# Set GHOSTVISION utils dir
USER_DIR = os.path.expanduser('~')
GV_UTILS_DIR = os.path.join(USER_DIR, '.mayamapper')
if not os.path.exists(GV_UTILS_DIR):
    os.makedirs(GV_UTILS_DIR)

# Default function to run
if len(sys.argv) == 1:
    to_do = 'gui'
else:
    to_do = sys.argv[1]

#=======================================================================
def main(process):
    '''
    '''

    from mayamapper.version import __version__
    print("\n\nMayaMapper v{}".format(__version__))

    # Launch GUI
    if process == 'gui':
        print('\n\nLaunching MayaMapper gui...\n\n')

        from mayamapper.gui_main import gui
        gui()

    return

#=======================================================================
if __name__ == "__main__":
    main(to_do)

