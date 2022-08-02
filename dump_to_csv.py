# %%
import lxml.etree 
import csv
import tarfile
import os
from tqdm import tqdm
import glob
import argparse


# %%


def getHeaderFromXSLT(xslt):
    """
    Converts XSLT selectors (xsl:value-of) into list of strings to use them as header rows for CSV exports

    Args:
      xslt: parsed xslt file via lxml
    Returns:
      headers (list): headers for CSV file
    """
    root=xslt.getroot()
    
    headers=[]

    for item in root.findall('.//xsl:value-of',namespaces=root.nsmap):
        #ignore variables
        if (item.find('..').tag!='{http://www.w3.org/1999/XSL/Transform}variable'):
            el = item.attrib['select'].replace('.//','').replace('@','').replace('normalize-space(translate(','').replace(",'[¬]',''))",'').replace('$','').replace('/','__')
            if(el=='.'):
                #select the parent of the tag where selector is '.' in order to get value of select attribute
                el = item.find('..').attrib['select'].replace('.//','').replace('@','').replace('normalize-space(translate(','').replace(",'[¬]',''))",'').replace('$','').replace('/','__')
            headers.append(el)
    return headers

def readTar(file:str):
    """
    Generator to read all xml files in tar file

    Args:
      file (str): path of tar file
    Returns:
      files (generator): generator of files in tar
    """    
    with tarfile.open(file, "r:gz") as tar:
        # Go over each member
        for member in tar:
            if '.xml' in member.name:
                yield tar.extractfile(member).read()  

def writeRows(writer,tree,header,xslt):
    """
    Converts XML input using the XSLT template and write it in CSV as rows.

    XSLT return string with escape characters which are split into lines using line separator ($end_line$) and then into columns using column separator (¬).

    Args:
      writer: CSV writer
      tree: XML input parsed by lxml
      header: list of header names
      xslt: XSLT template parsed by lxml
    """
    transform = lxml.etree.XSLT(xslt)
    transformed=transform(tree)
    lines=str(transformed).split('$end_line$')
    for line in lines:
        #write only if there are values in the line
        if (len(header)<=len(line)):
            writer.writerow(line.split('¬'))


def main(outdir,file):

    xslt_files=[]
    headers=[]
    files=[]
    filenames=[]
    writers=[]

    #for each XSLT template a CSV file will be generated
    for xslt_file in glob.glob('xslt/*.xsl'):
        #load XSLT templates into list
        xslt=lxml.etree.parse(xslt_file)
        xslt_files.append(xslt)
        #file names using the naming of XSLT files
        name=os.path.basename(xslt_file).replace('.xsl','')
        filenames.append(name)
        #open CSV files for write
        f=open(os.path.join(outdir, "orcid_"+name+'.csv'), "w", encoding="utf8")
        files.append(f)
        #CSV headers from XSLT template
        headers.append(getHeaderFromXSLT(xslt))
        #CSV writers
        writers.append(csv.writer(f, lineterminator="\n"))


    #write header row for each CSV
    for i in range(0,len(files)):
        writers[i].writerow(headers[i])



    #to run on the subset
    # import itertools
    # sample_size=100000
    # for xml in tqdm(itertools.islice(readTar(file), sample_size),total=sample_size):
    for xml in tqdm(readTar(file),total=12638934): #using arbitrary 12m file as total number of 2021 extract +- in order to avoid lengthy xml file count
        # Extract file from tar
        tree = lxml.etree.fromstring(xml)
        #for each output transform xml file and write it into CSVs
        for i in range(0,len(files)):
            writeRows(writers[i],tree,headers[i],xslt_files[i])
            
    #close the CSV files
    for file in files:
        file.close()
            


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=str, help="output folder")
    parser.add_argument("--file", type=str, help="tar file name including extension")
    args = parser.parse_args()
    
    if args.outdir:
        outdir=args.outdir
    else:
        outdir='data'
    os.makedirs(outdir, exist_ok=True)

    if args.file:
        file=args.file
    else:
        file='ORCID_2021_10_summaries.tar.gz'
    
    
    main(outdir,file)
