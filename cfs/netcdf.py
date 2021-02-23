"""
======
NetCDF
======

Classes:

 * NetCDFError - the exception raised on failure.

Functions:

 * :func:`_datetimes_to_time_vectors` - convert list of datetimes to Nx6 matrix.
 * :func:`_time_vectors_to_datetimes` - convert time vectors to datetimes.
 * :func:`nc_variables_with_dimension` - variables which use a given dimension.
 * :func:`nc_calendar` - timely calendar of a NetCDF file.
 * :func:`cf_decode_time_since` - decode time units of a NetCDF file.
 * :func:`_nc_decode_time_units` - decode time units of a NetCDF file.
 * :func:`nc_subdomain_bounds` - bounds of NetCDF subdomain.
 * :func:`nc_subdomain_indices` - indices of NetCDF subdomain.
 * :func:`nc_subperiod_slice` - slice of NetCDF subperiod.
 * :func:`nc_get_data` - get data over specified time period and region.
 * :func:`nc_validate` - validate NetCDF file.
 * :func:`nc_copy_attrs` - copy multiple global attributes.
 * :func:`nc_copy_dimensions` - copy dimensions.
 * :func:`nc_copy_variables_structure` - copy variables structure.
 * :func:`nc_copy_variables_attributes` - copy variables attribute.
 * :func:`nc_copy_variables_data` - copy variables data.
 * :func:`save_array` - save an array in a NetCDF file.

DOCUMENTATION TO DO
OUTDATED DOCUMENTATION
MORE COMMENTS NEEDED
NO TEST FUNCTION
PARTIAL TEST FUNCTIONS
FULL REVIEW REQUIRED

"""

import datetime
import warnings
import copy

import netCDF4
import numpy as np
import numpy.ma as ma

import timely as ty

# from . import ncgeo as geo
default_calendar = ty.CalGregorian


# try:
#    from ouranos.utils import timely as ty
#    from ouranos.utils import slice_shortcuts as ss
#    from ouranos.utils import geometry as geo
#    default_calendar = ty.CalGregorian
# except ImportError:
#    msg = "ouranos module not found, proceeding with limited functionality."
#    warnings.warn(msg)
#    default_calendar = None

class NetCDFError(Exception):
    pass

#
def mask_combinatorics(some_array, multislice, flag_start=True):
    """Mask combinatorics
    Parameters
    ----------
    some_array - ma.array
    multislice - Multidimensional slices
    Returns
    -------
    out - ma.array
    Notes
    -----
    This modifies the array in-place.
    Used to mask values outside of a polygon in multidimensional data.
    MORE COMMENTS NEEDED
    PARTIAL TEST FUNCTIONS
    """

    combinato_slices = []
    first_array = -1
    flag_multi_indices = False
    for i, my_slice in enumerate(multislice):
        if isinstance(my_slice, type(np.array([0]))):
            if first_array != -1:
                flag_multi_indices = True
                combinato_slices.append(my_slice)
            else:
                first_array = i
                combinato_slices.append(0)
        else:
            combinato_slices.append(my_slice)
    if first_array != -1:
        initial_mask = copy.deepcopy(ma.getmaskarray(some_array))
        if flag_start:
            some_array.mask = np.ones(some_array.shape, dtype=np.bool)
        if flag_multi_indices:
            for j in set(multislice[first_array]):
                combinato_slices[first_array] = j
                next_combo = []
                for i, my_slice in enumerate(combinato_slices):
                    if isinstance(my_slice, type(np.array([0]))):
                        restrain = np.where(multislice[first_array] == j)
                        next_combo.append(my_slice[restrain])
                    else:
                        next_combo.append(my_slice)
                mask_combinatorics(some_array, tuple(next_combo), False)
        else:
            for j in range(multislice[first_array].size):
                combinato_slices[first_array] = multislice[first_array][j]
                some_array.mask[tuple(combinato_slices)] = 0
            return
        some_array.mask[...] = np.bitwise_or(initial_mask,
                                             ma.getmaskarray(some_array))

#
def _time_vectors_int(time_vectors, force=False, raise_exception=False,
                      allow_masked=True, dtype='int32'):
    # tries to make the time vectors array an integer array if possible.
    if allow_masked:
        time_vectors_int = ma.array(time_vectors, dtype=dtype)
    else:
        time_vectors_int = np.array(time_vectors, dtype=dtype)
    if force or ((time_vectors_int - time_vectors).sum() == 0):
        return time_vectors_int
    else:
        if raise_exception:
            raise NetCDFError("Floats in time vectors.")
        else:
            return time_vectors


#
def _time_vectors_type(time_vectors, reference_time_vectors):
    # force time vectors array to the data type of another array
    if isinstance(reference_time_vectors, np.ndarray):
        return np.array(time_vectors, dtype=reference_time_vectors.dtype)
    elif isinstance(reference_time_vectors, ma.core.MaskedArray):
        return ma.array(time_vectors, dtype=reference_time_vectors.dtype)
    else:
        raise NotImplementedError()


#
def _datetimes_to_time_vectors(datetimes):
    """Convert list of datetimes to Nx6 matrix.

    Parameters
    ----------
    datetimes - list of datetime

    Returns
    -------
    out - numpy array
        Nx6 matrix of time vectors

    """

    # Does not support microsecond (datetime shape of length 7)
    def datetime_timetuple(one_datetime):
        if one_datetime is None:
            return ma.masked_all([6], dtype='int32')
        return one_datetime.timetuple()[0:6]

    try:
        time_tuples = map(datetime_timetuple, datetimes)
        return _time_vectors_int(ma.array(time_tuples))
    except (AttributeError, TypeError):
        time_tuple = datetimes.timetuple()
        return _time_vectors_int(ma.array(time_tuples))


#
def _time_vectors_to_datetimes(time_vectors):
    """Convert a MultiDate object to a list of datetime.

    Parameters
    ----------
    time_vectors - Nx6 matrix

    Returns
    -------
    out1,out2,out3 - list of datetimes, list of masked indices,
                     list of valid indices

    """

    datetimes = []
    ncdatetimes = []
    irregular_calendar = False
    masked_datetimes = []
    valid_datetimes = []
    if len(time_vectors.shape) == 1:
        full_vector = ma.masked_all([7], dtype='int32')
        for s in range(time_vectors.shape[0]):
            full_vector[s] = time_vectors[s]
        for s in range(time_vectors.shape[0], 7):
            if s in [1, 2]:
                full_vector[s] = 1
            else:
                full_vector[s] = 0
        try:
            one_datetime = datetime.datetime(*full_vector)
        except:
            irregular_calendar = True
        else:
            datetimes.append(one_datetime)
            valid_datetimes.append(0)
        if irregular_calendar:
            try:
                ndatetime = netCDF4.netcdftime.datetime(*full_vector)
                datetime_str = ndatetime.strftime()
            except (ma.MaskError, ValueError):
                masked_datetimes.append(0)
            else:
                ncdatetimes.append(ndatetime)
                valid_datetimes.append(0)
    else:
        for i in range(time_vectors.shape[0]):
            full_vector = ma.masked_all([7], dtype='int32')
            for s in range(time_vectors.shape[1]):
                full_vector[s] = time_vectors[i, s]
            for s in range(time_vectors.shape[1], 7):
                if s in [1, 2]:
                    full_vector[s] = 1
                else:
                    full_vector[s] = 0
            try:
                ndatetime = netCDF4.netcdftime.datetime(*full_vector)
                datetime_str = ndatetime.strftime()
            except (ma.MaskError, ValueError):
                masked_datetimes.append(i)
            else:
                ncdatetimes.append(ndatetime)
                valid_datetimes.append(i)
            if not irregular_calendar:
                try:
                    one_datetime = datetime.datetime(*full_vector)
                except ValueError:
                    irregular_calendar = True
                except ma.MaskError:
                    pass
                else:
                    datetimes.append(one_datetime)
    if irregular_calendar:
        return ncdatetimes, np.array(masked_datetimes), np.array(valid_datetimes)
    else:
        return datetimes, np.array(masked_datetimes), np.array(valid_datetimes)


#
def nc_variables_with_dimension(nc1, dimension):
    """Variables which use a given dimension.

    Parameters
    ----------
    nc1 - netCDF4.Dataset
    dimension - str

    Returns
    out - list of str

    """

    list_of_variables = []
    for var_name in nc1.variables.keys():
        var1 = nc1.variables[var_name]
        if dimension in var1.dimensions:
            list_of_variables.append(var_name)
    return list_of_variables


#
def nc_calendar(nc1):
    """calendar object of a NetCDF file.

    Parameters
    ----------
    nc1 - netCDF4.Dataset

    Returns
    -------
    timely Calendar

    """

    time1 = nc1.variables['time']
    return ty.calendar_from_alias(time1.calendar)


#
def cf_decode_time_since(time_since):
    """decode time units of a NetCDF file.

    Parameters
    ----------
    time_since - str

    Returns
    -------
    time_unit,time_vector,time_zone - str,list,list

    """

    split_time = time_since.split()
    base_unit = split_time[0]
    if base_unit in ['day', 'days', 'd']:
        time_unit = 'day'
    elif base_unit in ['hour', 'hours', 'h', 'hr']:
        time_unit = 'hour'
    elif base_unit in ['minute', 'minutes', 'min']:
        time_unit = 'minute'
    elif base_unit in ['second', 'seconds', 's', 'sec']:
        time_unit = 'second'
    else:
        raise NetCDFError("Unknown time units: %s" % (base_unit,))
    since = split_time[1]
    if since != 'since':
        msg = "'since' keyword expected in time units, got: %s" % (since,)
        raise NetCDFError(msg)
    time_vector = split_time[2].split('-')
    time_vector = map(int, time_vector)
    if len(split_time) > 3:
        hms = split_time[3].split(':')
        time_vector.append(int(hms[0]))
        time_vector.append(int(hms[1]))
        seconds = float(hms[2])
        if seconds % 1 == 0:
            time_vector.append(int(seconds))
        else:
            time_vector.append(seconds)
    if len(split_time) > 4:
        raise NetCDFError("Time zones not implemented")
    time_zone = None
    # padding reference date with zeros
    for i in range(len(time_vector), 6):
        time_vector.append(0)
    return time_unit, time_vector, time_zone


#
def _nc_decode_time_units(nc1):
    """Decode time units of a NetCDF file.

    Parameters
    ----------
    nc1 : netCDF4.Dataset

    Returns
    -------
    out1, out2 : Date object, DeltaT object
        the reference date and the time units, respectively.

    """

    if not ('time' in nc1.variables):
        raise NetCDFError("Dataset has no 'time' variable.")
    time = nc1.variables['time']
    if not hasattr(time, 'units'):
        raise NetCDFError("time variable has no 'units' attribute.")
    units_alias = time.units
    time_unit, time_vector, time_zone = cf_decode_time_since(units_alias)
    return time_vector, time_unit


#
def nc_subdomain_bounds(nc1, spatially):
    """Get bounds of NetCDF subdomain.

    Parameters
    ----------
    nc1 - netCDF4.Dataset
    spatially - spatially object

    Returns
    -------
    out - dictionary of slices

    """

    lon1 = nc1.variables['lon']
    lat1 = nc1.variables['lat']
    return geo.subdomain_bounds(lon1[...], lat1[...], spatially, lon1.dimensions)


#
def nc_subdomain_indices(nc1, geometry, warp_longitude=None):
    lon1 = nc1.variables['lon']
    lat1 = nc1.variables['lat']
    if (len(lon1.dimensions) == 1) and (len(lat1.dimensions) == 1):
        if lon1.dimensions[0] == lat1.dimensions[0]:
            indices = geo.linear_lonlat_subdomain_indices(lon1[:], lat1[:],
                                                          geometry,
                                                          warp_longitude)
            return {lon1.dimensions[0]: indices[0]}
    raise NotImplementedError()


#
def nc_subperiod_slice(nc1, initial_year, final_year, left_open=False,
                       right_open=True):
    time1 = nc1.variables['time']
    initial_nc_date = netCDF4.netcdftime.datetime(initial_year, 1, 1, 0, 0, 0)
    final_nc_date = netCDF4.netcdftime.datetime(final_year, 1, 1, 0, 0, 0)
    initial_num = netCDF4.date2num(initial_nc_date, time1.units, time1.calendar)
    final_num = netCDF4.date2num(final_nc_date, time1.units, time1.calendar)
    times = time1[:]
    if left_open:
        flag_over = times > initial_num
    else:
        flag_over = times >= initial_num
    if right_open:
        flag_under = times < final_num
    else:
        flag_under = times <= final_num
    indices = np.where(np.bitwise_and(flag_over, flag_under))
    if indices[0].size == 0:
        return None
    return slice(indices[0][0], indices[0][-1] + 1)


#
def nc_get_data(nc1, variable, timely=None, spatially=None, time_stats=None,
                spatial_stats=None, mask_outside_spatially=True):
    """Get variable in a NetCDF file.

    Parameters
    ----------
    nc1 - netCDF4.Dataset
    variable - str
    timely - timely
    spatially - spatially

    Returns
    -------
    out - numpy array or masked array

    Notes
    -----
    This is completely out of date.

    """

    var1 = nc1.variables[variable]
    dims1 = var1.dimensions
    if 'lon' in nc1.variables.keys():
        lon1 = nc1.variables['lon']
        lon = geo.grid_fix_longitudes(lon1[...], 180.0)
        lon_dimensions = lon1.dimensions
    else:
        lon_dimensions = []
    if 'lat' in nc1.variables.keys():
        lat1 = nc1.variables['lat']
        lat = lat1[...]
        lat_dimensions = lat1.dimensions
    else:
        lat_dimensions = []

    slices = []
    multiindices = []
    for dim1 in dims1:
        if dim1 == 'time' and timely:
            mdate1 = nc_timely(nc1)
            time_indices = mdate1.intersection(timely, as_indices=True)
            slices.append(time_indices[0])
            multiindices.append(slice(None, None, None))
        elif (dim1 in lon_dimensions) or (dim1 in lat_dimensions):
            indices = geo.subdomain_indices(lon, lat, spatially,
                                            lon_dimensions,
                                            lat_dimensions)
            bounds = geo.indices_bounds(indices)
            slices.append(bounds[dim1])
            multiindices.append(indices[dim1] - indices[dim1].min())
        else:
            slices.append(slice(None, None, None))
            multiindices.append(slice(None, None, None))
    print(slices)
    mydata = var1[tuple(slices)]
    if mask_outside_spatially:
        mydata = ma.array(mydata)
        ss.mask_combinatorics(mydata, tuple(multiindices))
    return mydata


#
def nc_validate(nc1, variables=[]):
    """Validate NetCDF file.

    Parameters
    ----------
    nc1 - netCDF4.Dataset
    variables - list of str
        fields that are expected in the NetCDF file.

    Notes
    -----
    1. 'lon' exists, units are 'degrees_east'
    2. 'lat' exists, units are 'degrees_north'
    3. if 'time' exists:
        3.1 attribute 'calendar' exists
        3.2 attribute 'units' exists
        3.3 netCDF4.num2date(time[:],time.units,time.calendar) works
    4. variables given as input exist and have 'units' attribute

    """

    warnings.simplefilter('always')
    if not 'lon' in nc1.variables.keys():
        warnings.warn("lon field missing.")
    if not 'lat' in nc1.variables.keys():
        warnings.warn("lat field missing.")
    for var1 in nc1.variables.keys():
        ncvar1 = nc1.variables[var1]
        if var1 == 'time':
            if not hasattr(ncvar1, 'calendar'):
                warnings.warn("time variable has no calendar.")
                test_calendar = 'gregorian'
            else:
                test_calendar = ncvar1.calendar
            if hasattr(ncvar1, 'units'):
                try:
                    date1 = netCDF4.num2date(ncvar1[0], ncvar1.units,
                                             test_calendar)
                except:
                    warp1 = (str(ncvar1[0]), ncvar1.units, test_calendar)
                    warp2 = "num2date failed."
                    warp3 = " value: %s, units: %s, calendar: %s."
                    warnings.warn(warp2 + warp3 % warp1)
        elif var1 == 'lon':
            if hasattr(ncvar1, 'units') and ncvar1.units != 'degrees_east':
                warp1 = "lon variable units are not 'degrees_north'. units: %s"
                warnings.warn(warp1 % (ncvar1.units,))
        elif var1 == 'lat':
            if hasattr(ncvar1, 'units') and ncvar1.units != 'degrees_north':
                warp1 = "lat variable units are not 'degrees_east'. units: %s"
                warnings.warn(warp1 % (ncvar1.units,))
        elif var1 in variables:
            if not hasattr(ncvar1, 'units'):
                warnings.warn("%s variable has no units." % (var1,))
    for variable in variables:
        if not (variable in nc1.variables.keys()):
            warnings.warn("%s variable not in netCDF file." % (variable,))


#
def nc_copy_attrs(nc_source, nc_destination, includes=[], excludes=[], renames=None,
                  defaults=None, appends=None):
    """Copy attributes from source file to destination file.

    Parameters
    ----------
    nc_source - netCDF4.Dataset or netCDF4.Variables
    nc_destination - netCDF4.Dataset or netCDF4.Variables
    includes - list of str
        attributes to copy.
    excludes - list of str
        attributes that will be ignored.
    renames - dict
    defaults - dict
        this is not affected by the mapping defined in 'renames'
    appends - dict
        this is not affected by the mapping defined in 'renames'

    Notes
    -----
    If includes is not empty, only those specified attributes are copied.
    To overwrite an attribute, put it in 'excludes' and set its value
    in 'defaults'.
    To append to an attribute, use 'appends'.
    To set an attribute only if it is not in the source file, use 'defaults'
    To replace an attribute and keep a backup, use 'renames' and 'defaults'

    """

    if renames is None:
        renames = {}
    if defaults is None:
        defaults = {}
    if appends is None:
        appends = {}
    attributes = nc_source.ncattrs()
    if includes:
        for include in includes:
            if include not in attributes:
                raise NotImplementedError("Attribute not found.")
        attributes = includes
    for attribute in attributes:
        if attribute not in excludes:
            if attribute not in renames.keys():
                renames[attribute] = attribute
            if renames[attribute] == '_FillValue':
                continue
            copy_attr = getattr(nc_source, attribute)
            # hack for bypassing unicode bug
            try:
                copy_attr = copy_attr.encode('latin-1')
            except (AttributeError, UnicodeEncodeError):
                pass
            nc_destination.__setattr__(renames[attribute], copy_attr)
    for attribute in defaults.keys():
        if not hasattr(nc_destination, attribute):
            # hack for bypassing unicode bug
            try:
                default_attr = defaults[attribute].encode('latin-1')
            except (AttributeError, UnicodeEncodeError):
                default_attr = defaults[attribute]
            nc_destination.__setattr__(attribute, default_attr)
    for attribute in appends.keys():
        if hasattr(nc_destination, attribute):
            warp = getattr(nc_destination, attribute)
            # hack for bypassing unicode bug
            try:
                append_attr = appends[attribute].encode('latin-1')
            except (AttributeError, UnicodeEncodeError):
                append_attr = appends[attribute]
            new_attr = warp + '\n' + append_attr
            nc_destination.__setattr__(attribute, new_attr)
        else:
            # hack for bypassing unicode bug
            try:
                append_attr = appends[attribute].encode('latin-1')
            except (AttributeError, UnicodeEncodeError):
                append_attr = appends[attribute]
            nc_destination.__setattr__(attribute, append_attr)


#
def nc_copy_dimensions(nc_source, nc_destination, includes=[], excludes=[],
                       renames=None, defaults=None, reshapes=None):
    """Copy NetCDF dimensions.

    Parameters
    ----------
    nc_source - netCDF4.Dataset
    nc_destination - netCDF4.Dataset
    includes - list of str
        dimensions to copy.
    excludes - list of str
        dimensions that will be ignored.
    renames - dict
    defaults - dict
        this is not affected by the mapping defined in 'renames'
    reshapes - dict
        this is not affected by the mapping defined in 'renames'

    Notes
    -----
    If includes is not empty, only those specified dimensions are copied.

    """

    if renames is None:
        renames = {}
    if defaults is None:
        defaults = {}
    if reshapes is None:
        reshapes = {}
    dims_src = nc_source.dimensions.keys()
    dims_dest = nc_destination.dimensions.keys()
    if includes:
        for include in includes:
            if include not in dims_src:
                raise NotImplementedError("Dimension not found.")
        dims_src = includes
    for dim_src in dims_src:
        if dim_src in excludes:
            continue
        if dim_src not in renames.keys():
            renames[dim_src] = dim_src
        if renames[dim_src] not in dims_dest:
            ncdim1 = nc_source.dimensions[dim_src]
            if renames[dim_src] not in reshapes:
                if ncdim1.isunlimited():
                    reshapes[renames[dim_src]] = None
                else:
                    reshapes[renames[dim_src]] = len(ncdim1)
            nc_destination.createDimension(renames[dim_src],
                                           reshapes[renames[dim_src]])
    for dim in defaults.keys():
        if not dim in nc_destination.dimensions.keys():
            nc_destination.createDimension(dim, defaults[dim])


#
def nc_copy_variables_structure(nc_source, nc_destination, includes=[],
                                excludes=[], renames=None, new_dtype=None,
                                new_dimensions=None, create_args=None):
    """Copy structure of multiple NetCDF variables.

    Parameters
    ----------
    nc_source - netCDF4.Dataset
    nc_destination - netCDF4.Dataset
    includes - list of str
    excludes - list of str
    renames - dict
    new_dtype - dict
    new_dimensions - dict
    create_args - dict
        Set key '_global' to apply to all variables.

    """

    if renames is None:
        renames = {}
    if new_dtype is None:
        new_dtype = {}
    if new_dimensions is None:
        new_dimensions = {}
    if create_args is None:
        create_args = {}
    vars_src = nc_source.variables.keys()
    vars_dest = nc_destination.variables.keys()
    if includes:
        for include in includes:
            if include not in vars_src:
                raise NotImplementedError("Variable not found.")
        vars_src = includes
    for var_src in vars_src:
        if var_src in excludes:
            continue
        if var_src not in vars_dest:
            ncvar1 = nc_source.variables[var_src]
            if var_src not in renames.keys():
                renames[var_src] = var_src
            if var_src not in new_dtype.keys():
                new_dtype[var_src] = ncvar1.dtype
            if var_src not in new_dimensions.keys():
                new_dimensions[var_src] = ncvar1.dimensions
            if var_src not in create_args.keys():
                create_args[var_src] = {}
            if '_global' in create_args.keys():
                for key in create_args['_global'].keys():
                    if key not in create_args[var_src]:
                        create_args[var_src][key] = create_args['_global'][key]
            warp = 'fill_value' not in create_args[var_src].keys()
            if hasattr(ncvar1, '_FillValue') and warp:
                create_args[var_src]['fill_value'] = ncvar1._FillValue
            if not create_args[var_src].has_key('chunksizes'):
                # If dimensions size have changed it is not safe to copy
                # chunksizes.
                for one_dimension in new_dimensions[var_src]:
                    source_size = len(nc_source.dimensions[one_dimension])
                    dest_size = len(nc_destination.dimensions[one_dimension])
                    if source_size != dest_size:
                        break
                else:
                    if ncvar1.chunking() == 'contiguous':
                        # This does not seem to work, why?
                        # create_args[var_src]['contiguous'] = True
                        pass
                    else:
                        create_args[var_src]['chunksizes'] = ncvar1.chunking()
            nc_destination.createVariable(renames[var_src], new_dtype[var_src],
                                          new_dimensions[var_src],
                                          **create_args[var_src])


#
def nc_copy_variables_attributes(nc_source, nc_destination, includes=[],
                                 excludes=[], renames=None, attr_includes=None,
                                 attr_excludes=None, attr_renames=None,
                                 attr_defaults=None, attr_appends=None):
    """Copy NetCDF variables attributes.

    Parameters
    ----------
    nc_source - netCDF4.Dataset
    nc_destination - netCDF4.Dataset
    includes - list of str
    excludes - list of str
    renames - dict
    attr_includes - dict
        for each variable, the entry will be the 'includes' in nc_copy_attr.
    attr_excludes - dict
        for each variable, the entry will be the 'excludes' in nc_copy_attr.
        Set key '_global' to apply to all variables.
    attr_renames - dict
        for each variable, the entry will be the 'renames' in nc_copy_attr.
    attr_defaults - dict
        for each variable, the entry will be the 'defaults' in nc_copy_attr.
    attr_appends - dict
        for each variable, the entry will be the 'appends' in nc_copy_attr.

    """

    if renames is None:
        renames = {}
    if attr_includes is None:
        attr_includes = {}
    if attr_excludes is None:
        attr_excludes = {}
    if attr_renames is None:
        attr_renames = {}
    if attr_defaults is None:
        attr_defaults = {}
    if attr_appends is None:
        attr_appends = {}
    vars_src = nc_source.variables.keys()
    vars_dest = nc_destination.variables.keys()
    if includes:
        for include in includes:
            if include not in vars_src:
                raise NotImplementedError("Variable not found in source file.")
        vars_src = includes
    for var_src in vars_src:
        if var_src in excludes:
            continue
        ncvar1 = nc_source.variables[var_src]
        if var_src not in renames.keys():
            renames[var_src] = var_src
        if renames[var_src] not in vars_dest:
            raise NotImplementedError("Variable not found in destination file.")
        ncvar2 = nc_destination.variables[renames[var_src]]
        if var_src not in attr_includes.keys():
            attr_includes[var_src] = []
        if var_src not in attr_excludes.keys():
            attr_excludes[var_src] = []
        if '_global' in attr_excludes.keys():
            attr_excludes[var_src].extend(attr_excludes['_global'])
        if var_src not in attr_renames.keys():
            attr_renames[var_src] = {}
        if var_src not in attr_defaults.keys():
            attr_defaults[var_src] = {}
        if var_src not in attr_appends.keys():
            attr_appends[var_src] = {}
        nc_copy_attrs(ncvar1, ncvar2, attr_includes[var_src],
                      attr_excludes[var_src], attr_renames[var_src],
                      attr_defaults[var_src], attr_appends[var_src])


#
def nc_copy_variables_data(nc_source, nc_destination, includes=[], excludes=[],
                           renames=None, source_slices=None,
                           destination_slices=None):
    """Copy NetCDF variables data.

    Parameters
    ----------
    nc_source - netCDF4.Dataset
    nc_destination - netCDF4.Dataset
    includes - list of str
    excludes - list of str
    renames - dict

    """

    if renames is None:
        renames = {}
    if source_slices is None:
        source_slices = {}
    if destination_slices is None:
        destination_slices = {}
    vars_src = nc_source.variables.keys()
    vars_dest = nc_destination.variables.keys()
    if includes:
        for include in includes:
            if include not in vars_src:
                raise NotImplementedError("Variable not found in source file.")
        vars_src = includes
    for var_src in vars_src:
        if var_src in excludes:
            continue
        ncvar1 = nc_source.variables[var_src]
        if var_src not in renames.keys():
            renames[var_src] = var_src
        if renames[var_src] not in vars_dest:
            raise NotImplementedError("Variable not found in destination file.")
        ncvar2 = nc_destination.variables[renames[var_src]]
        if var_src in source_slices:
            raise NotImplementedError("Slice copies.")
        if renames[var_src] in destination_slices:
            raise NotImplementedError("Slice copies.")
        ncvar2[...] = ncvar1[...]


#
def nc_copy(nc_source, nc_destination, timely=None, spatially=None, history_log=''):
    """Copy a NetCDF file.

    Parameters
    ----------
    nc_source - netCDF4.Dataset
    nc_destination - netCDF4.Dataset
    timely - timely
    spatially - spatially
    history_log - str

    Notes
    -----
    This is completely out of date.

    """

    bounds_dict = nc.nc_subdomain_bounds(nc_source, spatially)
    # Create netCDF dimensions
    excludes = []
    for k, v in iteritems(bounds_dict):
        nc1.createDimension(k, v.stop - v.start)
        excludes.append(k)
    nc_copy_dimensions(nc_source, nc_destination, excludes=excludes)

    # 2.6.2. Description of file contents
    if history_log:
        nc_append_gattr(nc_source, nc_destination, 'history', history_log)
        nc_copy_gattrs(nc_source, nc_destination, excludes=['history'])
    else:
        nc_copy_gattrs(nc_source, nc_destination)

    # Create netCDF variables
    for variable in nc_source.variables.keys():
        nc_copy_variable_structure(nc_source, nc_destination, variable, zlib=True)
        nc_copy_variable_attributes(nc_source, nc_destination, variable)
        var1 = nc_destination.variables[variable]
        var1[...] = nc_get_data(nc_source, variable, timely, spatially)


#
def save_array(nc1, array, variable_name, datatype='', dimensions=None,
               variable_attributes={}, **args):
    """Save an array to a netCDF file.

    Parameters
    ----------
    nc1 - netCDF4.Dataset
    array - numpy array (or masked array)
    variable_name - str
    datatype - str or numpy dtype
        optional, defaults to input array  data type.
    dimensions - list of str
        optional, defaults to ['arrayN1','arrayN2',...] where N1,N2,...
        are the size of each dimension.
    variable_attributes - dictionary
        optional.
    **args
        arguments passed to createVariable.

    Returns
    -------
    out - netCDF.Variable

    """

    if dimensions is None:
        dimensions = []
    if datatype == '':
        datatype = array.dtype
    if dimensions == []:
        for s in array.shape:
            dimensions.append("array%s" % str(s))
    for i, dimension in enumerate(dimensions):
        if dimension not in nc1.dimensions:
            nc1.createDimension(dimension, array.shape[i])
    var1 = nc1.createVariable(variable_name, datatype, dimensions, **args)
    var1[...] = array
    for key, value in variable_attributes.iteritems():
        var1.__setattr__(key, value)
    return var1


#
def open_cf_nc_file(nc_file, mode='r', var_names=None, output_type='individual',
                    load_data=False):
    # output_type are either 'individual' or 'dict' (also supports 'i' or 'd')
    # Remember to close the file if load_data is False!
    nc1 = netCDF4.Dataset(nc_file, mode)
    mykeys = ['time', 'lon', 'lat']
    if var_names is not None:
        mykeys.extend(var_names)
    else:
        var_names = []
    d = {}
    d['nc'] = nc1
    for mykey in mykeys:
        if mykey in nc1.variables.keys():
            if load_data:
                d[mykey] = nc1.variables[mykey][...]
            else:
                d[mykey] = nc1.variables[mykey]
        else:
            d[mykey] = None
    if load_data:
        nc1.close()
    if output_type in ['dict', 'd']:
        return d
    elif output_type in ['individual', 'i']:
        output_list = [d['nc'], d['time'], d['lon'], d['lat']]
        for var_name in var_names:
            output_list.append(d[var_name])
        return tuple(output_list)
    else:
        raise NetCDFError("Invalid output type.")


#
def nc_detect_grid(nc_file):
    nc1 = netCDF4.Dataset(nc_file, 'r')
    lon1 = nc1.variables['lon'][...]
    lat1 = nc1.variables['lat'][...]
    lon_dimensions = lon1.dimensions
    lat_dimensions = lat1.dimensions
    nc1.close()
    return geogrid.detect_grid(lon1, lat1, lon_dimensions, lat_dimensions)


def nc_grid_warp_longitude(nc_file):
    nc1 = netCDF4.Dataset(nc_file, 'r')
    lon1 = nc1.variables['lon'][...]
    lat1 = nc1.variables['lat'][...]
    nc1.close()
    return geogrid.grid_warp_longitude(lon1, lat1)


def _calendar_from_time_variable(nc_time):
    if hasattr(nc_time, 'calendar'):
        return nc_time.calendar
    else:
        return 'gregorian'


def _calendar_from_nc_dataset(nc_dataset):
    nc_time = nc_dataset.variables['time']
    return _calendar_from_time_variable(nc_time)


def _calendar_from_file(nc_file):
    nc_dataset = netCDF4.Dataset(nc_file, 'r')
    calendar = _calendar_from_nc_dataset(nc_dataset)
    nc_dataset.close()
    return calendar


def nt_from_multiple_files_with_calendar_check(nc_files):
    nt = 0
    nc_calendars = []
    for nc_file in nc_files:
        nc_dataset = netCDF4.Dataset(nc_file, 'r')
        nc_time = nc_dataset.variables['time']
        nt += nc_time.size
        nc_calendars.append(_calendar_from_time_variable(nc_time))
        nc_dataset.close()
    if len(set(nc_calendars)) != 1:
        raise NotImplementedError("Inconsistent calendars.")
    return nt, nc_calendars[0]


def load_point_timeseries_from_multiple_files(nc_files, var_name, k=None,
                                              j=None, i=None, nt=None):
    # if i is provided but not j, it's a list of 2d points...
    calendar = None
    start_units = None
    if nt is None:
        nt, calendar = nt_from_multiple_files_with_calendar_check(nc_files)
    tvs_ts = ma.masked_all([nt, 6])
    data_ts = ma.masked_all([nt])
    t = 0
    for nc_file in nc_files:
        nc_dataset = netCDF4.Dataset(nc_file, 'r')
        nc_time = nc_dataset.variables['time']
        if start_units is None:
            start_units = nc_time.units
        if calendar is None:
            calendar = _calendar_from_time_variable(nc_time)
        if 'time_vectors' in nc_dataset.variables.keys():
            tvs = _time_vectors_int(nc_dataset.variables['time_vectors'][:, :])
        else:
            nc_datetimes = netCDF4.num2date(nc_time[:], nc_time.units,
                                            nc_time.calendar)
            tvs = _datetimes_to_time_vectors(nc_datetimes)
        # Issue with 2nd dimension here, might not be always 6.
        if tvs.shape[1] == 6:
            tvs_ts[t:t + tvs.shape[0], :] = tvs[:, :]
        elif tvs.shape[1] == 3:
            tvs_ts[t:t + tvs.shape[0], 0:3] = tvs[:, :]
        else:
            raise NotImplementedError("Unexpected time vectors shape.")
        nc_var = nc_dataset.variables[var_name]
        if k is not None:
            if j is not None:
                data_ts[t:t + tvs.shape[0]] = nc_var[:, k, j, i]
            elif i is not None:
                data_ts[t:t + tvs.shape[0]] = nc_var[:, k, i]
            else:
                data_ts[t:t + tvs.shape[0]] = nc_var[:, k]
        else:
            if j is not None:
                data_ts[t:t + tvs.shape[0]] = nc_var[:, j, i]
            elif i is not None:
                data_ts[t:t + tvs.shape[0]] = nc_var[:, i]
            else:
                data_ts[t:t + tvs.shape[0]] = nc_var[:]
        t += tvs.shape[0]
        nc_dataset.close()
    tvs_ts = _time_vectors_type(tvs_ts, tvs)
    # There is no check for a uniform increase in the time steps
    # The data type of returned time vectors can be float even when it should
    # be integers.
    return tvs_ts, data_ts, start_units, calendar
