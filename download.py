import requests
from tqdm import tqdm



def main():
    url ='https://orcid.figshare.com/ndownloader/files/37635374'
    file ='ORCID_2022_10_summaries.tar.gz'

    total_size_in_bytes= 21231574177

    print(f'Downloading {file} of {int(total_size_in_bytes) / float(1 << 20):.2f} MB from {url}')
    response = requests.get(url, stream=True)
    block_size = 1024 #1 Kilobyte
    progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
    with open(file, 'wb') as f:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            f.write(data)
    progress_bar.close()



if __name__ == "__main__":
    main()