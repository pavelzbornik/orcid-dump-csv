# ORCID dump to CSV

Scope of this script is to convert ORCID yearly **summaries** XML dump (*ORCID_YYYY_MM_summaries.tar.gz*) into CSV, activities files are not processed.

Further information about the dump is available at [Bulk data integration guide](https://info.orcid.org/documentation/integration-guide/working-with-bulk-data/), the 2021 file is missing in the list, but is available in the section on  [Public data file use policy](https://info.orcid.org/public-data-file-use-policy/)

### XSD documentation of the XML files in the dump
XML files use the same structure as ORCID API and therefore the XSD files available at [ORCID GitHub](https://github.com/ORCID/orcid-model/tree/master/src/main/resources/record_2.1) are the base information source.


## How the script works
The script is leveraging XSLT transformation of XML files, [find more about XSLT on W3S](https://www.w3schools.com/xml/xsl_intro.asp), where input XML file is converted into a string with delimiters and than turned into 'normalized' CSV file. Script generate CSV file per XSLT file as a way to deal with nested structure of the XML.

- line separator: `$end_line$`
- column separator: `¬`

### Speed improvements
To speed up the process, **xml files are first concatenated** by the number defined in `chunk_size`, from tests the chunk size is best between 10-25 and `chunk_size=15` is used in the script. This approach **reduce the runtime by 50%** compared to transforming each individual xml file. Concatenation is done, by string operations with source xml file and new tag `records` is introduced to list ORCID `record:record`.

### XSLT tinkering

All XSLT files are in the `xslt` folder, if you want to experiment you can use web XSLT editors for example [.NET XSLT Fiddle](https://xsltfiddle.liberty-development.net/) and XML file from the dump. 

For this experimentation recommend to use new line character for visual representations of different rows in the XSLT Fiddle.

Replace `$end_line$` in XSLT
```xml 
<xsl:text>$end_line$</xsl:text> <!-- newline character -->
```
With newline character `&#10;` to escape rows
```xml
<xsl:text>&#10;</xsl:text> <!-- newline character -->
```

## Running the script

### 1. Create virtual environment and install packages

Recommended to create virtual environment
```sh
python3 -m venv .venv
```

Install packages
```sh
pip3 install -r requirements.txt
```

### 2. Download the dump

Script assumes 2022 summaries dump file `ORCID_2022_10_summaries.tar.gz` stored in the same folder with the script and default output folder `data`, both is possible to change with arguments.

If you want to download the file first you can run download script which will fetch 2021 dump into the script folder
```sh
python3 download.py
```

### 3. Run the script

### Notice
- Please note due to the dump size, the script will run for several hours (20+)
- Have enough free space on your disk (50 GB)

Run the script using default settings
```sh
python3 dump_to_csv.py
```

Adding file path and output dir arguments
```sh
python3 dump_to_csv.py --file ORCID_2022_10_summaries.tar.gz --outdir csv
```
