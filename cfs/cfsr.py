import datetime

import numpy as np
import numpy.ma as ma
import netCDF4
import ouranos.formats.netcdf as nc
from ouranos.utils.timely import CalGregorian
import gribou

# Step 1: gribou.all_str_dump(grib_file) of a sample file.

# Orography example :
# cfsr.fixed_grib2_to_netcdf('flxf01.gdas.1979010100.grb2',
#                            'orog_fx_cfsr_reanalysis.nc','orog',
#                            grib_var_name='Orography',overwrite_nc_units='m')

# Land-sea mask example :
# cfsr.fixed_grib2_to_netcdf('flxf01.gdas.1979010100.grb2',
#                            'sftlf_fx_cfsr_reanalysis.nc','sftlf',
#                            grib_var_name='Land-sea mask',
#                            overwrite_nc_units='1')

# Usually need to overwrite units. Also, accumulation variables are converted
# to rate (s-1).

# Note that when analysis is not present, the first timestep in an hourly file
# is at 1h, the last time step is at 0h on the first day of the next month.

standard_names = {'catsn':'categorical_snow_table_4.222', # force units to N/A,
                  'clt':'cloud_area_fraction', # force units to 1, fix below.
                  'depthBelowSea':'depth',
                  'dewpt':'dew_point_temperature',
                  'gflux':'ground_heat_flux',
                  'heightAboveGround':'height',
                  'hfls':'surface_upward_latent_heat_flux',
                  'hurs':'relative_humidity',
                  'huss':'specific_humidity',
                  'mrro':'runoff_flux', # force units to kg m-2 s-1
                  'ocnsal15':'ocean_salinity',
                  'ocnsal5':'ocean_salinity',
                  'ocnslh':'sea_surface_height_above_geoid',
                  'ocnsst5':'sea_water_potential_temperature',
                  'ocnt15':'sea_water_potential_temperature',
                  'ocnu15':'eastward_sea_water_velocity',
                  'ocnu5':'eastward_sea_water_velocity',
                  'ocnv15':'northward_sea_water_velocity',
                  'ocnv5':'northward_sea_water_velocity',
                  'orog':'surface_altitude', # force units to m
                  'phis':'geopotential_height',
                  'pr':'precipitation_flux',
                  'ps':'surface_air_pressure',
                  'psl':'air_pressure_at_sea_level',
                  'rlds':'surface_downwelling_longwave_flux_in_air',
                  'rlus':'surface_upwelling_longwave_flux_in_air',
                  'rsds':'surface_downwelling_shortwave_flux_in_air',
                  'rsus':'surface_upwelling_shortwave_flux_in_air',
                  'sic':'sea_ice_area_fraction', # force units to 1
                  'sit':'sea_ice_thickness',
                  'sftlf':'land_area_fraction', # force units to 1
                  'snw':'surface_snow_amount',
                  'tas':'air_temperature',
                  'tasmax':'air_temperature',
                  'tasmin':'air_temperature',
                  'ts':'surface_temperature',
                  'uas':'eastward_wind',
                  'vas':'northward_wind',}

variable_keys = ['standardDeviation','month','endStep','dataDate','day','year',
                 'validityTime','codedValues','stepRange','skewness',
                 'latLonValues','kurtosis','totalLength','forecastTime',
                 'startStep','values','julianDay','section7Length',
                 'validityDate','average','minimum','maximum','hour',
                 'dataTime']

defi2 = netCDF4.default_fillvals['i2']
defi4 = netCDF4.default_fillvals['i4']
deff4 = netCDF4.default_fillvals['f4']

class CFSRVariable:
    """CFSR variable definition."""

    def __init__(self,grib_msg_dict):
        """Initialize CFSR variable.

        Parameters
        ----------
        grib_msg_dict : dictionary

        """

        self.grib_msg_dict = {}
        for key in grib_msg_dict.keys():
            self.grib_msg_dict[key] = grib_msg_dict[key]
        self.name = self.grib_msg_dict['name']
        if self.name != self.grib_msg_dict['parameterName']:
            msg1 = "Name mismatch between 'name' and 'parameterName': " 
            msg2 = "%s vs %s" % (self.name,self.grib_msg_dict['parameterName'])
            #raise NotImplementedError(msg1+msg2)
            print msg1+msg2
        if self.name != self.grib_msg_dict['nameECMF']:
            msg1 = "Name mismatch between 'name' and 'nameECMF': " 
            msg2 = "%s vs %s" % (self.name,self.grib_msg_dict['nameECMF'])
            #raise NotImplementedError(msg1+msg2)
            print msg1+msg2
        self.units = self.grib_msg_dict['units'].replace('**','')
        if self.units != self.grib_msg_dict['parameterUnits'].replace('**',''):
            msg1 = "Unit mismatch between 'units' and 'parameterUnits': " 
            warp = (self.units,self.grib_msg_dict['parameterUnits'])
            msg2 = "%s vs %s" % warp
            #raise NotImplementedError(msg1+msg2)
            print msg1+msg2
        if self.units != self.grib_msg_dict['unitsECMF'].replace('**',''):
            msg1 = "Unit mismatch between 'units' and 'unitsECMF': " 
            msg2 = "%s vs %s" % (self.units,self.grib_msg_dict['unitsECMF'])
            #raise NotImplementedError(msg1+msg2)
            print msg1+msg2
        self.statistic = self.grib_msg_dict['stepType']
        if self.statistic != self.grib_msg_dict['stepTypeInternal']:
            msg1 = "Stat mismatch between 'stepType' and 'stepTypeInternal': " 
            warp = (self.statistic,self.grib_msg_dict['stepTypeInternal'])
            msg2 = "%s vs %s" % warp
            raise NotImplementedError(msg1+msg2)
        self.vertical_type = self.grib_msg_dict['typeOfLevel']
        self.vertical_units = self.grib_msg_dict['unitsOfFirstFixedSurface']
        if self.vertical_units == 'unknown':
            self.vertical_units = None
            self.level = None
        else:
            warp1 = self.grib_msg_dict['scaleFactorOfFirstFixedSurface']
            warp2 = self.grib_msg_dict['scaledValueOfFirstFixedSurface']
            level1 = warp2/float(10**warp1)
            if self.grib_msg_dict['unitsOfSecondFixedSurface'] == 'unknown':
                self.level = level1
            else:
                warp1 = self.grib_msg_dict['scaleFactorOfSecondFixedSurface']
                warp2 = self.grib_msg_dict['scaledValueOfSecondFixedSurface']
                level2 = warp2/float(10**warp1)
                self.level = (level1,level2)

    def __eq__(self,other):
        for key in self.grib_msg_dict.keys():
            if key not in other.grib_msg_dict.keys():
                return False
            if key in variable_keys:
                continue
            try:
                if self.grib_msg_dict[key] != other.grib_msg_dict[key]:
                    return False
            except ValueError:
                if (self.grib_msg_dict[key] != other.grib_msg_dict[key]).any():
                    return False
        for key in other.grib_msg_dict.keys():
            if key not in self.grib_msg_dict.keys():
                return False

    def __ne__(self,other):
        if self.__eq__(other):
            return False
        else:
            return True

def optimal_chunksizes(nt,nlat,nlon):
    """Optimal chunksizes for hourly data in a monthly file.

    Parameters
    ----------
    nt : int
    nlat : int
    nlon : int

    Returns
    -------
    out : tuple of int

    Notes
    -----
    This is for large grids, where files already contain only on month,
    so the chunksize in the time dimension is the number of timesteps.

    """

    clon = np.sqrt(1000000.0*nlon/(nlat*nt))
    clat = nlat*clon/nlon
    return (nt,int(np.ceil(clat)),int(np.ceil(clon)))

def filter_var_timesteps(list_of_msg_dicts,grib_var_name,grib_level,
                         include_analysis=True):
    """Find message ids that will create a timeserie for a given variable.

    Parameters
    ----------
    list_of_msg_dicts : list of dictionaries
    grib_var_name : string
    grib_level : float
    include_analysis : bool

    Returns
    -------
    out1,out2 : list of int, bool
        out1 is the list of message ids that create the timeseries,
        out2 is whether or not the 6hr timestep is skipped.

    """

    list_of_i = []
    analysis = 'unknown'
    skip_6 = False
    for j,msg_dict in enumerate(list_of_msg_dicts):
        cfsr_var = CFSRVariable(msg_dict)
        if cfsr_var.name != grib_var_name:
            continue
        if cfsr_var.level != grib_level:
            continue
        if (msg_dict['startStep'] == 0) and (msg_dict['endStep'] == 0):
            # assume this is the analysis, expect another instance afterward
            if analysis == 'unknown':
                analysis = 'candidate'
            elif analysis == 'candidate':
                # all is well, we have the 3min spinup afterward, which we
                # ignore. Reset analysis to unknown.
                if include_analysis:
                    list_of_i.append(j-1)
                    skip_6 = True
                analysis = 'unknown'
        elif analysis == 'candidate':
            # the candidate is not the analysis, reset analysis
            analysis = 'unknown'
        if (msg_dict['startStep'] == 6) and (msg_dict['endStep'] == 6):
            if not skip_6:
                list_of_i.append(j)
        elif (msg_dict['startStep'] != 0) or (msg_dict['endStep'] != 0):
            list_of_i.append(j)
    return list_of_i,skip_6

def hourly_grib2_to_netcdf(grib_file,grib_source,nc_file,nc_var_name,
                           grib_var_name,grib_level,cache_size=100,
                           initial_year=1979,overwrite_nc_units=None,
                           include_analysis=True,
                           nc_format='NETCDF4'):
    """Convert hourly data from GRIB file containing one month to NetCDF.

    Parameters
    ----------
    grib_file : string
    grib_source : string
        The two most common sources are 'rda' and 'nomads'.
    nc_file : string
    nc_var_name : string
    grib_var_name : string
    grib_level : float
    cache_size : int, optional
    initial_year : int, optional
    overwrite_nc_units : string, optional
    include_analysis : bool, optional
    nc_format : string, optional

    Notes
    -----
    Currently only implemented for 2d fields.

    """

    list_of_msg_dicts = gribou.get_all_msg_dict(grib_file)
    list_of_i,analysis_present = filter_var_timesteps(list_of_msg_dicts,
                                                      grib_var_name,
                                                      grib_level,
                                                      include_analysis)
    cfsr_var = CFSRVariable(list_of_msg_dicts[list_of_i[0]])
    lats,lons = gribou.get_latlons(grib_file,list_of_i[0]+1)

    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    nc1 = netCDF4.Dataset(nc_file,'w',format=nc_format)
    
    nc1.Conventions = 'CF-1.5'
    nc1.title = 'Climate System Forecast Reanalysis'
    nc1.history = "%s: Convert from grib2 to NetCDF" % (now,)
    nc1.institution = 'NCEP'
    nc1.source = 'Reanalysis'
    nc1.references = 'http://cfs.ncep.noaa.gov/cfsr/'
    if analysis_present:
        msg1 = "Obtained from %s server, " % (grib_source,)
        msg2 = "analysis is included, 6h forecast removed."
        nc1.comment = msg1+msg2
    else:
        msg1 = "Obtained from %s server, " % (grib_source,)
        msg2 = "no analysis, 6h forecast is included."
        nc1.comment = msg1+msg2
    nc1.redistribution = "Free to redistribute."
    
    nc1.createDimension('time',None)
    nc1.createDimension('timecomp',6)
    nc1.createDimension('lat',lats.shape[0])
    nc1.createDimension('lon',lats.shape[1])
    
    nc1.createVariable('timecomp','i2',('timecomp',),zlib=True,fill_value=defi2)
    
    time = nc1.createVariable('time','i4',('time',),zlib=True)
    time.axis = 'T'
    if initial_year is None:
        warp = (str(cfsr_var.grib_msg_dict['year']),)
    else:
        warp = (initial_year,)
    time.units = "hours since %s-01-01 00:00:00" % warp
    time.long_name = 'time'
    time.standard_name = 'time'
    time.calendar = 'gregorian'
    
    time_vectors = nc1.createVariable('time_vectors','i2',('time','timecomp'),
                                      zlib=True)
    
    vtype = cfsr_var.vertical_type
    if vtype in ['depthBelowSea','heightAboveGround']:
        try:
            dummy = len(cfsr_var.level)
            bounds = True
        except:
            bounds = False
        else:
            nc1.createDimension('nv',2)
        level = nc1.createVariable('level','f4',(),zlib=True)
        level.axis = 'Z'
        level.units = cfsr_var.vertical_units
        if vtype == 'depthBelowSea':
            level.positive = 'up'
        else:
            level.positive = 'down'
        level.long_name = vtype
        level.standard_name = standard_names[vtype]
        if bounds:
            level.bounds = 'level_bnds'
            level_bnds = nc1.createVariable('level_bnds','f4',('nv',),zlib=True)
            level_bnds[0] = cfsr_var.level[0]
            level_bnds[1] = cfsr_var.level[1]
            level[:] = (level_bnds[0]+level_bnds[1])/2.0
        else:
            level[:] = cfsr_var.level
    
    lat = nc1.createVariable('lat','f4',('lat'),zlib=True)
    lat.axis = 'Y'
    lat.units = 'degrees_north'
    lat.long_name = 'latitude'
    lat.standard_name = 'latitude'
    lat[:] = lats[::-1,0]
    
    lon = nc1.createVariable('lon','f4',('lon'),zlib=True)
    lon.axis = 'X'
    lon.units = 'degrees_east'
    lon.long_name = 'longitude'
    lon.standard_name = 'longitude'
    lon[:] = lons[0,:]

    warp = optimal_chunksizes(len(list_of_i),lat.size,lon.size)
    var1 = nc1.createVariable(nc_var_name,'f4',('time','lat','lon'),zlib=True,
                              fill_value=deff4,chunksizes=warp)
    if overwrite_nc_units is None:
        var1.units = cfsr_var.units
    else:
        var1.units = overwrite_nc_units
    var1.long_name = cfsr_var.name
    var1.standard_name = standard_names[nc_var_name]
    var1.statistic = cfsr_var.statistic
    
    t = 0 # counter for the NetCDF file
    c = 0 # counter for our temporary array
    temporary_array = ma.zeros([cache_size,var1.shape[1],var1.shape[2]])
    temporary_tvs = np.zeros([cache_size,6])
    flag_runtimeerror = False
    for i,grb_msg in enumerate(gribou.msg_iterator(grib_file)):
        if i not in list_of_i:
            continue
        try:
            data = grb_msg['values']
        except RuntimeError:
            data = ma.masked_all([var1.shape[1],var1.shape[2]])
            flag_runtimeerror = True
        dt = list_of_msg_dicts[i]['endStep']-list_of_msg_dicts[i]['startStep']
        if cfsr_var.statistic == 'avg':
            if dt == 1:
                temporary_array[c,:,:] = data
            else:
                if list_of_msg_dicts[i]['startStep'] != 0:
                    raise NotImplementedError("Weird delta t?")
                x = list_of_msg_dicts[i]['endStep']
                temporary_array[c,:,:] = x*data-(x-1)*previous_data
        elif cfsr_var.statistic == 'accum':
            if dt == 1:
                temporary_array[c,:,:] = data/3600.0
            else:
                if list_of_msg_dicts[i]['startStep'] != 0:
                    raise NotImplementedError("Weird delta t?")
                temporary_array[c,:,:] = (data-previous_data)/3600.0
        else:
            temporary_array[c,:,:] = data
        temporary_tvs[c,0] = list_of_msg_dicts[i]['year']
        temporary_tvs[c,1] = list_of_msg_dicts[i]['month']
        temporary_tvs[c,2] = list_of_msg_dicts[i]['day']
        warp = list_of_msg_dicts[i]['hour']+list_of_msg_dicts[i]['endStep']
        temporary_tvs[c,3] = warp
        if temporary_tvs[c,3] == 24:
            temporary_tvs[c,3] = 0
            warp = CalGregorian.count_days_in_cycle(temporary_tvs[c,1],
                                                    temporary_tvs[c,0])
            if temporary_tvs[c,2] == warp:
                temporary_tvs[c,2] = 1
                if temporary_tvs[c,1] == 12:
                    temporary_tvs[c,1] = 1
                    temporary_tvs[c,0] = temporary_tvs[c,0]+1
                else:
                    temporary_tvs[c,1] = temporary_tvs[c,1]+1
            else:
                temporary_tvs[c,2] = temporary_tvs[c,2]+1
        temporary_tvs[c,4] = 0
        temporary_tvs[c,5] = 0
        c += 1
        if c == cache_size:
            c = 0
            if nc_var_name == 'clt':
                var1[t:t+cache_size,:,:] = temporary_array/100.0
            else:
                var1[t:t+cache_size,:,:] = temporary_array
            time_vectors[t:t+cache_size,:] = temporary_tvs
            t += cache_size
        previous_data = data
    if nc_var_name == 'clt':
        var1[t:t+c,:,:] = temporary_array[0:c,:,:]/100.0
    else:
        var1[t:t+c,:,:] = temporary_array[0:c,:,:]
    time_vectors[t:t+c,:] = temporary_tvs[0:c,:]
    
    datetimes,masked,valid = nc._time_vectors_to_datetimes(time_vectors[:,:])
    num1 = netCDF4.date2num(datetimes,time.units,time.calendar)
    if time.dtype in [np.int8,np.int16,np.int32,np.int64]:
        time[valid] = np.array(np.round(num1),dtype=time.dtype)
    else:
        time[valid] = num1
    if len(masked): time[masked] = ma.masked_all([len(masked)])
    
    if flag_runtimeerror:
        nc1.warnings = "RuntimeError encountered, missing values inserted."
    nc1.close()

def fixed_grib2_to_netcdf(grib_file,nc_file,nc_var_name,msg_id=None,
                          grib_var_name=None,grib_level=None,
                          overwrite_nc_units=None,nc_format='NETCDF4'):
    """Convert a single spatial field from a GRIB file to NetCDF.

    Parameters
    ----------
    grib_file : string
    nc_file : string
    nc_var_name : string
    msg_id : int, optional
    grib_var_name : string, optional
    grib_level : float, optional
    overwrite_nc_units : string, optional
    nc_format : string, optional

    Notes
    -----
    Currently only implemented for 2d fields.

    """

    if msg_id is not None:
        i = msg_id-1
    else:
        list_of_msg_dicts = gribou.get_all_msg_dict(grib_file)
        flag_found = False
        for j,msg_dict in enumerate(list_of_msg_dicts):
            cfsr_var = CFSRVariable(msg_dict)
            if cfsr_var.name != grib_var_name:
                continue
            if cfsr_var.level != grib_level:
                continue
            if flag_found == True:
                raise NotImplementedError("Found duplicate?")
            i = j
            flag_found = True
    cfsr_var = CFSRVariable(list_of_msg_dicts[i])
    lats,lons = gribou.get_latlons(grib_file,i+1)
    
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    nc1 = netCDF4.Dataset(nc_file,'w',format=nc_format)
    
    nc1.Conventions = 'CF-1.5'
    nc1.title = 'Climate System Forecast Reanalysis'
    nc1.history = "%s: Convert from grib2 to NetCDF" % (now,)
    nc1.institution = 'NCEP'
    nc1.source = 'Reanalysis'
    nc1.references = 'http://cfs.ncep.noaa.gov/cfsr/'
    #nc1.comment = ''
    nc1.redistribution = "Free to redistribute."

    nc1.createDimension('lat',lats.shape[0])
    nc1.createDimension('lon',lats.shape[1])

    vtype = cfsr_var.vertical_type
    if vtype in ['depthBelowSea','heightAboveGround']:
        try:
            dummy = len(cfsr_var.level)
            bounds = True
        except:
            bounds = False
        else:
            nc1.createDimension('nv',2)
        level = nc1.createVariable('level','f4',(),zlib=True)
        level.axis = 'Z'
        level.units = cfsr_var.vertical_units
        if vtype == 'depthBelowSea':
            level.positive = 'down'
        else:
            level.positive = 'up'
        level.long_name = vtype
        level.standard_name = standard_names[vtype]
        if bounds:
            level.bounds = 'level_bnds'
            level_bnds = nc1.createVariable('level_bnds','f4',('nv',),zlib=True)
            level_bnds[0] = cfsr_var.level[0]
            level_bnds[1] = cfsr_var.level[1]
            level[:] = (level_bnds[0]+level_bnds[1])/2.0
        else:
            level[:] = cfsr_var.level
    
    lat = nc1.createVariable('lat','f4',('lat'),zlib=True)
    lat.axis = 'Y'
    lat.units = 'degrees_north'
    lat.long_name = 'latitude'
    lat.standard_name = 'latitude'
    lat[:] = lats[::-1,0]
    
    lon = nc1.createVariable('lon','f4',('lon'),zlib=True)
    lon.axis = 'X'
    lon.units = 'degrees_east'
    lon.long_name = 'longitude'
    lon.standard_name = 'longitude'
    lon[:] = lons[0,:]
    
    var1 = nc1.createVariable(nc_var_name,'f4',('lat','lon'),zlib=True,
                              fill_value=deff4)
    if overwrite_nc_units is None:
        var1.units = cfsr_var.units
    else:
        var1.units = overwrite_nc_units
    var1.long_name = cfsr_var.name
    var1.standard_name = standard_names[nc_var_name]
    var1.statistic = cfsr_var.statistic
    var1[:,:] = gribou.get_msg_data(grib_file,i+1)

    nc1.close()

