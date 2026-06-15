'''
Copyright (c) 2025 Cameron S. Bodine
'''

#########
# Imports
import os, sys, time


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

from os import cpu_count
from glob import glob
import pandas as pd
import geopandas as gpd
import json
import shutil
import requests, zipfile
import gc
gc.enable()

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

from pingtile.mosaic2tile import doMosaic2tile
from pingtile.utils import avg_npz_files, map_npzs, mosaic_maps, maps2Shp

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

    _debug = False  # For development/debugging

    start_time = time.time()

    outDir = os.path.join(outDirTop, projName)

    if os.path.exists(outDir) and not _debug:
        shutil.rmtree(outDir)

    if not os.path.exists(outDir):
        os.makedirs(outDir)

    ###########
    # Get model

    seg_model = os.path.basename(modelDir)

    if not os.path.exists(modelDir) or len(os.listdir(modelDir)) == 0:
        os.makedirs(modelDir, exist_ok=True)

        url = f'https://github.com/PINGEcosystem/MayaMapper/releases/download/models/{seg_model}.zip'
        print(f'\n\nDownloading segmentation models (v1.0): {url}')

        filename = modelDir + '.zip'
        try:
            # stream download to avoid memory spikes
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

            # quick validation
            if not zipfile.is_zipfile(filename):
                # read beginning of file to help debug (text/html error pages)
                with open(filename, 'rb') as fh:
                    head = fh.read(512).decode('utf-8', errors='replace')
                os.remove(filename)
                raise RuntimeError(f"Downloaded file is not a zip file. Server response starts with: {head!r}")

            # extract safely
            with zipfile.ZipFile(filename, 'r') as z_fp:
                z_fp.extractall(modelDir)

            os.remove(filename)
            print('Model download and extraction success!')

        except requests.RequestException as e:
            # network/HTTP problem
            if os.path.exists(filename):
                os.remove(filename)
            raise RuntimeError(f"Failed to download model from {url}: {e}") from e
        except zipfile.BadZipFile as e:
            if os.path.exists(filename):
                os.remove(filename)
            raise RuntimeError("Downloaded model archive is corrupted or not a zip file.") from e


    ###############################################
    # Specify multithreaded processing thread count
    if threadCnt==0: # Use all threads
        threadCnt=cpu_count()
    elif threadCnt<0: # Use all threads except threadCnt; i.e., (cpu_count + (-threadCnt))
        threadCnt=cpu_count()+threadCnt
        if threadCnt<0: # Make sure not negative
            threadCnt=1
    elif threadCnt<1: # Use proportion of available threads
        threadCnt = int(cpu_count()*threadCnt)
        # Make even number
        if threadCnt % 2 == 1:
            threadCnt -= 1
    else: # Use specified threadCnt if positive
        pass

    if threadCnt>cpu_count(): # If more than total avail. threads, make cpu_count()
        threadCnt=cpu_count();
        print("\nWARNING: Specified more process threads then available, \nusing {} threads instead.".format(threadCnt))

    # Set Stride
    windowStride_m = windowSize_m
    minArea = minArea_percent * windowSize_m[0]*windowSize_m[1]

    # Delete intermediate data
    to_delete = {}

    # Make output image dir
    dirName = projName
    outDir = os.path.join(outDirTop, dirName)
    outSonDir = os.path.join(outDir, 'images')

    if not os.path.exists(outSonDir):
        os.makedirs(outSonDir)

    # Get the sonar images
    mosaics = glob(os.path.join(inDir, '**', '*{}'.format(mosaicFileType)), recursive=True)

    print('\nFound {} mosaic files.'.format(len(mosaics)))
    for mosaic in mosaics:
        print(mosaic)

    # Get the model config file and load it
    config_candidates = [
        os.path.join(modelDir, 'config.json'),
    ]
    config_candidates += glob(os.path.join(modelDir, 'config', '*.json'))
    config_candidates = [c for c in config_candidates if os.path.exists(c)]

    if not config_candidates:
        raise FileNotFoundError(f"No config file found in model directory: {modelDir}")

    configFile = config_candidates[0]

    with open(configFile) as f:
        config = json.load(f)

    # Detect prediction backend based on model artifacts.
    has_torch_model = os.path.exists(os.path.join(modelDir, 'model.safetensors'))
    has_tf_model = bool(glob(os.path.join(modelDir, 'weights', '*_fullmodel.h5')))

    if has_torch_model:
        pred_backend = 'torch'
    elif has_tf_model:
        pred_backend = 'seg_gym'
    else:
        raise FileNotFoundError(
            f"Could not determine model backend for {modelDir}. "
            "Expected model.safetensors (Transformers) or weights/*_fullmodel.h5 (Segmentation Gym)."
        )

    if 'image_size' in config:
        target_size = (int(config['image_size']), int(config['image_size']))
    elif 'TARGET_SIZE' in config:
        target_size = (int(config['TARGET_SIZE'][0]), int(config['TARGET_SIZE'][1]))
    else:
        target_size = (224, 224)


    
    # # For debug
    # mosaics = mosaics[:1]




    ###############################
    # Generate moving window images

    print('\n\nTiling Mosaics...\n\n')

    imagesAll = []

    for mosaic in mosaics:
        r = doMosaic2tile(
            inFile = mosaic,
            outDir = outSonDir,
            windowSize = windowSize_m,
            windowStride_m = window_stride,
            outName = projName,
            epsg_out = epsg,
            threadCnt = threadCnt,
            target_size = target_size,
            minArea_percent = minArea_percent,
        )

        tile_cnt = len(r) if r is not None else 0
        print(f"Tiles accepted from {os.path.basename(mosaic)}: {tile_cnt}")
        imagesAll.append(r)
    
    imagesDF = pd.concat(imagesAll, axis=0, ignore_index=True)

    # For debug
    outDF = os.path.join(outDir, f'{projName}_{windowSize_m[0]}_{windowSize_m[1]}_tiles.csv')
    if not deleteIntData:
        imagesDF.to_csv(outDF, index=False)

    # Delete intermediate data
    if deleteIntData:
        to_delete['outSonDir'] = [outSonDir]

    print('Image Tiles Generated: {}'.format(len(imagesDF)))
    if len(imagesDF) == 0:
        print('[WARNING] No tiles met inclusion criteria. Check raster nodata/value scale and consider lowering minArea_percent.')

    print("\nDone!")
    print("Time (s):", round(time.time() - start_time, ndigits=1))
    printUsage()


    # For Debug
    if not deleteIntData:
        imagesDF = pd.read_csv(outDF)
        print(len(imagesDF))


    ################################
    # Perform segmentation on images

    print('\n\nPredicting substrate from sonar tiles...\n\n')
    start_time = time.time()

    out_npz = os.path.join(outDir, 'preds_npz')

    if pred_backend == 'torch':
        from pingseg.seg_torch import seg_torch_folder

        imagesDF = seg_torch_folder(
            imgDF=imagesDF,
            modelDir=modelDir,
            out_dir=out_npz,
            batch_size=predBatchSize,
            threadCnt=threadCnt,
        )
    else:
        from pingseg.seg_gym import seg_gym_folder

        imagesDF = seg_gym_folder(
            imgDF=imagesDF,
            modelDir=modelDir,
            out_dir=out_npz,
            batch_size=predBatchSize,
            threadCnt=threadCnt,
        )

    # For debug
    outDF = os.path.join(outDir, f'{projName}_{windowSize_m[0]}_{windowSize_m[1]}_tileseg.csv')
    if not deleteIntData:
        imagesDF.to_csv(outDF, index=False)

    # Delete intermediate data
    if deleteIntData:
        to_delete['out_npz'] = [out_npz]

        # Delete tiled images
        shutil.rmtree(outSonDir, ignore_errors=True)


    print("\nPrediction Complete!")
    print("Time (s):", round(time.time() - start_time, ndigits=1))
    printUsage()



    # For debug
    out_npz = os.path.join(outDir, 'preds_npz')
    outDF = os.path.join(outDir, f'{projName}_{windowSize_m[0]}_{windowSize_m[1]}_tileseg.csv')
    if not deleteIntData:
        imagesDF = pd.read_csv(outDF)

    ###############################
    # Average overlapping npz files
    print('\n\nAveraging overlapping substrate predictions...\n\n')
    start_time = time.time()

    out_avg_npz = os.path.join(outDir, 'preds_avg_npz')

    if not os.path.exists(out_avg_npz):
        os.makedirs(out_avg_npz)

    gdf = avg_npz_files(df=imagesDF, in_dir=out_npz, out_dir=out_avg_npz, outName=projName, windowSize_m=windowSize_m, stride=windowSize_m[0], epsg=epsg, threadCnt=threadCnt)

    # # Debug: Save df
    outDF = os.path.join(outDir, f'{projName}_{windowSize_m[0]}_{windowSize_m[1]}_avgnpz.csv')
    if not deleteIntData:
        gdf.to_csv(outDF, index=False)

    # Delete intermediate data
    if deleteIntData:
        to_delete['out_avg_npz'] = [out_avg_npz]

        # Delete npz predictions
        shutil.rmtree(out_npz, ignore_errors=True)

    print("\nDone!")
    print("Time (s):", round(time.time() - start_time, ndigits=1))
    printUsage()


    # For debug
    out_avg_npz = os.path.join(outDir, 'preds_avg_npz')
    outDF = os.path.join(outDir, f'{projName}_{windowSize_m[0]}_{windowSize_m[1]}_avgnpz.csv')
    if not deleteIntData:
        gdf = pd.read_csv(outDF)


    #######################
    # Map average npz files
    print('\n\nMapping predicted substrate...\n\n')
    start_time = time.time()

    out_maps = os.path.join(outDir, 'preds_mapped')

    if not os.path.exists(out_maps):
        os.makedirs(out_maps)

    # For minPatchSize in map tile, use 1/4 the minPatchSize to remedy hard edge between tiles
    minPatchSize_tile = minPatchSize / 4.0

    gdf = map_npzs(df=gdf, in_dir=out_avg_npz, out_dir=out_maps, outName=projName, minPatchSize=minPatchSize_tile, windowSize_m=windowSize_m, epsg=epsg, threadCnt=threadCnt)

    # Delete intermediate data
    if deleteIntData:
        # Delete avg npz predictions
        shutil.rmtree(out_avg_npz, ignore_errors=True)

    print("\nDone!")
    print("Time (s):", round(time.time() - start_time, ndigits=1))
    printUsage()


    # Debug: Save df
    outDF = os.path.join(outDir, f'{projName}_{windowSize_m[0]}_{windowSize_m[1]}_mapped_npzs.csv')
    if not deleteIntData:
        gdf.to_csv(outDF, index=False) 

    # Queue mapped tiles for cleanup after exports complete
    if deleteIntData:
        to_delete['out_maps'] = [out_maps]

    #############
    # Mosaic maps

    if mapRast:

        print('\n\nExport map as raster mosaic...\n\n')
        start_time = time.time()

        map_files = glob(os.path.join(out_maps, '*.tif'))

        out_mosaic = os.path.join(outDir, 'mosaic')

        if not os.path.exists(out_mosaic):
            os.makedirs(out_mosaic)

        mosaic_maps(map_files, out_mosaic, projName)

        print("\nDone!")
        print("Time (s):", round(time.time() - start_time, ndigits=1))
        printUsage()

    ###################
    # Maps to Shapefile

    if mapShp:

        print('\n\nExport map as shapefile...\n\n')
        start_time = time.time()

        map_files = glob(os.path.join(out_maps, '*.tif'))

        out_shp = os.path.join(outDir, 'map_shp')

        if not os.path.exists(out_shp):
            os.makedirs(out_shp)

        maps2Shp(map_files, out_shp, projName, configFile, minPatchSize, [1], smoothShp, smoothTol_m)

        print("\nDone!")
        print("Time (s):", round(time.time() - start_time, ndigits=1))
        printUsage()


    ##########################
    # Delete intermediate data

    # First do garbage collection to close any open files
    gc.collect()

    if deleteIntData:
        print('\n\nDeleting intermediate data...\n\n')
        start_time = time.time()

        for name, paths in to_delete.items():
            for path in paths:
                print(f"Deleting intermediate data: {name} -> {path}")
                shutil.rmtree(path, ignore_errors=True)

        print("\nDone!")
        print("Time (s):", round(time.time() - start_time, ndigits=1))
        printUsage()

    return