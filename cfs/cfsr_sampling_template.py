import os
import glob
import datetime

import netCDF4
import netcdf as nc

variables = ['tasmin', 'tasmax']

path_output = '/some/path'
path_cfsr = '/path/to/hourly/output'
nc_format = 'NETCDF4_CLASSIC'

sampling_start = 5
sampling_step = 6

for var_name in variables:
    nc_files = glob.glob(os.path.join(path_cfsr, var_name, '*'))
    for i, nc_file in enumerate(nc_files):
        warp = os.path.basename(nc_file).replace('1hr', '6hr')
        out_file = os.path.join(path_output, warp)
        ncref = netCDF4.Dataset(nc_file, 'r')
        timeref = ncref.variables['time']
        nt = timeref.shape[0] / sampling_step

        now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        nc1 = netCDF4.Dataset(out_file, 'w', format=nc_format)

        nc.nc_copy_attrs(ncref, nc1,
                         includes=[],
                         excludes=[],
                         renames={},
                         defaults={},
                         appends={'history': "%s: 6 hourly sample." % (now,)})

        nc.nc_copy_dimensions(ncref, nc1,
                              includes=[],
                              excludes=[],
                              renames={},
                              defaults={},
                              reshapes={})

        nc.nc_copy_variables_structure(ncref, nc1,
                                       includes=[],
                                       excludes=[],
                                       renames={},
                                       new_dtype={},
                                       new_dimensions={},
                                       create_args={'_global': {'zlib': True}})

        nc.nc_copy_variables_attributes(ncref, nc1,
                                        includes=[],
                                        excludes=[],
                                        renames={},
                                        attr_excludes={},
                                        attr_defaults={})

        nc.nc_copy_variables_data(ncref, nc1,
                                  includes=[],
                                  excludes=['time', 'time_vectors', var_name],
                                  renames={})

        timeref = timeref[:]
        tvsref = ncref.variables['time_vectors']

        tvsref = tvsref[:, :]
        varref = ncref.variables[var_name]

        varref = varref[...]
        time1 = nc1.variables['time']
        tvs1 = nc1.variables['time_vectors']
        var1 = nc1.variables[var_name]

        time1[:] = timeref[sampling_start::sampling_step]
        tvs1[:, :] = tvsref[sampling_start::sampling_step, :]
        var1[...] = varref[sampling_start::sampling_step, ...]

        ncref.close()
        nc1.close()
