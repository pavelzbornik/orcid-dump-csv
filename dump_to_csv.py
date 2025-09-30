# %%
import lxml.etree 
import csv
import tarfile
import os
from tqdm import tqdm
import glob
import argparse
import io
from concurrent.futures import ProcessPoolExecutor
import multiprocessing


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

def getMembers(file:str):
    """
    Returns all the files in tar

    Args:
      file (str): path of tar file
    Returns:
      files: list of TarFile objects
    """    
    print('Getting list of all the files in TarFile, this will take some time')
    with tarfile.open(file, "r:gz") as tar:
        return tar.getmembers()


def processChunk(chunk,tar):
    
    buffer =''
    for member in chunk:
        # Extract member
        if '.xml' in member.name:
            content=io.BytesIO(tar.extractfile(member).read()).getvalue().decode('utf-8')
            buffer=buffer+content.replace('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n','')

    buffer='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'+'<records>'+buffer+'</records>'        
    xml=buffer.encode(encoding='utf-8', errors='strict')

    return lxml.etree.fromstring(xml)


def processChunkWorker(args):
    """
    Worker function for parallel processing of chunks.
    Opens the tar file, processes the chunk, applies all XSLT transformations,
    and returns the resulting CSV rows.
    
    Args:
        args: tuple of (chunk, tar_file_path, xslt_file_paths)
    Returns:
        list of lists: Each inner list contains rows for one XSLT template
    """
    chunk, tar_file_path, xslt_file_paths = args
    
    # Open tar file in worker process
    with tarfile.open(tar_file_path, "r:gz") as tar:
        # Process the chunk
        buffer = processChunk(chunk, tar)
    
    # Apply each XSLT transformation and collect rows
    results = []
    for xslt_file in xslt_file_paths:
        xslt = lxml.etree.parse(xslt_file)
        header = getHeaderFromXSLT(xslt)
        
        # Transform and get rows
        transform = lxml.etree.XSLT(xslt)
        transformed = transform(buffer)
        lines = str(transformed).split('$end_line$')
        
        rows = []
        for line in lines:
            # Collect only if there are values in the line
            if len(header) <= len(line):
                rows.append(line.split('¬'))
        
        results.append(rows)
    
    return results


def main(outdir,file,workers=None):

    xslt_files=[]
    headers=[]
    files=[]
    filenames=[]
    writers=[]

    #get the number of files this takes some time
    tar_files=getMembers(file)

    #for each XSLT template a CSV file will be generated
    xslt_file_paths = glob.glob('xslt/*.xsl')
    for xslt_file in xslt_file_paths:
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

    #from the all tar files generate chunks
    chunk_size = 15 #number of xml files in chunk
    chunks = [tar_files[i:i + chunk_size] for i in range(0, len(tar_files), chunk_size)]
    
    # Determine number of workers
    if workers is None:
        workers = multiprocessing.cpu_count()
    elif workers < 1:
        print(f"Warning: workers must be at least 1, using 1 worker")
        workers = 1
    
    print(f'Processing {len(chunks)} chunks, each chunk is {chunk_size} xml files. Total files: {len(tar_files)}')
    print(f'Using {workers} parallel workers')
    
    # Prepare arguments for worker processes
    worker_args = [(chunk, file, xslt_file_paths) for chunk in chunks]
    
    # Process chunks in parallel
    with ProcessPoolExecutor(max_workers=workers) as executor:
        # Use tqdm to track progress
        for result in tqdm(executor.map(processChunkWorker, worker_args), total=len(chunks)):
            # result is a list of lists: one list of rows per XSLT template
            for i in range(len(files)):
                for row in result[i]:
                    writers[i].writerow(row)
                
    #close the CSV files
    for file in files:
        file.close()
            


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=str, help="output folder")
    parser.add_argument("--file", type=str, help="tar file name including extension")
    parser.add_argument("--workers", type=int, help="number of parallel workers (default: number of CPU cores)")
    args = parser.parse_args()
    
    if args.outdir:
        outdir=args.outdir
    else:
        outdir='data'
    os.makedirs(outdir, exist_ok=True)

    if args.file:
        file=args.file
    else:
        file='ORCID_2022_10_summaries.tar.gz'
    
    workers = args.workers if args.workers is not None else None
    
    main(outdir,file,workers)
