"""
DOCUMENTATION TO DO
MORE COMMENTS NEEDED
NO TEST FUNCTION
"""

import pygrib
import numpy.ma as ma

# http://www.nco.ncep.noaa.gov/pmb/docs/grib2/grib2_doc.shtml
# grib_dump grib_file.grb2 > log.text

data_keys = ['latitudes','longitudes','latLonValues','distinctLatitudes',
             'distinctLongitudes','values','codedValues']

def grib_msg_dict(grib_msg):
    """Put metadata of a GRIB message into a dictionary.

    Parameters
    ----------
    grib_msg : pygrib.gribmessage

    Returns
    -------
    out : dictionary

    """

    d = {}
    for key in grib_msg.keys():
        if key in data_keys:
            continue
        # Caught some weird cases where grib_msg.has_key(key) is true but
        # trying to access that key yields a RuntimeError: Key/value not found
        try:
            d[key] = grib_msg[key]
        except RuntimeError:
            continue
    return d

def msg_dump(grib_msg):
    """Dump a GRIB message.

    Parameters
    ----------
    grib_msg : pygrib.gribmessage

    """

    for key in grib_msg.keys():
        print key,grib_msg[key]

def first_msg_dump(grib_file):
    """Dump first message of a GRIB file.

    Parameters
    ----------
    grib_file : string

    """

    grb1 = pygrib.open(grib_file)
    msg_dump(grb1.message(1))
    grb1.close()

def first_str_dump(grib_file):
    """Print the __str__() value of first message of a GRIB file.

    Parameters
    ----------
    grib_file : string

    """

    grb1 = pygrib.open(grib_file)
    grb_msg = grb1.message(1)
    print grb_msg.__str__()
    grb1.close()

def all_str_dump(grib_file):
    """Dump all __str__() values of the messages of a GRIB file.

    Parameters
    ----------
    grib_file : string

    """

    grb1 = pygrib.open(grib_file)
    for grb_msg in grb1:
        print grb_msg.__str__()
    grb1.close()

def get_all_msg_dict(grib_file):
    """Get metadata of all messages in a GRIB file.

    Parameters
    ----------
    grib_file : string

    Returns
    -------
    out : list of dictionaries

    """

    list_of_msg_dict = []
    grb1 = pygrib.open(grib_file)
    for grb in grb1:
        list_of_msg_dict.append(grib_msg_dict(grb))
    grb1.close()
    return list_of_msg_dict

def number_of_msg(grib_file):
    """Number of messages in a GRIB file.

    Parameters
    ----------
    grib_file : string

    Returns
    -------
    out : int

    """

    grb1 = pygrib.open(grib_file)
    n = grb1.messages
    grb1.close()
    return n

def get_latlons(grib_file,msg_id=1):
    """Latitudes and longitudes of the GRIB file grid.

    Parameters
    ----------
    grib_file : string
    msg_id : int, optional

    Returns
    -------
    lats,lons : numpy arrays

    """

    grb1 = pygrib.open(grib_file)
    grb_msg = grb1.message(msg_id)
    lats,lons = grb_msg.latlons()
    grb1.close()
    return lats,lons
    
def get_msg_data(grib_file,msg_id):
    """Get data of a message in a GRIB file.

    Parameters
    ----------
    grib_file : string
    msg_id : int

    Returns
    -------
    out : numpy array

    """

    grb1 = pygrib.open(grib_file)
    grb_msg = grb1.message(msg_id)
    data = grb_msg['values']
    grb1.close()
    return data

def msg_iterator(grib_file):
    """Iterator for GRIB file messages.

    Parameters
    ----------
    grib_file : string

    """

    grb1 = pygrib.open(grib_file)
    for grb_msg in grb1:
        yield grb_msg
    grb1.close()

def get_all_data(grib_file):
    """Aggregate all messages data of a GRIB file.

    Parameters
    ----------
    grib_file : string

    Returns
    -------
    out : numpy masked array

    Notes
    -----
    All messages in the GRIB file are assumed to have the same shape.

    """

    grb1 = pygrib.open(grib_file)
    t = grb1.messages
    for i,grb_msg in enumerate(grb1):
        data = grb_msg['values']
        if i == 0:
            all_data = ma.masked_all([t,data.shape[0],data.shape[1]])
        all_data[i,:,:] = data
    grb1.close()
    return all_data

def get_subset_data(grib_file,msg_ids):
    """Aggregate data from subset of messages of a GRIB file.

    Parameters
    ----------
    grib_file : string
    msg_ids : list of int

    Returns
    -------
    out : numpy masked array

    Notes
    -----
    All selected messages in the GRIB file are assumed to have the same shape.

    """

    t = len(msg_ids)
    grb1 = pygrib.open(grib_file)
    c = 0
    for i,grb_msg in enumerate(grb1):
        if i not in msg_ids:
            continue
        data = grb_msg['values']
        if c == 0:
            all_data = ma.masked_all([t,data.shape[0],data.shape[1]])
        all_data[c,:,:] = data
        c += 1
    grb1.close()
    return all_data

def stack_data(grib_file,msg_ids):
    """Aggregate vertical data from a subset of messages of a GRIB file.

    Parameters
    ----------
    grib_file : string
    msg_ids : list of list of int
        Each list represent many timesteps of a single level. The order is
        important, the first id is the first level, first timestep.

    Returns
    -------
    out : numpy masked array

    Notes
    -----
    All selected messages in the GRIB file are assumed to have the same shape.

    """

    t = len(msg_ids[0])
    k = len(msg_ids)
    grb1 = pygrib.open(grib_file)
    c = 0
    for i,grb_msg in enumerate(grb1):
        for nk,first_list in enumerate(msg_ids):
            for nt,one_id in enumerate(first_list):
                if one_id == i:
                    break
        else:
            continue
        data = grb_msg['values']
        if c == 0:
            all_data = ma.masked_all([t,k,data.shape[0],data.shape[1]])
            c = 1
        all_data[nt,nk,:,:] = data
    grb1.close()
    return all_data
