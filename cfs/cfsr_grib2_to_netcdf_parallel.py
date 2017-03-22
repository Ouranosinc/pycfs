# ipcluster start -n 10

import os
from ipyparallel import Client

import cfsr

# !!! WARNING !!!
# It appears that starting with pygrib 1.9.8, the order of the returned
# grib data has changed, this is fixed in cfsr.py by using data[::-1,:]
# (could have also removed the lats[::-1,0] reorientation, but this would
# break the continuity with previously generated files)
# This code is now only valid for pygrib >1.9.8

# For new variables, need to edit the info in cfsr.py

path_data = '/scen3/stdenis/projects/climate_datasets/cfs2/grb_files'
path_output = '/scen3/stdenis/projects/climate_datasets/cfs2/nc_files'
grib_source = 'rda' # Should be 'rda' or 'nomads'
var_name = 'dlwsfc' # This is the name of the variable in the filename.
grib_var_name = 'Downward long-wave radiation flux' # This is the name in the grib file, can use
                           # gribou.all_str_dump(grib_file) to find it.
grib_level = None # If there is no units in the str dump, set to None.
                  # Otherwise this should be the number before the units.
nc_var_name = 'rlds' # If it is not clear what this is in the CF convention
                         # table, or the units don't match, use the CFSR name.
nc_units = 'W m-2' # Also available from gribou.all_str_dump(grib_file)
nc_format = 'NETCDF4_CLASSIC'
resolution = 'highres' # 'highres' or 'lowres' or 'prmslmidres' or
                       # 'ocnmidres' or 'ocnlowres'. This is determined
                       # by the selection of the grid when obtaining the
                       # files.
initial_year = 2016 # Usually 1979, sometimes the parallel code does not
                    # complete the later files, rerun with final years.
final_year = 2016 # Usually 2010, some ocean files end in 2009.
cache_size = 100

rc = Client()
with rc[:].sync_imports(): import sys
rc[:].execute("sys.path.append('/scen3/stdenis/projects/climate_datasets/cfs2/git/pycfs/cfs')")
with rc[:].sync_imports(): import cfsr
with rc[:].sync_imports(): import gribou

lview = rc.load_balanced_view()

mylviews = []
for yyyy in range(initial_year,final_year+1):
    for mm in ['01','02','03','04','05','06','07','08','09','10','11','12']:
    #for mm in ['12']:
        if resolution in ['highres','prmslmidres','ocnmidres']:
            if (yyyy > 2011) or ((yyyy == 2011) and (int(mm) > 3)):
                grib_file = "%s.cdas1.%s%s.grb2" % (var_name,str(yyyy),mm)
            else:
                grib_file = "%s.gdas.%s%s.grb2" % (var_name,str(yyyy),mm)
            warp = "%s_1hr_cfsr_reanalysis_%s%s.nc" % (nc_var_name,str(yyyy),mm)
            nc_file = os.path.join(path_output,warp)
        elif resolution in ['lowres','ocnlowres']:
            grib_file = "%s.l.gdas.%s%s.grb2" % (var_name,str(yyyy),mm)
            warp = "%s_1hr_cfsr_reanalysis_lowres_%s%s.nc" % (nc_var_name,
                                                              str(yyyy),mm)
            nc_file = os.path.join(path_output,warp)
        grib_file = os.path.join(path_data,grib_file)
        if not os.path.isfile(grib_file):
            continue
        print grib_file
        mylviews.append(lview.apply(cfsr.hourly_grib2_to_netcdf,grib_file,
                                    grib_source,nc_file,nc_var_name,
                                    grib_var_name,grib_level,
                                    cache_size=cache_size,
                                    overwrite_nc_units=nc_units,
                                    nc_format=nc_format))

if nc_var_name in ['tasmin','tasmax']:
    msg1 = "WARNING: this is a cumulative min/max variable, "
    msg2 = "need to run cfsr_sampling.py afterwards."
    print msg1+msg2
