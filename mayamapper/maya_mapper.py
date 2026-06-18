'''
Copyright (c) 2025 Cameron S. Bodine
'''

#########
# Imports
import os, sys

from mayamapper.utils import printUsage#, avg_npz_files, map_npzs

# Debug
pingTilePath = os.path.normpath('../PINGTile')
pingTilePath = os.path.abspath(pingTilePath)
sys.path.insert(0, pingTilePath)
sys.path.insert(0, 'src')

pingSegPath = os.path.normpath('../PINGSeg')
pingSegPath = os.path.abspath(pingSegPath)
sys.path.insert(0, pingSegPath)
sys.path.insert(0, 'src')

from pingtile.mapper_workflow import run_mapper_workflow
from pingtile.runtime import prepare_windows_mapper_runtime

prepare_windows_mapper_runtime(preload_torch=True)

# Set MAYAMAPPER utils dir
USER_DIR = os.path.expanduser('~')
GV_UTILS_DIR = os.path.join(USER_DIR, '.mayamapper')
if not os.path.exists(GV_UTILS_DIR):
    os.makedirs(GV_UTILS_DIR)

#=======================================================================
def do_work(
            inDir: str,
            outDirTop: str,
            modelDir: str,
            projName: str,
            mapRast: bool,
            mapShp: bool,
            epsg: int,
            windowSize_m: tuple,
            window_stride: int,
            minArea_percent: float,
            threadCnt: float, 
            mosaicFileType: str,
            predBatchSize: int,
            deleteIntData: bool=True,
            minPatchSize: float=3,
            smoothShp: bool=False,
            smoothTol_m: float=0.5,
        ):
    '''
    '''
    run_mapper_workflow(
        mapper_name='MayaMapper',
        releases_repo='MayaMapper',
        inDir=inDir,
        outDirTop=outDirTop,
        modelDir=modelDir,
        projName=projName,
        mapRast=mapRast,
        mapShp=mapShp,
        epsg=epsg,
        windowSize_m=windowSize_m,
        window_stride=window_stride,
        minArea_percent=minArea_percent,
        threadCnt=threadCnt,
        mosaicFileType=mosaicFileType,
        predBatchSize=predBatchSize,
        deleteIntData=deleteIntData,
        minPatchSize=minPatchSize,
        smoothShp=smoothShp,
        smoothTol_m=smoothTol_m,
        print_usage=printUsage,
        list_mosaics=True,
    )

    return