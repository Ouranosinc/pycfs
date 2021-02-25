"""CFSR & CVSv2 conversion

This requires a running UPCluster:

    $ ipcluster start -n 12

"""

import os
from ipyparallel import Client

import cfsr

path_input = '/some/path'
path_output = '/some/path'
path_pycfs = '/some/path'  # The path to cfsr.py and gribou.py
var_names = ['pressfc']  # The RDA archive cfsr dataset prefix
grib_var_names = ['Surface pressure']
"""The grib_var_names can be obtained from gribou.all_str_dump(file_name)"""
grib_levels = [None]
"""The grib levels are set to None if there are no vertical level units
in the groubou.all_str_dump(file_name), otherwise the number is used
(e.g. grib_levels = [2] for one 2 meter variable)"""
nc_var_names = ['ps']
nc_units = ['Pa']
"""nc_var_names can also be obtained in the gribou.all_str_dump(file_name)"""
nc_format = 'NETCDF4_CLASSIC'
initial_year = 1979
final_year = 2010
months = ['01', '02', '03', '04', '05', '06',
          '07', '08', '09', '10', '11', '12']

grib_source = 'rda'
resolution = 'highres'
"""This is related to the grid choice on the rda portal. Generally, if
the higher resolution is selected, set to 'highres'. For lower resolutions,
the file names should have a *.l.gdas.* structure, in this case set to
'lowres'"""
cache_size = 100

rc = Client()
with rc[:].sync_imports():
    import sys
rc[:].execute("sys.path.append('{0}')".format(path_pycfs))
with rc[:].sync_imports():
    import cfsr
with rc[:].sync_imports():
    import gribou

lview = rc.load_balanced_view()

mylviews = []
for i, var_name in enumerate(var_names):
    for yyyy in range(initial_year, final_year + 1):
        for mm in months:
            vym = (var_name, str(yyyy), mm)
            ncvym = (nc_var_names[i], str(yyyy), mm)
            if resolution in ['highres', 'prmslmidres', 'ocnmidres']:
                if (yyyy > 2011) or ((yyyy == 2011) and (int(mm) > 3)):
                    grib_file = "{0}.cdas1.{1}{2}.grb2".format(*vym)
                else:
                    grib_file = "{0}.gdas.{1}{2}.grb2".format(*vym)
                file_name = "{0}_1hr_cfsr_reanalysis_{1}{2}.nc".format(*ncvym)
                nc_file = os.path.join(path_output, file_name)
            elif resolution in ['lowres', 'ocnlowres']:
                grib_file = "{0}.l.gdas.{1}{2}.grb2".format(*vym)
                file_name = "{0}_1hr_cfsr_reanalysis_lowres_{1}{2}.nc".format(
                    *ncvym)
                nc_file = os.path.join(path_output, file_name)
            grib_file = os.path.join(path_input, grib_file)
            if not os.path.isfile(grib_file):
                continue
            print(grib_file)
            mylviews.append(lview.apply(
                cfsr.hourly_grib2_to_netcdf, grib_file, grib_source, nc_file,
                nc_var_names[i], grib_var_names[i], grib_levels[i],
                cache_size=cache_size, overwrite_nc_units=nc_units[i],
                nc_format=nc_format))

    if nc_var_names[i] in ['tasmin','tasmax']:
        print("WARNING: this is a cumulative min/max variable, need to run"
              "cfsr_sampling.py afterwards.")

