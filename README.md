# pycfs

## Usage

- Go to https://rda.ucar.edu/ and login
- Navigate to NCEP Climate Forecast System Reanalysis
- Select either CFSR or CFSv2, and the time frequency of the dataset
- Go to Data Access > Web File Listing > Faceted Browse
- Select the variable(s) to download
- Select the vertical level and grid if applicable, click Update the List
- With Range selection turned on, select all the files
- Create a Unix script using Python, copy the content to disk
- Execute as: python {name_of_the_script}.py {rda_password}

- Modify the parameters in cfsr_conversion_template.py
- Start ipyparallel cluster: ipcluster start -n 10
- Launch the conversion script: python cfsr_conversion_template.py

Default variable names and standard names are in cfsr_defaults.py.

## Warnings

It appears that starting with pygrib 1.9.8, the order of the returned
grib data has changed, this is fixed in cfsr.py by using data[::-1,:]
(could have also removed the lats[::-1,0] reorientation, but this would
break the continuity with previously generated files)
This code is now only valid for pygrib >1.9.8

## Limitations

This make use of some in-house legacy code...
