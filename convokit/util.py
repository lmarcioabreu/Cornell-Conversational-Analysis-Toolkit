import urllib.request
import shutil
import os
import zipfile
import json
from typing import Dict
from convokit.model import Utterance, Corpus
import requests


# returns a path to the dataset file
def download(name: str, verbose: bool=True, data_dir: str=None, use_newest_version: bool=True) -> str:
    """Use this to download (or use saved) convokit data by name.

    :param name: Which item to download. Currently supported:

        - "wiki-corpus": Wikipedia Talk Page Conversations Corpus
            A medium-size collection of conversations from Wikipedia editors' talk pages.
            (see http://www.cs.cornell.edu/~cristian/Echoes_of_power.html)
        - "wikiconv-<year>": Wikipedia Talk Page Conversations Corpus
            Conversations data for the specified year.
        - "supreme-corpus": Supreme Court Dialogs Corpus
            A collection of conversations from the U.S. Supreme Court Oral Arguments.
            (see http://www.cs.cornell.edu/~cristian/Echoes_of_power.html)
        - "parliament-corpus": UK Parliament Question-Answer Corpus
            Parliamentary question periods from May 1979 to December 2016
            (see http://www.cs.cornell.edu/~cristian/Asking_too_much.html)
        - "conversations-gone-awry-corpus": Wiki Personal Attacks Corpus
            Wikipedia talk page conversations that derail into personal attacks as labeled by crowdworkers
            (see http://www.cs.cornell.edu/~cristian/Conversations_gone_awry.html)
        - "conversations-gone-awry-cmv-corpus"
            Discussion threads on the subreddit ChangeMyView (CMV) that derail into rule-violating behavior
            (see http://www.cs.cornell.edu/~cristian/Conversations_gone_awry.html)
        -  "movie-corpus": Cornell Movie-Dialogs Corpus
            A large metadata-rich collection of fictional conversations extracted from raw movie scripts.
            (see https://www.cs.cornell.edu/~cristian/Chameleons_in_imagined_conversations.html)
        -  "tennis-corpus": Tennis post-match press conferences transcripts
            Transcripts for tennis singles post-match press conferences for major tournaments between 2007 to 2015
            (see http://www.cs.cornell.edu/~liye/tennis.html)
        -  "reddit-corpus-small" Reddit Corpus (sampled):
            A sample from 100 highly-active subreddits
        -  "subreddit-<subreddit-name>": Subreddit Corpus
            A corpus made from the given subreddit
        -  "chromium-corpus": Chromium Conversations Corpus
            A collection of almost 1.5 million conversations and 2.8 million comments posted by developers reviewing proposed code changes in the Chromium project.
    :param verbose: Print checkpoint statements for download
    :param data_dir: Output path of downloaded file (default: ~/.convokit)
    :param use_newest_version: Redownload if new version is found

    :return: The path to the downloaded item.
    """

    dataset_config = requests.get('https://zissou.infosci.cornell.edu/convokit/datasets/download_config.json').json()

    cur_version = dataset_config['cur_version']
    DatasetURLs = dataset_config['DatasetURLs']

    if name.startswith("subreddit"):
        subreddit_name = name.split("-")[1]
        # print(subreddit_name)
        cur_version[name] = cur_version['subreddit']
        DatasetURLs[name] = get_subreddit_info(subreddit_name)
        # print(DatasetURLs[name])
    elif name.startswith("wikiconv"):
        wikiconv_year = name.split("-")[1]
        cur_version[name] = cur_version['wikiconv']
        DatasetURLs[name] = get_wikiconv_year_info(wikiconv_year)
    else:
        name = name.lower()

    custom_data_dir = data_dir

    data_dir = os.path.expanduser("~/.convokit/")

        #pkg_resources.resource_filename("convokit", "")
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)
    if not os.path.exists(os.path.join(data_dir, "downloads")):
        os.mkdir(os.path.join(data_dir, "downloads"))

    dataset_path = os.path.join(data_dir, "downloads", name)

    if custom_data_dir is not None:
        dataset_path = os.path.join(custom_data_dir, name)

    if not os.path.exists(os.path.dirname(dataset_path)):
        os.makedirs(os.path.dirname(dataset_path))

    dataset_path = os.path.realpath(dataset_path)

    needs_download = False
    downloadeds_path = os.path.join(data_dir, "downloads", "downloaded.txt")
    if not os.path.isfile(downloadeds_path):
        open(downloadeds_path, "w").close()
    with open(downloadeds_path, "r") as f:
        downloaded_lines = f.read().splitlines()
        downloaded = {}
        downloaded_paths = {}
        for l in downloaded_lines:
            dname, path, version = l.split("$#$")
            version = int(version)
            if dname not in downloaded or downloaded[dname] < version:
                downloaded[dname, path] = version
                downloaded_paths[dname] = path
                if custom_data_dir is None and name == dname:
                    dataset_path = os.path.join(path, name)

        # print(list(downloaded.keys()))
        if (name, os.path.dirname(dataset_path)) in downloaded:
            if use_newest_version and name in cur_version and \
                downloaded[name, os.path.dirname(dataset_path)] < cur_version[name]:
                    needs_download = True
        else:
            needs_download = True

    if needs_download:

        print("Downloading {} to {}".format(name, dataset_path))
    #name not in downloaded or \
    #    (use_newest_version and name in cur_version and
    #        downloaded[name] < cur_version[name]):
        if name.endswith("-motifs"):
            for url in DatasetURLs[name]:
                full_name = name + url[url.rfind('/'):]
                if full_name not in downloaded:
                    motif_file_path = dataset_path + url[url.rfind('/'):]
                    if not os.path.exists(os.path.dirname(motif_file_path)):
                        os.makedirs(os.path.dirname(motif_file_path))
                    download_helper(motif_file_path, url, verbose, full_name, downloadeds_path)
        else:
            url = DatasetURLs[name]
            download_helper(dataset_path, url, verbose, name, downloadeds_path)
    else:

        print("Dataset already exists at {}".format(dataset_path))
        dataset_path = os.path.join(downloaded_paths[name], name)

    return dataset_path

def download_helper(dataset_path: str, url: str, verbose: bool, name: str, downloadeds_path: str) -> None:

    if url.lower().endswith(".corpus") or url.lower().endswith(".corpus.zip") or url.lower().endswith(".zip"):
        dataset_path += ".zip"

    with urllib.request.urlopen(url) as response, \
            open(dataset_path, "wb") as out_file:
        if verbose:
            l = float(response.info()["Content-Length"])
            length = str(round(l / 1e6, 1)) + "MB" \
                if l > 1e6 else \
                str(round(l / 1e3, 1)) + "KB"
            print("Downloading", name, "from", url,
                  "(" + length + ")...", end=" ", flush=True)
        shutil.copyfileobj(response, out_file)

    # post-process (extract) corpora
    if name.startswith("subreddit"):
        with zipfile.ZipFile(dataset_path, "r") as zipf:
            corpus_dir = os.path.join(os.path.dirname(dataset_path), name)
            if not os.path.exists(corpus_dir):
                os.mkdir(corpus_dir)
            zipf.extractall(corpus_dir)

    elif url.lower().endswith(".corpus") or url.lower().endswith(".zip"):
        #print(dataset_path)
        with zipfile.ZipFile(dataset_path, "r") as zipf:
            zipf.extractall(os.path.dirname(dataset_path))

    if verbose:
        print("Done")
    with open(downloadeds_path, "a") as f:
        fn = os.path.join(os.path.dirname(dataset_path), name)#os.path.join(os.path.dirname(data), name)
        f.write("{}$#${}$#${}\n".format(name, os.path.realpath(os.path.dirname(dataset_path) + "/"), corpus_version(fn)))
        #f.write(name + "\n")

def corpus_version(filename: str) -> int:
    with open(os.path.join(filename, "index.json")) as f:
        d = json.load(f)
        return int(d["version"])

# retrieve grouping and completes the download link for subreddit
def get_subreddit_info(subreddit_name: str) -> str:

    # base directory of subreddit corpuses
    subreddit_base = "http://zissou.infosci.cornell.edu/convokit/datasets/subreddit-corpus/"
    data_dir = subreddit_base + "corpus-zipped/"

    groupings_url = subreddit_base + "subreddit-groupings.txt"
    groups_fetched = urllib.request.urlopen(groupings_url)

    groups = [line.decode("utf-8").strip("\n") for line in groups_fetched]

    for group in groups:
        if subreddit_in_grouping(subreddit_name, group):
            # return os.path.join(data_dir, group, subreddit_name + ".corpus.zip")
            return data_dir + group + "/" + subreddit_name + ".corpus.zip"

    print("The subreddit requested is not available.")

    return ""

def subreddit_in_grouping(subreddit: str, grouping_key: str) -> bool:
    """
    :param subreddit: subreddit name
    :param grouping_key: example: "askreddit~-~blackburn"
    :return: if string is within the grouping range
    """
    bounds = grouping_key.split("~-~")
    if len(bounds) == 1:
        print(subreddit, grouping_key)
    return bounds[0] <= subreddit <= bounds[1]

def get_wikiconv_year_info(year: str) -> str:
    """completes the download link for wikiconv"""

    # base directory of wikicon corpuses
    wikiconv_base = "http://zissou.infosci.cornell.edu/convokit/datasets/wikiconv-corpus/"
    data_dir = wikiconv_base + "corpus-zipped/"

    return data_dir + year + "/full.corpus"

def meta_index(corpus: Corpus=None, filename: str=None) -> Dict:
    keys = ["utterances-index", "conversations-index", "users-index",
            "overall-index"]
    if corpus is not None:
        return {k: v for k, v in corpus.meta_index.items() if k in keys}
    if filename is not None:
        with open(os.path.join(filename, "index.json")) as f:
            d = json.load(f)
            return d

def display_thread_helper(thread: Dict[str, Utterance], root: str, indent: int=0) -> None:
    """
    Helper method for display_thread().

    :param thread: Dict for Utterance id -> Utterance for all utterances in the thread
    :param root: root of thread, aka thread id
    :param indent: Level of indentation so that reply structure of thread can be visualized
    """

    print(" "*indent + thread[root].user.name)
    children = [k for k, v in thread.items() if v.reply_to == root]
    for child in children:
        display_thread_helper(thread, child, indent=indent+4)

def display_thread(threads: Dict[str, Dict[str, Utterance]], root: str) -> None:
    """
    Prints to console a compact representation of a specified thread, e.g. a comment thread on a reddit post.
    Example usage: threads = corpus.utterance_threads(prefix_len=10, include_root=False)
    display_thread(threads, 'e5717fs') (assuming 'e5717fs' is a valid key in threads)

    :param threads: Dictionary of threads, where key is the thread id, and the value is a Dict of Utterance ids -> Utterance.
    :param root: thread id
    """

    return display_thread_helper(threads[root],root)
