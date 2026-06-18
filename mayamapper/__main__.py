'''
Copyright (c) 2025 Cameron S. Bodine
'''

#########
# Imports
import os, sys

from osgeo import gdal
gdal.PushErrorHandler('CPLQuietErrorHandler')

# Add the package root to the path, may not need after pypi package...
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.append(PACKAGE_DIR)

from pingtile.runtime import prepare_windows_mapper_runtime

prepare_windows_mapper_runtime(preload_torch=True)

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

