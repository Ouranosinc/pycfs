"""
=============
python-timely
=============

Operations on time vectors with variable calendar definitions.

Notes
-----
The terminology and structure is inspired by the shapely package and was
motivated by the need to deal with various time representation in the
climate modelling community.

The notion of years is assumed to be uniform across all cases. How the years
are divided into cycles (usually months) and each cycle into days can vary.
There is always 24 hours in a day, 60 minutes in an hour and 60 seconds in a
minute.

The basic unit is a 6-element time vector. However, the precision with which a
specific time or period is given is left to the user and decimals are allowed
in the last specified time element. For example, each of the following time
vectors can be used as a date:
    [2007] # The beginning of 2007
    [2007.25] # 1/4 of the way into year 2007
    [1980, 11] # The beginning of November 1980
    [1943, 5, 3, 0, 5.5] # Equivalent to [1943, 5, 3, 0, 5, 30]
    [2002, 2, 28, 12, 30, 0.0] # Fully explicit time

In order to be able to select a period (e.g. a given year) across various
calendars, we let the boundaries of periods be inclusive or exclusive.
For instance, the period [2001,2002[ is unambiguous while the period
[2001-1-1,2001-12-31] would cause problem in a context where one calendar
does not have a 31st of December in it.

The following aspects of time are not supported:
    - Time zones
    - Leap seconds

Overview on creation of timely objects (and useful shortcuts):

deltat = DeltaT([yyyy,mm,dd,hh,mn,ss])
    e.g. DeltaT([0,0,0,12]) = 12 hours
         DeltaT([0,0,0,0,0.5]) = 30 seconds

date = Date([yyyy,mm,dd,hh,mn,ss])
    e.g. Date([2010,1,10]) = January 10th, 2010, 0:00:00
    e.g. Date([2010]) = January 1st 2010, 0:00:00

multidate = MultiDate([[yyyy,mm,dd,hh,mn,ss],[yyyy,mm,dd,hh,mn,ss]])

period = Period([[yyyy,mm,dd,hh,mn,ss],[yyyy,mm,dd,hh,mn,ss]])
period = explicit_period(date1,date2)
period = implicit_period([yyyy,mm])
    e.g. implicit_period([2010]) = The year 2010
    e.g. implicit_period([2010,2]) = The month of February 2010

timeseries = Timeseries([[yyyy,mm,dd,hh,mn,ss],[yyyy,mm,dd,hh,mn,ss]])
timeseries = period.regular_sample(deltat)

"""

import warnings

import numpy as np
import numpy.ma as ma

# Default threshold for rounding seconds in time representation
threshold = 0.001
# Integer type for dates without decimals
dummy = np.array([0])
myint = dummy.dtype
# Float type for dates that convert to decimals
myfloat = 'float64'


class TimelyError(Exception):
    pass


# Vectorize functions on lists
def _index(some_list, value):
    return some_list.index(value)


#
_Vindex = np.vectorize(_index)


#
def _get_item(some_list, item):
    return some_list[item]


#
_Vget_item = np.vectorize(_get_item)


#


#
# Built-in functions for calendar definition
#
#     Cycles in year
#
def months_of_gregorian_calendar(year=0):
    """Months of the Gregorian calendar.

    Parameters
    ----------
    year : int, optional
        (dummy value).

    Returns
    -------
    out : dict
        integers as keys, months of the Gregorian calendar as values.

    Notes
    -----
    Appropriate for use as 'year_cycles' function in :class:`Calendar`.
    This module has a built-in calendar with months only:
    :data:`CalMonthsOnly`.

    """

    return {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
            7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November',
            12: 'December'}


#
def temperate_seasons(year=0):
    """Temperate seasons.

    Parameters
    ----------
    year : int, optional
        (dummy value).

    Returns
    -------
    out : dict
        integers as keys, temperate seasons as values.

    Notes
    -----
    Appropriate for use as 'year_cycles' function in :class:`Calendar`.
    This module has a built-in calendar with seasons only:
    :data:`CalSeasons`.

    """

    return {1: 'Spring', 2: 'Summer', 3: 'Autumn', 4: 'Winter'}


#
def year_cycle(year=0):
    """Year cycle.

    Parameters
    ----------
    year : int, optional
        (dummy value).

    Returns
    -------
    out : dict
        integer (1) as key, 'Year' as value.

    Notes
    -----
    Appropriate for use as 'year_cycles' function in :class:`Calendar`,
    this allows to essentially have a direct division of the years in
    days, without months, weeks or other subdivisions.
    For example, see built-in calendar :data:`Cal365NoMonths`.

    """

    return {1: 'Year'}


#
#     Days in cycle
#
def days_in_month_360(month=0, year=0):
    """Days of the month (360 days calendar).

    Parameters
    ----------
    month : int, optional
        (dummy value).
    year : int, optional
        (dummy value).

    Returns
    -------
    out : list of int
        days of the month.

    Notes
    -----
    Appropriate for use as 'days_in_cycle' function in :class:`Calendar`.
    This module has a built-in 360 days calendar with months:
    :data:`Cal360`.

    """

    return range(1, 31)


#
def days_in_month_365(month, year=0):
    """Days of the month (365 days calendar).

    Parameters
    ----------
    month : int
        numerical value of the month (1 to 12).
    year : int, optional
        (dummy value).

    Returns
    -------
    out : list of int
        days of the month.

    Notes
    -----
    Appropriate for use as 'days_in_cycle' function in :class:`Calendar`.
    This module has a built-in 365 days calendar with months:
    :data:`Cal365`.

    """

    try:
        month_float = float(month)
        month_int = int(month)
    except (TypeError, ValueError) as e:
        raise TimelyError("Month value is not numerical.")
    if month_int != month_float:
        raise TimelyError("Month value is not an integer.")
    elif (month_int < 1) or (month_int > 12):
        raise TimelyError("Month value has to be between 1 and 12.")
    days_in_months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return range(1, days_in_months[month_int - 1] + 1)


#
def days_in_month_366(month, year=0):
    """Days of the month (366 days calendar).

    Parameters
    ----------
    month : int
        numerical value of the month (1 to 12).
    year : int, optional
        (dummy value).

    Returns
    -------
    out : list of int
        days of the month.

    Notes
    -----
    Appropriate for use as 'days_in_cycle' function in :class:`Calendar`.
    This module has a built-in 366 days calendar with months:
    :data:`Cal366`.

    """

    try:
        month_float = float(month)
        month_int = int(month)
    except (TypeError, ValueError) as e:
        raise TimelyError("Month value is not numerical.")
    if month_int != month_float:
        raise TimelyError("Month value is not an integer.")
    elif (month_int < 1) or (month_int > 12):
        raise TimelyError("Month value has to be between 1 and 12.")
    days_in_months = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return range(1, days_in_months[month_int - 1] + 1)


#
def days_in_month_julian(month, year):
    """Days of the month (Julian calendar).

    Parameters
    ----------
    month : int
        numerical value of the month (1 to 12).
    year : int

    Returns
    -------
    out : list of int
        days of the month.

    Notes
    -----
    Leap year every 4 years.
    Appropriate for use as 'days_in_cycle' function in :class:`Calendar`.
    This module has a built-in julian calendar: :data:`CalJulian`.

    """

    try:
        year_float = float(year)
        year_int = int(year)
    except (TypeError, ValueError) as e:
        raise TimelyError("Year value is not numerical.")
    if year_int != year_float:
        raise TimelyError("Year value is not an integer.")
    if (year_int % 4) == 0:
        return days_in_month_366(month, year_int)
    else:
        return days_in_month_365(month, year_int)


#
def days_in_month_proleptic_gregorian(month, year):
    """Days of the month (Proleptic gregorian calendar).

    Parameters
    ----------
    month : int
        numerical value of the month (1 to 12).
    year : int

    Returns
    -------
    out : list of int
        days of the month.

    Notes
    -----
    Leap year every 4 years, except every 100 years,
    but still every 400 years.
    Appropriate for use as 'days_in_cycle' function in :class:`Calendar`.
    This module has a built-in proleptic gregorian calendar:
    :data:`CalProleptic`.

    """

    try:
        year_float = float(year)
        year_int = int(year)
    except (TypeError, ValueError) as e:
        raise TimelyError("Year value is not numerical.")
    if year_int != year_float:
        raise TimelyError("Year value is not an integer.")
    if ((year_int % 100) == 0) and ((year_int % 400) != 0):
        return days_in_month_365(month, year_int)
    else:
        return days_in_month_julian(month, year_int)


#
def days_in_month_gregorian(month, year):
    """Days of the month (Gregorian calendar).

    Parameters
    ----------
    month : int
        numerical value of the month (1 to 12).
    year : int

    Returns
    -------
    out : list of int
        days of the month.

    Notes
    -----
    Leap year every 4 years, except every 100 years,
    but still every 400 years.
    Transition to Julian calendar before 1582.
    October 5 to October 14 of 1582 do not exist.
    Appropriate for use as 'days_in_cycle' function in :class:`Calendar`.
    This module has a built-in gregorian calendar: :data:`CalGregorian`.

    """

    try:
        year_float = float(year)
        year_int = int(year)
    except (TypeError, ValueError) as e:
        raise TimelyError("Year value is not numerical.")
    if year_int != year_float:
        raise TimelyError("Year value is not an integer.")
    try:
        month_float = float(month)
        month_int = int(month)
    except (TypeError, ValueError) as e:
        raise TimelyError("Month value is not numerical.")
    if month_int != month_float:
        raise TimelyError("Month value is not an integer.")
    if (year_int > 1582) or ((year_int == 1582) and (month_int > 10)):
        return days_in_month_proleptic_gregorian(month_int, year_int)
    elif (year_int == 1582) and (month_int == 10):
        return [1, 2, 3, 4, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]
    else:
        return days_in_month_julian(month_int, year_int)


#
def days_in_year_365(cycle=1, year=0):
    """Days of the year (365 days calendar).

    Parameters
    ----------
    cycle : int, optional
        (dummy value).
    year : int, optional
        (dummy value).

    Returns
    -------
    out : list of int
        365 days of the year.

    Notes
    -----
    Appropriate for use as 'days_in_cycle' function in :class:`Calendar`.
    This module has a built-in 365 day calendar: :data:`Cal365NoMonths`.

    """

    return range(1, 366)


#
def day_in_year(cycle=1, year=0):
    """Single day in a year.

    Parameters
    ----------
    cycle : int, optional
        (dummy value).
    year : int, optional
        (dummy value).

    Returns
    -------
    out : list of int
        day of the month (1).

    Notes
    -----
    Appropriate for use as 'days_in_cycle' function in :class:`Calendar`,
    this is mostly a dummy function to avoid having to define how days
    behave. For example, see built-in calendar :data:`CalYearsOnly`.

    """

    return [1]


#
#     Leap year check
#
def is_leap_feb29(year, fn_year_cycles=year_cycle,
                  fn_days_in_cycle=days_in_month_360):
    """Check for leap year (last day of February is the 29th).

    Parameters
    ----------
    year : int
    fn_year_cycles : function(year), optional
        returns a dictionary of the year cycles (dummy value).
    fn_days_in_cycle : function(cycle,year), optional
        returns a list of the days in the cycle (default is chosen
        such that there is never any leap year).

    Returns
    -------
    out : bool
        True if the given year is a leap year, False otherwise.

    Notes
    -----
    Appropriate for use as 'fn_is_leap' function in :class:`Calendar`.

    """

    days_in_cycle = fn_days_in_cycle(2, year)
    if days_in_cycle[-1] == 29:
        return True
    else:
        return False


#


class Calendar:
    """Calendar definition.

    The calendar describes the relation between years, months/seasons
    (or other types of year subdivision), and days. Defining the concept of
    leap year is also possible.

    """

    def __init__(self, year_cycles, days_in_cycle, fn_is_leap, alias,
                 cycles_alias=None):
        """Initialize calendar.

        Parameters
        ----------
        year_cycles : function(year)
            returns a dictionary of the year cycles.
        days_in_cycle : function(cycle,year)
            returns a list of the days in the cycle, or float('inf').
        fn_is_leap : function(year,fn_year_cycles,fn_days_in_cycle) or None
            returns True for leap years, False otherwise.
        alias : str
            name given to the calendar, this is also the identifier used
            to test whether two calendars are the same, so this should
            be unique to each defined calendar.
        cycles_alias : str or None
            name of the cycles (e.g. 'month', default is None).

        Notes
        -----
        The dictionary returned by the `year_cycles` function must have
        integers starting from 1 as keys, and increasing by 1 for each
        entry.
        The cycle value input in `days_in_cycle` is a positive integer
        corresponding to the keys returned by the `year_cycles` function.
        The list of days returned by the `days_in_cycle` function has to
        be non-repeating, monotonically increasing integer values starting
        at 1.

        """

        self.year_cycles = year_cycles
        self.days_in_cycle = days_in_cycle
        self.fn_is_leap = fn_is_leap
        self.alias = alias
        self.cycles_alias = cycles_alias

        # Vectorize operations on calendars
        vec = np.vectorize
        self._Vyear_cycles = vec(self.year_cycles, otypes=[type({})])
        self._Vdays_in_cycle = vec(self.days_in_cycle, otypes=[type([])])
        self._Vis_leap = vec(self.is_leap)
        self._Vcount_cycles_in_year = vec(self.count_cycles_in_year)
        self._Vcount_days_in_cycle = vec(self.count_days_in_cycle)
        self._Vcount_days_in_year = vec(self.count_days_in_year)
        self._Vith_day_in_cycle = vec(self._ith_day_in_cycle)
        self._Vith_day_in_year = vec(self._ith_day_in_year)
        self._Vprevious_cycle = vec(self._previous_cycle)
        warp = self._count_cycles_in_previous_year
        self._Vcount_cycles_in_previous_year = vec(warp)
        warp = self._count_days_in_previous_cycle
        self._Vcount_days_in_previous_cycle = vec(warp)

    def __str__(self):
        return self.alias

    def __eq__(self, other):
        if self.alias == other.alias:
            return True
        else:
            return False

    def __ne__(self, other):
        if self.alias != other.alias:
            return True
        else:
            return False

    def is_leap(self, year):
        """Check if a given year is a leap year.

        Parameters
        ----------
        year : int

        Returns
        -------
        out : bool
            True if the given year is a leap year, False otherwise.

        """

        if self.fn_is_leap is None:
            warp = (self.alias,)
            msg = "Leap year concept not defined for '%s' calendar." % warp
            raise TimelyError(msg)
        if self.fn_is_leap(year, self.year_cycles, self.days_in_cycle):
            return True
        else:
            return False

    def count_cycles_in_year(self, year):
        """Count the number of cycles in a year.

        Parameters
        ----------
        year : int

        Returns
        -------
        out : int
            number of cycles in the year.

        """

        return len(self.year_cycles(year))

    def count_days_in_cycle(self, cycle, year):
        """Count the number of days in a cycle.

        Parameters
        ----------
        cycle : int
        year : int

        Returns
        -------
        out : int
            number of days in the cycle.

        """

        return len(self.days_in_cycle(cycle, year))

    def count_days_in_year(self, year):
        """Count the number of days in a year.

        Parameters
        ----------
        year : int

        Returns
        -------
        out : int or float('inf')
            number of days in the year.

        """

        if self.days_in_cycle(1, year) == float('inf'):
            return float('inf')
        year_cycles = self.year_cycles(year)
        days_in_year = 0
        for cycle in range(1, len(self.year_cycles(year)) + 1):
            days_in_year += len(self.days_in_cycle(cycle, year))
        return days_in_year

    def _ith_day_in_cycle(self, cycle, year, i):
        """Value of the ith day in a cycle.

        Parameters
        ----------
        cycle : int
        year : int
        i : int
            ith day of the cycle

        Returns
        -------
        out : int
            day value in the cycle

        """

        return self.days_in_cycle(cycle, year)[i - 1]

    def _ith_day_in_year(self, year, i):
        """Value of the cycle and day of the ith day in a year.

        Parameters
        ----------
        year : int
        i : int
            ith day of the year

        Returns
        -------
        out1,out2 : int
            cycle, day value in the year

        """

        c = 1
        days_in_cycle = self.count_days_in_cycle(c, year)
        while i > days_in_cycle:
            i = i - days_in_cycle
            c += 1
            days_in_cycle = self.count_days_in_cycle(c, year)
        return self.days_in_cycle(c, year)[i - 1]

    def _previous_cycle(self, cycle, year):
        """Previous cycle.

        Parameters
        ----------
        cycle : int
        year : int

        Returns
        -------
        out : int,int
            cycle, year of previous cycle

        """

        if cycle == 1:
            return self.count_cycles_in_year(year - 1), year - 1
        else:
            return cycle - 1, year

    def _count_cycles_in_previous_year(self, year):
        """Cycles in the previous year.

        Parameters
        ----------
        year : int

        Returns
        -------
        out : int
            number of cycles in the previous year

        """

        return (len(self.year_cycles(year - 1)))

    def _count_days_in_previous_cycle(self, cycle, year):
        """Days in the previous cycle.

        Parameters
        ----------
        cycle : int
        year : int

        Returns
        -------
        out : int
            number of days in the previous cycle

        """

        previous_cycle, previous_year = self._previous_cycle(cycle, year)
        return len(self.days_in_cycle(previous_cycle, previous_year))


#
# Built-in calendars
#
Cal360 = Calendar(months_of_gregorian_calendar, days_in_month_360, is_leap_feb29,
                  '360_day', 'month')
Cal365 = Calendar(months_of_gregorian_calendar, days_in_month_365, is_leap_feb29,
                  'noleap', 'month')
Cal366 = Calendar(months_of_gregorian_calendar, days_in_month_366, is_leap_feb29,
                  'all_leap', 'month')
CalJulian = Calendar(months_of_gregorian_calendar, days_in_month_julian,
                     is_leap_feb29, 'julian', 'month')
CalProleptic = Calendar(months_of_gregorian_calendar,
                        days_in_month_proleptic_gregorian, is_leap_feb29,
                        'proleptic_gregorian', 'month')
CalGregorian = Calendar(months_of_gregorian_calendar, days_in_month_gregorian,
                        is_leap_feb29, 'gregorian', 'month')
CalYearsOnly = Calendar(year_cycle, day_in_year, is_leap_feb29, 'years_only', None)
CalMonthsOnly = Calendar(months_of_gregorian_calendar, day_in_year, None,
                         'months_only', 'month')
CalSeasons = Calendar(temperate_seasons, day_in_year, is_leap_feb29, 'seasons',
                      'season')
Cal365NoMonths = Calendar(year_cycle, days_in_year_365, is_leap_feb29,
                          '365_days_no_months', None)


#
def calendar_from_alias(calendar_alias):
    """Get a Calendar object from its alias.

    Parameters
    ----------
    calendar_alias : str

    Returns
    -------
    out : Calendar object

    Notes
    -----
    This is mostly a mapping from the calendars of the CF conventions
    to built-in calendars.

    """

    if calendar_alias == '360_day':
        return Cal360
    elif calendar_alias in ['noleap', '365_day']:
        return Cal365
    elif calendar_alias in ['all_leap', '366_day']:
        return Cal366
    elif calendar_alias == 'julian':
        return CalJulian
    elif calendar_alias == 'proleptic_gregorian':
        return CalProleptic
    elif calendar_alias in ['gregorian', 'standard']:
        return CalGregorian
    elif calendar_alias == 'years_only':
        return CalYearsOnly
    elif calendar_alias == 'months_only':
        return CalMonthsOnly
    elif calendar_alias == 'seasons':
        return CalSeasons
    elif calendar_alias == '365_days_no_months':
        return Cal365NoMonths
    else:
        raise TimelyError("Unknown calendar: %s." % (calendar_alias,))


#


def _conversion_to_ma(time_vector):
    """Convert alternative sequence type to M1 x M2 x ... x Mm x 6 masked array.

    Parameters
    ----------
    time_vector - sequence

    Returns
    -------
    out - masked array

    Notes
    -----
    None and missing values in the input sequence are interpreted as
    masked values.

    """

    # Masked array input returned untouched
    if type(time_vector) == type(ma.array([])):
        return time_vector

    # Convert list input to masked array
    elif type(time_vector) == type([]):
        if not time_vector:
            return ma.array([0, 0, 0, 0, 0, 0], mask=[True, True, True, True, True, True])
        if type(time_vector[0]) in [type([]), type(np.array([]))]:
            flag_ini = True
            for i, element in enumerate(time_vector):
                ma_form = _conversion_to_ma(element)
                if flag_ini:
                    new_shape = [len(time_vector)]
                    new_shape.extend(ma_form.shape)
                    new_array = ma.zeros(new_shape)
                    flag_ini = False
                new_array[i, ...] = ma_form
            return ma.array(new_array)
        else:
            new_time = time_vector[:]
            mask = [x is None for x in new_time]
            for i in range(len(new_time)):
                if new_time[i] is None:
                    new_time[i] = 0
            for i in range(len(new_time), 6):
                new_time.append(0)
                mask.append(True)
            return ma.array(new_time, mask=mask)

    # Convert numpy array to list
    elif type(time_vector) == type(np.array([])):
        list_form = []
        for i in range(time_vector.shape[0]):
            list_form.append(time_vector[i])
        return _conversion_to_ma(list_form)

    else:
        raise TimelyError("Unsupported type for time.")


#
class _CollectionTime:
    """Collection of time."""

    def __init__(self, times):
        """Initialize _CollectionTime.

        Parameters
        ----------
        times - matrix
            M1 x M2 x ... x Mm x 6 time vectors

        """

        self.times = _conversion_to_ma(times)
        if self.times.shape == (6,):
            expand = ma.zeros([1, 6], dtype=self.times.dtype)
            expand[0, :] = self.times[:]
            self.times = expand
        if not len(self.times.shape) > 1:
            raise TimelyError("_CollectionTime needs at least two dimensions.")
        if self.times.shape[-1] != 6:
            msg = "_CollectionTime last dimension does not have 6 elements."
            raise TimelyError(msg)
        self.shape = self.times.shape[:-1]
        if self.times.count() == 0:
            self.resolution = 0
        elif self.times.count() == self.times.size:
            self.resolution = 6
        else:
            indices = ma.nonzero(~ma.getmaskarray(self.times))
            self.resolution = indices[-1].max() + 1
        if self.times.dtype in [np.dtype('int8'), np.dtype('int16'),
                                np.dtype('int32'), np.dtype('int64')]:
            self.decimals = False
        else:
            self.decimals = True

    def __getitem__(self, item):
        if isinstance(item, tuple):
            modified_item = list(item)
            modified_item.append(slice(None, None, None))
            new_item = tuple(modified_item)
        else:
            new_item = (item, slice(None, None, None))
        new_times = self.times.__getitem__(new_item)
        if new_times.shape == (6,):
            return _Time(new_times)
        else:
            return _CollectionTime(new_times)

    def __str__(self):
        return str(self.times)

    def year(self, set_value=None):
        """Year elements of the time vectors.

        Parameters
        ----------
        set_value - numpy array
            value to set in the time vector (default returns current value).

        Returns
        -------
        year - numpy array
           only returned if set_value is None.

        """

        if set_value is None:
            return self.times[..., 0]
        else:
            self.times[..., 0] = set_value

    def cycle(self, set_value=None):
        """Cycle element of the time vector.

        Parameters
        ----------
        set_value - numpy array
            value to set in the time vector (default returns current value).

        Returns
        -------
        cycle - numpy array
            only returned if set_value is None.

        """

        if set_value is None:
            return self.times[..., 1]
        else:
            self.times[..., 1] = set_value

    def month(self, set_value=None):
        """Month element of the time.

        Parameters
        ----------
        set_value - numpy array
            value to set in the time vector (default returns current value).

        Returns
        -------
        month - numpy array
            only returned if set_value is None.

        Notes
        -----
        This is simply an alias for the cycle() method.

        """

        return self.cycle(set_value)

    def day(self, set_value=None):
        """Day element of the time vector.

        Parameters
        ----------
        set_value - numpy array
            value to set in the time vector (default returns current value).

        Returns
        -------
        day - numpy array
            only returned if set_value is None.

        """

        if set_value is None:
            return self.times[..., 2]
        else:
            self.times[..., 2] = set_value

    def hour(self, set_value=None):
        """Hour element of the time vector.

        Parameters
        ----------
        set_value - numpy array
            value to set in the time vector (default returns current value).

        Returns
        -------
        hour - numpy array
            only returned if set_value is None.

        """

        if set_value is None:
            return self.times[..., 3]
        else:
            self.times[..., 3] = set_value

    def minute(self, set_value=None):
        """Minute element of the time vector.

        Parameters
        ----------
        set_value - numpy array
            value to set in the time vector (default returns current value).

        Returns
        -------
        minute - numpy array
            only returned if set_value is None.

        """

        if set_value is None:
            return self.times[..., 4]
        else:
            self.times[..., 4] = set_value

    def second(self, set_value=None):
        """Second element of the time vector.

        Parameters
        ----------
        set_value - numpy array
            value to set in the time vector (default returns current value).

        Returns
        -------
        second - numpy array
            only returned if set_value is None.

        """

        if set_value is None:
            return self.times[..., 5]
        else:
            self.times[..., 5] = set_value

    def __nonzero__(self):
        if self.times.count() == 0:
            return False
        return True

    def __eq__(self, other):
        if self.times.shape != other.times.shape:
            return False
        if (ma.getmaskarray(self.times) == ma.getmaskarray(other.times)).all():
            if (self.times == other.times).all():
                return True
        return False

    def __ne__(self, other):
        if self == other:
            return False
        else:
            return True

    def __add__(self, other):
        if ((~self.times.mask * self.times.data * other.times.mask).any() or
                (~other.times.mask * other.times.data * self.times.mask).any()):
            raise TimelyError("Trying to add to a masked element.")
        return _CollectionTime(self.times[...] + other.times[...])

    def __sub__(self, other):
        if ((~self.times.mask * self.times.data * other.times.mask).any() or
                (~other.times.mask * other.times.data * self.times.mask).any()):
            raise TimelyError("Trying to substract to/from a masked element.")
        return _CollectionTime(self.times[...] - other.times[...])

    def __mul__(self, multiplier):
        """Multiply every element of the time vectors by a multiplier.

        Parameters
        ----------
        multiplier : numerical

        Returns
        -------
        out - _CollectionTime

        """

        return _CollectionTime(self.times[...] * multiplier)

    def propagate_days_decimals(self):
        """Propagate decimals in day value further down the time vector."""

        int_values = ma.array(self.times[..., 2], dtype=myint)
        decimals = self.times[..., 2] - int_values
        unmasked_hours = 1 - ma.getmaskarray(self.times[..., 3])
        unmasked_minutes = 1 - ma.getmaskarray(self.times[..., 4])
        unmasked_seconds = 1 - ma.getmaskarray(self.times[..., 5])
        warp = np.bitwise_or(unmasked_hours, unmasked_minutes)
        unmasked_somewhere = np.bitwise_or(warp, unmasked_seconds)
        if unmasked_somewhere.sum() == 0:
            return
        indices = np.where(unmasked_somewhere)
        warp = tuple(list(indices) + [2])
        self.times[warp] = int_values[indices]
        indices = np.where(unmasked_hours)
        warp = tuple(list(indices) + [3])
        self.times[warp] = self.times[warp] + 24.0 * decimals[indices]
        unmasked_minutes[indices] = 0
        indices = np.where(unmasked_minutes)
        warp = tuple(list(indices) + [4])
        self.times[warp] = self.times[warp] + 1440.0 * decimals[indices]
        unmasked_seconds[indices] = 0
        indices = np.where(unmasked_seconds)
        warp = tuple(list(indices) + [5])
        self.times[warp] = self.times[warp] + 86400.0 * decimals[indices]

    def propagate_hours_decimals(self):
        """Propagate decimals in hour value further down the time vector."""

        int_values = ma.array(self.times[..., 3], dtype=myint)
        decimals = self.times[..., 3] - int_values
        unmasked_minutes = 1 - ma.getmaskarray(self.times[..., 4])
        unmasked_seconds = 1 - ma.getmaskarray(self.times[..., 5])
        unmasked_somewhere = np.bitwise_or(unmasked_minutes, unmasked_seconds)
        if unmasked_somewhere.sum() == 0:
            return
        indices = np.where(unmasked_somewhere)
        warp = tuple(list(indices) + [3])
        self.times[warp] = int_values[indices]
        indices = np.where(unmasked_minutes)
        warp = tuple(list(indices) + [4])
        self.times[warp] = self.times[warp] + 60.0 * decimals[indices]
        unmasked_seconds[indices] = 0
        indices = np.where(unmasked_seconds)
        warp = tuple(list(indices) + [5])
        self.times[warp] = self.times[warp] + 3600.0 * decimals[indices]

    def propagate_minutes_decimals(self):
        """Propagate decimals in minute value to second value."""

        int_values = ma.array(self.times[..., 4], dtype=myint)
        decimals = self.times[..., 4] - int_values
        unmasked_seconds = 1 - ma.getmaskarray(self.times[..., 5])
        if unmasked_seconds.sum() == 0:
            return
        indices = np.where(unmasked_seconds)
        warp = tuple(list(indices) + [4])
        self.times[warp] = int_values[indices]
        indices = np.where(unmasked_seconds)
        warp = tuple(list(indices) + [5])
        self.times[warp] = self.times[warp] + 60.0 * decimals[indices]

    def seconds_to_minutes(self):
        """Convert overloaded/negative second value to minutes."""

        unmasked_seconds = 1 - ma.getmaskarray(self.times[..., 5])
        unmasked_minutes = 1 - ma.getmaskarray(self.times[..., 4])
        seconds_abs = np.abs(self.times[..., 5])
        over_seconds = (seconds_abs >= 60.0)
        under_seconds = (self.times[..., 5] < 0)
        warp1 = np.bitwise_and(over_seconds, 1 - unmasked_minutes)
        warp2 = np.bitwise_and(under_seconds, 1 - unmasked_minutes)
        warp = np.bitwise_or(warp1, warp2)
        if warp.sum() != 0:
            warp = "Some minute values are masked where conversion required."
            raise TimelyError(warp)
        increments = ma.array(self.times[..., 5] / 60.0, dtype=myint)
        indices = np.where(over_seconds)
        warp = tuple(list(indices) + [4])
        self.times[warp] = self.times[warp] + increments[indices]
        warp = tuple(list(indices) + [5])
        self.times[warp] = np.copysign(np.mod(seconds_abs[indices], 60),
                                       self.times[warp])
        indices = np.where(under_seconds)
        warp = tuple(list(indices) + [5])
        self.times[warp] = self.times[warp] + 60
        warp = tuple(list(indices) + [4])
        self.times[warp] = self.times[warp] - 1

    def seconds_to_hours(self):
        """Convert overloaded/negative second value to hours."""

        unmasked_seconds = 1 - ma.getmaskarray(self.times[..., 5])
        unmasked_hours = 1 - ma.getmaskarray(self.times[..., 3])
        seconds_abs = np.abs(self.times[..., 5])
        over_seconds = (seconds_abs >= 3600.0)
        under_seconds = (self.times[..., 5] < 0)
        warp1 = np.bitwise_and(over_seconds, 1 - unmasked_hours)
        warp2 = np.bitwise_and(under_seconds, 1 - unmasked_hours)
        warp = np.bitwise_or(warp1, warp2)
        if warp.sum() != 0:
            warp = "Some hour values are masked where conversion required."
            raise TimelyError(warp)
        increments = ma.array(self.times[..., 5] / 3600.0, dtype=myint)
        indices = np.where(over_seconds)
        warp = tuple(list(indices) + [3])
        self.times[warp] = self.times[warp] + increments[indices]
        warp = tuple(list(indices) + [5])
        self.times[warp] = np.copysign(np.mod(seconds_abs[indices], 3600),
                                       self.times[warp])
        indices = np.where(under_seconds)
        warp = tuple(list(indices) + [5])
        self.times[warp] = self.times[warp] + 3600
        warp = tuple(list(indices) + [3])
        self.times[warp] = self.times[warp] - 1

    def seconds_to_days(self):
        """Convert overloaded/negative second value to days."""

        unmasked_seconds = 1 - ma.getmaskarray(self.times[..., 5])
        unmasked_days = 1 - ma.getmaskarray(self.times[..., 2])
        seconds_abs = np.abs(self.times[..., 5])
        over_seconds = (seconds_abs >= 86400.0)
        under_seconds = (self.times[..., 5] < 0)
        warp1 = np.bitwise_and(over_seconds, 1 - unmasked_days)
        warp2 = np.bitwise_and(under_seconds, 1 - unmasked_days)
        warp = np.bitwise_or(warp1, warp2)
        if warp.sum() != 0:
            warp = "Some day values are masked where conversion required."
            raise TimelyError(warp)
        increments = ma.array(self.times[..., 5] / 86400.0, dtype=myint)
        indices = np.where(over_seconds)
        warp = tuple(list(indices) + [2])
        self.times[warp] = self.times[warp] + increments[indices]
        warp = tuple(list(indices) + [5])
        self.times[warp] = np.copysign(np.mod(seconds_abs[indices], 86400),
                                       self.times[warp])
        indices = np.where(under_seconds)
        warp = tuple(list(indices) + [5])
        self.times[warp] = self.times[warp] + 86400
        warp = tuple(list(indices) + [2])
        self.times[warp] = self.times[warp] - 1

    def minutes_to_hours(self):
        """Convert overloaded/negative minute value to hours."""

        unmasked_minutes = 1 - ma.getmaskarray(self.times[..., 4])
        unmasked_hours = 1 - ma.getmaskarray(self.times[..., 3])
        minutes_abs = np.abs(self.times[..., 4])
        over_minutes = (minutes_abs >= 60.0)
        under_minutes = (self.times[..., 4] < 0)
        warp1 = np.bitwise_and(over_minutes, 1 - unmasked_hours)
        warp2 = np.bitwise_and(under_minutes, 1 - unmasked_hours)
        warp = np.bitwise_or(warp1, warp2)
        if warp.sum() != 0:
            warp = "Some hour values are masked where conversion required."
            raise TimelyError(warp)
        increments = ma.array(self.times[..., 4] / 60.0, dtype=myint)
        indices = np.where(over_minutes)
        warp = tuple(list(indices) + [3])
        self.times[warp] = self.times[warp] + increments[indices]
        warp = tuple(list(indices) + [4])
        self.times[warp] = np.copysign(np.mod(minutes_abs[indices], 60),
                                       self.times[warp])
        indices = np.where(under_minutes)
        warp = tuple(list(indices) + [4])
        self.times[warp] = self.times[warp] + 60
        warp = tuple(list(indices) + [3])
        self.times[warp] = self.times[warp] - 1

    def minutes_to_days(self):
        """Convert overloaded/negative minute value to days."""

        unmasked_minutes = 1 - ma.getmaskarray(self.times[..., 4])
        unmasked_days = 1 - ma.getmaskarray(self.times[..., 2])
        minutes_abs = np.abs(self.times[..., 4])
        over_minutes = (minutes_abs >= 60.0)
        under_minutes = (self.times[..., 4] < 0)
        warp1 = np.bitwise_and(over_minutes, 1 - unmasked_days)
        warp2 = np.bitwise_and(under_minutes, 1 - unmasked_days)
        warp = np.bitwise_or(warp1, warp2)
        if warp.sum() != 0:
            warp = "Some day values are masked where conversion required."
            raise TimelyError(warp)
        increments = ma.array(self.times[..., 4] / 1440.0, dtype=myint)
        indices = np.where(over_minutes)
        warp = tuple(list(indices) + [2])
        self.times[warp] = self.times[warp] + increments[indices]
        warp = tuple(list(indices) + [4])
        self.times[warp] = np.copysign(np.mod(minutes_abs[indices], 1440),
                                       self.times[warp])
        indices = np.where(under_minutes)
        warp = tuple(list(indices) + [4])
        self.times[warp] = self.times[warp] + 1440
        warp = tuple(list(indices) + [2])
        self.times[warp] = self.times[warp] - 1

    def hours_to_days(self):
        """Convert overloaded/negative hours value to days."""

        unmasked_hours = 1 - ma.getmaskarray(self.times[..., 3])
        unmasked_days = 1 - ma.getmaskarray(self.times[..., 2])
        hours_abs = np.abs(self.times[..., 3])
        over_hours = (hours_abs >= 24.0)
        under_hours = (self.times[..., 3] < 0)
        warp1 = np.bitwise_and(over_hours, 1 - unmasked_days)
        warp2 = np.bitwise_and(under_hours, 1 - unmasked_days)
        warp = np.bitwise_or(warp1, warp2)
        if warp.sum() != 0:
            warp = "Some day values are masked where conversion required."
            raise TimelyError(warp)
        increments = ma.array(self.times[..., 3] / 24.0, dtype=myint)
        indices = np.where(over_hours)
        warp = tuple(list(indices) + [2])
        self.times[warp] = self.times[warp] + increments[indices]
        warp = tuple(list(indices) + [3])
        self.times[warp] = np.copysign(np.mod(hours_abs[indices], 24),
                                       self.times[warp])
        indices = np.where(under_hours)
        warp = tuple(list(indices) + [3])
        self.times[warp] = self.times[warp] + 24
        warp = tuple(list(indices) + [2])
        self.times[warp] = self.times[warp] - 1


#
class _Time(_CollectionTime):
    """Base unit for time."""

    def year(self, set_value=None):
        """Year element of the time vector.

        Parameters
        ----------
        set_value - float
            value to set in the time vector (default returns current value).

        Returns
        -------
        year - numerical
           only returned if set_value is None.

        """

        if set_value is None:
            return self.times[0, 0]
        else:
            _CollectionTime.year(self, set_value)

    def cycle(self, set_value=None):
        """Cycle element of the time vector.

        Parameters
        ----------
        set_value - float
            value to set in the time vector (default returns current value).

        Returns
        -------
        cycle - numerical
            only returned if set_value is None.

        """

        if set_value is None:
            return self.times[0, 1]
        else:
            _CollectionTime.cycle(self, set_value)

    def month(self, set_value=None):
        """Month element of the time.

        Parameters
        ----------
        set_value - float
            value to set in the time vector (default returns current value).

        Returns
        -------
        month - numerical
            only returned if set_value is None.

        Notes
        -----
        This is simply an alias for the cycle() method.

        """

        return self.cycle(set_value)

    def day(self, set_value=None):
        """Day element of the time vector.

        Parameters
        ----------
        set_value - float
            value to set in the time vector (default returns current value).

        Returns
        -------
        day - numerical
            only returned if set_value is None.

        """

        if set_value is None:
            return self.times[0, 2]
        else:
            _CollectionTime.day(self, set_value)

    def hour(self, set_value=None):
        """Hour element of the time vector.

        Parameters
        ----------
        set_value - float
            value to set in the time vector (default returns current value).

        Returns
        -------
        hour - numerical
            only returned if set_value is None.

        """

        if set_value is None:
            return self.times[0, 3]
        else:
            _CollectionTime.hour(self, set_value)

    def minute(self, set_value=None):
        """Minute element of the time vector.

        Parameters
        ----------
        set_value - float
            value to set in the time vector (default returns current value).

        Returns
        -------
        minute - numerical
            only returned if set_value is None.

        """

        if set_value is None:
            return self.times[0, 4]
        else:
            _CollectionTime.minute(self, set_value)

    def second(self, set_value=None):
        """Second element of the time vector.

        Parameters
        ----------
        set_value - float
            value to set in the time vector (default returns current value).

        Returns
        -------
        second - numerical
            only returned if set_value is None.

        """

        if set_value is None:
            return self.times[0, 5]
        else:
            _CollectionTime.second(self, set_value)

    def __add__(self, other):
        ctime1 = _CollectionTime.__add__(self, other)
        return _Time(ctime1.times[...])

    def __sub__(self, other):
        ctime1 = _CollectionTime.__sub__(self, other)
        return _Time(ctime1.times[...])

    def __mul__(self, multiplier):
        """Multiply every element of the time vectors by a multiplier.

        Parameters
        ----------
        multiplier : numerical

        Returns
        -------
        out - _Time

        """

        ctime1 = _CollectionTime.__mul__(self, multiplier)
        return _Time(ctime1.times[...])


#
class MultiDeltaT(_CollectionTime):
    """MultiDeltaT representation."""

    def __init__(self, times):
        """Initialize MultiDeltaT.

        Parameters
        ----------
        times - matrix
            M1 x M2 x ... x Mm x 6 time vectors

        """

        _CollectionTime.__init__(self, times)
        self.times[ma.where(ma.getmaskarray(self.times))] = 0
        del self.resolution

    def __nonzero__(self):
        """A MultiDeltaT object is nonzero if it has a nonzero element."""

        if self.times.sum() == 0:
            return False
        return True

    def __eq__(self, other):
        raise NotImplementedError("Equality of two MultiDeltaT.")

    def __ne__(self, other):
        if self == other:
            return False
        else:
            return True

    def __add__(self, other):
        ctime1 = _CollectionTime.__add__(self, other)
        return MultiDeltaT(ctime1.times[...])

    def __sub__(self, other):
        ctime1 = _CollectionTime.__sub__(self, other)
        return MultiDeltaT(ctime1.times[...])

    def __mul__(self, multiplier):
        return MultiDeltaT(self.times[...] * multiplier)


#
class DeltaT(MultiDeltaT):
    """Time interval definition."""

    def __str__(self):
        try:
            deltat_string = "%f years" % (self.year(),)
        except TimelyError:
            deltat_string = ''
        try:
            deltat_string += ", %f cycles" % (self.cycle(),)
        except TimelyError:
            pass
        try:
            deltat_string += ", %f days" % (self.day(),)
        except TimelyError:
            pass
        try:
            deltat_string += ", %f hours" % (self.hour(),)
        except TimelyError:
            pass
        try:
            deltat_string += ", %f minutes" % (self.minute(),)
        except TimelyError:
            pass
        try:
            deltat_string += ", %f seconds" % (self.second(),)
        except TimelyError:
            pass
        return deltat_string.lstrip(', ')

    def __eq__(self, other):
        """Equality of two MultiDeltaT.

        Parameters
        ----------
        other - MultiDeltaT

        Notes
        -----
        An exception is raised if there is any ambiguity at all in the
        operation.

        """

        # new_self = deepcopy(self)
        new_self = MultiDeltaT(self.times[...])
        new_self.propagate_days_decimals()
        new_self.propagate_hours_decimals()
        new_self.propagate_minutes_decimals()
        new_self.seconds_to_minutes()
        new_self.minutes_to_hours()
        new_self.hours_to_days()
        # new_other = deepcopy(other)
        new_other = MultiDeltaT(other.times[...])
        new_other.propagate_days_decimals()
        new_other.propagate_hours_decimals()
        new_other.propagate_minutes_decimals()
        new_other.seconds_to_minutes()
        new_other.minutes_to_hours()
        new_other.hours_to_days()
        if (_CollectionTime.__eq__(new_self, new_other)):
            return True
        else:
            # Year value mixed with cycles/days
            flag_year = new_self.year() != 0
            flag_cycle = new_other.cycle() != 0
            flag_day = new_other.day() != 0
            warp = np.bitwise_or(flag_cycle, flag_day)
            if np.bitwise_and(flag_year, warp).sum():
                raise TimelyError("Ambiguous operation.")
            flag_year = new_other.year() != 0
            flag_cycle = new_self.cycle() != 0
            flag_day = new_self.day() != 0
            warp = np.bitwise_or(flag_cycle, flag_day)
            if np.bitwise_and(flag_year, warp).sum():
                raise TimelyError("Ambiguous operation.")
            # Cycle value mixed with days
            flag_cycle = new_self.cycle() != 0
            flag_day = new_other.day() != 0
            if np.bitwise_and(flag_cycle, flag_day).sum():
                raise TimelyError("Ambiguous operation.")
            flag_cycle = new_other.cycle() != 0
            flag_day = new_self.day() != 0
            if np.bitwise_and(flag_cycle, flag_day).sum():
                raise TimelyError("Ambiguous operation.")
            return False

    def __ne__(self, other):
        if self == other:
            return False
        else:
            return True

    def __add__(self, other):
        mdeltat1 = MultiDeltaT.__add__(self, other)
        return DeltaT(mdeltat1.times[...])

    def __sub__(self, other):
        mdeltat1 = MultiDeltaT.__sub__(self, other)
        return DeltaT(mdeltat1.times[...])

    def __mul__(self, multiplier):
        mdeltat1 = MultiDeltaT.__mul__(self, multiplier)
        return DeltaT(mdeltat1.times[...])


#
# Shortcuts for trivial DeltaT objects.
#
one_second = DeltaT([0, 0, 0, 0, 0, 1])
one_minute = DeltaT([0, 0, 0, 0, 1])
one_hour = DeltaT([0, 0, 0, 1])
one_day = DeltaT([0, 0, 1])
one_cycle = DeltaT([0, 1])
one_year = DeltaT([1])


#
class Date2(_Time):
    """Date representation."""

    def __init__(self, time, calendar=CalGregorian):
        """Initialize date.

        Parameters
        ----------
        time : sequence
            vector of length 1 to 6, with numeric elements.
        calendar : Calendar object, optional
            (default is the built-in gregorian calendar).

        Notes
        -----
        The input time vector takes one of the following form:
        [YYYY]
        [YYYY,CC]
        [YYYY,CC,DD]
        [YYYY,CC,DD,hh]
        [YYYY,CC,DD,hh,mm]
        [YYYY,CC,DD,hh,mm,ss]
        CC stands for cycle (e.g. month (MM)).
        All values are integer, except for the last element of the
        time vector, which can be float.
        The CC and DD values have to be in the `year_cycles` and
        `days_in_cycle` results from the calendar.
        The hh, mm and ss values have to be within their usual range.

        """

        _Time.__init__(self, time)
        masked_indices = ma.where(ma.getmaskarray(self.time))[0]
        if (len(masked_indices) and
                (~ma.getmaskarray(self.time)[masked_indices[0] + 1:]).any()):
            raise TimelyError("Unmasked value following a masked value.")
        decimal_deltat = DeltaT([0.0])
        for i, time_i in enumerate(self.time):
            if ~ma.getmask(self.time[i]):
                try:
                    (fractional, integral) = np.modf(time_i)
                except (TypeError, ValueError) as e:
                    msg = "An element of the date is not numerical."
                    raise TimelyError(msg)
                if (time_i < 0) and (i != 0):
                    raise TimelyError("Negative value in date.")
                if fractional:
                    if self.resolution != i + 1:
                        raise TimelyError("Unprocessed decimals in date.")
                    else:
                        decimal_deltat.time[i] = fractional
                        self.time[i] = int(integral)
        # self.time = ma.array(self.time,dtype=myint)
        self.calendar = calendar
        if ma.getmask(self.time[0]):
            raise TimelyError("Empty time vector.")
        if ma.getmask(self.time[1]):
            self.cycle(1)
        else:
            cycles_values = self.calendar.year_cycles(self.year())
            if not (self.cycle()) in cycles_values.keys():
                raise TimelyError("Cycle value outside of calendar.")
        if ma.getmask(self.time[2]):
            self.day(self.calendar.days_in_cycle(1, self.year())[0])
        else:
            days_values = self.calendar.days_in_cycle(self.cycle(), self.year())
            if not (self.day()) in days_values:
                raise TimelyError("Day value outside of calendar.")
        if ma.getmask(self.time[3]):
            self.hour(0)
        else:
            if (self.hour() < 0) or (self.hour() >= 24.0):
                raise TimelyError("Hour value outside of range.")
        if ma.getmask(self.time[4]):
            self.minute(0)
        else:
            if (self.minute() < 0) or (self.minute() >= 60.0):
                raise TimelyError("Minute value outside of range.")
        if ma.getmask(self.time[5]):
            self.second(0)
        else:
            if (self.second() < 0) or (self.second() >= 60.0):
                raise TimelyError("Second value outside of range.")
        if decimal_deltat:
            # actual_date = self.__add__(decimal_deltat)
            # self.time = actual_date.time
            self.decimals = True

    def __str__(self):
        date_string = "%s" % (str(self.year()).zfill(4),)
        time_vector_length = len(self.time)
        if ~ma.getmask(self.time[1]):
            date_string += "-%s" % (str(self.cycle()).zfill(2),)
        if ~ma.getmask(self.time[2]):
            date_string += "-%s" % (str(self.day()).zfill(2),)
        if ~ma.getmask(self.time[3]):
            date_string += "T%s" % (str(self.hour()).zfill(2),)
        if ~ma.getmask(self.time[4]):
            date_string += ":%s" % (str(self.minute()).zfill(2),)
        if ~ma.getmask(self.time[5]):
            date_string += ":%s" % (str(self.second()).zfill(2),)
        if ~ma.getmask(self.time[3]):
            date_string += 'Z'
        return date_string

    def __eq__(self, other):
        if _Time.__eq__(self, other) and (self.calendar == other.calendar):
            return True
        else:
            return False

    def __ne__(self, other):
        if self == other:
            return False
        else:
            return True

    def __gt__(self, other):
        if self.calendar == other.calendar:
            gt = (self.time > other.time)
            gt.mask = ma.getmaskarray(gt)
            gt.mask[ma.where(self.time == other.time)] = True
            gt_unmasked = gt[~gt.mask]
            if len(gt_unmasked) == 0:
                if self.time.count() == other.time.count():
                    return False
                else:
                    raise TimelyError("Ambiguous operations.")
            else:
                if gt_unmasked[0]:
                    return True
                else:
                    return False
        else:
            raise NotImplementedError("Different calendars.")

    def __ge__(self, other):
        if self.calendar == other.calendar:
            gt = (self.time > other.time)
            gt.mask = ma.getmaskarray(gt)
            gt.mask[ma.where(self.time == other.time)] = True
            gt_unmasked = gt[~gt.mask]
            if len(gt_unmasked) == 0:
                if self.time.count() == other.time.count():
                    return True
                else:
                    raise TimelyError("Ambiguous operations.")
            else:
                if gt_unmasked[0]:
                    return True
                else:
                    return False
        else:
            raise NotImplementedError("Different calendars.")

    def __lt__(self, other):
        if self.calendar == other.calendar:
            lt = (self.time < other.time)
            lt.mask = ma.getmaskarray(lt)
            lt.mask[ma.where(self.time == other.time)] = True
            lt_unmasked = lt[~lt.mask]
            if len(lt_unmasked) == 0:
                if self.time.count() == other.time.count():
                    return False
                else:
                    raise TimelyError("Ambiguous operations.")
            else:
                if lt_unmasked[0]:
                    return True
                else:
                    return False
        else:
            raise NotImplementedError("Different calendars.")

    def __le__(self, other):
        if self.calendar == other.calendar:
            lt = (self.time < other.time)
            lt.mask = ma.getmaskarray(lt)
            lt.mask[ma.where(self.time == other.time)] = True
            lt_unmasked = lt[~lt.mask]
            if len(lt_unmasked) == 0:
                if self.time.count() == other.time.count():
                    return True
                else:
                    raise TimelyError("Ambiguous operations.")
            else:
                if lt_unmasked[0]:
                    return True
                else:
                    return False
        else:
            raise NotImplementedError("Different calendars.")

    def day_number_in_year(self):
        """Day number in year."""

        day_in_year = 0
        for i in range(1, int(self.cycle())):
            day_in_year += len(self.calendar.days_in_cycle(i, self.year()))
        current_days = self.calendar.days_in_cycle(self.cycle(), self.year())
        day_in_year += current_days.index(self.day()) + 1
        return day_in_year

    def add_years(self, increment, fractional_interpretation='days'):
        """Add (or substract) a number of years to (from) the date.

        Parameters
        ----------
        increment : int
            number of years to add or substract
        fractional_interpretation : str
            'days' or 'cycles'

        """

        (fractional, integral) = np.modf(increment)
        self.year(self.year() + int(integral))
        if fractional:
            cal = self.calendar
            if fractional_interpretation == 'days':
                days_in_year = cal.count_days_in_year(self.year())
                self.add_days(fractional * days_in_year)
            elif fractional_interpretation in ['cycles', 'months']:
                days_in_cycle = len(cal.days_in_cycle(self.cycle(), self.year()))
                self.add_months(fractional * days_in_cycle)

    def add_cycles(self, increment):
        """Add (or substract) a number of cycles to (from) the date.

        Parameters
        ----------
        increment : int
            number of cycles to add or substract.

        """

        (fractional, integral) = np.modf(increment)
        increment = int(integral)
        cal = self.calendar
        number_of_cycles = len(cal.year_cycles(self.year()))
        while (self.cycle() + increment) > number_of_cycles:
            increment -= (number_of_cycles - self.cycle() + 1)
            self.year(self.year() + 1)
            self.cycle(1)
            number_of_cycles = len(cal.year_cycles(self.year()))
        while (self.cycle() + increment) < 1:
            increment += self.cycle()
            self.year(self.year() - 1)
            self.cycle(len(cal.year_cycles(self.year())))
        self.cycle(self.cycle() + increment)
        if fractional:
            days_in_cycle = len(cal.days_in_cycle(self.cycle(), self.year()))
            self.add_days(fractional * days_in_cycle)

    def add_days(self, increment):
        """Add (or substract) a number of days to (from) the date.

        Parameters
        ----------
        increment : int
            number of days to add or substract.

        """

        (fractional, integral) = np.modf(increment)
        increment = int(integral)
        cal = self.calendar
        if cal.days_in_cycle(self.cycle(), self.year()) == float('inf'):
            self.day(self.day() + increment)
        else:
            day_in_year = self.day_number_in_year()
            number_of_days = cal.count_days_in_year(self.year())
            while (day_in_year + increment) > number_of_days:
                increment -= (number_of_days - day_in_year + 1)
                self.year(self.year() + 1)
                self.cycle(1)
                new_days = cal.days_in_cycle(self.cycle(), self.year())
                self.day(new_days[0])
                day_in_year = 1
                number_of_days = cal.count_days_in_year(self.year())
            while (day_in_year + increment) < 1:
                increment += day_in_year
                self.year(self.year() - 1)
                self.cycle(len(cal.year_cycles(self.year())))
                new_days = cal.days_in_cycle(self.cycle(), self.year())
                self.day(new_days[-1])
                day_in_year = cal.count_days_in_year(self.year())
            current_days = cal.days_in_cycle(self.cycle(), self.year())
            number_of_days = len(current_days)
            day_in_cycle = current_days.index(self.day()) + 1
            while (day_in_cycle + increment) > number_of_days:
                increment -= (number_of_days - day_in_cycle + 1)
                self.cycle(self.cycle() + 1)
                current_days = cal.days_in_cycle(self.cycle(), self.year())
                self.day(current_days[0])
                day_in_cycle = 1
                number_of_days = len(current_days)
            while (day_in_cycle + increment) < 1:
                increment += day_in_cycle
                self.cycle(self.cycle() - 1)
                current_days = cal.days_in_cycle(self.cycle(), self.year())
                self.day(current_days[-1])
                day_in_cycle = len(current_days)
            self.day(current_days[day_in_cycle + increment - 1])
        if fractional:
            self.add_hours(24.0 * fractional)

    def add_hours(self, increment):
        """Add (or substract) a number of hours to (from) the date.

        Parameters
        ----------
        increment : int
            number of hours to add or substract.

        """

        (fractional, integral) = np.modf(increment)
        self.hour(self.hour() + int(integral))
        if fractional:
            self.add_minutes(60.0 * fractional)

    def add_minutes(self, increment):
        """Add (or substract) a number of minutes to (from) the date.

        Parameters
        ----------
        increment : int
            number of minutes to add or substract.

        """

        (fractional, integral) = np.modf(increment)
        self.minute(self.minute() + int(integral))
        if fractional:
            self.add_seconds(60.0 * fractional)

    def add_seconds(self, increment, threshold=0.0001,
                    float_type=np.dtype('float64')):
        """Add (or substract) a number of seconds to (from) the date.

        Parameters
        ----------
        increment : int
            number of seconds to add or substract.
        threshold : float
            rounding threshold
        float_type : dtype
            float type when necessary

        """

        (fractional, integral) = np.modf(increment)
        self.second(self.second() + int(integral))
        # if the date has decimals, it remains that way
        if self.decimals:
            self.second(self.second() + fractional)
        # if date has no decimals, use a threshold.
        elif fractional:
            if fractional > (1.0 - threshold):
                self.second(self.second() + 1)
                warnings.warn("Rounding up and throwing away %s milliseconds." % (str((1 - fractional) / 1000.0),))
            elif fractional < threshold:
                warnings.warn("Throwing away %s milliseconds." % (str(fractional / 1000.0),))
            else:
                self.time = ma.array(self.time, dtype=float_type)
                self.second(self.second() + fractional)
        self.seconds_to_minutes()
        self.minutes_to_hours()
        self.hours_to_days()

    def seconds_to_days(self):
        """Convert overloaded/negative second value to days."""

        if ~ma.getmask(self.time[5]):
            second_abs = abs(self.second())
            if second_abs >= 86400.0:
                increment = int(self.second() / 86400.0)
                self.add_days(increment)
                self.second(np.copysign(second_abs % 86400, self.second()))
            if self.second() < 0:
                self.second(self.second() + 86400)
                self.add_days(-1)

    def minutes_to_days(self):
        """Convert overloaded/negative minute value to days."""

        if ~ma.getmask(self.time[4]):
            minute_abs = abs(self.minute())
            if minute_abs >= 1440.0:
                increment = int(self.minute() / 1440.0)
                self.add_days(increment)
                self.minute(np.copysign(minute_abs % 1440, self.minute()))
            if self.minute() < 0:
                self.minute(self.minute() + 1440)
                self.add_days(-1)

    def hours_to_days(self):
        """Convert overloaded/negative hour value to days."""

        if ~ma.getmask(self.time[3]):
            hour_abs = abs(self.hour())
            if hour_abs >= 24.0:
                increment = int(self.hour() / 24.0)
                self.add_days(increment)
                self.hour(np.copysign(hour_abs % 24, self.hour()))
            if self.hour() < 0:
                self.hour(self.hour() + 24)
                self.add_days(-1)

    def __add__(self, deltat):
        """Add a time interval to a date.
        
        Parameters
        ----------
        deltat : DeltaT object

        Notes
        -----
        The order in which a combination of years, months and days are added
        to a date can change the result. It is recommended to add only one
        component at a time to a date. Also, decimals in the year value
        of the DeltaT are interpreted as a fraction of the number of days
        in the year. This means that adding 0.5 years is NOT equivalent to
        adding 6 months in a gregorian calendar. In fact, you should not use
        decimals in the year and month values of the DeltaT unless you really
        know what you are doing...
        
        In any case, this function performs the operation in the following
        order: years, cycles, days, hours, minutes, seconds.

        """

        # new_date = deepcopy(self)
        new_date = Date(self.time, self.calendar)
        new_date.add_years(deltat.year())
        new_date.add_cycles(deltat.cycle())
        new_date.add_days(deltat.day())
        new_date.add_hours(deltat.hour())
        new_date.add_minutes(deltat.minute())
        new_date.add_seconds(deltat.second())
        return new_date

    def __sub__(self, deltat):
        return self + (deltat * -1)

    def buffer(self, deltat):
        # Currently assumes a positive deltat...
        return Period(self - deltat, self + deltat)

    def boundary(self):
        return None

    def centroid(self):
        return self

    def convex_hull(self):
        return self

    def envelope(self):
        return self.convex_hull()

    def difference(self, other):
        if isinstance(other, Date):
            if self == other:
                return None
            else:
                return self
        else:
            raise NotImplementedError()

    def intersection(self, other):
        if isinstance(other, Date):
            if self == other:
                return self
            else:
                return None
        elif isinstance(other, Period):
            # pending
            raise NotImplementedError()
        else:
            raise NotImplementedError()

    def symmetric_difference(self, other):
        if isinstance(other, Date):
            if self == other:
                return None
            else:
                return self
        else:
            raise NotImplementedError()

    def union(self, other):
        if isinstance(other, Date):
            if self == other:
                return self
            else:
                if self.calendar != other.calendar:
                    msg = "Union of different calendars not supported."
                    raise TimelyError(msg)
                return MultiDate(ma.array([self.time, other.time], self.calendar))
        else:
            raise NotImplementedError()

    def contains(self, other):
        if isintance(other, Date):
            return False
        else:
            return NotImplementedError()

    def within(self, other):
        if other.contains(self):
            return True
        else:
            return False

    def intersects(self, other):
        if isinstance(other, Date):
            if self == other:
                return True
            else:
                return False
        elif isinstance(other, Period):
            if self.time.count() < other.initial_time.count():
                initial_copy = Date(deepcopy(other.initial_time), other.calendar)
                initial_copy.reduce(self.time.count())
                final_copy = Date(deepcopy(other.final_time), other.calendar)
                final_copy.reduce(self.time.count())
                if (self == initial_copy) or (self == final_copy):
                    raise TimelyError("Ambiguous operation.")
                elif (self > Date(other.initial_time, other.calendar) and
                      self < Date(other.final_time, other.calendar)):
                    return True
                else:
                    return False
            elif self.time.count() == other.initial_time.count():
                if (self >= Date(other.initial_time, other.calendar) and
                        self <= Date(other.final_time, other.calendar)):
                    return True
                else:
                    return False
            else:
                date_copy = deepcopy(self)
                date_copy.reduce(other.initial_time.count())
                if (date_copy >= Date(other.initial_time, other.calendar) and
                        date_copy <= Date(other.final_time, other.calendar)):
                    return True
                else:
                    return False
        else:
            raise TimelyError("Unsupported type for intersects method.")

    def disjoint(self, other):
        if self.intersects(other):
            return False
        else:
            return True

    def equals(self, other):
        if isinstance(other, Date):
            if self == other:
                return True
            else:
                return False
        else:
            raise NotImplementedError()

    def touches(self, other):
        if isinstance(other, Date):
            return False
        else:
            raise NotImplementedError()

    def distance(self, other):
        raise NotImplementedError()

    def bounds(self):
        return (self, self)

    def length(self):
        return DeltaT([0])


#
class MultiDate(_CollectionTime):
    """MultiDate representation."""

    def __init__(self, times, calendars=CalGregorian):
        """Initialize MultiDate."""

        _CollectionTime.__init__(self, times)
        del self.resolution
        (fractional, integral) = np.modf(self.times)
        if not fractional.sum():
            self.times = ma.array(self.times, dtype=myint)
            self.decimals = False
        if not hasattr(calendars, '__iter__'):
            self.calendars = ma.empty(self.times.shape[:-1],
                                      dtype=type(Calendar))
            self.calendars[...] = calendars
        else:
            self.calendars = calendars
        self._unique_calendars = np.unique(self.calendars)
        # Look for non-numerical values :
        try:
            (fractional, integral) = np.modf(self.times)
        except (TypeError, ValueError) as e:
            msg = "An element of the date is not numerical."
            raise TimelyError(msg)
        # Look for unmasked element following a masked element
        flag_masked_previous = self.times.mask[..., 0]
        for i in range(1, 6):
            flag_masked = self.times.mask[..., i]
            if (flag_masked_previous * (1 - flag_masked)).sum():
                msg = "Unmasked element following a masked element."
                raise TimelyError(msg)
            flag_masked_previous = flag_masked
        # Look for decimals :
        if fractional[..., 0:5].sum():
            raise TimelyError("Unprocessed decimal in dates.")
        # Look for negative values :
        if (self.times[..., 1:6] < 0).sum():
            raise TimelyError("Negative value in date.")
        # Check validity of elements and fill masked values :
        ijs = np.where(self.times.mask[..., 1])
        warp = tuple(list(ijs) + [1])
        self.times[warp] = 1
        cycles_in_year = self.count_cycles_in_year()
        days_in_cycle = self.days_in_cycle()
        ijs = np.where(self.times.mask[..., 2])
        warp = tuple(list(ijs) + [2])
        warp2 = _Vget_item(days_in_cycle, 0)
        self.times[warp] = warp2[ijs]
        t1 = self.times[..., 1] < 1
        t2 = self.times[..., 1] > cycles_in_year
        t3 = np.bitwise_or(t1, t2)
        if t3.sum():
            raise TimelyError("Invalid cycle value.")
        try:
            dummy = _Vindex(days_in_cycle, self.times[..., 2])
        except:
            raise TimelyError("Invalid day value.")
        ijs = np.where(self.times.mask[..., 3])
        warp = tuple(list(ijs) + [3])
        self.times[warp] = 0
        if (self.times[..., 3] >= 24).sum():
            raise TimelyError("Invalid hour value.")
        ijs = np.where(self.times.mask[..., 4])
        warp = tuple(list(ijs) + [4])
        self.times[warp] = 0
        if (self.times[..., 4] >= 60).sum():
            raise TimelyError("Invalid minute value.")
        ijs = np.where(self.times.mask[..., 5])
        warp = tuple(list(ijs) + [5])
        self.times[warp] = 0
        if (self.times[..., 5] >= 60).sum():
            raise TimelyError("Invalid second value.")

    def __getitem__(self, item):
        if isinstance(item, tuple):
            new_slices = list(item)
            new_slices.append(slice(None, None, None))
            new_slices = tuple(new_slices)
            subset_times = self.times[new_slices]
            if subset_times.shape == (6,):
                return Date(subset_times, self.calendars[item])
            else:
                return MultiDate(self.times[new_slices], self.calendars[item])
        elif isinstance(item, slice):
            subset_times = self.times[item, :]
            if subset_times.shape == (6,):
                return Date(subset_times, self.calendars[item])
            else:
                return MultiDate(self.times[item, :], self.calendars[item])
        else:
            return Date(self.times[item, :], self.calendars[item])

    def __eq__(self, other):
        c2 = np.equal(self.calendars, other.calendars).all()
        if _CollectionTime.__eq__(self, other) and c2:
            return True
        else:
            return False

    def __ne__(self, other):
        if self == other:
            return False
        else:
            return True

    def __gt__(self, other):
        if isinstance(other, Date):
            mtimes = ma.zeros(self.times.shape)
            for i in range(6):
                mtimes[..., i] = other.times[..., i]
            other = MultiDate(mtimes, other.calendar)
        if not (self.calendars == other.calendars).all():
            warp = "you better know what you are doing..."
            warnings.warn("__gt__ using different calendars, " + warp)
        warp = self.times[..., 5] > other.times[..., 5]
        warp = np.bitwise_and(self.times[..., 4] == other.times[..., 4], warp)
        warp = np.bitwise_or(self.times[..., 4] > other.times[..., 4], warp)
        warp = np.bitwise_and(self.times[..., 3] == other.times[..., 3], warp)
        warp = np.bitwise_or(self.times[..., 3] > other.times[..., 3], warp)
        warp = np.bitwise_and(self.times[..., 2] == other.times[..., 2], warp)
        warp = np.bitwise_or(self.times[..., 2] > other.times[..., 2], warp)
        warp = np.bitwise_and(self.times[..., 1] == other.times[..., 1], warp)
        warp = np.bitwise_or(self.times[..., 1] > other.times[..., 1], warp)
        warp = np.bitwise_and(self.times[..., 0] == other.times[..., 0], warp)
        return np.bitwise_or(self.times[..., 0] > other.times[..., 0], warp)

    def __lt__(self, other):
        if isinstance(other, Date):
            mtimes = ma.zeros(self.times.shape)
            for i in range(6):
                mtimes[..., i] = other.times[..., i]
            other = MultiDate(mtimes, other.calendar)
        if not (self.calendars == other.calendars).all():
            warp = "you better know what you are doing..."
            warnings.warn("__gt__ using different calendars, " + warp)
        warp = self.times[..., 5] < other.times[..., 5]
        warp = np.bitwise_and(self.times[..., 4] == other.times[..., 4], warp)
        warp = np.bitwise_or(self.times[..., 4] < other.times[..., 4], warp)
        warp = np.bitwise_and(self.times[..., 3] == other.times[..., 3], warp)
        warp = np.bitwise_or(self.times[..., 3] < other.times[..., 3], warp)
        warp = np.bitwise_and(self.times[..., 2] == other.times[..., 2], warp)
        warp = np.bitwise_or(self.times[..., 2] < other.times[..., 2], warp)
        warp = np.bitwise_and(self.times[..., 1] == other.times[..., 1], warp)
        warp = np.bitwise_or(self.times[..., 1] < other.times[..., 1], warp)
        warp = np.bitwise_and(self.times[..., 0] == other.times[..., 0], warp)
        return np.bitwise_or(self.times[..., 0] < other.times[..., 0], warp)

    def __ge__(self, other):
        if isinstance(other, Date):
            mtimes = ma.zeros(self.times.shape)
            for i in range(6):
                mtimes[..., i] = other.times[..., i]
            other = MultiDate(mtimes, other.calendar)
        if not (self.calendars == other.calendars).all():
            warp = "you better know what you are doing..."
            warnings.warn("__gt__ using different calendars, " + warp)
        warp = self.times[..., 5] >= other.times[..., 5]
        warp = np.bitwise_and(self.times[..., 4] == other.times[..., 4], warp)
        warp = np.bitwise_or(self.times[..., 4] > other.times[..., 4], warp)
        warp = np.bitwise_and(self.times[..., 3] == other.times[..., 3], warp)
        warp = np.bitwise_or(self.times[..., 3] > other.times[..., 3], warp)
        warp = np.bitwise_and(self.times[..., 2] == other.times[..., 2], warp)
        warp = np.bitwise_or(self.times[..., 2] > other.times[..., 2], warp)
        warp = np.bitwise_and(self.times[..., 1] == other.times[..., 1], warp)
        warp = np.bitwise_or(self.times[..., 1] > other.times[..., 1], warp)
        warp = np.bitwise_and(self.times[..., 0] == other.times[..., 0], warp)
        return np.bitwise_or(self.times[..., 0] > other.times[..., 0], warp)

    def __le__(self, other):
        if isinstance(other, Date):
            mtimes = ma.zeros(self.times.shape)
            for i in range(6):
                mtimes[..., i] = other.times[..., i]
            other = MultiDate(mtimes, other.calendar)
        if not (self.calendars == other.calendars).all():
            warp = "you better know what you are doing..."
            warnings.warn("__gt__ using different calendars, " + warp)
        warp = self.times[..., 5] <= other.times[..., 5]
        warp = np.bitwise_and(self.times[..., 4] == other.times[..., 4], warp)
        warp = np.bitwise_or(self.times[..., 4] < other.times[..., 4], warp)
        warp = np.bitwise_and(self.times[..., 3] == other.times[..., 3], warp)
        warp = np.bitwise_or(self.times[..., 3] < other.times[..., 3], warp)
        warp = np.bitwise_and(self.times[..., 2] == other.times[..., 2], warp)
        warp = np.bitwise_or(self.times[..., 2] < other.times[..., 2], warp)
        warp = np.bitwise_and(self.times[..., 1] == other.times[..., 1], warp)
        warp = np.bitwise_or(self.times[..., 1] < other.times[..., 1], warp)
        warp = np.bitwise_and(self.times[..., 0] == other.times[..., 0], warp)
        return np.bitwise_or(self.times[..., 0] < other.times[..., 0], warp)

    def year_cycles(self):
        ma_year_cycles = ma.empty(self.times.shape[:-1], dtype=type({}))
        for cal in self._unique_calendars:
            ijs = np.where(self.calendars == cal)
            warp = cal._Vyear_cycles(self.times[..., 0])
            ma_year_cycles[ijs] = warp[ijs]
        return ma_year_cycles

    def days_in_cycle(self):
        ma_days_in_cycle = ma.empty(self.times.shape[:-1], dtype=type([]))
        for cal in self._unique_calendars:
            ijs = np.where(self.calendars == cal)
            warp = cal._Vdays_in_cycle(self.times[..., 1], self.times[..., 0])
            ma_days_in_cycle[ijs] = warp[ijs]
        return ma_days_in_cycle

    def is_leap(self):
        ma_is_leap = ma.empty(self.times.shape[:-1], dtype=type(False))
        for cal in self._unique_calendars:
            ijs = np.where(self.calendars == cal)
            warp = cal._Vis_leap(self.times[..., 0])
            ma_is_leap[ijs] = warp[ijs]
        return ma_is_leap

    def count_cycles_in_year(self):
        ma_num_cycles_in_year = ma.empty(self.times.shape[:-1], dtype=myint)
        for cal in self._unique_calendars:
            ijs = np.where(self.calendars == cal)
            warp = cal._Vcount_cycles_in_year(self.times[..., 0])
            ma_num_cycles_in_year[ijs] = warp[ijs]
        return ma_num_cycles_in_year

    def count_days_in_cycle(self):
        ma_num_days_in_cycle = ma.empty(self.times.shape[:-1], dtype=myint)
        for cal in self._unique_calendars:
            ijs = np.where(self.calendars == cal)
            warp = cal._Vcount_days_in_cycle(self.times[..., 1],
                                             self.times[..., 0])
            ma_num_days_in_cycle[ijs] = warp[ijs]
        return ma_num_days_in_cycle

    def count_days_in_year(self):
        ma_num_days_in_year = ma.empty(self.times.shape[:-1], dtype=myint)
        for cal in self._unique_calendars:
            ijs = np.where(self.calendars == cal)
            warp = cal._Vcount_days_in_year(self.times[..., 0])
            ma_num_days_in_year[ijs] = warp[ijs]
        return ma_num_days_in_year

    def ith_day_in_cycle(self, indices):
        ma_ith_day_in_cycle = ma.empty(self.times.shape[:-1], dtype=myint)
        for cal in self._unique_calendars:
            ijs = np.where(self.calendars == cal)
            warp = cal._Vith_day_in_cycle(self.times[..., 1], self.times[..., 0],
                                          indices)
            ma_ith_day_in_cycle[ijs] = warp[ijs]
        return ma_ith_day_in_cycle

    def previous_cycle(self):
        ma_previous_cycle = ma.empty(self.times.shape[:-1], dtype=type(()))
        for cal in self._unique_calendars:
            ijs = np.where(self.calendars == cal)
            warp = cal._Vprevious_cycle(self.times[..., 1], self.times[..., 0])
            ma_previous_cycle[ijs] = warp[ijs]
        return ma_previous_cycle

    def count_cycles_in_previous_year(self):
        ma_num_cycles_in_previous_year = ma.empty(self.times.shape[:-1],
                                                  dtype=myint)
        for cal in self._unique_calendars:
            ijs = np.where(self.calendars == cal)
            warp = cal._Vcount_cycles_in_previous_year(self.times[..., 0])
            ma_num_cycles_in_previous_year[ijs] = warp[ijs]
        return ma_num_cycles_in_previous_year

    def count_days_in_previous_cycle(self):
        ma_num_days_in_previous_cycle = ma.empty(self.times.shape[:-1],
                                                 dtype=myint)
        for cal in self._unique_calendars:
            ijs = np.where(self.calendars == cal)
            warp = cal._Vcount_days_in_previous_cycle(self.times[..., 1],
                                                      self.times[..., 0])
            ma_num_days_in_previous_cycle[ijs] = warp[ijs]
        return ma_num_days_in_previous_cycle

    def day_number_in_cycle(self):
        """Day number in cycle."""

        days_in_cycle = self.days_in_cycle()
        warp = ma.ones(self.times.shape[:-1], dtype=myint)
        return _Vindex(days_in_cycle, self.times[..., 2]) + warp

    def day_number_in_year(self):
        """Day number in year."""

        ma_day_number_in_year = ma.zeros(self.times.shape[:-1], dtype=myint)
        my_ones = ma.ones(self.times.shape[:-1])
        for i in range(1, self.times[..., 1].max()):
            flag_over = self.count_cycles_in_year() < i
            this_cycle = my_ones * (i - (i - 1) * flag_over)
            ma_num_days_in_cycle = ma.empty(self.times.shape[:-1], dtype=myint)
            for cal in self._unique_calendars:
                ijs = np.where(self.calendars == cal)
                warp = cal._Vcount_days_in_cycle(this_cycle, self.times[..., 0])
                ma_num_days_in_cycle[ijs] = warp[ijs]
            warp1 = ma_num_days_in_cycle * (self.times[..., 1] > i)
            ma_day_number_in_year = ma_day_number_in_year + warp1
        return ma_day_number_in_year + self.day_number_in_cycle()

    def add_years(self, increments, fractional_interpretation='days'):
        """Add (or substract) a number of years to (from) the date.

        Parameters
        ----------
        increment : int
            number of years to add or substract
        fractional_interpretation : str
            'days' or 'cycles'

        """

        (fractional, integral) = np.modf(increments)
        if not hasattr(integral, 'size'):
            fractional = ma.ones(self.times.shape[:-1]) * fractional
            integral = ma.ones(self.times.shape[:-1]) * integral
        self.times[..., 0] = self.times[..., 0] + integral
        if fractional.sum() != 0:
            if fractional_interpretation == 'days':
                days_to_add = ma.zeros(self.times.shape[:-1])
                for cal in self._unique_calendars:
                    ijs = np.where(self.calendars == cal)
                    days_in_year = cal._Vcount_days_in_year(self.times[..., 0])
                    days_to_add[ijs] = fractional[ijs] * days_in_year[ijs]
                self.add_days(days_to_add)
            elif fractional_interpretation in ['cycles', 'months']:
                cycles_to_add = ma.zeros(self.times.shape[:-1])
                for cal in self._unique_calendars:
                    ijs = np.where(self.calendars == cal)
                    cyc_in_yr = cal._Vcount_cycles_in_year(self.times[..., 0])
                    cycles_to_add[ijs] = fractional[ijs] * cyc_in_yr[ijs]
                self.add_cycles(cycles_to_add)

    def add_cycles(self, increments):
        """Add (or substract) a number of cycles to (from) the date.

        Parameters
        ----------
        increment : int
            number of cycles to add or substract.

        """

        my_ones = ma.ones(self.times.shape[:-1])
        my_zeros = ma.zeros(self.times.shape[:-1])

        (fractional, integral) = np.modf(increments)
        if not hasattr(integral, 'size'):
            fractional = my_ones * fractional
            integral = my_ones * integral
        calendars = np.unique(self.calendars)

        # Add/substract just enough to get to first month where possible
        # Also substract when possible (i.e. does not go back to previous year)
        cycles_in_year = self.count_cycles_in_year()
        max_add = cycles_in_year - self.times[..., 1]
        max_sub = my_ones - self.times[..., 1]
        flag_over = integral > max_add
        flag_under = integral < max_sub
        flag_either = np.bitwise_or(flag_over, flag_under)
        self.times[..., 0] = self.times[..., 0] + flag_over
        flag_neg = integral < my_zeros
        warp1 = (self.times[..., 1] - my_ones) * flag_either
        warp2 = flag_neg * (1 - flag_under) * integral
        self.times[..., 1] = self.times[..., 1] - warp1 + warp2
        warp3 = flag_over * (max_add + my_ones)
        integral = integral - warp3 - flag_under * max_sub - warp2

        flag_under = my_zeros
        while True:
            cycles_in_year = self.count_cycles_in_year()
            integral = integral + cycles_in_year * flag_under
            flag_over = integral >= cycles_in_year
            flag_under = integral < my_zeros
            self.times[..., 0] = self.times[..., 0] + flag_over - flag_under
            integral = integral - cycles_in_year * flag_over
            if (1 - np.bitwise_or(flag_over, flag_under)).all():
                break
        integral = integral + cycles_in_year * flag_under
        self.times[..., 1] = self.times[..., 1] + integral

        if fractional.sum() != 0:
            days_to_add = ma.zeros(self.times.shape[:-1])
            for cal in calendars:
                ijs = np.where(self.calendars == cal)
                days_in_cycle = cal._Vcount_days_in_cycle(self.times[..., 1],
                                                          self.times[..., 0])
                days_to_add[ijs] = fractional[ijs] * days_in_cycle[ijs]
            self.add_days(days_to_add)

    def add_days(self, increments):
        """Add (or substract) a number of days to (from) the date.

        Parameters
        ----------
        increment : int
            number of days to add or substract.

        """

        my_ones = ma.ones(self.times.shape[:-1], dtype=myint)
        my_zeros = ma.zeros(self.times.shape[:-1], dtype=myint)

        # Separate integral and fractional part of the increments
        (fractional, integral) = np.modf(increments)
        # Make sure the data types and shapes are correct
        integral = ma.array(integral, dtype=myint)
        if not hasattr(integral, 'size'):
            fractional = ma.ones(self.times.shape[:-1]) * fractional
            integral = ma.ones(self.times.shape[:-1], dtype=myint) * integral

        # Add/substract just enough to get to first day where possible
        # Number of days in current year
        days_in_year = self.count_days_in_year()
        # Day number in current year
        days_numbers = self.day_number_in_year()
        # Maximum number of days we can add/substract in this year
        max_add = days_in_year - days_numbers
        max_sub = my_ones - days_numbers
        # Flags for increments that will require moving to another year
        flag_over = integral > max_add
        flag_under = integral < max_sub
        flag_either = np.bitwise_or(flag_over, flag_under)
        # Move to another year where necessary
        self.times[..., 0] = self.times[..., 0] + flag_over - flag_under
        # Where flag_either, we want to be on the first day of the first cycle
        # Set cycle = 1
        warp1 = (self.times[..., 1] - my_ones) * flag_either
        self.times[..., 1] = self.times[..., 1] - warp1
        # Set day = first day in first cycle
        first_day_in_first_cycle = ma.zeros(self.times.shape[:-1])
        for cal in self._unique_calendars:
            ijs = np.where(self.calendars == cal)
            dayval = cal._Vith_day_in_cycle(my_ones, self.times[..., 0], my_ones)
            first_day_in_first_cycle[ijs] = dayval[ijs]
        warp1 = (self.times[..., 2] - first_day_in_first_cycle) * flag_either
        self.times[..., 2] = self.times[..., 2] - warp1
        # Adjust remaining integral part
        days_in_year = self.count_days_in_year()
        integral = integral - flag_over * (max_add + my_ones) - flag_under * (max_sub - days_in_year)

        while True:
            flag_over = integral >= days_in_year
            flag_neg = integral < my_zeros
            flag_either = np.bitwise_or(flag_over, flag_neg * flag_under)
            self.times[..., 0] = self.times[..., 0] + flag_over - flag_under * flag_neg
            first_day_in_first_cycle = ma.zeros(self.times.shape[:-1])
            for cal in self._unique_calendars:
                ijs = np.where(self.calendars == cal)
                dayval = cal._Vith_day_in_cycle(my_ones, self.times[..., 0], my_ones)
                first_day_in_first_cycle[ijs] = dayval[ijs]
            warp1 = (self.times[..., 2] - first_day_in_first_cycle) * flag_either
            self.times[..., 2] = self.times[..., 2] - warp1
            warp1 = flag_over * days_in_year
            days_in_year = self.count_days_in_year()
            integral = integral - warp1 - flag_neg * flag_under * days_in_year
            if (1 - np.bitwise_or(flag_over, flag_under * flag_neg)).all():
                break

        # Add/substract just enough to get to first month where possible
        # Also substract when possible (i.e. does not go back to previous year)
        days_in_cycle = self.count_days_in_cycle()
        days_numbers = self.day_number_in_cycle()
        max_add = days_in_cycle - days_numbers
        max_sub = my_ones - days_numbers
        flag_over = integral > max_add
        flag_under = integral < max_sub
        flag_either = np.bitwise_or(flag_over, flag_under)
        self.times[..., 1] = self.times[..., 1] + flag_over - flag_under
        first_day_in_cycle = ma.zeros(self.times.shape[:-1])
        for cal in self._unique_calendars:
            ijs = np.where(self.calendars == cal)
            dayval = cal._Vith_day_in_cycle(self.times[..., 1], self.times[..., 0], my_ones)
            first_day_in_cycle[ijs] = dayval[ijs]
        warp1 = (self.times[..., 2] - first_day_in_cycle) * flag_either
        self.times[..., 2] = self.times[..., 2] - warp1
        # Adjust remaining integral part
        days_in_cycle = self.count_days_in_cycle()
        integral = integral - flag_over * (max_add + my_ones) - flag_under * (max_sub - days_in_cycle)

        while True:
            flag_over = integral >= days_in_cycle
            flag_neg = integral < my_zeros
            flag_either = np.bitwise_or(flag_over, flag_neg * flag_under)
            self.times[..., 1] = self.times[..., 1] + flag_over - flag_under * flag_neg
            first_day_in_cycle = ma.zeros(self.times.shape[:-1])
            for cal in self._unique_calendars:
                ijs = np.where(self.calendars == cal)
                dayval = cal._Vith_day_in_cycle(self.times[..., 1], self.times[..., 0], my_ones)
                first_day_in_cycle[ijs] = dayval[ijs]
            warp1 = (self.times[..., 2] - first_day_in_cycle) * flag_either
            self.times[..., 2] = self.times[..., 2] - warp1
            warp1 = flag_over * days_in_cycle
            days_in_cycle = self.count_days_in_cycle()
            integral = integral - warp1 + flag_neg * flag_under * days_in_cycle
            if (1 - np.bitwise_or(flag_over, flag_under * flag_neg)).all():
                break

        days_numbers = self.day_number_in_cycle()
        new_day_numbers = days_numbers + integral
        new_day_values = self.ith_day_in_cycle(new_day_numbers)
        self.times[..., 2] = new_day_values

        if fractional.sum() != 0:
            hours_to_add = fractional * 24.0
            self.add_hours(hours_to_add)

    def add_hours(self, increments):
        # split integral and fractional part of the increment
        (fractional, integral) = np.modf(increments)
        if not hasattr(integral, 'size'):
            fractional = ma.ones(self.times.shape[:-1]) * fractional
            integral = ma.ones(self.times.shape[:-1]) * integral

        # increment will overflow hours :
        flag_over = integral >= (24 - self.hour())
        # increment will underflow hours :
        flag_under = integral < -(self.hour())
        # need to add/substract days :
        overflow = np.bitwise_or(flag_over, flag_under)
        if overflow.sum():
            self.add_days(np.floor((integral + self.hour()) / 24.0))
        # add/substract hours
        warp = overflow * (-self.hour() + np.mod(integral + self.hour(), 24))
        self.hour(self.hour() + (1 - overflow) * integral + warp)

        if fractional.sum() != 0:
            minutes_to_add = fractional * 60.0
            self.add_minutes(minutes_to_add)

    def add_minutes(self, increments):
        # split integral and fractional part of the increment
        (fractional, integral) = np.modf(increments)
        if not hasattr(integral, 'size'):
            fractional = ma.ones(self.times.shape[:-1]) * fractional
            integral = ma.ones(self.times.shape[:-1]) * integral

        # increment will overflow minutes :
        flag_over = integral >= (60 - self.minute())
        # increment will underflow minutes :
        flag_under = integral < -(self.minute())
        # need to add/substract hours :
        overflow = np.bitwise_or(flag_over, flag_under)
        if overflow.sum():
            self.add_hours(np.floor((integral + self.minute()) / 60.0))
        # add/substract minutes
        warp = overflow * (-self.minute() + np.mod(integral + self.minute(), 60))
        self.minute(self.minute() + (1 - overflow) * integral + warp)

        if fractional.sum() != 0:
            seconds_to_add = fractional * 60.0
            self.add_seconds(seconds_to_add)

    def add_seconds(self, increments):
        new_seconds = self.second() + increments
        # split integral and fractional part of the increment
        (fractional, integral) = np.modf(increments)
        if not hasattr(integral, 'size'):
            fractional = ma.ones(self.times.shape[:-1]) * fractional
            integral = ma.ones(self.times.shape[:-1]) * integral

        # increment will overflow seconds :
        flag_over = new_seconds >= 60
        # increment will underflow seconds :
        flag_under = new_seconds < 0
        # need to add/substract minutes :
        overflow = np.bitwise_or(flag_over, flag_under)
        if overflow.sum():
            self.add_minutes(np.floor(new_seconds / 60.0))
        # add/substract seconds
        t1 = flag_over * (-new_seconds + np.mod(new_seconds, 60))
        t2 = flag_under * (-new_seconds + np.mod(new_seconds, 60))
        new_seconds = new_seconds + t1 + t2
        flag_threshold_under = new_seconds < threshold
        flag_threshold_over = new_seconds > 60.0 - threshold
        ijs = np.where(np.bitwise_or(flag_threshold_under, flag_threshold_over))
        new_seconds[ijs] = 0
        self.add_minutes(flag_threshold_over)
        (fractional, integral) = np.modf(new_seconds)
        if fractional.sum():
            self.times = ma.array(self.times, dtype=myfloat)
            self.second(new_seconds)
        else:
            new_seconds = ma.array(new_seconds, dtype=myint)
            self.second(new_seconds)

    def __add__(self, multideltat):
        new_mdate = MultiDate(self.times, self.calendars)
        new_mdate.add_years(multideltat.year())
        new_mdate.add_cycles(multideltat.cycle())
        new_mdate.add_days(multideltat.day())
        new_mdate.add_hours(multideltat.hour())
        new_mdate.add_minutes(multideltat.minute())
        new_mdate.add_seconds(multideltat.second())
        return new_mdate

    def __sub__(self, multideltat):
        return self + (multideltat * -1)

    def min(self):
        if len(self._unique_calendars) != 1:
            raise NotImplementedError("Different calendars.")
        min_time = [self.year().min()]
        indices = np.nonzero(self.year() == min_time[0])
        remains = self[indices]
        for j in range(1, 6):
            min_time.append(remains.times[..., j].min())
            indices = np.nonzero(remains.times[..., j] == min_time[j])
            remains = remains[indices]
        return Date(min_time, self._unique_calendars[0])

    def max(self):
        if len(self._unique_calendars) != 1:
            raise NotImplementedError("Different calendars.")
        max_time = [self.year().max()]
        indices = np.nonzero(self.year() == max_time[0])
        remains = self[indices]
        for j in range(1, 6):
            max_time.append(remains.times[..., j].max())
            indices = np.nonzero(remains.times[..., j] == max_time[j])
            remains = remains[indices]
        return Date(max_time, self._unique_calendars[0])

    def buffer(self, deltat):
        raise NotImplementedError()

    def boundary(self):
        return None

    def centroid(self):
        raise NotImplementedError()

    def convex_hull(self):
        initial_date = self.min()
        final_date = self.max()
        if initial_date == final_date:
            return initial_date
        else:
            return explicit_period(initial_date, self.max(),
                                   initial_date.calendar)

    def envelope(self):
        return self.convex_hull()

    def difference(self, other):
        raise NotImplementedError()

    def intersection(self, other, as_indices=False):
        if isinstance(other, Period):
            if other.left_open:
                flag_initial = self > other.initial_date()
            else:
                flag_initial = self >= other.initial_date()
            if other.right_open:
                flag_final = self < other.final_date()
            else:
                flag_final = self <= other.final_date()
            flag_within = np.bitwise_and(flag_initial, flag_final)
            if as_indices:
                return np.where(flag_within)
            # self < other.final_date()
            # other.initial_date()
            # other.final_date()
            ##initial_indice = None
            ##final_indice = None
            # list_indices = []
            # for i in range(self.times.shape[0]):
            # if self[i].within(other):
            # list_indices.append(i)
            ##if initial_indice is None:
            ##initial_indice = i
            ##final_indice = i
            ##else:
            ##final_indice = i
            # if as_indices:
            ##return initial_indice,final_indice+1
            # return (np.array(list_indices),)
            # else:
            ##return self[initial_indice:final_indice+1]
            # self[(np.array(list_indices),)]
        else:
            raise NotImplementedError()

    def symmetric_difference(self, other):
        raise NotImplementedError()

    def union(self, other):
        raise NotImplementedError()

    def contains(self, other):
        raise NotImplementedError()

    def within(self, other):
        if other.contains(self):
            return True
        else:
            return False

    def intersects(self, other):
        raise NotImplementedError()

    def disjoint(self, other):
        if self.intersects(other):
            return False
        else:
            return True

    def equals(self, other):
        raise NotImplementedError()

    def touches(self, other):
        raise NotImplementedError()

    def distance(self, other):
        raise NotImplementedError()

    def bounds(self):
        raise NotImplementedError()

    def length(self):
        raise NotImplementedError()


#
class Date(MultiDate):
    """Date representation."""

    def __init__(self, time, calendar=CalGregorian):
        MultiDate.__init__(self, time, calendars=calendar)
        self.calendar = self.calendars[0]

    def __str__(self):
        date_string = "%s" % (str(self.times[0, 0]).zfill(4),)
        time_vector_length = len(self.times)
        if ~ma.getmask(self.times[0, 1]):
            date_string += "-%s" % (str(self.times[0, 1]).zfill(2),)
        if ~ma.getmask(self.times[0, 2]):
            date_string += "-%s" % (str(self.times[0, 2]).zfill(2),)
        if ~ma.getmask(self.times[0, 3]):
            date_string += "T%s" % (str(self.times[0, 3]).zfill(2),)
        if ~ma.getmask(self.times[0, 4]):
            date_string += ":%s" % (str(self.times[0, 4]).zfill(2),)
        if ~ma.getmask(self.times[0, 5]):
            date_string += ":%s" % (str(self.times[0, 5]).zfill(2),)
        if ~ma.getmask(self.times[0, 3]):
            date_string += 'Z'
        return date_string

    def __gt_obsolete_(self, other):
        if self.calendars[0] == other.calendars[0]:
            gt = (self.times[0] > other.times[0])
            gt.mask = ma.getmaskarray(gt)
            gt.mask[ma.where(self.times[0] == other.times[0])] = True
            gt_unmasked = gt[~gt.mask]
            if len(gt_unmasked) == 0:
                if self.times[0].count() == other.times[0].count():
                    return False
                else:
                    raise TimelyError("Ambiguous operations.")
            else:
                if gt_unmasked[0]:
                    return True
                else:
                    return False
        else:
            raise NotImplementedError("Different calendars.")

    def __ge_obsolete_(self, other):
        if self.calendars[0] == other.calendars[0]:
            gt = (self.times[0] > other.times[0])
            gt.mask = ma.getmaskarray(gt)
            gt.mask[ma.where(self.times[0] == other.times[0])] = True
            gt_unmasked = gt[~gt.mask]
            if len(gt_unmasked) == 0:
                if self.times[0].count() == other.times[0].count():
                    return True
                else:
                    raise TimelyError("Ambiguous operations.")
            else:
                if gt_unmasked[0]:
                    return True
                else:
                    return False
        else:
            raise NotImplementedError("Different calendars.")

    def __lt_obsolete_(self, other):
        if self.calendars[0] == other.calendars[0]:
            lt = (self.times[0] < other.times[0])
            lt.mask = ma.getmaskarray(lt)
            lt.mask[ma.where(self.times[0] == other.times[0])] = True
            lt_unmasked = lt[~lt.mask]
            if len(lt_unmasked) == 0:
                if self.times[0].count() == other.times[0].count():
                    return False
                else:
                    raise TimelyError("Ambiguous operations.")
            else:
                if lt_unmasked[0]:
                    return True
                else:
                    return False
        else:
            raise NotImplementedError("Different calendars.")

    def __le_obsolete_(self, other):
        if self.calendars[0] == other.calendars[0]:
            lt = (self.times[0] < other.times[0])
            lt.mask = ma.getmaskarray(lt)
            lt.mask[ma.where(self.times[0] == other.times[0])] = True
            lt_unmasked = lt[~lt.mask]
            if len(lt_unmasked) == 0:
                if self.times[0].count() == other.times[0].count():
                    return True
                else:
                    raise TimelyError("Ambiguous operations.")
            else:
                if lt_unmasked[0]:
                    return True
                else:
                    return False
        else:
            raise NotImplementedError("Different calendars.")


#
class TimeSeries(MultiDate):
    def timestep(self):
        if self.times.shape[0] < 2:
            raise TimelyError("Need more than one date to compute timestep.")
        # get first timesteps
        period = explicit_period(self[0], self[1])
        counts = []
        flags_uniform = []
        for j in range(0, 6):
            if ~period.times[0, :].mask[j]:
                counts.append(period.len(j))
                if (j in [0, 1, 2]) and (counts[j] == 1):
                    flags_uniform.append(False)
                else:
                    flags_uniform.append(True)
        # check that every subsequent timesteps are the same
        for i in range(2, self.times.shape[0]):
            period = explicit_period(self[0], self[i])
            for j in range(0, 6):
                if ~period.times[0, :].mask[j] and flags_uniform[j]:
                    if j in [0, 1, 2]:
                        this_count = counts[j] - 1
                        this_timestep = period.len(j) - 1
                    else:
                        this_count = counts[j]
                        this_timestep = period.len(j)
                    if i * this_count != this_timestep:
                        flags_uniform[j] = False
            if not (True in flags_uniform):
                raise TimelyError("Could not calculate a uniform timestep.")
        if len(flags_uniform) > 5 and flags_uniform[5]:
            deltat = DeltaT([0, 0, 0, 0, 0, counts[5]])
            deltat.seconds_to_minutes()
            deltat.minutes_to_hours()
            deltat.hours_to_days()
            return deltat
        elif len(flags_uniform) > 4 and flags_uniform[4]:
            deltat = DeltaT([0, 0, 0, 0, counts[4]])
            deltat.minutes_to_hours()
            deltat.hours_to_days()
            return deltat
        elif len(flags_uniform) > 3 and flags_uniform[3]:
            deltat = DeltaT([0, 0, 0, counts[3]])
            deltat.hours_to_days()
            return deltat
        elif len(flags_uniform) > 2 and flags_uniform[2]:
            return DeltaT([0, 0, counts[2] - 1])
        elif len(flags_uniform) > 1 and flags_uniform[1]:
            return DeltaT([0, counts[1] - 1])
        elif flags_uniform[0]:
            return DeltaT([counts[0] - 1])


#
class MultiPeriod(MultiDate):

    def __init__(self, times, left_open=False, right_open=False,
                 calendars=CalGregorian):
        MultiDate.__init__(self, times, calendars)
        if not hasattr(left_open, '__iter__'):
            self.left_open = ma.empty(self.times.shape[:-2],
                                      dtype=type(False))
            self.left_open[...] = left_open
        else:
            self.left_open = left_open
        if not hasattr(right_open, '__iter__'):
            self.right_open = ma.empty(self.times.shape[:-2],
                                       dtype=type(False))
            self.right_open[...] = right_open
        else:
            self.right_open = right_open
        self.shape = self.times.shape[:-2]

    def __getitem__(self, item):
        if isinstance(item, tuple):
            new_slices = list(item)
            new_slices.append(slice(None, None, None))
            cal_slices = tuple(new_slices)
            new_slices.append(slice(None, None, None))
            new_slices = tuple(new_slices)
            subset_times = self.times[new_slices]
            if subset_times.shape == (2, 6):
                return Period(subset_times, self.left_open[item],
                              self.right_open[item], self.calendars[cal_slices])
            else:
                return MultiPeriod(subset_times, self.left_open[item],
                                   self.right_open[item],
                                   self.calendars[cal_slices])
        elif isinstance(item, slice):
            subset_times = self.times[item, :, :]
            if subset_times.shape == (2, 6):
                return Period(subset_times, self.left_open[item],
                              self.right_open[item], self.calendars[item, :])
            else:
                return MultiPeriod(subset_times, self.left_open[item],
                                   self.right_open[item], self.calendars[item, :])
        else:
            return Period(self.times[item, :, :], self.left_open[item],
                          self.right_open[item], self.calendars[item, :])

    def count_years(self):
        if not self.decimals:
            # Check for left_open condition
            days_in_cycle = self.count_days_in_cycle()
            last_cycle_in_year = self.count_cycles_in_year()
            last_day_in_cycle = self.ith_day_in_cycle(days_in_cycle)
            c1 = self.times[..., 0, 1] == last_cycle_in_year[..., 0]
            c2 = self.times[..., 0, 2] == last_day_in_cycle[..., 0]
            c3 = self.times[..., 0, 3] == 23
            c4 = self.times[..., 0, 4] == 59
            c5 = self.times[..., 0, 5] == 59
            ct = np.bitwise_and(c1, c2)
            ct = np.bitwise_and(c3, ct)
            ct = np.bitwise_and(c4, ct)
            ct = np.bitwise_and(c5, ct)
            flag_left_open = self.left_open * ct
            # Check for right_open condition
            first_day_in_cycle = self.ith_day_in_cycle(1)
            c1 = self.times[..., 1, 1] == 1
            c2 = self.times[..., 1, 2] == first_day_in_cycle[..., 1]
            c3 = self.times[..., 1, 3] == 0
            c4 = self.times[..., 1, 4] == 0
            c5 = self.times[..., 1, 5] == 0
            ct = np.bitwise_and(c1, c2)
            ct = np.bitwise_and(c3, ct)
            ct = np.bitwise_and(c4, ct)
            ct = np.bitwise_and(c5, ct)
            flag_right_open = self.right_open * ct
        # Calculate number of years
        warp = ma.ones(self.shape, dtype=myint)
        num_of_years = self.times[..., 1, 0] - self.times[..., 0, 0] + warp
        return num_of_years - flag_left_open - flag_right_open

    def count_cycles(self):
        if not self.decimals:
            # Check for left_open condition
            days_in_cycle = self.count_days_in_cycle()
            last_day_in_cycle = self.ith_day_in_cycle(days_in_cycle)
            c2 = self.times[..., 0, 2] == last_day_in_cycle[..., 0]
            c3 = self.times[..., 0, 3] == 23
            c4 = self.times[..., 0, 4] == 59
            c5 = self.times[..., 0, 5] == 59
            ct = np.bitwise_and(c2, c3)
            ct = np.bitwise_and(c4, ct)
            ct = np.bitwise_and(c5, ct)
            flag_left_open = self.left_open * ct
            # Check for right_open condition
            first_day_in_cycle = self.ith_day_in_cycle(1)
            c2 = self.times[..., 1, 2] == first_day_in_cycle[..., 1]
            c3 = self.times[..., 1, 3] == 0
            c4 = self.times[..., 1, 4] == 0
            c5 = self.times[..., 1, 5] == 0
            ct = np.bitwise_and(c2, c3)
            ct = np.bitwise_and(c4, ct)
            ct = np.bitwise_and(c5, ct)
            flag_right_open = self.right_open * ct
        # Calculate number of cycles
        cycle_count = ma.zeros(self.shape, dtype=myint)
        for y in range(self.times[..., 0, 0].min(), self.times[..., 1, 0].max() + 1):
            flag_initial_year = (y == self.times[..., 0, 0])
            flag_final_year = (y == self.times[..., 1, 0])
            warp1 = (y >= self.times[..., 0, 0])
            warp2 = (y <= self.times[..., 1, 0])
            flag_between = np.bitwise_and(warp1, warp2)
            cycles_in_year = ma.zeros(self.times.shape[:-1], dtype=myint)
            for cal in self._unique_calendars:
                ijs = np.where(self.calendars == cal)
                cycles_in_year[ijs] = cal.count_cycles_in_year(y)
            t1 = flag_initial_year * (self.times[..., 0, 1] - ma.ones(self.shape))
            t2 = flag_between * cycles_in_year[..., 0]
            t3 = flag_final_year * (cycles_in_year[..., 0] - self.times[..., 1, 1])
            cycle_count += -t1 + t2 - t3
        return cycle_count - flag_left_open - flag_right_open

    def count_days(self):
        if not self.decimals:
            # Check for left_open condition
            c3 = self.times[..., 0, 3] == 23
            c4 = self.times[..., 0, 4] == 59
            c5 = self.times[..., 0, 5] == 59
            ct = np.bitwise_and(c3, c4)
            ct = np.bitwise_and(c5, ct)
            flag_left_open = self.left_open * ct
            # Check for right_open condition
            c3 = self.times[..., 1, 3] == 0
            c4 = self.times[..., 1, 4] == 0
            c5 = self.times[..., 1, 5] == 0
            ct = np.bitwise_and(c3, c4)
            ct = np.bitwise_and(c5, ct)
            flag_right_open = self.right_open * ct
        day_count = ma.zeros(self.shape, dtype=myint)
        for y in range(self.times[..., 0, 0].min(), self.times[..., 1, 0].max() + 1):
            flag_initial_year = (y == self.times[..., 0, 0])
            flag_final_year = (y == self.times[..., 1, 0])
            warp1 = (y >= self.times[..., 0, 0])
            warp2 = (y <= self.times[..., 1, 0])
            flag_between = np.bitwise_and(warp1, warp2)
            if flag_between.sum() != 0:
                # deal with in-between years
                days_in_year = ma.zeros(self.times.shape[:-1], dtype=myint)
                for cal in self._unique_calendars:
                    ijs = np.where(self.calendars == cal)
                    days_in_year[ijs] = cal.count_days_in_year(y)
                day_count += flag_between * days_in_year[..., 0]
            if flag_initial_year.sum() != 0:
                # deal with initial years
                cycles_in_year = self.count_cycles_in_year()[..., 0]
                warp = ma.array(self.times[..., 0, 1], mask=~flag_initial_year)
                for cc in range(1, warp.max() + 1):
                    flag_initial_cycle = (cc == self.times[..., 0, 1])
                    flag_before = (cc < self.times[..., 0, 1])
                    days_in_cycle = ma.zeros(self.times.shape[:-1], dtype=myint)
                    for cal in self._unique_calendars:
                        ijs = np.where(self.calendars == cal)
                        days_in_cycle[ijs] = cal.count_days_in_cycle(cc, y)
                    day_num_in_cycle = self.day_number_in_cycle()
                    t1 = flag_initial_cycle * (day_num_in_cycle[..., 0] - ma.ones(self.shape))
                    t2 = flag_before * days_in_cycle[..., 0]
                    day_count -= flag_initial_year * (t1 + t2)
            if flag_final_year.sum() != 0:
                # deal with final years
                cycles_in_year = self.count_cycles_in_year()[..., 1]
                warp1 = ma.array(self.times[..., 1, 1], mask=~flag_final_year)
                warp2 = ma.array(cycles_in_year, mask=~flag_final_year)
                for cc in range(warp1.min(), warp2.max() + 1):
                    flag_final_cycle = (cc == self.times[..., 1, 1])
                    flag_after = (cc > self.times[..., 1, 1])
                    days_in_cycle = ma.zeros(self.times.shape[:-1], dtype=myint)
                    for cal in self._unique_calendars:
                        ijs = np.where(self.calendars == cal)
                        days_in_cycle[ijs] = cal.count_days_in_cycle(cc, y)
                    day_num_in_cycle = self.day_number_in_cycle()
                    warp = days_in_cycle[..., 1] - day_num_in_cycle[..., 1]
                    t1 = flag_after * days_in_cycle[..., 1]
                    t2 = flag_final_cycle * (warp)
                    day_count -= flag_final_year * (t1 + t2)
        return day_count - flag_left_open - flag_right_open

    def count_hours(self):
        if not self.decimals:
            # Check for left_open condition
            c3 = self.times[..., 0, 3] == 23
            c4 = self.times[..., 0, 4] == 59
            c5 = self.times[..., 0, 5] == 59
            ct = np.bitwise_and(c4, c5)
            flag_left_open_hour = self.left_open * ct
            ct = np.bitwise_and(c3, c4)
            ct = np.bitwise_and(c5, ct)
            flag_left_open = self.left_open * ct
            # Check for right_open condition
            c3 = self.times[..., 1, 3] == 0
            c4 = self.times[..., 1, 4] == 0
            c5 = self.times[..., 1, 5] == 0
            ct = np.bitwise_and(c4, c5)
            flag_right_open_hour = self.right_open * ct
            ct = np.bitwise_and(c3, c4)
            ct = np.bitwise_and(c5, ct)
            flag_right_open = self.right_open * ct
        num_of_hours = self.count_days() * 24
        t1 = -(self.times[..., 0, 3] + flag_left_open_hour) * (~flag_left_open)
        t2 = -(23 - self.times[..., 1, 3] + flag_right_open_hour) * (~flag_right_open)
        return num_of_hours + t1 + t2

    def count_minutes(self):
        if not self.decimals:
            # Check for left_open condition
            c4 = self.times[..., 0, 4] == 59
            c5 = self.times[..., 0, 5] == 59
            ct = np.bitwise_and(c4, c5)
            flag_left_open_hour = self.left_open * ct
            flag_left_open = self.left_open * c5
            # Check for right_open condition
            c4 = self.times[..., 1, 4] == 0
            c5 = self.times[..., 1, 5] == 0
            ct = np.bitwise_and(c4, c5)
            flag_right_open_hour = self.right_open * ct
            flag_right_open = self.right_open * c5
        num_of_minutes = self.count_hours() * 60
        t1 = -(self.times[..., 0, 4] + flag_left_open) * (~flag_left_open_hour)
        t2 = -(59 - self.times[..., 1, 4] + flag_right_open) * (~flag_right_open_hour)
        return num_of_minutes + t1 + t2

    def count_seconds(self):
        if not self.decimals:
            # Check for left_open condition
            c5 = self.times[..., 0, 5] == 59
            flag_left_open = self.left_open * c5
            # Check for right_open condition
            c5 = self.times[..., 1, 5] == 0
            flag_right_open = self.right_open * c5
        num_of_seconds = self.count_minutes() * 60
        t1 = -(self.times[..., 0, 5] + self.left_open) * (~flag_left_open)
        t2 = -(59 - self.times[..., 1, 5] + self.right_open) * (~flag_right_open)
        return num_of_seconds + t1 + t2

    def len(self, units='seconds'):
        if units == 'seconds' or units == 5:
            return self.count_seconds()
        elif units == 'minutes' or units == 4:
            return self.count_seconds() / 60.0
        elif units == 'hours' or units == 3:
            return self.count_seconds() / 360.0
        elif units == 'days' or units == 2:
            return self.count_seconds() / 86400.0
        elif units in ['cycles', 'months'] or units == 1:
            days_in_cycle = self.count_days_in_cycle()
            return self.count_seconds() / (86400.0 * days_in_cycle[..., 0])
        elif units == 'years' or units == 0:
            days_in_year = self.count_days_in_year()
            return self.count_seconds() / (86400.0 * days_in_year[..., 0])

    def buffer(self, deltat):
        raise NotImplementedError()

    def boundary(self):
        raise NotImplementedError()

    def centroid(self):
        raise NotImplementedError()

    def convex_hull(self):
        raise NotImplementedError()

    def envelope(self):
        return self.convex_hull()

    def difference(self, other):
        raise NotImplementedError()

    def intersection(self, other):
        raise NotImplementedError()

    def symmetric_difference(self, other):
        raise NotImplementedError()

    def union(self, other):
        raise NotImplementedError()

    def contains(self, other):
        raise NotImplementedError()

    def within(self, other):
        if other.contains(self):
            return True
        else:
            return False

    def intersects(self, other):
        raise NotImplementedError()

    def disjoint(self, other):
        if self.intersects(other):
            return False
        else:
            return True

    def equals(self, other):
        raise NotImplementedError()

    def touches(self, other):
        raise NotImplementedError()

    def distance(self, other):
        raise NotImplementedError()

    def bounds(self):
        raise NotImplementedError()

    def length(self):
        raise NotImplementedError()


#
class Period(MultiPeriod):
    """Period with its calendar reference."""

    def __init__(self, times, left_open=False, right_open=False,
                 calendar=CalGregorian):
        """Initialize period.

        Parameters
        ----------
        times : matrix
        left_open : bool
            A False value means the end point is included.
        right_open : bool
            A False value means the end point is included.
        calendar : Calendar

        Notes
        -----
        Currently, the two dates must have the same calendar,
        and be of the same shape.???
        It is strongly suggested to make use of the left_open and right_open
        attributes to avoid ambiguity across calendars.

        """

        MultiPeriod.__init__(self, times, left_open, right_open, calendar)
        initial_date = Date(self.times[0, :], self.calendars[0])
        final_date = Date(self.times[1, :], self.calendars[0])
        if (initial_date >= final_date):
            raise TimelyError("Initial date must precede final date.")

    def initial_date(self, set_value=None):
        return Date(self.times[0, :], self.calendars[0])

    def final_date(self, set_value=None):
        return Date(self.times[1, :], self.calendars[0])

    def initial_year(self, set_value=None):
        if ma.getmask(self.times[0, 0]):
            raise TimelyError("Time vector does not have a year element.")
        return self.times[0, 0]

    def initial_cycle(self, set_value=None):
        if ma.getmask(self.times[0, 1]):
            raise TimelyError("Time vector does not have a cycle element.")
        return self.times[0, 1]

    def initial_month(self, set_value=None):
        return self.initial_cycle()

    def initial_day(self, set_value=None):
        if ma.getmask(self.times[0, 2]):
            raise TimelyError("Time vector does not have a day element.")
        return self.times[0, 2]

    def initial_hour(self, set_value=None):
        if ma.getmask(self.times[0, 3]):
            raise TimelyError("Time vector does not have a hour element.")
        return self.times[0, 3]

    def initial_minute(self, set_value=None):
        if ma.getmask(self.times[0, 4]):
            raise TimelyError("Time vector does not have a minute element.")
        return self.times[0, 4]

    def initial_second(self, set_value=None):
        if ma.getmask(self.times[0, 5]):
            raise TimelyError("Time vector does not have a second element.")
        return self.times[0, 5]

    def final_year(self, set_value=None):
        if ma.getmask(self.times[1, 0]):
            raise TimelyError("Time vector does not have a year element.")
        return self.times[1, 0]

    def final_cycle(self, set_value=None):
        if ma.getmask(self.times[1, 1]):
            raise TimelyError("Time vector does not have a cycle element.")
        return self.times[1, 1]

    def final_month(self, set_value=None):
        return self.final_cycle()

    def final_day(self, set_value=None):
        if ma.getmask(self.times[1, 2]):
            raise TimelyError("Time vector does not have a day element.")
        return self.times[1, 2]

    def final_hour(self, set_value=None):
        if ma.getmask(self.times[1, 3]):
            raise TimelyError("Time vector does not have a hour element.")
        return self.times[1, 3]

    def final_minute(self, set_value=None):
        if ma.getmask(self.times[1, 4]):
            raise TimelyError("Time vector does not have a minute element.")
        return self.times[1, 4]

    def final_second(self, set_value=None):
        if ma.getmask(self.times[1, 5]):
            raise TimelyError("Time vector does not have a second element.")
        return self.times[1, 5]

    def __str__(self):
        return "%s to %s" % (str(self.initial_date()),
                             str(self.final_date()))

    def str_y(self):
        """String expression of period using only years."""

        return "%s to %s" % (str(self.initial_date.year()),
                             str(self.final_date.year()))

    def str_ym(self):
        """String expression of period using only years and months."""

        return "%s-%s to %s-%s" % (str(self.initial_date.year()),
                                   str(self.initial_date.cycle()),
                                   str(self.final_date.year()),
                                   str(self.final_date.cycle()))

    def __eq__(self, other):
        if self.initial_date() == other.initial_date() and \
                self.final_date() == other.final_date():
            return True
        else:
            return False

    def __ne__(self, other):
        if self == other:
            return False
        else:
            return True

    def regular_sample(self, deltat, buffer=None, new_calendar=None):
        """Regular interval sample of the period.

        Parameters
        ----------
        deltat : DeltaT
        buffer : DeltaT
        new_calendar : Calendar


        Returns
        -------
        out : TimeSeries

        Notes
        -----
        The buffer is only applied on the initial date.

        """

        if buffer:
            initial_date = self.initial_date() + buffer
        else:
            initial_date = self.initial_date()
        final_date = self.final_date()
        if new_calendar is not None:
            initial_date.calendars = np.array([new_calendar])
            final_date.calendars = np.array([new_calendar])
        if self.left_open and (initial_date == self.initial_date()):
            initial_date = initial_date + deltat
        if self.right_open:
            if initial_date >= final_date:
                return None
        else:
            if initial_date > final_date:
                return None
        multidate_times = ma.empty([1, 6])
        multidate_times[0, :] = initial_date.times
        next_date = initial_date + deltat
        while next_date <= final_date:
            if self.right_open and (next_date == final_date):
                break
            multidate_times = ma.vstack([multidate_times, next_date.times[0, :]])
            next_date = next_date + deltat
        if new_calendar is not None:
            return TimeSeries(multidate_times.data, new_calendar)
        else:
            return TimeSeries(multidate_times.data, self.calendars[0])

    def regular_division(self, deltat, buffer, length, new_calendar=None):
        """Regular interval sample of the period.

        Parameters
        ----------
        deltat : DeltaT
        buffer : DeltaT
        length : DeltaT
            division length
        new_calendar : Calendar


        Returns
        -------
        out : TimeSeries

        Notes
        -----
        The buffer is only applied on the initial date.

        """

        if buffer:
            initial_date = self.initial_date() + buffer
        else:
            initial_date = self.initial_date()
        if self.left_open and (initial_date == self.initial_date()):
            initial_date = initial_date + deltat
        if self.right_open:
            if initial_date >= self.final_date():
                return None
        else:
            if initial_date > self.final_date():
                return None
        multiperiod_times = ma.empty([1, 2, 6])
        multiperiod_times[0, 0, :] = initial_date.time
        # next_date = initial_date + deltat
        next_date = initial_date + deltat
        end_date = initial_date + length
        multiperiod_times[0, 1, :] = end_date.time
        final_date = self.final_date()
        if new_calendar is not None:
            final_date.calendar = new_calendar
        while next_date <= final_date:
            if self.right_open and (next_date == final_date):
                break
            next_period = ma.empty([2, 6])
            next_period[0, :] = next_date.time
            end_date = next_date + length
            next_period[1, :] = end_date.time
            multiperiod_times = ma.vstack([multiperiod_times, next_period])
            next_date = next_date + deltat
        return TimeWindows(multiperiod_times.data, self.calendar)

    # def count_years(self):
    # """Count the number of years covered by the period.

    # Returns
    # -------
    # out : int
    # number of years.

    # """

    # return (self.final_year() - self.initial_year() + 1)

    # def get_y(self):
    # """Get the years covered by the period.

    # Returns
    # -------
    # out : list of int
    # ordered list of year(s) that appear in the period.

    # """

    # warp = [int(self.initial_year()),int(self.final_year()+1)]
    # return range(*warp)

    # def get_ym(self):
    # """Get the years and cycles covered by the period.

    # Returns
    # -------
    # out : list of tuples
    # ordered list of (year,cycle) tuples that appear in the period.

    # """

    # if self.calendar.year_cycles is None:
    # raise TimelyError("Year cycles not defined.")
    # year_cycles = []
    # if self.initial_time.mask[1]:
    # initial_cycle = 1
    # else:
    # initial_cycle = self.initial_cycle()
    # for yyyy in self.get_y():
    # if (yyyy == self.final_year()) and (~self.initial_time.mask[1]):
    # final_cycle = self.final_cycle()
    # else:
    # final_cycle = len(self.calendar.year_cycles(yyyy))
    # for mm in range(int(initial_cycle),int(final_cycle)+1):
    # year_cycles.append((yyyy,mm))
    # initial_cycle = 1
    # return year_cycles

    # def get_ymd(self):
    # """Get the years, cycles and days covered by the period.

    # Returns
    # -------
    # out : list of tuples
    # ordered list of (year,cycle,day) tuples that appear in the period.

    # """

    # if self.calendar.year_cycles is None:
    # raise TimelyError("Year cycles not defined.")
    # if self.calendar.days_in_cycle is None:
    # raise TimelyError("Days in cycle not defined.")
    # if self.initial_time.mask[1]:
    # initial_yyyymm = (self.initial_year(),1)
    # else:
    # warp = (self.initial_year(),self.initial_cycle())
    # initial_yyyymm = warp
    # if self.initial_time.mask[1]:
    # calendar = self.calendar
    # warp = len(calendar.year_cycles(self.final_year()))
    # final_yyyymm = (self.final_year(),warp)
    # else:
    # final_yyyymm = (self.final_year(),self.final_cycle())
    # year_cycle_days = []
    # for yyyymm in self.get_ym():
    # if (yyyymm == initial_yyyymm) and (~self.initial_time.mask[2]):
    # initial_day = self.initial_day()
    # else:
    # initial_day = None
    # if (yyyymm == final_yyyymm) and (~self.initial_time.mask[2]):
    # final_day = self.final_day()
    # else:
    # final_day = None
    # dds = self.calendar.days_in_cycle(yyyymm[1],yyyymm[0])
    # for dd in dds:
    # if (initial_day is not None) and (dd < initial_day):
    # continue
    # if (final_day is not None) and (dd > final_day):
    # continue
    # year_cycle_days.append((yyyymm[0],yyyymm[1],dd))
    # return year_cycle_days

    # def count_cycles(self):
    # """Count the number of cycles covered by the period.

    # Returns
    # -------
    # out : int
    # number of cycles.

    # """

    # return len(self.get_ym())

    # def count_days(self):
    # """Count the number of days covered by the period.

    # Returns
    # -------
    # out : int
    # number of days.

    # """

    # if (self.initial_time.mask[2]) or (self.final_time.mask[2]):
    # raise TimelyError("Dates in period have no days.")
    # calendar = self.calendar
    # days_in_period = 0
    # current_days = calendar.days_in_cycle(self.initial_cycle(),
    # self.initial_year())
    # day1 = current_days.index(int(self.initial_day())) + 1
    # if self.initial_year() == self.final_year():
    # if self.initial_cycle() == self.final_cycle():
    # day2 = current_days.index(int(self.final_day())) + 1
    # return (day2 - day1 + 1)
    # final_cycle = self.final_cycle()-1
    # else:
    # final_cycle = len(calendar.year_cycles(self.initial_year()))
    # for i in range(int(self.initial_year())+1,int(self.final_year())):
    # days_in_period += calendar.count_days_in_year(i)
    # for i in range(1,int(self.final_cycle())):
    # days_in_period += len(calendar.days_in_cycle(i,
    # self.final_year()))
    # for i in range(int(self.initial_cycle())+1,int(final_cycle)+1):
    # days_in_period += len(calendar.days_in_cycle(i,self.initial_year()))
    # days_in_period += len(current_days) - day1 + 1
    # current_days = calendar.days_in_cycle(self.final_cycle(),
    # self.final_year())
    # day2 = current_days.index(int(self.final_day())) + 1
    # days_in_period += day2
    # return days_in_period

    # def count_hours(self):
    # """Count the hours covered by the period.

    # Returns
    # -------
    # out : int or float
    # hours.

    # """

    # hours_diff = self.final_hour() - self.initial_hour()
    # return ((self.count_days()-1)*24 + hours_diff)

    # def count_minutes(self):
    # """Count the minutes covered by the period.

    # Returns
    # -------
    # out : int or float
    # minutes.

    # """

    # minutes_diff = self.final_minute() - self.initial_minute()
    # return (self.count_hours()*60 + minutes_diff)

    # def count_seconds(self):
    # """Count the seconds covered by the period.

    # Returns
    # -------
    # out : int or float
    # seconds.

    # """

    # seconds_diff = self.final_second() - self.initial_second()
    # return (self.count_minutes()*60 + seconds_diff)

    ## to be replaced by length method
    # def len(self, time_component):
    # """Length along the given time_component.

    # Parameters
    # ----------
    # time_component : int
    # indice determining which count_* function will be used.
    # (e.g. time_component=2 will call count_days())

    # Returns
    # -------
    # out - int or float
    # length along the chosen component.

    # """

    # if time_component == 0:
    # return self.count_years()
    # elif time_component == 1:
    # return self.count_cycles()
    # elif time_component == 2:
    # return self.count_days()
    # elif time_component == 3:
    # return self.count_hours()
    # elif time_component == 4:
    # return self.count_minutes()
    # elif time_component == 5:
    # return self.count_seconds()

    # to be replaced by intersects?
    def overlap(self, other):
        """Check if two periods overlap.

        Parameters
        ----------
        other : PeriodCalendar object

        Returns
        -------
        out : bool

        Notes
        -----
        Matching end points are considered overlaps too.

        """

        if self.initial_date() > other.final_date() or \
                other.initial_date() > self.final_date():
            return False
        else:
            return True

    # to be replaced by touches?
    def continuous(self, other, deltat=None):
        """Check if two periods are continuous.

        Parameters
        ----------
        other : PeriodCalendar object
            the period that should follow.
        deltat : DeltaT object, optional
            the allowed jump between the two periods
            (default is no jump allowed).

        Returns
        -------
        out : bool

        Notes
        -----
        The periods are continuous if the final date of `self` is the same
        as the initial date of `other` or if there is a provided time
        interval separating the two.

        """

        if self.final_date() == other.initial_date():
            return True
        if deltat is not None:
            if self.final_date() + deltat == other.initial_date():
                return True
        return False

    def buffer(self, deltat):
        raise NotImplementedError()

    def boundary(self):
        raise NotImplementedError()

    def centroid(self):
        raise NotImplementedError()

    def convex_hull(self):
        raise NotImplementedError()

    def envelope(self):
        return self.convex_hull()

    def difference(self, other):
        raise NotImplementedError()

    def intersection(self, other):
        raise NotImplementedError()

    def symmetric_difference(self, other):
        raise NotImplementedError()

    def union(self, other):
        if isinstance(other, Period):
            raise NotImplementedError()
        else:
            raise NotImplementedError()

    def contains(self, other):
        if isinstance(other, Date):
            if self.initial_date() < other and self.final_date() > other:
                return True
            else:
                return False
        else:
            raise NotImplementedError()

    def within(self, other):
        if other.contains(self):
            return True
        else:
            return False

    def intersects(self, other):
        raise NotImplementedError()

    def disjoint(self, other):
        if self.intersects(other):
            return False
        else:
            return True

    def equals(self, other):
        if isinstance(other, Period):
            if self == other:
                return True
            else:
                return False
        else:
            raise NotImplementedError()

    def touches(self, other):
        raise NotImplementedError()

    def distance(self, other):
        raise NotImplementedError()

    def bounds(self):
        raise NotImplementedError()

    def length(self):
        raise NotImplementedError()


#


def deltats2dates(multideltat, reference_date):
    time_array = np.zeros([len(num), 6])
    time_array[:, 0] = reference_date.year()
    time_array[:, 1] = reference_date.cycle()
    time_array[:, 2] = reference_date.day()
    time_array[:, 3] = reference_date.hour()
    time_array[:, 4] = reference_date.minute()
    time_array[:, 5] = reference_date.second()
    yyyy = reference_date.year()
    # while True:
    #    days_in_year = reference_date.calendar.count_days_in_year(yyyy)


def implicit_multidate(times, calendars=CalGregorian):
    (fractional, integral) = np.modf(times)
    mdate = MultiDate(integral, calendars)
    mdeltat = MultiDeltaT(fractional)
    return mdate + mdeltat


def implicit_date(time, calendar=CalGregorian):
    (fractional, integral) = np.modf(time)
    date = Date(integral, calendar)
    deltat = DeltaT(fractional)
    return date + deltat


def explicit_period(initial_date, final_date, left_open=False, right_open=False):
    """Return a Period instance based on an initial and final Date instance.

    Parameters
    ----------
    initial_date : Date
    final_date : Date
    left_open : bool
    right_open : bool

    Returns
    -------
    out : Period

    """

    if initial_date.calendars[0] != final_date.calendars[0]:
        msg = "The two dates defining the period must have the same calendar."
        raise TimelyError(msg)
    period_matrix = ma.empty([2, 6])
    period_matrix[0, :] = initial_date.times[0, :]
    period_matrix[1, :] = final_date.times[0, :]
    return Period(period_matrix, left_open, right_open, initial_date.calendars[0])


def implicit_period(time, calendar=CalGregorian):
    """Return a Period instance using a partial time representation.

    Parameters
    ----------
    time : ?
    calendar : Calendar

    Returns
    -------
    out : Period

    Examples?
    -----
    [1961] would return a period of [1961,1962[

    """

    validate_time = _Time(time)
    date1 = Date(validate_time.times, calendar)
    interval = ma.zeros([6])
    if ma.getmaskarray(validate_time.times[0]).sum() == 6:
        resolution = 0
    else:
        warp = ~ma.getmaskarray(validate_time.times[0])
        resolution = np.nonzero(warp)[0][-1] + 1
    interval[resolution - 1] = 1
    date2 = date1 + DeltaT(interval)
    period_matrix = ma.empty([2, 6])
    period_matrix[0, :] = _conversion_to_ma(time)
    period_matrix[1, :] = date2.times[:]
    return Period(period_matrix, False, True, calendar)
